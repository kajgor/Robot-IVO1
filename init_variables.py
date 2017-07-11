class arrow(object):
    points = (
        (0, -35),
        (-28, 35),
        (0, 25),
        (28, 35),
        (0, -35)
    )

class KEY_control:
    Left    = False
    Right   = False
    Up      = False
    Down    = False
    Space   = False

class COMM_vars:
    speed       = 0
    direction   = 0
    camera      = True
    light       = False
    mic         = False
    display     = False
    speakers    = False
    Motor_Power = (0, 0)
    mouse       = (100, 45)

    mouseX = 100
    mouseY = 45


TIMEOUT_GUI = 20
position = (242, 135)
ACCELERATION = 0.5
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
Debug = 3
Encoding = 'latin_1'

class Paths:
    Gstreamer_Path = '/usr/bin/'
    GUI_file = "./gui_artifacts/MainConsole_extended.glade"
    cfg_file = "./racII.cfg"

