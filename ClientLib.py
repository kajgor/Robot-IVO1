#!/usr/bin/env python
# -*- coding: CP1252 -*-

import datetime
import socket
import cairo
import math
import time

import gi
gi.require_version('Gst', '1.0')
gi.require_version('Gdk', '3.0')
gi.require_version('GstVideo', '1.0')
from gi.repository import Gst, GstVideo, Gdk
from os import system
from _thread import *
from init_variables import *


class MainLoop:
    ###############################################################################
    ################   MAIN LOOP START   ##########################################
    ###############################################################################
    def __init__(self, GUI):
        self.GUI = GUI
        self.counter = 0

    def on_timer(self):
        if COMM_vars.connected:
            self.counter += .03

        if COMM_vars.comm_link_idle > COMM_IDLE:
            self.GUI.spinner_connection.stop()
            COMM_vars.comm_link_idle = COMM_IDLE  # Do not need to increase counter anymore
        else:
            self.GUI.spinner_connection.start()

        COMM_vars.comm_link_idle += 1
        # else:
        #     self.GUI.spinner_connection.stop()
        # print("COMM_vars.comm_link_idle", COMM_vars.comm_link_idle)

        # Any update tasks would go here (moving sprites, advancing animation frames etc.)
        self.UpdateControlData()
        self.UpdateMonitorData()

        self.GUI.statusbar2.push(self.GUI.context_id2, datetime.timedelta(seconds=int(self.counter)).__str__())
        self.GUI.drawingarea_control.queue_draw()

        if COMM_vars.connected is True:
            if CommunicationFFb is False:
                RacUio().get_speed_and_direction()  # Keyboard input
                RacUio().calculate_MotorPower()
                RacUio().mouseInput()               # Mouse input
        else:
            self.GUI.button_connect.set_active(False)
            self.GUI.on_ToggleButton_Connect_toggled(self.GUI.button_connect)

        return True

    def UpdateMonitorData(self):
        self.GUI.LabelRpmL.set_text(COMM_vars.Motor_RPM[LEFT].__str__())
        self.GUI.LabelRpmR.set_text(COMM_vars.Motor_RPM[RIGHT].__str__())
        self.GUI.LabelPowerL.set_text(COMM_vars.Motor_PWR[LEFT].__str__())
        self.GUI.LabelPowerR.set_text(COMM_vars.Motor_PWR[RIGHT].__str__())
        self.GUI.LabelRpmReqL.set_text(COMM_vars.Motor_Power[LEFT].__str__())
        self.GUI.LabelRpmReqR.set_text(COMM_vars.Motor_Power[RIGHT].__str__())
        self.GUI.LabelRpmAckL.set_text(COMM_vars.Motor_ACK[LEFT].__str__())
        self.GUI.LabelRpmAckR.set_text(COMM_vars.Motor_ACK[RIGHT].__str__())
        self.GUI.LabelCamPosH.set_text(COMM_vars.CamPos[X_AXIS].__str__())
        self.GUI.LabelCamPosV.set_text(COMM_vars.CamPos[Y_AXIS].__str__())

        self.GUI.LabelCoreTemp.set_text("{:.2f}".format(COMM_vars.CoreTemp).__str__())
        self.GUI.LabelBattV.set_text("{:.2f}".format(COMM_vars.Voltage).__str__())
        self.GUI.LabelPowerA.set_text("{:.2f}".format(COMM_vars.Current).__str__())
        self.GUI.LabelS1Dist.set_text(COMM_vars.DistanceS1.__str__())

        return

    def UpdateControlData(self):
        self.GUI.LevelBar_Voltage.set_value(int(COMM_vars.Voltage * 10))
        self.GUI.LevelBar_Current.set_value(int(COMM_vars.Current * 10))
        self.GUI.LeverBar_PowerL.set_value(65)
        self.GUI.LeverBar_PowerR.set_value(65)
        # print("int(COMM_vars.Current * 10) - 70", int(COMM_vars.Current * 10))

        return
###############################################################################
################   MAIN LOOP END   ############################################
###############################################################################


