# !/usr/bin/env python

import gi

gi.require_version("Gst", "1.0")
from gi.repository import Gst, GObject, Gtk

import atexit

class GTK_Main:
    def __init__(self):
        atexit.register(self.closesrv)

        window = Gtk.Window(Gtk.WindowType.TOPLEVEL)
        window.set_title("Videotestsrc-SERVER")
        window.set_default_size(250, 75)
        window.connect("destroy", Gtk.main_quit, "WM destroy")
        vbox = Gtk.VBox()
        window.add(vbox)
        self.button = Gtk.Button("Start")
        self.button.connect("clicked", self.start_stop)
        vbox.add(self.button)
        window.show_all()

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
        # self.player.add(self.encoder)
        # self.player.add(self.sink)

        self.source.link(self.filter)
        self.filter.link(self.encoder)
        self.encoder.link(self.sink)

    def closesrv(self):
        print("Closing socket[*]")
        self.player.set_state(Gst.State.NULL)

    def start_stop(self, w):
        if self.button.get_label() == "Start":
            print("Opening socket[+]")
            self.button.set_label("*** STOP ***")
            self.player.set_state(Gst.State.PLAYING)
        else:
            self.closesrv()
            self.button.set_label("Start")

GObject.threads_init()
Gst.init(None)
GTK_Main()
Gtk.main()