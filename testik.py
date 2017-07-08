#!/usr/bin/python

'''
ZetCode PyCairo tutorial

This program uses PyCairo to
draw on a window in GTK.

Author: Jan Bodnar
Website: zetcode.com
Last edited: April 2016
'''
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, cairo
# import cairo

GUI_file = "./gui_artifacts/Testik.glade"
# GUI_file = "./gui_artifacts/MainConsole_extended.glade"

class Example(Gtk.Window):
    def __init__(self):
        super(Example, self).__init__()

    #     self.init_ui()
    #
    # def init_ui(self):

        builder = Gtk.Builder()
        builder.add_objects_from_file(GUI_file, ("MainWindow", "DrawingArea"))
        # builder = Gtk.Builder()
        # builder.add_objects_from_file(GUI_file, ("MainWindow", "Adjustement_Port", "Adjustment_Resolution", "Action_StartTestServer"))
        print("GUI file added: ", GUI_file)

        self.window = builder.get_object("MainWindow")
        self.drawingarea = builder.get_object("DrawingArea")
        print("drawingarea", self.drawingarea)
        # self.window.show()
        # self.drawingarea.show()

        self.drawingarea.set_can_default(True)
        self.drawingarea.set_can_focus(True)
        self.drawingarea.set_sensitive(True)
        self.drawingarea.set_app_paintable(True)
        self.drawingarea.set_size_request(400, 200)
        # drawingarea.connect("draw", self.on_draw)
        # self.window.add(self.drawingarea)
        # self.drawingarea.realize()

        self.set_title("GTK window test")
        self.resize(406, 206)
        self.set_position(Gtk.WindowPosition.CENTER)
        self.connect("delete-event", Gtk.main_quit)
        self.connect("draw", self.on_draw)
        self.drawingarea.connect("button-press-event", self.on_draw1)
        self.show_all()
        # self.drawingarea.draw()

        builder.connect_signals(self)


    def on_draw1(self, wid, cr):
        print("XXXXXXXXXXXXXXXXXXXXXXXXXXXX")

    def on_draw(self, wid, cr):
        print("****************************")
        cr.set_source_rgb(100, 0, 10)
        cr.select_font_face("Sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
        cr.set_font_size(50)

        cr.move_to(10, 50)
        cr.show_text("TralalaLALA")


def main():
    app = Example()
    Gtk.main()


if __name__ == "__main__":
    main()
