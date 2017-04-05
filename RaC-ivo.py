### PYGAME IN WX ###
# A simple test of embedding Pygame in a wxPython frame
#
#
#
#
#

import pygame
import sys, time, socket, os
from os import system
# import init_variables
from init_variables import *
from config_rw import *
from class_console import *
# from pygame import display, draw, event, mouse, Surface

Rac_connection = RacConnection(socket)
Rac_Uio = RacUio()

class PygameDisplay(wx.Window):
    Motor_PWR = Motor_RPM = Motor_ACK = Motor_Power = mouse = [0, 0]
    Current = Voltage = speed = direction = 0

    def __init__(self, parent, ID):
        wx.Window.__init__(self, parent, ID)
        self.parent = parent
        self.hwnd = self.GetHandle()

        self.size = self.GetSizeTuple()
        self.draw_init = True

        self.timer = wx.Timer(self)
        self.Bind(wx.EVT_PAINT, self.OnPaint)
        self.Bind(wx.EVT_TIMER, self.Update, self.timer)
        self.Bind(wx.EVT_SIZE, self.OnSize)
        self.Bind(wx.EVT_KEY_DOWN, self.OnKeyDown)
        self.Bind(wx.EVT_MOTION, self.OnMouseMotion)
        self.Bind(wx.EVT_IDLE, self.OnIdle)
        # wx.EVT_IDLE(self, self.OnIdle)
        # self.Bind(wx.EVT_LEFT_DOWN, self.OnMouseLdown)

        self.fps = 60.0
        self.timespacing = 1000.0 / self.fps
        self.timer.Start(self.timespacing, False)

        # self.curframe = 0
        self.linespacing = 5

        self.initialized = False

    def OnMouseMotion(self, mouse_event):
        if mouse_event.LeftIsDown():
            self.mouse = Rac_Uio.get_mouseInput(mouse_event, self.mouse)

    def OnKeyDown(self, key):
        self.speed, self.direction = Rac_Uio.get_keyInput(key, self.speed, self.direction)

    def OnIdle(self, event):
        if not self.initialized:
            self.initialized = True

    def Update(self, event):
        # Any update tasks would go here (moving sprites, advancing animation frames etc.)
        if Rac_connection.connected == True:
            if self.speed != "HALT":
                self.Motor_Power = [0, 0]
                self.Motor_Power[RIGHT] = self.speed - self.direction
                self.Motor_Power[LEFT] = self.speed + self.direction
                # print Motor_Power
                request = Rac_Uio.encode_transmission(self.Motor_Power, self.mouse, "")
                resp = Rac_connection.transmit(request)
                # print "RESP>>> " + resp.__str__()
                self.Motor_PWR, self.Motor_RPM, self.Motor_ACK, self.Current, self.Voltage = Rac_Uio.decode_transmission(resp)
            else:
                halt_cmd = self.direction
                Rac_connection.transmit(halt_cmd)
                print "Closing connection..."
                Rac_connection.srv.close()
                print "Connection closed."
                Rac_connection.connected = False
                sys.exit(0)  # quit the program

            self.Redraw()

    def Redraw(self):
        pygame.font.init()
        # pygame.display.init()
        if self.draw_init:
            self.draw_init = False
            # Rac_Display = RacDisplay(self.display)

            self.screen = pygame.Surface(self.size, 0, 32)
            self.hwnd = self.GetHandle()
            print self.hwnd
            os.environ['SDL_WINDOWID'] == str(self.hwnd)

            pygame.display.set_caption("Robot IVO-1 console", "IVO-1")
            self.screen = pygame.display.set_mode((480, 360), pygame.DOUBLEBUF)

            pygame.init()
            pygame.display.flip()

        # self.screen.fill((0, 0, 0))

        Rac_display = RacDisplay(self.screen)
        Rac_display.plot_screen(self.Motor_Power, self.speed, self.direction, self.Motor_PWR, self.Motor_RPM, self.Motor_ACK,
                                self.mouse, self.Voltage, self.Current, Motor_DBG = [0, 0])
        # RacDisplay(self.screen).disp_big_text(str(self.curframe), 236, 130, DDBLUE, CYAN)
        # self.screen.blit(self.screen, (0, 0))
        # pygame.display.flip()

        s = pygame.image.tostring(self.screen, 'RGB')  # Convert the surface to an RGB string
        img = wx.ImageFromData(self.size[0], self.size[1], s)  # Load this string into a wx image
        bmp = wx.BitmapFromImage(img)  # Get the image in bitmap form
        dc = wx.ClientDC(self)  # Device context for drawing the bitmap
        dc.DrawBitmap(bmp, 0, 0, False)  # Blit the bitmap image to the display
        del dc

        # pygame.display.flip()


    def OnPaint(self, event):
        # self.Redraw()
        event.Skip()  # Make sure the parent frame gets told to redraw as well


    def OnSize(self, event):
        self.size = self.GetSizeTuple()
        self.draw_init = True


    def Kill(self, event):
        # Make sure Pygame can't be asked to redraw /before/ quitting by unbinding all methods which
        # call the Redraw() method
        # (Otherwise wx seems to call Draw between quitting Pygame and destroying the frame)
        # This may or may not be necessary now that Pygame is just drawing to surfaces
        self.Unbind(event=wx.EVT_PAINT, handler=self.OnPaint)
        self.Unbind(event=wx.EVT_TIMER, handler=self.Update, source=self.timer)


