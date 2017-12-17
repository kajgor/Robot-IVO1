#!/usr/bin/env python3.5
# -*- coding: CP1252 -*-
import datetime
import pickle
import gi
gi.require_version('Gtk', '3.0')
gi.require_version('Gdk', '3.0')
from gi.repository import Gtk, Gdk, GLib

from ClientLib   import ConnectionThread, Console
from Client_vars import Paths, Debug, CAM0_control, KEY_control, CommunicationFFb
from Common_vars import VideoFramerate, AudioBitrate, AudioCodec, VideoCodec, \
    TIMEOUT_GUI, PROTO_NAME, LEFT, RIGHT, X_AXIS, Y_AXIS, MOUSE_MIN, MOUSE_MAX, COMM_vars, COMM_IDLE


# noinspection PyAttributeOutsideInit
class MainWindow(Gtk.Window):
    def __init__(self):
        super(MainWindow, self).__init__()

        builder = self.init_vars

        self.counter         = 0
        self.context_id      = self.StatusBar.get_context_id("message")
        self.context_id1     = self.StatusBar1.get_context_id("message")
        self.context_id2     = self.StatusBar2.get_context_id("message")
        self.camera_on       = True
        self.resolution      = 0
        self.Protocol        = 0
        self.DispAvgVal      = [0, 0]
        self.Console         = Console()

        self.Console.print("Console 3.0 initialized.\n")

        ####### Main loop definition ###############
        GLib.timeout_add(TIMEOUT_GUI, self.on_timer)
        ############################################
        self.init_ui()

        CAMXPROP = self.LiveCam_window.get_property('window')
        self.Connection_Thread = ConnectionThread(CAMXPROP)

        # Connect signals
        builder.connect_signals(self)

        self.Host, self.Port = None, None
        # reset_save(Paths.cfg_file)
        HostList = self.load_config()

        self.init_config()

        self.Connection_Thread.load_HostList(self.ComboBox_host, HostList)

        if Debug > 2:
            print("Objects:")
            print(builder.get_objects().__str__())

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
        self.ComboBoxText_FxEffect  = builder.get_object("ComboBoxText_FxEffect")

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
        self.Menu_CamFx_Item0       = builder.get_object("Menu_CamFx_Item0")
        self.Menu_CamFx_Item1       = builder.get_object("Menu_CamFx_Item1")
        self.Menu_CamFx_Item2       = builder.get_object("Menu_CamFx_Item2")
        self.Menu_CamFx_Item3       = builder.get_object("Menu_CamFx_Item3")
        self.Menu_CamFx_Item4       = builder.get_object("Menu_CamFx_Item4")
        self.Menu_CamFx_Item5       = builder.get_object("Menu_CamFx_Item5")
        self.Menu_CamFx_Item6       = builder.get_object("Menu_CamFx_Item6")
        self.Menu_CamFx_Item7       = builder.get_object("Menu_CamFx_Item7")
        self.Menu_CamFx_Item8       = builder.get_object("Menu_CamFx_Item8")
        self.Menu_CamFx_Item9       = builder.get_object("Menu_CamFx_Item9")
        self.Menu_CamFx_Item10      = builder.get_object("Menu_CamFx_Item10")
        self.Menu_CamFx_Item11      = builder.get_object("Menu_CamFx_Item11")
        self.Menu_CamFx_Item12      = builder.get_object("Menu_CamFx_Item12")
        self.Menu_CamFx_Item13      = builder.get_object("Menu_CamFx_Item13")
        self.Menu_CamFx_Item14      = builder.get_object("Menu_CamFx_Item14")
        self.Menu_CamFx_Item15      = builder.get_object("Menu_CamFx_Item15")

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
        self.on_key_press_handler = self.connect("key-press-event", self.on_key_press)
        self.on_key_release_handler = self.connect("key-release-event", self.on_key_release)
        self.on_mouse_press_handler = self.connect("button-press-event", self.on_mouse_press)
        self.on_mouse_release_handler = self.connect("button-release-event", self.on_mouse_release)
        self.on_motion_notify_handler = self.connect("motion-notify-event", self.on_motion_notify)

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
        Local_Test = configstorage.read(Paths.cfg_file)

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
        # self.ComboBoxText_Rotate.set_active(Compression[5])
        self.ComboBoxText_Proto.set_active(Network)
        self.CheckButton_localtest.set_active(Local_Test)

        return HostList

    def init_config(self):
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

    ###############################################################################
    ################   MAIN LOOP START ############################################
    ###############################################################################
    def on_timer(self):
        if COMM_vars.connected:
            self.counter += .05

        if COMM_vars.comm_link_idle > COMM_IDLE:
            self.Spinner_connection.stop()
            COMM_vars.comm_link_idle = COMM_IDLE  # Do not need to increase counter anymore
        else:
            self.Spinner_connection.start()

        # Idle timer for checking the link
        COMM_vars.comm_link_idle += 1

        # Any update tasks would go here (moving sprites, advancing animation frames etc.)
        self.UpdateControlData()
        self.UpdateMonitorData()
        self.Console.display_message(self.TextView_Log)

        self.StatusBar2.push(self.context_id2, str(datetime.timedelta(seconds=int(self.counter))))
        self.DrawingArea_control.queue_draw()

        if COMM_vars.connected is True:
            if CommunicationFFb is False:
                ConnectionThread.get_speed_and_direction()  # Keyboard input
                ConnectionThread.calculate_MotorPower()
                ConnectionThread.mouseInput()  # Mouse input
        else:
            if self.ToggleButton_connect.get_active() is True:
                self.ToggleButton_connect.set_active(False)
                # self.on_ToggleButton_Connect_toggled(self.ToggleButton_Connect)

        return True

    def UpdateMonitorData(self):
        self.LabelRpmL.set_text(COMM_vars.motor_RPM[LEFT].__str__())
        self.LabelRpmR.set_text(COMM_vars.motor_RPM[RIGHT].__str__())
        self.LabelPowerL.set_text(COMM_vars.motor_PWR[LEFT].__str__())
        self.LabelPowerR.set_text(COMM_vars.motor_PWR[RIGHT].__str__())
        self.LabelRpmReqL.set_text(COMM_vars.motor_Power[LEFT].__str__())
        self.LabelRpmReqR.set_text(COMM_vars.motor_Power[RIGHT].__str__())
        self.LabelRpmAckL.set_text(COMM_vars.motor_ACK[LEFT].__str__())
        self.LabelRpmAckR.set_text(COMM_vars.motor_ACK[RIGHT].__str__())
        self.LabelCamPosH.set_text(COMM_vars.camPosition[X_AXIS].__str__())
        self.LabelCamPosV.set_text(COMM_vars.camPosition[Y_AXIS].__str__())

        self.LabelCoreTemp.set_text("{:.2f}".format(COMM_vars.coreTemp).__str__())
        self.LabelBattV.set_text("{:.2f}".format(COMM_vars.voltage).__str__())
        self.LabelPowerA.set_text("{:.2f}".format(COMM_vars.current).__str__())
        self.LabelS1Dist.set_text(COMM_vars.distanceS1.__str__())

        return

    def UpdateControlData(self):
        self.DispAvgVal[0] = (self.DispAvgVal[0] * 4 + COMM_vars.voltage) / 5
        self.DispAvgVal[1] = (self.DispAvgVal[1] * 4 + COMM_vars.current) / 5
        self.LevelBar_Voltage.set_value(self.DispAvgVal[0])
        self.LevelBar_Current.set_value(self.DispAvgVal[1])
        self.LeverBar_PowerL.set_value(COMM_vars.motor_PWR[LEFT])
        self.LeverBar_PowerR.set_value(COMM_vars.motor_PWR[RIGHT])

        return

