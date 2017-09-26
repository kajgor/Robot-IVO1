TIMEOUT_GUI = 50
COMM_IDLE   = 10
position = (242, 135)
MAX_SPEED = 50
MOUSE_MIN = [40, 45]
MOUSE_MAX = [150, 100]
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
CYAN = (0, 255, 255)
RED = (255, 0, 0)
DRED = (128, 0, 0)
DDRED = (30, 0, 0)
GREEN = (0, 255, 0)
DGREEN = (0, 128, 0)
DDGREEN = (0, 30, 0)
BLUE = (0, 0, 255)
DBLUE = (0, 0, 128)
DDBLUE = (0, 0, 30)
######################
COMM_BITSHIFT = 30
RECMSGLEN = 15

capsstr = [None, None, None, None, None, None]
capsstr[1] = ", width=320, height=240, framerate=15/1"
capsstr[2] = ", width=640, height=480, framerate=15/1"
capsstr[3] = ", width=800, height=600, framerate=25/1"
capsstr[4] = ", width=1280, height=800, framerate=25/1"
capsstr[5] = ", width=1920, height=1080, framerate=25/1"

RIGHT = 0
LEFT = 1
######################
X_AXIS = 0
Y_AXIS = 1
Debug = 1
# Encoding = 'cp037'
Encoding = 'latin_1'
VideoCodec = ["video/x-h264", "video/x-raw"]


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


class COMM_vars:
    connected   = False
    comm_link_idle = 0
    ConnErr     = 0
    speed       = 0
    direction   = 0
    resolution  = 1
    light       = False
    mic         = True
    display     = False
    speakers    = False
    laser       = False
    CamPos      = [100, 45]
    Motor_Power = [0, 0]
    Motor_PWR   = [0, 0]
    Motor_RPM   = [0, 0]
    Motor_ACK   = [0, 0]
    Current     = 0
    Voltage     = 0
    CoreTemp    = 0
    DistanceS1  = 100
    RESP_DELAY  = 0.025
    RetryCnt    = 15
    streaming_mode = 0
    # resolution_last = resolution
    # camera      = True

CommunicationFFb = False
if CommunicationFFb is True:
    ACCELERATION = 0.5
else:
    ACCELERATION = 1

import os
import sys
import binascii


class Paths:
    pathname = os.path.dirname(sys.argv[0])
    GUI_file = pathname + "/gui_artifacts/MainConsole_extendedIII.glade"
    cfg_file = pathname + "/racII.cfg"
    background_file = pathname + "/images/HUD_small.png"


def calc_checksum(string):
    """
    Calculates checksum for sending commands to the server.
    """
    return binascii.crc32(string) % 256

