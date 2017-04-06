#!/usr/bin/env python
# -*- coding: CP1252 -*-

# import pygame
import sys, time, os
# from os import system
# from thread import *
# import threading
from init_variables import *
from config_rw import *
from class_console import *
# from pygame import display, draw, event, mouse, Surface

Rac_connection = RacConnection()
Rac_Uio = RacUio()

class PygameDisplay(wx.Window):
    def __init__(self, parent, ID):
        wx.Window.__init__(self, parent, ID)
        self.parent = parent
        self.hwnd = self.GetHandle()

        self.size = self.GetSize()
        self.draw_init = True

        self.timer = wx.Timer(self)
        self.Bind(wx.EVT_PAINT, self.OnPaint)
        self.Bind(wx.EVT_TIMER, self.Update, self.timer)
        self.Bind(wx.EVT_SIZE, self.OnSize)
        self.Bind(wx.EVT_KEY_DOWN, self.OnKeyDown)
        self.Bind(wx.EVT_MOTION, self.OnMouseMotion)
        # self.Bind(wx.EVT_IDLE, self.OnIdle)
        # wx.EVT_IDLE(self, self.OnIdle)
        # self.Bind(wx.EVT_LEFT_DOWN, self.OnMouseLdown)

        self.fps = 60.0
        self.timespacing = 1000.0 / self.fps
        self.timer.Start(self.timespacing, False)

        self.linespacing = 5

        self.initialized = False

    def OnMouseMotion(self, mouse_event):
        if mouse_event.LeftIsDown():
            App.mouse = Rac_Uio.get_mouseInput(mouse_event)

    def OnKeyDown(self, key):
        App.speed, App.direction = Rac_Uio.get_keyInput(key, App.speed, App.direction)

    # def OnIdle(self, event):
    #     if not self.initialized:
    #         self.initialized = True

    def Update(self, event):
        # Any update tasks would go here (moving sprites, advancing animation frames etc.)
        if Rac_connection.conoff:
            if Rac_connection.check_connection("127.0.0.1"):
                if App.speed != "HALT":
                    App.Motor_Power = [0, 0]
                    App.Motor_Power[RIGHT] = App.speed - App.direction
                    App.Motor_Power[LEFT] = App.speed + App.direction
                    # print("Motor Powwer sent: " + App.Motor_Power.__str__())
                    request = Rac_Uio.encode_transmission(App.Motor_Power, App.mouse, "")
                    resp = Rac_connection.transmit(request)
                    # print("RESP>>> " + resp.__str__())
                    if resp is not None:
                        App.Motor_PWR, App.Motor_RPM, App.Motor_ACK, App.Current, App.Voltage\
                            = Rac_Uio.decode_transmission(resp)
                else:
                    halt_cmd = App.direction
                    Rac_connection.transmit(halt_cmd)
                    print("Closing connection...")
                    Rac_connection.srv.close()
                    print("Connection closed.")
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
            # self.hwnd = self.GetHandle()
            # print self.hwnd
            os.environ['SDL_WINDOWID'] == self.hwnd.__str__()

            pygame.display.set_caption("Robot IVO-1 console", "IVO-1")
            self.screen = pygame.display.set_mode((480, 360), pygame.DOUBLEBUF)

            pygame.init()
            pygame.display.flip()

        # self.screen.fill((0, 0, 0))

        Rac_display = RacDisplay(self.screen)
        Rac_display.plot_screen(App.Motor_Power, App.speed, App.direction, App.Motor_PWR, App.Motor_RPM, App.Motor_ACK,
                                App.mouse, App.Voltage, App.Current, Motor_DBG = [0, 0])

        s = pygame.image.tostring(self.screen, 'RGB')  # Convert the surface to an RGB string
        img = wx.Image(self.size[0], self.size[1], s)  # Load this string into a wx image
        bmp = wx.Bitmap(img)  # Get the image in bitmap form
        dc = wx.ClientDC(self)  # Device context for drawing the bitmap
        dc.DrawBitmap(bmp, 0, 0, False)  # Blit the bitmap image to the display
        del dc

    def OnPaint(self, event):
        # self.Redraw()
        event.Skip()  # Make sure the parent frame gets told to redraw as well


    def OnSize(self, event):
        self.size = self.GetSize()
        self.draw_init = True


    def Kill(self, event):
        # Make sure Pygame can't be asked to redraw /before/ quitting by unbinding all methods which
        # call the Redraw() method
        # (Otherwise wx seems to call Draw between quitting Pygame and destroying the frame)
        # This may or may not be necessary now that Pygame is just drawing to surfaces
        self.Unbind(event=wx.EVT_PAINT, handler=self.OnPaint)
        self.Unbind(event=wx.EVT_TIMER, handler=self.Update, source=self.timer)


