# !/usr/bin/env python

import gi
gi.require_version('Gst', '1.0')
gi.require_version('Gtk', '3.0')
gi.require_version('GstVideo', '1.0')
from gi.repository import Gst, GObject, Gtk, GstVideo

import atexit
GUI_file = "./gui_artifacts/TestServer_extended.glade"

class GTK_TSMain:
    def __init__(self):
        atexit.register(self.closesrv)

        builder = Gtk.Builder()
        builder.add_from_file(GUI_file)
        # builder.add_objects_from_file(GUI_file, ("TestServerWindow"))
        print("GUI file added: ", GUI_file)

        self.TS_window = Gtk.Window(Gtk.WindowType.TOPLEVEL)
        self.switch_ServerStart = builder.get_object("Switch_ServerStart")
        self.statusbar_TestServer = builder.get_object("StatusBar_TestServer")

        self.TS_window.show_all()
        builder.connect_signals(self)

        self.player = Gst.Pipeline.new("player")

        self.source = Gst.ElementFactory.make("videotestsrc", "video-source")
        self.source.set_property("pattern", "smpte")

        self.sink = Gst.ElementFactory.make("tcpserversink", "video-output")
        self.sink.set_property("host", "127.0.0.1")
        self.sink.set_property("port", 12344)

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

    def on_Switch_ServerStart_activate(self, widget):
        if self.switch_ServerStart.active() is True:
            print("Opening socket[+]")
            self.player.set_state(Gst.State.PLAYING)
        else:
            self.closesrv()

    def gtk_main_quit(self, dialog):
        Gtk.main_quit ()

Gst.init(None)
GTK_TSMain()
GObject.threads_init()
Gtk.main()
