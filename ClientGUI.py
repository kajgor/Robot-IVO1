#!/usr/bin/env python3.5
# -*- coding: CP1252 -*-
import gi
gi.require_version('Gst', '1.0')
gi.require_version('Gtk', '3.0')
gi.require_version('GstVideo', '1.0')
from gi.repository import Gtk, Gdk, GdkX11, GLib

from Common_vars import TIMEOUT_GUI, VideoBitrate, AudioBitrate
from Client_vars import Paths, Debug

from config_rw import *
from ClientLib import RacConnection, RacUio, RacDisplay, MainLoop, Console


# noinspection PyAttributeOutsideInit
class MainWindow(Gtk.Window):
    def __init__(self):
        super(MainWindow, self).__init__()

        builder = self.init_vars

        self.context_id             = self.statusbar.get_context_id("message")
        self.context_id1            = self.statusbar1.get_context_id("message")
        self.context_id2            = self.statusbar2.get_context_id("message")
        self.camera_on = True
        self.resolution = 1

        self.Host, self.Port = None, None
        # reset_save(Paths.cfg_file)

        HostList, \
        Mask1, \
        Reserved_1, \
        Reserved_2, \
        Reserved_3, \
        Network, \
        Compression, \
        Ssh, \
        Reserved_7, \
        Local_Test = config_read(Paths.cfg_file)

        self.checkbutton_cam.set_active(bool(COMM_vars.resolution))
        self.ComboBoxResolution.set_active(int(COMM_vars.resolution) - bool(COMM_vars.resolution))
        self.CheckButton_Lights.set_active(COMM_vars.light)
        self.CheckButton_Speakers.set_active(COMM_vars.speakers)
        self.CheckButton_Display.set_active(COMM_vars.display)
        self.CheckButton_Mic.set_active(COMM_vars.mic)
        self.CheckButton_Laser.set_active(COMM_vars.laser)
        self.CheckButton_Auto.set_active(COMM_vars.AutoMode)
        self.Entry_RsaKey.set_text(Ssh[0])
        self.Entry_KeyPass.set_text(Ssh[1])
        self.Entry_User.set_text(Ssh[2])
        self.Entry_RemoteHost.set_text(Ssh[3])
        self.Switch_Compression.set_active(Compression[0])
        self.ComboBoxText_Vcodec.set_active(Compression[1])
        self.ComboBoxText_Acodec.set_active(Compression[2])
        self.checkbutton_localtest.set_active(Local_Test)
        self.ComboBoxText_Proto.set_active(Network)
        # self.ComboBoxText_Vbitrate.set_active(Compression[3])
        # self.ComboBoxText_Abitrate.set_active(Compression[4])

        self.on_CheckButton_LocalTest_toggled(self.checkbutton_localtest)
        self.on_ComboBoxText_Proto_changed(self.ComboBoxText_Proto)
        self.on_ComboBoxResolution_changed(self.ComboBoxResolution)
        self.on_ComboBoxText_Vbitrate_changed(self.ComboBoxText_Vcodec)
        self.on_ComboBoxText_Abitrate_changed(self.ComboBoxText_Acodec)
        self.on_CheckButton_Mic_toggled(self.CheckButton_Mic)

        Rac_connection.load_HostList(self.combobox_host, HostList)

        ####### Main loop definition ###############
        GLib.timeout_add(TIMEOUT_GUI, MainLoop(self).on_timer)
        ############################################
        self.init_ui()

        self.CAMXPROP = self.movie_window.get_property('window')
        # print("self.CAMXPROP", self.CAMXPROP)
        # Connect signals
        builder.connect_signals(self)

        if Debug > 2:
            print("Objects:")
            print(builder.get_objects().__str__())

        bus = RacConnection.player_video[0][False].get_bus()
        bus.add_signal_watch()
        bus.enable_sync_message_emission()
        bus.connect("message", self.on_cam_message)
        bus.connect("sync-message::element", self.on_cam_sync_message)

        bus_test = RacConnection.player_video[0][True].get_bus()
        bus_test.add_signal_watch()
        bus_test.enable_sync_message_emission()
        bus_test.connect("message", self.on_cam_message)
        bus_test.connect("sync-message::element", self.on_cam_sync_message)

        bus = RacConnection.player_video[1][False].get_bus()
        bus.add_signal_watch()
        bus.enable_sync_message_emission()
        bus.connect("message", self.on_cam_message)
        bus.connect("sync-message::element", self.on_cam_sync_message)

        bus_test = RacConnection.player_video[1][True].get_bus()
        bus_test.add_signal_watch()
        bus_test.enable_sync_message_emission()
        bus_test.connect("message", self.on_cam_message)
        bus_test.connect("sync-message::element", self.on_cam_sync_message)

    @property
    def init_vars(self):
        builder = Gtk.Builder()
        builder.add_objects_from_file(Paths.GUI_file, ("MainBox_CON", "Adjustement_Port", "Action_StartTestServer",
                                                       "Window_Log", "Window_Advanced"))
        print("GUI file added: ", Paths.GUI_file)

        self.add(builder.get_object("MainBox_CON"))
        self.button_connect         = builder.get_object("ToggleButton_Connect")
        self.movie_window           = builder.get_object("DrawingArea_Cam")
        self.checkbutton_localtest  = builder.get_object("CheckButton_LocalTest")
        self.checkbutton_cam        = builder.get_object("CheckButton_Cam")
        self.combobox_host          = builder.get_object("ComboBox_Host")
        self.comboboxtext_host      = builder.get_object("ComboBoxTextEntry_Host")
        self.CheckButton_Lights     = builder.get_object("CheckButton_Lights")
        self.CheckButton_Speakers   = builder.get_object("CheckButton_Speakers")
        self.CheckButton_Display    = builder.get_object("CheckButton_Display")
        self.CheckButton_Mic        = builder.get_object("CheckButton_Mic")
        self.CheckButton_Laser      = builder.get_object("CheckButton_Laser")
        self.CheckButton_Auto       = builder.get_object("CheckButton_Auto")

        self.spinbutton_port        = builder.get_object("SpinButton_Port")
        self.drawingarea_control    = builder.get_object("DrawingArea_Control")
        self.statusbar              = builder.get_object("StatusBar")
        self.statusbar1             = builder.get_object("StatusBar1")
        self.statusbar2             = builder.get_object("StatusBar2")
        self.spinner_connection     = builder.get_object("spinner1")
        self.togglebutton_log       = builder.get_object("ToggleButton_Log")
        self.CheckButton_SshTunnel  = builder.get_object("CheckButton_SshTunnel")

        self.LogWindow              = builder.get_object("Window_Log")
        self.TextView_Log           = builder.get_object("TextView_Log")
        self.TextView_Log.override_color(Gtk.StateType.NORMAL, Gdk.RGBA(1, .75, 0, 1))
        self.TextView_Log.override_background_color(Gtk.StateType.NORMAL, Gdk.RGBA(.15, 0.15, 0.15, 1))

        self.AdvancedWindow         = builder.get_object("Window_Advanced")
        self.Entry_RsaKey           = builder.get_object("Entry_RsaKey")
        self.Entry_KeyPass          = builder.get_object("Entry_KeyPass")
        self.Entry_User             = builder.get_object("Entry_User")
        self.Entry_RemoteHost       = builder.get_object("Entry_RemoteHost")
        self.Switch_Compression     = builder.get_object("ComboBoxText_Ssh_Compression")
        self.ComboBoxText_Vcodec    = builder.get_object("ComboBoxText_Vcodec")
        self.ComboBoxText_Acodec    = builder.get_object("ComboBoxText_Acodec")
        self.ComboBoxText_Proto     = builder.get_object("ComboBoxText_Proto")
        # self.on_Button_Adv          = builder.get_object("on_Button_Adv")
        self.ComboBoxText_Vbitrate  = builder.get_object("ComboBoxText_Vbitrate")
        self.ComboBoxText_Abitrate  = builder.get_object("ComboBoxText_Abitrate")

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

        self.ComboBoxResolution     = builder.get_object("ComboBoxResolution")

        return builder

    def init_ui(self):
        ###### Initiate UI start ######
        self.connect("destroy", self.gtk_main_quit)
        self.movie_window.set_can_default(True)
        # self.movie_window.set_size_request(640, 480)
        ####### Initiate UI end #######

        self.show_all()

    def connect_gui(self):
        self.combobox_host.set_sensitive(False)
        self.spinbutton_port.set_sensitive(False)
        self.checkbutton_localtest.set_sensitive(False)
        self.CheckButton_SshTunnel.set_sensitive(False)

    def connect_gui_handlers(self):
        self.on_key_press_handler = self.connect("key-press-event", RacUio.on_key_press)
        self.on_key_release_handler = self.connect("key-release-event", RacUio.on_key_release)
        self.on_mouse_press_handler = self.connect("button-press-event", RacUio.on_mouse_press)
        self.on_mouse_release_handler = self.connect("button-release-event", RacUio.on_mouse_release)
        self.on_motion_notify_handler = self.connect("motion-notify-event", RacUio.on_motion_notify)

    def disconnect_gui(self):
        if self.on_key_press_handler is not None:
            self.disconnect(self.on_key_press_handler)
            self.disconnect(self.on_key_release_handler)
            self.disconnect(self.on_mouse_press_handler)
            self.disconnect(self.on_mouse_release_handler)
            self.disconnect(self.on_motion_notify_handler)

        self.button_connect.set_active(False)
        self.checkbutton_localtest.set_sensitive(True)
        # if Rac_connection.Test_Mode is False:
        self.combobox_host.set_sensitive(True)
        self.spinbutton_port.set_sensitive(True)
        self.CheckButton_SshTunnel.set_sensitive(True)

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
        # print("widget", widget.get_model()[widget.get_active()][1])
        self.Host = widget.get_active_text()
        self.Port = int(float(widget.get_model()[widget.get_active()][1]))
        self.spinbutton_port.set_value(self.Port)

    def on_SpinButton_Port_value_changed(self, widget):
        self.Port = widget.get_value_as_int()

    def on_CheckButton_LocalTest_toggled(self, widget):
        RacConnection.Video_Mode = not(widget.get_active())

    def on_ComboBoxText_Proto_changed(self, widget):
        RacConnection.Protocol = widget.get_active()

    def on_ToggleButton_Connect_toggled(self, widget):
        self.on_key_press_handler = None
        if widget.get_active() is True:
            widget.set_label(Gtk.STOCK_DISCONNECT)
            self.connect_gui()

            if self.CheckButton_SshTunnel.get_active() is True:
                Host, Port = Rac_connection.open_ssh_tunnel(self.Host, self.Port,
                                                            self.Entry_RsaKey.get_text(),
                                                            self.Entry_KeyPass.get_text(),
                                                            self.Entry_User.get_text(),
                                                            self.Entry_RemoteHost.get_text(),
                                                            self.Switch_Compression.get_active())
            else:
                Host, Port = self.Host, self.Port

            success = bool(Host)
            retmsg = "SSH Connection Error!"
            if success is True:
                success, retmsg = Rac_connection.establish_connection(Host, Port)

                if success is True:
                    self.connect_gui_handlers()
                    RacConnection.update_server_list(self.combobox_host, self.spinbutton_port.get_value())

            if success is not True:
                self.disconnect_gui()
            self.statusbar.push(self.context_id, retmsg)
        else:
            COMM_vars.connected = False
            widget.set_label(Gtk.STOCK_CONNECT)
            self.statusbar.push(self.context_id, "Disconnected.")
            self.disconnect_gui()

    def on_CheckButton_Cam_toggled(self, widget):
        self.camera_on = widget.get_active()
        COMM_vars.resolution = self.resolution * self.camera_on
        retmsg = "Camera:" + self.camera_on.__str__()

        self.statusbar.push(self.context_id, retmsg)

    def on_ComboBoxResolution_changed(self, widget):
        self.resolution = widget.get_active() + 1
        # Console.print("Change mode to", self.resolution)
        if self.resolution == 1:
            self.movie_window.set_size_request(640, 480)
        if self.resolution == 2:
            self.movie_window.set_size_request(640, 480)
        if self.resolution == 3:
            self.movie_window.set_size_request(800, 600)
        if self.resolution == 4:
            self.movie_window.set_size_request(1280, 800)
        if self.resolution == 5:
            self.movie_window.set_size_request(1920, 1080)

        COMM_vars.resolution = self.resolution * self.camera_on

    def on_ComboBoxText_Vbitrate_changed(selfs, widget):
        COMM_vars.Vbitrate = widget.get_active()
        Console.print("Video Bitrate:", VideoBitrate[COMM_vars.Vbitrate])

    def on_ComboBoxText_Abitrate_changed(selfs, widget):
        COMM_vars.Abitrate = widget.get_active()
        Console.print("Audio Bitrate:", AudioBitrate[COMM_vars.Abitrate])

    def on_CheckButton_Speakers_toggled(self, widget):
        COMM_vars.speakers = widget.get_active()
        Console.print("Speakers:", COMM_vars.speakers)

    def on_CheckButton_Display_toggled(self, widget):
        COMM_vars.display = widget.get_active()
        Console.print("Display:", COMM_vars.display)

    def on_CheckButton_Lights_toggled(self, widget):
        COMM_vars.light = widget.get_active()
        Console.print("Light:", COMM_vars.light)

    def on_CheckButton_Mic_toggled(self, widget):
        COMM_vars.mic = widget.get_active()
        Console.print("Mic:", COMM_vars.mic)

    def on_CheckButton_Laser_toggled(self, widget):
        COMM_vars.laser = widget.get_active()
        Console.print("Laser:", COMM_vars.laser)

    def on_ToggleButton_Log_toggled(self, widget):
        if widget.get_active() is True:
            self.LogWindow.show()
        else:
            self.LogWindow.hide()

    def on_MainWindow_notify(self, bus, message):
        print("***")
        return

    def on_Button_AdvOk_activate(self, widget):
        self.AdvancedWindow.hide()

    def on_Button_AdvOk_clicked(self, widget):
        self.AdvancedWindow.hide()

    def on_Button_Preferences_clicked(self, widget):
        self.AdvancedWindow.show()
        # print("TEXT IN COMBOBOX: ", self.combobox_host.get_active_text())
        # print("NO OF ITEMS:", self.combobox_host.get_model().iter_n_children())
        # Host_list = Rac_connection.HostList_get(self.combobox_host.get_model(), None)
        # Rac_connection.config_snapshot(Host_list)
        # reset_save(Paths.cfg_file)

    def on_Window_Advanced_delete_event(self, bus, message):
        self.AdvancedWindow.hide()
        return True

    def save_config(self):
        HostList = []
        HostListRaw = self.combobox_host.get_model()
        for iter_x in range(0, HostListRaw.iter_n_children()):
            HostList.append(HostListRaw[iter_x][0] + ":" + HostListRaw[iter_x][1])

        Compression_Mask = (self.Switch_Compression.get_active(),
                            self.ComboBoxText_Vcodec.get_active(),
                            self.ComboBoxText_Acodec.get_active(),
                            self.ComboBoxText_Vbitrate.get_active(),
                            self.ComboBoxText_Abitrate.get_active())

        Ssh_Mask = (self.Entry_RsaKey.get_text(),
                    self.Entry_KeyPass.get_text(),
                    self.Entry_User.get_text(),
                    self.Entry_RemoteHost.get_text())

        Network_Mask = self.ComboBoxText_Proto.get_active()

        config_save(Paths.cfg_file, tuple(HostList),
                    False,
                    False,
                    False,
                    Network_Mask,
                    Compression_Mask,
                    Ssh_Mask,
                    False,
                    self.checkbutton_localtest.get_active())

    def gtk_main_quit(self, dialog):
        Rac_connection.close_connection()
        # Host_list = Rac_connection.HostList_get(self.combobox_host.get_model(), None)
        # Rac_connection.config_snapshot(Host_list)
        self.save_config()

        Gtk.main_quit ()

###############################################################################


def main():
    MainWindow()
    Gtk.main()

if __name__ == "__main__":
    Rac_connection = RacConnection()
    Rac_Display = RacDisplay()
    # Rac_Console = Console(True)
    main()
