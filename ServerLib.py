import threading
import signal
import socket
import atexit
import time
import sys
import gi
gi.require_version('Gst', '1.0')
gi.require_version('Gtk', '3.0')
gi.require_version('GstVideo', '1.0')
from gi.repository import Gst, GObject, Gtk, GstVideo
from init_variables import Encoding, LEFT, RIGHT, COMM_BITSHIFT, calc_checksum, RECMSGLEN

GUI_file = "./gui_artifacts/MainConsole_extended.glade"

HOST = 'localhost'   # Symbolic name meaning all available interfaces
Port_COMM = 5000
Debug = 0
RESP_DELAY = 0.025


class ClientThread(threading.Thread):
    srv = None
    on_btn = False

    def __init__(self):
        threading.Thread.__init__(self)
        self.volt = chr(130) + chr(35)
        self.current = chr(60) + chr(39)
        self.Motor_PWR = [60, 50]
        self.Motor_RPM = [80, 80]
        self.CPUtemp = chr(160)
        # The shutdown_flag is a threading.Event object that
        # indicates whether the thread should be terminated.
        # self.shutdown_flag = threading.Event()

        # ... Other thread setup code here ...

    def run(self):
        print('Thread #%s started' % self.ident)

        self.create_socket()
        print("Opening socket[+]")
        self.srv.listen(5)
        print('Socket now listening')

        # now keep talking with the client
        # while self.switch_ServerStart.get_active():
        conn = addr = None
        try:
            conn, addr = self.srv.accept()
        except:
            print("User break")

        if conn is None:
            print("No connection interrupted.")
        else:
            print('Connected with ' + addr[0] + ':' + str(addr[1]))
            # Sending message to connected client
            conn.send('AWAITING CONNECTION: ENGINE\n'.encode('ascii'))  # send only takes string

        lastresolution = 0

        nodata_cnt = 0
        inc = 30; adx = 1
        while self.on_btn is True:
            # Receiving from client
            try:
                data = conn.recv(8)
                # print("data==>", data, len(data))
            except socket.error:
                data = None
                print("Socket error!")

            if len(data) < 8:
                nodata_cnt += 1
                if nodata_cnt >= 15:
                    print("NO DATA - closing connection")
                    break
            else:
                # print("data[6]", data[6])
                resolution = data[6] - COMM_BITSHIFT
                if lastresolution != resolution:
                    if resolution == 0:
                        print("Stopping Gstreamer.")
                        init_Gstreamer.player.set_state(Gst.State.PAUSED)
                    elif resolution == 1:
                        caps = Gst.Caps.from_string("video/x-raw, width=320, height=240, framerate=15/1")
                        init_Gstreamer.filter.set_property("caps", caps)
                    elif resolution == 2:
                        caps = Gst.Caps.from_string("video/x-raw, width=640, height=480, framerate=15/1")
                        init_Gstreamer.filter.set_property("caps", caps)
                    elif resolution == 3:
                        caps = Gst.Caps.from_string("video/x-raw, width=800, height=600, framerate=15/1")
                        init_Gstreamer.filter.set_property("caps", caps)
                    elif resolution == 4:
                        caps = Gst.Caps.from_string("video/x-raw, width=1280, height=800, framerate=15/1")
                        init_Gstreamer.filter.set_property("caps", caps)
                    elif resolution == 5:
                        caps = Gst.Caps.from_string("video/x-raw, width=1920, height=1080, framerate=15/1")
                        init_Gstreamer.filter.set_property("caps", caps)

                    if lastresolution == 0:
                        print("Starting Gstreamer.")
                        init_Gstreamer.player.set_state(Gst.State.PLAYING)

                    lastresolution = resolution

                nodata_cnt = 0
                inc += adx
                if inc > 250 or inc < 30:
                    adx = -adx

                self.current = chr(60 + int(inc / 10)) + chr(int(inc % 100))

                retstr = chr(calc_checksum(data))
                retstr += chr(self.Motor_PWR[RIGHT])
                retstr += chr(self.Motor_PWR[LEFT])
                retstr += chr(self.Motor_RPM[RIGHT])
                retstr += chr(self.Motor_RPM[LEFT])
                retstr += chr(data[5])  # CntrlMask1
                retstr += chr(data[6])  # CntrlMask2
                retstr += chr(10) + chr(10)
                retstr += self.CPUtemp
                retstr += self.current
                retstr += self.volt

                if Debug > 0: print("chksum", retstr[0])
                reply = retstr.encode(Encoding).ljust(RECMSGLEN, chr(10).encode(Encoding))

                if Debug > 2:
                    print("DATA_IN>> " + data.__str__())

                if Debug > 2:
                    print("DATA_OUT>> " + reply.__str__())

                time.sleep(RESP_DELAY)
                try:
                    conn.sendall(reply)
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

        if conn:
            # came out of loop
            conn.close()
            self.closesrv()
            print('Connection with ' + addr[0] + ':' + str(addr[1]) + " closed.")

        # ... Clean shutdown code here ...
        print('Thread #%s stopped' % self.ident)

    @staticmethod
    def encode_data(data):
        Motor_PWR = [0, 0]
        Motor_PWR[RIGHT] = data[0] - COMM_BITSHIFT + data[1] - COMM_BITSHIFT
        Motor_PWR[LEFT] = (10 * (data[0] - COMM_BITSHIFT) % 10) + (data[2] - COMM_BITSHIFT)

        print("Motor_PWR", Motor_PWR)
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

            init_Gstreamer.player.set_state(Gst.State.PAUSED)
            ClientThread.srv = None