class OptionsScreen(wx.Frame):
    def __init__(self, *args, **kwds):
        config_read(self, "rac.cfg")

        self.Destroy()

    def dummy(self):
        return
# end of class OptionsScreen


class Frame(wx.Frame):
    # def __init__(self, *args, **kwds):
    #     # begin wxGlade: RacMainFrame.__init__
    #     wx.Frame.__init__(self, *args, **kwds)
    def __init__(self, parent):
# Todo:
        wx.Frame.__init__(self, parent, -1, size=(720, 410))
        # wx.Frame.__init__(self, parent, -1)

        config_read(self, "rac.cfg")
        print(self.Host + "< Host")
        print(self.Port_Comm.__str__() + "< Comm")
        # self.MainFrame_statusbar = self.CreateStatusBar(1)
        self.statusbar = self.CreateStatusBar()
        self.button_Options = wx.Button(self, wx.ID_ANY, "&Options")
        self.label_IpPort = wx.StaticText(self, wx.ID_ANY, "Server IP/Port")
        self.combo_box_HostIp = wx.ComboBox(self, wx.ID_ANY, str(self.Host),
                                      choices=["localhost", "athome21.hopto.org"], style=wx.CB_DROPDOWN)
        self.spin_ctrl_HostPort = wx.SpinCtrl(self, wx.ID_ANY, self.Port_Comm.__str__(), min=100, max=19999)
        self.button_Connect = wx.ToggleButton(self, wx.ID_ANY, "&CONNECT")

        self.display = PygameDisplay(self, -1)

        self.checkbox_local_test = wx.CheckBox(self, wx.ID_ANY, "Local Test")
        self.label_Resolution_Auto = wx.StaticText(self, wx.ID_ANY, "Resolution              Auto")
        self.slider_Res = wx.Slider(self, wx.ID_ANY, 2, 0, 3)
        self.checkbox_1 = wx.CheckBox(self, wx.ID_ANY, "")
        self.checkbox_Light = wx.CheckBox(self, wx.ID_ANY, "Lights")
        self.checkbox_Display = wx.CheckBox(self, wx.ID_ANY, "Display")
        self.checkbox_Speakers = wx.CheckBox(self, wx.ID_ANY, "Speakers")
        self.label_Voltage = wx.StaticText(self, wx.ID_ANY, "Voltage")
        self.gauge_Voltage = wx.Gauge(self, wx.ID_ANY, 10)
        self.label_Current = wx.StaticText(self, wx.ID_ANY, "Current")
        self.gauge_Current = wx.Gauge(self, wx.ID_ANY, 10)
        self.gauge_PwrL = wx.Gauge(self, wx.ID_ANY, 10, style=wx.GA_VERTICAL)
        self.label_Power = wx.StaticText(self, wx.ID_ANY, "Power")
        self.gauge_PwrR = wx.Gauge(self, wx.ID_ANY, 10, style=wx.GA_VERTICAL)
        self.bitmap_button_OnTop = wx.BitmapButton(self, wx.ID_ANY, wx.Bitmap("./icons/robot_icon_64x64.png", wx.BITMAP_TYPE_ANY))

        self.curframe = 0

        self.__set_properties()
        self.__do_layout()
        self.hwnd = self.GetHandle()
        self.display.SetFocus()
        # end wxGlade

    def __set_properties(self):
        # begin wxGlade: RacMainFrame.__set_properties
        self.SetTitle("Remote Access Console - IVO")
        self.SetSize((720, 410))
        # _icon = wx.NullIcon
        # _icon.CopyFromBitmap(
        #     wx.Bitmap("icons/robot_icon_24x24.png", wx.BITMAP_TYPE_ANY))
        # self.SetIcon(_icon)
        # self.SetFocus()

        # statusbar fields
        # MainFrame_statusbar_fields = ["MainFrame_statusbar"]
        # for i in range(len(MainFrame_statusbar_fields)):
        #     self.MainFrame_statusbar.SetStatusText(MainFrame_statusbar_fields[i], i)
        self.statusbar.SetFieldsCount(3)
        self.statusbar.SetStatusWidths([-3, -4, -2])
        self.statusbar.SetStatusText("RAC Console", 0)
        self.statusbar.SetStatusText("High Transfer Rate", 1)

        self.button_Options.SetMinSize((85, 27))
        self.button_Options.SetBackgroundColour(wx.Colour(143, 143, 188))
        self.label_IpPort.SetMinSize((95, 22))
        self.combo_box_HostIp.SetMinSize((225, 27))
        self.combo_box_HostIp.SetSelection(0)
        self.spin_ctrl_HostPort.SetMinSize((70, 27))
        self.button_Connect.SetMinSize((120, 27))
        self.display.SetMinSize((490, 310))
        self.display.SetBackgroundColour(wx.Colour(27, 109, 82))
        self.checkbox_local_test.SetValue(self.Local_Test)
        self.checkbox_local_test.SetToolTip(wx.ToolTip("Please ensure that Test Server is running"))
        self.slider_Res.SetMinSize((120, 19))
        self.checkbox_1.SetMinSize((21, 21))
        self.gauge_Voltage.SetMinSize((100, 15))
        self.gauge_Current.SetMinSize((100, 15))
        self.gauge_PwrL.SetMinSize((15, 75))
        self.label_Power.SetMinSize((44, 86))
        self.gauge_PwrR.SetMinSize((15, 75))
        self.bitmap_button_OnTop.SetSize(self.bitmap_button_OnTop.GetBestSize())
        # end wxGlade

        self.timer = wx.Timer(self)
        self.timer.Start((1000.0 / self.display.fps))

        self.Bind(wx.EVT_SIZE, self.OnSize)
        self.Bind(wx.EVT_CLOSE, self.Kill)
        self.Bind(wx.EVT_SCROLL, self.OnScroll)
        self.Bind(wx.EVT_SIZE, self.OnSize)
        self.Bind(wx.EVT_TIMER, self.Update, self.timer)
        self.Bind(wx.EVT_TOGGLEBUTTON, self.ButtonClick, self.button_Connect)
        self.Bind(wx.EVT_KEY_DOWN, self.OnButton_setup, self.button_Options)
        # self.Bind(wx.EVT_IDLE, self.OnIdle)

    def __do_layout(self):
        # begin wxGlade: RacMainFrame.__do_layout
        sizer_1 = wx.BoxSizer(wx.VERTICAL)
        sizer_3 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_4 = wx.BoxSizer(wx.VERTICAL)
        sizer_5 = wx.BoxSizer(wx.VERTICAL)
        sizer_6 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_8 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_7 = wx.BoxSizer(wx.VERTICAL)
        sizer_9 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_2 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_2.Add(self.button_Options, 0, wx.ALIGN_CENTER_HORIZONTAL | wx.LEFT | wx.RIGHT, 10)
        sizer_2.Add(self.label_IpPort, 0, wx.ALIGN_BOTTOM | wx.LEFT, 75)
        sizer_2.Add(self.combo_box_HostIp, 0, wx.LEFT, 5)
        sizer_2.Add(self.spin_ctrl_HostPort, 0, wx.LEFT, 2)
        sizer_2.Add(self.button_Connect, 0, wx.LEFT, 10)
        sizer_1.Add(sizer_2, 0, wx.TOP, 5)
        sizer_3.Add(self.display, 1, wx.ALIGN_CENTER | wx.ALL, 5)
        sizer_4.Add(self.checkbox_local_test, 0, wx.ALIGN_CENTER | wx.BOTTOM, 3)
        sizer_4.Add(self.label_Resolution_Auto, 0, wx.ALIGN_CENTER | wx.TOP, 10)
        sizer_9.Add(self.slider_Res, 0, wx.BOTTOM | wx.EXPAND | wx.LEFT | wx.RIGHT, 5)
        sizer_9.Add(self.checkbox_1, 0, wx.LEFT, 25)
        sizer_4.Add(sizer_9, 0, 0, 0)
        sizer_4.Add(self.checkbox_Light, 0, wx.BOTTOM, 3)
        sizer_4.Add(self.checkbox_Display, 0, wx.BOTTOM, 3)
        sizer_4.Add(self.checkbox_Speakers, 0, wx.BOTTOM, 3)
        sizer_7.Add(self.label_Voltage, 0, wx.ALIGN_CENTER_HORIZONTAL | wx.TOP, 10)
        sizer_7.Add(self.gauge_Voltage, 0, wx.ALIGN_CENTER | wx.EXPAND | wx.RIGHT | wx.TOP, 5)
        sizer_7.Add(self.label_Current, 0, wx.ALIGN_CENTER_HORIZONTAL | wx.TOP, 5)
        sizer_7.Add(self.gauge_Current, 0, wx.ALIGN_CENTER | wx.EXPAND | wx.RIGHT | wx.TOP, 5)
        sizer_6.Add(sizer_7, 1, 0, 0)
        sizer_8.Add(self.gauge_PwrL, 0, wx.ALIGN_BOTTOM | wx.LEFT, 20)
        sizer_8.Add(self.label_Power, 0, 0, 0)
        sizer_8.Add(self.gauge_PwrR, 0, wx.ALIGN_BOTTOM, 0)
        sizer_6.Add(sizer_8, 1, 0, 0)
        sizer_5.Add(sizer_6, 1, 0, 0)
        sizer_4.Add(sizer_5, 1, 0, 0)
        sizer_4.Add(self.bitmap_button_OnTop, 0, wx.BOTTOM | wx.EXPAND | wx.RIGHT | wx.TOP, 5)
        sizer_3.Add(sizer_4, 1, wx.TOP, 10)
        sizer_1.Add(sizer_3, 0, 0, 0)
        self.SetSizer(sizer_1)
        self.Layout()
        self.Centre()
        # end wxGlade

    def OnKeyDown(self, key):
        speed, direction = Rac_Uio.get_keyInput(key, PygameDisplay.speed, PygameDisplay.direction)
        PygameDisplay.speed = speed
        PygameDisplay.direction = direction
        self.Layout()

    def Kill(self, event):
        self.SaveConfig()
        self.display.Kill(event)
        self.Destroy()

    def OnSize(self, event):
        self.Layout()

    def Update(self, event):
        self.curframe += 1
        self.statusbar.SetStatusText("Frame %i" % self.curframe, 2)

    def OnScroll(self, event):
        self.display.linespacing = self.slider_Res.GetValue()

    def OnButton_setup(self, button_label):
        wx.MessageBox("Not implemented yet!", "Button pressed.");

    # def OnIdle(self, event):
        # self.display.SetFocus()

    # def OnButton_cancel(event, button_label):
    #     #  wx.MessageBox("This is a message.", "Button pressed.");
    #     event.SaveConfig()
    #     event.Destroy()

    def config_snapshot(self):
        self.Host = self.combo_box_HostIp.GetValue()
        self.Port_Comm = self.spin_ctrl_HostPort.GetValue()
        self.Local_Test = self.checkbox_local_test.GetValue()
