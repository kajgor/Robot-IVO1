# !/usr/bin/env python

import ServerLib

ServerLib.init_Gstreamer()

ServerLib.ClientThread.on_btn = True
if ServerLib.ClientThread.srv is None:
    Conn_thread = ServerLib.ThreadRestart()
    Conn_thread.start()

exit(0)
