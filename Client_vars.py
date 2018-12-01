# Working UDP server:
# gst-launch-1.0 v4l2src ! video/x-raw,framerate=15/1,width=640,height=480 ! videoconvert ! x264enc pass=qual quantizer=20 tune=zerolatency ! rtph264pay ! udpsink host=127.0.0.1 port=1234
# Working UDP client:
# gst-launch-1.0 udpsrc port=1234 ! "application/x-rtp, encoding-name=H264, payload=96" ! rtph264depay ! avdec_h264 ! videoconvert ! videorate ! xvimagesink sync=false
# Tee for client cam:
# gst-launch-1.0 -v v4l2src device=/dev/video0 ! tee name=t t.
# ! videorate ! queue ! video/x-raw, framerate=15/1, width=320, height=240 ! videoconvert ! xvimagesink t.
# ! videorate ! queue ! video/x-raw, framerate=15/1, width=320, height=240 ! videoconvert ! x264enc pass=qual bitrate=300 tune=zerolatency ! rtph264pay ! udpsink host=10.0.0.55 port=1234

Debug = 1

# DEVICES
# MIC0_DEVICE = "alsa_input.usb-C-Media_Electronics_Inc._USB_PnP_Sound_Device-00.analog-mono"
# MIC0_DEVICE = "alsa_input.pci-0000_00_05.0.analog-stereo"
