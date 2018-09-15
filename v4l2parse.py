#!/usr/bin/env python2
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk

from Common_vars import v4lparse

x_list = v4lparse('/dev/video0')

# print(list)
# print(x_list[0])
# print(x_list[1])

# exit(0)

# contrast = 'contrast=30'
# brightness = 'brightness=0'
#
# v4l2parse('/dev/video0', contrast, brightness)


class MyWindow(Gtk.Window):
    def __init__(self):
        Gtk.Window.__init__(self, title="v4l2 Setup")

        grid = None
        notebook = Gtk.Notebook()
        notebook.set_name('v4l2parse')
        # self.grid.set_valign(Gtk.Align.FILL)
        # self.grid.set_halign(Gtk.Align.FILL)

        for x, x_line in enumerate(x_list):
            print(x_line)
            if type(x_line) is list:
                x_name = x_line[0]
                x_code = x_line[1]
                x_type = x_line[2]
                if x_type == '(int)':
                    x_min       = int(x_line[4].split("=")[1])
                    x_max       = int(x_line[5].split("=")[1])
                    x_step      = int(x_line[6].split("=")[1])
                    x_default   = int(x_line[7].split("=")[1])
                    x_value     = int(x_line[8].split("=")[1])

                    # Make Label
                    widget = self.create_label_widget(x_name)
                    grid.add(widget)

                    # Make Slider
                    adjustment = self.get_adjustment_widget(x_min, x_max, x_step, x_default, x_value)
                    widget = self.create_scale_widget(x_name, adjustment)
                    widget.set_digits(0)
                    # self.grid.set_row_spacing(20)
                    setattr(self, x_code, widget)
                    grid.add(widget)

                elif x_type == '(menu)':
                    pass
            else:
                # Create New Tab
                x_name = x_line
                grid = Gtk.Grid(orientation=1)
                grid.set_margin_top(10)
                grid.set_margin_left(10)
                grid.set_margin_right(10)
                grid.set_margin_bottom(5)
                notebook.append_page(grid)
                notebook.set_tab_label_text(grid, x_name)

        # self.button1 = Gtk.Button(label="Hello")
        # self.grid.add(self.button1)
        # self.button1.connect("clicked", self.on_button1_clicked)
        # self.box.pack_start(self.button1, True, True, 0)

        # self.button2 = Gtk.Button(label="Goodbye")
        # self.grid.add(self.button2)
        # self.button2.connect("clicked", self.on_button2_clicked)
        # self.box.pack_start(self.button2, True, True, 0)
        # self.notebook.add(self.grid)
        self.add(notebook)

    def on_button1_clicked(self, widget):
        print("Hello")

    def on_button2_clicked(self, widget):
        print("Goodbye")

    def create_label_widget(self, x_name):
        # widget_name = 'Label_Cam_%s' % x_name
        widget = Gtk.Label()
        widget.set_name(x_name)
        widget.set_text(x_name)
        return widget

    def create_scale_widget(self, x_name, adjustment):
        # widget_name = 'Scale_Cam_%s' % x_name
        widget = Gtk.Scale(orientation=Gtk.Orientation.HORIZONTAL, adjustment=adjustment)
        widget.set_margin_bottom(15)
        widget.set_name(x_name)
        return widget

    def get_adjustment_widget(self, x_min, x_max, x_step, x_default, x_value):
        widget = Gtk.Adjustment(x_default, x_min, x_max, x_step, x_step, 0)
        widget.set_value(x_value)
        return widget

win = MyWindow()
win.connect("destroy", Gtk.main_quit)
win.show_all()
Gtk.main()