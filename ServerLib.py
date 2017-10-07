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
            Console.print('Connected with ' + addr[0] + ':' + str(addr[1]))
            # Sending message to connected client
            conn.send('AWAITING__COMM\n'.encode(Encoding))  # send only takes string
            data = self.get_bytes_from_client(conn, 9)
            if len(data) == 9:
                Console.print("Message Validation... ")
                if data[1:3].decode(Encoding) == "IP":
                    TestMode = bool(data[3])
                    ConnIP  = data[4].__str__() + "."
                    ConnIP += data[5].__str__() + "."
                    ConnIP += data[6].__str__() + "."
                    ConnIP += data[7].__str__()
                    Console.print("IP detected: " + ConnIP)
                    Console.print("Video Codec is " + VideoCodec[TestMode])

                    conn = self.connection_loop(conn, TestMode)

                    if conn:
                        # came out of loop
                        conn.close()
                        self.closesrv()

                        Console.print("Connection with %s closed." % str(addr))
                else:
                    Console.print("Invalid message detected! Breaking connection.")
            else:
                Console.print("Incomplete message received! Breaking connection.")

    def connection_loop(self, conn, TestMode):
        noData_cnt = 0
        COMM_vars.streaming_mode = 0
        self.Stream_Thread = StreamThread(TestMode)
        self.Stream_Thread.start()
        # now keep talking with the client
        while not self.shutdown_flag.is_set():
            # Receiving from client
            data = self.get_bytes_from_client(conn, 8)
            try:
                data_len = len(data)
            except TypeError:
                data_len = False

            if data_len < 8:
                noData_cnt += 1
                if noData_cnt > RETRY_LIMIT:
                    Console.print("NO DATA - closing connection")
                    break
            else:
                noData_cnt = 0

                resolution = self.decode_data(data)
                response = self.encode_data(data)

                if Debug > 0:
                    Console.print("chksum" + response[0].__str__())

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
        COMM_vars.light     = Cntrl_Mask1[7]
        COMM_vars.speakers  = Cntrl_Mask1[6]
        COMM_vars.mic       = Cntrl_Mask1[5]
        COMM_vars.display   = Cntrl_Mask1[4]
        COMM_vars.laser     = Cntrl_Mask1[3]
        COMM_vars.AutoMode  = Cntrl_Mask1[2]

        resolution = data[6] - (int(data[6] / 10) * 10)

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

    def __init__(self, TestMode):
        threading.Thread.__init__(self)
        self.shutdown_flag = threading.Event()

        self.TestMode = TestMode

        self.player = [Gst.Pipeline.new("player"),
                  Gst.Pipeline.new("player_test")]
        self.capsfilter = [Gst.ElementFactory.make("capsfilter", "capsfilter"),
                      Gst.ElementFactory.make("capsfilter", "capsfilter_test")]
        self.encoder = [Gst.ElementFactory.make("gdppay", "encoder"),
                        Gst.ElementFactory.make("gdppay", "encoder_test")]
        self.sink = [Gst.ElementFactory.make("tcpserversink", "video-output"),
                     Gst.ElementFactory.make("tcpserversink", "video-output_test")]
        self.source = [Gst.ElementFactory.make("v4l2src", "video-source"),
                       Gst.ElementFactory.make("videotestsrc", "video-source_test")]

        self.init_Gstreamer()
        self.res_queue = queue.Queue()

    def run(self):
        Console.print('Streamer Thread #%s started' % self.ident)

        req_mode = Gst.State.READY
        self.res_queue.put(req_mode)

        Update = False
        res_switch = 9
        curr_resolution = 0

        while not self.shutdown_flag.is_set():
            if curr_resolution != self.req_resolution:
                if self.req_resolution > 0:
                    Console.print("Changing Gstreamer resolution")
                    ### CHANGE RESOLUTION CAPS ###
                    caps = Gst.Caps.from_string(VideoCodec[self.TestMode] + capsstr[self.req_resolution])
                    self.capsfilter[self.TestMode].set_property("caps", caps)

                    if self.TestMode is False:
                        self.res_queue.put(Gst.State.READY)
                        self.res_queue.put(Gst.State.PAUSED)
                        self.res_queue.put(Gst.State.PLAYING)

                    self.res_queue.put(Gst.State.PLAYING)
                    if curr_resolution == 0:
                        self.res_queue.put(Gst.State.PLAYING)
                else:
                    self.res_queue.put(Gst.State.PAUSED)

                curr_resolution = self.req_resolution

            if not self.res_queue.empty():
                curr_state = self.player[self.TestMode].get_state(1)[1]
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
                    self.player[self.TestMode].set_state(req_mode)

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

        self.player[self.TestMode].set_state(Gst.State.PAUSED)
        self.player[True].set_state(Gst.State.NULL)
        self.player[False].set_state(Gst.State.NULL)

        Console.print('Streamer Thread #%s stopped' % self.ident)

    def init_Gstreamer(self):
        if HOST:
            self.sink[False].set_property("host", HOST)
            self.sink[True].set_property("host", HOST)
        else:
            self.sink[False].set_property("host", "0.0.0.0")
            self.sink[True].set_property("host", "0.0.0.0")

        self.sink[False].set_property("port", Port_CAM0)
        self.sink[True].set_property("port", Port_CAM0)

        self.gst_init_test()
        self.gst_init_cam()

    def gst_init_test(self):
        ####################################################################
        ### Build test video pipelineas following:
        ###   Source[cam] > Caps > Encoder > Sink[tcp]
        self.source[True].set_property("pattern", "smpte")

        self.player[True].add(self.source[True])
        self.player[True].add(self.capsfilter[True])
        self.player[True].add(self.encoder[True])
        self.player[True].add(self.sink[True])

        self.source[True].link(self.capsfilter[True])
        self.capsfilter[True].link(self.encoder[True])
        self.encoder[True].link(self.sink[True])
        # self.player[True].set_state(Gst.State.READY)

    def gst_init_cam(self):
        ####################################################################
        ### Build video pipelineas following:
        ###   Source[cam] > Caps > Parser > Codec_Opt > Encoder > Sink[tcp]
        # source (already defined)
        # capsfilter (already defined)
        parser = Gst.ElementFactory.make("h264parse", "parser")
        rtimer = Gst.ElementFactory.make("rtph264pay", "rtimer")
        # encoder (already defined)
        # sink (already defined)
        ####################################################################

        rtimer.set_property("config_interval", 1)
        rtimer.set_property("pt", 96)

        self.player[False].add(self.source[False])
        self.player[False].add(self.capsfilter[False])
        self.player[False].add(parser)
        self.player[False].add(rtimer)
        self.player[False].add(self.encoder[False])
        self.player[False].add(self.sink[False])

        self.source[False].link(self.capsfilter[False])
        self.capsfilter[False].link(parser)
        parser.link(rtimer)
        rtimer.link(self.encoder[False])
        self.encoder[False].link(self.sink[False])
        # self.player[False].set_state(Gst.State.READY)


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
