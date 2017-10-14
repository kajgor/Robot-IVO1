capsstr = [None, None, None, None, None, None]
capsstr[1] = ", width=320, height=240, framerate=25/1"
capsstr[2] = ", width=640, height=480, framerate=30/1"
capsstr[3] = ", width=800, height=600, framerate=30/1"
capsstr[4] = ", width=1280, height=800, framerate=25/1"
capsstr[5] = ", width=1920, height=1080, framerate=25/1"

VERSION = "B3.0"
HOST = ''   # Symbolic name meaning all available interfaces
VERTICAL = 0
HORIZONTAL = 1
Port_COMM = 4550
Port_CAM0 = Port_COMM + 1
Port_MIC0 = Port_COMM + 2
Port_DSP0 = Port_COMM + 4
Port_SPK0 = Port_COMM + 5
SO_RETRY_LIMIT = 65

Debug = 0

class SRV_vars:
    GUI_CONSOLE = False

from os import path
from sys import argv
class Paths:
    pathname = path.dirname(argv[0])
    GUI_file = pathname + "/gui_artifacts/MainConsole_extendedIII.glade"
