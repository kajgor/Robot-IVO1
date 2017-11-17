capsstr = [None, None, None, None, None, None]
capsstr[1] = ", width=320, height=240, framerate=25/1"
capsstr[2] = ", width=640, height=480, framerate=30/1"
capsstr[3] = ", width=800, height=600, framerate=30/1"
capsstr[4] = ", width=1280, height=800, framerate=25/1"
capsstr[5] = ", width=1920, height=1080, framerate=25/1"

VERSION = "B3.0"
HOST = ''   # Empty name meaning all available interfaces
VERTICAL = 0
HORIZONTAL = 1

# Socket retry - make more than 60 as this is the default timeout
SO_RETRY_LIMIT = 65

# Arduino driver message len (in/out)
DRV_A1_MSGLEN_REQ = 8
DRV_A1_MSGLEN_RES = 16

# Note omxh264enc element which is hardware h264 encoder.
# Software h264 encoder is called h264enc.
# generic GST is x264?
H264_ENC = "x264enc"

# DEVICES
# MIC0_DEVICE = "alsa_input.usb-C-Media_Electronics_Inc._USB_PnP_Sound_Device-00.analog-mono"
MIC0_DEVICE = "alsa_input.usb-0d8c_USB_PnP_Sound_Device-00.analog-mono"

Debug = 0

import serial.tools.list_ports


class SRV_vars:
    GUI_CONSOLE = False
    TestMode    = False
    DRV_A1_request = chr(50) + chr(50) + chr(0) + chr(0) + chr(0)

    DRV_A1_response  = chr(0) + chr(0) + chr(0) + chr(0) + chr(0)
    DRV_A1_response += chr(0) + chr(0) + chr(0) + chr(0) + chr(0)

    available_ports = list(serial.tools.list_ports.comports())
    available_ports.append(None)
    for Serial_Port in available_ports:
        print(Serial_Port)
        if Serial_Port is not None:
            if "USB2.0-Serial" in Serial_Port:
                Serial_Port = Serial_Port[0]
                break

    Port_Baudrate = 115200
    Port_bytesize = serial.EIGHTBITS
    Port_parity   = serial.PARITY_NONE
    Port_stopbits = serial.STOPBITS_ONE
    Port_Timeout  = 1
    Port_XonXoff  = serial.XOFF
    Port_DsrDtr   = serial.XOFF
    Port_RtsCts   = serial.XON  # disable/enable hardware (RTS/CTS) flow control

    CTRL1_Mask    = 0

from os import path
from sys import argv


class Paths:
    pathname = path.dirname(argv[0])
    GUI_file = pathname + "/gui_artifacts/MainConsole_extendedIII.glade"
