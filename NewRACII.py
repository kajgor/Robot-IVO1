#!/usr/bin/env python
# -*- coding: CP1252 -*-

# import os
# import sys
# import time
from config_rw import *
from class_console import *
import gi
gi.require_version('Gst', '1.0')
gi.require_version('Gtk', '3.0')
gi.require_version('GstVideo', '1.0')
from gi.repository import Gst, GObject, Gtk, GstVideo

from importlib import reload
# from os import system
# from thread import *
# import threading
# import pygame
# from pygame import display, draw, event, mouse, Surface

Rac_connection = RacConnection()
Rac_Uio = RacUio()

Debug = 3
GUI_file = "./gui_artifacts/MainConsole_extended.glade"
cfg_file = "./racII.cfg"

class GTK_Main:
    def __init__(self):
        # Read configuration
        config_read(self, cfg_file)
        # reset_save(cfg_file)

        builder = Gtk.Builder()
        builder.add_objects_from_file(GUI_file, ("MainWindow", "Adjustement_Port", "Adjustment_Resolution", "Action_StartTestServer"))
        print("GUI file added: ", GUI_file)

        self.window = builder.get_object("MainWindow")

        self.movie_window = builder.get_object("DrawingArea_Cam")
        self.movie_window.set_size_request(640, 480)

        self.button_connect = builder.get_object("ToggleButton_Connect")

        self.statusbar = builder.get_object("StatusBar")
        self.context_id = self.statusbar.get_context_id("message")

        self.checkbutton_localtest = builder.get_object("CheckButton_LocalTest")

        self.combobox_host = builder.get_object("ComboBox_Host")
        self.comboboxtext_host = builder.get_object("ComboBoxTextEntry_Host")

        self.spinbutton_port = builder.get_object("SpinButton_Port")

        self.window.show_all()
        self.load_HostList(self.Host)
        builder.connect_signals(self)

        self.TEST_Host = "127.0.0.1"
        self.TEST_Port = 12344
        # self.Host_store = Gtk.ListStore(str)
        self.Host = ''

        if Debug > 1:
            print("Objects:")
            print(builder.get_objects().__str__())

        # --- Gstreamer setup begin ---
        self.player = Gst.Pipeline.new("player")

        bus = self.player.get_bus()
        bus.add_signal_watch()
        bus.enable_sync_message_emission()
        bus.connect("message", self.on_message)
        bus.connect("sync-message::element", self.on_sync_message)

        self.source = Gst.ElementFactory.make("tcpclientsrc", "source")
        self.decoder = Gst.ElementFactory.make("gdpdepay", "decoder")
        self.vconvert = Gst.ElementFactory.make("videoconvert")
        self.sink = Gst.ElementFactory.make("ximagesink", None)
        self.sink.set_property("sync", False)

        if not self.sink or not self.source:
            print("GL elements not available.")
            exit()

        self.player.add(self.source, self.decoder, self.vconvert, self.sink)
        self.source.link(self.decoder)
        self.decoder.link(self.vconvert)
        self.vconvert.link(self.sink)
        # --- Gstreamer setup end ---

    def on_ComboBox_Host_changed(self, widget):
        model = self.combobox_host.get_model()
        Port = model[self.combobox_host.get_active()][1] + "."
        Port = Port[:Port.index('.')]
        self.spinbutton_port.set_value(int(Port))
        print("Changed:", self.combobox_host.get_active(), Port)
        return

    def on_CheckButton_LocalTest_toggled(self, widget):
        if self.checkbutton_localtest.get_active() == True:
            ret = self.HostList_get(self.TEST_Host)
            if self.HostList_get(self.TEST_Host) == False:
                ret = 0
                self.combobox_host.insert(ret, self.TEST_Port.__str__(), self.TEST_Host)

            self.combobox_host.set_active(ret)
            self.spinbutton_port.set_value(self.TEST_Port)
            self.combobox_host.set_sensitive(False)
            self.spinbutton_port.set_sensitive(False)
            try:
                print("try")
                import Test_Srv_GTK
            except:
                print("except")
                reload(Test_Srv_GTK)
        else:
            self.combobox_host.set_sensitive(True)
            self.spinbutton_port.set_sensitive(True)

    def on_ToggleButton_Connect_toggled(self, widget):
        if self.button_connect.get_active() == True:
            self.combobox_host.set_sensitive(False)
            self.checkbutton_localtest.set_sensitive(False)
            self.spinbutton_port.set_sensitive(False)

            if self.checkbutton_localtest.get_active() == True:
                self.source.set_property("host", self.TEST_Host)
                self.source.set_property("port", self.TEST_Port)
            else:
                self.source.set_property("host", self.combobox_host.get_active_text())
                self.source.set_property("port", self.spinbutton_port.get_value())

            ret = self.player.set_state(Gst.State.PLAYING)
            if ret == Gst.StateChangeReturn.FAILURE:
                print("ERROR: Unable to set the pipeline to the playing state")
                self.statusbar.push(self.context_id, "VIDEO CONNECTION ERROR: Unable to set the pipeline to the playing state.")
            else:
                print("VIDEO CONNECTION ESTABILISHED: OK")
                self.statusbar.push(self.context_id, "VIDEO CONNECTION ESTABILISHED: OK")

                list_iter = self.combobox_host.get_active_iter()
                if list_iter is not None:
                    model = self.combobox_host.get_model()
                    Host, Port = model[list_iter][:2]
                    Port = Port[:Port.index('.')]
                    print("Selected: Port=%s, Host=%s" % (int(Port), Host))
                else:
                    entry = self.combobox_host.get_child()
                    self.combobox_host.insert(0, self.spinbutton_port.get_value().__str__(), entry.get_text())
                    self.combobox_host.set_active(0)

                    print("New entry: %s" % entry.get_text())
                    print("New port: %s" % self.spinbutton_port.get_value().__str__())
        else:
            self.player.set_state(Gst.State.NULL)

            self.statusbar.push(self.context_id, "Disconnected.")

            self.button_connect.set_active(False)
            self.checkbutton_localtest.set_sensitive(True)

            if self.checkbutton_localtest.get_active() is False:
                self.combobox_host.set_sensitive(True)
                self.spinbutton_port.set_sensitive(True)

    def on_CheckButton_Speakers_toggled(self, widget):
        return

    def on_CheckButton_Display_toggled(self, widget):
        return

    def on_CheckButton_Lights_toggled(self, widget):
        return

    def on_Button_Preferences_clicked(self, widget):
        print("TEXT IN COMBOBOX: ", self.combobox_host.get_active_text())
        print("NO OF ITEMS:", self.combobox_host.get_model().iter_n_children())
        self.config_snapshot()
        return

    def on_message(self, bus, message):
        t = message.type
        # print ("on_message " + t.__str__())
        if t == Gst.MessageType.EOS:
            self.player.set_state(Gst.State.NULL)
            self.button_connect.set_active(False)
            if Debug > 1:
                self.statusbar.push(self.context_id, "VIDEO CONNECTION EOS: SIGNAL LOST")
                print ("EOS: SIGNAL LOST")

        elif t == Gst.MessageType.ERROR:
            self.player.set_state(Gst.State.NULL)
            err, debug = message.parse_error()
            debug_s = debug.split("\n")
            self.button_connect.set_active(False)
            if Debug > 0:
                self.statusbar.push(self.context_id, debug_s[debug_s.__len__() - 1])
                print ("ERROR:", debug_s)
        return

    def on_sync_message(self, bus, message):
        # print ("on_sync_message " + message.type.__str__())
        if message.get_structure().get_name() == 'prepare-window-handle':
            imagesink = message.src
            imagesink.set_property("force-aspect-ratio", True)
            imagesink.set_window_handle(self.movie_window.get_property('window').get_xid())
        # else:
        #     print("message.get_structure().get_name():", message.get_structure().get_name())

        return

    def HostList_get(self, HostToFind):
        HostList_str = []
        model = self.combobox_host.get_model()
        for iter_x in range(0, model.iter_n_children()):
            if HostToFind is None:
                HostList_str.append(model[iter_x][0] + ":" + model[iter_x][1])
            else:
                if model[iter_x][0] == HostToFind:
                    return iter_x

        if HostToFind is None:
            print("HostList_str: [%d]" % model.iter_n_children(), HostList_str)
            return HostList_str
        else:
            return False

    def config_snapshot(self):
        self.Host = self.HostList_get(None)
# ToDo:
        self.Port_Comm = "5000"
        self.Port_Video = "5001"
        self.Port_Audio = "5002"
        self.Gstreamer_Path = "/usr/bin"

        return

    def load_HostList(self, HostList_str):
        x = 0
        for HostName in HostList_str:
            Host = HostName.split(":")[0]
            Port = HostName.split(":")[1]
            self.combobox_host.insert(x, Port, Host)
            x += 1
            # print("HostName %s > Port/Host:" % HostName, Port, Host)
        return

    def gtk_main_quit(self, dialog):
        self.config_snapshot()
        # config_save(self, cfg_file)
        Gtk.main_quit ()

Gst.init(None)
GTK_Main()
GObject.threads_init()
Gtk.main()
