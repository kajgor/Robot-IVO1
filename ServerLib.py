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
    stop_request = False

    def __init__(self, Port):
        threading.Thread.__init__(self)

        # The shutdown_flag is a threading.Event object that
        # indicates whether the thread should be terminated.
        self.shutdown_flag = threading.Event()
        self.Port = Port

    def run(self):
        Console.print('Server Thread #%i started' % self.ident)

        while not self.shutdown_flag.is_set():
            for n in range(SO_RETRY_LIMIT):
                self.srv = self.create_socket(HOST, self.Port)
                if self.srv is not None:
                    break
                else:
                    if self.shutdown_flag.is_set() is True:
                        break
                    time.sleep(1)

            if self.srv is None:
                if self.shutdown_flag.is_set() is True:
                    Console.print("Connection aborted.")
                else:
                    Console.print("Bind failed for %i times. Resetting socket." % SO_RETRY_LIMIT)
                    self.shutdown_flag.set()
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
        for port in range(self.Port, self.Port + 5):
            exe_cmd = 'lsof -F u -i :%i | head -1 | cut -c2-' % port
            pid, err = execute_cmd(exe_cmd)
            while pid != "":
                Console.print('killing port blocker %i for port %i' % (pid, port))
                execute_cmd('kill -9 %s' % pid)
                time.sleep(.25)
                pid, err = execute_cmd(exe_cmd)

        Console.print('Server Thread #%s stopped' % self.ident)

    def listen_socket(self):
        self.srv.listen(5)
        Console.print('Socket now listening on %s:%i' % (HOST , self.Port))

        self.conn = addr = None
        try:
            self.conn, addr = self.srv.accept()
        except OSError:
            Console.print("User break")

        if self.conn is None:
            Console.print("No connection interrupted.")
        else:
            client_IP = addr[0]
            Console.print('Connected with %s on %i' % (client_IP, addr[1]))
            # Sending message to connected client
            data = self.get_bytes_from_client(CLIMSGLEN)
            if len(data) == 9:
                Console.print("Message Validation... ")
                if int(data[1]) == 48:
                    Protocol = TCP
                elif int(data[1]) == 49:
                    Protocol = UDP
                else:
                    Protocol = None

                if Protocol is not None:
                    ConnectionData.Protocol = Protocol
                    ConnectionData.Vcodec   = int(data[2]) - 48
                    SRV_vars.TestMode       = int(data[3]) - 48  # Substract 48 ASCII to decode the mode
                    ConnIP                  =  data[4].__str__() + "."
                    ConnIP                  += data[5].__str__() + "."
                    ConnIP                  += data[6].__str__() + "."
                    ConnIP                  += data[7].__str__()
                    Console.print("Client: %s/%s" % (client_IP, PROTO_NAME[Protocol]))
                    Console.print("Video Codec is %s " % VideoCodec[ConnectionData.Vcodec])

                    self.connection_loop(client_IP)

                    # STOP THE ROBOT!
                    SRV_vars.DRV_A1_request = chr(50) + chr(50) + chr(0) + chr(0) + chr(0)
                else:
                    Console.print("Invalid message detected! Breaking connection.")

                if self.conn:
                    # came out of loop
                    self.conn.close()
                    self.close_srv()

                    Console.print("Connection with %s closed." % str(addr))
            else:
                Console.print("Incomplete message received! Breaking connection.")

    def connection_loop(self, client_IP):
        noData_cnt = 0
        SRV_vars.heartbeat = HB_VALUE

        # Load connection parameters
        Cam0, MicIn, SpkOut, Port_COMM, PRG_CONN_BEGIN, PRG_CONN_END = load_setup()

        # Execute program after connection established
        if PRG_CONN_BEGIN:
            execute_cmd(PRG_CONN_BEGIN)

        # Initialize media streams
        Conn_param = client_IP, Port_COMM
        Media_Stream = MediaStream(Conn_param, Cam0, MicIn, SpkOut)

        # ...and now keep talking with the client
        while not self.shutdown_flag.is_set():
            # Receiving from client
            data = self.get_bytes_from_client(CLIMSGLEN)
            if data is not None:
                data_len = len(data)
            else:
            # except TypeError:
                data_len = False

            if data_len != CLIMSGLEN:
                noData_cnt += 1
                if noData_cnt > RETRY_LIMIT:
                    Console.print("BAD CLIMSGLEN - closing connection [len = %i]" % data_len)
                    self.shutdown_flag.set()
            else:
                noData_cnt = 0
                cmd = None

                Fxmode, Fxvalue = self.decode_data(data)

                if Fxmode == 0:  # Set resolution (0 - camera off)
                    ConnectionData.resolution = Fxvalue
                elif Fxmode < 30:
                    if Fxmode < 4:
                        Fxvalue -= 100
                    Console.print("_Entering FX mode %s, value %i" % (FxModes[Fxmode - 1], Fxvalue))
