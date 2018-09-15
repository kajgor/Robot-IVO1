import threading
import signal
import socket
import serial
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


class ServerThread(threading.Thread):
    srv = None

    def __init__(self, Port_COMM):
        threading.Thread.__init__(self)

        # The shutdown_flag is a threading.Event object that
        # indicates whether the thread should be terminated.
        self.shutdown_flag = threading.Event()
        self.stop_request  = False
        self.Port_COMM = Port_COMM

    def run(self):
        Console.print('Server Thread #%i started' % self.ident)

        while not self.shutdown_flag.is_set():
            success = False
            # while self.create_socket() is False:
            for n in range(SO_RETRY_LIMIT):
                success = self.create_socket()
                if success is True:
                    break
                else:
                    if self.shutdown_flag.is_set() is True:
                        break
                    time.sleep(1)

            if success is False:
                if self.shutdown_flag.is_set() is True:
                    Console.print("Connection aborted.")
                else:
                    Console.print("Bind failed for %i times. Resetting socket." % SO_RETRY_LIMIT)
                    self.shutdown_flag.set()
                self.close_srv()
            else:
                # result, out_data = self.open_tcp_to_udp_link()
                # if result is False:
                #     Console.print("Can't open SoCat for ports", str(out_data))
                # else:
                #     Console.print("SoCat links open:", str(out_data))

                self.listen_socket()

        # ... Clean shutdown code here ...
        # Kill all processes that block necessary ports
        # also replace "execute_cmd('killall socat')"
        for port in range(self.Port_COMM, self.Port_COMM + 5):
            exe_cmd = 'lsof -F u -i :%i | head -1 | cut -c2-' % port
            pid, err = execute_cmd(exe_cmd)
            while pid != "":
                Console.print('killing port blocker [%s] for ' % pid, port)
                execute_cmd('kill %s' % pid)
                time.sleep(1)
                pid, err = execute_cmd(exe_cmd)

        Console.print('Server Thread #%s stopped' % self.ident)

    # def open_tcp_to_udp_link(self):
    #     res = True
    #     ports = list()
    #     pids  = list()
    #     for port in (Port_CAM0, Port_MIC0, Port_SPK0):
    #         cmd = 'socat tcp4-listen:' + str(port) + ',reuseaddr,fork udp:localhost:' + str(port) + ' &'
    #         out, err = execute_cmd(cmd)
    #         if str(out).isdigit():
    #             pids.append(out)
    #         else:
    #             ports.append(port)
    #             res = False
    #
    #     if res is True:
    #         return res, pids
    #     else:
    #         return res, ports

    def listen_socket(self):
        self.srv.listen(5)
        Console.print('Socket now listening on', HOST + "[%i]" % self.Port_COMM)

        conn = addr = None
        try:
            conn, addr = self.srv.accept()
        except OSError:
            Console.print("User break")

        if conn is None:
            Console.print("No connection interrupted.")
        else:
            client_IP = addr[0]
            Console.print('Connected with', client_IP + ':%i' % addr[1])
            # Sending message to connected client
            data = self.get_bytes_from_client(conn, CLIMSGLEN)
            if len(data) == 9:
                Console.print("Message Validation... ")
                Protocol = None
                if int(data[1]) == 48:
                    Protocol = TCP
                elif int(data[1]) == 49:
                    Protocol = UDP

                if Protocol is not None:
                    Video_Codec         = int(data[2]) - 48
                    SRV_vars.TestMode   = int(data[3]) - 48  # Substract 48 ASCII to decode the mode
                    ConnIP              =  data[4].__str__() + "."
                    ConnIP              += data[5].__str__() + "."
                    ConnIP              += data[6].__str__() + "."
                    ConnIP              += data[7].__str__()
                    Console.print("Client:", client_IP + "[%s]" % PROTO_NAME[Protocol])
                    Console.print("Video Codec is " + VideoCodec[Video_Codec])

                    conn = self.connection_loop(conn, client_IP, Protocol, Video_Codec)

                    # STOP THE ROBOT!
                    SRV_vars.DRV_A1_request = chr(50) + chr(50) + chr(0) + chr(0) + chr(0)
                else:
                    Console.print("Invalid message detected! Breaking connection.")

                if conn:
                    # came out of loop
                    conn.close()
                    self.close_srv()

                    Console.print("Connection with %s closed." % str(addr))
            else:
                Console.print("Incomplete message received! Breaking connection.")

    def connection_loop(self, conn, client_IP, Protocol, Video_Codec):
        noData_cnt = 0
        resolution = 0
        SRV_vars.heartbeat = HB_VALUE

        Cam0, MicIn, SpkOut, Port_COMM = load_setup()

        Stream_Thread = StreamThread(client_IP, Protocol, Video_Codec, Cam0, MicIn, SpkOut, Port_COMM)
        Stream_Thread.start()

        # now keep talking with the client
        while not self.shutdown_flag.is_set():
            # Receiving from client
            data = self.get_bytes_from_client(conn, CLIMSGLEN)
            try:
                data_len = len(data)
            except TypeError:
                data_len = False

            if data_len != CLIMSGLEN:
                noData_cnt += 1
                if noData_cnt > RETRY_LIMIT:
                    Console.print("NO DATA - closing connection [len = %i]" % data_len)
                    break
            else:
                noData_cnt = 0

                Fxmode, Fxvalue = self.decode_data(data)

                if Fxmode == 0:
                    resolution = Fxvalue
                elif Fxmode < 30:
                    if Fxmode < 4:
                        Fxvalue -= 100
                    Console.print(" Entering FX mode %s, value" % FxModes[Fxmode - 1], Fxvalue)
