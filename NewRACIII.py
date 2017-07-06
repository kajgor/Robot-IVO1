#!/usr/bin/env python
# -*- coding: CP1252 -*-

# import os
import pygame
import threading
# import sys
import time
from config_rw import *
from class_consoleIII import *
import gi
gi.require_version('Gst', '1.0')
gi.require_version('Gtk', '3.0')
gi.require_version('GstVideo', '1.0')
from gi.repository import GObject, Gtk, Gdk, GdkX11

from importlib import reload
# from os import system
# from thread import *
# import threading
# import pygame
# from pygame import display, draw, event, mouse, Surface

Rac_connection = RacConnection()
# Rac_Display = RacDisplay()
Rac_Uio = RacUio()

Debug = 3
GUI_file = "./gui_artifacts/MainConsole_extended.glade"
cfg_file = "./racII.cfg"


GObject.threads_init()


class GTK_Main:
    def __init__(self):
        # Read configuration
        config_read(self, cfg_file)
        # reset_save(cfg_file)

        builder = Gtk.Builder()
        builder.add_objects_from_file(GUI_file, ("MainWindow", "Adjustement_Port", "Adjustment_Resolution", "Action_StartTestServer"))
        print("GUI file added: ", GUI_file)

        self.window = builder.get_object("MainWindow")

        self.counter = builder.get_object("counter")

        self.movie_window = builder.get_object("DrawingArea_Cam")
        self.movie_window.set_size_request(640, 480)

        self.button_connect = builder.get_object("ToggleButton_Connect")

        self.statusbar = builder.get_object("StatusBar")
        self.context_id = self.statusbar.get_context_id("message")

        self.checkbutton_localtest = builder.get_object("CheckButton_LocalTest")
        self.checkbutton_cam = builder.get_object("CheckButton_Cam")

        self.combobox_host = builder.get_object("ComboBox_Host")
        self.comboboxtext_host = builder.get_object("ComboBoxTextEntry_Host")

        self.spinbutton_port = builder.get_object("SpinButton_Port")

        ##############################################
        self.drawingarea_control = builder.get_object("DrawingArea_Control")
        # self.drawingarea_control.set_flags(Gtk.CAN_DEFAULT | Gtk.CAN_FOCUS | Gtk.SENSITIVE | Gtk.PARENT_SENSITIVE)
        self.drawingarea_control.set_can_default(True)
        self.drawingarea_control.set_can_focus(True)
        self.drawingarea_control.set_sensitive(True)
        # self.drawingarea_control.set_parent_sensitive(True)
        self.drawingarea_control.set_app_paintable(True)
        self.drawingarea_control.set_size_request(150, 150)

        # # self.drawingarea_control.set_events(Gtk.BUTTON_PRESS_MASK)
        # self.drawingarea_control.connect("key-press-event", self.on_DrawingArea_Cam_key_press_event)

        self.window.add(self.drawingarea_control)
        self.drawingarea_control.realize()

        # We need to flush the XLib event loop otherwise we can't
        # access the XWindow which set_mode() requires
        Gdk.flush()
        pygame.init()
        pygame.display.set_mode((0, 200), 0, 0)
        self.screen = pygame.display.get_surface()

        #############################################
        # GObject.timeout_add(60, self.on_idle, None)
        # GObject.idle_add(self.on_idle)
        #############################################

        self.window.show_all()

        self.load_HostList(self.Host)
        builder.connect_signals(self)

        self.TEST_Host = "127.0.0.1"
        self.TEST_Port = 12344
        # self.Host_store = Gtk.ListStore(str)
        self.Host = ''

        if Debug > 1:
            print("Objects:")
            print(builder.get_objects().__str__())

        self.SXID = self.drawingarea_control.get_property('window')
        self.PXID = self.movie_window.get_property('window')

        bus = Rac_connection.player.get_bus()
        bus.add_signal_watch()
        bus.enable_sync_message_emission()
        bus.connect("message", self.on_message)
        bus.connect("sync-message::element", self.on_sync_message)

        self.background = RacDisplay(self.SXID, self.PXID, self.screen).background
        self.screen.blit(self.background, (0, 0))
        # pygame.display.flip()

    def on_MainWindow_notify(self, bus, message):
        return

    def on_message(self, bus, message):
        retmsg = RacDisplay(self.SXID, self.PXID, self.screen).on_message(message)
        if retmsg is not None:
            self.button_connect.set_active(False)
            self.statusbar.push(self.context_id, retmsg)

    def on_sync_message(self, bus, message):
        RacDisplay(self.SXID, self.PXID, self.screen).on_sync_message(message)

    def on_ComboBox_Host_changed(self, widget):
        model = self.combobox_host.get_model()
        Port = model[self.combobox_host.get_active()][1] + "."
        Port = Port[:Port.index('.')]
        self.spinbutton_port.set_value(int(Port))
        print("Changed:", self.combobox_host.get_active(), Port)

    def on_CheckButton_Cam_toggled(self,widget):
        if self.checkbutton_cam.get_active() == True:
            retmsg = Rac_connection.connect_camstream(True)
            if retmsg is True:
                retmsg = "VIDEO CONNECTION ESTABILISHED: OK"
            else:
                retmsg = "VIDEO CONNECTION ERROR: Unable to set the pipeline to the playing state."
        else:
            retmsg = Rac_connection.connect_camstream(False)
            if retmsg is True:
                retmsg = "VIDEO DISCONNECTED: OK"
            else:
                retmsg = "VIDEO NOT CONNECTED!"

        self.statusbar.push(self.context_id, retmsg)

    def on_CheckButton_LocalTest_toggled(self, widget):
        if self.checkbutton_localtest.get_active() == True:
            ret = self.HostList_get(self.TEST_Host)
            if self.HostList_get(self.TEST_Host) == False:
                ret = 0
                self.combobox_host.insert(ret, self.TEST_Port.__str__(), self.TEST_Host)

            self.combobox_host.set_active(ret)
            self.spinbutton_port.set_value(self.TEST_Port)
            self.combobox_host.set_sensitive(False)
            self.spinbutton_port.set_sensitive(False)
            try:
                print("try")
                import Test_Srv_GTK
            except:
                print("except")
                reload(Test_Srv_GTK)
        else:
            self.combobox_host.set_sensitive(True)
            self.spinbutton_port.set_sensitive(True)

    def on_ToggleButton_Connect_toggled(self, widget):
        if self.button_connect.get_active() == True:
            self.connect_gui()

            Host, Port_Comm = self.get_host_and_port()

            # Gstreamer setup start
            Rac_connection.source.set_property("host", Host)
            Rac_connection.source.set_property("port", Port_Comm)
            # Gstreamer setup end

            retmsg, success = Rac_connection.estabilish_connection(Host, Port_Comm)

            if success is True:
                self.update_server_list()
                if self.checkbutton_cam.get_active() is True:
                    retmsg = Rac_connection.connect_camstream(True)
                    if retmsg is True:
                        retmsg = "VIDEO CONNECTION ESTABILISHED: OK"
                    else:
                        retmsg = "VIDEO CONNECTION ERROR: Unable to set the pipeline to the playing state."

                self.drawingarea_control.grab_focus()
            else:
                self.disconnect_gui()

            self.statusbar.push(self.context_id, retmsg)
        else:
            Rac_connection.close_connection()
            self.disconnect_gui()

    def get_host_and_port(self):
        if self.checkbutton_localtest.get_active() == True:
            Host = self.TEST_Host
            Port_Comm = self.TEST_Port.__int__()
        else:
            Host = self.combobox_host.get_active_text()
            Port_Comm = self.spinbutton_port.get_value().__int__()

        return Host, Port_Comm

    def connect_gui(self):
        self.combobox_host.set_sensitive(False)
        self.checkbutton_localtest.set_sensitive(False)
        self.spinbutton_port.set_sensitive(False)

    def disconnect_gui(self):
        self.statusbar.push(self.context_id, "Disconnected.")

        self.button_connect.set_active(False)
        self.checkbutton_localtest.set_sensitive(True)

        if self.checkbutton_localtest.get_active() is False:
            self.combobox_host.set_sensitive(True)
            self.spinbutton_port.set_sensitive(True)

    def update_server_list(self):
        list_iter = self.combobox_host.get_active_iter()
        if list_iter is not None:
            model = self.combobox_host.get_model()
            Host, Port = model[list_iter][:2]
            try:
                Port = Port[:Port.index('.')]
            except:
                None
            print("Selected: Port=%s, Host=%s" % (int(Port), Host))
        else:
            entry = self.combobox_host.get_child()
            self.combobox_host.insert(0, self.spinbutton_port.get_value().__str__(), entry.get_text())
            self.combobox_host.set_active(0)

            print("New entry: %s" % entry.get_text())
            print("New port: %s" % self.spinbutton_port.get_value().__str__())

    def on_CheckButton_Speakers_toggled(self, widget):
        return

    def on_CheckButton_Display_toggled(self, widget):
        return

    def on_CheckButton_Lights_toggled(self, widget):
        return

    def on_Button_Preferences_clicked(self, widget):
        print("TEXT IN COMBOBOX: ", self.combobox_host.get_active_text())
        print("NO OF ITEMS:", self.combobox_host.get_model().iter_n_children())
        self.config_snapshot()

    def HostList_get(self, HostToFind):
        HostList_str = []
        model = self.combobox_host.get_model()
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

    def config_snapshot(self):
        self.Host = self.HostList_get(None)
