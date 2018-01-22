#!/usr/bin/env python3.5
# -*- coding: CP1252 -*-
import datetime
import pickle
import gi
gi.require_version('Gtk', '3.0')
gi.require_version('Gdk', '3.0')
from gi.repository import Gtk, Gdk, GLib
from sys import argv

from ClientLib   import ConnectionThread, Console
from Client_vars import Paths, Debug, CAM0_control, KEY_control, CommunicationFFb
from Common_vars import VideoFramerate, AudioBitrate, AudioCodec, VideoCodec, \
    TIMEOUT_GUI, PROTO_NAME, LEFT, RIGHT, X_AXIS, Y_AXIS, MOUSE_MIN, MOUSE_MAX, COMM_vars, COMM_IDLE


# noinspection PyAttributeOutsideInit
class MainWindow(Gtk.Window):
    Console = Console()
    def __init__(self):
        super(MainWindow, self).__init__()

        self.builder = self.init_gui
        self.Window_Console.show()

        self.counter         = 0
        self.resolution      = 0
        self.Protocol        = 0
        self.camera_on       = True
        self.DispAvgVal      = [0, 0]
        self.context_id      = self.StatusBar.get_context_id("message")
        self.context_id1     = self.StatusBar1.get_context_id("message")
        self.context_id2     = self.StatusBar2.get_context_id("message")

        self.Console.print("Console 3.0 initialized.\n")

        SXID = self.DrawingArea_Cam.get_property('window')
        self.Connection_Thread = ConnectionThread(SXID)

        # Connect signals
        self.builder.connect_signals(self)

        configstorage.load_setup(self.builder)
        self.process_argv()

        if Debug > 2:
            print("Objects:")
            print(self.builder.get_objects().__str__())

    def process_argv(self):
        for x in range(1, len(argv)):
            if argv[x] == "reset":
                configstorage.reset(Paths.cfg_file)
            else:
                print("Invalid arument:", argv[x])
            pass

    @property
    def init_gui(self):
        builder = Gtk.Builder()
        print("Adding GUI file", Paths.GUI_file, end="... ")
        builder.add_from_file(Paths.GUI_file)
        print("done.")

        for obj in builder.get_objects():
            if issubclass(type(obj), Gtk.Buildable):
                name = Gtk.Buildable.get_name(obj)
                setattr(self, name, obj)
            else:
                print("WARNING: can not get name for '%s'" % obj)

        self.Window_Console.connect("destroy", self.gtk_main_quit)
        self.TextView_Log.override_color(Gtk.StateType.NORMAL, Gdk.RGBA(1, .75, 0, 1))
        self.TextView_Log.override_background_color(Gtk.StateType.NORMAL, Gdk.RGBA(.15, 0.15, 0.15, 1))
        self.DrawingArea_Cam.set_can_default(True)

        return builder

    def connect_gui(self):
        self.ComboBox_Host.set_sensitive(False)
        self.SpinButton_Port.set_sensitive(False)
        self.CheckButton_LocalTest.set_sensitive(False)
        self.CheckButton_SshTunnel.set_sensitive(False)

    def connect_gui_handlers(self):
        # self.on_mouse_press_handler = self.connect("button-press-event", self.on_mouse_press)
        # self.on_mouse_release_handler = self.connect("button-release-event", self.on_mouse_release)
        # self.on_motion_notify_handler = self.connect("motion-notify-event", self.on_motion_notify)

        ####### Main loop definition ###############
        GLib.timeout_add(TIMEOUT_GUI, self.on_timer)
        ############################################

    def disconnect_gui(self):
        # if self.on_key_press_handler is not None:
        #     self.disconnect(self.on_key_press_handler)
        #     self.disconnect(self.on_key_release_handler)
        #     self.disconnect(self.on_mouse_press_handler)
        #     self.disconnect(self.on_mouse_release_handler)
        #     self.disconnect(self.on_motion_notify_handler)

        self.ToggleButton_Connect.set_active(False)
        self.CheckButton_LocalTest.set_sensitive(True)
        # if Rac_connection.Test_Mode is False:
        self.ComboBox_Host.set_sensitive(True)
        self.SpinButton_Port.set_sensitive(True)
        self.CheckButton_SshTunnel.set_sensitive(True)

    ###############################################################################
    ################   MAIN LOOP START ############################################
    ###############################################################################
    def on_timer(self):
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

        if COMM_vars.connected:
            self.counter += .05
            return True
        else:
            self.counter = 0
            return False

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

    def on_Window_Console_key_press_event(self, widget, event):
        self.keybuffer_set(event, True)
        return True

    def on_Window_Console_key_release_event(self, widget, event):
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

    def gtk_main_quit(self, dialog):
        self.Connection_Thread.close_connection()
        configstorage.save_setup(self.builder)

        Gtk.main_quit()

###############################################################################


class configstorage:
    @staticmethod
    def load_setup(builder):
        with open(Paths.ini_file, "rb") as iniFile:
            SetupVar = pickle.load(iniFile)
            for v_list, name, value in SetupVar:
                for obj in builder.get_objects():
                    if issubclass(type(obj), Gtk.Buildable):
                        if name != Gtk.Buildable.get_name(obj):
                            continue

                        if type(obj) == Gtk.CheckButton:
                            obj.set_active(value)
                            continue

                        if type(obj) == Gtk.CheckMenuItem:
                            obj.set_active(value)
                            continue

                        if type(obj) == Gtk.ComboBoxText:
                            if name == "ComboBox_Host":
                                for Host in v_list:
                                    obj.append(Host[1], Host[0])
                            obj.set_active(value)
                            continue

                        if type(obj) == Gtk.SpinButton:
                            obj.set_value(value)
                            continue

                        if type(obj) == Gtk.Entry:
                            obj.set_text(value)
                            continue

                        if type(obj) == Gtk.Scale:
                            obj.set_value_pos(value)
                            continue

        print("Configuration loaded.")

    @staticmethod
    def save_setup(builder):
        SetupVar = []
        for obj in builder.get_objects():
            if issubclass(type(obj), Gtk.Buildable):
                name = Gtk.Buildable.get_name(obj)
            else:
                continue

            if type(obj) == Gtk.CheckButton:
                SetupVar.append((None, name, obj.get_active()))
                continue

            if type(obj) == Gtk.CheckMenuItem:
                SetupVar.append((None, name, obj.get_active()))
                continue

            if type(obj) == Gtk.ComboBoxText:
                HostList = []
                if name == "ComboBox_Host":
                    HostListRaw = obj.get_model()
                    for iter_x in range(0, HostListRaw.iter_n_children()):
                        HostList.append((HostListRaw[iter_x][0], HostListRaw[iter_x][1]))

                SetupVar.append((tuple(HostList), name, obj.get_active()))
                continue

            if type(obj) == Gtk.SpinButton:
                SetupVar.append((None, name, obj.get_value_as_int()))
                continue

            if type(obj) == Gtk.Entry:
                SetupVar.append((None, name, obj.get_text()))
                continue

            if type(obj) == Gtk.Scale:
                SetupVar.append((None, name, obj.get_value_pos()))
                continue

        with open(Paths.ini_file, "wb") as iniFile:
            pickle.dump(SetupVar, iniFile)
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
