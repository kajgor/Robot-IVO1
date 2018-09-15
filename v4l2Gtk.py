#!/usr/bin/env python2
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk

from subprocess import call, Popen, CalledProcessError, TimeoutExpired, PIPE

def get_command_output(cmd_string):
    try:
        proc = Popen(cmd_string, shell=True, stdout=PIPE)
    except CalledProcessError:
        return None

    try:
        stdout, errs = proc.communicate(timeout=3)
    except TimeoutExpired:
        proc.kill()
        stdout, errs = proc.communicate()

    if not (str(stdout).isdigit()):  # Not numeric string
        stdout = stdout.decode('latin1')
        if stdout > '':
            if stdout[-1] == chr(10):
                stdout = stdout[0:-1]  # Do not return CR
            elif stdout[-1] == chr(13):
                stdout = stdout[0:-1]  # Do not return NL

    return stdout

def v4lparse(device, *args):
    if args:
        for arg in args:
            if device:
                call('v4l2-ctl -d %s -c ' % device + arg, shell=True)
            else:
                call('v4l2-ctl -c %s' % arg, shell=True)
    else:
        tmp_line = None
        out_list = []
        if device:
            # sss = get_command_output('v4l2-ctl -L')
            v4l2_prop_txt = get_command_output('v4l2-ctl -L -d %s' % device)
            # v4l2_prop_txt, err = execute_cmd('cat ./v4l2-ctl-server.txt')
        else:
            v4l2_prop_txt = get_command_output('v4l2-ctl -L')

        prop_list = v4l2_prop_txt.split('\n')
        prop_list.append(": .\n")  # Spool out last line of the list with that string
        if ":" in prop_list[0]:
            prop_list.insert(0, "Defaults")

        for i_line in prop_list:
            if not i_line:
                continue
            i_line = i_line.strip()
            if ":" in i_line:
                if i_line.split()[0][-1] == ":":
                    tmp_line.append(i_line.split(": "))
                else:
                    if tmp_line is not None:
                        out_list.append(tmp_line)

                    tmp_line = i_line.split()

                    if tmp_line[1][-2:] == '):':  # In order to process '(intmenu):' string
                        tmp_line[1] = tmp_line[1][0:-1]
                        tmp_line.insert(2, ":")
            else:
                out_list.append(i_line)

        return out_list


