import subprocess
import threading
import signal
import socket
import queue
import time
import gi
import re
gi.require_version('Gst', '1.0')
gi.require_version('GstVideo', '1.0')
from gi.repository import Gst, GstVideo
from Server_vars import *
from Common_vars import *

Gst.init(None)


class ClientThread(threading.Thread):
    srv = None

    def __init__(self):
        threading.Thread.__init__(self)

        # The shutdown_flag is a threading.Event object that
        # indicates whether the thread should be terminated.
        self.shutdown_flag = threading.Event()

    def run(self):
        Console.print('Client Thread #%s started' % self.ident)

        while not self.shutdown_flag.is_set():
            success = False
            # while self.create_socket() is False:
            for n in range(SO_RETRY_LIMIT):
                success = self.create_socket()
                if success is True:
                    break
                else:
                    time.sleep(1)

            if success is False:
                self.shutdown_flag.set()
                Console.print("Bind failed for", SO_RETRY_LIMIT, "times. Resetting socket.")
                self.closesrv()
            else:
                self.listen_socket()

        # ... Clean shutdown code here ...
        Console.print('Client Thread #%s stopped' % self.ident)

    def listen_socket(self):
        self.srv.listen(5)
        Console.print('Socket now listening on ' + HOST + "[" + Port_COMM.__str__() + "]")

        conn = addr = None
        try:
            conn, addr = self.srv.accept()
        except OSError:
            Console.print("User break")

        if conn is None:
            Console.print("No connection interrupted.")
        else:
            client_IP = addr[0]
            Console.print('Connected with ' + client_IP + ':' + str(addr[1]))
            # Sending message to connected client
            # conn.send('AWAITING__COMM\n'.encode(Encoding))  # send only takes string
            data = self.get_bytes_from_client(conn, 9)
            if len(data) == 9:
                Console.print("Message Validation... ")
                Protocol = None
                if data[1:3].decode(Encoding) == "TC":
                    Protocol = TCP
                elif data[1:3].decode(Encoding) == "UD":
                    Protocol = UDP

                if Protocol is not None:
                    Video_Mode = int(data[3]) - 48  # Substract 48 ASCII to decode the mode
                    ConnIP  = data[4].__str__() + "."
                    ConnIP += data[5].__str__() + "."
                    ConnIP += data[6].__str__() + "."
                    ConnIP += data[7].__str__()
                    Console.print("Client: " + client_IP + "[" + PROTO_NAME[Protocol] + "]")
                    Console.print("Video Codec is " + VideoCodec[Video_Mode])

                    conn = self.connection_loop(conn, Video_Mode, client_IP, Protocol)
                else:
                    Console.print("Invalid message detected! Breaking connection.")

                if conn:
                    # came out of loop
                    conn.close()
                    self.closesrv()

                    Console.print("Connection with %s closed." % str(addr))
            else:
                Console.print("Incomplete message received! Breaking connection.")

    def connection_loop(self, conn, Video_Mode, client_IP, Protocol):
        noData_cnt = 0
        COMM_vars.streaming_mode = 0
        self.Stream_Thread = StreamThread(Video_Mode, client_IP, Protocol)
        self.Stream_Thread.start()
        # now keep talking with the client
        while not self.shutdown_flag.is_set():
            # Receiving from client
            data = self.get_bytes_from_client(conn, 9)
            try:
                data_len = len(data)
            except TypeError:
                data_len = False

            if data_len < 9:
                noData_cnt += 1
                if noData_cnt > RETRY_LIMIT:
                    Console.print("NO DATA - closing connection")
                    break
            else:
                noData_cnt = 0

                resolution = self.decode_data(data)
                response = self.encode_data(data)

                if Debug > 0:
                    Console.print("Chksum", response[0].__str__())

                    if Debug > 2:
                        Console.print("DATA_IN>> " + data.__str__())
                        Console.print("DATA_OUT>> " + response.__str__())

                if self.Stream_Thread.res_queue.empty():
                    self.Stream_Thread.req_resolution = resolution

                try:
                    conn.sendall(response.encode(Encoding))
                except BrokenPipeError:
                    Console.print("transmit_message: BrokenPipeError")
                    break
                except AttributeError:
                    Console.print("transmit_message: AttributeError")
                    break
                except OSError:
                    Console.print("transmit_message: OSError (client lost)")
                    break

        self.Stream_Thread.shutdown_flag.set()

        return conn

    def get_bytes_from_client(self, conn, count):
        try:
            data = conn.recv(count)
        except socket.error:
            data = None
            Console.print("Socket error!")

        return data

    @staticmethod
    def decode_data(data):
        COMM_vars.motor_Power[RIGHT] = data[1]
        COMM_vars.motor_Power[LEFT]  = data[2]

        COMM_vars.camPosition[X_AXIS] = data[3]
        COMM_vars.camPosition[Y_AXIS] = data[4]

        # Force 8bit format to extract switches
        Cntrl_Mask1 = format(data[5] + 256, 'b')
        COMM_vars.light     = int(Cntrl_Mask1[7])
        COMM_vars.speakers  = int(Cntrl_Mask1[6])
        COMM_vars.mic       = bool(int(Cntrl_Mask1[5]))
        COMM_vars.display   = int(Cntrl_Mask1[4])
        COMM_vars.laser     = int(Cntrl_Mask1[3])
        COMM_vars.AutoMode  = int(Cntrl_Mask1[2])

        resolution = data[6] - (int(data[6] / 10) * 10)
        Bitratemask = data[7]
        if Bitratemask >= 100:
            COMM_vars.Vbitrate = int(str(Bitratemask)[1])
            COMM_vars.Abitrate = int(str(Bitratemask)[2])

        return resolution

    @staticmethod
    def encode_data(data):
        retstr = chr(calc_checksum(data))
        retstr += chr(COMM_vars.motor_PWR[RIGHT])
        retstr += chr(COMM_vars.motor_PWR[LEFT])
        retstr += chr(COMM_vars.motor_RPM[RIGHT])
        retstr += chr(COMM_vars.motor_RPM[LEFT])
        retstr += chr(data[5])  # CntrlMask1
        retstr += chr(COMM_vars.streaming_mode)  # CntrlMask2
        retstr += chr(10) + chr(10)
        retstr += chr(COMM_vars.coreTemp)
        retstr += COMM_vars.current
        retstr += COMM_vars.voltage

        return retstr.ljust(RECMSGLEN, chr(10))

    def create_socket(self):
        # Create Socket
        self.srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # ClientThread.srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        Console.print('Socket created')
        srv_address = (HOST, Port_COMM)

        try:
            self.srv.bind(srv_address)

        except socket.error as msg:
            Console.print('Bind failed. Error Code : ' + msg.__str__())
            # Console.print('Bind failed. Error Code : ' + str(msg[0]) + ' Message ' + msg[1])
            return False

        except OSError as msg:
            Console.print('Bind failed. Error Code : ' + str(msg[0]) + ' Message ' + msg[1])
            Console.print('Advice: check for python process to kill it!')
            return False

        # Start listening on socket
        Console.print('Socket bind complete')
        return True

    def closesrv(self):
        if self.srv is None:
            Console.print("Socket is closed!")
        else:
            Console.print("Closing socket...")
            try:
                self.srv.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass

            try:
                self.srv.close()
            except AttributeError:
                pass

            ClientThread.srv = None
            time.sleep(.5)


