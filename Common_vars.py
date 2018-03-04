
# 0 - Resolution ***
# 1 - Brightness
# 2 - Contrast
# 3 - Saturation
# 4 - RedBalance
# 5 - BlueBalance
# 6 - PowerLineFreq
# 7 - Sharpness
# 8 - ColorEffects
# 9 - ColorEffectsCbCr
# 10 - BRmode
# 11 - BR
# 12 - RepeatSeqHeader
# 13 - IframePeriod
# 14 - H264level
# 15 - H264profile
# 16 - ExpAuto
# 17 - ExpTimeAbs
# 18 - ExpDynFrate
# 19 - ExpAutoBias
# 20 - WBalanceAuto
# 21 - ImageStabilization
# 22 - IsoSens
# 23 - IsoSensAuto
# 24 - ExpMeteringMode
# 25 - Scene Mode
# 26 - JpgComprQual

Port_COMM = 4550
Port_CAM0 = Port_COMM + 1
Port_MIC0 = Port_COMM + 2
Port_DSP0 = Port_COMM + 4
Port_SPK0 = Port_COMM + 5
######################
RECMSGLEN = 16
CLIMSGLEN = 12
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
PrintOnOff = ('off', 'on')
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


class ConnectionData:
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
    camPosition = [100, 70]
    motor_Power = [0, 0]
    motor_PWR   = [0, 0]
    motor_RPM   = [0, 0]
    motor_ACK   = [0, 0]
    current     = 0
    voltage     = 0
    coreTemp    = 0
    distanceS1  = 100
    TestMode    = 1
    Vcodec      = 0
    Vbitrate    = 0
    Framerate   = 3
    Fxmode      = 255
    Fxvalue     = 0
    Exposure    = 0
    Contrast    = 0
    Brightness  = 0
    Acodec      = 0
    Abitrate    = 0
    Protocol    = 0


import binascii


def calc_checksum(string):
    """
    Calculates checksum for sending commands to the server.
    """
    return binascii.crc32(string) % 256


import subprocess


def execute_cmd(cmd_string):
    stdout = None
    try:
        stdout = subprocess.check_output(cmd_string, shell=True)
    except subprocess.CalledProcessError:
        pass
    return stdout
