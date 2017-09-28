#!/usr/bin/env python3.5
# -*- coding: CP1252 -*-
import atexit
from ServerLib import ThreadManager

Thread_Manager = ThreadManager(None)
atexit.register(Thread_Manager.ProgramExit)

if not Thread_Manager.is_alive():
    Thread_Manager.start()

exit(0)
