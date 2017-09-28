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
from gi.repository import Gst, Gtk, GstVideo, Gdk
from init_variables import Encoding, LEFT, RIGHT, COMM_BITSHIFT, RECMSGLEN,\
    calc_checksum, Paths, VideoCodec, capsstr, COMM_vars

VERSION = "B3.0"
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

    def __init__(self, GUI):
        threading.Thread.__init__(self)

        # The shutdown_flag is a threading.Event object that
        # indicates whether the thread should be terminated.
        self.shutdown_flag = threading.Event()

        self.GUI = GUI

    def run(self):
        self.GUI.printc('Client Thread #%s started' % self.ident)

        while not self.shutdown_flag.is_set():
            while self.create_socket() is False:
                time.sleep(1)

            self.srv.listen(5)
            self.GUI.printc('Socket now listening on ' + HOST + "[" + Port_COMM.__str__() + "]")

            conn = addr = None
            try:
                conn, addr = self.srv.accept()
            except OSError:
                self.GUI.printc("User break")

            if conn is None:
                self.GUI.printc("No connection interrupted.")
            else:
                self.GUI.printc('Connected with ' + addr[0] + ':' + str(addr[1]))
                # Sending message to connected client
                conn.send('AWAITING__COMM\n'.encode(Encoding))  # send only takes string
                data = self.get_bytes_from_client(conn, 9)
                if len(data) == 9:
                    self.GUI.printc("Message Validation... ")
                    if data[1:3].decode(Encoding) == "IP":
                        TestMode = bool(data[3] - COMM_BITSHIFT)
                        ConnIP  = (data[4] - COMM_BITSHIFT).__str__() + "."
                        ConnIP += (data[5] - COMM_BITSHIFT).__str__() + "."
                        ConnIP += (data[6] - COMM_BITSHIFT).__str__() + "."
                        ConnIP += (data[7] - COMM_BITSHIFT).__str__()
                        self.GUI.printc("IP detected: " + ConnIP)
                        self.GUI.printc("Video Codec is " + VideoCodec[TestMode])

                        conn = self.connection_loop(conn, TestMode)

                        if conn:
                            # came out of loop
                            conn.close()
                            self.closesrv()

                            self.GUI.printc("Connection with %s closed." % str(addr))
                    else:
                        self.GUI.printc("Invalid message detected! Breaking connection.")
                else:
                    self.GUI.printc("Incomplete message received! Breaking connection.")

        # ... Clean shutdown code here ...
        self.GUI.printc('Client Thread #%s stopped' % self.ident)

    def connection_loop(self, conn, TestMode):
        noData_cnt = 0
        COMM_vars.streaming_mode = 0
        # init_Gstreamer = InitGstreamer()
        self.Stream_Thread = StreamThread(self.GUI, TestMode)
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
                    self.GUI.printc("NO DATA - closing connection")
                    break
            else:
                noData_cnt = 0
                # self.GUI.printc("streaming_mode", streaming_mode)
                retstr = chr(calc_checksum(data))
                retstr += chr(COMM_vars.Motor_PWR[RIGHT])
                retstr += chr(COMM_vars.Motor_PWR[LEFT])
                retstr += chr(COMM_vars.Motor_RPM[RIGHT])
                retstr += chr(COMM_vars.Motor_RPM[LEFT])
                retstr += chr(data[5])  # CntrlMask1
                retstr += chr(COMM_vars.streaming_mode + COMM_BITSHIFT)  # CntrlMask2
                retstr += chr(10) + chr(10)
                retstr += chr(COMM_vars.CoreTemp)
                retstr += COMM_vars.Current
                retstr += COMM_vars.Voltage

                reply = retstr.ljust(RECMSGLEN, chr(10))

                if Debug > 0:
                    self.GUI.printc("chksum" + retstr[0].__str__())

                if Debug > 2:
                    self.GUI.printc("DATA_IN>> " + data.__str__())
                    self.GUI.printc("DATA_OUT>> " + reply.__str__())

                if self.Stream_Thread.res_queue.empty():
                    self.Stream_Thread.resolution = data[6] - COMM_BITSHIFT
                    # self.GUI.printc(">>>self.Stream_Thread.resolution", self.Stream_Thread.resolution)
                # else:
                    # self.GUI.printc("queue not empty")
                try:
                    conn.sendall(reply.encode(Encoding))
                except BrokenPipeError:
                    self.GUI.printc("transmit_message: BrokenPipeError")
                    break
                    # return None
                except AttributeError:
                    self.GUI.printc("transmit_message: AttributeError")
                    break
                    # return None
                except OSError:
                    self.GUI.printc("transmit_message: OSError (client lost)")
                    break
                    # return None

        self.Stream_Thread.shutdown_flag.set()

        return conn

    def get_bytes_from_client(self, conn, count):
        try:
            data = conn.recv(count)
            # self.GUI.printc("data==>", data, len(data))
        except socket.error:
            data = None
            self.GUI.printc("Socket error!")

        return data

    @staticmethod
    def encode_data(data):
        Motor_PWR = [0, 0]
        Motor_PWR[RIGHT] = data[0] - COMM_BITSHIFT + data[1] - COMM_BITSHIFT
        Motor_PWR[LEFT] = (10 * (data[0] - COMM_BITSHIFT) % 10) + (data[2] - COMM_BITSHIFT)

        # self.GUI.printc("Motor_PWR", Motor_PWR)
        return Motor_PWR

    def create_socket(self):
        # Create Socket
        ClientThread.srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # ClientThread.srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.GUI.printc('Socket created')
        srv_address = (HOST, Port_COMM)

        try:
            ClientThread.srv.bind(srv_address)

        except socket.error as msg:
            self.GUI.printc('Bind failed. Error Code : ' + msg.__str__())
            # self.GUI.printc('Bind failed. Error Code : ' + str(msg[0]) + ' Message ' + msg[1])
            return False

        except OSError as msg:
            self.GUI.printc('Bind failed. Error Code : ' + str(msg[0]) + ' Message ' + msg[1])
            self.GUI.printc('Advice: check for python process to kill it!')
            return False

        self.GUI.printc('Socket bind complete')
        # Start listening on socket
        return True

    def closesrv(self):
        if self.srv is None:
            self.GUI.printc("Socket is closed!")
        else:
            self.GUI.printc("Closing socket...")
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
    resolution = 1

    def __init__(self, GUI, TestMode):
        threading.Thread.__init__(self)
        self.shutdown_flag = threading.Event()

        self.GUI = GUI
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
        self.GUI.printc('Streamer Thread #%s started' % self.ident)

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
                        self.GUI.printc("Resetting Gstreamer for resolution change")
                        self.res_queue.put(Gst.State.READY)
                        self.res_queue.put(Gst.State.PAUSED)
                    else:
                        self.GUI.printc("Changing Gstreamer resolution")
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
                        self.GUI.printc("Paused.")
                    elif curr_state == Gst.State.READY:
                        self.GUI.printc("Ready.")
                    elif curr_state == Gst.State.PLAYING:
                        self.GUI.printc("Streaming!")
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
                    self.GUI.printc("Pausing Gstreamer...")
                elif req_mode == Gst.State.READY:
                    self.GUI.printc("Preparing Gstreamer...")
                elif req_mode == Gst.State.PLAYING and self.resolution > 0:
                    self.GUI.printc("Requesting streaming in mode " + self.resolution.__str__() + '... ')
                else:
                    self.GUI.printc('ERROR: resolution' + self.resolution.__str__() + ", mode " + req_mode)
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
        self.GUI.printc('Streamer Thread #%s stopped' % self.ident)

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
    def __init__(self, GUI):
        threading.Thread.__init__(self)

        # The shutdown_flag is a threading.Event object that
        # indicates whether the thread should be terminated.
        self.shutdown_flag = threading.Event()

        self.GUI = GUI

    def run(self):
        self.GUI.printc('Driver Thread #%s started' % self.ident)
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

            # Motor Power
            COMM_vars.Motor_PWR = [60, 50]

            # Mmotor RPM
            COMM_vars.Motor_RPM = [80, 80]

            # TEMP - report every 3sec
            if idx == 30:
                Tempstr = execute_cmd("LD_LIBRARY_PATH=/opt/vc/lib && /opt/vc/bin/vcgencmd measure_temp")
                Tempstr = re.findall(r"\d+", Tempstr.decode(Encoding))
                Temp = int(Tempstr[0]) * 10 + int(Tempstr[1])
                COMM_vars.CoreTemp = int(Temp / 5) + COMM_BITSHIFT
                idx = 0

            time.sleep(.1)
            idx += 1

        self.GUI.printc('Driver Thread #%s stopped' % self.ident)