class StreamThread(threading.Thread):
    req_resolution = 0
    Source_test = 0
    Source_h264 = 1

    def __init__(self, Video_Mode, client_IP, Protocol):
        threading.Thread.__init__(self)
        self.shutdown_flag = threading.Event()

        self.res_queue = queue.Queue()

        self.Video_Mode = Video_Mode

        self.player_video = [Gst.Pipeline.new("player_video_test"),
                             Gst.Pipeline.new("player_video")]
        self.capsfilter_video = [Gst.ElementFactory.make("capsfilter", "capsfilter_test"),
                                 Gst.ElementFactory.make("capsfilter", "capsfilter")]
        self.source_video = [Gst.ElementFactory.make("videotestsrc", "video-source_test"),
                             Gst.ElementFactory.make("v4l2src", "video-source")]
        self.rtimer_video = [Gst.ElementFactory.make("rtph264pay", "rtimer_test_udp"),
                             Gst.ElementFactory.make("rtph264pay", "rtimer_udp")]

        self.player_audio = [Gst.Pipeline.new("player_audio_test"),
                             Gst.Pipeline.new("player_audio")]
        self.source_audio = [Gst.ElementFactory.make("audiotestsrc", "audio-source_test"),
                             Gst.ElementFactory.make("pulsesrc", "audio-source")]
        self.capsfilter_audio = [Gst.ElementFactory.make("capsfilter", "capsfilter_audio_test"),
                                 Gst.ElementFactory.make("capsfilter", "capsfilter_audio")]

        if Protocol == TCP:
            self.encoder_video = [Gst.ElementFactory.make("gdppay", "encoder_test"),
                                  Gst.ElementFactory.make("gdppay", "encoder")]

            self.sink_video = [Gst.ElementFactory.make("tcpserversink", "video-output_test"),
                               Gst.ElementFactory.make("tcpserversink", "video-output")]

            if HOST:
                self.sink_video[self.Source_test].set_property("host", HOST)
                self.sink_video[self.Source_h264].set_property("host", HOST)
            else:
                self.sink_video[self.Source_test].set_property("host", "0.0.0.0")
                self.sink_video[self.Source_h264].set_property("host", "0.0.0.0")
