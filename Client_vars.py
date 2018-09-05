# Working UDP server:
# gst-launch-1.0 v4l2src ! video/x-raw,framerate=15/1,width=640,height=480 ! videoconvert ! x264enc pass=qual quantizer=20 tune=zerolatency ! rtph264pay ! udpsink host=127.0.0.1 port=1234
# Working UDP client:
# gst-launch-1.0 udpsrc port=1234 ! "application/x-rtp, encoding-name=H264, payload=96" ! rtph264depay ! avdec_h264 ! videoconvert ! videorate ! xvimagesink sync=false

CONSOLE_GUI = True
RESP_DELAY = 0.025
#RESP_DELAY = 0.05
H264_ENC = "x264enc"

Debug = 1

CommunicationFFb = False
if CommunicationFFb is True:
    ACCELERATION = 0.5
else:
    ACCELERATION = 1

# DEVICES
# MIC0_DEVICE = "alsa_input.usb-C-Media_Electronics_Inc._USB_PnP_Sound_Device-00.analog-mono"
# MIC0_DEVICE = "alsa_input.pci-0000_00_05.0.analog-stereo"


class arrow(object):
    points = (
        (0, -35),
        (-28, 35),
        (0, 25),
        (28, 35),
        (0, -35)
    )


class rombe(object):
    points = (
        (0, -5),
        (-5, 0),
        (0, 5),
        (5, 0),
        (0, -5),
        (0, -3),
        (-3, 0),
        (0, 3),
        (3, 0),
        (0, -3),
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
    hud     = False


class DEVICE_control:
    DEV_Cam0    = None
    DEV_AudioIn = None
    DEV_AudioOut = None
    Cam0_Flip   = 0


from os import path
from sys import argv


class Files:
    pathname = path.dirname(argv[0])
    ini_file = pathname + "/ClientGUI.ini"
    background_file = pathname + "/gui_artifacts/images/HUD_small.png"
