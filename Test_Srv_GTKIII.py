# !/usr/bin/env python

import socket
import atexit
import sys
import gi
gi.require_version('Gst', '1.0')
gi.require_version('Gtk', '3.0')
gi.require_version('GstVideo', '1.0')
from gi.repository import Gst, GObject, Gtk, GstVideo

from _thread import *
from init_variables import Encoding

# import atexit
# GUI_file = "./gui_artifacts/TestServer_extended.glade"
GUI_file = "./gui_artifacts/MainConsole_extended.glade"

WinType = Gtk.Window

HOST = 'localhost'   # Symbolic name meaning all available interfaces
Port_COMM = 5000
Debug = 1

class GTK_TSMain(WinType):
    srv = None

    Gst.init(None)
    player = Gst.Pipeline.new("player")
    Host = "localhost"
    VID_Port = Port_COMM + 1

    def __init__(self):
        super(GTK_TSMain, self).__init__()

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
        atexit.register(self.closesrv)

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

    def create_socket(self):
        # Create Socket
        self.srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        print('Socket created')
        srv_address = (HOST, Port_COMM)

        try:
            self.srv.bind(srv_address)

        except socket.error as msg:
            print('Bind failed. Error Code : ' + str(msg[0]) + ' Message ' + msg[1])
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
        self.srv.shutdown(socket.SHUT_RDWR)
        self.srv.close()
        self.player.set_state(Gst.State.NULL)

    def on_Switch_ServerStart_activate(self, widget, event):
        if self.switch_ServerStart.get_active() is True:
            self.create_socket()
            print("Opening socket[+]")
            self.srv.listen(5)
            print('Socket now listening')
            self.player.set_state(Gst.State.PLAYING)
            self.statusbar_TestServer.push(self.context_id, "Streaming on port " + self.VID_Port.__str__())

            start_new_thread(self.clientthread, (self,))

        else:
            self.closesrv()
            self.statusbar_TestServer.push(self.context_id, "Port " + self.VID_Port.__str__() + " closed.")

    # Function for handling connections. This will be used to create threads
    def clientthread(self, GUI):
        # now keep talking with the client
        while 1:
            conn = addr = None
            try:
                conn, addr = GUI.srv.accept()
            except:
                print("User break")

            if conn is None:
                print("conn is None!!")
                return

            print('Connected with ' + addr[0] + ':' + str(addr[1]))
            # Sending message to connected client
            conn.send('AWAITING CONNECTION: ENGINE\n'.encode('ascii'))  # send only takes string

            nodata_cnt = 0
            # infinite loop so that function do not terminate and thread do not end.
            while True:
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
                    reply = data.ljust(15, chr(10).encode(Encoding))
                    if Debug > 0:
                        print("DATA_IN>> " + data.__str__())

                    if Debug > 0:
                        print("DATA_OUT>> " + reply.__str__())

                    conn.sendall(reply)

            # came out of loop
            conn.close()
            self.closesrv()
            print('Connection with ' + addr[0] + ':' + str(addr[1]) + " closed. EXITING THREAD!")
            exit_thread()

    def gtk_main_quit(self, dialog):
        self.closesrv()
        Gtk.main_quit ()

GTK_TSMain()
# GObject.threads_init()
Gtk.main()
