#!/usr/bin/env python3.5
# -*- coding: CP1252 -*-
from time import sleep
from ServerLib import ThreadManager

Thread_Manager = ThreadManager(False)
Thread_Manager.shutdown_flag = False

Thread_Manager.run()

while Thread_Manager.shutdown_flag is not True:
    sleep(.1)

Thread_Manager.shutdown_flag = True
while Thread_Manager.shutdown_flag is True:
    sleep(.1)

exit(0)
