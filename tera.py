### PYGAME IN WX ###
# A simple test of embedding Pygame in a wxPython frame
#
# By David Barker (aka Animatinator), 14/07/2010
# Patch for cross-platform support by Sean McKean, 16/07/2010
# Patch to fix redrawing issue by David Barker, 20/07/2010
# Second window demo added by David Barker, 21/07/2010

import wx, sys, os, pygame, time, socket
from os import system
from config_rw import *
from init_variables import *

class PygameDisplay(wx.Window):
    def __init__(self, parent, ID):
        wx.Window.__init__(self, parent, ID)
        self.parent = parent
        self.hwnd = self.GetHandle()

        self.size = self.GetSizeTuple()
        self.size_dirty = True

        self.timer = wx.Timer(self)
        self.Bind(wx.EVT_PAINT, self.OnPaint)
        self.Bind(wx.EVT_TIMER, self.Update, self.timer)
        self.Bind(wx.EVT_SIZE, self.OnSize)

        self.fps = 60.0
        self.timespacing = 1000.0 / self.fps
        self.timer.Start(self.timespacing, False)

        self.linespacing = 5

    def Update(self, event):
        # Any update tasks would go here (moving sprites, advancing animation frames etc.)
        self.Redraw()

    def Redraw(self):
        if self.size_dirty:
            self.screen = pygame.Surface(self.size, 0, 32)
            self.size_dirty = False

        self.screen.fill((0, 0, 0))

        cur = 0

        w, h = self.screen.get_size()
        while cur <= h:
            pygame.draw.aaline(self.screen, (255, 255, 255), (0, h - cur), (cur, 0))

            cur += self.linespacing

        s = pygame.image.tostring(self.screen, 'RGB')  # Convert the surface to an RGB string
        img = wx.ImageFromData(self.size[0], self.size[1], s)  # Load this string into a wx image
        bmp = wx.BitmapFromImage(img)  # Get the image in bitmap form
        dc = wx.ClientDC(self)  # Device context for drawing the bitmap
        dc.DrawBitmap(bmp, 0, 0, False)  # Blit the bitmap image to the display
        del dc

    def OnPaint(self, event):
        self.Redraw()
        event.Skip()  # Make sure the parent frame gets told to redraw as well

    def OnSize(self, event):
        self.size = self.GetSizeTuple()
        self.size_dirty = True

    def Kill(self, event):
        # Make sure Pygame can't be asked to redraw /before/ quitting by unbinding all methods which
        # call the Redraw() method
        # (Otherwise wx seems to call Draw between quitting Pygame and destroying the frame)
        # This may or may not be necessary now that Pygame is just drawing to surfaces
        self.Unbind(event=wx.EVT_PAINT, handler=self.OnPaint)
        self.Unbind(event=wx.EVT_TIMER, handler=self.Update, source=self.timer)


class FoolDisplay(PygameDisplay):
    def __init__(self, parent, id):
        PygameDisplay.__init__(self, parent, id)
        pygame.font.init()
        self.mainfont = pygame.font.Font(None, 40)
        self.text = self.mainfont.render("FOOOOOOL! NOW WE ARE ALL DAMNED!", True, (255, 0, 0))
        self.borw = True  # True = draw a black background, False = draw a white background
        self.points = []  # A list of points to draw

        self.Bind(wx.EVT_LEFT_DOWN, self.OnClick)

    def Update(self, event):
        PygameDisplay.Update(self, event)
        self.borw = not self.borw  # Alternate the background colour

        for i, point in enumerate(self.points):  # Slide all the points down and slightly to the right
            self.points[i] = (point[0] + 0.1, point[1] + 1)

    def Redraw(self):
        # If the size has changed, create a new surface to match it
        if self.size_dirty:
            self.screen = pygame.Surface(self.size, 0, 32)
            self.size_dirty = False

        # Draw the background
        if self.borw:
            self.screen.fill((0, 0, 0))
        else:
            self.screen.fill((255, 255, 255))

        self.screen.blit(self.text, (0, 0))

        # Draw circles at all the stored points
        for point in self.points:
            pygame.draw.circle(self.screen, (0, 255, 0), (int(point[0]), int(point[1])), 5)

        s = pygame.image.tostring(self.screen, 'RGB')  # Convert the surface to an RGB string
        img = wx.ImageFromData(self.size[0], self.size[1], s)  # Load this string into a wx image
        bmp = wx.BitmapFromImage(img)  # Get the image in bitmap form
        dc = wx.ClientDC(self)  # Device context for drawing the bitmap
        dc.DrawBitmap(bmp, 0, 0, False)  # Blit the bitmap image to the display
        del dc

    def OnClick(self, event):
        self.points.append(event.GetPositionTuple())  # Add a new point at the mouse position

