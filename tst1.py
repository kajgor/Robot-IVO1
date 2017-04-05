import wx


class MainWindow(wx.Frame):
    def __init__(self, parent, title):
        wx.Frame.__init__(self, parent, -1, title, (500, 200), (650, 500),
            wx.DEFAULT_FRAME_STYLE | wx.NO_FULL_REPAINT_ON_RESIZE)

        panel = wx.Panel(self)
        button = wx.Button(panel, wx.ID_OPEN)

        panel.sizer = wx.BoxSizer(wx.VERTICAL)
        panel.sizer.Add(button, 0, wx.ALL, 7)
        panel.SetSizer(panel.sizer)

        button.Bind(wx.EVT_BUTTON, self.on_button)
        self.Bind(wx.EVT_CLOSE, self.on_close)

        self.rec_window = None

    def on_button(self, event):
        rec_window = RecWindow(self, 'Rec window')
        rec_window.Show()
        self.Hide()
        rec_window.Bind(wx.EVT_CLOSE, self.on_close)
        self.rec_window = rec_window

    def on_close(self, event):
        closed_window = event.EventObject
        if closed_window == self.rec_window:
            self.rec_window = None
            self.Show()
        elif closed_window == self:
            print 'Carry out your code for when Main window closes'
        event.Skip()


class RecWindow(wx.Frame):
    def __init__(self, parent, title):
        wx.Frame.__init__(self, parent, -1, title, (400, 200), (700, 600),
            wx.DEFAULT_FRAME_STYLE | wx.NO_FULL_REPAINT_ON_RESIZE)


app = wx.App(False)
main_window = MainWindow(None, 'Main window')
main_window.Show()
app.MainLoop()