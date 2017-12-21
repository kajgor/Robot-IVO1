CONSOLE_GUI = True
RESP_DELAY = 0.025
#RESP_DELAY = 0.05

Debug = 1

CommunicationFFb = False
if CommunicationFFb is True:
    ACCELERATION = 0.5
else:
    ACCELERATION = 1

# DEVICES
# MIC0_DEVICE = "alsa_input.usb-C-Media_Electronics_Inc._USB_PnP_Sound_Device-00.analog-mono"
MIC0_DEVICE = "alsa_input.pci-0000_00_05.0.analog-stereo"

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
    time    = 0


class CAM0_control:
    Flip     = 0

from os import path
from sys import argv
class Paths:
    pathname = path.dirname(argv[0])
    GUI_file = pathname + "/gui_artifacts/Client_GUI.glade"
    cfg_file = pathname + "/ClientGUI.cfg"
    background_file = pathname + "/gui_artifacts/images/HUD_small.png"
