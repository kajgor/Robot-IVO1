import subprocess
import threading
import signal
import socket
import queue
import time
import sys
import gi
import re
gi.require_version('Gst', '1.0')
gi.require_version('Gtk', '3.0')
gi.require_version('GstVideo', '1.0')
from gi.repository import Gst, Gtk, GstVideo
from init_variables import Encoding, LEFT, RIGHT, COMM_BITSHIFT, RECMSGLEN,\
    calc_checksum, Paths, VideoCodec, capsstr, COMM_vars

HOST = ''   # Symbolic name meaning all available interfaces
Port_COMM = 4550
Port_CAM0 = Port_COMM + 1
Port_MIC0 = Port_COMM + 2
Port_DSP0 = Port_COMM + 4
Port_SPK0 = Port_COMM + 5
Debug = 0
Retry_Cnt = 15

Gst.init(None)

class ClientThread(threading.Thread):
    srv = None
    # on_btn = False

    def __init__(self):
        threading.Thread.__init__(self)

        # The shutdown_flag is a threading.Event object that
        # indicates whether the thread should be terminated.
        self.shutdown_flag = threading.Event()

        # self.Stream_Thread = StreamThread()
        self.Motor_PWR = [60, 50]
        self.Motor_RPM = [80, 80]

    def run(self):
        print('Client Thread #%s started' % self.ident)

        while not self.shutdown_flag.is_set():
            self.create_socket()
            print("Opening socket[+]")
            self.srv.listen(5)
            print('Socket now listening on', HOST, "[", Port_COMM, "]")

            conn = addr = None
            try:
                conn, addr = self.srv.accept()
            except OSError:
                print("User break")

            if conn is None:
                print("No connection interrupted.")
            else:
                print('Connected with ' + addr[0] + ':' + str(addr[1]))
                # Sending message to connected client
                conn.send('AWAITING__COMM\n'.encode(Encoding))  # send only takes string
                data = self.get_bytes_from_client(conn, 9)
                if len(data) == 9:
                    print("Message Validation", end='... ')
                    if data[1:3].decode(Encoding) == "IP":
                        TestMode = bool(data[3] - COMM_BITSHIFT)
                        ConnIP  = (data[4] - COMM_BITSHIFT).__str__() + "."
                        ConnIP += (data[5] - COMM_BITSHIFT).__str__() + "."
                        ConnIP += (data[6] - COMM_BITSHIFT).__str__() + "."
                        ConnIP += (data[7] - COMM_BITSHIFT).__str__()
                        print("IP detected:", ConnIP)
                        print("Video Codec is", VideoCodec[TestMode])

                        conn = self.connection_loop(conn, TestMode)

                        if conn:
                            # came out of loop
                            conn.close()
                            self.closesrv()

                            print("Connection with %s closed." % str(addr))
                    else:
                        print("Invalid message detected! Breaking connection.")
                else:
                    print("Incomplete message received! Breaking connection.")

        # ... Clean shutdown code here ...
        print('Client Thread #%s stopped' % self.ident)

    def connection_loop(self, conn, TestMode):
        noData_cnt = 0
        COMM_vars.streaming_mode = 0
        # init_Gstreamer = InitGstreamer()
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
                if noData_cnt > Retry_Cnt:
                    print("NO DATA - closing connection")
                    break
            else:
                noData_cnt = 0
                # print("streaming_mode", streaming_mode)
                retstr = chr(calc_checksum(data))
                retstr += chr(self.Motor_PWR[RIGHT])
                retstr += chr(self.Motor_PWR[LEFT])
                retstr += chr(self.Motor_RPM[RIGHT])
                retstr += chr(self.Motor_RPM[LEFT])
                retstr += chr(data[5])  # CntrlMask1
                retstr += chr(COMM_vars.streaming_mode + COMM_BITSHIFT)  # CntrlMask2
                retstr += chr(10) + chr(10)
                retstr += chr(COMM_vars.CoreTemp)
                retstr += COMM_vars.Current
                retstr += COMM_vars.Voltage

                reply = retstr.ljust(RECMSGLEN, chr(10))

                if Debug > 0:
                    print("chksum", retstr[0])

                if Debug > 2:
                    print("DATA_IN>> " + data.__str__())
                    print("DATA_OUT>> " + reply.__str__())

                if self.Stream_Thread.res_queue.empty():
                    self.Stream_Thread.resolution = data[6] - COMM_BITSHIFT
                    # print(">>>self.Stream_Thread.resolution", self.Stream_Thread.resolution)
                # else:
                    # print("queue not empty")
                try:
                    conn.sendall(reply.encode(Encoding))
                except BrokenPipeError:
                    print("transmit_message: BrokenPipeError")
                    break
                    # return None
                except AttributeError:
                    print("transmit_message: AttributeError")
                    break
                    # return None
                except OSError:
                    print("transmit_message: OSError (client lost)")
                    break
                    # return None

        self.Stream_Thread.shutdown_flag.set()

        return conn

    def get_bytes_from_client(self, conn, count):
        try:
            data = conn.recv(count)
            # print("data==>", data, len(data))
        except socket.error:
            data = None
            print("Socket error!")

        return data

    @staticmethod
    def encode_data(data):
        Motor_PWR = [0, 0]
        Motor_PWR[RIGHT] = data[0] - COMM_BITSHIFT + data[1] - COMM_BITSHIFT
        Motor_PWR[LEFT] = (10 * (data[0] - COMM_BITSHIFT) % 10) + (data[2] - COMM_BITSHIFT)

        # print("Motor_PWR", Motor_PWR)
        return Motor_PWR

    @staticmethod
    def create_socket():
        # Create Socket
        ClientThread.srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # ClientThread.srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        print('Socket created')
        srv_address = (HOST, Port_COMM)

        try:
            ClientThread.srv.bind(srv_address)

        except socket.error as msg:
            print('Bind failed. Error Code : ' + msg.__str__())
            # print('Bind failed. Error Code : ' + str(msg[0]) + ' Message ' + msg[1])
            sys.exit()

        except OSError as msg:
            print('Bind failed. Error Code : ' + str(msg[0]) + ' Message ' + msg[1])
            print('Advice: check for python process to kill it!')
            sys.exit()

        print('Socket bind complete')
        # Start listening on socket
        return True

    def closesrv(self):
        print("Closing socket[-]")
        if self.srv is not None:
            try:
                self.srv.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass

            try:
                self.srv.close()
            except AttributeError:
                pass

            ClientThread.srv = None