# Todo:
        self.Gstreamer_Path = "/usr/bin/"

    def ButtonClick(self, event):
        print ("event: " + str(event))
        gstreamer_cmd = self.Gstreamer_Path + "gst-launch-1.0 tcpclientsrc "
        if self.Local_Test:
            gstreamer_cmd += "host=127.0.0.1 port=12344"
            gstreamer_cmd += " ! gdpdepay ! videoconvert ! ximagesink sync=false"
        else:
            gstreamer_cmd += "host=" + self.Host + " port=" + self.Port_Video.__str__()
            gstreamer_cmd += " ! gdpdepay ! rtph264depay ! avdec_h264 ! videoconvert ! ximagesink sync=false"
            # gstreamer_cmd += " ! gdpdepay ! rtph264depay ! avdec_h264 ! videoconvert ! autovideosink sync=false"

        self.SaveConfig()
        # Rac_connection.conoff = self.button_Connect.GetValue()
        print ("Rac_connection.check_connection(self.Host): " + Rac_connection.check_connection(self.Host).__str__())

        Rac_connection.conoff = self.button_Connect.GetValue()

        if Rac_connection.check_connection(self.Host) is False and Rac_connection.conoff:
            retmsg = Rac_connection.estabilish_connection(self.Host, self.Port_Comm)
            # retmsg = start_new_thread(Rac_connection.estabilish_connection,(self.Host, self.Port_Comm))
            # print("retmsg = " + retmsg.__str__())
            # if retmsg.__str__().isdigit():
            if not retmsg:
                time.sleep(3)
                #        event.button_commit.SetLabel('Connecting...')
                # Client
                # gst-launch-1.0 videotestsrc pattern=smpte ! video/x-raw,width=320,height=240 ! glimagesink (default)
                # /gtksink/cacasink/autovideosink sync=false
                #
                #

                # retmsg = start_new_thread(Rac_Uio.execute_cmd,(gstreamer_cmd + ' &',))
                retmsg = Rac_Uio.execute_cmd(gstreamer_cmd + ' &')
                print(gstreamer_cmd + " [" + retmsg.__str__() + "]")

                self.Layout()
                self.button_Connect.SetLabel("DISCONNECT")
                self.button_Connect.SetValue(True)
                self.checkbox_local_test.Enable(False)
                self.combo_box_HostIp.Enable(False)
                self.spin_ctrl_HostPort.Enable(False)
                self.Layout()

                # start_new_thread(PygameDisplay,(self, -1)).Show()
                PygameDisplay(self, self.hwnd).Show()

            else:
                print("Connection error: " + retmsg.__str__())
                self.button_Connect.SetLabel("RECONNECT")
                self.button_Connect.SetValue(False)
                self.checkbox_local_test.Enable(True)
                self.combo_box_HostIp.Enable(True)
                self.spin_ctrl_HostPort.Enable(True)
                self.Layout()

        else:
            self.button_Connect.SetLabel("CONNECT")
            self.button_Connect.SetValue(False)
            self.checkbox_local_test.Enable(True)
            self.combo_box_HostIp.Enable(True)
            self.spin_ctrl_HostPort.Enable(True)
            Rac_connection.close_connection(gstreamer_cmd)
            # print "exiting thread"
            # exit_thread()

        Rac_connection.conoff = self.button_Connect.GetValue()
        self.Layout()

    def SaveConfig(self):
        self.config_snapshot()
        config_save(self, "rac.cfg")


class App(wx.App):
    Motor_PWR = Motor_RPM = Motor_ACK = Motor_Power = mouse = [0, 0]
    Current = Voltage = speed = direction = 0

    def OnInit(self):
        self.frame = Frame(parent=None)
        self.frame.Show()
        self.SetTopWindow(self.frame)

        return True


if __name__ == "__main__":
    Console = App()
    Console.MainLoop()

#######################################################################################################################