# ToDo:
            self.sink_video[self.Source_test].set_property("sync", False)
            self.sink_video[self.Source_h264].set_property("sync", False)
            self.gst_init_video_test()
            self.gst_init_cam_tcp()

            self.sink_audio = [Gst.ElementFactory.make("tcpserversink", "sink_audio_test"),
                               Gst.ElementFactory.make("tcpserversink", "sink_audio")]
        else:
            self.encoder_video = [Gst.ElementFactory.make(H264_ENC, "encoder_test_udp"),
                                  Gst.ElementFactory.make("h264parse", "encoder_udp")]
            self.encoder_video[self.Source_test].set_property("tune", "zerolatency")
            self.sink_video = [Gst.ElementFactory.make("udpsink", "video-output_test"),
                               Gst.ElementFactory.make("udpsink", "video-output")]
            self.sink_video[self.Source_test].set_property("host", client_IP)
            self.sink_video[self.Source_h264].set_property("host", client_IP)
            self.sink_video[self.Source_test].set_property("sync", True)
            self.sink_video[self.Source_h264].set_property("sync", True)

            self.gst_init_video_test_udp()
            self.gst_init_cam_udp()

            self.sink_audio = [Gst.ElementFactory.make("udpsink", "sink_audio_test"),
                               Gst.ElementFactory.make("udpsink", "sink_audio")]

        # pulsesrc device=2 ! audio/x-raw,rate=32000 ! audioresample ! speexenc ! audioresample ! speexenc !
        #          rtpspeexpay ! udpsink host=x.x.x.x port=xxxx sync=false
        self.resample_audio = [Gst.ElementFactory.make("audioresample", "resample_audio_test"),
                               Gst.ElementFactory.make("audioresample", "resample_audio")]
        self.encoder_audio  = [Gst.ElementFactory.make("speexenc", "encoder_audio_test"),
                               Gst.ElementFactory.make("speexenc", "encoder_audio")]
        self.rtimer_audio = [Gst.ElementFactory.make("rtpspeexpay", "rtimer_audio_test"),
                             Gst.ElementFactory.make("rtpspeexpay", "rtimer_audio")]

        self.sink_audio[self.Source_test].set_property("host", client_IP)
        self.sink_audio[self.Source_h264].set_property("host", client_IP)
        self.sink_audio[self.Source_test].set_property("sync", True)
        self.sink_audio[self.Source_h264].set_property("sync", True)
        self.source_audio[self.Source_test].set_property("wave", 0)
        self.source_audio[self.Source_h264].set_property("device", MIC0_DEVICE)

        # caps = Gst.Caps.from_string("audio/x-raw, rate=32000")
        # self.capsfilter_audio[self.Source_h264].set_property("caps", caps)
        # self.capsfilter_audio[self.Source_test].set_property("caps", caps)

        self.gst_init_audio_udp()

        self.sink_video[self.Source_test].set_property("port", Port_CAM0)
        self.sink_video[self.Source_h264].set_property("port", Port_CAM0)

        self.sink_audio[self.Source_test].set_property("port", Port_MIC0)
        self.sink_audio[self.Source_h264].set_property("port", Port_MIC0)

    def gst_init_video_test(self):
        ####################################################################
        ### Build test video pipelineas following:
        ###   Source[cam] > Caps > Encoder > Sink[tcp]
        ####################################################################
        self.source_video[self.Source_test].set_property("pattern", "smpte")

        self.player_video[self.Source_test].add(self.source_video[self.Source_test])
        self.player_video[self.Source_test].add(self.capsfilter_video[self.Source_test])
        self.player_video[self.Source_test].add(self.encoder_video[self.Source_test])
        self.player_video[self.Source_test].add(self.sink_video[self.Source_test])

        self.source_video[self.Source_test].link(self.capsfilter_video[self.Source_test])
        self.capsfilter_video[self.Source_test].link(self.encoder_video[self.Source_test])
        self.encoder_video[self.Source_test].link(self.sink_video[self.Source_test])

    def gst_init_video_test_udp(self):
        ####################################################################
        ### Build test video pipelineas following:
        ###   Source[cam] > Caps > Encoder > Sink[tcp]
        ####################################################################
        self.source_video[self.Source_test].set_property("pattern", "smpte")

        self.player_video[self.Source_test].add(self.source_video[self.Source_test])
        self.player_video[self.Source_test].add(self.capsfilter_video[self.Source_test])
        self.player_video[self.Source_test].add(self.encoder_video[self.Source_test])
        self.player_video[self.Source_test].add(self.rtimer_video[self.Source_test])
        self.player_video[self.Source_test].add(self.sink_video[self.Source_test])

        self.source_video[self.Source_test].link(self.capsfilter_video[self.Source_test])
        self.capsfilter_video[self.Source_test].link(self.encoder_video[self.Source_test])
        self.encoder_video[self.Source_test].link(self.rtimer_video[self.Source_test])
        self.rtimer_video[self.Source_test].link(self.sink_video[self.Source_test])

    def gst_init_cam_tcp(self):
        ####################################################################
        ### Build video pipelineas following:
        ###   Source[cam] > Caps > Parser > Codec_Opt > Encoder > Sink[tcp]
        ####################################################################
        parser = Gst.ElementFactory.make("h264parse", "parser")

        self.rtimer_video[self.Source_h264].set_property("config_interval", 1)
        self.rtimer_video[self.Source_h264].set_property("pt", 96)

        self.player_video[self.Source_h264].add(self.source_video[self.Source_h264])
        self.player_video[self.Source_h264].add(self.capsfilter_video[self.Source_h264])
        self.player_video[self.Source_h264].add(parser)
        self.player_video[self.Source_h264].add(self.rtimer_video[self.Source_h264])
        self.player_video[self.Source_h264].add(self.encoder_video[self.Source_h264])
        self.player_video[self.Source_h264].add(self.sink_video[self.Source_h264])

        self.source_video[self.Source_h264].link(self.capsfilter_video[self.Source_h264])
        self.capsfilter_video[self.Source_h264].link(parser)
        parser.link(self.rtimer_video[self.Source_h264])
        self.rtimer_video[self.Source_h264].link(self.encoder_video[self.Source_h264])
        self.encoder_video[self.Source_h264].link(self.sink_video[self.Source_h264])

    def gst_init_cam_udp(self):
        ####################################################################
        ### Build video pipelineas following:
        ###   Source[cam] > Caps > Parser > Codec_Opt > Encoder > Sink[tcp]
        ####################################################################

        self.player_video[self.Source_h264].add(self.source_video[self.Source_h264])
        self.player_video[self.Source_h264].add(self.capsfilter_video[self.Source_h264])
        self.player_video[self.Source_h264].add(self.encoder_video[self.Source_h264])
        self.player_video[self.Source_h264].add(self.rtimer_video[self.Source_h264])
        self.player_video[self.Source_h264].add(self.sink_video[self.Source_h264])

        self.source_video[self.Source_h264].link(self.capsfilter_video[self.Source_h264])
        self.capsfilter_video[self.Source_h264].link(self.encoder_video[self.Source_h264])
        self.encoder_video[self.Source_h264].link(self.rtimer_video[self.Source_h264])
        self.rtimer_video[self.Source_h264].link(self.sink_video[self.Source_h264])

    def gst_init_audio_udp(self):
        self.player_audio[self.Source_test].add(self.source_audio[self.Source_test])
        self.player_audio[self.Source_test].add(self.capsfilter_audio[self.Source_test])
        self.player_audio[self.Source_test].add(self.resample_audio[self.Source_test])
        self.player_audio[self.Source_test].add(self.encoder_audio[self.Source_test])
        self.player_audio[self.Source_test].add(self.rtimer_audio[self.Source_test])
        self.player_audio[self.Source_test].add(self.sink_audio[self.Source_test])

        self.source_audio[self.Source_test].link(self.capsfilter_audio[self.Source_test])
        self.capsfilter_audio[self.Source_test].link(self.resample_audio[self.Source_test])
        self.resample_audio[self.Source_test].link(self.encoder_audio[self.Source_test])
        self.encoder_audio[self.Source_test].link(self.rtimer_audio[self.Source_test])
        self.rtimer_audio[self.Source_test].link(self.sink_audio[self.Source_test])

        self.player_audio[self.Source_h264].add(self.source_audio[self.Source_h264])
        self.player_audio[self.Source_h264].add(self.capsfilter_audio[self.Source_h264])
        self.player_audio[self.Source_h264].add(self.resample_audio[self.Source_h264])
        self.player_audio[self.Source_h264].add(self.encoder_audio[self.Source_h264])
        self.player_audio[self.Source_h264].add(self.rtimer_audio[self.Source_h264])
        self.player_audio[self.Source_h264].add(self.sink_audio[self.Source_h264])

        self.source_audio[self.Source_h264].link(self.capsfilter_audio[self.Source_h264])
        self.capsfilter_audio[self.Source_h264].link(self.resample_audio[self.Source_h264])
        self.resample_audio[self.Source_h264].link(self.encoder_audio[self.Source_h264])
        self.encoder_audio[self.Source_h264].link(self.rtimer_audio[self.Source_h264])
        self.rtimer_audio[self.Source_h264].link(self.sink_audio[self.Source_h264])

    def run(self):
        Console.print('Streamer Thread #%s started' % self.ident)

        req_mode = Gst.State.READY
        self.res_queue.put(req_mode)

        Update = False
        res_switch = 9
        curr_resolution = 0

        req_audio_mode = [Gst.State.READY, Gst.State.PLAYING]
        curr_mic0 = False
        curr_AudioBitrate = None
        self.player_audio[self.Video_Mode].set_state(req_audio_mode[curr_mic0])

        while not self.shutdown_flag.is_set():
            if AudioBitrate[COMM_vars.Abitrate] != curr_AudioBitrate:
                self.player_audio[self.Video_Mode].set_state(Gst.State.READY)
                curr_mic0 = None

            if curr_mic0 is not COMM_vars.mic:
                if COMM_vars.mic is True:
                    Console.print(" Mic0 requested rate:", AudioBitrate[COMM_vars.Abitrate])
                    caps = Gst.Caps.from_string("audio/x-raw, rate=" + AudioBitrate[COMM_vars.Abitrate])
                    self.capsfilter_audio[self.Source_h264].set_property("caps", caps)
                    self.capsfilter_audio[self.Source_test].set_property("caps", caps)
                else:
                    Console.print(" Mic0 muted")

                self.player_audio[self.Video_Mode].set_state(req_audio_mode[COMM_vars.mic])
                curr_mic0 = COMM_vars.mic
                curr_AudioBitrate = AudioBitrate[COMM_vars.Abitrate]

            if curr_resolution != self.req_resolution:
                if self.req_resolution > 0:
                    Console.print("Changing Gstreamer resolution")
                    ### CHANGE RESOLUTION CAPS ###
                    caps = Gst.Caps.from_string("video/x-" + VideoCodec[self.Video_Mode] + capsstr[self.req_resolution])
                    self.capsfilter_video[self.Video_Mode].set_property("caps", caps)

                    if self.Video_Mode is not False:
                        self.res_queue.put(Gst.State.READY)
                        # self.res_queue.put(Gst.State.PAUSED)
                        self.res_queue.put(Gst.State.PLAYING)

                    self.res_queue.put(Gst.State.PLAYING)
                    if curr_resolution == 0:
                        self.res_queue.put(Gst.State.PLAYING)
                else:
                    self.res_queue.put(Gst.State.PAUSED)

                curr_resolution = self.req_resolution

            if not self.res_queue.empty():
                curr_state = self.player_video[self.Video_Mode].get_state(1)[1]
                if curr_state == req_mode:
                    Update = True
                    req_mode = self.res_queue.get()
                else:
                    res_switch += 1

                if req_mode != curr_state:
                    res_switch = bool(req_mode) * 10

            if res_switch == 10:
                res_switch = 0
                if req_mode == Gst.State.PAUSED:
                    Console.print("Pausing Gstreamer", end="...")
                elif req_mode == Gst.State.READY:
                    Console.print("Preparing Gstreamer", end="...")
                elif req_mode == Gst.State.PLAYING:
                    Console.print("Requested streaming in mode " + self.req_resolution.__str__() + '... ')
                else:
                    Console.print('ERROR: resolution' + self.req_resolution.__str__() + ", mode " + req_mode)
                    res_switch = 10

                if res_switch == 0:
                    self.player_video[self.Video_Mode].set_state(req_mode)

            if Update is True:
                Update = False
                if curr_state == Gst.State.PAUSED:
                    Console.print("Paused.")
                elif curr_state == Gst.State.READY:
                    Console.print("Ready.")
                elif curr_state == Gst.State.PLAYING:
                    Console.print("Streaming in mode " + self.req_resolution.__str__())
                    COMM_vars.streaming_mode = self.req_resolution

            time.sleep(.25)

        self.player_video[self.Video_Mode].set_state(Gst.State.PAUSED)
        self.player_video[self.Source_test].set_state(Gst.State.NULL)
        self.player_video[self.Source_h264].set_state(Gst.State.NULL)

        self.player_audio[self.Video_Mode].set_state(Gst.State.READY)
        self.player_audio[self.Source_test].set_state(Gst.State.NULL)
        self.player_audio[self.Source_h264].set_state(Gst.State.NULL)

        Console.print('Streamer Thread #%s stopped' % self.ident)


