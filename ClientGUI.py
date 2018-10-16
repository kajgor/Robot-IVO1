#!/usr/bin/env python3
# -*- coding: CP1252 -*-
import datetime
import pickle
import gi
gi.require_version('Gtk', '3.0')
gi.require_version('Gdk', '3.0')
from gi.repository import Gtk, Gdk, GLib
from sys import argv

from ClientLib import ConnectionThread, Console, SenderStream, ReceiverStream
from Client_vars import Files, DEVICE_control, KEY_control, CommunicationFFb
from Common_vars import VideoFramerate, AudioBitrate, AudioCodec, VideoCodec, PrintOnOff, execute_cmd,\
    TIMEOUT_GUI, PROTO_NAME, LEFT, RIGHT, X_AXIS, Y_AXIS, MOUSE_MIN, MOUSE_MAX, ConnectionData, COMM_IDLE,\
    CAM_1_CMD, DEV_OUT_CMD, DEV_INP_CMD
from v4l2Gtk import v4l2Gtk

# noinspection PyAttributeOutsideInit
class MainWindow(Gtk.Window):
    Console = Console()
    Sender_Stream = None
    Host = "0.0.0.0"
    Port = 0

    def __init__(self):
        super(MainWindow, self).__init__()

        self.counter         = 0
        self.resolution      = 0
        self.camera_on       = True
        self.SyncOn          = True
        self.DispAvgVal      = [0, 0]

        cmd = 'tail -3 %s | grep -aF \.glade | grep -v ^#####' % Files.ini_file
        GuiFile, err         = execute_cmd(cmd)
        self.builder         = self.init_gui_builder(GuiFile)
        self.context_id      = self.StatusBar.get_context_id('message')
        self.context_id1     = self.StatusBar1.get_context_id('message')
        self.context_id2     = self.StatusBar2.get_context_id('message')

        # Init v4l2 panel
        self.load_v4l2_panel()

        # Connect signals
        self.builder.connect_signals(self)

        self.Window_Console.show()
        self.P_SXID = self.DrawingArea_Cam.get_property('window')
        self.S_SXID = self.DrawingArea_Disp.get_property('window')

        # print("SXID0: %s" % P_SXID)
        # print("SXID1: %s" % S_SXID)
        self.Sender_Stream     = SenderStream(self.S_SXID)
        self.Receiver_Stream   = ReceiverStream(self.P_SXID)
        self.Connection_Thread = ConnectionThread()

        Console.print('Console 3.0 initialized.\n')

        self.Config_Storage = ConfigStorage()
        if self.get_argv('reset') is False:
            self.RunSeqNo, self.SyncItemCount = self.Config_Storage.load_setup(self.builder)
            self.Entry_SkinFile.set_text(GuiFile)

            if self.TreeView_Hosts.get_model() is None:
                for i, column in enumerate(["Host", "Port"]):
                    cell = Gtk.CellRendererText()
                    if i == 0:
                        pass
                    col = Gtk.TreeViewColumn(column, cell, text=i)
                    self.TreeView_Hosts.append_column(col)

                obj = Gtk.ListStore(str, int)
                self.TreeView_Hosts.set_model(obj)

            self.ComboBox_Host.set_model(self.TreeView_Hosts.get_model())
            self.ComboBox_Host.set_active(0)
            self.StatusBar.push(self.context_id, '[%s-th configuration load]' % str(self.RunSeqNo))
        else:
            self.SyncItemCount = 0
            self.Console.print('Resetting to default configuration.')
            self.StatusBar.push(self.context_id, 'Resetting to default configuration.')

        Proto = self.ComboBoxText_Proto.get_active()
        self.Sender_Stream.set_video_source(Proto)
        self.Sender_Stream.set_audio_source(Proto)
        self.Sender_Stream.CliCamera_gtksync()

        self.load_devices()

    def load_v4l2_panel(self):
        notebook = v4l2Gtk().v4l2Gtk()
        self.Grid_AdvancedDisp.attach(notebook, 0, 0, 1, 1)

        self.Window_AdvancedDisp.show_all()
        self.Window_AdvancedDisp.hide()

    @staticmethod
    def get_argv(checkval):
        for x in range(1, len(argv)):
            argtmp = argv[x].split("=")
            if argtmp[0] == checkval:
                if len(argtmp) > 1:
                    return argtmp[1]
                else:
                    return True
            # else:
            #     print("Invalid arument:", argv[x])
            # pass
        return False

    # @property
    def init_gui_builder(self, GuiFile):
        builder = Gtk.Builder()
        print('Adding GUI file', GuiFile, end='... ')
        builder.add_from_file(GuiFile)
        print('done.')

        for obj in builder.get_objects():
            if issubclass(type(obj), Gtk.Buildable):
                name = Gtk.Buildable.get_name(obj)
                setattr(self, name, obj)
            else:
                print('WARNING: can not get name for "%s"' % obj)

        self.TextView_Log.override_color(Gtk.StateType.NORMAL, Gdk.RGBA(1, .75, 0, 1))
        self.TextView_Log.override_background_color(Gtk.StateType.NORMAL, Gdk.RGBA(.15, 0.15, 0.15, 1))

        return builder

    def gui_connect_loop(self):

        ####### Main loop definition ###############
        GLib.timeout_add(TIMEOUT_GUI, self.on_timer)
        ############################################

    def gui_update_connect(self):
        self.ComboBox_Host.set_sensitive(False)
        self.SpinButton_Port.set_sensitive(False)
        self.CheckButton_LocalTest.set_sensitive(False)
        self.CheckButton_SshTunnel.set_sensitive(False)
        self.ComboBoxText_Proto.set_sensitive(False)

    def gui_update_disconnect(self):
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
        self.ComboBoxText_Proto.set_sensitive(True)
        self.Spinner_Connected.stop()

    def SSBar_update(self):
        SStatBar = PROTO_NAME[ConnectionData.Protocol] + ": "
        SStatBar += VideoCodec[ConnectionData.Vcodec] + "/"
        SStatBar += VideoFramerate[ConnectionData.Framerate].__str__() + "  "
        SStatBar += AudioCodec[ConnectionData.Acodec] + "/"
        SStatBar += AudioBitrate[ConnectionData.Abitrate].__str__()

        self.StatusBar1.push(self.context_id1, SStatBar)

    def load_devices(self):
        fail = 0
        detected_devices, err = execute_cmd(CAM_1_CMD)
        detected_devices += "\nvideotestsrc"
        err  = self.set_device(detected_devices, self.ComboBoxText_Cam1, DEVICE_control.DEV_Cam0)
        if err:
            self.CheckButton_Show.set_active(False)
            self.CheckButton_Show.sensitive(False)
            fail += 1

        detected_devices, err = execute_cmd(DEV_INP_CMD)
        detected_devices += "\naudiotestsrc"
        err  = self.set_device(detected_devices, self.ComboBoxText_AudioIn, DEVICE_control.DEV_AudioIn)
        if err:
            self.CheckButton_Speakers.set_active(False)
            self.CheckButton_Speakers.sensitive(False)
            fail += 1

        detected_devices, err = execute_cmd(DEV_OUT_CMD)
        # detected_devices += "\nnull"
        fail += self.set_device(detected_devices, self.ComboBoxText_AudioOut, DEVICE_control.DEV_AudioOut)

        if fail > 0:
            self.MessageDialog_Warning.show()

    def set_device(self, detected_devices, widget, DevToMatch):
        active_item = 0
        if DevToMatch is None:
            Console.print("Warning: %s device set automatically as default." % Gtk.Buildable.get_name(widget).split('_')[1])

        LsDev = Gtk.ListStore(str, int)
        if detected_devices > "":
            for idx, DevName in enumerate(detected_devices.splitlines()):
                if DevName.find(":") == -1:
                    Dev = DevName
                else:
                    Dev = DevName.split(':')[1]

                if Dev == DevToMatch:
                    active_item = idx
                LsDev.append((DevName, idx))
            widget.set_model(LsDev)

            widget.set_active(active_item)

            return False
        else:
            return True

    ###############################################################################
    ################   MAIN LOOP START ############################################
    ###############################################################################
    def on_timer(self):
        # Idle timer for checking the link
        ConnectionData.comm_link_idle += 1

        # Update Hud & Control widgets
        if KEY_control.hud is True:
            self.DrawingArea_Cam.queue_draw()

        self.DrawingArea_Control.queue_draw()

        # Any update tasks would go here (moving sprites, advancing animation frames etc.)
        self.UpdateControlData()
        self.UpdateMonitorData()
        self.Console.display_message(self.TextView_Log)

        self.StatusBar2.push(self.context_id2, str(datetime.timedelta(seconds=int(self.counter))))

        if ConnectionData.connected is True:
            self.counter += .05

            if self.SyncOn:
                qSize = self.Connection_Thread.FxQueue.qsize()
                if qSize is 0:
                    self.SyncOn = False
                    self.ProgressBar_SsBar.hide()
                    self.StatusBar.push(self.context_id, "Sync completed!")
                    self.StatusBar1.show()
                else:
                    self.StatusBar1.hide()
                    self.ProgressBar_SsBar.show()
                    # print("q/c", qSize, self.SyncItemCount)
                    self.ProgressBar_SsBar.set_fraction((self.SyncItemCount - qSize) / self.SyncItemCount)

            if CommunicationFFb is False:
                ConnectionThread.get_speed_and_direction()  # Keyboard input
                ConnectionThread.calculate_MotorPower()
                ConnectionThread.mouseInput()  # Mouse input
            return True
        else:
            self.counter = 0
            if self.ToggleButton_Connect.get_active() is True:
                self.ToggleButton_Connect.set_active(False)
            if ConnectionData.comm_link_idle >= COMM_IDLE:
                ConnectionData.comm_link_idle = COMM_IDLE  # Do not need to increase counter anymore
                return True
            else:
                self.Spinner_Connected.stop()
                return False

    def UpdateMonitorData(self):
        self.LabelRpmL.set_text(ConnectionData.motor_RPM[LEFT].__str__())
        self.LabelRpmR.set_text(ConnectionData.motor_RPM[RIGHT].__str__())
        self.LabelPowerL.set_text(ConnectionData.motor_PWR[LEFT].__str__())
        self.LabelPowerR.set_text(ConnectionData.motor_PWR[RIGHT].__str__())
        self.LabelRpmReqL.set_text(ConnectionData.motor_Power[LEFT].__str__())
        self.LabelRpmReqR.set_text(ConnectionData.motor_Power[RIGHT].__str__())
        self.LabelRpmAckL.set_text(ConnectionData.motor_ACK[LEFT].__str__())
        self.LabelRpmAckR.set_text(ConnectionData.motor_ACK[RIGHT].__str__())
        self.LabelCamPosH.set_text(ConnectionData.camPosition[X_AXIS].__str__())
        self.LabelCamPosV.set_text(ConnectionData.camPosition[Y_AXIS].__str__())

        Voltage = "{:.2f}".format(ConnectionData.voltage).__str__()
        Current = "{:.2f}".format(ConnectionData.current).__str__()
        self.LabelCoreTemp.set_text("{:.2f}".format(ConnectionData.coreTemp).__str__())
        self.LabelBattV.set_text(Voltage)
        self.LabelPowerA.set_text(Current)
        self.LabelS1Dist.set_text(ConnectionData.distanceS1.__str__())

        self.LevelBar_Voltage.set_tooltip_text("%s V" % Voltage)
        self.LevelBar_Current.set_tooltip_text("%s A" % Current)

        return

    def UpdateControlData(self):
        self.DispAvgVal[0] = (self.DispAvgVal[0] * 4 + ConnectionData.voltage) / 5
        self.DispAvgVal[1] = (self.DispAvgVal[1] * 4 + ConnectionData.current) / 5
        self.LevelBar_Voltage.set_value(self.DispAvgVal[0])
        self.LevelBar_Current.set_value(self.DispAvgVal[1])
        self.LeverBar_PowerL.set_value(ConnectionData.motor_PWR[LEFT])
        self.LeverBar_PowerR.set_value(ConnectionData.motor_PWR[RIGHT])

        return

