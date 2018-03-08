#!/usr/bin/env python3.5
# -*- coding: CP1252 -*-
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GLib

from ServerLib import *
from sys import argv


class GtkTsMain(Gtk.Window):

    Main_Box   = ["MainBox_TSRV", "MainBox_TSRH"]
    Sw_Start   = ["Switch_ServerStartV", "Switch_ServerStartH"]
    SB_Server  = ["StatusBar_TestServerV", "StatusBar_TestServerH"]
    TV_Console = ["TextView_ConsoleV", "TextView_ConsoleH"]

    def __init__(self, POSITION):
        self.Thread_Manager = None
        self.Thread_ID = None

        builder = self.init_GUI(POSITION)
        builder.connect_signals(self)

        self.switch_ServerStart   = builder.get_object(self.Sw_Start[POSITION])
        self.StatusBar_Server     = builder.get_object(self.SB_Server[POSITION])
        self.TextView_Console     = builder.get_object(self.TV_Console[POSITION])
        self.Window_Setup         = builder.get_object("Window_Setup")
        self.ComboBoxText_Cam1    = builder.get_object("ComboBoxText_Cam1")
        self.ComboBoxText_AudioIn = builder.get_object("ComboBoxText_AudioIn")
        self.ComboBoxText_AudioOut= builder.get_object("ComboBoxText_AudioOut")

        self.context_id           = self.StatusBar_Server.get_context_id("message")
        self.TextView_Console.override_color(Gtk.StateType.NORMAL, Gdk.RGBA(1, .75, 0, 1))
        self.TextView_Console.override_background_color(Gtk.StateType.NORMAL, Gdk.RGBA(.15, 0.15, 0.15, 1))

        self.load_devices()

        self.show_all()
        self.process_argv()

    def init_Thread(self):
        self.Thread_Manager = ThreadManager(self.TextView_Console)
        self.Thread_Manager.shutdown_flag = False

    def init_GUI(self, POSITION):
        super(GtkTsMain, self).__init__()
        builder = Gtk.Builder()
        builder.add_objects_from_file(Paths.GUI_file, (self.Main_Box[POSITION], self.SB_Server[POSITION],
                                      self.TV_Console[POSITION], self.Sw_Start[POSITION], "Window_Setup"))
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
        Cam0, MicIn, SpkOut = load_setup()

        item = None
        LsDev1 = Gtk.ListStore(str, int)
        DEV_LIST = execute_cmd(CAM_1_CMD).decode(Encoding)
        for idx, DevName in enumerate(DEV_LIST.splitlines()):
            LsDev1.append((DevName, idx))
            if DevName == Cam0.split(' ')[1]:
                item = LsDev1.iter_n_children() - 1
        self.ComboBoxText_Cam1.set_model(LsDev1)
        if item is not None:
            self.ComboBoxText_Cam1.set_active(item)

        item = None
        LsDev2 = Gtk.ListStore(str, int)
        DEV_LIST = execute_cmd(DEV_INP_CMD).decode(Encoding)
        for idx, DevName in enumerate(DEV_LIST.splitlines()):
            LsDev2.append((DevName, idx))
            if DevName == MicIn.split(' ')[1]:
                item = LsDev2.iter_n_children() - 1
        self.ComboBoxText_AudioIn.set_model(LsDev2)
        if item is not None:
            self.ComboBoxText_AudioIn.set_active(item)

        item = None
        LsDev3 = Gtk.ListStore(str, int)
        DEV_LIST = execute_cmd(DEV_OUT_CMD).decode(Encoding)
        for idx, DevName in enumerate(DEV_LIST.splitlines()):
            LsDev3.append((DevName, idx))
            if DevName == SpkOut.split(' ')[1]:
                item = LsDev3.iter_n_children() - 1
        self.ComboBoxText_AudioOut.set_model(LsDev3)
        if item is not None:
            self.ComboBoxText_AudioOut.set_active(item)

    def on_Button_Setup_clicked(self, widget):
        self.Window_Setup.show()

    def on_Switch_ServerStart_activate(self, widget, event):
        if widget.get_active() is True:  # and ClientThread.srv is None:
            if self.Thread_ID is not None:
                GLib.source_remove(self.Thread_ID)

            self.init_Thread()

            ####### Main loop definition ###############
            self.Thread_ID = GLib.timeout_add(TIMEOUT_GUI, self.Thread_Manager.run)
            ############################################

            self.StatusBar_Server.push(self.context_id, "Port " + Port_COMM.__str__() + " open!")
            # self.set_deletable(False)
        else:
            if self.Thread_Manager.shutdown_flag is False:
                self.Thread_Manager.shutdown_flag = True

            # self.set_deletable(True)
            self.StatusBar_Server.push(self.context_id, "Port " + Port_COMM.__str__() + " closed.")

        self.show_all()

    def on_Window_Setup_delete_event(self, bus, message):
        self.save_setup()
        self.Window_Setup.hide()
        return True

    def save_setup(self):
        OutStr = "CAM0\t" + str(self.ComboBoxText_Cam1.get_active_text())
        CMD = "echo " + OutStr + " > " + Paths.ini_file
        execute_cmd(CMD)
        OutStr = "MIC0\t" + str(self.ComboBoxText_AudioIn.get_active_text())
        CMD = "echo " + OutStr + " >> " + Paths.ini_file
        execute_cmd(CMD)
        OutStr = "SPK0\t" + str(self.ComboBoxText_AudioOut.get_active_text())
        CMD = "echo " + OutStr + " >> " + Paths.ini_file
        execute_cmd(CMD)

    def gtk_main_quit(self, *args):
        if self.switch_ServerStart.get_active() is True:
            self.switch_ServerStart.set_active(False)
            self.Thread_Manager.ProgramExit()
            time.sleep(1)
        Gtk.main_quit()


if __name__ == "__main__":
    GtkTsMain(VERTICAL)
    Gtk.main()

exit(0)