# ToDo:
#  call('v4l2-ctl -d %s -c ' % device + FxModes[Fxmode - 1] + '=' + Fxvalue.__str__(), shell=True)
                    arg = FxModes[Fxmode - 1] + '=' + Fxvalue.__str__()
                    cmd = 'v4l2-ctl -c %s' % arg
                    # call('v4l2-ctl -c %s' % arg, shell=True)

                elif Fxmode < 35:
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
                else:
                    # Nothing should happen here
                    pass

                Media_Stream.process_client_request()

                if cmd:
                    retmsg, err = execute_cmd(cmd)
                    if err:
                        Console.print(err)

                response = self.encode_data(data)

                if Debug > 0:
                    print("Chksum is %s" % response[0].__str__())
                    if Debug > 2:
                        print("DATA_OUT>>%s" % response.__str__(), len(response))
                        print("DATA_IN>>%s" % data.__str__(), len(data))
                try:
                    self.conn.sendall(response.encode(Encoding))
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

        # Execute program after connection finished/broken
        if PRG_CONN_END:
            execute_cmd(PRG_CONN_END)

        # Close media pipes
        Media_Stream.close_all()

    def get_bytes_from_client(self, count):
        try:
            data = self.conn.recv(count)
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
    def encode_data(data):
        retstr = chr(calc_checksum(data))               # 1
        retstr += str(SRV_vars.DRV_A1_response[1:11])   # 2,3,4,5,6,7,8,9,10,11
        retstr += chr(data[5])  # CntrlMask1            # 12
        retstr += chr(ConnectionData.StreamMode)        # 13
        retstr += chr(255)                              # 14
        retstr += chr(ConnectionData.coreTemp)          # 15
        retstr += chr(255)                              # 16

        return retstr  # .ljust(RECMSGLEN, chr(255))

    def create_socket(self, Host, Port):
        # Create Socket
        srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        Console.print('Socket created')
        srv_address = (Host, Port)
        try:
            srv.bind(srv_address)

        except socket.error as msg:
            Console.print('Bind failed. Error Code: %s' % msg)
            return None

        except OSError as msg:
            Console.print('Bind failed. Error Code: %i, Message' % msg[0], msg[1])
            Console.print('Advice: check for python process to kill it!')
            return None

        # Start listening on socket
        Console.print('Socket bind complete')
        return srv

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
class ThreadManager:
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