###############################################################################
################   MAIN LOOP END   ############################################
###############################################################################

    def on_Button_AdvancedShow_clicked(self, widget):
        self.Window_AdvancedDisp.show()
        return True

    def on_DrawingArea_Control_draw(self, widget, message):
        self.Connection_Thread.draw_arrow(message)

    def on_DrawingArea_Cam_draw(self, widget, message):
        self.Connection_Thread.draw_hud(message)

    def get_host_and_port(self):
        widget = self.ComboBox_Host
        try:
            Host = str(widget.get_model()[widget.get_active()][0])
            Port = int(float(widget.get_model()[widget.get_active()][1]))
        except IndexError:
            return None

        return Host, Port

    def on_ComboBox_Host_changed(self, widget):
        pass
        # try:
        #     self.Host = str(widget.get_model()[widget.get_active()][0])
        #     self.Port = int(float(widget.get_model()[widget.get_active()][1]))
        # except IndexError:
        #     return

    def on_SpinButton_Port_value_changed(self, widget):
        # self.Port = widget.get_value_as_int()
        pass

    def on_CheckButton_LocalTest_toggled(self, widget):
        ConnectionData.TestMode = not(widget.get_active())
        ConnectionData.Vcodec = bool(ConnectionData.Protocol + ConnectionData.TestMode)
        self.SSBar_update()

    def on_ComboBoxText_Proto_changed(self, widget):
        ConnectionData.Protocol = widget.get_active()
        self.SSBar_update()

    def on_ToggleButton_Connect_toggled(self, widget):
        self.on_key_press_handler = None
        if widget.get_active() is True:
            widget.set_label(Gtk.STOCK_DISCONNECT)

            self.gui_update_connect()
            self.gui_connect_loop()

            self.Host, self.Port = self.get_host_and_port()

            # retmsg = 'SSH Connection Error!'
            # if self.CheckButton_SshTunnel.get_active() is True:
            #     Host, Port = self.Connection_Thread.open_ssh_tunnel(self.Host, 22,
            #                                                         self.Entry_RsaKey.get_text(),
            #                                                         self.Entry_KeyPass.get_text(),
            #                                                         self.Entry_User.get_text(),
            #                                                         self.Entry_RemoteHost.get_text(),
            #                                                         self.ComboBoxText_Ssh_Compression.get_active())
            # else:
            # Host, Port = self.Host, self.Port

            success = bool(self.Host)
            # if success is True:
                # if ConnectionData.Protocol == 1:  # UDP Protocol
                #     success, retmsg = self.Connection_Thread.open_udp_to_tcp_link()
                #     if not(success):
                #         retmsg = 'Failed Ports:' + str(retmsg)

            if success is True:
                self.Spinner_Connected.start()
                success, retmsg = self.Connection_Thread.establish_connection(self.Host, self.Port,
                                                                              self.Receiver_Stream)
                # if success is True:
                #     self.Connection_Thread.update_server_list(self.ComboBox_Host, self.SpinButton_Port.get_value())

                if success is True:
                    Port_CAM0 = self.Port + 1
                    Port_MIC0 = self.Port + 2
                    Port_DSP0 = self.Port + 4
                    Port_SPK0 = self.Port + 5
                    self.Receiver_Stream.prepare_receiver(None, Port_CAM0, Port_MIC0)
                    self.Sender_Stream.prepare_sender(self.Host, Port_DSP0, Port_SPK0)
                else:
                    Console.print(retmsg)
                    self.gui_update_disconnect()
                    self.StatusBar.push(self.context_id, retmsg)
        else:
            self.Host = "0.0.0.0"
            self.Port = 0
            ConnectionData.connected = False
            widget.set_label(Gtk.STOCK_CONNECT)
            self.StatusBar.push(self.context_id, 'Disconnected.')
            self.gui_update_disconnect()

    def store_FX_request(self, FXmode, FXvalue):
        items = self.Connection_Thread.FxQueue.qsize()
        if items == 0:
            self.Connection_Thread.FxQueue.put((FXmode, FXvalue))
        else:
            item_found = False
            for i in range(items):
                qFXmode, qFXvalue = self.Connection_Thread.FxQueue.get()
                if qFXmode == FXmode:
                    self.Connection_Thread.FxQueue.put((qFXmode, FXvalue))
                    item_found = True
                    break
                else:
                    self.Connection_Thread.FxQueue.put((qFXmode, qFXvalue))

            if item_found is False:
                self.Connection_Thread.FxQueue.put((FXmode, FXvalue))

    def on_ComboBoxText_FxEffect_changed(self, widget):
        FXmode   = 8
        FXvalue  = widget.get_active()
        self.store_FX_request(FXmode, FXvalue)

        if FXvalue == 0:
            self.Menu_CamFx_Item0.set_active(True)
        elif FXvalue == 1:
            self.Menu_CamFx_Item1.set_active(True)
        elif FXvalue == 2:
            self.Menu_CamFx_Item2.set_active(True)
        elif FXvalue == 3:
            self.Menu_CamFx_Item3.set_active(True)
        elif FXvalue == 4:
            self.Menu_CamFx_Item4.set_active(True)
        elif FXvalue == 5:
            self.Menu_CamFx_Item5.set_active(True)
        elif FXvalue == 6:
            self.Menu_CamFx_Item6.set_active(True)
        elif FXvalue == 7:
            self.Menu_CamFx_Item7.set_active(True)
        elif FXvalue == 8:
            self.Menu_CamFx_Item8.set_active(True)
        elif FXvalue == 9:
            self.Menu_CamFx_Item9.set_active(True)
        elif FXvalue == 10:
            self.Menu_CamFx_Item10.set_active(True)
        elif FXvalue == 11:
            self.Menu_CamFx_Item11.set_active(True)
        elif FXvalue == 12:
            self.Menu_CamFx_Item12.set_active(True)
        elif FXvalue == 13:
            self.Menu_CamFx_Item13.set_active(True)
        elif FXvalue == 14:
            self.Menu_CamFx_Item14.set_active(True)
        elif FXvalue == 15:
            self.Menu_CamFx_Item15.set_active(True)

        retmsg = 'FX effect changed [%i]' % FXvalue
        self.StatusBar.push(self.context_id, retmsg)

    def on_ComboBoxResolution_changed(self, widget):
        self.resolution = widget.get_active() + 1
        if self.resolution == 1:
            self.DrawingArea_Cam.set_size_request(640, 480)
            self.Menu_CamRes_Item1.set_active(True)
        elif self.resolution == 2:
            self.DrawingArea_Cam.set_size_request(640, 480)
            self.Menu_CamRes_Item2.set_active(True)
        elif self.resolution == 3:
            self.DrawingArea_Cam.set_size_request(800, 600)
            self.Menu_CamRes_Item3.set_active(True)
        elif self.resolution == 4:
            self.DrawingArea_Cam.set_size_request(1024, 768)
            self.Menu_CamRes_Item4.set_active(True)
        elif self.resolution == 5:
            self.DrawingArea_Cam.set_size_request(1152, 864)
            self.Menu_CamRes_Item5.set_active(True)

        ConnectionData.resolution = self.resolution * self.camera_on

        retmsg = 'Resolution changed [%i]' % ConnectionData.resolution
        self.StatusBar.push(self.context_id, retmsg)

    def on_FxValue_selected(self, widget):
        self.store_FX_request(widget.get_name(), widget.get_active())

    def on_FX_value_changed(self, widget):
        FXmode = int(widget.get_name())
        if FXmode < 4:  # Avoid negative values to be sent for Brightness, Contrast & Saturation
            self.store_FX_request(FXmode, int(widget.get_value()) + 100)
        elif FXmode == 11:
            self.store_FX_request(FXmode, int(widget.get_value()) / 1000)
        else:
            self.store_FX_request(FXmode, int(widget.get_value()))

    def on_ComboBoxText_Vcodec_changed(self, widget):
        ConnectionData.Vcodec = widget.get_active()
        self.Console.print('Video Codec Changed:', ConnectionData.Vcodec)
        self.SSBar_update()

    def on_ComboBoxText_Acodec_changed(self, widget):
        ConnectionData.Acodec = widget.get_active()
        self.Console.print('Audio Codec Changed:', ConnectionData.Acodec)
        self.SSBar_update()

    def on_ComboBoxText_Framerate_changed(self, widget):
        ConnectionData.Framerate = widget.get_active()
        self.Console.print('Video Framerate:', VideoFramerate[ConnectionData.Framerate])
        self.SSBar_update()

    def on_ComboBoxText_Rotate_changed(self, widget):
        DEVICE_control.Cam0_Flip = widget.get_active()
        if self.Receiver_Stream.player_video:
            self.Receiver_Stream.player_video_flip.set_property("method", DEVICE_control.Cam0_Flip)  # => "rotate"

    def on_ComboBoxText_Abitrate_changed(self, widget):
        ConnectionData.Abitrate = widget.get_active()
        if self.CheckButton_Speakers.get_active() is True:  # restart stream
            self.CheckButton_Speakers.set_active(False)
            self.CheckButton_Speakers.set_active(True)
        self.Console.print('Audio Bitrate:', AudioBitrate[ConnectionData.Abitrate])
        self.SSBar_update()

    def on_ComboBoxText_Cam1_changed(self, widget):
        DEVICE_control.DEV_Cam0 = widget.get_active_text()

    def on_CheckButton_Speakers_toggled(self, widget):
        ConnectionData.speakers = widget.get_active()

        ret = False
        if ConnectionData.speakers is True:
            Console.print(" Speaker requested rate:", AudioBitrate[ConnectionData.Abitrate])
            ret = self.Sender_Stream.run_audio(ConnectionData.speakers)
        else:
            if self.Sender_Stream.sender_audio:
                ret = self.Sender_Stream.run_audio(ConnectionData.speakers)

        retmsg = 'Speakers: %s' % PrintOnOff[ret]
        self.Console.print(retmsg)
        self.StatusBar.push(self.context_id, retmsg)

    def on_CheckButton_Mic_toggled(self, widget):
        ConnectionData.mic = widget.get_active()

        ret = False
        if ConnectionData.mic is True:
            Console.print(" Mic requested rate:", AudioBitrate[ConnectionData.Abitrate])
            ret = self.Receiver_Stream.run_audio(ConnectionData.mic)
        else:
            if self.Receiver_Stream.player_audio:
                ret = self.Receiver_Stream.run_audio(ConnectionData.mic)
        retmsg = 'Microphone: ' + PrintOnOff[ret]
        self.Console.print(retmsg)
        self.StatusBar.push(self.context_id, retmsg)

    def on_CheckButton_Display_toggled(self, widget):
        ConnectionData.display = widget.get_active()

        if ConnectionData.display is True:
            self.DrawingArea_Disp.show()
            self.Sender_Stream.run_video(ConnectionData.display)
        else:
            self.Sender_Stream.run_video(ConnectionData.display)
            self.DrawingArea_Disp.hide()

        self.Console.print('Display:', ConnectionData.display)
        retmsg = 'Display: ' + PrintOnOff[ConnectionData.display]
        self.StatusBar.push(self.context_id, retmsg)

    def on_CheckButton_Cam_toggled(self, widget):
        self.camera_on = widget.get_active()
        ConnectionData.resolution = self.resolution * self.camera_on
        retmsg = 'Camera: %s' % PrintOnOff[self.camera_on]
        self.Console.print(retmsg)
        self.StatusBar.push(self.context_id, retmsg)

    def on_CheckButton_Lights_toggled(self, widget):
        ConnectionData.light = widget.get_active()
        self.Console.print('Lights:', ConnectionData.light)
        retmsg = 'Lights: ' + PrintOnOff[ConnectionData.light]
        self.StatusBar.push(self.context_id, retmsg)

    def on_CheckButton_Laser_toggled(self, widget):
        ConnectionData.laser = widget.get_active()
        self.Console.print('Laser:', ConnectionData.laser)
        retmsg = 'Laser: ' + PrintOnOff[ConnectionData.laser]
        self.StatusBar.push(self.context_id, retmsg)

    def on_ToggleButton_Log_toggled(self, widget):
        if widget.get_active() is True:
            self.Window_Log.show()
        else:
            self.Window_Log.hide()
        return True

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

    def on_Menu_CmdExe_Item_activate(self, widget):
        FXmode = 30
        FXvalue = int(widget.get_name())
        if FXvalue == 250:
            self.Label_dialog_yn.set_text("Do you really want\n\tto reboot RPI?")
            resp = self.Dialog_YN.run()
            if resp < 1:
                return
        elif FXvalue == 251:
            self.Label_dialog_yn.set_text("Restart server?")
            resp = self.Dialog_YN.run()
            if resp < 1:
                return
        elif FXvalue == 0:
            self.Label_dialog_yn.set_text("Do you really want\n\tto shutdown the server?")
            resp = self.Dialog_YN.run()
            if resp < 1:
                return
        elif FXvalue == 1:
            self.Config_Storage.reload_current_setup(self.builder)
            self.SyncOn = True
            return
        else:
            return

        self.store_FX_request(FXmode, FXvalue)

    def on_Button_AdvOk_clicked(self, widget):
        self.ComboBox_Host.set_model(self.TreeView_Hosts.get_model())
        self.Entry_Hosts.set_text('')

        self.Window_Advanced.hide()
        return True

    def on_Button_AdvCamOk_clicked(self, widget):
        self.Window_AdvancedCam.hide()
        return True

    def on_Button_Preferences_clicked(self, widget):
        self.Window_Advanced.show()
        return True

    def on_Button_AdvancedCam_clicked(self, widget):
        self.Window_AdvancedCam.show()
        return True

    def on_Button_SelectFile_clicked(self, widget):
        if widget.get_name() == "SelectSkinFile":
            # self.FileChooserDialog_open.set_action(Gtk.FILE_CHOOSER_ACTION_OPEN)
            self.FileChooserDialog_open.set_action(0)  # OPEN_FILE
            # self.FileChooserDialog_open.remove_filter(self.FileFilter_ini)
            self.FileChooserDialog_open.add_filter(self.FileFilter_glade)
            if self.FileChooserDialog_open.run() == 1:
                self.Entry_SkinFile.set_text(self.FileChooserDialog_open.get_filename())
        else:
            # self.FileChooserDialog_open.set_action(Gtk.FILE_CHOOSER_ACTION_SELECT_FOLDER)
            self.FileChooserDialog_open.set_action(2)  # SELECT_FOLDER
            self.FileChooserDialog_open.remove_filter(self.FileFilter_glade)
            # self.FileChooserDialog_open.remove_filter(self.FileFilter_ini)
            if self.FileChooserDialog_open.run() == 1:
                self.Entry_LogPath.set_text(self.FileChooserDialog_open.get_filename())

        return True

    def on_FileChooserDialog_open_response(self, widget, response):
        self.FileChooserDialog_open.hide()
        return response

    def on_Button_FileChooser_clicked(self, widget):  # Gtk.ResponseType.APPLY
        self.FileChooserDialog_open.emit("response", int(widget.get_name()))
        return True

    def return_widget_name(self, widget):
        self.Dialog_YN.emit("response", int(widget.get_name()))
        self.Dialog_YN.hide()
        return True

    def on_Window_delete_event(self, widget, *message):
        widget.hide()
        return True

    def on_TreeSelection_Hosts_changed(self, selection):
        # get the model and the iterator that points at the data in the model
        model, iter = selection.get_selected()
        # set the label to a new value depending on the selection
        # self.label.set_text("\n %s %s" %
        #                     (model[iter][0],  model[iter][1]))
        return True

    def on_TreeView_Hosts_row_activated(self, widget, iter, column):
        model = tuple(widget.get_model()[iter])
        self.Entry_Hosts.set_text(model[0] + ":" + model[1].__str__())
        self.Entry_Hosts.show()

        return True

    def on_TreeView_Hosts_cursor_changed(self, widget):
        self.Entry_Hosts.set_text('')
        self.Entry_Hosts.hide()

        return True

    def on_Button_Hosts_add_clicked(self, widget):
        obj = self.TreeView_Hosts.get_model()
        obj.append(("NewEntry", int(self.SpinButton_Port.get_value())))
        self.TreeView_Hosts.set_model(obj)

        return True

    def on_Button_Hosts_delete_clicked(self, widget):
        selection = self.TreeView_Hosts.get_selection()
        model, paths = selection.get_selected_rows()
        # Get the TreeIter instance for each path
        for path in paths:
            iter = model.get_iter(path)
            # Remove the ListStore row referenced by iter
            model.remove(iter)

        return True

    def on_Entry_Hosts_activate(self, widget):
        HostPort = widget.get_text().split(":")
        if len(HostPort) == 2:
            selection = self.TreeView_Hosts.get_selection()
            model, iter = selection.get_selected()
            if iter is None:
                iter = ""

            model.set(iter, 0, HostPort[0], 1, int(HostPort[1]))

            widget.set_text('')
            widget.hide()
            return True
        else:
            return False

    def on_Window_Console_key_press_event(self, widget, event):
        self.keybuffer_set(event, True)

        return True

    def on_Window_Console_key_release_event(self, widget, event):
        key_name = self.keybuffer_set(event, False)

        return key_name

    # @staticmethod
    def keybuffer_set(self, event, value):
        key_name = Gdk.keyval_name(event.keyval)
        if key_name == 'Left' or key_name.replace("A", "a", 1) == "a":
            KEY_control.Left = value

        elif key_name == 'Right' or key_name.replace("D", "d", 1) == "d":
            KEY_control.Right = value

        elif key_name == 'Up' or key_name.replace("W", "w", 1) == "w":
            KEY_control.Up = value

        elif key_name == 'Down' or key_name.replace("S", "s", 1) == "s":
            KEY_control.Down = value

        elif key_name == 'space':
            ConnectionData.speed = 0
            ConnectionData.direction = 0
            KEY_control.Space = value

        elif key_name.replace("H", "h", 1) == "h":
            if value is False:
                KEY_control.hud = not KEY_control.hud

        elif key_name.replace("C", "c", 1) == "c":
            if value is False:
                self.camera_on = not self.camera_on
                if self.CheckButton_Cam.get_active() is True:
                    self.CheckButton_Cam.set_active(False)
                else:
                    self.CheckButton_Cam.set_active(True)

        elif key_name.replace("M", "m", 1) == "m":
            if value is False:
                if self.CheckButton_Mic.get_active() is True:
                    self.CheckButton_Mic.set_active(False)
                else:
                    self.CheckButton_Mic.set_active(True)

        elif key_name.replace("O", "o", 1) == "o":
            if value is False:
                if self.CheckButton_Speakers.get_active() is True:
                    self.CheckButton_Speakers.set_active(False)
                else:
                    self.CheckButton_Speakers.set_active(True)

        elif key_name.replace("L", "l", 1) == "l":
            if value is False:
                if self.CheckButton_Laser.get_active() is True:
                    self.CheckButton_Laser.set_active(False)
                else:
                    self.CheckButton_Laser.set_active(True)
                # self.CheckButton_Laser.emit("toggled")

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
            self.Menu_MainHub.popup(None, None, None, None, Gdk.BUTTON_SECONDARY, mouse_event.time)
            self.last_MouseButtonR = KEY_control.MouseBtn[RIGHT]

    def on_motion_notify(self, widget, mouse_event):
        mouseX = int(mouse_event.x)
        mouseY = int(mouse_event.y)
        if KEY_control.MouseBtn[LEFT] is True:
            tmp = (KEY_control.MouseXY[X_AXIS] - mouseX) / 2
            if abs(tmp) >= 1:
                if ConnectionData.camPosition[X_AXIS] + tmp > MOUSE_MAX[X_AXIS]:
                    ConnectionData.camPosition[X_AXIS] = MOUSE_MAX[X_AXIS]
                elif ConnectionData.camPosition[X_AXIS] + tmp < MOUSE_MIN[X_AXIS]:
                    ConnectionData.camPosition[X_AXIS] = MOUSE_MIN[X_AXIS]
                else:
                    ConnectionData.camPosition[X_AXIS] += int(tmp)

            tmp = (mouseY - KEY_control.MouseXY[Y_AXIS]) / 2
            if abs(tmp) >= 1:
                if ConnectionData.camPosition[Y_AXIS] + tmp > MOUSE_MAX[Y_AXIS]:
                    ConnectionData.camPosition[Y_AXIS] = MOUSE_MAX[Y_AXIS]
                elif ConnectionData.camPosition[Y_AXIS] + tmp < MOUSE_MIN[Y_AXIS]:
                    ConnectionData.camPosition[Y_AXIS] = MOUSE_MIN[Y_AXIS]
                else:
                    ConnectionData.camPosition[Y_AXIS] += int(tmp)

            KEY_control.MouseXY = [mouseX, mouseY]

        # if KEY_control.MouseBtn[RIGHT] is True:
        #     self.Console.print("KEY_control.MouseXY[right]", KEY_control.MouseXY)

    def gtk_main_quit(self, widget, message):
        self.Connection_Thread.close_connection()
        self.Config_Storage.save_setup(self.builder, self.RunSeqNo)

        Gtk.main_quit()
        return True

