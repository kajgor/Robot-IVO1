#!/usr/bin/env python
# -*- coding: CP1252 -*-

# import os
# import pygame
# import threading
# import sys
# import time

import gi
gi.require_version('Gst', '1.0')
gi.require_version('Gtk', '3.0')
gi.require_version('GstVideo', '1.0')
from gi.repository import GObject, Gtk, Gdk, GdkX11, GLib

from importlib import reload
from init_variables import TIMEOUT_GUI

from config_rw import *
from class_consoleIII import RacConnection, RacUio, RacDisplay

Rac_connection = RacConnection()
# Rac_Display = RacDisplay()
Rac_Uio = RacUio()

Debug = 3
GUI_file = "./gui_artifacts/MainConsole_extended.glade"
cfg_file = "./racII.cfg"


# GObject.threads_init()

class GUI_window(Gtk.Window):
    def __init__(self):
        super(GUI_window, self).__init__()

        # Read configuration
        config_read(self, cfg_file)
        # reset_save(cfg_file)

        GLib.timeout_add(TIMEOUT_GUI, self.on_timer)

        self.init_vars()

        builder = Gtk.Builder()
        builder.add_objects_from_file(GUI_file, ("MainBox_CON", "Adjustement_Port", "Adjustment_Resolution", "Action_StartTestServer"))
        print("GUI file added: ", GUI_file)
        self.add(builder.get_object("MainBox_CON"))
        self.counter                = builder.get_object("counter")
        self.button_connect         = builder.get_object("ToggleButton_Connect")
        self.movie_window           = builder.get_object("DrawingArea_Cam")
        self.checkbutton_localtest  = builder.get_object("CheckButton_LocalTest")
        self.checkbutton_cam        = builder.get_object("CheckButton_Cam")
        self.combobox_host          = builder.get_object("ComboBox_Host")
        self.comboboxtext_host      = builder.get_object("ComboBoxTextEntry_Host")
        self.spinbutton_port        = builder.get_object("SpinButton_Port")
        self.drawingarea_control    = builder.get_object("DrawingArea_Control")
        self.statusbar              = builder.get_object("StatusBar")
        self.context_id             = self.statusbar.get_context_id("message")

        self.init_ui()
        # Connect signals
        builder.connect_signals(self)

        self.load_HostList(self.Host)

        # ToDo
        self.TEST_Host = "127.0.0.1"
        self.TEST_Port = 12344

        if Debug > 1:
            print("Objects:")
            print(builder.get_objects().__str__())

        self.CAMXPROP = self.movie_window.get_property('window')
        print("self.CAMXPROP", self.CAMXPROP)

        bus = Rac_connection.player.get_bus()
        bus.add_signal_watch()
        bus.enable_sync_message_emission()
        bus.connect("message", self.on_cam_message)
        bus.connect("sync-message::element", self.on_cam_sync_message)

    def init_ui(self):
        ###### Initiate UI start ######
        self.connect("destroy", self.gtk_main_quit)
        self.connect("key-press-event", RacUio.on_key_press)
        self.connect("key-release-event", RacUio.on_key_release)
        self.movie_window.set_size_request(640, 480)
        self.drawingarea_control.set_can_default(True)
        self.drawingarea_control.set_can_focus(True)
        self.drawingarea_control.set_sensitive(True)
        self.drawingarea_control.set_app_paintable(True)
        self.drawingarea_control.set_size_request(150, 150)
        ####### Initiate UI end #######
        # self.drawingarea_control.realize()
        # self.CONTROLXPROP = self.drawingarea_control.get_property('window')
        # print("self.CONTROLXPROP", self.CONTROLXPROP)
        self.show_all()

    def init_vars(self):
        self.delta = 0

    def on_timer(self):
        self.delta += 1

        Rac_Uio.get_speed_and_direction()
        self.counter.set_text("Frame %i" % self.delta)
        self.drawingarea_control.queue_draw()
        self.statusbar.queue_draw()
        # print("RACUIO", RacUio.speed, RacUio.direction)

        return True

    def on_DrawingArea_Control_draw(self, bus, message):
        RacDisplay().on_DrawingArea_Control_draw(message)
        # RacDisplay().on_DrawingArea_Control_draw(message, RacUio.speed, RacUio.direction)

    def on_MainWindow_notify(self, bus, message):
        return

    def on_cam_message(self, bus, message):
        retmsg = RacDisplay().on_message(message)
        if retmsg is not None:
            self.button_connect.set_active(False)
            self.statusbar.push(self.context_id, retmsg)

    def on_cam_sync_message(self, bus, message):
        RacDisplay().on_sync_message(message, self.CAMXPROP)

    def on_ComboBox_Host_changed(self, widget):
        model = self.combobox_host.get_model()
        Port = model[self.combobox_host.get_active()][1] + "."
        Port = Port[:Port.index('.')]
        self.spinbutton_port.set_value(int(Port))
        print("Changed:", self.combobox_host.get_active(), Port)

    def on_CheckButton_Cam_toggled(self,widget):
        if self.checkbutton_cam.get_active() == True:
            retmsg = Rac_connection.connect_camstream(True)
            if retmsg is True:
                retmsg = "VIDEO CONNECTION ESTABILISHED: OK"
            else:
                retmsg = "VIDEO CONNECTION ERROR: Unable to set the pipeline to the playing state."
        else:
            retmsg = Rac_connection.connect_camstream(False)
            if retmsg is True:
                retmsg = "VIDEO DISCONNECTED: OK"
            else:
                retmsg = "VIDEO NOT CONNECTED!"

        self.statusbar.push(self.context_id, retmsg)

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
            self.connect_gui()

            Host, Port_Comm = self.get_host_and_port()

            # Gstreamer setup start
            Rac_connection.source.set_property("host", Host)
            Rac_connection.source.set_property("port", Port_Comm)
            # Gstreamer setup end

            retmsg, success = Rac_connection.estabilish_connection(Host, Port_Comm)

            if success is True:
                self.update_server_list()
                if self.checkbutton_cam.get_active() is True:
                    retmsg = Rac_connection.connect_camstream(True)
                    if retmsg is True:
                        retmsg = "VIDEO CONNECTION ESTABILISHED: OK"
                    else:
                        retmsg = "VIDEO CONNECTION ERROR: Unable to set the pipeline to the playing state."

                self.drawingarea_control.grab_focus()
            else:
                self.disconnect_gui()

            self.statusbar.push(self.context_id, retmsg)
        else:
            Rac_connection.close_connection()
            self.disconnect_gui()

    def get_host_and_port(self):
        if self.checkbutton_localtest.get_active() == True:
            Host = self.TEST_Host
            Port_Comm = self.TEST_Port.__int__()
        else:
            Host = self.combobox_host.get_active_text()
            Port_Comm = self.spinbutton_port.get_value().__int__()

        return Host, Port_Comm

    def connect_gui(self):
        self.combobox_host.set_sensitive(False)
        self.checkbutton_localtest.set_sensitive(False)
        self.spinbutton_port.set_sensitive(False)

    def disconnect_gui(self):
        self.statusbar.push(self.context_id, "Disconnected.")

        self.button_connect.set_active(False)
        self.checkbutton_localtest.set_sensitive(True)

        if self.checkbutton_localtest.get_active() is False:
            self.combobox_host.set_sensitive(True)
            self.spinbutton_port.set_sensitive(True)

    def update_server_list(self):
        list_iter = self.combobox_host.get_active_iter()
        if list_iter is not None:
            model = self.combobox_host.get_model()
            Host, Port = model[list_iter][:2]
            try:
                Port = Port[:Port.index('.')]
            except:
                None
            print("Selected: Port=%s, Host=%s" % (int(Port), Host))
        else:
            entry = self.combobox_host.get_child()
            self.combobox_host.insert(0, self.spinbutton_port.get_value().__str__(), entry.get_text())
            self.combobox_host.set_active(0)

            print("New entry: %s" % entry.get_text())
            print("New port: %s" % self.spinbutton_port.get_value().__str__())

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

    def load_HostList(self, HostList_str):
        x = 0
        for HostName in HostList_str:
            Host = HostName.split(":")[0]
            Port = HostName.split(":")[1]
            self.combobox_host.insert(x, Port, Host)
            x += 1
            # print("HostName %s > Port/Host:" % HostName, Port, Host)

    def on_DrawingArea_Cam_button_press_event(self, mouse_event):
        if mouse_event.LeftIsDown():
            self.mouse = Rac_Uio.get_mouseInput(mouse_event)

    def on_DrawingArea_Cam_key_press_event(self, Area , event):
        print("event:", event)
        for iter_x in range(0, event.iter_n()):
            print("iter_x:", iter_x)

    # def on_Grid_Control_focus(self, widget, data=None):
    #     # if ev.keyval == Gdk.KEY_Escape: #If Escape pressed, reset text
    #     print("focus", widget)
    #     # print("key.keyval", key.keyval)
    #     self.speed, self.direction = Rac_Uio.get_speed_and_direction(self.speed, self.direction)

    def gtk_main_quit(self, dialog):
        Rac_connection.close_connection()
        self.config_snapshot()
        # config_save(self, cfg_file)
        Gtk.main_quit ()

###############################################################################
###############################################################################
###############################################################################
###############################################################################

def main():
    GUI_window()
    Gtk.main()

if __name__ == "__main__":
    main()





# gui = GUI_window()
# control = UI(gui)
# control.start()
#
# Gtk.main()
# control.quit = True