# ToDo:
#                     call('v4l2-ctl -d %s -c ' % device + FxModes[Fxmode - 1] + '=' + Fxvalue.__str__(), shell=True)

                    arg =  FxModes[Fxmode - 1] + '=' + Fxvalue.__str__()
                    retmsg, err = execute_cmd('v4l2-ctl -c %s' % arg)
                    if err:
                        Console.print(err)
                    # call('v4l2-ctl -c %s' % arg, shell=True)

                elif Fxmode < 35:
                    cmd = None
                    if Fxmode == 30:
                        Console.print(" Executing command", Fxvalue)
                        # 0    Exit Server
                        # 250  Exit Server & reboot RPI
                        # 251  Restart Server
                        # 252  Restart Server and USB ports
                        self.stop_request = Fxvalue
                        if Fxvalue >= 250:
                            cmd = ExeCmd.cmd[Fxvalue - 250]
                    elif Fxmode == 31:
                        Console.print(" Setting Mic Level to", Fxvalue)
                        cmd = "pactl set-source-volume " + MicIn + " " + str(Fxvalue * 7000)
                    elif Fxmode == 32:
                        Console.print(" Setting Speker volume to", Fxvalue)
                        cmd = "pactl set-sink-volume " + SpkOut + " " + str(Fxvalue * 7000)
                    else:
                        Console.print(" WARNING: Invalid mode [%s]" % Fxmode)

                    if cmd:
                        retmsg, err = execute_cmd(cmd)
                        if retmsg:
                            Console.print(retmsg)

                response = self.encode_data(data, Stream_Thread.streaming_mode)

                if Stream_Thread.res_queue.empty():
                    Stream_Thread.req_resolution = resolution

                if Debug > 0:
                    print("Chksum", response[0].__str__())
                    if Debug > 2:
                        print("DATA_OUT>>", response.__str__(), len(response))
                        print("DATA_IN>>", data.__str__(), len(data))
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
                except UnicodeEncodeError:
                    print(response)
                    print("temp", ConnectionData.coreTemp)
                    print("curr", ConnectionData.current)
                    print("volt", ConnectionData.voltage)

                    break

                SRV_vars.heartbeat = HB_VALUE

        Stream_Thread.shutdown_flag.set()

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
        SRV_vars.DRV_A1_request = data[1:6].decode(Encoding)

        SRV_vars.CTRL1_Mask = data[5]
        # Force 8bit format to extract switches
        CTRL1_Mask   = format(SRV_vars.CTRL1_Mask + 256, 'b')
        ConnectionData.light     = bool(int(CTRL1_Mask[7]))
        ConnectionData.speakers  = bool(int(CTRL1_Mask[6]))
        ConnectionData.mic       = bool(int(CTRL1_Mask[5]))
        ConnectionData.display   = bool(int(CTRL1_Mask[4]))
        ConnectionData.laser     = bool(int(CTRL1_Mask[3]))
        ConnectionData.AutoMode  = bool(int(CTRL1_Mask[2]))
        # COMM_vars.          = bool(int(CTRL1_Mask[1]))
        # COMM_vars.          = bool(int(CTRL1_Mask[0]))

        FXmode              = data[6]
        FXvalue             = data[7] * 256 + data[8]
        if FXmode == 11:
            FXvalue *= 1000

        Bitratemask  = str(int(data[9]) + 1000)
        ConnectionData.Abitrate  = int(Bitratemask[1])
        ConnectionData.Vbitrate  = int(Bitratemask[2])
        ConnectionData.Framerate = int(Bitratemask[3])

        return FXmode, FXvalue

    @staticmethod
    def encode_data(data, streaming_mode):
        retstr = chr(calc_checksum(data))               # 1
        retstr += str(SRV_vars.DRV_A1_response[1:11])   # 2,3,4,5,6,7,8,9,10,11
        retstr += chr(data[5])  # CntrlMask1            # 12
        retstr += chr(streaming_mode)                   # 13
        retstr += chr(255)                              # 14
        retstr += chr(ConnectionData.coreTemp)          # 15
        retstr += chr(255)                              # 16

        return retstr  # .ljust(RECMSGLEN, chr(255))

    def create_socket(self):
        # Create Socket
        self.srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        Console.print('Socket created')
        srv_address = (HOST, self.Port_COMM)
        try:
            self.srv.bind(srv_address)

        except socket.error as msg:
            Console.print('Bind failed. Error Code: %s' % msg)
            return False

        except OSError as msg:
            Console.print('Bind failed. Error Code: %i, Message' % msg[0], msg[1])
            Console.print('Advice: check for python process to kill it!')
            return False

        # Start listening on socket
        Console.print('Socket bind complete')
        return True

    def close_srv(self):
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

            ServerThread.srv = None
            time.sleep(.5)


