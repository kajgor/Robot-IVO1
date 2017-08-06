# !/usr/bin/env python

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

# from _thread import *
from init_variables import Encoding, LEFT, RIGHT, COMM_BITSHIFT, calc_checksum

# import atexit
# GUI_file = "./gui_artifacts/TestServer_extended.glade"
GUI_file = "./gui_artifacts/MainConsole_extended.glade"

WinType = Gtk.Window

HOST = 'localhost'   # Symbolic name meaning all available interfaces
Port_COMM = 5000
Debug = 1

class clientthread(threading.Thread):
    srv = None

    def __init__(self, GUI):
        threading.Thread.__init__(self)

        self.GUI = GUI
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
            print("conn is None!!")
            # return
        else:
            print('Connected with ' + addr[0] + ':' + str(addr[1]))
            # Sending message to connected client
            conn.send('AWAITING CONNECTION: ENGINE\n'.encode('ascii'))  # send only takes string

        nodata_cnt = 0
        # infinite loop so that function do not terminate and thread do not end.
        while self.GUI.switch_ServerStart.get_active():
            # Receiving from client
            try:
                data = conn.recv(6)
            except socket.error:
                data = ''
                print("Socket error!")

            if not data:
                nodata_cnt += 1
                if nodata_cnt >= 10:
                    print("NO DATA - closing connection")
                    break
            else:
                nodata_cnt = 0
                # data_decoded = self.encode_data(data)
                # reply = data_decoded.ljust(15, chr(10).encode(Encoding))
                retstr = data[:6] + chr(calc_checksum(data)).encode(Encoding) + data[8:]
                print("chksum", chr(calc_checksum(data)))
                reply = retstr.ljust(15, chr(10).encode(Encoding))

                if Debug > 2:
                    print("DATA_IN>> " + data.__str__())

                if Debug > 2:
                    print("DATA_OUT>> " + reply.__str__())

                time.sleep(0.01)
                try:
                    conn.sendall(reply)
                except BrokenPipeError:
                    print("transmit: BrokenPipeError")
                    return None
                except AttributeError:
                    print("transmit: AttributeError")
                    return None
                except OSError:
                    print("transmit: OSError (client lost)")
                    return None

        if conn:
            # came out of loop
            conn.close()
            self.closesrv()
            print('Connection with ' + addr[0] + ':' + str(addr[1]) + " closed. EXITING THREAD!")
            # start_new_thread(self.thread_restart, (None,))
            # exit_thread()

        # ... Clean shutdown code here ...
        print('Thread #%s stopped' % self.ident)

    def encode_data(self, data):
        Motor_PWR = [0, 0]
        Motor_PWR[RIGHT] = data[0] - COMM_BITSHIFT + data[1] - COMM_BITSHIFT
        Motor_PWR[LEFT] = (10 * (data[0] - COMM_BITSHIFT) % 10) + (data[2] - COMM_BITSHIFT)

        print("Motor_PWR", Motor_PWR)
        return Motor_PWR

    def create_socket(self):
        # Create Socket
        clientthread.srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # GTK_TSMain.srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        print('Socket created')
        srv_address = (HOST, Port_COMM)

        try:
            clientthread.srv.bind(srv_address)

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
        print("Closing socket[*]")
        if self.srv is not None:
            try:
                self.srv.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass

            self.srv.close()
            GTK_TSMain.player.set_state(Gst.State.NULL)
            clientthread.srv = None


# Function for handling connections. This will be used to create threads
class thread_restart(threading.Thread):
    def __init__(self, GUI):
        threading.Thread.__init__(self)
        self.GUI = GUI

    def run(self):
        while self.GUI.switch_ServerStart.get_active() is True:
            if not clientthread(self.GUI).srv:
                # self.create_socket()
                clientthread(self.GUI).start()
            time.sleep(0.1)
        return True


class ServiceExit(Exception):
    """
    Custom exception which is used to trigger the clean exit
    of all running threads and the main program.
    """
    pass

class GTK_TSMain(WinType):
    Gst.init(None)
    player = Gst.Pipeline.new("player")
    Host = "localhost"
    VID_Port = Port_COMM + 1

    def __init__(self):
        super(GTK_TSMain, self).__init__()


        # Register the signal handlers
        signal.signal(signal.SIGTERM, clientthread(self).closesrv)
        signal.signal(signal.SIGINT, clientthread(self).closesrv)

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
        self.switch_ServerStart = builder.get_object("Switch_ServerStart")
        # self.switch_ServerStart.connect("notify::active", self.on_Switch_ServerStart_activate)
        self.statusbar_TestServer = builder.get_object("StatusBar_TestServer")
        self.context_id           = self.statusbar_TestServer.get_context_id("message")

        self.show_all()
        builder.connect_signals(self)
        atexit.register(clientthread(self).closesrv)

        self.source = Gst.ElementFactory.make("videotestsrc", "video-source")
        self.source.set_property("pattern", "smpte")

        self.sink = Gst.ElementFactory.make("tcpserversink", "video-output")
        self.sink.set_property("host", self.Host)
        self.sink.set_property("port", self.VID_Port)

        caps = Gst.Caps.from_string("video/x-raw, width=640, height=480, framerate=15/1")
        self.filter = Gst.ElementFactory.make("capsfilter", "filter")
        self.filter.set_property("caps", caps)
        # self.filter.set_property("width", 640)
        # self.filter.set_property("height", 480)

        self.encoder = Gst.ElementFactory.make("gdppay", "encoder")

        self.player.add(self.source, self.filter, self.encoder, self.sink)

        self.source.link(self.filter)
        self.filter.link(self.encoder)
        self.encoder.link(self.sink)

    def on_Switch_ServerStart_activate(self, widget, event):
        # now keep talking with the client
        while self.switch_ServerStart.get_active() and clientthread.srv is None:
        # if self.switch_ServerStart.get_active() is True:
            self.player.set_state(Gst.State.PLAYING)
            self.statusbar_TestServer.push(self.context_id, "Streaming on port " + self.VID_Port.__str__())

            # start_new_thread(self.clientthread, (None,))
            Conn_thread = thread_restart(self)
            Conn_thread.start()
            time.sleep(.25)

        if self.switch_ServerStart.get_active() is False and clientthread.srv is not None:
            clientthread(self).closesrv()
            self.statusbar_TestServer.push(self.context_id, "Port " + self.VID_Port.__str__() + " closed.")

    def gtk_main_quit(self, dialog):
        clientthread(self).closesrv()
        Gtk.main_quit ()



GTK_TSMain()
# GObject.threads_init()
Gtk.main()
