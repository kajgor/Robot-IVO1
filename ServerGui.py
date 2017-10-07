#!/usr/bin/env python3.5
# -*- coding: CP1252 -*-
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GLib

from Common_vars import TIMEOUT_GUI
from ServerLib import *


class GtkTsMain(Gtk.Window):

    Main_Box   = ["MainBox_TSRV", "MainBox_TSRH"]
    Sw_Start   = ["Switch_ServerStartV", "Switch_ServerStartH"]
    SB_Server  = ["StatusBar_TestServerV", "StatusBar_TestServerH"]
    TV_Console = ["TextView_ConsoleV", "TextView_ConsoleH"]

    def __init__(self, POSITION):
        self.Thread_Manager = None
        self.Thread_ID = None

        builder = self.init_GUI(POSITION)

        self.switch_ServerStart   = builder.get_object(self.Sw_Start[POSITION])
        self.StatusBar_Server     = builder.get_object(self.SB_Server[POSITION])
        self.TextView_Console     = builder.get_object(self.TV_Console[POSITION])

        self.context_id           = self.StatusBar_Server.get_context_id("message")
        self.TextView_Console.override_color(Gtk.StateType.NORMAL, Gdk.RGBA(1, .75, 0, 1))
        self.TextView_Console.override_background_color(Gtk.StateType.NORMAL, Gdk.RGBA(.15, 0.15, 0.15, 1))

        self.show_all()
        builder.connect_signals(self)

        Gtk.main()

    def init_Thread(self):
        self.Thread_Manager = ThreadManager(self.TextView_Console)
        self.Thread_Manager.shutdown_flag = False

    def init_GUI(self, POSITION):
        super(GtkTsMain, self).__init__()
        builder = Gtk.Builder()
        # builder.add_from_file(GUI_file)
        builder.add_objects_from_file(Paths.GUI_file, (self.Main_Box[POSITION], self.SB_Server[POSITION],
                                      self.TV_Console[POSITION], self.Sw_Start[POSITION]))
        print("GUI file %s loaded. " % Paths.GUI_file)

        self.add(builder.get_object(self.Main_Box[POSITION]))
        self.set_resizable(False)
        self.set_destroy_with_parent(True)
        # self.set_deletable(False)

        self.set_title("ROBOT SERVER")
        # self.set_title(self.Main_Box[POSITION])
        self.connect("destroy", self.gtk_main_quit)
        self.connect("delete-event", Gtk.main_quit)

        return builder

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

            # if self.Thread_Manager.shutdown_flag is None:
            #     print("remove GLIB")
            #     GLib.source_remove(self.Thread_ID)

            # self.set_deletable(True)
            self.StatusBar_Server.push(self.context_id, "Port " + Port_COMM.__str__() + " closed.")

        self.show_all()

    def gtk_main_quit(self, dialog):
        self.Thread_Manager.ProgramExit()
        Gtk.main_quit()

GtkTsMain(VERTICAL)

exit(0)
