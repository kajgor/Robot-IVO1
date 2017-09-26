#!/usr/bin/env python3.5
# -*- coding: CP1252 -*-
import atexit
from ServerLib import ThreadRestart, ClientThread

Thread_Restart = ThreadRestart()
atexit.register(Thread_Restart.ProgramExit)

ClientThread.on_btn = True
if ClientThread.srv is None:
    Thread_Restart.start()

exit(0)
