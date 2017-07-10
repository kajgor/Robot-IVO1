import gi
gi.require_version('Gst', '1.0')
gi.require_version('Gdk', '3.0')
gi.require_version('GstVideo', '1.0')
from gi.repository import Gst, GstVideo, Gdk

import socket
from os import system
# import os
import cairo

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
        success = True
        self.srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_address = (Host, Port_Comm)
        if Debug > 1: print("Connecting...")
        try:
            retmsg = self.srv.connect(server_address)

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
            # retmsg = "VIDEO CONNECTION ERROR: Unable to set the pipeline to the playing state."
            # success = False
        else:
            return True
            # retmsg = "VIDEO CONNECTION ESTABILISHED: OK"
            # success = True

        # if Debug > 1: print(retmsg)
        # return retmsg, success

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
    background = cairo.ImageSurface.create_from_png("images/HUD_small.png")
    # def __init__(self):


    def on_DrawingArea_Control_draw(self, message):
        # print("on_draw", direction)

        message.set_source_surface(self.background, 15, 0)
        message.paint()

        message.set_source_rgb(0, 0.44, 0.9)
        message.set_line_width(1)

        message.translate(105, 81)

        message.rotate(COMM_vars.direction)

        for i in range(5):
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
        # else:
        #     print("message.get_structure().get_name():", message.get_structure().get_name())

        # self.disp_text("CamV: " + str(mouse[X_AXIS]) + " ", 350, 210, CYAN, DDBLUE)
        # self.disp_text("CamH: " + str(mouse[Y_AXIS]) + " ", 350, 230, CYAN, DDBLUE)


class RacUio:

    # def __init__(self):
        # self.Left = False
        # self.Right = False

    def on_key_press(self, event):
        keyname = Gdk.keyval_name(event.keyval)
        # print("keypress", keyname)
        if keyname == "Left":
            KEY_control.Left = True

        elif keyname == "Right":
            KEY_control.Right = True

        elif keyname == "Up":
            KEY_control.Up = True

        elif keyname == "Down":
            KEY_control.Down = True

        return keyname

    def on_key_release(self, event):
        keyname = Gdk.keyval_name(event.keyval)
        # print("keyrelease", keyname)
        if keyname == "Left":
            KEY_control.Left = False

        elif keyname == "Right":
            KEY_control.Right = False

        elif keyname == "Up":
            KEY_control.Up = False

        elif keyname == "Down":
            KEY_control.Down = False

        return keyname

    def get_speed_and_direction(self):
        print("reeee:", KEY_control.Down, KEY_control.Up, KEY_control.Left, KEY_control.Right, COMM_vars.speed, COMM_vars.direction)
        if KEY_control.Down is True:
            if COMM_vars.speed > MAX_REVERSE_SPEED:
                COMM_vars.speed -= ACCELERATION

        if KEY_control.Up is True:
            if COMM_vars.speed < MAX_FORWARD_SPEED:
                COMM_vars.speed += ACCELERATION

        if KEY_control.Left is True:
            if COMM_vars.direction > MAX_LEFT_ANGLE:
                COMM_vars.direction -= ACCELERATION

        if KEY_control.Right is True:
            if COMM_vars.direction < MAX_RIGHT_ANGLE:
                COMM_vars.direction += ACCELERATION

        # print("get_speed_and_direction", self.speed, self.direction, ACCELERATION)
        return COMM_vars.speed, COMM_vars.direction

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

class arrow(object):
    points = (
        (0, -35),
        (-28, 35),
        (0, 25),
        (28, 35),
        (0, -35)
    )
    SPEED = 20
    TIMER_ID = 1

class KEY_control:
    Left = False
    Right = False
    Up = False
    Down = False

class COMM_vars:
    speed = 0
    direction = 0