class v4l2Gtk():
    def v4l2Gtk(self):
        # def __init__(self):
    #     Gtk.Window.__init__(self, title='v4l2 Setup')

        # self.grid.set_halign(Gtk.Align.FILL)

        x_pos = 0
        x_add_tab = 1
        x_list = v4lparse('/dev/video0')
        self.notebook = Gtk.Notebook()
        self.notebook.set_name('v4l2parse')

        for x, x_line in enumerate(x_list):
            if type(x_line) is list:
                if x_pos >= 19:
                    x_pos = 0
                    x_add_tab += 1
                    grid = self.create_grid()
                    self.create_new_tab(tab_name + str(x_add_tab), grid)

                x_name = x_line[0]
                x_code = x_line[1]
                if x_code[0:2] == '0x':
                    x_code = x_name
                    x_shift = 1
                    x_type = x_line[2]
                else:
                    x_shift = 0
                    x_type = x_code
                    x_code = x_name

                if x_type == '(int)':
                    x_min       = int(x_line[3 + x_shift].split("=")[1])
                    x_max       = int(x_line[4 + x_shift].split("=")[1])
                    x_step      = int(x_line[5 + x_shift].split("=")[1])
                    x_default   = int(x_line[6 + x_shift].split("=")[1])
                    x_value     = int(x_line[7 + x_shift].split("=")[1])

                    # Make Label
                    widget = self.create_label_widget(x_name)
                    grid.attach(widget, 1, x_pos, 1, 1)

                    # Make button
                    widget = self.create_default_button(x_code, x_default)
                    grid.attach(widget, 0, x_pos, 1, 2)
                    x_pos += 1

                    # Make Slider
                    adjustment = self.create_adjustment_widget(x_min, x_max, x_step, x_default, x_value)
                    widget = self.create_scale_widget(x_name, adjustment, 300, None)
                    setattr(self, str(x_code) + '_widget', widget)
                    grid.attach(widget, 1, x_pos, 1, 1)
                    x_pos += 1

                elif x_type == '(bool)':
                    print('bool')
                    x_default   = int(x_line[3 + x_shift].split("=")[1])
                    x_value     = int(x_line[4 + x_shift].split("=")[1])

                    widget = self.create_check_button(x_name, x_code, x_value)
                    # setattr(self, str(x_code) + '_widget', widget)
                    grid.attach(widget, 1, x_pos, 1, 1)
                    x_pos += 1
                    pass

                elif x_type[-5:] == 'menu)':
                    print(x_line)
                    # x_min       = int(x_line[3 + x_shift].split("=")[1])
                    # x_max       = int(x_line[4 + x_shift].split("=")[1])
                    x_default   = int(x_line[5 + x_shift].split("=")[1])
                    x_value     = int(x_line[6 + x_shift].split("=")[1])

                    # Make Label
                    widget = self.create_label_widget(x_name)
                    grid.attach(widget, 1, x_pos, 1, 1)

                    # Make button
                    widget = self.create_default_button(x_code, x_default)
                    grid.attach(widget, 0, x_pos, 1, 2)
                    x_pos += 1

                    widget = self.create_combobox(x_name, x_value, x_line[7:])
                    setattr(self, str(x_code) + '_widget', widget)
                    grid.attach(widget, 1, x_pos, 1, 1)
                    x_pos += 1

            else:
                x_pos = 0
                grid = self.create_grid()
                tab_name = self.create_new_tab(x_line, grid)

        # self.add(self.notebook)
        # self.set_property('default-width', 300)

        return self.notebook

    def create_new_tab(self, x_line, grid):
        # Create New Tab
        self.notebook.append_page(grid)
        x_name = x_line
        if x_name is not None:
            x_name = x_name.split()
            print('tab_name %s' % x_name)
            if len(x_name) == 3:
                x_name[1] = x_name[1][0:4] + "." + x_name[2][0:4] + "."
                x_name = x_name[:-1]

            x_name = " ".join(x_name)
            self.notebook.set_tab_label_text(grid, x_name.replace(" ", "\n"))

        return x_name

    def on_button_clicked(self, widget):
        if ";" in widget.get_name():
            x_code, x_default = widget.get_name().split(";")
        else:
            x_code = widget.get_name()

        if type(widget) == Gtk.CheckButton:
            state = int(widget.get_active())
            v4lparse(None, x_code + "=" + str(state))
            # print(x_code, state)
        else:
            x_widget = getattr(self, str(x_code) + '_widget')
            if type(x_widget) == Gtk.ComboBox:
                # tree_iter = widget.get_active_iter()
                model = x_widget.get_model()
                for cx, item in enumerate(model):
                    if int(model[cx][0]) == int(x_default):
                        x_widget.set_active(int(cx))
            elif type(x_widget) == Gtk.Scale:
                x_widget.set_value(int(x_default))

    def create_combobox(self, x_name, x_value, x_line):
        print('combobox %s' % x_line)
        combobox_list = Gtk.ListStore(str, str)
        for _value in x_line:
            if type(_value) is list:
                print(_value)
                _value[1] = _value[1].split()[0]
                combobox_list.append(_value)

        combobox = Gtk.ComboBox.new_with_model(combobox_list)
        combobox.set_property('width-request', 100)
        renderer_text = Gtk.CellRendererText()
        combobox.pack_start(renderer_text, True)
        combobox.add_attribute(renderer_text, 'text', 1)
        combobox.set_margin_top(5)
        combobox.set_margin_bottom(13)
        combobox.set_margin_right(40)
        combobox.connect("changed", self.on_combobox_changed)
        combobox.set_name(str(x_name))

        model = combobox.get_model()
        for cx, item in enumerate(model):
            if int(model[cx][0]) == int(x_value):
                combobox.set_active(int(cx))
        return combobox

    def on_combobox_changed(self, widget):
        tree_iter = widget.get_active_iter()
        x_name = widget.get_name()
        if tree_iter is not None:
            model = widget.get_model()
            x_item = model[tree_iter][0]
            print("Selected: combomenu=%s" % x_item)
            v4lparse(None, x_name + "=" + str(x_item))

    def on_scale_changed(self, widget):
        x_name = widget.get_name()
        x_value = widget.get_value()
        # print("Set: scale=%s" % x_value)
        v4lparse(None, x_name + "=" + str(x_value))

    def create_default_button(self, x_code, x_default):
        button = Gtk.Button(label='Default')
        button.set_margin_top(5)
        button.set_margin_right(10)
        # button.set_margin_left(10)
        # button.set_margin_bottom(5)
        button.set_valign(Gtk.Align.CENTER)

        button.set_name(str(x_code) + ";" + str(x_default))
        button.connect('clicked', self.on_button_clicked)
        return button

    def create_check_button(self, x_name, x_code, x_value):
        button = Gtk.CheckButton(label=x_name.replace("_", " "))
        button.set_margin_top(5)
        # button.set_margin_left(10)
        button.set_margin_right(40)
        button.set_margin_bottom(10)
        button.set_name(str(x_code))
        button.set_active(x_value)
        button.connect('clicked', self.on_button_clicked)
        return button

    def create_grid(self):
        grid = Gtk.Grid(orientation=1)
        grid.set_margin_top(10)
        grid.set_margin_left(15)
        grid.set_margin_right(15)
        grid.set_margin_bottom(5)
        grid.set_valign(Gtk.Align.FILL)
        grid.set_halign(Gtk.Align.CENTER)
        return grid

    def create_label_widget(self, x_name):
        label = Gtk.Label()
        label.set_name(x_name)
        label.set_text(x_name.replace("_", " "))
        return label

    def create_scale_widget(self, x_name, adjustment, width, precision):
        if precision is None:
            precision = 0
        if width is None:
            width = 250

        scale = Gtk.Scale(orientation=Gtk.Orientation.HORIZONTAL, adjustment=adjustment)
        scale.set_margin_bottom(15)
        scale.set_property('value-pos', 1)
        scale.set_property('width-request', width)
        scale.set_digits(precision)
        scale.connect('value-changed', self.on_scale_changed)
        scale.set_name(x_name)
        return scale

    def create_adjustment_widget(self, x_min, x_max, x_step, x_default, x_value):
        adjustment = Gtk.Adjustment(x_default, x_min, x_max, x_step, x_step, 0)
        adjustment.set_value(x_value)
        return adjustment

# Main_Win = v4l2Gtk()
# Main_Win.connect("destroy", Gtk.main_quit)
# Main_Win.show_all()
# Gtk.main()