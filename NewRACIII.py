#!/usr/bin/env python3.5
# -*- coding: CP1252 -*-
import gi
gi.require_version('Gst', '1.0')
gi.require_version('Gtk', '3.0')
gi.require_version('GstVideo', '1.0')
from gi.repository import GObject, Gtk, Gdk, GdkX11, GLib

# from importlib import reload
from init_variables import TIMEOUT_GUI, Paths, Debug, COMM_vars

from config_rw import *
from class_consoleIII import RacConnection, RacUio, RacDisplay, MainLoop

Rac_connection = RacConnection()
Rac_Display = RacDisplay()
Rac_Uio = RacUio()


# noinspection PyAttributeOutsideInit
class MainWindow(Gtk.Window):
    def __init__(self):
        super(MainWindow, self).__init__()

        # Read configuration
        reset_save(Paths.cfg_file)
        config_read(self, Paths.cfg_file)

        builder = self.init_vars
        self.context_id             = self.statusbar.get_context_id("message")
        self.context_id1            = self.statusbar1.get_context_id("message")
        self.context_id2            = self.statusbar2.get_context_id("message")

        Rac_connection.load_HostList(self.combobox_host, self.Host)

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

    @property
    def init_vars(self):
        builder = Gtk.Builder()
        builder.add_objects_from_file(Paths.GUI_file, ("MainBox_CON", "Adjustement_Port", "ListStoreResolution", "Action_StartTestServer"))
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
        self.spinner_connection     = builder.get_object("spinner1")

        self.LabelRpmL              = builder.get_object("LabelRpmL")
        self.LabelRpmR              = builder.get_object("LabelRpmR")
        self.LabelPowerL            = builder.get_object("LabelPowerL")
        self.LabelPowerR            = builder.get_object("LabelPowerR")
        self.LabelRpmReqL           = builder.get_object("LabelRpmReqL")
        self.LabelRpmReqR           = builder.get_object("LabelRpmReqR")
        self.LabelRpmAckL           = builder.get_object("LabelRpmAckL")
        self.LabelRpmAckR           = builder.get_object("LabelRpmAckR")
        self.LabelCamPosH           = builder.get_object("LabelCamPosH")
        self.LabelCamPosV           = builder.get_object("LabelCamPosV")

        self.LabelCoreTemp          = builder.get_object("LabelCoreTemp")
        self.LabelBattV             = builder.get_object("LabelBattV")
        self.LabelPowerA            = builder.get_object("LabelPowerA")
        self.LabelS1Dist            = builder.get_object("LabelS1Dist")

        self.LevelBar_Voltage       = builder.get_object("LevelBar_Voltage")
        self.LevelBar_Current       = builder.get_object("LevelBar_Current")
        self.LeverBar_PowerL        = builder.get_object("LeverBar_PowerL")
        self.LeverBar_PowerR        = builder.get_object("LeverBar_PowerR")

        return builder

    def init_ui(self):
        ###### Initiate UI start ######
        self.connect("destroy", self.gtk_main_quit)
        # self.movie_window.connect("button-press-event", self.on_DrawingArea_Cam_button_press_event)
        self.movie_window.set_size_request(640, 480)
        self.movie_window.set_can_default(True)
        ####### Initiate UI end #######

        self.show_all()

    def disconnect_gui(self):
        self.statusbar.push(self.context_id, "Disconnected.")

        self.button_connect.set_active(False)
        self.checkbutton_localtest.set_sensitive(True)

        if Rac_connection.LocalTest is False:
            self.combobox_host.set_sensitive(True)
            self.spinbutton_port.set_sensitive(True)

        if self.on_key_press_handler is not None:
            self.disconnect(self.on_key_press_handler)
            self.disconnect(self.on_key_release_handler)
            self.disconnect(self.on_mouse_press_handler)
            self.disconnect(self.on_mouse_release_handler)
            self.disconnect(self.on_motion_notify_handler)

    @staticmethod
    def on_DrawingArea_Control_draw(bus, message):
        Rac_Display.draw_arrow(message)

    def on_cam_message(self, bus, message):
        retmsg = Rac_Display.on_message(message)
        if retmsg is not None:
            self.button_connect.set_active(False)
            self.statusbar.push(self.context_id, retmsg)

    def on_cam_sync_message(self, bus, message):
        Rac_Display.on_sync_message(message, self.CAMXPROP)

    def on_ComboBox_Host_changed(self, widget):
        RacConnection.Host = widget.get_active_text()
        RacConnection.Port_Comm = int(float(widget.get_model()[widget.get_active()][1]))
        self.spinbutton_port.set_value(RacConnection.Port_Comm)
        # print("Changed:", model.get_active(), RacConnection.Port_Comm)

    @staticmethod
    def on_SpinButton_Port_value_changed(widget):
        RacConnection.Port_Comm = widget.get_value_as_int()
        print("RacConnection.Port_Comm", RacConnection.Port_Comm)

    def on_CheckButton_LocalTest_toggled(self, widget):
        Rac_connection.LocalTest = widget.get_active()

        if Rac_connection.LocalTest is True:
            self.combobox_host.set_sensitive(False)
            self.spinbutton_port.set_sensitive(False)