class DriverThread(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)

        # The shutdown_flag is a threading.Event object that
        # indicates whether the thread should be terminated.
        self.shutdown_flag = threading.Event()

    def run(self):
        Console.print('Driver Thread #%s started' % self.ident)
        inc = 30 ; adx = 1
        idx = 30
        while not self.shutdown_flag.is_set():

            # CURRENT - report continuously
            inc += adx
            if inc > 250 or inc < 30:
                adx = -adx
            COMM_vars.current = chr(60 + int(inc / 10)) + chr(int(inc % 100))

            # Voltage - report continuously
            COMM_vars.voltage = chr(130) + chr(35)

            # DistanceS1
            COMM_vars.distanceS1 = chr(+ 100)

            # Motor Power
            COMM_vars.motor_PWR = [60, 50]

            # Mmotor RPM
            COMM_vars.motor_RPM = [80, 80]

            # TEMP - report every 3sec
            if idx == 30:
                Tempstr = execute_cmd("LD_LIBRARY_PATH=/opt/vc/lib && /opt/vc/bin/vcgencmd measure_temp")
                Tempstr = re.findall(r"\d+", Tempstr.decode(Encoding))
                Temp = int(Tempstr[0]) * 10 + int(Tempstr[1])
                COMM_vars.coreTemp = int(Temp / 5)
                idx = 0

            time.sleep(.1)
            idx += 1

        Console.print('Driver Thread #%s stopped' % self.ident)