# ToDo:
        self.Port_Comm = "5000"
        self.Port_Video = "5001"
        self.Port_Audio = "5002"
        self.Gstreamer_Path = "/usr/bin"

    def load_HostList(self, HostList_str):
        x = 0
        for HostName in HostList_str:
            Host = HostName.split(":")[0]
            Port = HostName.split(":")[1]
            self.combobox_host.insert(x, Port, Host)
            x += 1
            # print("HostName %s > Port/Host:" % HostName, Port, Host)

    def on_DrawingArea_Cam_button_press_event(self, mouse_event):
        if mouse_event.LeftIsDown():
            self.mouse = Rac_Uio.get_mouseInput(mouse_event)

    def on_DrawingArea_Cam_key_press_event(self, Area , event):
        print("event:", event)
        for iter_x in range(0, event.iter_n()):
            print("iter_x:", iter_x)

    def on_Grid_Control_focus(self, widget, data=None):
        # if ev.keyval == Gdk.KEY_Escape: #If Escape pressed, reset text
        print("focus", widget)
        # print("key.keyval", key.keyval)
        self.speed, self.direction = Rac_Uio.get_keyInput(widget, self.speed, self.direction)

    def gtk_main_quit(self, dialog):
        Rac_connection.close_connection()
        self.config_snapshot()
        # config_save(self, cfg_file)
        Gtk.main_quit ()


