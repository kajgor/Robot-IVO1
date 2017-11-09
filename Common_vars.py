Port_COMM = 4550
Port_CAM0 = Port_COMM + 1
Port_MIC0 = Port_COMM + 2
Port_DSP0 = Port_COMM + 4
Port_SPK0 = Port_COMM + 5
######################
RECMSGLEN = 16
TIMEOUT_GUI = 50
COMM_IDLE   = 10
RETRY_LIMIT = 15
######################
MAX_SPEED = 50
MOUSE_MIN = [20, 10]
MOUSE_MAX = [180, 100]
######################
X_AXIS = 0
Y_AXIS = 1
RIGHT = 1
LEFT = 0
######################
# Encoding = 'cp037'
Encoding = 'latin_1'
# Encoding = 'utf8'
VideoCodec = ("raw", "h264", "mjpeg", "VP8")
VideoFramerate = ("30", "25", "15", "5")
AudioCodec = ("speex", "mp3", "aac")
AudioBitrate = ("32000", "16000", "8000")
###### COLOURS #######
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

TCP = 0
UDP = 1
PROTO_NAME = ["TCP", "UDP"]

class COMM_vars:
    connected   = False
    comm_link_idle = 0
    connErr     = 0
    speed       = 0
    direction   = 0
    resolution  = 0
    AutoMode    = False
    light       = False
    mic         = True
    display     = False
    speakers    = False
    laser       = False
    camPosition = [100, 45]
    motor_Power = [0, 0]
    motor_PWR   = [0, 0]
    motor_RPM   = [0, 0]
    motor_ACK   = [0, 0]
    current     = 0
    voltage     = 0
    coreTemp    = 0
    distanceS1  = 100
    streaming_mode = 0
    Vcodec      = 0
    Acodec      = 0
    Framerate   = 0
    Abitrate    = 0


import binascii
def calc_checksum(string):
    """
    Calculates checksum for sending commands to the server.
    """
    return binascii.crc32(string) % 256

