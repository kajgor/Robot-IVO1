#!/usr/bin/env python3
# -*- coding: CP1252 -*-
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GLib

from ServerLib import *
from sys import argv


class GtkTsMain(Gtk.Window):

    Main_Box   = ["MainBox_TSRV", "MainBox_TSRH"]
    Sw_Start   = ["Switch_ServerStartV", "Switch_ServerStartH"]
    SB_Server  = ["StatusBarV", "StatusBarH"]
    TV_Console = ["TextView_ConsoleV", "TextView_ConsoleH"]
    LB_Voltage = ["LevelBar_VoltageV", "LevelBar_VoltageH"]
    LB_Current = ["LevelBar_CurrentV", "LevelBar_CurrentH"]

    def __init__(self, POSITION):
        self.Thread_Manager = None
        self.Thread_ID = None

        builder = self.init_GUI(POSITION)
        builder.connect_signals(self)

        self.switch_ServerStart   = builder.get_object(self.Sw_Start[POSITION])
        self.StatusBar_Server     = builder.get_object(self.SB_Server[POSITION])
        self.TextView_Console     = builder.get_object(self.TV_Console[POSITION])
        self.Level_Voltage        = builder.get_object(self.LB_Voltage[POSITION])
        self.Level_Current        = builder.get_object(self.LB_Current[POSITION])
        self.Window_Setup         = builder.get_object("Window_Setup")
        self.ComboBoxText_Cam1    = builder.get_object("ComboBoxText_Cam1")
        self.ComboBoxText_AudioIn = builder.get_object("ComboBoxText_AudioIn")
        self.ComboBoxText_AudioOut= builder.get_object("ComboBoxText_AudioOut")
        self.SpinButton_Port      = builder.get_object("SpinButton_Port")

        tmp, tmp, tmp, self.Port_COMM, tmp, tmp = load_setup()
        if self.Port_COMM:
            self.SpinButton_Port.set_value(self.Port_COMM)

        self.context_id           = self.StatusBar_Server.get_context_id("message")
        self.TextView_Console.override_color(Gtk.StateType.NORMAL, Gdk.RGBA(1, .75, 0, 1))
        self.TextView_Console.override_background_color(Gtk.StateType.NORMAL, Gdk.RGBA(.15, 0.15, 0.15, 1))

        self.load_devices()

        self.show_all()
        self.process_argv()

    def init_Thread(self):
        self.Thread_Manager = ThreadManager(self.TextView_Console, self.Port_COMM, self.Level_Voltage, self.Level_Current,
                                            self.switch_ServerStart)
        self.Thread_Manager.shutdown_flag = False

    def init_GUI(self, POSITION):
        super(GtkTsMain, self).__init__()
        builder = Gtk.Builder()
        builder.add_objects_from_file(Paths.GUI_file, (self.Main_Box[POSITION], self.SB_Server[POSITION],
                                      self.TV_Console[POSITION], self.Sw_Start[POSITION], "Window_Setup",
                                      self.LB_Voltage[POSITION], self.LB_Current[POSITION], "Adjustement_Port"))
        print("GUI file %s loaded. " % Paths.GUI_file)

        self.add(builder.get_object(self.Main_Box[POSITION]))
        self.set_resizable(False)
        self.set_destroy_with_parent(True)

        self.set_title("* ROBOT SERVER *")
        self.set_icon_from_file("./icons/robot_icon_24x24.png")
        self.connect("destroy", self.gtk_main_quit)
        self.connect("delete-event", self.gtk_main_quit)

        return builder

    def process_argv(self):
        for x in range(1, len(argv)):
            if argv[x] == "start":
                self.switch_ServerStart.set_active(True)
            else:
                print("Invalid arument:", argv[x])

    def load_devices(self):
        Cam0, MicIn, SpkOut, Port_Comm, tmp, tmp = load_setup()

        fail = self.set_device(CAM_1_CMD, self.ComboBoxText_Cam1, Cam0)
        fail += self.set_device(DEV_INP_CMD, self.ComboBoxText_AudioIn, MicIn)
        fail += self.set_device(DEV_OUT_CMD, self.ComboBoxText_AudioOut, SpkOut)

        if fail > 0:
            Console.print("Warning: Some devices are missing!")

    def set_device(self, CMD, widget, DevToMatch):
        active_item = 0
        if DevToMatch is None:
            Console.print("Warning: %s device not setup yet!" % Gtk.Buildable.get_name(widget).split('_')[1])

        LsDev = Gtk.ListStore(str, int)
        detected_devices, err = execute_cmd(CMD)

        if detected_devices > "":
            for idx, DevName in enumerate(detected_devices.splitlines()):
                if DevName.find(":") == -1:
                    Dev = DevName
                else:
                    Dev = DevName.split(':')[1]

                if Dev == DevToMatch:
                    active_item = idx
                LsDev.append((DevName, idx))
            widget.set_model(LsDev)

            widget.set_active(active_item)

            return False
        else:
            return True

    def on_Switch_ServerStart_activate(self, widget, event):
        if widget.get_active() is True:  # and ClientThread.srv is None:
            self.Port_COMM = self.SpinButton_Port.get_value_as_int()
            if self.Thread_ID is not None:
                GLib.source_remove(self.Thread_ID)

            self.init_Thread()

            ####### Main loop definition ###############
            self.Thread_ID = GLib.timeout_add(TIMEOUT_GUI * 4, self.Thread_Manager.run)
            ############################################

            self.StatusBar_Server.push(self.context_id, "Port %i open!" % self.Port_COMM)
            # self.set_deletable(False)
        else:
            if self.Thread_Manager.shutdown_flag is False:
                self.Thread_Manager.shutdown_flag = True

            # self.set_deletable(True)
            self.StatusBar_Server.push(self.context_id, "Port %i closed." % self.Port_COMM)

        self.show_all()

    def on_Button_Setup_clicked(self, widget):
        self.Window_Setup.show()

    def on_Window_Setup_delete_event(self, widget, *message):
        self.save_setup()
        self.Window_Setup.hide()
        return True

    def save_setup(self):
        CMD = "echo -n > " + Paths.ini_file
        execute_cmd(CMD)
        for OutStr in ("CAM0\t" + str(self.ComboBoxText_Cam1.get_active_text()),
                    "MIC0\t" + str(self.ComboBoxText_AudioIn.get_active_text()),
                    "SPK0\t" + str(self.ComboBoxText_AudioOut.get_active_text()),
                    "IPP0\t" + str(self.ComboBoxText_AudioOut.get_active_text()),
                    "PORT\t" + str(self.SpinButton_Port.get_value_as_int()),
                    "PRG_CONN_BEGIN /usr/bin/xscreensaver-command -exit",
                    "PRG_CONN_END /usr/bin/xscreensaver -no-splash &"):
            CMD = "echo " + OutStr + " >> " + Paths.ini_file
            execute_cmd(CMD)

    def gtk_main_quit(self, *args):
        if self.switch_ServerStart.get_active() is True:
            self.switch_ServerStart.set_active(False)
            self.Thread_Manager.ProgramExit(249)
            while Gtk.events_pending():
                time.sleep(0.5)
                Gtk.main_iteration()
            time.sleep(1)
        Gtk.main_quit()


if __name__ == "__main__":
    GtkTsMain(VERTICAL)
    Gtk.main()

exit(0)