class StreamThread(threading.Thread):
    resolution = 1

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
        print('Streamer Thread #%s started' % self.ident)

        req_mode = Gst.State.READY
        self.res_queue.put(req_mode)
        req_mode = Gst.State.READY
        self.res_queue.put(req_mode)

        res_switch = 9
        curr_resolution = self.resolution

        while not self.shutdown_flag.is_set():
            if curr_resolution != self.resolution:
                curr_resolution = self.resolution
                if self.resolution > 0:
                    self.res_queue.put(Gst.State.PAUSED)
                    if self.TestMode is False:
                        print("Resetting Gstreamer for resolution change")
                        self.res_queue.put(Gst.State.READY)
                        self.res_queue.put(Gst.State.PAUSED)
                    else:
                        print("Changing Gstreamer resolution")
                    self.res_queue.put(Gst.State.PLAYING)
                    self.res_queue.put(Gst.State.PLAYING)
                else:
                    self.res_queue.put(Gst.State.READY)
                    self.res_queue.put(Gst.State.PAUSED)
                    self.res_queue.put(Gst.State.PAUSED)

            if not self.res_queue.empty():
                curr_state = self.player[self.TestMode].get_state(1)[1]
                if curr_state == req_mode:
                    if curr_state == Gst.State.PAUSED:
                        print("Paused.")
                    elif curr_state == Gst.State.READY:
                        print("Ready.")
                    elif curr_state == Gst.State.PLAYING:
                        print("Streaming!")
                        COMM_vars.streaming_mode = self.resolution

                    req_mode = self.res_queue.get()
                    if req_mode != curr_state:
                        res_switch = bool(req_mode) * 10
                else:
                    res_switch += 1

            if res_switch == 10:
                res_switch = 0
                if req_mode == Gst.State.PAUSED:
                    if self.resolution > 0:
                        caps = Gst.Caps.from_string(VideoCodec[self.TestMode] + capsstr[self.resolution])
                        self.capsfilter[self.TestMode].set_property("caps", caps)
                    print("Pausing Gstreamer", end='... ')
                elif req_mode == Gst.State.READY:
                    print("Preparing Gstreamer", end='... ')
                elif req_mode == Gst.State.PLAYING and self.resolution > 0:
                    print("Requesting streaming in mode", self.resolution, end='... ')
                else:
                    print('ERROR: resolution', self.resolution, ", mode", req_mode)
                    res_switch = 10

                if res_switch == 0:
                    self.player[self.TestMode].set_state(req_mode)

            time.sleep(.25)

        self.player[self.TestMode].set_state(Gst.State.PAUSED)
        self.player[True].set_state(Gst.State.NULL)
        self.player[False].set_state(Gst.State.NULL)

        # self.init_Gstreamer.player[False].set_state(Gst.State.READY)
        # self.init_Gstreamer.player[True].set_state(Gst.State.READY)
        # self.init_Gstreamer.player[False].set_state(Gst.State.NULL)
        # self.init_Gstreamer.player[True].set_state(Gst.State.NULL)
        print('Streamer Thread #%s stopped' % self.ident)


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
        print('Driver Thread #%s started' % self.ident)
        inc = 30 ; adx = 1
        idx = 30
        while not self.shutdown_flag.is_set():

            # CURRENT - report continuously
            inc += adx
            if inc > 250 or inc < 30:
                adx = -adx
            COMM_vars.Current = chr(60 + int(inc / 10)) + chr(int(inc % 100))

            # Voltage - report continuously
            COMM_vars.Voltage = chr(130) + chr(35)

            # DistanceS1
            COMM_vars.DistanceS1 = chr(COMM_BITSHIFT + 100)

            # TEMP - report every 3sec
            if idx == 30:
                Tempstr = execute_cmd("LD_LIBRARY_PATH=/opt/vc/lib && /opt/vc/bin/vcgencmd measure_temp")
                Tempstr = re.findall(r"\d+", Tempstr.decode(Encoding))
                Temp = int(Tempstr[0]) * 10 + int(Tempstr[1])
                COMM_vars.CoreTemp = int(Temp / 5) + COMM_BITSHIFT
                idx = 0

            time.sleep(.1)
            idx += 1

        print('Driver Thread #%s stopped' % self.ident)


