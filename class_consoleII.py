import pygame
# import wx
import socket
from os import system
# from thread import *

from init_variables import *
# from pygame.locals import *
import gi
gi.require_version('Gst', '1.0')
from gi.repository import Gst, GstVideo

pygame.init()
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

        self.srv.close()
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

        if not retmsg:
            if Debug > 1: print("Connected!")

            retmsg = self.player.set_state(Gst.State.PLAYING)

            if retmsg == Gst.StateChangeReturn.FAILURE:
                retmsg = "VIDEO CONNECTION ERROR: Unable to set the pipeline to the playing state."
                success = False
            else:
                retmsg = "VIDEO CONNECTION ESTABILISHED: OK"

            return retmsg, success
            # [thread: " + get_ident().__str__() + "]"
            # while True:
            #     if not self.conoff:
            #         self.close_connection("")
            #         print "[Exiting connection thread]"
            #         exit_thread()
            #         # interrupt_main()
            #     time.sleep(1)
        else:
            if Debug > 0: print(retmsg)
            return retmsg, False

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
    green_arrow = pygame.image.load('images/green_arrow.png')
    red_arrow = pygame.image.load('images/red_arrow.png')
    cyan_arrow = pygame.image.load('images/cyan_arrow.png')
    gray_arrow = pygame.image.load('images/gray_arrow.png')
    background = pygame.image.load('images/HUD.jpg')
    RacConnection = RacConnection()

    def __init__(self, scr):
        self.screen = scr

    def disp_text(self, rawtext, x, y, f_color, b_color):
        #    font = pygame.font.Font(None, 15)
        myfont = pygame.font.SysFont("monospace", 15)
        out_text = myfont.render(str(rawtext), 1, f_color, b_color)
        self.screen.blit(out_text, (x, y))

    def disp_big_text(self, rawtext, x, y, f_color, b_color):
        #    font = pygame.font.Font(None, 20)
        myfont = pygame.font.SysFont("monospace", 20)
        out_text = myfont.render(str(rawtext), 1, f_color, b_color)
        self.screen.blit(out_text, (x, y))

    def disp_small_text(self, rawtext, x, y, f_color, b_color):
        #    font = pygame.font.Font(None, 10)
        myfont = pygame.font.SysFont("monospace", 10)
        out_text = myfont.render(str(rawtext), 1, f_color, b_color)
        self.screen.blit(out_text, (x, y))

    def plot_screen(self, Motor_Power, speed, direction):
        self.screen.blit(self.background, (0, 0))

        if speed < 0:
            rotated = pygame.transform.rotate(self.cyan_arrow, direction * 4 + 180)
        elif speed > 0:
            rotated = pygame.transform.rotate(self.cyan_arrow, direction * 4)
        else:
            if abs(Motor_Power[RIGHT]) + abs(Motor_Power[LEFT]) != 0:
                rotated = pygame.transform.rotate(self.cyan_arrow, direction * 4)
            else:
                rotated = pygame.transform.rotate(self.gray_arrow, direction * 4)
        # .. position the arrow on screen
        # .. render the arrow to screen
        rect = rotated.get_rect()
        rect.center = position
        self.screen.blit(rotated, rect)

        power_displayed = int(Motor_Power[RIGHT] + Motor_Power[LEFT])
        # power_displayed = int(Motor_Power[RIGHT] + Motor_Power[LEFT]) / 2.5
        # print power_displayed
        if abs(power_displayed) == 0:
            self.disp_big_text("--", 70, 130, CYAN, BLACK)
        elif abs(power_displayed) < 10:
            self.disp_big_text(abs(power_displayed), 70 + 6, 130, DDBLUE, CYAN)
        elif abs(power_displayed) < 100:
            self.disp_big_text(abs(power_displayed), 70, 130, DDBLUE, CYAN)
        elif abs(power_displayed) > 100:
            self.disp_big_text("MAX", 70 - 6, 130, DRED, CYAN)
        else:
            self.disp_big_text(abs(power_displayed), 70 - 6, 130, DDBLUE, CYAN)

        # self.disp_text("CamV: " + str(mouse[X_AXIS]) + " ", 350, 210, CYAN, DDBLUE)
        # self.disp_text("CamH: " + str(mouse[Y_AXIS]) + " ", 350, 230, CYAN, DDBLUE)

    def on_message(self, bus, message):
        msgtype = message.type
        if msgtype == Gst.MessageType.EOS:
            RacConnection.player.set_state(Gst.State.NULL)
            self.button_connect.set_active(False)
            if Debug > 1:
                self.statusbar.push(self.context_id, "VIDEO CONNECTION EOS: SIGNAL LOST")
                print ("EOS: SIGNAL LOST")

        elif msgtype == Gst.MessageType.ERROR:
            self.player.set_state(Gst.State.NULL)
            err, debug = message.parse_error()
            debug_s = debug.split("\n")
            self.button_connect.set_active(False)
            if Debug > 0:
                self.statusbar.push(self.context_id, debug_s[debug_s.__len__() - 1])
                print ("ERROR:", debug_s)

    def on_sync_message(self, bus, message):
        # print ("on_sync_message " + message.type.__str__())
        if message.get_structure().get_name() == 'prepare-window-handle':
            imagesink = message.src
            imagesink.set_property("force-aspect-ratio", True)
            imagesink.set_window_handle(self.movie_window.get_property('window').get_xid())
        # else:
        #     print("message.get_structure().get_name():", message.get_structure().get_name())

        return

class RacUio:
    # def __init__(self):
        # pygame.display.init()

    def get_keyInput(self, event, speed, direction):
        k_up = k_down = k_right = k_left = 0

#        ToDo:
#         if event.type == pygame.QUIT:
#             return "HALT", HALT_1, mouseX, mouseY

        # key = event.keyval
        events = pygame.event.get()
        print("Pygame events:", events)
        for event in events:
            if event.type == pygame.KEYDOWN:
                down = 1
                print("Pygame key:", event.key)
                if event.key == pygame.K_RIGHT:
                    k_right = down * -TURN_SPEED

                elif event.key == pygame.K_LEFT:
                    k_left = down * TURN_SPEED

                elif event.key == pygame.K_UP:
                    if speed > MAX_REVERSE_SPEED:
                        k_up = down * ACCELERATION
                    else:
                        k_up = down * 1

                elif event.key == pygame.K_DOWN:
                    if speed < MAX_FORWARD_SPEED:
                        k_down = down * -ACCELERATION
                    else:
                        k_down = down * -1

                elif event.key == pygame.K_SPACE:
                    speed = 0
                    direction = 0

                elif event.key == pygame.K_ESCAPE:
                    # transmit("R0L0")
                    return "HALT", HALT_0

        # SIMULATION
        # .. new speed and direction based on acceleration and turn
        speed += (k_up + k_down)
        if speed > MAX_FORWARD_SPEED:
            speed = MAX_FORWARD_SPEED
        if speed < MAX_REVERSE_SPEED:
            speed = MAX_REVERSE_SPEED

        direction += (k_right + k_left)
        if direction < MAX_LEFT_ANGLE:
            direction = MAX_LEFT_ANGLE
        if direction > MAX_RIGHT_ANGLE:
            direction = MAX_RIGHT_ANGLE

        return speed, direction

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
