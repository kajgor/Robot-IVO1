import pygame
import wx
import socket
from os import system
# from thread import *

from init_variables import *
# from pygame.locals import *


class RacConnection:
    def __init__(self):
        self.srv = None
        self.conoff = False

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

    def close_connection(self, gstreamer_cmd):
        if Debug > 1: print("Closing connection...")
        if gstreamer_cmd:
            RacUio().execute_cmd("pkill -f '" + gstreamer_cmd + "'")

        try:
            self.srv.shutdown(socket.SHUT_WR)
        except:
            if Debug > 1: print("...not connected!")

        self.srv.close()
        self.srv = None
        if Debug > 1: print("Connection closed.")

    def estabilish_connection(self, Host, Port_Comm):
        self.srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_address = (Host, Port_Comm)
        if Debug > 1: print("Connecting...")
        try:
            retmsg = self.srv.connect(server_address)

        except:
            retmsg = "Connection Error [" + server_address.__str__() + "]"

        if not retmsg:
            if Debug > 1: print("Connected!")
            return True
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
            return False

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

    def plot_screen(self, Motor_Power, speed, direction, Motor_PWR, Motor_RPM, Motor_ACK, mouse, Voltage, Current,
                    Motor_DBG):
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
            self.disp_big_text("--", 230, 130, CYAN, BLACK)
        elif abs(power_displayed) < 10:
            self.disp_big_text(abs(power_displayed), 236, 130, DDBLUE, CYAN)
        elif abs(power_displayed) < 100:
            self.disp_big_text(abs(power_displayed), 230, 130, DDBLUE, CYAN)
        elif abs(power_displayed) > 100:
            self.disp_big_text("MAX", 224, 130, DRED, CYAN)
        else:
            self.disp_big_text(abs(power_displayed), 224, 130, DDBLUE, CYAN)

        self.disp_text("R Power: " + str(Motor_PWR[RIGHT]), 350, 37, CYAN, DDBLUE)
        self.disp_text("R Rpm:   " + str(Motor_RPM[RIGHT]), 350, 57, CYAN, DDBLUE)
        self.disp_text("R ACK:   " + str(Motor_ACK[RIGHT]), 350, 77, CYAN, DDBLUE)

        self.disp_text("L Power: " + str(Motor_PWR[LEFT]), 10, 37, CYAN, DDBLUE)
        self.disp_text("L Rpm:   " + str(Motor_RPM[LEFT]), 10, 57, CYAN, DDBLUE)
        self.disp_text("L ACK:   " + str(Motor_ACK[LEFT]), 10, 77, CYAN, DDBLUE)

        # self.disp_text("L DeBug: " + str(Motor_DBG[LEFT]), 10, 310, CYAN, DDBLUE)
        # self.disp_text("R DeBug: " + str(Motor_DBG[RIGHT]), 130, 310, CYAN, DDBLUE)
        # self.disp_text("Voltage: " + str(Voltage) + " V ", 10, 330, CYAN, DDBLUE)
        # self.disp_text("Current: " + str(Current) + " mA ", 150, 330, CYAN, DDBLUE)

        # self.disp_text("CamV: " + str(mouse[X_AXIS]) + " ", 350, 310, CYAN, DDBLUE)
        # self.disp_text("CamH: " + str(mouse[Y_AXIS]) + " ", 350, 330, CYAN, DDBLUE)
        self.disp_text("CamV: " + str(mouse[X_AXIS]) + " ", 350, 210, CYAN, DDBLUE)
        self.disp_text("CamH: " + str(mouse[Y_AXIS]) + " ", 350, 230, CYAN, DDBLUE)


class RacUio:
    # def __init__(self):
        # pygame.display.init()

    def get_keyInput(self, event, speed, direction):
        k_up = k_down = k_right = k_left = 0

#        ToDo:
#         if event.type == pygame.QUIT:
#             return "HALT", HALT_1, mouseX, mouseY

        key = event.GetKeyCode()
        down = 1
        if key == wx.WXK_RIGHT:
            k_right = down * -TURN_SPEED

        elif key == wx.WXK_LEFT:
            k_left = down * TURN_SPEED

        elif key == wx.WXK_UP:
            if speed > MAX_REVERSE_SPEED:
                k_up = down * ACCELERATION
            else:
                k_up = down * 1

        elif key == wx.WXK_DOWN:
            if speed < MAX_FORWARD_SPEED:
                k_down = down * -ACCELERATION
            else:
                k_down = down * -1

        elif key == wx.WXK_SPACE:
            speed = 0
            direction = 0

        elif key == wx.WXK_ESCAPE:
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
