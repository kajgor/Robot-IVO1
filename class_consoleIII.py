#!/usr/bin/env python
# -*- coding: CP1252 -*-

import socket
import cairo
import math

import gi
gi.require_version('Gst', '1.0')
gi.require_version('Gdk', '3.0')
gi.require_version('GstVideo', '1.0')
from gi.repository import Gst, GstVideo, Gdk
from os import system
from _thread import *
from init_variables import *

###############################################################################
################   MAIN LOOP START   ##########################################
###############################################################################
class MainLoop:
    def __init__(self, GUI):
        self.counter = 0
        self.GUI = GUI

    def on_timer(self):
        self.counter += 1

        RacUio().get_speed_and_direction()

        Motor_Power = RacUio().get_MotorPower()
        Mouse = RacUio().mouseInput()

        # print("RacConnection().connected", COMM_vars.connected)
        # localhost 5000
        # Any update tasks would go here (moving sprites, advancing animation frames etc.)
        if COMM_vars.connected is True:
            if RacConnection().check_connection(""):
                if COMM_vars.speed != "HALT":

                    request = RacConnection().encode_transmission(COMM_vars.Motor_Power, KEY_control.mouseXY, "")
                    resp = RacConnection().transmit(request)

                    print("request/resp:", request, resp)

                    if resp is not None:
                        COMM_vars.Motor_PWR, COMM_vars.Motor_RPM, COMM_vars.Motor_ACK, COMM_vars.Current, COMM_vars.Voltage\
                            = RacConnection().decode_transmission(resp)
                else:
                    halt_cmd = HALT_0
                    RacConnection().transmit(halt_cmd)
                    self.GUI.srv.close()
                    COMM_vars.connected = False
                    # sys.exit(0)  # quit the program

            print("Motor_Power", Motor_Power, "Mouse", Mouse)

        # self.GUI.counter.set_text("Frame %i" % self.delta)
        self.GUI.statusbar2.push(self.GUI.context_id2, self.counter.__str__())
        self.GUI.drawingarea_control.queue_draw()

        # print("Motor_Power", Motor_Power, "Mouse", Mouse)
        return True

###############################################################################
################   MAIN LOOP END   ############################################
###############################################################################