# Function for handling connections. This will be used to create threads
class ThreadRestart(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)

    def run(self):
        while ClientThread.on_btn is True:
            if not ClientThread().srv:
                ClientThread().start()
            time.sleep(0.35)
        return True


class ServiceExit(Exception):
    """
    Custom exception which is used to trigger the clean exit
    of all running threads and the main program.
    """
    pass


class init_Gstreamer:
    Gst.init(None)
    player = Gst.Pipeline.new("player")
    Host = "localhost"
    VID_Port = Port_COMM + 1
    filter = Gst.ElementFactory.make("capsfilter", "filter")

    def __init__(self):
        self.source = Gst.ElementFactory.make("videotestsrc", "video-source")
        self.source.set_property("pattern", "smpte")

        self.sink = Gst.ElementFactory.make("tcpserversink", "video-output")
        self.sink.set_property("host", self.Host)
        self.sink.set_property("port", self.VID_Port)

        self.encoder = Gst.ElementFactory.make("gdppay", "encoder")

        self.player.add(self.source, self.filter, self.encoder, self.sink)

        self.source.link(self.filter)
        self.filter.link(self.encoder)
        self.encoder.link(self.sink)
        self.player.set_state(Gst.State.READY)


class GtkTsMain(Gtk.Window):
    def __init__(self):
        builder = self.init_GUI()
        self.switch_ServerStart   = builder.get_object("Switch_ServerStart")
        self.StatusBar_TestServer = builder.get_object("StatusBar_TestServer")
        self.context_id           = self.StatusBar_TestServer.get_context_id("message")

        self.show_all()
        builder.connect_signals(self)
        atexit.register(ClientThread().closesrv)

        Gtk.main()

    def init_GUI(self):
        super(GtkTsMain, self).__init__()
        # Register the signal handlers
        signal.signal(signal.SIGTERM, ClientThread().closesrv)
        signal.signal(signal.SIGINT, ClientThread().closesrv)

        builder = Gtk.Builder()
        # builder.add_from_file(GUI_file)
        builder.add_objects_from_file(GUI_file, ("MainBox_TSRV", "StatusBar_TestServer"))
        print("GUI file added: ", GUI_file)

        self.add(builder.get_object("MainBox_TSRV"))
        self.set_resizable(False)
        # self.set_deletable(False)
        self.set_destroy_with_parent(True)

        self.set_title("TEST SERVER")
        self.connect("destroy", self.gtk_main_quit)
        self.connect("delete-event", Gtk.main_quit)

        return builder

    def on_Switch_ServerStart_activate(self, widget, event):
        # now keep talking with the client
        ClientThread.on_btn = widget.get_active()

        if ClientThread.on_btn is True:  # and ClientThread.srv is None:
            self.StatusBar_TestServer.push(self.context_id, "Waiting on port " + Port_COMM.__str__())

            if ClientThread.srv is None:
                Conn_thread = ThreadRestart()
                Conn_thread.start()
        else:
            time.sleep(0.5)

            if ClientThread.on_btn is False and ClientThread.srv is not None:
                ClientThread().closesrv()
                self.StatusBar_TestServer.push(self.context_id, "Port " + Port_COMM.__str__() + " closed.")

    def gtk_main_quit(self, dialog):
        ClientThread().closesrv()
        Gtk.main_quit()