# Function for handling connections. This will be used to create threads
class ThreadManager(threading.Thread):
    def __init__(self, GUI):
        threading.Thread.__init__(self)
        # # The shutdown_flag is a threading.Event object that
        # # indicates whether the thread should be terminated.
        self.shutdown_flag = threading.Event()

        self._GUI = GUI
        self.GUI = Console(self._GUI)
        self.Driver_Thread = DriverThread(self.GUI)
        self.Client_Thread = ClientThread(self.GUI)

        self.GUI.printc("Console " + VERSION + " initialized\n")

    def run(self):
        self.GUI.printc("services starting up...")
        self.GUI.printc('Thread manager #%s started' % self.ident)

        while not self.shutdown_flag.is_set():
            if not self.Driver_Thread.is_alive():
                self.Driver_Thread.start()
            if not self.Client_Thread.is_alive():
                self.Client_Thread.start()

            self.GUI.display_message()

            time.sleep(.25)

        # EXIT thread
        self.stop_()

    def stop_(self):
        self.GUI.printc("shutting down services...")
        self.GUI.display_message()
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

        self.GUI.printc('Thread manager #%s stopped' % self.ident)
        self.GUI.display_message()
        self.__init__(self._GUI)

    def ProgramExit(self):
        self.GUI.printc("Exit requested!")

        while self.is_alive():
            self.shutdown_flag.set()
            # print("Finishing threads...")
            time.sleep(.2)