###############################################################################


class ConfigStorage:
    def reload_current_setup(self, builder):
        for obj in builder.get_objects():
            if issubclass(type(obj), Gtk.Buildable):
                if type(obj) != Gtk.TreeView:
                    self.set_object_value(obj)

    def load_setup(self, builder):
        # Emulate button press for signal processing
        KEY_control_sav = KEY_control.MouseBtn[LEFT]
        KEY_control.MouseBtn[LEFT] = True

        ItemCount = 0
        with open(Files.ini_file, 'rb') as iniFile:
            SetupVar = pickle.load(iniFile)
            AddInfoVar = pickle.load(iniFile)
            for text, name, value in SetupVar:
                for obj in builder.get_objects():
                    if issubclass(type(obj), Gtk.Buildable):
                        if name != Gtk.Buildable.get_name(obj):
                            continue
                        else:
                            if text is None:
                                ItemCount += int(self.set_object_value(obj, value))
                            else:
                                ItemCount += 1
                                # print('LOAD NAME/TEXT %s' % name)
                                # print('LOAD TEXT %s' % text)
                                if name == "ComboBoxText_Cam1":
                                    DEVICE_control.DEV_Cam0 = text
                                elif name == "ComboBoxText_AudioIn":
                                    DEVICE_control.DEV_AudioIn = text
                                elif name == "ComboBoxText_AudioOut":
                                    DEVICE_control.DEV_AudioOut = text
                                else:
                                    text = None

        KEY_control.MouseBtn[LEFT] = KEY_control_sav
        LoadSeqNumber = int(AddInfoVar)

        print('Configuration loaded.', LoadSeqNumber)
        return LoadSeqNumber, ItemCount - 10

    def save_setup(self, builder, RunSeqNo):
        SkinFile = "gui_artifacts/Client_GUI_v3.glade"  # default skin
        SetupVar = list()
        AddInfoVar = RunSeqNo + 1
        for obj in builder.get_objects():
            if issubclass(type(obj), Gtk.Buildable):
                name = Gtk.Buildable.get_name(obj)
            else:
                continue

            value = self.get_object_value(obj)
            if value is not None:
                active_text = None
                if name == "ComboBoxText_Cam1":
                    active_text = DEVICE_control.DEV_Cam0
                elif name == "ComboBoxText_AudioIn":
                    active_text = DEVICE_control.DEV_AudioIn
                elif name == "ComboBoxText_AudioOut":
                    active_text = DEVICE_control.DEV_AudioOut
                elif name == "Entry_SkinFile":
                    SkinFile = value
                    continue
                elif name == "CheckButton_Speakers":
                    value = False
                elif name == "CheckButton_Show":
                    value = False

                # if active_text:
                #     print('SAVE NAME/TEXT %s' % name + " >> " + active_text)
                SetupVar.append((active_text, name, value))

        with open(Files.ini_file, 'wb') as iniFile:
            pickle.dump(SetupVar, iniFile)
            pickle.dump(AddInfoVar, iniFile)
            pickle.dump("\n##### Skin File #####\n%s\n#####################" % SkinFile, iniFile)

        print('Configuration saved.')

    @staticmethod
    def set_object_value(obj, *value):
        if type(obj) == Gtk.CheckButton:
            if value:
                obj.set_active(value[0])
            obj.emit('toggled')
            return False

        if type(obj) == Gtk.CheckMenuItem:
            if value:
                obj.set_active(value[0])
            return False

        if type(obj) == Gtk.ComboBoxText:
            if value:
                obj.set_active(value[0])
            obj.emit('changed')
            return True

        if type(obj) == Gtk.SpinButton:
            if value:
                obj.set_value(value[0])
            obj.emit('value-changed')
            return True

        if type(obj) == Gtk.Scale:
            if value:
                obj.set_value_pos(value[0])
            obj.emit('value-changed')
            return True

        if type(obj) == Gtk.Entry:
            if value:
                obj.set_text(value[0])
            return False

        if type(obj) == Gtk.TreeView:
            for i, column in enumerate(["Host", "Port"]):
                # cellrenderer to render the text
                cell = Gtk.CellRendererText()
                # the text in the first column should be in boldface
                # if i == 0:
                    # cell.props.weight_set = True
                    # cell.props.weight = 12000
                    # pass
                # the column is created
                col = Gtk.TreeViewColumn(column, cell, text=i)
                obj.append_column(col)

            obj_LS = Gtk.ListStore(str, int)
            if value:
                for Host, Port in value[0]:
                    obj_LS.append((Host, Port))

            obj.set_model(obj_LS)
            return False

        return False

    @staticmethod
    def get_object_value(obj):
        if type(obj) == Gtk.CheckButton:
            return obj.get_active()

        if type(obj) == Gtk.CheckMenuItem:
            return obj.get_active()

        if type(obj) == Gtk.ComboBoxText:
            return obj.get_active()

        if type(obj) == Gtk.SpinButton:
            return obj.get_value_as_int()

        if type(obj) == Gtk.Entry:
            return obj.get_text()

        if type(obj) == Gtk.Scale:
            return obj.get_value_pos()

        if type(obj) == Gtk.TreeView:
            return_list = list()
            return_list_raw = obj.get_model()
            for iter_x in range(0, return_list_raw.iter_n_children()):
                return_list.append(tuple(return_list_raw[iter_x]))

            return return_list

        return None

if __name__ == '__main__':
    MainWindow()
    Gtk.main()
