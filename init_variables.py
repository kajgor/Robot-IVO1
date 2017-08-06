TIMEOUT_GUI = 30
position = (242, 135)
MAX_SPEED = 50
MOUSEX_MIN = 40
MOUSEX_MAX = 150
MOUSEY_MIN = 45
MOUSEY_MAX = 100
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
HALT_0 = chr(COMM_BITSHIFT + 51) + chr(COMM_BITSHIFT + 51) + chr(COMM_BITSHIFT) + chr(COMM_BITSHIFT)
HALT_1 = chr(COMM_BITSHIFT + 51) + chr(COMM_BITSHIFT + 51) + chr(100) + chr(45)
RIGHT = 0
LEFT = 1
######################
X_AXIS = 0
Y_AXIS = 1
Debug = 1
Encoding = 'latin_1'

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
    speed       = 0
    direction   = 0
    camera      = True
    light       = False
    mic         = False
    display     = False
    speakers    = False
    CamPos      = [100, 45]
    Motor_Power = [0, 0]
    Motor_PWR   = [0, 0]
    Motor_RPM   = [0, 0]
    Motor_ACK   = [0, 0]
    CheckSum    = 0
    Current     = 0
    Voltage     = 0
    CoreTemp    = 0
    DistanceS1  = 100


class Paths:
    Gstreamer_Path = '/usr/bin/'
    GUI_file = "./gui_artifacts/MainConsole_extendedIII.glade"
    cfg_file = "./racII.cfg"

CommunicationFFb = False
if CommunicationFFb is True:
    ACCELERATION = 0.5
else:
    ACCELERATION = 1

import binascii
def calc_checksum(string):
    """
    Calculates checksum for sending commands to the ELKM1.
    Sums the ASCII character values mod256 and takes
    the lower byte of the two's complement of that value.
    """
    # return '%2X' % (-(sum(ord(c) for c in string.__str__()) % 256) & 0xFF)
    return binascii.crc32(string) % 256