# noinspection PyPep8Naming
class RacConnection:
    Gdk.threads_init()
    # print("checksum", calc_checksum("ABCD174")
    srv = None
    LocalTest = False
    Host = None
    Port_Comm = None
    Last_Active = 0

    def __init__(self):
        # --- Gstreamer setup begin ---
        Gst.init(None)
        self.player = Gst.Pipeline.new("player")
        self.source = Gst.ElementFactory.make("tcpclientsrc", "source")
        decoder = Gst.ElementFactory.make("gdpdepay", "decoder")
        vconvert = Gst.ElementFactory.make("videoconvert")
        self.sink = Gst.ElementFactory.make("ximagesink", None)
        self.sink.set_property("sync", False)
        if not self.sink or not self.source:
            print("GL elements not available.")
            exit()
        else:
            self.player.add(self.source, decoder, vconvert, self.sink)
            self.source.link(decoder)
            decoder.link(vconvert)
            vconvert.link(self.sink)
        # --- Gstreamer setup end ---

    def establish_connection(self):
        if Debug > 2: print("Estabilishing Connection:", self.Host, self.Port_Comm)

        # Gstreamer setup start
        self.source.set_property("host", self.Host)
        self.source.set_property("port", self.Port_Comm.__int__() + 1)
        # Gstreamer setup end

        start_new_thread(self.connection_thread, (self.Host, self.Port_Comm))
        time.sleep(1)

        return COMM_vars.connected

    def close_connection(self):
        if Debug > 1:
            print("Closing connection...")
        self.player.set_state(Gst.State.NULL)

        try:
            self.srv.shutdown(socket.SHUT_RDWR)
        except OSError:
            if Debug > 1:
                print("...not connected!")
        except AttributeError:
            if Debug > 1:
                print("...not connected!")

        try:
            RacConnection.srv.close()
        except AttributeError:
            RacConnection.srv = None

        COMM_vars.connected = False
        if Debug > 1: print("Connection closed.")

    @staticmethod
    def check_connection(HostIp):
        try:
            # status = self.srv.getsockname()
            status = RacConnection.srv.getpeername()
            # print("Status", status)
        except OSError:
            status = (False, False)

        if not HostIp:
            if status[0] != '0.0.0.0':
                HostIp = status[0]

        if status[0] == HostIp:
            if Debug > 2: print("Connection status: " + status.__str__())
            return True
        else:
            if Debug > 1: print("Not connected.")
            return False

    ###############################################################################
    ################   COMMUNICATION LOOP START   #################################
    ###############################################################################

    def connection_thread(self, Host, Port_Comm):
        if Debug > 2: print("Connecting...")
        RacConnection.srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_address = (Host, Port_Comm)
        try:
            self.srv.connect(server_address)
            COMM_vars.connected = True
            if Debug > 2: print("Connected! self.srv.getpeername()", self.srv.getpeername())
        except ConnectionResetError:
            COMM_vars.connected = False
            if Debug > 0: print("Server not responding <", COMM_vars.connected, ">")
        except ConnectionRefusedError:
            COMM_vars.connected = False
            if Debug > 0: print("Server refused connection <", COMM_vars.connected, ">")
        except socket.gaierror:
            COMM_vars.connected = False
            if Debug > 0: print("Invalid protocol <", COMM_vars.connected, ">")

        if COMM_vars.connected is True:
            time.sleep(1.48)

        rac__uio = RacUio()
        while COMM_vars.connected is True:
            if CommunicationFFb is True:
                rac__uio.get_speed_and_direction()  # Keyboard input
                rac__uio.calculate_MotorPower()     # Set control variables
                rac__uio.mouseInput()               # Set mouse Variables

            if self.check_connection(None) is True:
                self.send_and_receive()

        self.close_connection()
        print("Closing Thread: COMM_vars.connected is", COMM_vars.connected)
        exit_thread()

    def send_and_receive(self):
        if COMM_vars.speed != "HALT":
            request  = self.encode_message()
            checksum = self.transmit_message(request)
            if checksum is None:
                COMM_vars.ConnErr += 1
                if COMM_vars.ConnErr > 15:
                    COMM_vars.ConnErr = 0
                    COMM_vars.connected = False
                return
            else:
                COMM_vars.ConnErr = 0

            resp = self.receive_message()
            if resp is not None:
                if Debug > 1: print("CheckSum Sent/Received:", checksum, ord(resp[0]))
                if checksum == ord(resp[0]):
                    RacConnection().decode_transmission(resp)
                    COMM_vars.Motor_ACK = COMM_vars.Motor_Power
        else:
            self.transmit_message(HALT_0)
            COMM_vars.connected = False

    ###############################################################################
    ################   CONN LOOP END   ############################################
    ###############################################################################

    def connect_camstream(self, connect):
        if connect is True:
            retmsg = self.player.set_state(Gst.State.PLAYING)
        else:
            retmsg = self.player.set_state(Gst.State.NULL)

        if retmsg == Gst.StateChangeReturn.FAILURE:
            return False
        else:
            return True

    def conect_micstream(self):
        retmsg = self.player.set_state(Gst.State.PLAYING)
        if retmsg == Gst.StateChangeReturn.FAILURE:
            retmsg = "VIDEO CONNECTION ERROR: Unable to set the pipeline to the playing state."
            success = False
        else:
            retmsg = "VIDEO CONNECTION ESTABILISHED: OK"
            success = True

        if Debug > 1: print(retmsg)
        return retmsg, success

    def transmit_message(self, out_str):
        sendstr = chr(COMM_BITSHIFT - 1).encode(Encoding) + out_str + chr(10).encode(Encoding)
        if Debug > 2:
            print("CLISENT[len]: " + len(sendstr).__str__())

        if self.srv is None:
            print("self.srv is NONE!")
            return None
        try:
            self.srv.sendall(sendstr)
        except BrokenPipeError:
            print("transmit_message: BrokenPipeError")
            return None
        except AttributeError:
            print("transmit_message: AttributeError")
            return None
        except OSError:
            print("transmit_message: OSError (server lost)")
            return None

        return calc_checksum(sendstr)

    def receive_message(self):
        try:
            data = self.srv.recv(RECMSGLEN).decode(Encoding)
        except ConnectionResetError:
            return None
        except OSError:
            return None

        if Debug > 2: print("CLIRCVD[len]: " + len(data).__str__())

        try:
            data_end = data[14]
        except IndexError:
            data_end = False

        if data_end == chr(10):
            COMM_vars.comm_link_idle = 0
            return data
        else:
            try:
                self.srv.recv(1024)  # flush buffer
            except OSError:
                print("transmit_message [flush]: OSError (server lost)")
                return None

            if Debug > 1: print(">>>FlushBuffer>>>")
            return None

    def update_server_list(self, combobox_host, port):
        list_iter = combobox_host.get_active_iter()
        if list_iter is not None:
            model = combobox_host.get_model()
            Host, Port = model[list_iter][:2]
            try:
                Port = Port[:Port.index('.')]
            except:
                Port = Port

            print("Selected: Port=%s, Host=%s" % (int(Port), Host))
        else:
            entry = combobox_host.get_child()
            combobox_host.prepend(port.__str__(), entry.get_text())
            combobox_host.set_active(0)

            print("New entry: %s" % entry.get_text())
            print("New port: %s" % port.__str__())

    def HostList_get(self, model, HostToFind):
        HostList = []
        for iter_x in range(0, model.iter_n_children()):
            if HostToFind is None:
                HostList.append(model[iter_x][0] + ":" + model[iter_x][1])
            else:
                if model[iter_x][0] == HostToFind:
                    return iter_x

        if HostToFind is None:
            print("HostList_str: [%d]" % model.iter_n_children(), HostList)
            return HostList
        else:
            return False

    def config_snapshot(self, Host):
        self.Host = Host
        # ToDo:
        self.Port_Comm = "5000"
        self.Port_Video = "5001"
        self.Port_Audio = "5002"
        self.Gstreamer_Path = "/usr/bin"

    def load_HostList(self, combobox_host, HostList_str):
        x = 0
        for HostName in HostList_str:
            Host = HostName.split(":")[0]
            Port = HostName.split(":")[1]
            combobox_host.insert(x, Port, Host)
            x += 1

    @staticmethod
    def decode_transmission(resp):
        # checksum  - transmission checksum
        # Motor_PWR - power delivered to motors
        # Motor_RPM - Motor rotations

        # checksum
        # CheckSum = ord(resp[0])

        COMM_vars.Motor_PWR[RIGHT] = (ord(resp[1]) - COMM_BITSHIFT) + (ord(resp[2]) - COMM_BITSHIFT)
        COMM_vars.Motor_PWR[LEFT] = (10 * ((ord(resp[1]) - COMM_BITSHIFT) % 10)) + (ord(resp[3]) - COMM_BITSHIFT)

        COMM_vars.Motor_RPM[RIGHT] = (ord(resp[4]) - COMM_BITSHIFT) + (ord(resp[5]) - COMM_BITSHIFT)
        COMM_vars.Motor_RPM[LEFT] = (10 * ((ord(resp[4]) - COMM_BITSHIFT) % 10)) + (ord(resp[6]) - COMM_BITSHIFT)

        CntrlMask1 = ord(resp[7])
        CntrlMask2 = ord(resp[8])

        COMM_vars.CoreTemp = float(ord(resp[9]) - 50) * 0.5
        COMM_vars.Current  = float((ord(resp[10]) - COMM_BITSHIFT) * 10 + (ord(resp[11]) - COMM_BITSHIFT)) * 0.01
        COMM_vars.Voltage  = float((ord(resp[12]) - COMM_BITSHIFT) * 10 + (ord(resp[13]) - COMM_BITSHIFT)) * 0.01
        # print("Motor_ACK/PWR/RPM", COMM_vars.CheckSum, COMM_vars.Motor_PWR, COMM_vars.Motor_RPM)

    @staticmethod
    def encode_message():
        # print("MP l/r:", Motor_Power[RIGHT], Motor_Power[LEFT])
        # print("COMM_vars.Motor_Power", COMM_vars.Motor_Power)
        CntrlMask1 = 0
        for idx, x in enumerate([COMM_vars.light, COMM_vars.speakers, COMM_vars.mic,
                                 COMM_vars.display, COMM_vars.laser, 0, 0, 0]):
            CntrlMask1 |= (x << idx)

        requestMsg = chr(COMM_vars.Motor_Power[RIGHT] + 51 + COMM_BITSHIFT)
        requestMsg += chr(COMM_vars.Motor_Power[LEFT] + 51 + COMM_BITSHIFT)
        requestMsg += chr(COMM_vars.CamPos[X_AXIS])
        requestMsg += chr(COMM_vars.CamPos[Y_AXIS])
        requestMsg += chr(CntrlMask1)
        CntrlMask2 = COMM_vars.resolution * COMM_vars.camera
        requestMsg += chr(CntrlMask2 + COMM_BITSHIFT)
        if Debug == 2:
            print("requestMsg", requestMsg)

        return requestMsg.encode(Encoding)


