#!/usr/bin/env python3.5
# -*- coding: CP1252 -*-
from ServerLib import ThreadRestart, ClientThread, init_Gstreamer

init_Gstreamer()

ClientThread.on_btn = True
if ClientThread.srv is None:
    Conn_thread = ThreadRestart()
    Conn_thread.start()

exit(0)