# Function for handling connections. This will be used to create threads
class ThreadRestart(threading.Thread):

    def __init__(self):
        threading.Thread.__init__(self)
        # # The shutdown_flag is a threading.Event object that
        # # indicates whether the thread should be terminated.
        self.shutdown_flag = threading.Event()

        self.Driver_Thread = DriverThread()
        self.Client_Thread = ClientThread()
        # self.Stream_Thread = StreamThread(self.init_Gstreamer)
        #
        # try:
        #     self.init_Gstreamer.player[False].get_state(1)[1]
        # except:
        #     print("init_Gstreamer()")
            # self.init_Gstreamer()

    def run(self):
        print("services starting up...")
        print('Thread manager #%s started' % self.ident)
        self.Driver_Thread.start()
        self.Client_Thread.start()

        while not self.shutdown_flag.is_set():
            time.sleep(1)

        # EXIT thread
        self.stop_()

    def stop_(self):
        print("shutting down services...")
        self.Client_Thread.shutdown_flag.set()
        if self.Client_Thread.srv is not None:
            self.Client_Thread.closesrv()
        self.Driver_Thread.shutdown_flag.set()

        if self.Client_Thread.is_alive():
            self.Client_Thread.join()

        if self.Driver_Thread.is_alive():
            self.Driver_Thread.join()
        # except RuntimeError:
        #     pass

        print('Thread manager #%s stopped' % self.ident)
        self.__init__()

    def ProgramExit(self):
        print("Exit requested!")

        while self.is_alive():
            self.shutdown_flag.set()
            # print("Finishing threads...")
            time.sleep(.2)


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


class GtkTsMain(Gtk.Window):

    Thread_Restart = ThreadRestart()

    def __init__(self):
        builder = self.init_GUI()
        self.switch_ServerStart   = builder.get_object("Switch_ServerStart")
        self.StatusBar_TestServer = builder.get_object("StatusBar_TestServer")
        self.context_id           = self.StatusBar_TestServer.get_context_id("message")

        self.show_all()
        builder.connect_signals(self)

        Gtk.main()

    def init_GUI(self):
        super(GtkTsMain, self).__init__()
        # Register the signal handlers
        signal.signal(signal.SIGTERM, self.Thread_Restart.ProgramExit)
        signal.signal(signal.SIGINT, self.Thread_Restart.ProgramExit)

        builder = Gtk.Builder()
        # builder.add_from_file(GUI_file)
        builder.add_objects_from_file(Paths.GUI_file, ("MainBox_TSRV", "StatusBar_TestServer"))
        print("GUI file added: ", Paths.GUI_file)

        self.add(builder.get_object("MainBox_TSRV"))
        self.set_resizable(False)
        # self.set_deletable(False)
        self.set_destroy_with_parent(True)

        self.set_title("TEST SERVER")
        self.connect("destroy", self.gtk_main_quit)
        self.connect("delete-event", Gtk.main_quit)

        return builder

    def on_Switch_ServerStart_activate(self, widget, event):
        on_btn = widget.get_active()
        # now keep talking with the client
        if on_btn is True:  # and ClientThread.srv is None:
            # if ClientThread.srv is None:
            self.Thread_Restart.start()
            # self.set_deletable(False)
            self.StatusBar_TestServer.push(self.context_id, "Waiting on port " + Port_COMM.__str__())
        else:
            self.Thread_Restart.shutdown_flag.set()
            while self.Thread_Restart.is_alive():
                time.sleep(0.25)

            # self.set_deletable(True)
            self.StatusBar_TestServer.push(self.context_id, "Port " + Port_COMM.__str__() + " closed.")
            # self.Thread_Restart = ThreadRestart()

        self.show_all()

    def gtk_main_quit(self, dialog):
        self.Thread_Restart.ProgramExit()
        Gtk.main_quit()

