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

SO_RETRY_LIMIT = 65

# Note omxh264enc element which is hardware h264 encoder.
# Software h264 encoder is called h264enc.
# Why I use x246 then?
H264_ENC = "x264enc"

Debug = 0

class SRV_vars:
    GUI_CONSOLE = False

from os import path
from sys import argv
class Paths:
    pathname = path.dirname(argv[0])
    GUI_file = pathname + "/gui_artifacts/MainConsole_extendedIII.glade"
