#!/usr/bin/python3.5
import gi, os
gi.require_version('Gst', '1.0')
gi.require_version('Gtk', '3.0')
gi.require_version('GstVideo', '1.0')
from gi.repository import Gst, GObject, Gtk, GstVideo


class GTK_main(object):
    def  __init__(self):
        window = Gtk.Window(Gtk.WindowType.TOPLEVEL)
        window.set_title("Audio-Player")
        window.set_default_size(300, -1)
        window.connect("destroy", Gtk.main_quit, "WM destroy")
        vbox = Gtk.VBox()
        window.add(vbox)
        self.entry = Gtk.Entry()
        vbox.pack_start(self.entry, False, True, 0)
        self.button = Gtk.Button("Start")
        self.button.connect("clicked", self.start_stop)
        vbox.add(self.button)
        window.show_all()

        bus = init_Gstreamer.player.get_bus()
        bus.add_signal_watch()
        bus.connect("message", self.on_message)

    def start_stop(self, w):
        if self.button.get_label() == "Start":
            self.button.set_label("Stop")
            init_Gstreamer.player.set_state(Gst.State.PLAYING)
        else:
            init_Gstreamer.player.set_state(Gst.State.PAUSED)
            self.button.set_label("Start")

    def           on_message(self,           bus,           message):
        t           =           message.type
        if           t           ==           Gst.MessageType.EOS:
            init_Gstreamer.player.set_state(Gst.State.PAUSED)
            self.button.set_label("Start")
        elif           t           ==           Gst.MessageType.ERROR:
            init_Gstreamer.player.set_state(Gst.State.PAUSED)
            err,           debug           =           message.parse_error()
            print("Error:           %s"           %           err,           debug)
            self.button.set_label("Start")


class init_Gstreamer:
# gst-launch-1.0 -v tcpclientsrc host=127.0.0.1 port=4550  ! gdpdepay !  rtph264depay ! avdec_h264 ! videoconvert ! gtksink sync=false
# gst-launch-1.0 -v v4l2src  ! h264parse !  rtph264pay config-interval=1 pt=96 ! gdppay ! tcpserversink host=127.0.0.1 port=4550
    Gst.init(None)
    player = Gst.Pipeline.new("player")
    sink = Gst.ElementFactory.make("glimagesink", None)  # glimagesink(default)/gtksink/cacasink/autovideosink
    # sink = Gst.ElementFactory.make("tcpserversink", "video-output")
    # filter = Gst.ElementFactory.make("capsfilter", "filter")

    def __init__(self):
        self.source = Gst.ElementFactory.make("videotestsrc", "video-source")
        # self.source.set_property("pattern", "smpte")

        self.sink.set_property("sync", False)
        # self.encoder = Gst.ElementFactory.make("gdppay", "encoder")

        self.player.add(self.source)
        # self.player.add(self.filter)
        # self.player.add(self.encoder)
        self.player.add(self.sink)

        # self.source.link(self.filter)
        # self.filter.link(self.encoder)
        # self.encoder.link(self.sink)
        self.player.set_state(Gst.State.READY)

        caps = Gst.Caps.from_string("video/x-raw, width=1280, height=800, framerate=15/1")
        # self.filter.set_property("caps", caps)
        print("caps:", caps)

init_Gstreamer()
GTK_main()
Gtk.main()
while 1:
    pass