# class FoolDisplay(PygameDisplay):
#     def __init__(self, parent, id):
#         PygameDisplay.__init__(self, parent, id)
#         pygame.font.init()
#         self.mainfont = pygame.font.Font(None, 40)
#         self.text = self.mainfont.render("FOOOOOOL! NOW WE ARE ALL DAMNED!", True, (255, 0, 0))
#         self.borw = True  # True = draw a black background, False = draw a white background
#         self.points = []  # A list of points to draw
#
#         self.Bind(wx.EVT_LEFT_DOWN, self.OnClick)
#
#     def Update(self, event):
#         PygameDisplay.Update(self, event)
#         self.borw = not self.borw  # Alternate the background colour
#
#         for i, point in enumerate(self.points):  # Slide all the points down and slightly to the right
#             self.points[i] = (point[0] + 0.1, point[1] + 1)
#
#     def Redraw(self):
#         # If the size has changed, create a new surface to match it
#         if self.size_dirty:
#             self.screen = pygame.Surface(self.size, 0, 32)
#             self.size_dirty = False
#
#         # Draw the background
#         if self.borw:
#             self.screen.fill((0, 0, 0))
#         else:
#             self.screen.fill((255, 255, 255))
#
#         self.screen.blit(self.text, (0, 0))
#
#         # Draw circles at all the stored points
#         for point in self.points:
#             pygame.draw.circle(self.screen, (0, 255, 0), (int(point[0]), int(point[1])), 5)
#
#         s = pygame.image.tostring(self.screen, 'RGB')  # Convert the surface to an RGB string
#         img = wx.ImageFromData(self.size[0], self.size[1], s)  # Load this string into a wx image
#         bmp = wx.BitmapFromImage(img)  # Get the image in bitmap form
#         dc = wx.ClientDC(self)  # Device context for drawing the bitmap
#         dc.DrawBitmap(bmp, 0, 0, False)  # Blit the bitmap image to the display
#         del dc
#
#     def OnClick(self, event):
#         self.points.append(event.GetPositionTuple())  # Add a new point at the mouse position