class Console:
    def __init__(self, GUI):
        self.GUI = GUI
        if self.GUI:
            self.TextBuffer = self.GUI.get_buffer()
            self.TextQueue  = queue.Queue()

        self.stdout = None

    def printc(self, in_string):
        if self.GUI:
            self.TextQueue.put(in_string)
        else:
            print(in_string)

    def display_message(self):
        while not self.TextQueue.empty():
        #     return True
        # else:
            Text = self.TextQueue.get()
            if Text:
                end_iter = self.TextBuffer.get_end_iter()
                self.TextBuffer.insert(end_iter, Text + "\n")
                # self.TextBuffer.insert_at_cursor(self.stdout)

                mark = self.TextBuffer.get_insert()
                self.GUI.scroll_to_mark(mark, 0.0, True, 0.5, 0.5)
                time.sleep(.1)

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

    def __init__(self):
        builder = self.init_GUI()
        self.switch_ServerStart   = builder.get_object("Switch_ServerStart")
        self.StatusBar_TestServer = builder.get_object("StatusBar_TestServer")
        self.TextView_Console     = builder.get_object("TextView_Console")
        self.context_id           = self.StatusBar_TestServer.get_context_id("message")

        self.TextView_Console.override_color(Gtk.StateType.NORMAL, Gdk.RGBA(1, .75, 0, 1))
        self.TextView_Console.override_background_color(Gtk.StateType.NORMAL, Gdk.RGBA(.15, 0.15, 0.15, 1))

        self.Thread_Restart = None
        self.init_Thread()

        self.show_all()
        builder.connect_signals(self)

        Gtk.main()

    def init_Thread(self):
        self.Thread_Restart = ThreadManager(self.TextView_Console)

        # Register the signal handlers
        signal.signal(signal.SIGTERM, self.Thread_Restart.ProgramExit)
        signal.signal(signal.SIGINT, self.Thread_Restart.ProgramExit)

    def init_GUI(self):
        super(GtkTsMain, self).__init__()

        builder = Gtk.Builder()
        # builder.add_from_file(GUI_file)
        builder.add_objects_from_file(Paths.GUI_file, ("MainBox_TSRV", "StatusBar_TestServer"))
        print("GUI file added: ", Paths.GUI_file)

        self.add(builder.get_object("MainBox_TSRV"))
        self.set_resizable(False)
        # self.set_deletable(False)
        self.set_destroy_with_parent(True)

        self.set_title("ROBOT SERVER")
        self.connect("destroy", self.gtk_main_quit)
        self.connect("delete-event", Gtk.main_quit)

        return builder

    def on_Switch_ServerStart_activate(self, widget, event):
        # now keep talking with the client
        if widget.get_active() is True:  # and ClientThread.srv is None:
            # if ClientThread.srv is None:
            self.Thread_Restart.start()
            # self.set_deletable(False)
            self.StatusBar_TestServer.push(self.context_id, "Waiting on port " + Port_COMM.__str__())
        else:
            self.Thread_Restart.shutdown_flag.set()
            while self.Thread_Restart.is_alive():
                time.sleep(0.25)

            self.init_Thread()
            # self.set_deletable(True)
            self.StatusBar_TestServer.push(self.context_id, "Port " + Port_COMM.__str__() + " closed.")

        self.show_all()

    def gtk_main_quit(self, dialog):
        self.Thread_Restart.ProgramExit()
        Gtk.main_quit()

