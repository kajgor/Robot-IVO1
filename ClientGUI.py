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
    Console = Console()
    def __init__(self):
        super(MainWindow, self).__init__()

        builder = self.init_gui

        self.counter         = 0
        self.context_id      = self.StatusBar.get_context_id("message")
        self.context_id1     = self.StatusBar1.get_context_id("message")
        self.context_id2     = self.StatusBar2.get_context_id("message")
        self.camera_on       = True
        self.resolution      = 0
        self.Protocol        = 0
        self.DispAvgVal      = [0, 0]

        self.Console.print("Console 3.0 initialized.\n")

        ####### Main loop definition ###############
        GLib.timeout_add(TIMEOUT_GUI, self.on_timer)
        ############################################
        self.init_ui()

        SXID = self.DrawingArea_Cam.get_property('window')
        self.Connection_Thread = ConnectionThread(SXID)

        # Connect signals
        builder.connect_signals(self)

        self.Host, self.Port = None, None
        # reset_save(Paths.cfg_file)
        HostList = self.load_config()

        self.init_config()

        self.Connection_Thread.load_HostList(self.ComboBox_Host, HostList)

        if Debug > 2:
            print("Objects:")
            print(builder.get_objects().__str__())

    @property
    def init_gui(self):
        builder = Gtk.Builder()
        print("Adding GUI file", Paths.GUI_file, end="... ")
        builder.add_from_file(Paths.GUI_file)
        print("done.")

        # self.add(builder.get_object("MainBox_CON"))

        for obj in builder.get_objects():
            if issubclass(type(obj), Gtk.Buildable):
                name = Gtk.Buildable.get_name(obj)
                setattr(self, name, obj)
            else:
                print("WARNING: can not get name for '%s'" % obj)

        self.add(self.MainBox_CON)
        self.TextView_Log.override_color(Gtk.StateType.NORMAL, Gdk.RGBA(1, .75, 0, 1))
        self.TextView_Log.override_background_color(Gtk.StateType.NORMAL, Gdk.RGBA(.15, 0.15, 0.15, 1))

        return builder

    def init_ui(self):
        ###### Initiate UI start ######
        self.connect("destroy", self.gtk_main_quit)
        self.DrawingArea_Cam.set_can_default(True)
        # self.movie_window.set_size_request(640, 480)
        ####### Initiate UI end #######

        self.show_all()

    def connect_gui(self):
        self.ComboBox_Host.set_sensitive(False)
        self.SpinButton_Port.set_sensitive(False)
        self.CheckButton_LocalTest.set_sensitive(False)
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

        self.ToggleButton_Connect.set_active(False)
        self.CheckButton_LocalTest.set_sensitive(True)
        # if Rac_connection.Test_Mode is False:
        self.ComboBox_Host.set_sensitive(True)
        self.SpinButton_Port.set_sensitive(True)
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

        self.CheckButton_Cam.set_active(bool(COMM_vars.resolution))
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
        self.ComboBoxText_Ssh_Compression.set_active(Compression[0])
        self.ComboBoxText_Vcodec.set_active(Compression[1])
        self.ComboBoxText_Acodec.set_active(Compression[2])
        self.ComboBoxText_Framerate.set_active(Compression[3])
        self.ComboBoxText_Abitrate.set_active(Compression[4])
        # self.ComboBoxText_Rotate.set_active(Compression[5])
        self.ComboBoxText_Proto.set_active(Network)
        self.CheckButton_LocalTest.set_active(Local_Test)

        return HostList

    def init_config(self):
        self.on_ComboBoxText_Proto_changed(self.ComboBoxText_Proto)
        self.on_ComboBoxResolution_changed(self.ComboBoxResolution)
        self.on_ComboBoxText_Vcodec_changed(self.ComboBoxText_Vcodec)
        self.on_ComboBoxText_Acodec_changed(self.ComboBoxText_Acodec)
        self.on_ComboBoxText_Framerate_changed(self.ComboBoxText_Framerate)
        self.on_ComboBoxText_Abitrate_changed(self.ComboBoxText_Abitrate)
        self.on_ComboBoxText_Rotate_changed(self.ComboBoxText_Rotate)
        self.on_CheckButton_LocalTest_toggled(self.CheckButton_LocalTest)
        self.on_CheckButton_Mic_toggled(self.CheckButton_Mic)
        self.on_CheckButton_Speakers_toggled(self.CheckButton_Display)

    ###############################################################################
    ################   MAIN LOOP START ############################################
    ###############################################################################
    def on_timer(self):
        if COMM_vars.connected:
            self.counter += .05

        if COMM_vars.comm_link_idle > COMM_IDLE:
            self.Spinner_Connected.stop()
            COMM_vars.comm_link_idle = COMM_IDLE  # Do not need to increase counter anymore
        else:
            self.Spinner_Connected.start()

        # Idle timer for checking the link
        COMM_vars.comm_link_idle += 1

        # Any update tasks would go here (moving sprites, advancing animation frames etc.)
        self.UpdateControlData()
        self.UpdateMonitorData()
        self.Console.display_message(self.TextView_Log)

        self.StatusBar2.push(self.context_id2, str(datetime.timedelta(seconds=int(self.counter))))
        self.DrawingArea_Control.queue_draw()

        if COMM_vars.connected is True:
            if CommunicationFFb is False:
                ConnectionThread.get_speed_and_direction()  # Keyboard input
                ConnectionThread.calculate_MotorPower()
                ConnectionThread.mouseInput()  # Mouse input
        else:
            if self.ToggleButton_Connect.get_active() is True:
                self.ToggleButton_Connect.set_active(False)
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
        self.SpinButton_Port.set_value(self.Port)

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
                                                                    self.ComboBoxText_Ssh_Compression.get_active())
            else:
                Host, Port = self.Host, self.Port

            success = bool(Host)
            retmsg = "SSH Connection Error!"
            if success is True:
                success, retmsg = self.Connection_Thread.establish_connection(Host, Port, self.Protocol)

                if success is True:
                    self.connect_gui_handlers()
                    self.Connection_Thread.update_server_list(self.ComboBox_Host, self.SpinButton_Port.get_value())

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
            self.DrawingArea_Cam.set_size_request(640, 480)
            self.Menu_CamRes_Item1.set_active(True)
        if self.resolution == 2:
            self.DrawingArea_Cam.set_size_request(640, 480)
            self.Menu_CamRes_Item2.set_active(True)
        if self.resolution == 3:
            self.DrawingArea_Cam.set_size_request(800, 600)
            self.Menu_CamRes_Item3.set_active(True)
        if self.resolution == 4:
            self.DrawingArea_Cam.set_size_request(1024, 768)
            self.Menu_CamRes_Item4.set_active(True)
        if self.resolution == 5:
            self.DrawingArea_Cam.set_size_request(1152, 864)
            self.Menu_CamRes_Item5.set_active(True)

        COMM_vars.resolution = self.resolution * self.camera_on

    def on_FxValue_changed(self, widget):
        self.Connection_Thread.FXmode   = int(widget.get_name())
        self.Connection_Thread.FXvalue  = int(widget.get_active())

    def on_FxValue_spinned(self, widget):
        self.Connection_Thread.FXmode   = int(widget.get_name())
        if self.Connection_Thread.FXmode == 11:
            self.Connection_Thread.FXvalue = int(widget.get_value()) / 1000
        else:
            self.Connection_Thread.FXvalue  = int(widget.get_value())


    def on_FxValue_scrolled(self, widget, event):
        if KEY_control.MouseBtn[LEFT] is True:
            self.Connection_Thread.FXmode   = int(widget.get_name())
            if self.Connection_Thread.FXmode < 4:   # Avoid negative values to be sent for Brightness, Contrast & Saturation
                self.Connection_Thread.FXvalue  = int(widget.get_value()) + 100
            else:
                self.Connection_Thread.FXvalue  = int(widget.get_value())

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
            self.Window_Log.show()
        else:
            self.Window_Log.hide()

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
        self.Window_Advanced.hide()

    def on_Button_AdvOk_clicked(self, widget):
        self.Window_Advanced.hide()

    def on_Button_Preferences_clicked(self, widget):
        self.Window_Advanced.show()
        # print("TEXT IN COMBOBOX: ", self.combobox_host.get_active_text())
        # print("NO OF ITEMS:", self.combobox_host.get_model().iter_n_children())
        # Host_list = Rac_connection.HostList_get(self.combobox_host.get_model(), None)
        # Rac_connection.config_snapshot(Host_list)
        # reset_save(Paths.cfg_file)

    def on_Button_AdvancedCam_clicked(self, widget):
        self.Window_AdvancedCam.show()

    def on_Window_Advanced_delete_event(self, bus, message):
        self.Window_Advanced.hide()
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
        HostListRaw = self.ComboBox_Host.get_model()
        for iter_x in range(0, HostListRaw.iter_n_children()):
            HostList.append(HostListRaw[iter_x][0] + ":" + HostListRaw[iter_x][1])

        Compression_Mask = (self.ComboBoxText_Ssh_Compression.get_active(),
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
                           self.CheckButton_LocalTest.get_active())

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