class UI(threading.Thread):
    Motor_PWR = Motor_RPM = Motor_ACK = Motor_Power = mouse = [0, 0]
    Current = Voltage = speed = direction = 0

    def __init__(self, GUI):
        super(UI, self).__init__()
        self.label = GUI.counter
        self.quit = False

    def update_label(self, counter):
        self.label.set_text("Frame %i" % counter)
        return False

    def run(self):
        print("***", self)
        counter = 0
        while not self.quit:
            counter += 1
            GObject.idle_add(self.update_label, counter)
            time.sleep(0.01)

            # try:
            #     GTK_Main().screen.blit(GTK_Main().background, (0, 0))
            # except:
            #     None

            # return
            # Any update tasks would go here (moving sprites, advancing animation frames etc.)
            if Rac_connection.conoff:
                if Rac_connection.check_connection(""):
                    if self.speed != "HALT":
                        self.Motor_Power = [0, 0]
                        self.Motor_Power[RIGHT] = self.speed - self.direction
                        self.Motor_Power[LEFT] = self.speed + self.direction

                        request = Rac_Uio.encode_transmission(self.Motor_Power, self.mouse, "")
                        resp = Rac_connection.transmit(request)

                        if resp is not None:
                            self.Motor_PWR, self.Motor_RPM, self.Motor_ACK, self.Current, self.Voltage\
                                = Rac_Uio.decode_transmission(resp)
                    else:
                        halt_cmd = self.direction
                        Rac_connection.transmit(halt_cmd)
                        Rac_connection.srv.close()
                        Rac_connection.connected = False
                        # sys.exit(0)  # quit the program

                self.Redraw()

    def Redraw(self):
        # pygame.font.init()
        # pygame.display.init()
        # if self.draw_init:
        #     self.draw_init = False
        #     # Rac_Display = RacDisplay(self.display)
        #     self.screen = pygame.Surface(self.size, 0, 32)
        #     # self.hwnd = self.GetHandle()
        #     # print self.hwnd
        #     os.environ['SDL_WINDOWID'] == self.hwnd.__str__()
        #
        #     pygame.display.set_caption("Robot IVO-1 console", "IVO-1")
        #     self.screen = pygame.display.set_mode((480, 360), pygame.DOUBLEBUF)
        #
        #     pygame.init()
        #     pygame.display.flip()

        # self.screen.fill((0, 0, 0))

        Rac_display = RacDisplay(self.drawingarea_control)
        Rac_display.plot_screen(self.Motor_Power, self.speed, self.direction)

        # s = pygame.image.tostring(self.drawingarea_control, 'RGB')  # Convert the surface to an RGB string
        # img = wx.Image(self.size[0], self.size[1], s)  # Load this string into a wx image
        # bmp = wx.Bitmap(img)  # Get the image in bitmap form
        # dc = wx.ClientDC(self)  # Device context for drawing the bitmap

        # dc.DrawBitmap(bmp, 0, 0, False)  # Blit the bitmap image to the display
        # del dc

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
        # self.Unbind(event=wx.EVT_PAINT, handler=self.OnPaint)
        # self.Unbind(event=wx.EVT_TIMER, handler=self.Update, source=self.timer)
        return

gui = GTK_Main()
control = UI(gui)
control.start()

Gtk.main()
control.quit = True