class RacDisplay:
    background_control = cairo.ImageSurface.create_from_png("images/HUD_small.png")

    def draw_arrow(self, message):
        message.set_source_surface(self.background_control, 15, 0)
        message.paint()

        message.set_line_width(1)
        message.translate(105, 81)

        if COMM_vars.speed >= 0:
            message.rotate(COMM_vars.direction / (math.pi * 5))
        else:
            message.rotate((COMM_vars.direction + MAX_SPEED) / (math.pi * 5))

        # Direction arrow
        message.set_source_rgb(0.25, 0.25, 0.25)
        for i in range(4):
            message.line_to(arrow.points[i][0], arrow.points[i][1])
        message.fill()
        message.set_source_rgb(0, 0.75, 0.75)
        for i in range(5):
            message.line_to(arrow.points[i][0], arrow.points[i][1])
        message.stroke()

        # Speed arrow (REQ)
        message.set_source_rgb(abs(COMM_vars.speed/MAX_SPEED), 1 - abs(COMM_vars.speed/MAX_SPEED), 0)
        message.line_to(arrow.points[0][0], arrow.points[0][1] + 60 - abs((COMM_vars.speed / MAX_SPEED) * 50))
        for i in range(1, 4):
                message.line_to(arrow.points[i][0], arrow.points[i][1])
        message.fill()

        # Speed arrow (ACK)
        message.set_source_rgb(0, 0.75, 0.75)
        speed_ACK = abs(COMM_vars.Motor_ACK[0] + COMM_vars.Motor_ACK[1]) * 0.5
        message.line_to(arrow.points[1][0], arrow.points[1][1])
        message.line_to(arrow.points[0][0], arrow.points[0][1] + 60 - speed_ACK)
        message.line_to(arrow.points[3][0], arrow.points[3][1])
        message.stroke()

    def on_message(self, message):
        msgtype = message.type
        if msgtype == Gst.MessageType.EOS:
            RacConnection().player.set_state(Gst.State.NULL)
            if Debug > 1:
                # self.statusbar.push(self.context_id, "VIDEO CONNECTION EOS: SIGNAL LOST")
                print ("EOS: SIGNAL LOST")
            return "VIDEO CONNECTION EOS: SIGNAL LOST"
        elif msgtype == Gst.MessageType.ERROR:
            RacConnection().player.set_state(Gst.State.NULL)
            err, debug = message.parse_error()
            debug_s = debug.split("\n")
            if Debug > 0:
                # self.statusbar.push(self.context_id, debug_s[debug_s.__len__() - 1])
                print ("ERROR:", debug_s)
            return debug_s[debug_s.__len__() - 1]
        else:
            return None

    def on_sync_message(self, message, SXID):
        if message.get_structure().get_name() == 'prepare-window-handle':
            imagesink = message.src
            imagesink.set_property("force-aspect-ratio", True)
            imagesink.set_window_handle(SXID.get_xid())