# Function for handling connections. This will be used to create threads
class ThreadManager():
    def __init__(self, GUI):
        # threading.Thread.__init__(self)
        # # The shutdown_flag is a threading.Event object that
        # # indicates whether the thread should be terminated.
        self.shutdown_flag = True

        signal.signal(signal.SIGTERM, self.ProgramExit)
        signal.signal(signal.SIGINT, self.ProgramExit)
        signal.signal(signal.SIGABRT, self.ProgramExit)


        self._GUI = GUI
        if GUI is False:
            SRV_vars.GUI_CONSOLE = False
        else:
            SRV_vars.GUI_CONSOLE = True

        self.Console = Console()
        self.Driver_Thread = DriverThread()
        self._init_ClientThread()

        Console.print("Console " + VERSION + " initialized\n")

    def _init_ClientThread(self):
        self.Client_Thread = ClientThread()

    def run(self):
        if self.shutdown_flag is False:
            if not self.Driver_Thread.is_alive():
                self.Driver_Thread.start()
            if not self.Client_Thread.is_alive():
                try:
                    self.Client_Thread.start()
                except RuntimeError:
                    self._init_ClientThread()
                    self.Client_Thread.start()
                    print("hehehe")
        else:
            if not(self.Client_Thread.shutdown_flag.is_set() and self.Client_Thread.shutdown_flag.is_set()):
                Console.print("shutting down services...")
                self._stop()

        self.Console.display_message(self._GUI)

        return True

    def _stop(self):
        self.Client_Thread.shutdown_flag.set()
        self.Driver_Thread.shutdown_flag.set()
        if self.Client_Thread.srv is not None:
            self.Client_Thread.closesrv()

        if self.Client_Thread.is_alive():
            self.Client_Thread.join()

        if self.Driver_Thread.is_alive():
            self.Driver_Thread.join()

        Console.print('Thread manager has stopped.')
        self.shutdown_flag = None
        self.Console.display_message(self._GUI)

    def ProgramExit(self, *args):
        Console.print("Exit requested!")
        self._stop()
        exit(0)