class ConnectScreen(wx.Frame):

    def __init__(self, *args, **kwds):
        config_read(self, "rac.cfg")
        print self.Host + "< Host"
        print self.Port_Comm.__str__() + "< Comm"
        # begin wxGlade: ConnectScreen.__init__
        kwds["style"] = wx.CAPTION | wx.CLOSE_BOX | wx.FRAME_FLOAT_ON_PARENT
        wx.Frame.__init__(self, *args, **kwds)

        self.label_server_ip_address = wx.StaticText(self, wx.ID_ANY, "Server IP/address", style=wx.ALIGN_RIGHT)
        self.ip_address = wx.ComboBox(self, wx.ID_ANY, str(self.Host),
                                      choices=["127.0.0.1", "localhost", "athome21.hopto.org"], style=wx.CB_DROPDOWN)
        self.label_port = wx.StaticText(self, wx.ID_ANY, "Port", style=wx.ALIGN_RIGHT)
        self.ip_port = wx.SpinCtrl(self, wx.ID_ANY, str(self.Port_Comm), min=100, max=19999)
        self.button_setup = wx.Button(self, wx.ID_PROPERTIES, "")
        self.checkbox_local_test = wx.CheckBox(self, wx.ID_ANY, "Local Test ", style=wx.ALIGN_RIGHT)
        # self.static_line_1 = wx.StaticLine(self, wx.ID_ANY)
        self.button_cancel = wx.Button(self, wx.ID_CANCEL, "")
        self.button_commit = wx.Button(self, wx.ID_OPEN, "")

        self.__set_properties()
        self.__do_layout()
        # end wxGlade

    def __set_properties(self):
        # begin wxGlade: ConnectScreen.__set_properties
        self.SetTitle("Remote Access Console")
        _icon = wx.NullIcon
        _icon.CopyFromBitmap(
            wx.Bitmap("icons/robot_icon_24x24.png", wx.BITMAP_TYPE_ANY))
        self.SetIcon(_icon)
        self.SetFocus()
        self.label_server_ip_address.SetMinSize((130, 20))
        self.ip_address.SetFocus()
        self.ip_port.SetMinSize((100, -1))
        self.checkbox_local_test.SetValue(1)
        # end wxGlade

        self.button_setup.Bind(wx.EVT_BUTTON, self.OnButton_setup)
        self.button_cancel.Bind(wx.EVT_BUTTON, self.OnButton_cancel)
        self.button_commit.Bind(wx.EVT_BUTTON, self.OnButton_commit)

    def __do_layout(self):
        # begin wxGlade: ConnectScreen.__do_layout
        grid_sizer_MF = wx.GridSizer(2, 4, 5, 1)
        grid_sizer_MF.Add(self.label_server_ip_address, 0, wx.ALIGN_CENTER, 0)
        grid_sizer_MF.Add(self.ip_address, 0, wx.ALIGN_CENTER, 0)
        grid_sizer_MF.Add(self.label_port, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_RIGHT, 0)
        grid_sizer_MF.Add(self.ip_port, 0, wx.ALIGN_CENTER, 0)
        grid_sizer_MF.Add(self.button_setup, 0, wx.ALIGN_CENTER, 0)
        grid_sizer_MF.Add(self.checkbox_local_test, 0, wx.ALIGN_CENTER, 0)
        # grid_sizer_MF.Add(self.static_line_1, 0, wx.ALIGN_CENTER, 0)
        grid_sizer_MF.Add(self.button_cancel, 0, wx.ALIGN_CENTER, 0)
        grid_sizer_MF.Add(self.button_commit, 0, wx.ALIGN_CENTER, 0)
        self.SetSizer(grid_sizer_MF)
        grid_sizer_MF.Fit(self)
        self.Layout()
        self.Centre()
        # end wxGlade

    def execute_cmd(self, cmd_string):
        #  system("clear")
        retcode = system(cmd_string)
        print ""
        if retcode == 0:
            print "Command executed successfully"
        else:
            print "Command terminated with error: " + str(retcode)
        # raw_input("Press enter")
        print ""

    def SaveConfig(self):
        config_save(self, "rac.cfg")

    def OnButton_setup(event, button_label):
        wx.MessageBox("Not implemented yet!", "Button pressed.");

    def OnButton_cancel(event, button_label):
        #  wx.MessageBox("This is a message.", "Button pressed.");
        event.SaveConfig()
        event.Destroy()

    def OnButton_commit(event, button_label):
        global Port_Video, Port_Audio, srv, Host, Port_Comm

        print "Button Label: " + str(button_label)

        Host = event.ip_address.GetValue()
        Port_Comm = event.ip_port.GetValue()

        print "Host: " + Host.__str__()
        print "Port: " + Port_Comm.__str__()

        event.SaveConfig()

        srv = Rac_connection.estabilish_connection(Host, Port_Comm)
        time.sleep(3)

        #        event.button_commit.SetLabel('Connecting...')
        # Client
        # gst-launch-1.0 videotestsrc pattern=smpte ! video/x-raw,width=320,height=240 ! glimagesink (default)
        # /gtksink/cacasink/autovideosink sync=false
        #
        #

        event.Gstreamer_Path = "/usr/bin/"
        gstreamer_cmd = event.Gstreamer_Path + "gst-launch-1.0 tcpclientsrc "
        if event.checkbox_local_test.GetValue():
            gstreamer_cmd += "host=127.0.0.1 port=12344"
            gstreamer_cmd += " ! gdpdepay ! videoconvert ! ximagesink sync=false"
        else:
            gstreamer_cmd += "host=" + Host + " port=" + event.Port_Video.__str__()
            gstreamer_cmd += " ! gdpdepay ! rtph264depay ! avdec_h264 ! videoconvert ! autovideosink sync=false"

        print gstreamer_cmd
        event.execute_cmd(gstreamer_cmd + ' &')

        PygameDisplay(event, -1).Show()

        # Frame.button.SetLabel("DISCONNECT")
        # Frame.button.Enable(True)

        event.Destroy()