class RacUio:
    def on_key_press(self, event):
        RacUio().keybuffer_set(event, True)
        return True

    def on_key_release(self, event):
        key_name = RacUio().keybuffer_set(event, False)
        return key_name

    def keybuffer_set(self, event, value):
        key_name = Gdk.keyval_name(event.keyval)
        # print("key", key_name, value)
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
            print("SHIIIIIIIIIIIIIIIFT!!!")

        return key_name

    def on_mouse_press(self, widget, mouse_event):
        self.mousebuffer_set(mouse_event, True)

    def on_mouse_release(self, widget, mouse_event):
        self.mousebuffer_set(mouse_event, False)

    def mousebuffer_set(self, mouse_event, value):
        if mouse_event.button == Gdk.BUTTON_PRIMARY:
            KEY_control.MouseBtn[LEFT] = value
            if value is True:
                KEY_control.MouseXY = [int(mouse_event.x) / 2,
                                       int(mouse_event.y) / 2]

        if mouse_event.button == Gdk.BUTTON_SECONDARY:
            KEY_control.MouseBtn[RIGHT] = value
            KEY_control.MouseXY = [0, 0]

    def on_motion_notify(self, widget, mouse_event):
        mouseX = int(mouse_event.x) / 2
        mouseY = int(mouse_event.y) / 2
        if KEY_control.MouseBtn[LEFT] is True:
            tmp = mouseX - KEY_control.MouseXY[X_AXIS]
            if abs(tmp) >= 1:
                COMM_vars.CamPos[X_AXIS] += int(tmp)

            tmp = mouseY - KEY_control.MouseXY[Y_AXIS]
            if abs(tmp) >= 1:
                COMM_vars.CamPos[Y_AXIS] += int(tmp)

            KEY_control.MouseXY = [mouseX, mouseY]

        if KEY_control.MouseBtn[RIGHT] is True:
            print("KEY_control.MouseXY[right]", KEY_control.MouseXY)

    @staticmethod
    def get_speed_and_direction():
        # print("COMM_vars:", KEY_control.Down, KEY_control.Up, KEY_control.Left, KEY_control.Right, COMM_vars.speed, COMM_vars.direction)
        if KEY_control.Down is True:
            if COMM_vars.speed > -MAX_SPEED:
                COMM_vars.speed -= ACCELERATION

        if KEY_control.Up is True:
            if COMM_vars.speed < MAX_SPEED:
                COMM_vars.speed += ACCELERATION

        if KEY_control.Left is True:
            if COMM_vars.direction > -MAX_SPEED:
                COMM_vars.direction -= ACCELERATION
            else:
                COMM_vars.direction = MAX_SPEED - ACCELERATION

        if KEY_control.Right is True:
            if COMM_vars.direction < MAX_SPEED:
                COMM_vars.direction += ACCELERATION
            else:
                COMM_vars.direction = -MAX_SPEED + ACCELERATION

        return COMM_vars.speed, COMM_vars.direction

    @staticmethod
    def calculate_MotorPower():
        if COMM_vars.direction < MAX_SPEED/2 and COMM_vars.direction > -MAX_SPEED/2:
            direction = COMM_vars.direction
        else:
            offset = MAX_SPEED * (COMM_vars.direction / abs(COMM_vars.direction))
            direction = (-COMM_vars.direction + offset)

        COMM_vars.Motor_Power = [int(COMM_vars.speed - direction), int(COMM_vars.speed + direction)]
        return COMM_vars.Motor_Power

    @staticmethod
    def mouseInput():
        if COMM_vars.CamPos[X_AXIS] > MOUSEX_MAX:
            COMM_vars.CamPos[X_AXIS] = MOUSEX_MAX
        if COMM_vars.CamPos[X_AXIS] < MOUSEX_MIN:
            COMM_vars.CamPos[X_AXIS] = MOUSEX_MIN
        if COMM_vars.CamPos[Y_AXIS] > MOUSEY_MAX:
            COMM_vars.CamPos[Y_AXIS] = MOUSEY_MAX
        if COMM_vars.CamPos[Y_AXIS] < MOUSEY_MIN:
            COMM_vars.CamPos[Y_AXIS] = MOUSEY_MIN

        return COMM_vars.CamPos

    def execute_cmd(self, cmd_string):
        #  system("clear")
        retcode = system(cmd_string)
        if retcode == 0:
            if Debug > 1: print("\nCommand executed successfully")
        else:
            if Debug > 1: print("\nCommand terminated with error: " + str(retcode))
        # raw_input("Press enter")
        return retcode
