#!/usr/bin/env python
# -*- coding: UTF-8 -*-
#
# generated by wxGlade 0.7.1 on Mon Mar 27 12:09:40 2017
#

import wx

# begin wxGlade: dependencies
import gettext
# end wxGlade

# begin wxGlade: extracode
# end wxGlade


class RacMainFrame(wx.Frame):
    def __init__(self, *args, **kwds):
        # begin wxGlade: RacMainFrame.__init__
        wx.Frame.__init__(self, *args, **kwds)
        self.MainFrame_statusbar = self.CreateStatusBar(1)
        self.button_Options = wx.Button(self, wx.ID_ANY, _("&Options"))
        self.label_IpPort = wx.StaticText(self, wx.ID_ANY, _("Server IP/Port"))
        self.combo_box_HostIp = wx.ComboBox(self, wx.ID_ANY, choices=[_("localhost"), _("athome21.hopto.org")], style=wx.CB_DROPDOWN)
        self.spin_ctrl_HostPort = wx.SpinCtrl(self, wx.ID_ANY, "5000", min=100, max=19999)
        self.button_Connect = wx.ToggleButton(self, wx.ID_ANY, _("&CONNECT"))
        self.panel_1 = wx.Panel(self, wx.ID_ANY)
        self.checkbox_local_test = wx.CheckBox(self, wx.ID_ANY, _("Local Test"))
        self.label_Resolution_Auto = wx.StaticText(self, wx.ID_ANY, _("Resolution              Auto"))
        self.slider_1 = wx.Slider(self, wx.ID_ANY, 2, 0, 3)
        self.checkbox_1 = wx.CheckBox(self, wx.ID_ANY, "")
        self.checkbox_Light = wx.CheckBox(self, wx.ID_ANY, _("Lights"))
        self.checkbox_Display = wx.CheckBox(self, wx.ID_ANY, _("Display"))
        self.checkbox_Speakers = wx.CheckBox(self, wx.ID_ANY, _("Speakers"))
        self.label_Voltage = wx.StaticText(self, wx.ID_ANY, _("Voltage"))
        self.gauge_Voltage = wx.Gauge(self, wx.ID_ANY, 10)
        self.label_Current = wx.StaticText(self, wx.ID_ANY, _("Current"))
        self.gauge_Current = wx.Gauge(self, wx.ID_ANY, 10)
        self.gauge_PwrL = wx.Gauge(self, wx.ID_ANY, 10, style=wx.GA_VERTICAL)
        self.label_Power = wx.StaticText(self, wx.ID_ANY, _("Power"))
        self.gauge_PwrR = wx.Gauge(self, wx.ID_ANY, 10, style=wx.GA_VERTICAL)
        self.bitmap_button_OnTop = wx.BitmapButton(self, wx.ID_ANY, wx.Bitmap("/media/sf_PycharmProjects/Robot-IVO/icons/robot_icon_64x64.png", wx.BITMAP_TYPE_ANY))

        self.__set_properties()
        self.__do_layout()
        # end wxGlade

    def __set_properties(self):
        # begin wxGlade: RacMainFrame.__set_properties
        self.SetTitle(_("Remote Access Console"))
        self.SetSize((720, 410))
        self.SetFocus()
        self.MainFrame_statusbar.SetStatusWidths([-1])

        # statusbar fields
        MainFrame_statusbar_fields = [_("MainFrame_statusbar")]
        for i in range(len(MainFrame_statusbar_fields)):
            self.MainFrame_statusbar.SetStatusText(MainFrame_statusbar_fields[i], i)
        self.button_Options.SetMinSize((85, 27))
        self.button_Options.SetBackgroundColour(wx.Colour(143, 143, 188))
        self.label_IpPort.SetMinSize((95, 22))
        self.combo_box_HostIp.SetMinSize((225, 27))
        self.combo_box_HostIp.SetSelection(0)
        self.spin_ctrl_HostPort.SetMinSize((70, 27))
        self.button_Connect.SetMinSize((120, 27))
        self.panel_1.SetMinSize((490,310))
        self.panel_1.SetBackgroundColour(wx.Colour(27, 109, 82))
        self.checkbox_local_test.SetToolTip(wx.ToolTip(_("Please ensure that Test Server is running")))
        self.slider_1.SetMinSize((120, 19))
        self.checkbox_1.SetMinSize((21, 21))
        self.gauge_Voltage.SetMinSize((100, 15))
        self.gauge_Current.SetMinSize((100, 15))
        self.gauge_PwrL.SetMinSize((15, 75))
        self.label_Power.SetMinSize((44, 86))
        self.gauge_PwrR.SetMinSize((15, 75))
        self.bitmap_button_OnTop.SetSize(self.bitmap_button_OnTop.GetBestSize())
        # end wxGlade

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
        sizer_3.Add(self.panel_1, 1, wx.ALIGN_CENTER | wx.ALL, 5)
        sizer_4.Add(self.checkbox_local_test, 0, wx.ALIGN_CENTER | wx.BOTTOM, 3)
        sizer_4.Add(self.label_Resolution_Auto, 0, wx.ALIGN_CENTER | wx.TOP, 10)
        sizer_9.Add(self.slider_1, 0, wx.BOTTOM | wx.EXPAND | wx.LEFT | wx.RIGHT, 5)
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

# end of class RacMainFrame
