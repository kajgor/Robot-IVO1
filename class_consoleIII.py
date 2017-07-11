import gi
gi.require_version('Gst', '1.0')
gi.require_version('Gdk', '3.0')
gi.require_version('GstVideo', '1.0')
from gi.repository import Gst, GstVideo, Gdk

import socket
from os import system
# import os
import cairo
import math

from init_variables import *
# from pygame.locals import *

# pygame.init()
Gst.init(None)

class RacConnection:
    def __init__(self):
        self.srv = None
        self.conoff = False

        # --- Gstreamer setup begin ---
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
            self.srv.shutdown(socket.SHUT_WR)
        except:
            if Debug > 1: print("...not connected!")

        try:
            self.srv.close()
        except AttributeError:
            self.srv = None

        if Debug > 1: print("Connection closed.")

    def estabilish_connection(self, Host, Port_Comm):
        # success = True
        self.srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_address = (Host, Port_Comm)
        if Debug > 1: print("Connecting...")
        try:
            self.srv.connect(server_address)

        except:
            retmsg = "Connection Error [" + server_address.__str__() + "]"
            if Debug > 0: print(retmsg)
            return retmsg, False

        retmsg = "Server connected!"
        if Debug > 1: print(retmsg)
        return retmsg, True

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

        data = self.srv.recv(15).decode(Encoding)
        if Debug > 2: print("CLIRCVD[len]: " + len(data).__str__())

        if data[0] == chr(COMM_BITSHIFT - 1) and data[14] == chr(10):
            return data
        else:
            self.srv.recv(1024)  # flush buffer
            if Debug > 1: print(">>>FlushBuffer>>>")
            return


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
        # print("msgtype:", msgtype)
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

        # self.disp_text("CamV: " + str(mouse[X_AXIS]) + " ", 350, 210, CYAN, DDBLUE)
        # self.disp_text("CamH: " + str(mouse[Y_AXIS]) + " ", 350, 230, CYAN, DDBLUE)


class RacUio:

    def on_key_press(self, event):
        keyname = Gdk.keyval_name(event.keyval)
        self.key_set(keyname, True)
        return keyname

    def on_key_release(self, event):
        keyname = Gdk.keyval_name(event.keyval)
        self.key_set(keyname, False)
        return keyname

    def key_set(RacUio, keyname, value):
        print("key", keyname, value)
        if keyname == "Left":
            KEY_control.Left = value

        elif keyname == "Right":
            KEY_control.Right = value

        elif keyname == "Up":
            KEY_control.Up = value

        elif keyname == "Down":
            KEY_control.Down = value

        elif keyname == "space":
            COMM_vars.speed = 0
            COMM_vars.direction = 0
            KEY_control.Space = value

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
            # if COMM_vars.direction > 0:
            #     offset = MAX_SPEED
            # else:
            #     offset = -MAX_SPEED
            offset = MAX_SPEED * (COMM_vars.direction / abs(COMM_vars.direction))
            direction = (-COMM_vars.direction + offset)

        return [int(speed - direction), int(speed + direction)]


    def get_mouseInput(self, event):
        mouseXY = event.GetPosition()
        mouseX = int(MOUSEX_MAX - mouseXY[0] / 2)
        mouseY = int(MOUSEY_MAX - mouseXY[1] / 2)
        if mouseX > MOUSEX_MAX:
            mouseX = MOUSEX_MAX
        if mouseX < MOUSEX_MIN:
            mouseX = MOUSEX_MIN
        if mouseY > MOUSEY_MAX:
            mouseY = MOUSEY_MAX
        if mouseY < MOUSEY_MIN:
            mouseY = MOUSEY_MIN
        # print mouseX.__str__() + "<>" + mouseY.__str__()
        return [mouseX, mouseY]

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

    def execute_cmd(self, cmd_string):
        #  system("clear")
        retcode = system(cmd_string)
        if retcode == 0:
            if Debug > 1: print("\nCommand executed successfully")
        else:
            if Debug > 1: print("\nCommand terminated with error: " + str(retcode))

        # raw_input("Press enter")
        return retcode

