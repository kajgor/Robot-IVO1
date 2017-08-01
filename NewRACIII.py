#!/usr/bin/env python
# -*- coding: CP1252 -*-
# import time
import gi
gi.require_version('Gst', '1.0')
gi.require_version('Gtk', '3.0')
gi.require_version('GstVideo', '1.0')
from gi.repository import GObject, Gtk, Gdk, GdkX11, GLib

from importlib import reload
from init_variables import TIMEOUT_GUI, Paths, Debug

from config_rw import *
from class_consoleIII import RacConnection, RacUio, RacDisplay, MainLoop

Rac_connection = RacConnection()
Rac_Display = RacDisplay()
Rac_Uio = RacUio()


# noinspection PyAttributeOutsideInit
class GUI_window(Gtk.Window):
    def __init__(self):
        super(GUI_window, self).__init__()

        builder = self.init_vars()
        Rac_connection.load_HostList(self, self.Host)

        ####### Main loop definition ###############
        GLib.timeout_add(TIMEOUT_GUI, MainLoop(self).on_timer)
        ############################################
        self.init_ui()

        self.CAMXPROP = self.movie_window.get_property('window')
        print("self.CAMXPROP", self.CAMXPROP)
        # Connect signals
        builder.connect_signals(self)
# ToDo
        self.TEST_Host = "127.0.0.1"
        self.TEST_Port = 12344

        if Debug > 2:
            print("Objects:")
            print(builder.get_objects().__str__())

        bus = Rac_connection.player.get_bus()
        bus.add_signal_watch()
        bus.enable_sync_message_emission()
        bus.connect("message", self.on_cam_message)
        bus.connect("sync-message::element", self.on_cam_sync_message)

    def init_vars(self):
        # Read configuration
        reset_save(Paths.cfg_file)
        config_read(self, Paths.cfg_file)

        builder = Gtk.Builder()
        builder.add_objects_from_file(Paths.GUI_file, ("MainBox_CON", "Adjustement_Port", "Adjustment_Resolution", "Action_StartTestServer"))
        print("GUI file added: ", Paths.GUI_file)
        self.add(builder.get_object("MainBox_CON"))
        self.button_connect         = builder.get_object("ToggleButton_Connect")
        self.movie_window           = builder.get_object("DrawingArea_Cam")
        self.checkbutton_localtest  = builder.get_object("CheckButton_LocalTest")
        self.checkbutton_cam        = builder.get_object("CheckButton_Cam")
        self.combobox_host          = builder.get_object("ComboBox_Host")
        self.comboboxtext_host      = builder.get_object("ComboBoxTextEntry_Host")
        self.spinbutton_port        = builder.get_object("SpinButton_Port")
        self.drawingarea_control    = builder.get_object("DrawingArea_Control")
        self.statusbar              = builder.get_object("StatusBar")
        self.statusbar1             = builder.get_object("StatusBar")
        self.statusbar2             = builder.get_object("StatusBar2")
        self.context_id             = self.statusbar.get_context_id("message")
        self.context_id1            = self.statusbar1.get_context_id("message")
        self.context_id2            = self.statusbar2.get_context_id("message")

        return builder

    def init_ui(self):
        ###### Initiate UI start ######
        self.connect("destroy", self.gtk_main_quit)
        self.connect("key-press-event", RacUio.on_key_press)
        self.connect("key-release-event", RacUio.on_key_release)
        self.connect("button-press-event", Rac_Uio.on_mouse_press)
        self.connect("button-release-event", Rac_Uio.on_mouse_release)
        self.connect("motion-notify-event", Rac_Uio.on_motion_notify)
        # self.movie_window.connect("button-press-event", self.on_DrawingArea_Cam_button_press_event)
        self.movie_window.set_size_request(640, 480)
        self.movie_window.set_can_default(True)
        ####### Initiate UI end #######

        self.show_all()

    def on_DrawingArea_Control_draw(self, bus, message):
        Rac_Display.draw_arrow(message)

    def on_cam_message(self, bus, message):
        retmsg = Rac_Display.on_message(message)
        if retmsg is not None:
            self.button_connect.set_active(False)
            self.statusbar.push(self.context_id, retmsg)

    def on_cam_sync_message(self, bus, message):
        Rac_Display.on_sync_message(message, self.CAMXPROP)

    def on_ComboBox_Host_changed(self, widget):
        model = self.combobox_host.get_model()
        Port = int(float(model[self.combobox_host.get_active()][1]))
        self.spinbutton_port.set_value(Port)
        print("Changed:", self.combobox_host.get_active(), Port)

    def on_CheckButton_Cam_toggled(self,widget):
        if self.checkbutton_cam.get_active() is True:
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
        if self.checkbutton_localtest.get_active() is True:
            ret = Rac_connection.HostList_get(self, self.TEST_Host)
            if ret is False:
                ret = 0
                self.combobox_host.insert(ret, self.TEST_Port.__str__(), self.TEST_Host)

            self.combobox_host.set_active(ret)
            self.spinbutton_port.set_value(self.TEST_Port)
            self.combobox_host.set_sensitive(False)
            self.spinbutton_port.set_sensitive(False)