class ConnectScreen(wx.Frame):
    def __init__(self, *args, **kwds):
        config_read(self)
        print self.Host
        print self.Port_Comm
        # begin wxGlade: ConnectScreen.__init__
        kwds["style"] = wx.CAPTION | wx.CLOSE_BOX
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
            wx.Bitmap("images/robot_icon_24x24.png", wx.BITMAP_TYPE_ANY))
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
        config_save(self)

    def OnButton_setup(event, button_label):
        wx.MessageBox("Not implemented yet!", "Button pressed.");

    def OnButton_cancel(event, button_label):
        #  wx.MessageBox("This is a message.", "Button pressed.");
        event.SaveConfig()
        event.Destroy()

    def OnButton_commit(event, button_label):
        # global Port_Video, Port_Audio, srv, Host, Port_Comm

        print "Button Label: " + str(button_label)
        print "Port Video: " + event.Port_Video.__str__()

        Host = event.ip_address.GetValue()
        Port_Comm = event.ip_port.GetValue()
        event.SaveConfig()

        event.srv = event.estabilish_connection(Host, Port_Comm)
        time.sleep(3)

        #        event.button_commit.SetLabel('Connecting...')
        gstreamer_cmd = "start /B " + event.Gstreamer_Path + "gst-launch-1.0 -v tcpclientsrc "
        if event.checkbox_local_test.GetValue():
            gstreamer_cmd += "host=127.0.0.1 port=12344"
            gstreamer_cmd += " ! gdpdepay ! videoconvert ! autovideosink sync = false"
        else:
            gstreamer_cmd += "host=" + Host + " port=" + event.Port_Video.__str__()
            gstreamer_cmd += " ! gdpdepay ! rtph264depay ! avdec_h264 ! videoconvert ! autovideosink sync=false"

        print gstreamer_cmd
        event.execute_cmd(gstreamer_cmd)

        # frame_CON = Console(None, wx.ID_ANY, "")
        # print "GetApp().TopWindow: " + str(wx.GetApp().TopWindow)
        # import sys
        event.hwnd = event.GetChildren()[0].GetHandle()
        # if sys.platform == "win32":
        #     os.environ['SDL_VIDEODRIVER'] = 'windib'
        # os.environ['SDL_WINDOWID'] = str(event.hwnd) #must be before init

        ## NOTE WE DON'T IMPORT PYGAME UNTIL NOW.  Don't put "import pygame" at the top of the file.
        # frame_CONSOLE = PygameDisplay(event, -1)

        frame_CONSOLE = Console(None, -1, "Console")
        frame_CONSOLE.Show()

        # execfile("rac_console.py")
        # event.Destroy()


    def estabilish_connection(self, Host, Port_Comm):
        # global srv
        server_address = (Host, Port_Comm)
        self.srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        print "Connecting..."
        self.srv.connect(server_address)
        print "Connected!"


# end of class ConnectScreen

class FoolFrame(wx.Frame):
    def __init__(self, parent):
        wx.Frame.__init__(self, parent, -1, size=(600, 300), style=wx.CAPTION | wx.SYSTEM_MENU | wx.CLOSE_BOX)

        self.display = FoolDisplay(self, -1)

        self.SetTitle("NOOOOOOOO!")


class Frame(wx.Frame):
    def __init__(self, parent):
        wx.Frame.__init__(self, parent, -1, size=(600, 600))

        self.display = PygameDisplay(self, -1)

        self.statusbar = self.CreateStatusBar()
        self.statusbar.SetFieldsCount(3)
        self.statusbar.SetStatusWidths([-3, -4, -2])
        self.statusbar.SetStatusText("wxPython", 0)
        self.statusbar.SetStatusText("Look, it's a nifty status bar!!!", 1)

        self.Bind(wx.EVT_SIZE, self.OnSize)
        self.Bind(wx.EVT_CLOSE, self.Kill)

        self.curframe = 0

        self.SetTitle("Pygame embedded in wxPython")

        self.slider = wx.Slider(self, wx.ID_ANY, 5, 1, 10, style=wx.SL_HORIZONTAL | wx.SL_LABELS)
        self.slider.SetTickFreq(0.1, 1)
        self.button = wx.Button(self, -1, "DO NOT PRESS THIS BUTTON")

        self.timer = wx.Timer(self)

        self.Bind(wx.EVT_SCROLL, self.OnScroll)
        self.Bind(wx.EVT_SIZE, self.OnSize)
        self.Bind(wx.EVT_TIMER, self.Update, self.timer)
        self.Bind(wx.EVT_BUTTON, self.ButtonClick, self.button)

        self.timer.Start((1000.0 / self.display.fps))

        self.sizer = wx.BoxSizer(wx.VERTICAL)
        self.sizer2 = wx.BoxSizer(wx.HORIZONTAL)

        self.sizer.Add(self.sizer2, 0, flag=wx.EXPAND)
        self.sizer.Add(self.display, 1, flag=wx.EXPAND)
        self.sizer2.Add(self.slider, 1, flag=wx.EXPAND | wx.RIGHT, border=5)
        self.sizer2.Add(self.button, 0, flag=wx.EXPAND | wx.ALL, border=5)

        self.SetAutoLayout(True)
        self.SetSizer(self.sizer)
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
        # (Commented code replaces the main display with the 'foooool!' display)
        # self.sizer.Detach(self.display)
        # self.display.Destroy()
        # self.display = FoolDisplay(self, -1)
        # self.sizer.Add(self.display, 1, flag = wx.EXPAND)
        # self.Layout()

        # newframe = FoolFrame(self)
        newframe = ConnectScreen(self)
        newframe.Show()

        self.button.SetLabel("YOU WERE WARNED!")
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
