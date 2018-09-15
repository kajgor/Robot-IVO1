#################################
# 0 - Resolution ***            #
# 1 - Brightness                #
# 2 - Contrast                  #
# 3 - Saturation                #
# 4 - RedBalance                #
# 5 - BlueBalance               #
# 6 - PowerLineFreq             #
# 7 - Sharpness                 #
# 8 - ColorEffects              #
# 9 - ColorEffectsCbCr          #
# 10 - BRmode                   #
# 11 - BR                       #
# 12 - RepeatSeqHeader          #
# 13 - IframePeriod             #
# 14 - H264level                #
# 15 - H264profile              #
# 16 - ExpAuto                  #
# 17 - ExpTimeAbs               #
# 18 - ExpDynFrate              #
# 19 - ExpAutoBias              #
# 20 - WBalanceAuto             #
# 21 - ImageStabilization       #
# 22 - IsoSens                  #
# 23 - IsoSensAuto              #
# 24 - ExpMeteringMode          #
# 25 - Scene Mode               #
# 26 - JpgComprQual             #
# 31 - Speaker Volume           #
# 32 - Mic. Level               #
#################################
# Port_COMM = 4550
# Port_CAM0 = Port_COMM + 1
# Port_MIC0 = Port_COMM + 2
# Port_DSP0 = Port_COMM + 4
# Port_SPK0 = Port_COMM + 5
#################################
RECMSGLEN = 16
CLIMSGLEN = 12
TIMEOUT_GUI = 50
COMM_IDLE   = 10
RETRY_LIMIT = 15
#################################
MAX_SPEED = 50
MOUSE_MIN = [20, 10]
MOUSE_MAX = [180, 100]
#################################
X_AXIS = 0
Y_AXIS = 1
RIGHT = 1
LEFT = 0
#################################
# Encoding = 'cp037'
Encoding = 'latin_1'
VideoCodec = ('raw', 'h264', 'mjpeg', 'VP8')
AudioCodec = ('speex', 'mp3', 'aac')
VideoFramerate = [5, 15, 25, 30]
AudioBitrate = [32000, 16000, 8000]
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
#################################
TCP = 0
UDP = 1
PROTO_NAME = ['TCP', 'UDP']
#################################
# DEVICES
# MIC0_DEVICE = "alsa_input.usb-C-Media_Electronics_Inc._USB_PnP_Sound_Device-00.analog-mono"
# MIC0_DEVICE = "alsa_input.usb-0d8c_USB_PnP_Sound_Device-00.analog-mono"
CAM_1_CMD    = "v4l2-ctl --list-devices|grep 'video'|tr -d '\t'"
DEV_OUT_CMD  = "pactl list short sinks|grep output|cut -f1-2|tr '\t' ':'"
DEV_INP_CMD  = "pactl list short sources|grep input|cut -f1-2|tr '\t' ':'"


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
    stdout  = None
    errs    = None
    try:
        proc = subprocess.Popen(cmd_string, shell=True, stdout=subprocess.PIPE)
    except subprocess.CalledProcessError:
        proc = None

    if proc:
        if cmd_string[-1] == "&":   # Run process in background
            stdout = proc.pid
        else:
            try:
                stdout, errs = proc.communicate(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
                stdout, errs = proc.communicate()

            if not(str(stdout).isdigit()):  # Not numeric string
                    stdout = stdout.decode(Encoding)
                    if stdout > '':
                        if stdout[-1] == chr(10):
                            stdout = stdout[0:-1]  # Do not return CR
                        elif stdout[-1] == chr(13):
                            stdout = stdout[0:-1]  # Do not return NL

    return stdout, errs