class MediaStream:
    curr_resolution   = None
    curr_AudioBitrate = None
    curr_mic0         = None
    curr_speakers     = None
    curr_display      = None
    last_pending      = Gst.State.READY
    sender_audio_mode = Gst.State.READY
    sender_video_mode = Gst.State.READY
    # curr_Framerate    = None

    def __init__(self, Conn_param, Cam0, MicIn, SpkOut):

        client_IP, Port_COMM = Conn_param
        self.delay_counter = 10

        Port_CAM0 = Port_COMM + 1
        Port_MIC0 = Port_COMM + 2
        Port_DSP0 = Port_COMM + 4
        Port_SPK0 = Port_COMM + 5

        self.video_sender_queue = queue.Queue()
        self.audio_sender_queue = queue.Queue()

        # Define pipelines:
        self.player_video   = Gst.Pipeline.new("player_video")
        self.player_audio   = Gst.Pipeline.new("player_audio")
        self.sender_video   = Gst.Pipeline.new("sender_video")
        self.sender_audio   = Gst.Pipeline.new("sender_audio")

        bus = self.sender_video.get_bus()
        bus.add_signal_watch()
        bus.enable_sync_message_emission()
        bus.connect("message", self.on_sender_message)

        # Define elements:
        # pulsesrc device=2 ! audio/x-raw,rate=32000 ! audioresample ! speexenc ! audioresample ! speexenc !
        #          rtpspeexpay ! udpsink host=x.x.x.x port=xxxx sync=false
        # glimagesink(default)/gtksink/cacasink/autovideosink/ximagesink(working)

        # PLAYER VIDEO
        self.player_video_capsfilter = Gst.ElementFactory.make("capsfilter", "capsfilter")
        self.player_video_rtphdepay  = Gst.ElementFactory.make("rtph264depay", "rtimer")
        self.player_video_queue      = Gst.ElementFactory.make("queue", "queue")
        self.player_video_decoder    = Gst.ElementFactory.make("avdec_h264", "avdec")
        self.player_video_convert    = Gst.ElementFactory.make("videoconvert")
        self.player_video_sink       = Gst.ElementFactory.make("ximagesink", "local_sink_video")

        if ConnectionData.Protocol == TCP:
            self.player_video_source  = Gst.ElementFactory.make("tcpclientsrc", "remote_source_video")
        else:
            self.player_video_source  = Gst.ElementFactory.make("udpsrc", "remote_source_video")

        # SENDER VIDEO
        if SRV_vars.TestMode == 0:
            self.sender_video_source = Gst.ElementFactory.make("videotestsrc", "local_source_video")
        else:
            self.sender_video_source = Gst.ElementFactory.make("v4l2src", "local_source_video")

        if ConnectionData.Protocol == TCP:
            self.sender_video_encoder = Gst.ElementFactory.make("gdppay", "encoder_video")
            self.sender_video_sink    = Gst.ElementFactory.make("tcpserversink", "sink_video")
        else:
            self.sender_video_encoder = Gst.ElementFactory.make("h264parse", "encoder_video")
            self.sender_video_sink    = Gst.ElementFactory.make("udpsink", "sink_video")

        self.sender_video_capsfilter = Gst.ElementFactory.make("capsfilter", "capsfilter_video")
        self.sender_video_rtimer     = Gst.ElementFactory.make("rtph264pay", "rtimer_video")

        # PLAYER AUDIO
        self.player_audio_capsfilter = Gst.ElementFactory.make("capsfilter", "capsfilter_audio")
        self.player_audio_depayloader = Gst.ElementFactory.make("rtpspeexdepay", "depayloader_audio")
        self.player_audio_decoder    = Gst.ElementFactory.make("speexdec", "decoder_audio")
        self.player_audio_sink       = Gst.ElementFactory.make("pulsesink", "local_sink_audio")

        if ConnectionData.Protocol == TCP:
            self.player_audio_source  = Gst.ElementFactory.make("tcpclientsrc", "source_audio")
        else:
            self.player_audio_source  = Gst.ElementFactory.make("udpsrc", "source_audio")

        # SENDER AUDIO
        self.sender_audio_capsfilter = Gst.ElementFactory.make("capsfilter", "capsfilter_audio")
        self.sender_audio_resample   = Gst.ElementFactory.make("audioresample", "resample_audio")
        self.sender_audio_encoder    = Gst.ElementFactory.make("speexenc", "encoder_audio")
        self.sender_audio_rtimer     = Gst.ElementFactory.make("rtpspeexpay", "rtimer_audio")

        if SRV_vars.TestMode == 0:
            self.sender_audio_source = Gst.ElementFactory.make("audiotestsrc", "local_source_audio")
        else:
            self.sender_audio_source = Gst.ElementFactory.make("pulsesrc", "local_source_audio")

        if ConnectionData.Protocol == TCP:
            self.sender_audio_sink    = Gst.ElementFactory.make("tcpserversink", "sink_audio")
        else:
            self.sender_audio_sink    = Gst.ElementFactory.make("udpsink", "sink_audio")

    # def set_properties(self):
        # Set element properties
        self.player_video_source.set_property("port", Port_DSP0)
        caps = Gst.Caps.from_string("application/x-rtp, encoding-name=H264, payload=96")
        self.player_video_capsfilter.set_property("caps", caps)
        self.player_video_sink.set_property("sync", False)

        self.sender_video_sink.set_property("port", Port_CAM0)
        self.sender_video_sink.set_property("sync", False)

        if SRV_vars.TestMode == 0:
            self.sender_video_source.set_property("pattern", "smpte")
        else:
            self.sender_video_source.set_property("device", Cam0)
            self.sender_video_rtimer.set_property("config_interval", 1)
            self.sender_video_rtimer.set_property("pt", 96)

        self.player_audio_source.set_property("port", Port_SPK0)
        self.player_audio_sink.set_property("device", SpkOut)

        if SRV_vars.TestMode == 0:
            self.sender_audio_source.set_property("wave", 0)
        else:
            self.sender_audio_source.set_property("device", MicIn)

        self.sender_audio_sink.set_property("host", client_IP)
        self.sender_audio_sink.set_property("sync", False)
        self.sender_audio_sink.set_property("port", Port_MIC0)

        # set initial caps
        caps = Gst.Caps.from_string("application/x-rtp, media=audio, clock-rate=16000, encoding-name=SPEEX, payload=96")
        self.player_audio_capsfilter.set_property("caps", caps)
        self.player_audio_sink.set_property("sync", True)

        if ConnectionData.Protocol == TCP:
            if HOST:
                self.player_video_source.set_property("host", HOST)
                self.sender_video_sink.set_property("host", HOST)
            else:
                self.player_video_source.set_property("host", "0.0.0.0")
                self.sender_video_sink.set_property("host", "0.0.0.0")

            if SRV_vars.TestMode == 0:
                self.gst_init_video_test_tcp()
            else:
                self.gst_init_cam_tcp()
        else:
            if SRV_vars.TestMode == 0:
                self.sender_video_encoder.set_property("tune", "zerolatency")
                self.sender_video_encoder.set_property("pass", "qual")
                self.sender_video_encoder.set_property("bitrate", 512)
                self.sender_video_encoder.set_property("byte-stream", True)
                self.sender_video_sink.set_property("host", client_IP)
                self.gst_init_video_test_udp()
            else:
                self.sender_video_sink.set_property("host", client_IP)
                self.gst_init_cam_udp()
                self.gst_init_disp_udp()
                self.gst_init_audio_udp()

    def gst_init_video_test_tcp(self):
        ####################################################################
        ### Build test video pipelineas following:
        ###   Source[cam] > Caps > Encoder > Sink[tcp]
        ####################################################################
        self.sender_video.add(self.sender_video_source)
        self.sender_video.add(self.sender_video_capsfilter)
        self.sender_video.add(self.sender_video_encoder)
        self.sender_video.add(self.sender_video_sink)

        self.sender_video_source.link(self.sender_video_capsfilter)
        self.sender_video_capsfilter.link(self.sender_video_encoder)
        self.sender_video_encoder.link(self.sender_video_sink)

    def gst_init_video_test_udp(self):
        ####################################################################
        ### Build test video pipelineas following:
        ###   Source[cam] > Caps > Encoder > RtPay > Sink[tcp]
        ####################################################################
        self.sender_video.add(self.sender_video_source)
        self.sender_video.add(self.sender_video_capsfilter)
        self.sender_video.add(self.sender_video_encoder)
        self.sender_video.add(self.sender_video_rtimer)
        self.sender_video.add(self.sender_video_sink)

        self.sender_video_source.link(self.sender_video_capsfilter)
        self.sender_video_capsfilter.link(self.sender_video_encoder)
        self.sender_video_encoder.link(self.sender_video_rtimer)
        self.sender_video_rtimer.link(self.sender_video_sink)

    def gst_init_cam_tcp(self):
        ####################################################################
        ### Build video pipelineas following:
        ###   Source[cam] > Caps > Parser > Codec_Opt > Encoder > Sink[tcp]
        ####################################################################
        parser = Gst.ElementFactory.make("h264parse", "parser")
        self.sender_video.add(self.sender_video_source)
        self.sender_video.add(self.sender_video_capsfilter)
        self.sender_video.add(parser)
        self.sender_video.add(self.sender_video_rtimer)
        self.sender_video.add(self.sender_video_encoder)
        self.sender_video.add(self.sender_video_sink)

        self.sender_video_source.link(self.sender_video_capsfilter)
        self.sender_video_capsfilter.link(parser)
        parser.link(self.sender_video_rtimer)
        self.sender_video_rtimer.link(self.sender_video_encoder)
        self.sender_video_encoder.link(self.sender_video_sink)

    def gst_init_cam_udp(self):
        ####################################################################
        ### Build video pipeline as following:
        ###   Source[cam] > Caps > Encoder > RtPay > Sink[udp]
        ####################################################################
        self.sender_video.add(self.sender_video_source)
        self.sender_video.add(self.sender_video_capsfilter)
        self.sender_video.add(self.sender_video_encoder)
        self.sender_video.add(self.sender_video_rtimer)
        self.sender_video.add(self.sender_video_sink)

        self.sender_video_source.link(self.sender_video_capsfilter)
        self.sender_video_capsfilter.link(self.sender_video_encoder)
        self.sender_video_encoder.link(self.sender_video_rtimer)
        self.sender_video_rtimer.link(self.sender_video_sink)

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
        self.sender_audio.add(self.sender_audio_source)
        self.sender_audio.add(self.sender_audio_capsfilter)
        self.sender_audio.add(self.sender_audio_resample)
        self.sender_audio.add(self.sender_audio_encoder)
        self.sender_audio.add(self.sender_audio_rtimer)
        self.sender_audio.add(self.sender_audio_sink)

        self.sender_audio_source.link(self.sender_audio_capsfilter)
        self.sender_audio_capsfilter.link(self.sender_audio_resample)
        self.sender_audio_resample.link(self.sender_audio_encoder)
        self.sender_audio_encoder.link(self.sender_audio_rtimer)
        self.sender_audio_rtimer.link(self.sender_audio_sink)

        # PLAYER
        self.player_audio.add(self.player_audio_source)
        self.player_audio.add(self.player_audio_capsfilter)
        self.player_audio.add(self.player_audio_depayloader)
        self.player_audio.add(self.player_audio_decoder)
        self.player_audio.add(self.player_audio_sink)

        self.player_audio_source.link(self.player_audio_capsfilter)
        self.player_audio_capsfilter.link(self.player_audio_depayloader)
        self.player_audio_depayloader.link(self.player_audio_decoder)
        self.player_audio_decoder.link(self.player_audio_sink)

    def on_sender_message(self, bus, message):
        msgtype = message.type
        if msgtype == Gst.MessageType.EOS:
            if Debug > 1:
                Console.print("EOS: SIGNAL LOST")
            return False

        elif msgtype == Gst.MessageType.STATE_CHANGED:
            old_state, curr_state, pending_state = message.parse_state_changed()
            # print("old_state/new_state/pending_state is %s/%s/%s" % (old_state, curr_state, pending_state))
            if pending_state == Gst.State.VOID_PENDING:
                next_queue_item = self.process_video_queue()
                if next_queue_item is not None:
                    self.sender_video_mode = next_queue_item
                    self.sender_video.set_state(next_queue_item)

            if curr_state == Gst.State.NULL == self.last_pending:
                Console.print("reset.")

            elif curr_state == Gst.State.PAUSED == self.last_pending:
                # SET the v4l2 framerate
                # self.set_v4l2_framerate(VideoFramerate[ConnectionData.Framerate])
                Console.print("paused.")

            elif curr_state == Gst.State.READY:
                if ConnectionData.resolution > 0:
                    if self.last_pending == curr_state:
                        ### SET RESOLUTION/FPS CAPS ###
                        caps = "video/x-%s, %s, framerate=%i/1, stream-format=byte-stream, tune=zerolatency" % \
                               (VideoCodec[ConnectionData.Vcodec], capsstr_resolution[ConnectionData.resolution],
                                VideoFramerate[ConnectionData.Framerate])
                        self.sender_video_capsfilter.set_property("caps", Gst.Caps.from_string(caps))
                        Console.print("stopped.")

            elif curr_state == Gst.State.PLAYING == self.last_pending:
                ConnectionData.StreamMode = ConnectionData.resolution
                Console.print("streaming [mode %i]." % ConnectionData.resolution)

            self.last_pending = pending_state

        elif msgtype == Gst.MessageType.BUFFERING:
            pass

        elif msgtype == Gst.MessageType.ERROR:
            err, debug = message.parse_error()
            debug_s = debug.split("\n")
            if Debug > 0:
                Console.print("ERROR:", debug_s)
            return False

        else:
            pass

        return True

    def set_client_camstream(self, Connect):
        if Connect is True:
            time.sleep(0.1)
            retmsg = self.player_video.set_state(Gst.State.PLAYING)
        else:
            retmsg = self.player_video.set_state(Gst.State.NULL)

        if retmsg == Gst.StateChangeReturn.FAILURE:
            return False
        else:
            return True

    def set_v4l2_framerate(self, Framerate):
        # set HW framerate of the camera
        cmd = "v4l2-ctl -p %s" % Framerate
        retmsg, err = execute_cmd(cmd)
        if err:
            Console.print(err)
            return False
        else:
            return True

    def process_client_request(self):
        req_audio_mode  = [Gst.State.READY, Gst.State.PLAYING]

        if self.curr_AudioBitrate != AudioBitrate[ConnectionData.Abitrate]:
            self.curr_AudioBitrate = AudioBitrate[ConnectionData.Abitrate]
            Console.print(" Audio bitrate set to %i" % AudioBitrate[ConnectionData.Abitrate])
            caps = "audio/x-raw, rate=%i" % AudioBitrate[ConnectionData.Abitrate]
            self.sender_audio_capsfilter.set_property("caps", Gst.Caps.from_string(caps))
            self.audio_sender_queue.put(Gst.State.READY)
            self.curr_mic0 = None

        if self.curr_mic0 is not ConnectionData.mic:
            self.curr_mic0 = ConnectionData.mic
            if ConnectionData.mic is True:
                Console.print(" Mic0 listening")
                self.audio_sender_queue.put(Gst.State.PLAYING)
            else:
                Console.print(" Mic0 muted")
                self.audio_sender_queue.put(Gst.State.READY)

        self.process_audio_queue()

        if self.curr_resolution != [ConnectionData.resolution, ConnectionData.Framerate]:
            self.curr_resolution = [ConnectionData.resolution, ConnectionData.Framerate]
            ConnectionData.StreamMode = 0
            if ConnectionData.resolution > 0:
                Console.print("Setting Gstreamer parameters")
                self.sender_video.set_state(Gst.State.READY)
                self.sender_video_mode = Gst.State.PLAYING
                self.video_sender_queue.put(self.sender_video_mode)
            else:
                self.sender_video_mode = Gst.State.NULL
                self.sender_video.set_state(self.sender_video_mode)

            self.video_sender_queue.put(None)  # finish the queue

        if self.curr_speakers is not ConnectionData.speakers:
            self.curr_speakers = ConnectionData.speakers
            if ConnectionData.speakers is True:
                Console.print(" Speakers on")
            else:
                Console.print(" Speakers muted")

            self.player_audio.set_state(req_audio_mode[ConnectionData.speakers])

        if self.curr_display is not ConnectionData.display:
            success = self.set_client_camstream(ConnectionData.display)
            if not success:
                Console.print(" Display Failed")
            else:
                self.curr_display = ConnectionData.display
                if self.curr_display is True:
                    Console.print(" Display On")
                else:
                    Console.print(" Display Off")

    def process_audio_queue(self):
        if not self.audio_sender_queue.empty():
            curr_state = self.sender_audio.get_state(1)[1]
            if curr_state == self.sender_audio_mode:
                self.sender_audio_mode = self.audio_sender_queue.get()
            self.sender_audio.set_state(self.sender_audio_mode)

    def process_video_queue(self):
        if not self.video_sender_queue.empty():
            next_queue_item = self.video_sender_queue.get()
        else:
            return None

        if next_queue_item == Gst.State.PAUSED:
            Console.print("Pausing Gstreamer", end="...")

        elif next_queue_item == Gst.State.NULL:
            Console.print("Stopping", end="...")

        elif next_queue_item == Gst.State.READY:
            Console.print("Preparing Gstreamer", end="...")

        elif next_queue_item == Gst.State.PLAYING:
            Console.print("Requested streaming in mode %i/%i..." % (ConnectionData.resolution,
                          VideoFramerate[ConnectionData.Framerate]))
        else:
            Console.print('ERROR: resolution %i/%i, mode %s' % (ConnectionData.resolution,
                                                                VideoFramerate[ConnectionData.Framerate],
                                                                self.sender_video_mode))
        return next_queue_item

    def close_all(self):
        ConnectionData.resolution = 0  # init camera to standby mode
        ConnectionData.StreamMode = 0  # to close streams nicely
        self.curr_resolution[0]   = 1  # Switching to low resolution

        Console.print("Stopping media streams", end="... ")

        if self.sender_video:
            self.sender_video.set_state(Gst.State.NULL)
        if self.sender_audio:
            self.sender_audio.set_state(Gst.State.NULL)
        if self.player_video:
            self.player_video.set_state(Gst.State.NULL)
        if self.player_audio:
            self.player_audio.set_state(Gst.State.NULL)

        time.sleep(0.25)
        Console.print('media stopped.')


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

    PRG_CONN_BEGIN, err = execute_cmd("cat %s |grep PRG_CONN_BEGIN|cut -d' ' -f2-" % Paths.ini_file)

    PRG_CONN_END, err = execute_cmd("cat %s |grep PRG_CONN_END|cut -d' ' -f2-" % Paths.ini_file)

    return Cam0, MicIn, SpkOut, int(Port_COMM), PRG_CONN_BEGIN, PRG_CONN_END