# ToDo:
            try:
                print("import TestSRV")
                import Test_Srv_GTKII
            except:
                print("TestSRV initialization error")
                # reload(self.Test_Srv_GTKII)

            Rac_connection.Host = self.TEST_Host
            Rac_connection.Port_Comm = self.TEST_Port

            ret = Rac_connection.HostList_get(self.combobox_host.get_model(), self.TEST_Host)
            if ret is False:
                ret = 25
                self.combobox_host.insert(ret, self.TEST_Port.__str__(), self.TEST_Host)

            self.combobox_host.set_active(ret)
            self.spinbutton_port.set_value(self.TEST_Port)

        else:
            self.combobox_host.set_sensitive(True)
            self.spinbutton_port.set_sensitive(True)

            del self.Test_Srv_GTKII

    def on_ToggleButton_Connect_toggled(self, widget):
        self.on_key_press_handler = None
        if widget.get_active() is True:
            self.combobox_host.set_sensitive(False)
            self.spinbutton_port.set_sensitive(False)
            self.checkbutton_localtest.set_sensitive(False)

            success = Rac_connection.establish_connection()

            if Debug > 0:
                print("success:", success)

            if success is True:
                retmsg = "Server connected! " + Rac_connection.srv.getsockname().__str__()
                # print("self.srv.getpeername()", self.srv.getpeername())
                if Debug > 2: print(retmsg)

                self.on_key_press_handler     = self.connect("key-press-event", RacUio.on_key_press)
                self.on_key_release_handler   = self.connect("key-release-event", RacUio.on_key_release)
                self.on_mouse_press_handler   = self.connect("button-press-event", Rac_Uio.on_mouse_press)
                self.on_mouse_release_handler = self.connect("button-release-event", Rac_Uio.on_mouse_release)
                self.on_motion_notify_handler = self.connect("motion-notify-event", Rac_Uio.on_motion_notify)

                Rac_connection.update_server_list(self)
                if self.checkbutton_cam.get_active() is True:
                    # time.sleep(1)
                    retmsg = Rac_connection.connect_camstream(True)
                    if retmsg is True:
                        retmsg = "VIDEO CONNECTION ESTABILISHED: OK"
                    else:
                        retmsg = "VIDEO CONNECTION ERROR: Unable to set the pipeline to the playing state."

            else:
                retmsg = "Connection Error [" + (Rac_connection.Host, Rac_connection.Port_Comm).__str__() + "]"
                if Debug > 0: print(retmsg)
                self.disconnect_gui()

            self.statusbar.push(self.context_id, retmsg)
        else:
            Rac_connection.close_connection()
            self.disconnect_gui()

    def on_CheckButton_Cam_toggled(self, widget):
        COMM_vars.camera = widget.get_active()
        if COMM_vars.camera is True:
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

    def on_CheckButton_Speakers_toggled(self, widget):
        COMM_vars.speakers = widget.get_active()

    def on_CheckButton_Display_toggled(self, widget):
        COMM_vars.display = widget.get_active()

    def on_CheckButton_Lights_toggled(self, widget):
        COMM_vars.light = widget.get_active()

    def on_CheckButton_Mic_toggled(self, widget):
        COMM_vars.mic = widget.get_active()

    def on_CheckButton_Laser_toggled(self, widget):
        COMM_vars.laser = widget.get_active()

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
        Host_list = Rac_connection.HostList_get(self.combobox_host.get_model(), None)
        Rac_connection.config_snapshot(Host_list)

    def gtk_main_quit(self, dialog):
        Rac_connection.close_connection()
        Host_list = Rac_connection.HostList_get(self.combobox_host.get_model(), None)
        Rac_connection.config_snapshot(Host_list)

        # config_save(self, cfg_file)
        Gtk.main_quit ()

###############################################################################


def main():
    MainWindow()
    Gtk.main()

if __name__ == "__main__":
    main()
