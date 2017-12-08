#!/usr/bin/env python3.5
# -*- coding: CP1252 -*-
import gi
gi.require_version('Gst', '1.0')
gi.require_version('Gtk', '3.0')
gi.require_version('GstVideo', '1.0')
from gi.repository import Gtk, Gdk, GdkX11, GLib

from Common_vars import TIMEOUT_GUI, VideoFramerate, AudioBitrate, AudioCodec, VideoCodec, PROTO_NAME
from Client_vars import Paths, Debug, CAM0_control

from config_rw import *
from ClientLib import RacConnection, RacUio, RacDisplay, MainLoop, Console


# noinspection PyAttributeOutsideInit
class MainWindow(Gtk.Window):
    def __init__(self):
        super(MainWindow, self).__init__()

        builder = self.init_vars

        self.context_id             = self.StatusBar.get_context_id("message")
        self.context_id1            = self.StatusBar1.get_context_id("message")
        self.context_id2            = self.StatusBar2.get_context_id("message")
        self.camera_on = True
        self.resolution = 0

        Console.print("Console 3.0 initialized.\n")

        ####### Main loop definition ###############
        GLib.timeout_add(TIMEOUT_GUI, MainLoop(self).on_timer)
        ############################################
        self.init_ui()

        self.CAMXPROP = self.LiveCam_window.get_property('window')

        # Connect signals
        builder.connect_signals(self)

        self.Host, self.Port = None, None
        # reset_save(Paths.cfg_file)
        HostList = self.load_config()

        Rac_connection.load_HostList(self.ComboBox_host, HostList)

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
        builder.add_from_file(Paths.GUI_file)
        print("GUI file added: ", Paths.GUI_file)

        self.add(builder.get_object("MainBox_CON"))
        self.ToggleButton_connect   = builder.get_object("ToggleButton_Connect")
        self.LiveCam_window         = builder.get_object("DrawingArea_Cam")
        self.ComboBox_host          = builder.get_object("ComboBox_Host")
        self.ComboBoxText_host      = builder.get_object("ComboBoxTextEntry_Host")
        self.CheckButton_localtest  = builder.get_object("CheckButton_LocalTest")
        self.CheckButton_camera     = builder.get_object("CheckButton_Cam")
        self.CheckButton_Lights     = builder.get_object("CheckButton_Lights")
        self.CheckButton_Speakers   = builder.get_object("CheckButton_Speakers")
        self.CheckButton_Display    = builder.get_object("CheckButton_Display")
        self.CheckButton_Mic        = builder.get_object("CheckButton_Mic")
        self.CheckButton_Laser      = builder.get_object("CheckButton_Laser")
        self.CheckButton_Auto       = builder.get_object("CheckButton_Auto")

        self.SpinButton_port        = builder.get_object("SpinButton_Port")
        self.DrawingArea_control    = builder.get_object("DrawingArea_Control")
        self.StatusBar              = builder.get_object("StatusBar")
        self.StatusBar1             = builder.get_object("StatusBar1")
        self.StatusBar2             = builder.get_object("StatusBar2")
        self.Spinner_connection     = builder.get_object("spinner1")
        self.ToggleButton_log       = builder.get_object("ToggleButton_Log")
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
        self.ComboBoxText_Framerate = builder.get_object("ComboBoxText_Framerate")
        self.ComboBoxText_Abitrate  = builder.get_object("ComboBoxText_Abitrate")
        self.ComboBoxText_Rotate    = builder.get_object("ComboBoxText_Rotate")
        self.ComboBoxResolution     = builder.get_object("ComboBoxResolution")

        self.AdvancedCamWindow      = builder.get_object("Window_AdvancedCam")

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

        self.Menu_CamOptions        = builder.get_object("Menu_CamOptions")
        self.Menu_CamRes_Item1      = builder.get_object("Menu_CamRes_Item1")
        self.Menu_CamRes_Item2      = builder.get_object("Menu_CamRes_Item2")
        self.Menu_CamRes_Item3      = builder.get_object("Menu_CamRes_Item3")
        self.Menu_CamRes_Item4      = builder.get_object("Menu_CamRes_Item4")
        self.Menu_CamRes_Item5      = builder.get_object("Menu_CamRes_Item5")
        self.Menu_CamFx_Item1       = builder.get_object("Menu_CamFx_Item1")
        self.Menu_CamFx_Item2       = builder.get_object("Menu_CamFx_Item2")
        self.Menu_CamFx_Item3       = builder.get_object("Menu_CamFx_Item3")
        self.Menu_CamFx_Item4       = builder.get_object("Menu_CamFx_Item4")
        self.Menu_CamFx_Item5       = builder.get_object("Menu_CamFx_Item5")
        self.Menu_CamFx_Item6       = builder.get_object("Menu_CamFx_Item6")
        self.Menu_CamFx_Item7       = builder.get_object("Menu_CamFx_Item7")

        return builder

    def init_ui(self):
        ###### Initiate UI start ######
        self.connect("destroy", self.gtk_main_quit)
        self.LiveCam_window.set_can_default(True)
        # self.movie_window.set_size_request(640, 480)
        ####### Initiate UI end #######

        self.show_all()

    def connect_gui(self):
        self.ComboBox_host.set_sensitive(False)
        self.SpinButton_port.set_sensitive(False)
        self.CheckButton_localtest.set_sensitive(False)
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

        self.ToggleButton_connect.set_active(False)
        self.CheckButton_localtest.set_sensitive(True)
        # if Rac_connection.Test_Mode is False:
        self.ComboBox_host.set_sensitive(True)
        self.SpinButton_port.set_sensitive(True)
        self.CheckButton_SshTunnel.set_sensitive(True)

    def load_config(self):
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

        self.CheckButton_camera.set_active(bool(COMM_vars.resolution))
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
        self.ComboBoxText_Framerate.set_active(Compression[3])
        self.ComboBoxText_Abitrate.set_active(Compression[4])
        self.ComboBoxText_Rotate.set_active(Compression[5])
        self.ComboBoxText_Proto.set_active(Network)
        self.CheckButton_localtest.set_active(Local_Test)

        self.on_ComboBoxText_Proto_changed(self.ComboBoxText_Proto)
        self.on_ComboBoxResolution_changed(self.ComboBoxResolution)
        self.on_ComboBoxText_Vcodec_changed(self.ComboBoxText_Vcodec)
        self.on_ComboBoxText_Acodec_changed(self.ComboBoxText_Acodec)
        self.on_ComboBoxText_Framerate_changed(self.ComboBoxText_Framerate)
        self.on_ComboBoxText_Abitrate_changed(self.ComboBoxText_Abitrate)
        self.on_ComboBoxText_Rotate_changed(self.ComboBoxText_Rotate)
        self.on_CheckButton_LocalTest_toggled(self.CheckButton_localtest)
        self.on_CheckButton_Mic_toggled(self.CheckButton_Mic)
        self.on_CheckButton_Speakers_toggled(self.CheckButton_Display)

        return HostList

    @staticmethod
    def on_DrawingArea_Control_draw(bus, message):
        Rac_Display.draw_arrow(message)

    def on_cam_message(self, bus, message):
        retmsg = Rac_Display.on_message(message)
        if retmsg is not None:
            self.ToggleButton_connect.set_active(False)
            self.StatusBar.push(self.context_id, retmsg)

    def on_cam_sync_message(self, bus, message):
        Rac_Display.on_sync_message(message, self.CAMXPROP)

    def on_ComboBox_Host_changed(self, widget):
        # print("widget", widget.get_model()[widget.get_active()][1])
        self.Host = widget.get_active_text()
        self.Port = int(float(widget.get_model()[widget.get_active()][1]))
        self.SpinButton_port.set_value(self.Port)

    def on_SpinButton_Port_value_changed(self, widget):
        self.Port = widget.get_value_as_int()

    def on_CheckButton_LocalTest_toggled(self, widget):
        RacConnection.Video_Mode = not(widget.get_active())
        self.SSBar_update()

    def on_ComboBoxText_Proto_changed(self, widget):
        RacConnection.Protocol = widget.get_active()
        self.SSBar_update()

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
                    RacConnection.update_server_list(self.ComboBox_host, self.SpinButton_port.get_value())

            if success is not True:
                self.disconnect_gui()
            self.StatusBar.push(self.context_id, retmsg)
        else:
            COMM_vars.connected = False
            widget.set_label(Gtk.STOCK_CONNECT)
            self.StatusBar.push(self.context_id, "Disconnected.")
            self.disconnect_gui()

    def on_CheckButton_Cam_toggled(self, widget):
        self.camera_on = widget.get_active()
        COMM_vars.resolution = self.resolution * self.camera_on
        retmsg = "Camera:" + self.camera_on.__str__()

        self.StatusBar.push(self.context_id, retmsg)

    def on_ComboBoxResolution_changed(self, widget):
        self.resolution = widget.get_active() + 1
        # Console.print("Change mode to", self.resolution)
        if self.resolution == 1:
            self.LiveCam_window.set_size_request(640, 480)
            self.Menu_CamRes_Item1.set_active(True)
        if self.resolution == 2:
            self.LiveCam_window.set_size_request(640, 480)
            self.Menu_CamRes_Item2.set_active(True)
        if self.resolution == 3:
            self.LiveCam_window.set_size_request(800, 600)
            self.Menu_CamRes_Item3.set_active(True)
        if self.resolution == 4:
            self.LiveCam_window.set_size_request(1024, 768)
            self.Menu_CamRes_Item4.set_active(True)
        if self.resolution == 5:
            self.LiveCam_window.set_size_request(1152, 864)
            self.Menu_CamRes_Item5.set_active(True)

        COMM_vars.resolution = self.resolution * self.camera_on

    def on_ComboBoxText_Vcodec_changed(self, widget):
        COMM_vars.Vcodec = widget.get_active()
        self.SSBar_update()

    def on_ComboBoxText_Acodec_changed(self, widget):
        COMM_vars.Acodec = widget.get_active()
        self.SSBar_update()

    def on_ComboBoxText_Framerate_changed(self, widget):
        COMM_vars.Framerate = widget.get_active()
        Console.print("Video Framerate:", VideoFramerate[COMM_vars.Framerate])
        self.SSBar_update()

    def on_ComboBoxText_Rotate_changed(self, widget):
        CAM0_control.Flip = widget.get_active()

    def on_ComboBoxText_Abitrate_changed(self, widget):
        COMM_vars.Abitrate = widget.get_active()
        Console.print("Audio Bitrate:", AudioBitrate[COMM_vars.Abitrate])
        self.SSBar_update()

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

    def on_Menu_CamRes_Item_activate(self, widget):
        if widget.get_active() is True:
            w_id = int(widget.get_name())
            if self.ComboBoxResolution.get_active != w_id:
                self.ComboBoxResolution.set_active(w_id)
            if widget != self.Menu_CamRes_Item1:
                self.Menu_CamRes_Item1.set_active(False)
            if widget != self.Menu_CamRes_Item2:
                self.Menu_CamRes_Item2.set_active(False)
            if widget != self.Menu_CamRes_Item3:
                self.Menu_CamRes_Item3.set_active(False)
            if widget != self.Menu_CamRes_Item4:
                self.Menu_CamRes_Item4.set_active(False)
            if widget != self.Menu_CamRes_Item5:
                self.Menu_CamRes_Item5.set_active(False)

    def on_Menu_CamFx_Item_activate(self, widget):
        if widget.get_active() is True:
            COMM_vars.Fxmode = int(widget.get_name())
            if widget != self.Menu_CamFx_Item1:
                self.Menu_CamFx_Item1.set_active(False)
            if widget != self.Menu_CamFx_Item2:
                self.Menu_CamFx_Item2.set_active(False)
            if widget != self.Menu_CamFx_Item3:
                self.Menu_CamFx_Item3.set_active(False)
            if widget != self.Menu_CamFx_Item4:
                self.Menu_CamFx_Item4.set_active(False)
            if widget != self.Menu_CamFx_Item5:
                self.Menu_CamFx_Item5.set_active(False)
            if widget != self.Menu_CamFx_Item6:
                self.Menu_CamFx_Item6.set_active(False)
            if widget != self.Menu_CamFx_Item7:
                self.Menu_CamFx_Item7.set_active(False)

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

    def on_Button_AdvancedCam_clicked(self, widget):
        self.AdvancedCamWindow.show()

    def on_Window_Advanced_delete_event(self, bus, message):
        self.AdvancedWindow.hide()
        return True

    def SSBar_update(self):
        SStatBar = PROTO_NAME[Rac_connection.Protocol] + ": "
        SStatBar += VideoCodec[RacConnection.Video_Mode] + "/"
        SStatBar += VideoFramerate[COMM_vars.Framerate] + "  "
        SStatBar += AudioCodec[COMM_vars.Acodec] + "/"
        SStatBar += AudioBitrate[COMM_vars.Abitrate]

        self.StatusBar1.push(self.context_id1, SStatBar)

    def save_config(self):
        HostList = []
        HostListRaw = self.ComboBox_host.get_model()
        for iter_x in range(0, HostListRaw.iter_n_children()):
            HostList.append(HostListRaw[iter_x][0] + ":" + HostListRaw[iter_x][1])

        Compression_Mask = (self.Switch_Compression.get_active(),
                            self.ComboBoxText_Vcodec.get_active(),
                            self.ComboBoxText_Acodec.get_active(),
                            self.ComboBoxText_Framerate.get_active(),
                            self.ComboBoxText_Abitrate.get_active(),
                            self.ComboBoxText_Rotate.get_active())

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
                    self.CheckButton_localtest.get_active())

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