# end of class ConnectScreen

# class FoolFrame(wx.Frame):
#     def __init__(self, parent):
#         wx.Frame.__init__(self, parent, -1, size=(600, 300), style=wx.CAPTION | wx.SYSTEM_MENU | wx.CLOSE_BOX)
#
#         # self.display = FoolDisplay(self, -1)
#
#         self.SetTitle("NOOOOOOOO!")


class Frame(wx.Frame):
    def __init__(self, parent):
        wx.Frame.__init__(self, parent, -1, size=(600, 600))

        self.display = PygameDisplay(self, -1)

        self.statusbar = self.CreateStatusBar()
        self.statusbar.SetFieldsCount(3)
        self.statusbar.SetStatusWidths([-3, -4, -2])
        self.statusbar.SetStatusText("RAC Console", 0)
        self.statusbar.SetStatusText("Awaiting connection...", 1)

        self.Bind(wx.EVT_SIZE, self.OnSize)
        self.Bind(wx.EVT_CLOSE, self.Kill)

        self.curframe = 0

        self.SetTitle("Remote Access Console - IVO")

        self.slider = wx.Slider(self, wx.ID_ANY, 5, 1, 10, style=wx.SL_HORIZONTAL | wx.SL_LABELS)
        self.slider.SetTickFreq(0.1, 1)
        self.button = wx.Button(self, -1, "CONNECT")

        self.timer = wx.Timer(self)

        self.Bind(wx.EVT_SCROLL, self.OnScroll)
        self.Bind(wx.EVT_SIZE, self.OnSize)
        self.Bind(wx.EVT_TIMER, self.Update, self.timer)
        self.Bind(wx.EVT_BUTTON, self.ButtonClick, self.button)
        self.Bind(wx.EVT_KEY_DOWN, self.OnKeyDown)

        self.timer.Start((1000.0 / self.display.fps))

        self.sizer = wx.BoxSizer(wx.VERTICAL)
        self.sizer2 = wx.BoxSizer(wx.HORIZONTAL)

        self.sizer.Add(self.sizer2, 0, flag=wx.EXPAND)
        self.sizer.Add(self.display, 1, flag=wx.EXPAND | wx.ALIGN_CENTRE, border=10)
        self.sizer2.Add(self.slider, 1, flag=wx.EXPAND | wx.RIGHT, border=5)
        self.sizer2.Add(self.button, 0, flag=wx.EXPAND | wx.ALL, border=5)

        self.display.SetFocus()
        self.button.Enable(True)

        self.SetAutoLayout(True)
        self.SetSizer(self.sizer)
        self.Layout()

    def OnKeyDown(self, key):
        speed, direction = Rac_Uio.get_keyInput(key, PygameDisplay.speed, PygameDisplay.direction)
        PygameDisplay.speed = speed
        PygameDisplay.direction = direction
        self.Layout()

    def Kill(self, event):
        self.display.Kill(event)
        self.Destroy()

    def OnSize(self, event):
        self.Layout()

    def Update(self, event):
        self.curframe += 1
        self.statusbar.SetStatusText("Frame %i" % self.curframe, 2)

    def OnScroll(self, event):
        self.display.linespacing = self.slider.GetValue()

    def ButtonClick(self, event):
        ConnectScreen(self).Show()
        # self.button.SetLabel("DISCONNECT")
        self.button.Enable(False)
        self.Layout()


class App(wx.App):
    def OnInit(self):
        self.frame = Frame(parent=None)
        self.frame.Show()
        self.SetTopWindow(self.frame)

        return True


if __name__ == "__main__":
    Console = App()
    Console.MainLoop()