class StreamThread(threading.Thread):
    req_resolution = 0
    streaming_mode = 0
    Source_test = 0
    Source_h264 = 1

    def __init__(self, client_IP, Protocol, Video_Codec, Cam0, MicIn, SpkOut, Port_COMM):

        Port_CAM0 = Port_COMM + 1
        Port_MIC0 = Port_COMM + 2
        Port_DSP0 = Port_COMM + 4
        Port_SPK0 = Port_COMM + 5

        threading.Thread.__init__(self)
        self.shutdown_flag = threading.Event()

        self.res_queue = queue.Queue()

        self.Video_Codec = Video_Codec

        # Define pipelines:
        self.player_video            =  Gst.Pipeline.new("player_video")
        self.sender_video            = [Gst.Pipeline.new("sender_video_test"),
                                        Gst.Pipeline.new("sender_video")]
        self.player_audio            = [Gst.Pipeline.new("player_audio_test"),
                                        Gst.Pipeline.new("player_audio")]
        self.sender_audio            = [Gst.Pipeline.new("sender_audio_test"),
                                        Gst.Pipeline.new("sender_audio")]
        # Define elements:
        # pulsesrc device=2 ! audio/x-raw,rate=32000 ! audioresample ! speexenc ! audioresample ! speexenc !
        #          rtpspeexpay ! udpsink host=x.x.x.x port=xxxx sync=false
        # glimagesink(default)/gtksink/cacasink/autovideosink/ximagesink(working)
        # caps = Gst.Caps.from_string("audio/x-raw, rate=32000")
        # self.capsfilter_audio[self.Source_h264].set_property("caps", caps)
        # self.capsfilter_audio[self.Source_test].set_property("caps", caps)
        # self.player_video_flip       = Gst.ElementFactory.make("videoflip", "flip")
        self.player_video_capsfilter = Gst.ElementFactory.make("capsfilter", "capsfilter")
        # self.player_video_gdpdepay   = Gst.ElementFactory.make("gdpdepay", "depayloader")
        self.player_video_rtphdepay  = Gst.ElementFactory.make("rtph264depay", "rtimer")
        self.player_video_queue      = Gst.ElementFactory.make("queue", "queue")
        self.player_video_decoder    = Gst.ElementFactory.make("avdec_h264", "avdec")
        self.player_video_convert    = Gst.ElementFactory.make("videoconvert")
        # self.player_video_videorate  = Gst.ElementFactory.make("videorate")
        # self.player_video_fpsadjcaps = Gst.ElementFactory.make("capsfilter", "fpsadj")
        # self.player_video_sink       = Gst.ElementFactory.make("ximagesink", "sink")
        # self.player_video_sink       = Gst.ElementFactory.make("gtksink", "sink")
        self.player_video_sink       = Gst.ElementFactory.make("ximagesink", "player_video_sink")

        self.sender_video_capsfilter = [Gst.ElementFactory.make("capsfilter", "capsfilter_test"),
                                        Gst.ElementFactory.make("capsfilter", "capsfilter")]
        self.sender_video_source     = [Gst.ElementFactory.make("videotestsrc", "video-source_test"),
                                        Gst.ElementFactory.make("v4l2src", "video-source")]
        self.sender_video_rtimer     = [Gst.ElementFactory.make("rtph264pay", "rtimer_test_udp"),
                                        Gst.ElementFactory.make("rtph264pay", "rtimer_udp")]
        self.player_audio_capsfilter = [Gst.ElementFactory.make("capsfilter", "capsfilter_audio_test"),
                                        Gst.ElementFactory.make("capsfilter", "capsfilter_audio")]
        self.player_audio_depayloader= [Gst.ElementFactory.make("rtpspeexdepay", "depayloader_audio_test"),
                                        Gst.ElementFactory.make("rtpspeexdepay", "depayloader_audio")]
        self.player_audio_decoder    = [Gst.ElementFactory.make("speexdec", "decoder_audio_test"),
                                        Gst.ElementFactory.make("speexdec", "decoder_audio")]
        self.player_audio_sink       = [Gst.ElementFactory.make("pulsesink", "sink_audio_test"),
                                        Gst.ElementFactory.make("pulsesink", "sink_audio")]
        self.sender_audio_source     = [Gst.ElementFactory.make("audiotestsrc", "audio-source_test"),
                                        Gst.ElementFactory.make("pulsesrc", "audio-source")]
        self.sender_audio_capsfilter = [Gst.ElementFactory.make("capsfilter", "capsfilter_audio_test"),
                                        Gst.ElementFactory.make("capsfilter", "capsfilter_audio")]
        self.sender_audio_resample   = [Gst.ElementFactory.make("audioresample", "resample_audio_test"),
                                        Gst.ElementFactory.make("audioresample", "resample_audio")]
        self.sender_audio_encoder    = [Gst.ElementFactory.make("speexenc", "encoder_audio_test"),
                                        Gst.ElementFactory.make("speexenc", "encoder_audio")]
        self.sender_audio_rtimer     = [Gst.ElementFactory.make("rtpspeexpay", "rtimer_audio_test"),
                                        Gst.ElementFactory.make("rtpspeexpay", "rtimer_audio")]
        if Protocol == TCP:
            self.player_video_source  =  Gst.ElementFactory.make("tcpclientsrc", "remote_source_video")
            self.sender_video_encoder = [Gst.ElementFactory.make("gdppay", "encoder_test"),
                                         Gst.ElementFactory.make("gdppay", "encoder")]
            self.sender_video_sink    = [Gst.ElementFactory.make("tcpserversink", "video-output_test"),
                                         Gst.ElementFactory.make("tcpserversink", "video-output")]
            self.player_audio_source  = [Gst.ElementFactory.make("tcpclientsrc", "source_audio_test"),
                                         Gst.ElementFactory.make("tcpclientsrc", "source_audio")]
            self.sender_audio_sink    = [Gst.ElementFactory.make("tcpserversink", "sink_audio_test"),
                                         Gst.ElementFactory.make("tcpserversink", "sink_audio")]
        else:
            self.player_video_source  =  Gst.ElementFactory.make("udpsrc", "remote_source_video_udp")
            self.sender_audio_sink    = [Gst.ElementFactory.make("udpsink", "sink_audio_test"),
                                         Gst.ElementFactory.make("udpsink", "sink_audio")]
            self.player_audio_source  = [Gst.ElementFactory.make("udpsrc", "source_audio_test_udp"),
                                         Gst.ElementFactory.make("udpsrc", "source_audio_udp")]
            self.sender_video_encoder = [Gst.ElementFactory.make(H264_ENC, "encoder_test_udp"),
                                         Gst.ElementFactory.make("h264parse", "encoder_udp")]
            self.sender_video_sink    = [Gst.ElementFactory.make("udpsink", "video-output_test"),
                                         Gst.ElementFactory.make("udpsink", "video-output")]

        # Set element properties
        self.player_video_source.set_property("port", Port_DSP0)
        caps = Gst.Caps.from_string("application/x-rtp, encoding-name=H264, payload=96")
        self.player_video_capsfilter.set_property("caps", caps)
        self.player_video_sink.set_property("sync", False)

        self.sender_video_sink[SRV_vars.TestMode].set_property("port", Port_CAM0)
        self.sender_video_sink[SRV_vars.TestMode].set_property("sync", False)
        self.sender_video_source[self.Source_test].set_property("pattern", "smpte")
        self.sender_video_rtimer[self.Source_h264].set_property("config_interval", 1)
        self.sender_video_rtimer[self.Source_h264].set_property("pt", 96)
        self.player_audio_source[SRV_vars.TestMode].set_property("port", Port_SPK0)
        self.player_audio_sink[SRV_vars.TestMode].set_property("device", SpkOut)
        self.sender_audio_source[self.Source_test].set_property("wave", 0)
        self.sender_audio_source[self.Source_h264].set_property("device", MicIn)
        self.sender_audio_sink[SRV_vars.TestMode].set_property("host", client_IP)
        self.sender_audio_sink[SRV_vars.TestMode].set_property("sync", False)
        self.sender_audio_sink[SRV_vars.TestMode].set_property("port", Port_MIC0)
        # set initial caps
        caps = Gst.Caps.from_string("application/x-rtp, media=audio, clock-rate=32000, encoding-name=SPEEX, payload=96")
        self.player_audio_capsfilter[self.Source_test].set_property("caps", caps)
        self.player_audio_capsfilter[self.Source_h264].set_property("caps", caps)

        self.player_audio_sink[self.Source_test].set_property("sync", True)
        self.player_audio_sink[self.Source_h264].set_property("sync", True)

        if Protocol == TCP:
            if HOST:
                self.player_video_source.set_property("host", HOST)
                self.sender_video_sink[self.Source_test].set_property("host", HOST)
                self.sender_video_sink[self.Source_h264].set_property("host", HOST)
            else:
                self.player_video_source.set_property("host", "0.0.0.0")
                self.sender_video_sink[self.Source_test].set_property("host", "0.0.0.0")
                self.sender_video_sink[self.Source_h264].set_property("host", "0.0.0.0")
            self.gst_init_video_test_tcp()
            self.gst_init_cam_tcp()
        else:
            self.sender_video_encoder[self.Source_test].set_property("tune", "zerolatency")
            self.sender_video_encoder[self.Source_test].set_property("pass", "qual")
            self.sender_video_encoder[self.Source_test].set_property("bitrate", 512)
            self.sender_video_encoder[self.Source_test].set_property("byte-stream", True)
            self.sender_video_sink[self.Source_test].set_property("host", client_IP)
            self.sender_video_sink[self.Source_h264].set_property("host", client_IP)
            self.gst_init_video_test_udp()
            self.gst_init_cam_udp()
            self.gst_init_disp_udp()

        self.gst_init_audio_udp()

    def gst_init_video_test_tcp(self):
        ####################################################################
        ### Build test video pipelineas following:
        ###   Source[cam] > Caps > Encoder > Sink[tcp]
        ####################################################################
        self.sender_video[self.Source_test].add(self.sender_video_source[self.Source_test])
        self.sender_video[self.Source_test].add(self.sender_video_capsfilter[self.Source_test])
        self.sender_video[self.Source_test].add(self.sender_video_encoder[self.Source_test])
        self.sender_video[self.Source_test].add(self.sender_video_sink[self.Source_test])

        self.sender_video_source[self.Source_test].link(self.sender_video_capsfilter[self.Source_test])
        self.sender_video_capsfilter[self.Source_test].link(self.sender_video_encoder[self.Source_test])
        self.sender_video_encoder[self.Source_test].link(self.sender_video_sink[self.Source_test])

    def gst_init_video_test_udp(self):
        ####################################################################
        ### Build test video pipelineas following:
        ###   Source[cam] > Caps > Encoder > RtPay > Sink[tcp]
        ####################################################################
        self.sender_video[self.Source_test].add(self.sender_video_source[self.Source_test])
        self.sender_video[self.Source_test].add(self.sender_video_capsfilter[self.Source_test])
        self.sender_video[self.Source_test].add(self.sender_video_encoder[self.Source_test])
        self.sender_video[self.Source_test].add(self.sender_video_rtimer[self.Source_test])
        self.sender_video[self.Source_test].add(self.sender_video_sink[self.Source_test])

        self.sender_video_source[self.Source_test].link(self.sender_video_capsfilter[self.Source_test])
        self.sender_video_capsfilter[self.Source_test].link(self.sender_video_encoder[self.Source_test])
        self.sender_video_encoder[self.Source_test].link(self.sender_video_rtimer[self.Source_test])
        self.sender_video_rtimer[self.Source_test].link(self.sender_video_sink[self.Source_test])

    def gst_init_cam_tcp(self):
        ####################################################################
        ### Build video pipelineas following:
        ###   Source[cam] > Caps > Parser > Codec_Opt > Encoder > Sink[tcp]
        ####################################################################
        parser = Gst.ElementFactory.make("h264parse", "parser")
        self.sender_video[self.Source_h264].add(self.sender_video_source[self.Source_h264])
        self.sender_video[self.Source_h264].add(self.sender_video_capsfilter[self.Source_h264])
        self.sender_video[self.Source_h264].add(parser)
        self.sender_video[self.Source_h264].add(self.sender_video_rtimer[self.Source_h264])
        self.sender_video[self.Source_h264].add(self.sender_video_encoder[self.Source_h264])
        self.sender_video[self.Source_h264].add(self.sender_video_sink[self.Source_h264])

        self.sender_video_source[self.Source_h264].link(self.sender_video_capsfilter[self.Source_h264])
        self.sender_video_capsfilter[self.Source_h264].link(parser)
        parser.link(self.sender_video_rtimer[self.Source_h264])
        self.sender_video_rtimer[self.Source_h264].link(self.sender_video_encoder[self.Source_h264])
        self.sender_video_encoder[self.Source_h264].link(self.sender_video_sink[self.Source_h264])

    def gst_init_cam_udp(self):
        ####################################################################
        ### Build video pipeline as following:
        ###   Source[cam] > Caps > Encoder > RtPay > Sink[udp]
        ####################################################################
        self.sender_video[self.Source_h264].add(self.sender_video_source[self.Source_h264])
        self.sender_video[self.Source_h264].add(self.sender_video_capsfilter[self.Source_h264])
        self.sender_video[self.Source_h264].add(self.sender_video_encoder[self.Source_h264])
        self.sender_video[self.Source_h264].add(self.sender_video_rtimer[self.Source_h264])
        self.sender_video[self.Source_h264].add(self.sender_video_sink[self.Source_h264])

        self.sender_video_source[self.Source_h264].link(self.sender_video_capsfilter[self.Source_h264])
        self.sender_video_capsfilter[self.Source_h264].link(self.sender_video_encoder[self.Source_h264])
        self.sender_video_encoder[self.Source_h264].link(self.sender_video_rtimer[self.Source_h264])
        self.sender_video_rtimer[self.Source_h264].link(self.sender_video_sink[self.Source_h264])

    def gst_init_disp_udp(self):
        ####################################################################
        ### Build video pipeline as following:
        ###   Source[UDP] > Caps > RtDepay > Queue > Decoder > Convert > Sink[ximage]
        ####################################################################
        self.player_video.add(self.player_video_source)
        self.player_video.add(self.player_video_capsfilter)
        self.player_video.add(self.player_video_rtphdepay)
        self.player_video.add(self.player_video_queue)
        self.player_video.add(self.player_video_decoder)
        self.player_video.add(self.player_video_convert)
        # self.player_video.add(self.player_video_flip)
        # self.player_video.add(self.player_video_videorate)
        # self.player_video.add(self.player_video_fpsadjcaps)
        self.player_video.add(self.player_video_sink)

        self.player_video_source.link(self.player_video_capsfilter)
        self.player_video_capsfilter.link(self.player_video_rtphdepay)
        self.player_video_rtphdepay.link(self.player_video_queue)
        self.player_video_queue.link(self.player_video_decoder)
        self.player_video_decoder.link(self.player_video_convert)
        # self.player_video_convert.link(self.player_video_flip)
        # self.player_video_convert.link(self.player_video_videorate)
        # self.player_video_videorate.link(self.player_video_fpsadjcaps)
        self.player_video_convert.link(self.player_video_sink)

    def gst_init_audio_udp(self):
        # SENDER
        self.sender_audio[self.Source_h264].add(self.sender_audio_source[self.Source_h264])
        self.sender_audio[self.Source_h264].add(self.sender_audio_capsfilter[self.Source_h264])
        self.sender_audio[self.Source_h264].add(self.sender_audio_resample[self.Source_h264])
        self.sender_audio[self.Source_h264].add(self.sender_audio_encoder[self.Source_h264])
        self.sender_audio[self.Source_h264].add(self.sender_audio_rtimer[self.Source_h264])
        self.sender_audio[self.Source_h264].add(self.sender_audio_sink[self.Source_h264])

        self.sender_audio_source[self.Source_h264].link(self.sender_audio_capsfilter[self.Source_h264])
        self.sender_audio_capsfilter[self.Source_h264].link(self.sender_audio_resample[self.Source_h264])
        self.sender_audio_resample[self.Source_h264].link(self.sender_audio_encoder[self.Source_h264])
        self.sender_audio_encoder[self.Source_h264].link(self.sender_audio_rtimer[self.Source_h264])
        self.sender_audio_rtimer[self.Source_h264].link(self.sender_audio_sink[self.Source_h264])

        # PLAYER
        self.player_audio[self.Source_h264].add(self.player_audio_source[self.Source_h264])
        self.player_audio[self.Source_h264].add(self.player_audio_capsfilter[self.Source_h264])
        self.player_audio[self.Source_h264].add(self.player_audio_depayloader[self.Source_h264])
        self.player_audio[self.Source_h264].add(self.player_audio_decoder[self.Source_h264])
        self.player_audio[self.Source_h264].add(self.player_audio_sink[self.Source_h264])

        self.player_audio_source[self.Source_h264].link(self.player_audio_capsfilter[self.Source_h264])
        self.player_audio_capsfilter[self.Source_h264].link(self.player_audio_depayloader[self.Source_h264])
        self.player_audio_depayloader[self.Source_h264].link(self.player_audio_decoder[self.Source_h264])
        self.player_audio_decoder[self.Source_h264].link(self.player_audio_sink[self.Source_h264])

    def run(self):
        Console.print('Streamer Thread #%s started' % self.ident)

        update          = False
        res_switch      = 9
        curr_resolution = 0
        curr_state      = None      # just to avoid error highlight

        req_audio_mode  = [Gst.State.READY, Gst.State.PLAYING]
        curr_mic0       = not ConnectionData.mic
        curr_speakers   = not ConnectionData.speakers
        curr_display    = not ConnectionData.display
        curr_AudioBitrate = None
        curr_Framerate  = None

        req_mode        = Gst.State.READY
        self.res_queue.put(req_mode)
        self.sender_audio[SRV_vars.TestMode].set_state(req_audio_mode[curr_mic0])
        self.player_audio[SRV_vars.TestMode].set_state(req_audio_mode[curr_speakers])

        while not self.shutdown_flag.is_set():
            if AudioBitrate[ConnectionData.Abitrate] != curr_AudioBitrate:
                curr_AudioBitrate = AudioBitrate[ConnectionData.Abitrate]
                self.sender_audio[SRV_vars.TestMode].set_state(Gst.State.READY)
                curr_mic0 = None

            if curr_mic0 is not ConnectionData.mic:
                curr_mic0 = ConnectionData.mic
                if ConnectionData.mic is True:
                    Console.print(" Mic0 on [rate %i]" % AudioBitrate[ConnectionData.Abitrate])
                    caps = Gst.Caps.from_string("audio/x-raw, rate=%i" % AudioBitrate[ConnectionData.Abitrate])
                    self.sender_audio_capsfilter[self.Source_h264].set_property("caps", caps)
                    self.sender_audio_capsfilter[self.Source_test].set_property("caps", caps)
                else:
                    Console.print(" Mic0 muted")

                self.sender_audio[SRV_vars.TestMode].set_state(req_audio_mode[ConnectionData.mic])

            if curr_speakers is not ConnectionData.speakers:
                curr_speakers = ConnectionData.speakers
                if ConnectionData.speakers is True:
                    Console.print(" Speakers on [rate %i]" % AudioBitrate[ConnectionData.Abitrate])
                else:
                    Console.print(" Speakers muted")

                self.player_audio[SRV_vars.TestMode].set_state(req_audio_mode[ConnectionData.speakers])

            if curr_display is not ConnectionData.display:
                fail = self.connect_camstream(ConnectionData.display)

                if fail is True:
                    Console.print(" Display Failed")
                else:
                    curr_display = ConnectionData.display
                    if curr_display is True:
                        Console.print(" Display On")
                    else:
                        Console.print(" Display Off")

            if curr_Framerate != ConnectionData.Framerate:
                curr_Framerate = ConnectionData.Framerate
                curr_resolution = None  # force cam reinitialization
                Console.print(" Setting fps to %s/s..." % VideoFramerate[ConnectionData.Framerate])

            if curr_resolution != self.req_resolution:
                if self.req_resolution > 0:
                    Console.print("Changing Gstreamer resolution")
                    ### CHANGE RESOLUTION/FPS CAPS ###
                    caps = "video/x-%s" % VideoCodec[self.Video_Codec] + capsstr[self.req_resolution] +\
                           VideoFramerate[ConnectionData.Framerate].__str__() + "/1"
                    caps = Gst.Caps.from_string(caps)
                    self.sender_video_capsfilter[SRV_vars.TestMode].set_property("caps", caps)

                    if self.Video_Codec > 0:
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
                curr_state = self.sender_video[SRV_vars.TestMode].get_state(1)[1]
                if curr_state == req_mode:
                    update = True
                    req_mode = self.res_queue.get()
                else:
                    res_switch += 1

                if req_mode != curr_state:
                    res_switch = bool(req_mode) * 10

            if res_switch == 10:
                res_switch = 0
                if req_mode == Gst.State.PAUSED:
                    Console.print("Pausing Gstreamer", end="...")
                    self.sender_video[SRV_vars.TestMode].set_state(req_mode)
                elif req_mode == Gst.State.READY:
                    Console.print("Preparing Gstreamer", end="...")
                    self.sender_video[SRV_vars.TestMode].set_state(req_mode)
                    # set HW framerate of the camera
                    cmd = "v4l2-ctl -p %s" % VideoFramerate[ConnectionData.Framerate]
                    retmsg, err = execute_cmd(cmd)
                    if err:
                        Console.print(err)
                elif req_mode == Gst.State.PLAYING:
                    Console.print("Requested streaming in mode " + self.req_resolution.__str__() + "/" +
                                  VideoFramerate[ConnectionData.Framerate].__str__() + "... ")
                    self.sender_video[SRV_vars.TestMode].set_state(req_mode)
                else:
                    Console.print('ERROR: resolution' + self.req_resolution.__str__() + ", mode " + req_mode)
                    res_switch = 10

            if update is True:
                update = False
                if curr_state == Gst.State.PAUSED:
                    Console.print("Paused.")
                elif curr_state == Gst.State.READY:
                    Console.print("Ready.")
                elif curr_state == Gst.State.PLAYING:
                    Console.print("Streaming in mode " + self.req_resolution.__str__())
                    self.streaming_mode = self.req_resolution

            time.sleep(.25)

        if curr_resolution > 3:
            Console.print("Switching to low resolution...")
            caps = Gst.Caps.from_string("video/x-%s" % VideoCodec[self.Video_Codec] + capsstr[1])
            self.sender_video_capsfilter[SRV_vars.TestMode].set_property("caps", caps)
            self.sender_video[SRV_vars.TestMode].set_state(Gst.State.READY)
            time.sleep(1)

        # self.sender_video[SRV_vars.TestMode].set_state(Gst.State.PAUSED)
        self.sender_video[SRV_vars.TestMode].set_state(Gst.State.READY)
        self.sender_audio[SRV_vars.TestMode].set_state(Gst.State.READY)
        self.player_audio[SRV_vars.TestMode].set_state(Gst.State.READY)
        self.player_video.set_state(Gst.State.READY)
        time.sleep(0.25)
        self.sender_video[self.Source_test].set_state(Gst.State.NULL)
        self.sender_video[self.Source_h264].set_state(Gst.State.NULL)

        self.sender_audio[self.Source_test].set_state(Gst.State.NULL)
        self.sender_audio[self.Source_h264].set_state(Gst.State.NULL)

        self.player_audio[self.Source_test].set_state(Gst.State.NULL)
        self.player_audio[self.Source_h264].set_state(Gst.State.NULL)
        self.player_video.set_state(Gst.State.NULL)

        Console.print('Streamer Thread #%s stopped' % self.ident)

    def connect_camstream(self, Connect):
        if Connect is True:
            time.sleep(0.1)
            retmsg = self.player_video.set_state(Gst.State.PLAYING)
        else:
            retmsg = self.player_video.set_state(Gst.State.NULL)

        if retmsg == Gst.StateChangeReturn.FAILURE:
            return True
        else:
            return False