class RacConnection:
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

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

    def check_connection(self, HostIp):
        try:
            status = self.srv.getsockname()
        except:
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

    def close_connection(self):
        if Debug > 1: print("Closing connection...")
        self.player.set_state(Gst.State.NULL)

        try:
            self.srv.shutdown(socket.SHUT_RDWR)
        except:
            if Debug > 1: print("...not connected!")

        try:
            self.srv.close()
        except AttributeError:
            self.srv = None

        COMM_vars.connected = False
        if Debug > 1: print("Connection closed.")

    def estabilish_connection(self, Host, Port_Comm):
        server_address = (Host, Port_Comm)
        if Debug > 1: print("Connecting...")

        retmsg = "Server connected!"
        COMM_vars.connected = True

        try:
            self.srv.connect(server_address)

        except:
            retmsg = "Connection Error [" + server_address.__str__() + "]"
            self.close_connection()
            if Debug > 0: print(retmsg)
            COMM_vars.connected = False

        if Debug > 1: print(retmsg)
        print("COMM_vars.connected", COMM_vars.connected)
        return retmsg, COMM_vars.connected

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

    def transmit(self, out_str):
        sendenc = chr(COMM_BITSHIFT - 1) + out_str + chr(10)
        if Debug > 2: print("CLISENT[len]: " + len(sendenc).__str__())

        try:
            self.srv.sendall(bytes(sendenc, Encoding))
        except BrokenPipeError:
            return None

        try:
            data = self.srv.recv(15).decode(Encoding)
        except ConnectionResetError:
            return None

        if Debug > 2: print("CLIRCVD[len]: " + len(data).__str__())

        if data[0] == chr(COMM_BITSHIFT - 1) and data[14] == chr(10):
            return data
        else:
            self.srv.recv(1024)  # flush buffer
            if Debug > 1: print(">>>FlushBuffer>>>")
            return

    def get_host_and_port(self, GUI):
        if GUI.checkbutton_localtest.get_active() is True:
            Host = GUI.TEST_Host
            Port_Comm = GUI.TEST_Port.__int__()
        else:
            Host = GUI.combobox_host.get_active_text()
            Port_Comm = GUI.spinbutton_port.get_value().__int__()

        return Host, Port_Comm

    def update_server_list(self, GUI):
        list_iter = GUI.combobox_host.get_active_iter()
        if list_iter is not None:
            model = GUI.combobox_host.get_model()
            Host, Port = model[list_iter][:2]
            try:
                Port = Port[:Port.index('.')]
            except:
                Port = Port

            print("Selected: Port=%s, Host=%s" % (int(Port), Host))
        else:
            entry = GUI.combobox_host.get_child()
            GUI.combobox_host.insert(0, GUI.spinbutton_port.get_value().__str__(), entry.get_text())
            GUI.combobox_host.set_active(0)

            print("New entry: %s" % entry.get_text())
            print("New port: %s" % GUI.spinbutton_port.get_value().__str__())

    def HostList_get(self, GUI, HostToFind):
        HostList_str = []
        model = GUI.combobox_host.get_model()
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

    def config_snapshot(self, Host):
        self.Host = Host
        # ToDo:
        self.Port_Comm = "5000"
        self.Port_Video = "5001"
        self.Port_Audio = "5002"
        self.Gstreamer_Path = "/usr/bin"

    def load_HostList(self, GUI, HostList_str):
        x = 0
        for HostName in HostList_str:
            Host = HostName.split(":")[0]
            Port = HostName.split(":")[1]
            GUI.combobox_host.insert(x, Port, Host)
            x += 1

    def connect_gui(self, GUI):
        GUI.combobox_host.set_sensitive(False)
        GUI.checkbutton_localtest.set_sensitive(False)
        GUI.spinbutton_port.set_sensitive(False)

    def disconnect_gui(self, GUI):
        GUI.statusbar.push(GUI.context_id, "Disconnected.")

        GUI.button_connect.set_active(False)
        GUI.checkbutton_localtest.set_sensitive(True)

        if GUI.checkbutton_localtest.get_active() is False:
            GUI.combobox_host.set_sensitive(True)
            GUI.spinbutton_port.set_sensitive(True)

    def decode_transmission(self, resp):
        # Motor_ACK - last value accepted by the driver
        # Motor_PWR - power delivered to motors
        # Motor_RPM - Motor rotations

        Motor_PWR = [0, 0]
        Motor_PWR[RIGHT] = (ord(resp[1]) - COMM_BITSHIFT) + (ord(resp[2]) - COMM_BITSHIFT)
        Motor_PWR[LEFT] = (10 * ((ord(resp[1]) - COMM_BITSHIFT) % 10)) + (ord(resp[3]) - COMM_BITSHIFT)

        Motor_RPM = [0, 0]
        Motor_RPM[RIGHT] = (ord(resp[4]) - COMM_BITSHIFT) + (ord(resp[5]) - COMM_BITSHIFT)
        Motor_RPM[LEFT] = (10 * ((ord(resp[4]) - COMM_BITSHIFT) % 10)) + (ord(resp[6]) - COMM_BITSHIFT)

        Motor_ACK = [0, 0]
        Motor_ACK[RIGHT] = (ord(resp[7]) - 51 - COMM_BITSHIFT) * 5
        Motor_ACK[LEFT] = (ord(resp[8]) - 51 - COMM_BITSHIFT) * 5

        Current = (ord(resp[9]) - COMM_BITSHIFT) * 100 + (ord(resp[10]) - COMM_BITSHIFT)
        Voltage = float((ord(resp[11]) - COMM_BITSHIFT) * 100 + (ord(resp[12]) - COMM_BITSHIFT)) * 0.1

        return Motor_PWR,\
               Motor_RPM,\
               Motor_ACK,\
               Current,\
               Voltage

    def encode_transmission(self, Motor_Power, mouse, request):
        if not request:
            request = chr(Motor_Power[RIGHT] + 51 + COMM_BITSHIFT)
            request += chr(Motor_Power[LEFT] + 51 + COMM_BITSHIFT)
            request += chr(mouse[X_AXIS])
            request += chr(mouse[Y_AXIS])

        return request


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

        # Background arrow
        message.set_source_rgb(0.25, 0.25, 0.25)
        for i in range(4):
            message.line_to(arrow.points[i][0], arrow.points[i][1])
        message.fill()
        message.set_source_rgb(0, 0.75, 0.75)
        for i in range(5):
            message.line_to(arrow.points[i][0], arrow.points[i][1])
        message.stroke()
        # Speed arrow
        message.set_source_rgb(abs(COMM_vars.speed/MAX_SPEED), 1 - abs(COMM_vars.speed/MAX_SPEED), 0)
        message.line_to(arrow.points[0][0], arrow.points[0][1] + 60 - abs((COMM_vars.speed / MAX_SPEED) * 50))
        for i in range(1, 4):
                message.line_to(arrow.points[i][0], arrow.points[i][1])
        message.fill()

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

    def keybuffer_set(RacUio, event, value):
        key_name = Gdk.keyval_name(event.keyval)
        # print("key", keyname, value)
        if key_name == "Left":
            KEY_control.Left = value

        elif key_name == "Right":
            KEY_control.Right = value

        elif key_name == "Up":
            KEY_control.Up = value

        elif key_name == "Down":
            KEY_control.Down = value

        elif key_name == "space":
            COMM_vars.speed = 0
            COMM_vars.direction = 0
            KEY_control.Space = value

        return key_name

    def on_mouse_press(self, widget, mouse_event):
        self.mousebuffer_set(mouse_event, True)

    def on_mouse_release(self, widget, mouse_event):
        self.mousebuffer_set(mouse_event, False)

    def mousebuffer_set(RacUio, mouse_event, value):
        if mouse_event.button == Gdk.BUTTON_PRIMARY:
            KEY_control.Mouse_L = value
            KEY_control.mouseXY = [int(mouse_event.x), int(mouse_event.y)]

        if mouse_event.button == Gdk.BUTTON_SECONDARY:
            KEY_control.Mouse_R = value
            KEY_control.mouseXY = [None, None]

    def on_motion_notify(self, widget, mouse_event):
        KEY_control.mouseXY = [int(mouse_event.x), int(mouse_event.y)]

    def get_speed_and_direction(self):
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

    def get_MotorPower(self):
        speed = COMM_vars.speed
        if COMM_vars.direction < MAX_SPEED/2 and COMM_vars.direction > -MAX_SPEED/2:
            direction = COMM_vars.direction
        else:
            offset = MAX_SPEED * (COMM_vars.direction / abs(COMM_vars.direction))
            direction = (-COMM_vars.direction + offset)

        return [int(speed - direction), int(speed + direction)]

    def mouseInput(self):
        # if KEY_control.Mouse_L is True:
        # mouseX = KEY_control.mouseXY[RIGHT]
        # mouseY = KEY_control.mouseXY[LEFT]

        mouseX = int(MOUSEX_MAX - KEY_control.mouseXY[RIGHT] / 2)
        mouseY = int(MOUSEY_MAX - KEY_control.mouseXY[LEFT] / 2)
        if mouseX > MOUSEX_MAX:
            KEY_control.mouseXY[RIGHT] = MOUSEX_MAX
        if mouseX < MOUSEX_MIN:
            KEY_control.mouseXY[RIGHT] = MOUSEX_MIN
        if mouseY > MOUSEY_MAX:
            KEY_control.mouseXY[LEFT] = MOUSEY_MAX
            mouseY = MOUSEY_MAX
        if mouseY < MOUSEY_MIN:
            KEY_control.mouseXY[LEFT] = MOUSEY_MIN
        # print mouseX.__str__() + "<>" + mouseY.__str__()
        return KEY_control.mouseXY

    def execute_cmd(self, cmd_string):
        #  system("clear")
        retcode = system(cmd_string)
        if retcode == 0:
            if Debug > 1: print("\nCommand executed successfully")
        else:
            if Debug > 1: print("\nCommand terminated with error: " + str(retcode))
        # raw_input("Press enter")
        return retcode
