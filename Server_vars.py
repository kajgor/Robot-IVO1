capsstr = [None, None, None, None, None, None]
capsstr[1] = ", width=320, height=240, framerate="
capsstr[2] = ", width=640, height=480, framerate="
capsstr[3] = ", width=800, height=600, framerate="
capsstr[4] = ", width=1024, height=768, framerate="
capsstr[5] = ", width=1152, height=864, framerate="
FxModes  = ["brightness", "contrast", "saturation", "red_balance", "blue_balance", "power_line_frequency", "sharpness",
            "color_effects", "color_effects_cbcr", "video_bitrate_mode", "video_bitrate", "repeat_sequence_header",
            "h264_i_frame_period", "h264_level", "h264_profile", "auto_exposure", "exposure_time_absolute",
            "exposure_dynamic_framerate", "auto_exposure_bias", "white_balance_auto_preset", "image_stabilization",
            "iso_sensitivity", "iso_sensitivity_auto", "exposure_metering_mode", "scene_mode", "compression_quality"]
FpsModes = [5, 15, 25, 30]

VERSION = "B3.1"
HOST = ''   # Empty name meaning all available interfaces
VERTICAL = 0
HORIZONTAL = 1

# Socket retry - make more than 60 as this is the default timeout
SO_RETRY_LIMIT = 65

# HeartBeat counter
HB_VALUE = 25

# Arduino driver message len (in/out) and HeartBeat response shift
DRV_A1_MSGLEN_REQ = 8
DRV_A1_MSGLEN_RES = 16
HB_BITSHIFT       = 30

# Note omxh264enc element which is hardware h264 encoder.
# Software h264 encoder is called h264enc.
# generic GST is x264?
H264_ENC = "x264enc"

# DEVICES
# MIC0_DEVICE = "alsa_input.usb-C-Media_Electronics_Inc._USB_PnP_Sound_Device-00.analog-mono"
# MIC0_DEVICE = "alsa_input.usb-0d8c_USB_PnP_Sound_Device-00.analog-mono"
CAM_1_CMD    = "v4l2-ctl --list-devices|grep 'video'|tr -d '\t'"
DEV_OUT_CMD  = "pactl list short sinks|grep output|cut -f1-2|tr '\t' ':'"
DEV_INP_CMD  = "pactl list short sources|grep input|cut -f1-2|tr '\t' ':'"


Debug = 0

import serial.tools.list_ports


class SRV_vars:
    heartbeat   = HB_VALUE
    GUI_CONSOLE = False
    TestMode    = False
    DRV_A1_request = chr(50) + chr(50) + chr(0) + chr(0) + chr(0)

    DRV_A1_response  = chr(0) + chr(0) + chr(0) + chr(0) + chr(0)
    DRV_A1_response += chr(0) + chr(0) + chr(0) + chr(0) + chr(0) + chr(0)

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
    GUI_file = pathname + '/gui_artifacts/Server_GUI_v2.glade'
    ini_file = pathname + '/Server.ini'


class ExeCmd:
    cmd = list()                                                                        # Init
    cmd.append('echo "shutdown"')                                                       # 0
    cmd.append('echo "USB restart"')                                                    # 1
    cmd.append('')                                                                      # 2
    cmd.append('')                                                                      # 3
    cmd.append('')                                                                      # 4
    cmd.append('')                                                                      # 5
