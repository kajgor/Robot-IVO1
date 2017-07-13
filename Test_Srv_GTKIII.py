# !/usr/bin/env python

import sys
import gi
gi.require_version('Gst', '1.0')
gi.require_version('Gtk', '3.0')
gi.require_version('GstVideo', '1.0')
from gi.repository import Gst, GObject, Gtk, GstVideo

import atexit
# GUI_file = "./gui_artifacts/TestServer_extended.glade"
GUI_file = "./gui_artifacts/MainConsole_extended.glade"

try:
    Pread = sys.argv[1]
except:
    Pread = None

if Pread is None:
    WinType = Gtk.Window
else:
    WinType = Gtk.ApplicationWindow

print("Par1: ", Pread.__str__())

class GTK_TSMain(WinType):
    Gst.init(None)
    player = Gst.Pipeline.new("player")
    Host = "localhost"
    Port = 12344

    def __init__(self):
        super(GTK_TSMain, self).__init__()
        atexit.register(self.closesrv)

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

        self.source = Gst.ElementFactory.make("videotestsrc", "video-source")
        self.source.set_property("pattern", "smpte")

        self.sink = Gst.ElementFactory.make("tcpserversink", "video-output")
        self.sink.set_property("host", self.Host)
        self.sink.set_property("port", self.Port)

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

    def closesrv(self):
        print("Closing socket[*]")
        self.player.set_state(Gst.State.NULL)

    def on_Switch_ServerStart_activate(self, widget, event):
        if self.switch_ServerStart.get_active() is True:
            print("Opening socket[+]")
            self.player.set_state(Gst.State.PLAYING)
            self.statusbar_TestServer.push(self.context_id, "Streaming on port " + self.Port.__str__())
        else:
            self.statusbar_TestServer.push(self.context_id, "Port " + self.Port.__str__() + " closed.")
            self.closesrv()

    def gtk_main_quit(self, dialog):
        Gtk.main_quit ()

GTK_TSMain()
# GObject.threads_init()
Gtk.main()