class DriverThread(threading.Thread):

    def __init__(self):
        threading.Thread.__init__(self)

        # The shutdown_flag is a threading.Event object that
        # indicates whether the thread should be terminated.
        self.shutdown_flag = threading.Event()

    def run(self):
        Console.print('AT328-1 Thread #%s started' % self.ident)

        if bool(SRV_vars.TestMode) is True:
            self._testrun()
        else:
            self._liverun()

        Console.print('AT328-1 Thread #%s stopped' % self.ident)

    def _liverun(self):
        SerPort1          = serial.Serial(SRV_vars.Serial_Port)
        SerPort1.port     = SRV_vars.Serial_Port
        SerPort1.baudrate = SRV_vars.Port_Baudrate
        SerPort1.bytesize = SRV_vars.Port_bytesize
        SerPort1.parity   = SRV_vars.Port_parity
        SerPort1.stopbits = SRV_vars.Port_stopbits
        SerPort1.timeout  = SRV_vars.Port_Timeout
        SerPort1.xonxoff  = SRV_vars.Port_XonXoff
        SerPort1.dsrdtr   = SRV_vars.Port_DsrDtr
        SerPort1.rtscts   = SRV_vars.Port_RtsCts
        SerPort1.flush()
        Console.print("Serial Port %s connected." % SRV_vars.Serial_Port)

        inStr = ""
        while True:
            inChar = SerPort1.read().decode(Encoding)
            inStr += inChar
            if inChar == chr(10):
                Console.print(inStr)
                break

        idx = 75        # Timer for reporting parameters
        HeartBeat       = HB_BITSHIFT
        while not self.shutdown_flag.is_set():
            # SerPort1.flushInput()

            NoOfBytes = self.write_serial_data(SerPort1, HeartBeat)

            if NoOfBytes == DRV_A1_MSGLEN_REQ:
                time.sleep(0.04)
                HeartBeat = self.read_serial_data(SerPort1)
                if HeartBeat is False:
                    continue
            else:
                Console.print(">>>Flush:", NoOfBytes)
                SerPort1.flushOutput()

            # TEMP - report every 3sec
            if idx == 75:
                self.read_CPU_temp()
                idx = 0
            else:
                idx += 1

            if SRV_vars.heartbeat > 0:
                SRV_vars.heartbeat -= 1

    @staticmethod
    def write_serial_data(SerPort1, HeartBeat):
        data = chr(255)  # 1
        data += SRV_vars.DRV_A1_request  # 2,3,4,5,6
        data += chr(HeartBeat + HB_BITSHIFT * bool(SRV_vars.heartbeat))  # 7
        data += chr(255)  # 8

        NoOfBytes = SerPort1.write(data.encode(Encoding))

        return NoOfBytes

    @staticmethod
    def read_serial_data(SerPort1):
        resp_data = SerPort1.read(DRV_A1_MSGLEN_RES)  # Wait and read data

        HeartBeat = False
        if len(resp_data) < DRV_A1_MSGLEN_RES:
            Console.print(">>>DATA TIMEOUT!", len(resp_data))
        else:
            # 1st and pre-last char must be 255 (255 + 255 = 510)
            if resp_data[0] + resp_data[DRV_A1_MSGLEN_RES - 1] == 510:
                SRV_vars.DRV_A1_response = resp_data.decode(Encoding)
                HeartBeat = resp_data[DRV_A1_MSGLEN_RES - 2]

                dataint = list()
                for idx in range(5, 9):
                    if resp_data[idx] == 252:
                        dataint.append(17)
                    elif resp_data[idx] == 253:
                        dataint.append(19)
                    else:
                        dataint.append(resp_data[idx])

                curr_sensor = 0.0048 * (dataint[0] * 250 + dataint[1])  # 6,7
                ConnectionData.current = (2.48 - curr_sensor) * 5
                ConnectionData.voltage = 0.0157 * (dataint[2] * 250 + dataint[3]) - 0.95  # 8,9
            else:
                if resp_data.decode(Encoding).split(":")[0] != "IVO-A1":
                    Console.print(">>>BAD CHKSUM", resp_data[0], resp_data[15])
                SerPort1.flushInput()

        return HeartBeat

    def _testrun(self):
        Console.print("Test Port Emulated")
        inc = 30 ; adx = 1
        idx = 30
        while not self.shutdown_flag.is_set():

            # CURRENT - report continuously
            inc += adx
            if inc > 250 or inc < 30:
                adx = -adx
            ConnectionData.current = inc / 50

            # Voltage - report continuously
            ConnectionData.voltage = 12

            # DistanceS1
            ConnectionData.distanceS1 = 150

            # Motor Power
            ConnectionData.motor_PWR = [60, 50]

            # Mmotor RPM
            ConnectionData.motor_RPM = [80, 80]

            # TEMP - report every 3sec
            if idx == 30:
                self.read_CPU_temp()
                idx = 0

            time.sleep(.1)
            idx += 1

    @staticmethod
    def read_CPU_temp():
        Tempstr, err = execute_cmd("LD_LIBRARY_PATH=/opt/vc/lib && /opt/vc/bin/vcgencmd measure_temp")
        Tempstr = re.findall(r"\d+", Tempstr)
        Temp = int(Tempstr[0]) * 10 + int(Tempstr[1])
        if Temp <= 1275:
            ConnectionData.coreTemp = int(Temp / 5)


