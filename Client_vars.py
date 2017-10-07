CONSOLE_GUI = True
RESP_DELAY = 0.025

Port_COMM = 4550
Port_CAM0 = Port_COMM + 1
Port_MIC0 = Port_COMM + 2
Port_DSP0 = Port_COMM + 4
Port_SPK0 = Port_COMM + 5

Debug = 1

CommunicationFFb = False
if CommunicationFFb is True:
    ACCELERATION = 0.5
else:
    ACCELERATION = 1


class arrow(object):
    points = (
        (0, -35),
        (-28, 35),
        (0, 25),
        (28, 35),
        (0, -35)
    )


class KEY_control:
    Shift   = False
    Left    = False
    Right   = False
    Up      = False
    Down    = False
    Space   = False
    MouseBtn = [False, False]
    MouseXY = [0, 0]


from os import path
from sys import argv
class Paths:
    pathname = path.dirname(argv[0])
    GUI_file = pathname + "/gui_artifacts/MainConsole_extendedIII.glade"
    cfg_file = pathname + "/racII.cfg"
    background_file = pathname + "/images/HUD_small.png"