# ToDo:
            try:
                print("try")
                import Test_Srv_GTKII
            except:
                print("except")
                reload(self.Test_Srv_GTKII)
        else:
            self.combobox_host.set_sensitive(True)
            self.spinbutton_port.set_sensitive(True)

            del self.Test_Srv_GTKII

    def on_ToggleButton_Connect_toggled(self, widget):
        if self.button_connect.get_active() is True:

            Rac_connection.connect_gui(self)

            Host, Port_Comm = Rac_connection.get_host_and_port(self)

            # Gstreamer setup start
            Rac_connection.source.set_property("host", Host)
            Rac_connection.source.set_property("port", Port_Comm + 1)
            # Gstreamer setup end

            retmsg, success = Rac_connection.estabilish_connection(Host, Port_Comm)
            print("retmsg/success", retmsg, success)

            if success is True:
                Rac_connection.update_server_list(self)
                if self.checkbutton_cam.get_active() is True:
                    # time.sleep(1)
                    retmsg = Rac_connection.connect_camstream(True)
                    if retmsg is True:
                        retmsg = "VIDEO CONNECTION ESTABILISHED: OK"
                    else:
                        retmsg = "VIDEO CONNECTION ERROR: Unable to set the pipeline to the playing state."

                # self.drawingarea_control.grab_focus()
            else:
                Rac_connection.disconnect_gui(self)

            Rac_Uio.connected = success
            self.statusbar.push(self.context_id, retmsg)
        else:
            Rac_connection.close_connection()
            Rac_connection.disconnect_gui(self)

    def on_CheckButton_Speakers_toggled(self, widget):
        return

    def on_CheckButton_Display_toggled(self, widget):
        return

    def on_CheckButton_Lights_toggled(self, widget):
        return

    def on_MainWindow_notify(self, bus, message):
        return

    # def on_DrawingArea_Cam_motion_notify_event(self, widget, event):
    #     print("motion!!!!!!!")
    #     Rac_Uio.on_motion_notify(event)
    #     return True
    #
    # def on_DrawingArea_Cam_button_press_event(self, widget, mouse_event):
    #     print("*********************** BUTTON!!! ", widget)
    #     Rac_Uio.on_mouse_press(mouse_event)
    #
    # def on_DrawingArea_Cam_button_release_event(self, widget, mouse_event):
    #     Rac_Uio.on_mouse_release(mouse_event)

    def on_Button_Preferences_clicked(self, widget):
        print("TEXT IN COMBOBOX: ", self.combobox_host.get_active_text())
        print("NO OF ITEMS:", self.combobox_host.get_model().iter_n_children())
        Host_list = Rac_connection.HostList_get(self, None)
        Rac_connection.config_snapshot(Host_list)

    def gtk_main_quit(self, dialog):
        Rac_connection.close_connection()
        Host_list = Rac_connection.HostList_get(self, None)
        Rac_connection.config_snapshot(Host_list)

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