# Function for handling connections. This will be used to create threads
class ThreadManager():
    def __init__(self, GUI, Port_COMM, LB_Voltage, LB_Current, SW_OnOff):
        # threading.Thread.__init__(self)
        # # The shutdown_flag is a threading.Event object that
        # # indicates whether the thread should be terminated.
        self.shutdown_flag = True

        signal.signal(signal.SIGTERM, self.ProgramExit)
        signal.signal(signal.SIGINT, self.ProgramExit)
        signal.signal(signal.SIGABRT, self.ProgramExit)

        self._GUI = GUI
        self.LbVoltage = LB_Voltage
        self.LbCurrent = LB_Current
        self.SwOnOff   = SW_OnOff
        self.Port_COMM = Port_COMM

        self.DispAvgVal = [0, 0]

        if GUI is False:
            SRV_vars.GUI_CONSOLE = False
        else:
            SRV_vars.GUI_CONSOLE = True

        self.Console = Console()
        Console.print("Console %s initialized\n" % VERSION)

        if SRV_vars.Serial_Port is None:
            Console.print("No Serial Port found!")
        else:
            self._init_DriverThread()

        self._init_ServerThread()

    def _init_ServerThread(self):
        self.Server_Thread = ServerThread(self.Port_COMM)

    def _init_DriverThread(self):
        self.Driver_Thread = DriverThread()

    def run(self):
        if self.shutdown_flag is False:
            if SRV_vars.Serial_Port is not None:
                if not self.Driver_Thread.is_alive():
                    try:
                        self.Driver_Thread.start()
                    except RuntimeError:
                        self._init_DriverThread()
                        self.Driver_Thread.start()

            if self.Server_Thread.is_alive():
                if self.Server_Thread.stop_request is not False:
                    self.shutdown_flag = True
                    self.ProgramExit(self.Server_Thread.stop_request)
            else:
                try:
                    self.Server_Thread.start()
                except RuntimeError:
                    self._init_ServerThread()
                    self.Server_Thread.start()

            self.DispAvgVal[0] = (self.DispAvgVal[0] * 4 + ConnectionData.voltage) / 5
            self.DispAvgVal[1] = (self.DispAvgVal[1] * 4 + ConnectionData.current) / 5
        else:
            self.DispAvgVal[0] = 0
            self.DispAvgVal[1] = 0
            if not(self.Server_Thread.shutdown_flag.is_set() and self.Server_Thread.shutdown_flag.is_set()):
                Console.print("shutting down services...")
                self._stop()

        self.Console.display_message(self._GUI)

        if self._GUI:
            self.LbVoltage.set_value(self.DispAvgVal[0])
            self.LbCurrent.set_value(self.DispAvgVal[1])
            Voltage = "{:.2f}".format(ConnectionData.voltage).__str__()
            Current = "{:.2f}".format(ConnectionData.current).__str__()
            self.LbVoltage.set_tooltip_text("%s V" % Voltage)
            self.LbCurrent.set_tooltip_text("%s A" % Current)

        return True

    def _stop(self):
        self.Server_Thread.shutdown_flag.set()

        if self.Server_Thread.srv is not None:
            self.Server_Thread.close_srv()

        if self.Server_Thread.is_alive():
            self.Server_Thread.join()

        if SRV_vars.Serial_Port is not None:
            self.Driver_Thread.shutdown_flag.set()
            if self.Driver_Thread.is_alive():
                self.Driver_Thread.join()

        Console.print('Thread manager has stopped.')
        self.shutdown_flag = None
        self.Console.display_message(self._GUI)

    def ProgramExit(self, *args):
        if args:
            ExitCode = args[0]
        else:
            ExitCode = 0

        Console.print("Exit requested! [%i]" % ExitCode)
        self.Console.display_message(self._GUI)
        self._stop()

        if ExitCode != 249:
            time.sleep(1)
            exit(ExitCode)


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


class ServiceExit(Exception):
    """
    Custom exception which is used to trigger the clean exit
    of all running threads and the main program.
    """
#    pass


def load_setup():
    dev, err = execute_cmd("cat %s |grep CAM0|cut -d' ' -f2" % Paths.ini_file)
    if dev.find(":") != -1:
        Cam0 = dev.split(":")[1]
    else:
        Cam0 = dev

    dev, err = execute_cmd("cat %s |grep MIC0|cut -d' ' -f2" % Paths.ini_file)
    if dev.find(":") != -1:
        MicIn = dev.split(":")[1]
    else:
        MicIn = dev

    dev, err = execute_cmd("cat %s |grep SPK0|cut -d' ' -f2" % Paths.ini_file)
    if dev.find(":") != -1:
        SpkOut = dev.split(":")[1]
    else:
        SpkOut = dev

    dev, err = execute_cmd("cat %s |grep PORT|cut -d' ' -f2" % Paths.ini_file)
    if dev.find(":") != -1:
        Port_COMM = dev.split(":")[1]
    else:
        Port_COMM = dev

    return Cam0, MicIn, SpkOut, int(Port_COMM)