class Console:
    # if SRV_vars.GUI_CONSOLE is True:
    TextQueue = queue.Queue()

    def __init__(self):
        if SRV_vars.GUI_CONSOLE is True:
            print("GUI Console initialized.")
        else:
            print("Terminal output initialized.")
        # pass

    @staticmethod
    def print(*args, **kwargs):
        if SRV_vars.GUI_CONSOLE is True:
            l_args = list(args)
            if 'end' in kwargs:
                l_args.append(str(kwargs['end']))
            else:
                l_args.append("\n")

            Console.TextQueue.put(tuple(l_args))
        else:
            print(*args, **kwargs)

    def display_message(self, Txt_Console):
        if SRV_vars.GUI_CONSOLE is False:
            return

        TextBuffer = Txt_Console.get_buffer()
        if not self.TextQueue.empty():
            Text = self.TextQueue.get()
            # if Text:
            for cText in Text:
                TextBuffer.insert_at_cursor(str(cText) + " ")

            Txt_Console.scroll_mark_onscreen(TextBuffer.get_insert())
            # time.sleep(.2)


def execute_cmd(cmd_string):
    #  system("clear")
    # retcode = system(cmd_string)
    stdout = subprocess.check_output(cmd_string, shell=True)
    # if retcode == 0:
    #     if Debug > 1: print("\nCommand executed successfully")
    # else:
    #     if Debug > 1: print("\nCommand terminated with error: " + str(retcode))
    # raw_input("Press enter")
    return stdout


class ServiceExit(Exception):
    """
    Custom exception which is used to trigger the clean exit
    of all running threads and the main program.
    """
#    pass
