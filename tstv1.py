import sys, os
import pygtk, gtk, gobject
import pygst
import gst
gst.require("0.10")
import wx


class Frame(wx.Frame):
    """Frame class that displays an image."""

    def __init__(self, parent=None, id=-1,
                 pos=wx.DefaultPosition, title='Hello, wxPython!'):
        wx.Frame.__init__(self, parent, id, title, pos, (400, 300))
        # self.windows = wx.PaintDC(self)
        self.Bind(wx.EVT_CLOSE, self.OnCloseWindow)
        self.player = gst.parse_launch("v4l2src ! autovideosink")
        bus = self.player.get_bus()
        bus.add_signal_watch()
        bus.enable_sync_message_emission()
        bus.connect("message", self.on_message)
        bus.connect("sync-message::element", self.on_sync_message)
        self.player.set_state(gst.STATE_PLAYING)

    def OnCloseWindow(self, event):
        self.player.set_state(gst.STATE_NULL);
        event.Skip()

    def on_message(self, bus, message):
        t = message.type
        if t == gst.MESSAGE_EOS:
            self.player.set_state(gst.STATE_NULL)
        elif t == gst.MESSAGE_ERROR:
            err, debug = message.parse_error()
            print "Error: %s" % err, debug
            self.player.set_state(gst.STATE_NULL)

    def on_sync_message(self, bus, message):
        if message.structure is None:
            return
        message_name = message.structure.get_name()
        if message_name == "prepare-xwindow-id":
            # Assign the viewport  
            imagesink = message.src
            imagesink.set_property("force-aspect-ratio", True)
            imagesink.set_xwindow_id(self.GetHandle())


class App(wx.App):
    """Application class."""

    def OnInit(self):
        self.frame = Frame()
        self.frame.Show()
        self.SetTopWindow(self.frame)
        return True


def main():
    gtk.gdk.threads_init()
    app = App()
    app.MainLoop()


if __name__ == '__main__':
    main()