###############################################################################
################   MAIN LOOP END   ############################################
###############################################################################

    # @staticmethod
    def on_DrawingArea_Control_draw(self, bus, message):
        # pass
        self.Connection_Thread.draw_arrow(message)

    def on_ComboBox_Host_changed(self, widget):
        # print("widget", widget.get_model()[widget.get_active()][1])
        self.Host = widget.get_active_text()
        self.Port = int(float(widget.get_model()[widget.get_active()][1]))
        self.SpinButton_port.set_value(self.Port)

    def on_SpinButton_Port_value_changed(self, widget):
        self.Port = widget.get_value_as_int()

    def on_CheckButton_LocalTest_toggled(self, widget):
        self.Connection_Thread.Video_Mode = not(widget.get_active())
        self.Connection_Thread.Video_Codec = bool(self.Protocol + self.Connection_Thread.Video_Mode)
        self.SSBar_update()

    def on_ComboBoxText_Proto_changed(self, widget):
        self.Protocol = widget.get_active()
        self.SSBar_update()

    def on_ToggleButton_Connect_toggled(self, widget):
        self.on_key_press_handler = None
        if widget.get_active() is True:
            widget.set_label(Gtk.STOCK_DISCONNECT)
            self.connect_gui()

            if self.CheckButton_SshTunnel.get_active() is True:
                Host, Port = self.Connection_Thread.open_ssh_tunnel(self.Host, self.Port,
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
                success, retmsg = self.Connection_Thread.establish_connection(Host, Port, self.Protocol)

                if success is True:
                    self.connect_gui_handlers()
                    self.Connection_Thread.update_server_list(self.ComboBox_host, self.SpinButton_port.get_value())

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

    def on_ComboBoxText_FxEffect_changed(self, widget):
        self.Connection_Thread.FXmode   = 8
        self.Connection_Thread.FXvalue  = widget.get_active()

        if self.Connection_Thread.FXvalue == 0:
            self.Menu_CamFx_Item0.set_active(True)
        if self.Connection_Thread.FXvalue == 1:
            self.Menu_CamFx_Item1.set_active(True)
        if self.Connection_Thread.FXvalue == 2:
            self.Menu_CamFx_Item2.set_active(True)
        if self.Connection_Thread.FXvalue == 3:
            self.Menu_CamFx_Item3.set_active(True)
        if self.Connection_Thread.FXvalue == 4:
            self.Menu_CamFx_Item4.set_active(True)
        if self.Connection_Thread.FXvalue == 5:
            self.Menu_CamFx_Item5.set_active(True)
        if self.Connection_Thread.FXvalue == 6:
            self.Menu_CamFx_Item6.set_active(True)
        if self.Connection_Thread.FXvalue == 7:
            self.Menu_CamFx_Item7.set_active(True)
        if self.Connection_Thread.FXvalue == 8:
            self.Menu_CamFx_Item8.set_active(True)
        if self.Connection_Thread.FXvalue == 9:
            self.Menu_CamFx_Item9.set_active(True)
        if self.Connection_Thread.FXvalue == 10:
            self.Menu_CamFx_Item10.set_active(True)
        if self.Connection_Thread.FXvalue == 11:
            self.Menu_CamFx_Item11.set_active(True)
        if self.Connection_Thread.FXvalue == 12:
            self.Menu_CamFx_Item12.set_active(True)
        if self.Connection_Thread.FXvalue == 13:
            self.Menu_CamFx_Item13.set_active(True)
        if self.Connection_Thread.FXvalue == 14:
            self.Menu_CamFx_Item14.set_active(True)
        if self.Connection_Thread.FXvalue == 15:
            self.Menu_CamFx_Item15.set_active(True)

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

    def on_ComboBoxText_h264BitRateMode_changed(self, widget):
        self.Connection_Thread.FXmode   = 10
        self.Connection_Thread.FXvalue  = widget.get_active()

    def on_SpinButton_h264BitRate_change_value(self, widget):
        self.Connection_Thread.FXmode   = 11
        self.Connection_Thread.FXvalue  = widget.get_active()

    def on_CheckButton_h264Header_toggled(self, widget):
        self.Connection_Thread.FXmode   = 12
        self.Connection_Thread.FXvalue  = widget.get_active()

    def on_ComboBoxText_h264Level_changed(self, widget):
        self.Connection_Thread.FXmode   = 14
        self.Connection_Thread.FXvalue  = widget.get_active()

    def on_ComboBoxText_h264Profile_changed(self, widget):
        self.Connection_Thread.FXmode   = 15
        self.Connection_Thread.FXvalue  = widget.get_active()

    def on_ComboBoxText_ExpMeteringMode_changed(self, widget):
        self.Connection_Thread.FXmode   = 24
        self.Connection_Thread.FXvalue  = widget.get_active()

    def on_ComboBoxText_SceneMode_changed(self, widget):
        self.Connection_Thread.FXmode   = 25
        self.Connection_Thread.FXvalue  = widget.get_active()

    def on_SpinButton_JpgComprQuality_change_value(self, widget):
        self.Connection_Thread.FXmode   = 26
        self.Connection_Thread.FXvalue  = widget.get_active()

    def on_ComboBoxText_Vcodec_changed(self, widget):
        COMM_vars.Vcodec = widget.get_active()
        self.SSBar_update()

    def on_ComboBoxText_Acodec_changed(self, widget):
        COMM_vars.Acodec = widget.get_active()
        self.SSBar_update()

    def on_ComboBoxText_Framerate_changed(self, widget):
        COMM_vars.Framerate = widget.get_active()
        self.Console.print("Video Framerate:", VideoFramerate[COMM_vars.Framerate])
        self.SSBar_update()

    def on_ComboBoxText_Rotate_changed(self, widget):
        CAM0_control.Flip = widget.get_active()

    def on_ComboBoxText_Abitrate_changed(self, widget):
        COMM_vars.Abitrate = widget.get_active()
        self.Console.print("Audio Bitrate:", AudioBitrate[COMM_vars.Abitrate])
        self.SSBar_update()

    def on_CheckButton_Speakers_toggled(self, widget):
        COMM_vars.speakers = widget.get_active()
        self.Console.print("Speakers:", COMM_vars.speakers)

    def on_CheckButton_Display_toggled(self, widget):
        COMM_vars.display = widget.get_active()
        self.Console.print("Display:", COMM_vars.display)

    def on_CheckButton_Lights_toggled(self, widget):
        COMM_vars.light = widget.get_active()
        self.Console.print("Light:", COMM_vars.light)

    def on_CheckButton_Mic_toggled(self, widget):
        COMM_vars.mic = widget.get_active()
        self.Console.print("Mic:", COMM_vars.mic)

    def on_CheckButton_Laser_toggled(self, widget):
        COMM_vars.laser = widget.get_active()
        self.Console.print("Laser:", COMM_vars.laser)

    def on_ToggleButton_Log_toggled(self, widget):
        if widget.get_active() is True:
            self.LogWindow.show()
        else:
            self.LogWindow.hide()

    def on_Menu_CamRes_Item_activate(self, widget):
        if widget.get_active() is True:
            w_id = int(widget.get_name())
            if self.ComboBoxResolution.get_active() != w_id:
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
            w_id = int(widget.get_name())
            if self.ComboBoxText_FxEffect.get_active() != w_id:
                self.ComboBoxText_FxEffect.set_active(w_id)
            if widget != self.Menu_CamFx_Item0:
                self.Menu_CamFx_Item0.set_active(False)
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
            if widget != self.Menu_CamFx_Item8:
                self.Menu_CamFx_Item8.set_active(False)
            if widget != self.Menu_CamFx_Item9:
                self.Menu_CamFx_Item9.set_active(False)
            if widget != self.Menu_CamFx_Item10:
                self.Menu_CamFx_Item10.set_active(False)
            if widget != self.Menu_CamFx_Item11:
                self.Menu_CamFx_Item11.set_active(False)
            if widget != self.Menu_CamFx_Item12:
                self.Menu_CamFx_Item12.set_active(False)
            if widget != self.Menu_CamFx_Item13:
                self.Menu_CamFx_Item13.set_active(False)
            if widget != self.Menu_CamFx_Item14:
                self.Menu_CamFx_Item14.set_active(False)
            if widget != self.Menu_CamFx_Item15:
                self.Menu_CamFx_Item15.set_active(False)
        # else:
        #     widget.set_active(False)

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
        SStatBar = PROTO_NAME[self.Protocol] + ": "
        SStatBar += VideoCodec[self.Connection_Thread.Video_Codec] + "/"
        SStatBar += VideoFramerate[COMM_vars.Framerate] + "  "
        SStatBar += AudioCodec[COMM_vars.Acodec] + "/"
        SStatBar += AudioBitrate[COMM_vars.Abitrate]

        self.StatusBar1.push(self.context_id1, SStatBar)

    def on_key_press(self, widget, event):
        self.keybuffer_set(event, True)
        return True

    def on_key_release(self, widget, event):
        key_name = self.keybuffer_set(event, False)
        return key_name

    @staticmethod
    def keybuffer_set(event, value):
        key_name = Gdk.keyval_name(event.keyval)
        if key_name == "Left" or key_name.replace("A", "a", 1) == "a":
            KEY_control.Left = value

        elif key_name == "Right" or key_name.replace("D", "d", 1) == "d":
            KEY_control.Right = value

        elif key_name == "Up" or key_name.replace("W", "w", 1) == "w":
            KEY_control.Up = value

        elif key_name == "Down" or key_name.replace("S", "s", 1) == "s":
            KEY_control.Down = value

        elif key_name == "space":
            COMM_vars.speed = 0
            COMM_vars.direction = 0
            KEY_control.Space = value

        if event.state is True and Gdk.KEY_Shift_L is not KEY_control.Shift:
            KEY_control.Shift = Gdk.KEY_Shift_L
            # self.Console.print("SHIFT!!!")

        return key_name

    def on_mouse_press(self, widget, mouse_event):
        self.mousebuffer_set(mouse_event, True)

    def on_mouse_release(self, widget, mouse_event):
        self.mousebuffer_set(mouse_event, False)

    def mousebuffer_set(self, mouse_event, value):
        if mouse_event.button == Gdk.BUTTON_PRIMARY:
            KEY_control.MouseBtn[LEFT] = value
            if value is True:
                KEY_control.MouseXY = [int(mouse_event.x),
                                       int(mouse_event.y)]

        if mouse_event.button == Gdk.BUTTON_SECONDARY:
            KEY_control.MouseBtn[RIGHT] = value
            self.Menu_CamOptions.popup(None, None, None, None, Gdk.BUTTON_SECONDARY, mouse_event.time)
            self.last_MouseButtonR = KEY_control.MouseBtn[RIGHT]

    def on_motion_notify(self, widget, mouse_event):
        mouseX = int(mouse_event.x)
        mouseY = int(mouse_event.y)
        if KEY_control.MouseBtn[LEFT] is True:
            tmp = (KEY_control.MouseXY[X_AXIS] - mouseX) / 2
            if abs(tmp) >= 1:
                if COMM_vars.camPosition[X_AXIS] + tmp > MOUSE_MAX[X_AXIS]:
                    COMM_vars.camPosition[X_AXIS] = MOUSE_MAX[X_AXIS]
                elif COMM_vars.camPosition[X_AXIS] + tmp < MOUSE_MIN[X_AXIS]:
                    COMM_vars.camPosition[X_AXIS] = MOUSE_MIN[X_AXIS]
                else:
                    COMM_vars.camPosition[X_AXIS] += int(tmp)

            tmp = (mouseY - KEY_control.MouseXY[Y_AXIS]) / 2
            if abs(tmp) >= 1:
                if COMM_vars.camPosition[Y_AXIS] + tmp > MOUSE_MAX[Y_AXIS]:
                    COMM_vars.camPosition[Y_AXIS] = MOUSE_MAX[Y_AXIS]
                elif COMM_vars.camPosition[Y_AXIS] + tmp < MOUSE_MIN[Y_AXIS]:
                    COMM_vars.camPosition[Y_AXIS] = MOUSE_MIN[Y_AXIS]
                else:
                    COMM_vars.camPosition[Y_AXIS] += int(tmp)

            KEY_control.MouseXY = [mouseX, mouseY]

        # if KEY_control.MouseBtn[RIGHT] is True:
        #     self.Console.print("KEY_control.MouseXY[right]", KEY_control.MouseXY)

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

        configstorage.save(Paths.cfg_file, tuple(HostList),
                    False,
                    False,
                    False,
                    Network_Mask,
                    Compression_Mask,
                    Ssh_Mask,
                    False,
                    self.CheckButton_localtest.get_active())

    def gtk_main_quit(self, dialog):
        self.Connection_Thread.close_connection()
        # Host_list = Rac_connection.HostList_get(self.combobox_host.get_model(), None)
        # Rac_connection.config_snapshot(Host_list)
        self.save_config()

        Gtk.main_quit ()

###############################################################################
# def main():


class configstorage:
    @staticmethod
    def read(filename):
        with open(filename, "rb") as iniFile:
            HostList = pickle.load(iniFile)
            Mask1 = pickle.load(iniFile)
            RSA_Key = pickle.load(iniFile)
            Key_Pass = pickle.load(iniFile)
            Ssh_User = pickle.load(iniFile)
            Remote_Host = pickle.load(iniFile)
            Compression = pickle.load(iniFile)
            Reserved_6 = pickle.load(iniFile)
            Reserved_7 = pickle.load(iniFile)
            Local_Test = pickle.load(iniFile)
            END_CFG = pickle.load(iniFile)

            COMM_vars.resolution = Mask1[0]
            COMM_vars.light = Mask1[1]
            COMM_vars.mic = Mask1[2]
            COMM_vars.display = Mask1[3]
            COMM_vars.speakers = Mask1[4]
            COMM_vars.laser = Mask1[5]
            COMM_vars.AutoMode = Mask1[6]

        print("Configuration read from", filename)
        return HostList, \
               Mask1, \
               RSA_Key, \
               Key_Pass, \
               Ssh_User, \
               Remote_Host, \
               Compression, \
               Reserved_6, \
               Reserved_7, \
               Local_Test

    @staticmethod
    def save(filename, HostList, RSA_Key, Key_Pass, Ssh_User, Remote_Host,
                    Compression, Reserved_6, Reserved_7, Local_Test):
        with open(filename, "wb") as iniFile:
            # print("HostList", HostList)

            Mask1 = (COMM_vars.resolution,
                     COMM_vars.light,
                     COMM_vars.mic,
                     COMM_vars.display,
                     COMM_vars.speakers,
                     COMM_vars.laser,
                     COMM_vars.AutoMode)

            for item in [HostList,
                         Mask1,
                         RSA_Key,
                         Key_Pass,
                         Ssh_User,
                         Remote_Host,
                         Compression,
                         Reserved_6,
                         Reserved_7,
                         Local_Test,
                         "END"]:
                pickle.dump(item, iniFile)
        print("Configuration saved.")

    @staticmethod
    def reset(filename):
        with open(filename, "wb") as iniFile:
            for item in (("localhost:4550:True", "10.0.0.23:4550:False", "athome106.hopto.org:222:True"),
                         (1, False, False, False, False, False, False, False),
                         "/home/igor/.ssh/id_rsa",
                         "nescape",
                         "igor",
                         "127.0.0.1",
                         True,
                         False,
                         False,
                         True,
                         "END"):
                pickle.dump(item, iniFile)
        print("Configuration reset.")


if __name__ == "__main__":
    MainWindow()
    Gtk.main()
