import socket
import queue
import time
import gi.repository

gi.require_version('Gst', '1.0')
gi.require_version('GstVideo', '1.0')
from gi.repository import Gst, GstVideo, GdkPixbuf

# from sshtunnel import SSHTunnelForwarder
# from paramiko import RSAKey
from cairo import ImageSurface
from math import pi
from re import findall
from _thread import *
from Common_vars import ConnectionData, TCP, MAX_SPEED, AudioBitrate,\
    RETRY_LIMIT, CLIMSGLEN, RECMSGLEN, Encoding, LEFT, RIGHT, calc_checksum, X_AXIS, Y_AXIS

from Client_vars import *

Gst.init(None)


class DisplayStream:
    def __init__(self):
        self.sender_video       = Gst.Pipeline.new("sender_video")
        # glimagesink(default)/gtksink/cacasink/autovideosink/ximagesink(working)
        #   SET VIDEO (SENDER)
        self.sender_video_source       = Gst.ElementFactory.make("v4l2src", "video-source")

        self.sender_video_videorate_udp = Gst.ElementFactory.make("videorate", "vr1")
        self.sender_video_queue_udp    = Gst.ElementFactory.make("queue", "queue1")
        self.sender_video_caps_udp     = Gst.ElementFactory.make("capsfilter", "capsfilter1")
        self.sender_video_convert_udp  = Gst.ElementFactory.make("videoconvert", "vc1")
        self.sender_video_encoder      = Gst.ElementFactory.make(H264_ENC, "encoder_udp")
        self.sender_video_rtimer       = Gst.ElementFactory.make("rtph264pay", "rtimer_udp")
        self.sender_video_sink_udp     = Gst.ElementFactory.make("udpsink", "udp-output")

        self.sender_video_videorate_xv = Gst.ElementFactory.make("videorate", "vr2")
        self.sender_video_queue_xv     = Gst.ElementFactory.make("queue", "queue2")
        self.sender_video_caps_xv      = Gst.ElementFactory.make("capsfilter", "capsfilter2")
        self.sender_video_convert_xv   = Gst.ElementFactory.make("videoconvert", "vc2")
        self.sender_video_sink_xv      = Gst.ElementFactory.make("xvimagesink", "video-output")

        self.sender_video_tee          = Gst.ElementFactory.make("tee", "tee")
# ! videorate ! queue ! video/x-raw, framerate=15/1, width=320, height=240 ! videoconvert ! x264enc pass=qual bitrate=300 tune=zerolatency ! rtph264pay ! udpsink host=10.0.0.55 port=1234
# ! videorate ! queue ! video/x-raw, framerate=15/1, width=320, height=240 ! videoconvert ! xvimagesink

        # if ConnectionData.Protocol == TCP:
        #     # self.sender_video_encoder = Gst.ElementFactory.make("gdppay", "encoder")
        #     # self.sender_video_sink   = Gst.ElementFactory.make("tcpserversink", "video-output")
        #     # if Host:
        #     #     self.sender_video_sink.set_property("host", Host)
        #     # else:
        #     #     self.sender_video_sink.set_property("host", "0.0.0.0")
        #     pass
        # else:

        self.gst_init_cam_udp()

        self.sender_video_encoder.set_property("tune", "zerolatency")
        self.sender_video_encoder.set_property("pass", "qual")
        self.sender_video_encoder.set_property("bitrate", 300)
        self.sender_video_encoder.set_property("byte-stream", True)
        # self.sender_video_encoder.set_property("b-pyramid", True)

        self.sender_video_sink_udp.set_property("host", 'localhost')
        self.sender_video_sink_udp.set_property("port", 9999)
        self.sender_video_sink_udp.set_property("sync", False)
        caps = Gst.Caps.from_string("video/x-raw, width=320, height=240, frametrate=15/1")
        self.sender_video_caps_udp.set_property("caps", caps)

        caps = Gst.Caps.from_string("video/x-raw, width=320, height=240, frametrate=15/1")
        self.sender_video_caps_xv.set_property("caps", caps)
        self.sender_video_sink_xv.set_property("sync", False)

    def gst_init_cam_udp(self):
        ####################################################################
        ### Build video pipeline as following:
        ####################################################################

        self.sender_video.add(self.sender_video_source)
        self.sender_video.add(self.sender_video_tee)

        self.sender_video.add(self.sender_video_videorate_xv)
        self.sender_video.add(self.sender_video_queue_xv)
        self.sender_video.add(self.sender_video_caps_xv)
        self.sender_video.add(self.sender_video_convert_xv)
        self.sender_video.add(self.sender_video_sink_xv)

        self.sender_video.add(self.sender_video_videorate_udp)
        self.sender_video.add(self.sender_video_queue_udp)
        self.sender_video.add(self.sender_video_caps_udp)
        self.sender_video.add(self.sender_video_convert_udp)
        self.sender_video.add(self.sender_video_encoder)
        self.sender_video.add(self.sender_video_rtimer)
        self.sender_video.add(self.sender_video_sink_udp)

        self.sender_video_videorate_udp.link(self.sender_video_queue_udp)
        self.sender_video_queue_udp.link(self.sender_video_caps_udp)
        self.sender_video_caps_udp.link(self.sender_video_convert_udp)
        self.sender_video_convert_udp.link(self.sender_video_encoder)
        self.sender_video_encoder.link(self.sender_video_rtimer)
        self.sender_video_rtimer.link(self.sender_video_sink_udp)

        self.sender_video_videorate_xv.link(self.sender_video_queue_xv)
        self.sender_video_queue_xv.link(self.sender_video_caps_xv)
        self.sender_video_caps_xv.link(self.sender_video_convert_xv)
        self.sender_video_convert_xv.link(self.sender_video_sink_xv)

        self.sender_video_tee.link(self.sender_video_videorate_udp)
        self.sender_video_tee.link(self.sender_video_videorate_xv)

        self.sender_video_source.link(self.sender_video_tee)

# noinspection PyPep8Naming
class ReceiverStream:
    # TCP
    # SRV TEST TCP:
    # Source>Capsfilter>Payloader>Sink
    # CLI TEST TCP:
    # Source>Depayloader>Convert>Sink

    # SRV LIVE TCP:
    # Source>Capsfilter>Parser>RtPay>Encoder>Sink
    # CLI LIVE TCP:
    # Source>Depayloader>RtDePay>Decoder>Convert>VideoFlip>Sink

    # UDP
    # SRV TEST UDP:
    # Source>Capsfilter>Encoder>RtPay>Sink
    # CLI TEST UDP:
    # Source>Capsfilter>RtDePay>Decoder>Convert>Sink

    # SRV LIVE UDP:
    # Source>Capsfilter>Encoder>RtPay>Sink
    # CLI LIVE UDP:
    # Source>Capsfilter>RtDePay>Decoder>Convert>VideoFlip>Sink

    def __init__(self, Host, Port_COMM, VideoMode):
        Port_CAM0 = Port_COMM + 1
        Port_MIC0 = Port_COMM + 2
        # Port_DSP0 = Port_COMM + 4
        Port_SPK0 = Port_COMM + 5

        self.player_video       = Gst.Pipeline.new("player_video")
        self.player_audio       = Gst.Pipeline.new("player_audio")
        self.sender_audio       = Gst.Pipeline.new("sender_audio")

        #   SET VIDEO (PLAYER)
        self.player_video_flip         = Gst.ElementFactory.make("videoflip", "flip")
        self.player_video_capsfilter   = Gst.ElementFactory.make("capsfilter", "capsfilter")
        self.player_video_depayloader  = Gst.ElementFactory.make("gdpdepay", "depayloader")
        self.player_video_convert      = Gst.ElementFactory.make("videoconvert")
        self.player_video_rtimer       = Gst.ElementFactory.make("rtph264depay", "rtimer")
        self.player_video_decoder      = Gst.ElementFactory.make("avdec_h264", "avdec")
        self.player_video_fpsadj       = Gst.ElementFactory.make("videorate")
        self.player_video_fpsadjcaps   = Gst.ElementFactory.make("capsfilter", "fpsadj")
        self.player_video_sink         = Gst.ElementFactory.make("ximagesink", "sink")

# ToDo: Hud sync
#         caps = Gst.Caps.from_string("video/x-raw, framerate=30/1")
#         self.fpsadjcaps_video.set_property("caps", caps)
#         self.fpsadj_video.set_property("max-rate", 30)

        #   SET AUDIO RECEIVER
        #    udpsrc port=3333 ! application/x-rtp, media=audio, clock-rate=32000, encoding-name=SPEEX, payload=96 !
        #    rtpspeexdepay ! speexdec ! pulsesink sync=false
        self.player_audio_capsfilter   = Gst.ElementFactory.make("capsfilter", "capsfilter_audio")
        self.player_audio_depayloader  = Gst.ElementFactory.make("rtpspeexdepay", "depayloader_audio")
        self.player_audio_decoder      = Gst.ElementFactory.make("speexdec", "decoder_audio")
        # self.convert_audio = ([Gst.ElementFactory.make("audioresample"),
        #                        Gst.ElementFactory.make("audioresample")])
        #
        self.sink_audio = Gst.ElementFactory.make("pulsesink", "local_sink_audio")
        self.sink_audio.set_property("device", DEVICE_control.DEV_AudioOut)

        # SET AUDIO SENDER
        if VideoMode is False:
            self.sender_audio_source = Gst.ElementFactory.make("audiotestsrc", "local_source_audio")
            self.sender_audio_source.set_property("wave", 0)
        else:
            self.sender_audio_source = Gst.ElementFactory.make("pulsesrc", "local_source_audio")
            self.sender_audio_source.set_property("device", DEVICE_control.DEV_AudioIn)

        self.sender_audio_capsfilter = Gst.ElementFactory.make("capsfilter", "capsfilter_audio")
        self.sender_audio_resample   = Gst.ElementFactory.make("audioresample", "resample_audio")
        self.sender_audio_encoder    = Gst.ElementFactory.make("speexenc", "encoder_audio")
        self.sender_audio_rtimer     = Gst.ElementFactory.make("rtpspeexpay", "rtimer_audio")

        if ConnectionData.Protocol == TCP:
            self.player_video_source = Gst.ElementFactory.make("tcpclientsrc", "remote_source_video")
            self.player_audio_source = Gst.ElementFactory.make("tcpclientsrc", "remote_source_audio")
            self.sender_audio_sink   = Gst.ElementFactory.make("tcpserversink", "remote_sink_audio")
# ToDo:
            self.player_video_source.set_property("host", Host)
            self.player_audio_source.set_property("host", Host)

            if VideoMode is False:
                self.gst_init_test_tcp()
            else:
                self.gst_init_live()

        else:
            self.player_video_source  = Gst.ElementFactory.make("udpsrc", "remote_source_video_udp")
            self.player_audio_source  = Gst.ElementFactory.make("udpsrc", "remote_source_audio_udp")
            self.sender_audio_sink    = Gst.ElementFactory.make("udpsink", "remote_sink_audio_udp")

            if VideoMode is False:
                self.gst_init_test_udp()
            else:
                self.gst_init_live_udp()

        self.player_video_source.set_property("port", Port_CAM0)
        caps = Gst.Caps.from_string("application/x-rtp, encoding-name=H264, payload=96")
        self.player_video_capsfilter.set_property("caps", caps)
        self.player_audio_source.set_property("port", Port_MIC0)
        caps = Gst.Caps.from_string("application/x-rtp, media=audio, clock-rate=32000, encoding-name=SPEEX, payload=96")
        self.player_audio_capsfilter.set_property("caps", caps)
        self.sender_audio_sink.set_property("host", Host)
        self.sender_audio_sink.set_property("port", Port_SPK0)
        self.sender_audio_sink.set_property("sync", False)
        # self.sink_video.set_property("sync", False)
        # self.sink_video.set_property("set_clock", "100")
        self.sink_audio.set_property("sync", True)

        if not self.player_video_sink or not self.player_video_source:
            print("ERROR! GL elements not available.")
            exit()

    def gst_init_test_tcp(self):
        # receive raw test image generated by gstreamer server
        # --- Gstreamer setup begin ---
        self.player_video.add(self.player_video_source)
        self.player_video.add(self.player_video_depayloader)
        self.player_video.add(self.player_video_convert)
        self.player_video.add(self.player_video_fpsadj)
        self.player_video.add(self.player_video_fpsadjcaps)
        self.player_video.add(self.player_video_sink)

        self.player_video_source.link(self.player_video_depayloader)
        self.player_video_depayloader.link(self.player_video_convert)
        self.player_video_convert.link(self.player_video_fpsadj)
        self.player_video_fpsadj.link(self.player_video_fpsadjcaps)
        self.player_video_fpsadjcaps.link(self.player_video_sink)

        #    tcpclientsrc host=x.x.x.x port=4552 ! application/x-rtp, media=audio, clock-rate=32000, encoding-name=SPEEX, payload=96 !
        #    rtpspeexdepay ! speexdec ! pulsesink sync=false
        self.player_audio.add(self.player_audio_source)
        self.player_audio.add(self.player_audio_capsfilter)
        self.player_audio.add(self.player_audio_depayloader)
        self.player_audio.add(self.player_audio_decoder)
        self.player_audio.add(self.sink_audio)

        self.player_audio_source.link(self.player_audio_capsfilter)
        self.player_audio_capsfilter.link(self.player_audio_depayloader)
        self.player_audio_depayloader.link(self.player_audio_decoder)
        self.player_audio_decoder.link(self.sink_audio)

        # SENDER (TCP)
        self.sender_audio.add(self.sender_audio_source)
        self.sender_audio.add(self.sender_audio_capsfilter)
        self.sender_audio.add(self.sender_audio_resample)
        self.sender_audio.add(self.sender_audio_encoder)
        self.sender_audio.add(self.sender_audio_rtimer)
        self.sender_audio.add(self.sender_audio_sink)

        self.sender_audio_source.link(self.sender_audio_capsfilter)
        self.sender_audio_capsfilter.link(self.sender_audio_resample)
        self.sender_audio_resample.link(self.sender_audio_encoder)
        self.sender_audio_encoder.link(self.sender_audio_rtimer)
        self.sender_audio_rtimer.link(self.sender_audio_sink)
        # --- Gstreamer setup end ---

    def gst_init_live(self):
        # --- Gstreamer setup begin ---
        self.player_video.add(self.player_video_source)
        self.player_video.add(self.player_video_depayloader)
        self.player_video.add(self.player_video_rtimer)
        self.player_video.add(self.player_video_decoder)
        self.player_video.add(self.player_video_convert)
        self.player_video.add(self.player_video_flip)
        self.player_video.add(self.player_video_fpsadj)
        self.player_video.add(self.player_video_fpsadjcaps)
        self.player_video.add(self.player_video_sink)

        self.player_video_source.link(self.player_video_depayloader)
        self.player_video_depayloader.link(self.player_video_rtimer)
        self.player_video_rtimer.link(self.player_video_decoder)
        self.player_video_decoder.link(self.player_video_convert)
        self.player_video_convert.link(self.player_video_flip)
        self.player_video_flip.link(self.player_video_fpsadj)
        self.player_video_fpsadj.link(self.player_video_fpsadjcaps)
        self.player_video_fpsadjcaps.link(self.player_video_sink)

        #    tcpclientsrc host=x.x.x.x port=4552 ! application/x-rtp, media=audio, clock-rate=32000, encoding-name=SPEEX, payload=96 !
        #    rtpspeexdepay ! speexdec ! pulsesink sync=false
        self.player_audio.add(self.player_audio_source)
        self.player_audio.add(self.player_audio_capsfilter)
        self.player_audio.add(self.player_audio_depayloader)
        self.player_audio.add(self.player_audio_decoder)
        self.player_audio.add(self.sink_audio)

        self.player_audio_source.link(self.player_audio_capsfilter)
        self.player_audio_capsfilter.link(self.player_audio_depayloader)
        self.player_audio_depayloader.link(self.player_audio_decoder)
        self.player_audio_decoder.link(self.sink_audio)

        # SENDER (TCP)
        self.sender_audio.add(self.sender_audio_source)
        self.sender_audio.add(self.sender_audio_capsfilter)
        self.sender_audio.add(self.sender_audio_resample)
        self.sender_audio.add(self.sender_audio_encoder)
        self.sender_audio.add(self.sender_audio_rtimer)
        self.sender_audio.add(self.sender_audio_sink)

        self.sender_audio_source.link(self.sender_audio_capsfilter)
        self.sender_audio_capsfilter.link(self.sender_audio_resample)
        self.sender_audio_resample.link(self.sender_audio_encoder)
        self.sender_audio_encoder.link(self.sender_audio_rtimer)
        self.sender_audio_rtimer.link(self.sender_audio_sink)
        # --- Gstreamer setup end ---

    def gst_init_test_udp(self):
        # receive raw test image generated by gstreamer server
        # --- Gstreamer setup begin ---
        self.player_video.add(self.player_video_source)
        self.player_video.add(self.player_video_capsfilter)
        self.player_video.add(self.player_video_rtimer)
        self.player_video.add(self.player_video_decoder)
        self.player_video.add(self.player_video_convert)
        self.player_video.add(self.player_video_fpsadj)
        self.player_video.add(self.player_video_fpsadjcaps)
        self.player_video.add(self.player_video_sink)

        self.player_video_source.link(self.player_video_capsfilter)
        self.player_video_capsfilter.link(self.player_video_rtimer)
        self.player_video_rtimer.link(self.player_video_decoder)
        # self.capsfilter_video.link(self.decoder_video)
        self.player_video_decoder.link(self.player_video_convert)
        self.player_video_convert.link(self.player_video_fpsadj)
        self.player_video_fpsadj.link(self.player_video_fpsadjcaps)
        self.player_video_fpsadjcaps.link(self.player_video_sink)

        #    udpsrc port=3333 ! application/x-rtp, media=audio, clock-rate=32000, encoding-name=SPEEX, payload=96 !
        #    rtpspeexdepay ! speexdec ! pulsesink sync=false
        self.player_audio.add(self.player_audio_source)
        self.player_audio.add(self.player_audio_capsfilter)
        self.player_audio.add(self.player_audio_depayloader)
        self.player_audio.add(self.player_audio_decoder)
        self.player_audio.add(self.sink_audio)

        self.player_audio_source.link(self.player_audio_capsfilter)
        self.player_audio_capsfilter.link(self.player_audio_depayloader)
        self.player_audio_depayloader.link(self.player_audio_decoder)
        self.player_audio_decoder.link(self.sink_audio)

        # SENDER (UDP)
        self.sender_audio.add(self.sender_audio_source)
        self.sender_audio.add(self.sender_audio_capsfilter)
        self.sender_audio.add(self.sender_audio_resample)
        self.sender_audio.add(self.sender_audio_encoder)
        self.sender_audio.add(self.sender_audio_rtimer)
        self.sender_audio.add(self.sender_audio_sink)

        self.sender_audio_source.link(self.sender_audio_capsfilter)
        self.sender_audio_capsfilter.link(self.sender_audio_resample)
        self.sender_audio_resample.link(self.sender_audio_encoder)
        self.sender_audio_encoder.link(self.sender_audio_rtimer)
        self.sender_audio_rtimer.link(self.sender_audio_sink)
        # --- Gstreamer setup end ---

    def gst_init_live_udp(self):
        # --- Gstreamer setup begin ---
        self.player_video.add(self.player_video_source)
        self.player_video.add(self.player_video_capsfilter)
        self.player_video.add(self.player_video_rtimer)
        self.player_video.add(self.player_video_decoder)
        self.player_video.add(self.player_video_convert)
        self.player_video.add(self.player_video_fpsadj)
        self.player_video.add(self.player_video_fpsadjcaps)
        self.player_video.add(self.player_video_flip)
        self.player_video.add(self.player_video_sink)

        self.player_video_source.link(self.player_video_capsfilter)
        self.player_video_capsfilter.link(self.player_video_rtimer)
        self.player_video_rtimer.link(self.player_video_decoder)
        self.player_video_decoder.link(self.player_video_convert)
        self.player_video_convert.link(self.player_video_fpsadj)
        self.player_video_fpsadj.link(self.player_video_fpsadjcaps)
        self.player_video_fpsadjcaps.link(self.player_video_flip)
        self.player_video_flip.link(self.player_video_sink)

        #    udpsrc port=3333 ! application/x-rtp, media=audio, clock-rate=32000, encoding-name=SPEEX, payload=96 !
        #    rtpspeexdepay ! speexdec ! pulsesink sync=false
        # PLAYER
        self.player_audio.add(self.player_audio_source)
        self.player_audio.add(self.player_audio_capsfilter)
        self.player_audio.add(self.player_audio_depayloader)
        self.player_audio.add(self.player_audio_decoder)
        self.player_audio.add(self.sink_audio)

        self.player_audio_source.link(self.player_audio_capsfilter)
        self.player_audio_capsfilter.link(self.player_audio_depayloader)
        self.player_audio_depayloader.link(self.player_audio_decoder)
        self.player_audio_decoder.link(self.sink_audio)

        # SENDER (UDP)
        self.sender_audio.add(self.sender_audio_source)
        self.sender_audio.add(self.sender_audio_capsfilter)
        self.sender_audio.add(self.sender_audio_resample)
        self.sender_audio.add(self.sender_audio_encoder)
        self.sender_audio.add(self.sender_audio_rtimer)
        self.sender_audio.add(self.sender_audio_sink)

        self.sender_audio_source.link(self.sender_audio_capsfilter)
        self.sender_audio_capsfilter.link(self.sender_audio_resample)
        self.sender_audio_resample.link(self.sender_audio_encoder)
        self.sender_audio_encoder.link(self.sender_audio_rtimer)
        self.sender_audio_rtimer.link(self.sender_audio_sink)
        # --- Gstreamer setup end ---


class MainDisplay:
    background_control = ImageSurface.create_from_png(Files.background_file)

    image = None

    def draw_hud(self, image):

        if image is None:
            image = self.image
        else:
            self.image = image

        image.set_line_width(1)
        image.translate(300, 200)

        if ConnectionData.speed >= 0:
            image.rotate(ConnectionData.direction / (pi * 5))
        else:
            image.rotate((ConnectionData.direction + MAX_SPEED) / (pi * 5))

        # Direction arrow
        image.set_source_rgb(0.25, 0.25, 0.25)
        for i in range(4):
            image.line_to(arrow.points[i][0], arrow.points[i][1])
        # image.fill()
        image.set_source_rgb(0, 0.75, 0.75)
        for i in range(5):
            image.line_to(arrow.points[i][0], arrow.points[i][1])
        image.stroke()

        # Speed arrow (REQ)
        image.set_source_rgb(abs(ConnectionData.speed / MAX_SPEED), 1 - abs(ConnectionData.speed / MAX_SPEED), 0)
        image.line_to(arrow.points[0][0], arrow.points[0][1] + 60 - abs((ConnectionData.speed / MAX_SPEED) * 50))
        for i in range(1, 4):
                image.line_to(arrow.points[i][0], arrow.points[i][1])
        # image.fill()

        # Speed arrow (ACK)
        image.set_source_rgb(0, 0.75, 0.75)
        speed_ACK = abs(ConnectionData.motor_ACK[0] + ConnectionData.motor_ACK[1]) * 0.5
        image.line_to(arrow.points[1][0], arrow.points[1][1])
        image.line_to(arrow.points[0][0], arrow.points[0][1] + 60 - speed_ACK)
        image.line_to(arrow.points[3][0], arrow.points[3][1])
        image.stroke()

        # Camera position
        image.set_source_rgb(.8, 0.05, 0.8)
        for i in range(10):
            image.line_to(rombe.points[i][0] - ConnectionData.camPosition[0] + 100,
                          rombe.points[i][1] + ConnectionData.camPosition[1] - 70)
        image.stroke()

    def draw_arrow(self, image):
        image.set_source_surface(self.background_control, 0, 0)
        image.paint()

        image.set_line_width(1)
        image.translate(90, 81)

        if ConnectionData.speed >= 0:
            image.rotate(ConnectionData.direction / (pi * 5))
        else:
            image.rotate((ConnectionData.direction + MAX_SPEED) / (pi * 5))

        # Direction arrow
        image.set_source_rgb(0.25, 0.25, 0.25)
        for i in range(4):
            image.line_to(arrow.points[i][0], arrow.points[i][1])
        image.fill()
        image.set_source_rgb(0, 0.75, 0.75)
        for i in range(5):
            image.line_to(arrow.points[i][0], arrow.points[i][1])
        image.stroke()

        # Speed arrow (REQ)
        image.set_source_rgb(abs(ConnectionData.speed / MAX_SPEED), 1 - abs(ConnectionData.speed / MAX_SPEED), 0)
        image.line_to(arrow.points[0][0], arrow.points[0][1] + 60 - abs((ConnectionData.speed / MAX_SPEED) * 50))
        for i in range(1, 4):
                image.line_to(arrow.points[i][0], arrow.points[i][1])
        image.fill()

        # Speed arrow (ACK)
        image.set_source_rgb(0, 0.75, 0.75)
        speed_ACK = abs(ConnectionData.motor_ACK[0] + ConnectionData.motor_ACK[1]) * 0.5
        image.line_to(arrow.points[1][0], arrow.points[1][1])
        image.line_to(arrow.points[0][0], arrow.points[0][1] + 60 - speed_ACK)
        image.line_to(arrow.points[3][0], arrow.points[3][1])
        image.stroke()

        # Camera position
        image.set_source_rgb(.8, 0.05, 0.8)
        for i in range(10):
            image.line_to(rombe.points[i][0] - ConnectionData.camPosition[0] + 100,
                          rombe.points[i][1] + ConnectionData.camPosition[1] - 70)
        image.stroke()

    def on_message(self, message):
        msgtype = message.type
        if msgtype == Gst.MessageType.EOS:
            if Debug > 1:
                Console.print ("EOS: SIGNAL LOST")
            return "VIDEO CONNECTION EOS: SIGNAL LOST"

        elif msgtype == Gst.MessageType.ERROR:
            err, debug = message.parse_error()
            debug_s = debug.split("\n")
            if Debug > 0:
                Console.print ("ERROR:", debug_s)
            return debug_s[debug_s.__len__() - 1]

        elif msgtype == Gst.MessageType.STATE_CHANGED:
            # print('STATE_CHANGED')
            pass

        # elif msgtype == Gst.MessageType.BUFFERING:
        #     print('BUFFERING')

        else:
            return None

    def on_sync_message(self, message, SXID):
        if message.get_structure().get_name() == 'prepare-window-handle':
            imagesink = message.src
            imagesink.set_property("force-aspect-ratio", True)
            imagesink.set_window_handle(SXID.get_xid())


class SenderDisplay:
    def on_message(self, message):
        msgtype = message.type
        if msgtype == Gst.MessageType.EOS:
            if Debug > 1:
                Console.print ("EOS: SIGNAL LOST")
            return "VIDEO CONNECTION EOS: SIGNAL LOST"

        elif msgtype == Gst.MessageType.ERROR:
            err, debug = message.parse_error()
            debug_s = debug.split("\n")
            if Debug > 0:
                Console.print ("ERROR:", debug_s)
            return debug_s[debug_s.__len__() - 1]

        elif msgtype == Gst.MessageType.STATE_CHANGED:
            # print('STATE_CHANGED')
            pass

        # elif msgtype == Gst.MessageType.BUFFERING:
        #     print('BUFFERING')
        else:
            return None

    def on_sync_message(self, message, SXID):
        if message.get_structure().get_name() == 'prepare-window-handle':
            imagesink = message.src
            imagesink.set_property("force-aspect-ratio", True)
            imagesink.set_window_handle(SXID.get_xid())

class ConnectionThread:
    srv = None
    tunnel = None

    Player_Display = MainDisplay()
    Sender_Display = SenderDisplay()
    Display_Stream = DisplayStream()
    FxQueue = queue.Queue()

    def __init__(self, P_SXID, S_SXID):
        self.Player_SXID    = P_SXID
        self.Sender_SXID    = S_SXID
        self.Rac_Stream     = None
        self.Streaming_mode = 0
        self.FxMode         = 255
        self.FxValue        = 0

    # def open_ssh_tunnel(self, Host, Port, rsa_file, rsa_password, username, remote_host, compression):
    #     if compression == 0:  # Auto
    #         compression = not(bool(ConnectionData.TestMode))
    #     elif compression == 1:
    #         compression = True
    #     else:
    #         compression = False
    #
    #     Console.print("Tunneling mode started\n [Compression is %s]" % compression)
    #     self.tunnel = SSHTunnelForwarder(
    #         (Host, Port),  # jump server address
    #         ssh_username=username,
    #         ssh_pkey=RSAKey.from_private_key_file(rsa_file, password=rsa_password),
    #         remote_bind_addresses=[(remote_host, Port_COMM),
    #                                (remote_host, Port_CAM0),
    #                                (remote_host, Port_MIC0),
    #                                (remote_host, Port_SPK0)],  # storage box ip address
    #         local_bind_addresses=[('127.0.0.1', Port_COMM),
    #                               ('127.0.0.1', Port_CAM0),
    #                               ('127.0.0.1', Port_MIC0),
    #                               ('127.0.0.1', Port_SPK0)],
    #         compression=compression)
    #
    #     try:
    #         self.tunnel.start()
    #     except:
    #         return None, None
    #
    #     Console.print("SSH tunnels opened on ports:\n   ", self.tunnel.local_bind_ports)
    #     return "localhost", Port_COMM
    #
    # def open_udp_to_tcp_link(self):
    #     res = True
    #     ports = list()
    #     pids  = list()
    #     for port in (Port_CAM0, Port_MIC0, Port_SPK0):
    #         cmd = 'socat -T15 udp4-recvfrom:' + str(port) + ',reuseaddr,fork tcp:localhost:' + str(port) + ' &'
    #         out, err = execute_cmd(cmd)
    #         if out.__str__().isdigit():
    #             pids.append(out)
    #         else:
    #             ports.append(port)
    #             res = False
    #
    #     if res is True:
    #         return res, pids
    #     else:
    #         return res, ports

    def draw_arrow(self, message):
        self.Player_Display.draw_arrow(message)

    def draw_hud(self, message):
        # if self.Rac_Stream is not None:
        #     self.Rac_Stream.player_video.set_state(Gst.State.READY)
        #     self.Rac_Stream.player_video.set_state(Gst.State.PAUSED)
        self.Player_Display.draw_hud(message)

    def on_player_message(self, bus, message):
        retmsg = self.Player_Display.on_message(message)
        if retmsg is not None:
            print("retmsg:", retmsg)
            # self.ToggleButton_connect.set_active(False)
            # self.StatusBar.push(self.context_id, retmsg)

    def on_player_sync_message(self, bus, message):
        self.Player_Display.on_sync_message(message, self.Player_SXID)

    def on_sender_message(self, bus, message):
        retmsg = self.Sender_Display.on_message(message)
        if retmsg is not None:
            print("retmsg:", retmsg)
            # self.ToggleButton_connect.set_active(False)
            # self.StatusBar.push(self.context_id, retmsg)

    def on_sender_sync_message(self, bus, message):
        self.Sender_Display.on_sync_message(message, self.Sender_SXID)

    def run_camera(self):
        bus = self.Display_Stream.sender_video.get_bus()
        bus.add_signal_watch()
        bus.enable_sync_message_emission()
        bus.connect("message", self.on_sender_message)
        bus.connect("sync-message::element", self.on_sender_sync_message)


    def establish_connection(self, Host, Port):
        Console.print("Establishing connection with \n %s on port"  % Host, Port)
        self.Rac_Stream = ReceiverStream(Host, Port, ConnectionData.TestMode)

        bus = self.Rac_Stream.player_video.get_bus()
        bus.add_signal_watch()
        bus.enable_sync_message_emission()
        bus.connect("message", self.on_player_message)
        bus.connect("sync-message::element", self.on_player_sync_message)


        # if self.Display_Stream.sender_video.get_state() == Gst.State.PLAYING:
        self.Display_Stream.sender_video.set_state(Gst.State.READY)
        Port_DSP0 = Port + 4
        self.Display_Stream.sender_video_sink_udp.set_property('port', Port_DSP0)
        self.Display_Stream.sender_video_sink_udp.set_property('host', Host)

        start_new_thread(self.connection_thread, (Host, Port))
        time.sleep(0.25)

        l_iter = 0
        while ConnectionData.connected is False and l_iter < 10:
            l_iter += 1
            Console.print("Retry:", l_iter)
            time.sleep(0.25)

        if ConnectionData.connected is True:
            retmsg = "Server connected! " + self.srv.getsockname().__str__()
            # if Debug > 2:
            Console.print(retmsg)
        else:
            retmsg = "Connection Error [" + (Host, Port).__str__() + "]"
            # if Debug > 0:
            Console.print(retmsg)

        return ConnectionData.connected, retmsg

    def close_connection(self):
        # if Debug > 1:
        Console.print("Closing connection...")
        # print("Closing connection...")
        try:
            self.tunnel.close()
        except:
            Console.print("tunnel not open")

        try:
            self.srv.shutdown(socket.SHUT_RDWR)
        except OSError:
            # if Debug > 1:
            Console.print("...not connected!")
            # print("...not connected!")
        except AttributeError:
            # if Debug > 1:
            Console.print("...not connected!")
            # print("...not connected!")

        try:
            self.srv.close()
        except AttributeError:
            self.srv = None

        # execute_cmd("killall socat")
        ConnectionData.connected = False
        # if Debug > 1:
        Console.print("Connection closed.")
        # print("Connection closed.")

    def check_connection(self, HostIp):
        try:
            status = self.srv.getpeername()
        except OSError:
            status = (False, False)

        if not HostIp:
            if status[0] != '0.0.0.0':
                HostIp = status[0]

        if status[0] == HostIp:
            if Debug > 2: Console.print("Connection status: " + status.__str__())
            return True
        else:
            if Debug > 1: Console.print("Not connected.")
            return False

    ###############################################################################
    ################   COMMUNICATION LOOP START   #################################
    ###############################################################################

    def connection_thread(self, Host, Port_Comm):
        if Debug > 2:
            Console.print("Connecting...")
        self.srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_address = (Host, Port_Comm)

        Console.print("CONN:", end="")

        ConnectionData.connected = True
        try:
            self.srv.connect(server_address)
        except ConnectionResetError:
            ConnectionData.connected = False
            Console.print("Server not responding.")
        except ConnectionRefusedError:
            ConnectionData.connected = False
            Console.print("Server refused connection.")
        except socket.gaierror:
            ConnectionData.connected = False
            Console.print("Invalid protocol.")
        except OSError:
            ConnectionData.connected = False
            Console.print("No route to host.")

        if ConnectionData.connected is True:
            Console.print("Link with", self.srv.getpeername(), "established.")
            time.sleep(1)
            IP_addr = socket.gethostbyname(Host)
            self.send_init_string(IP_addr)

        cam0_restart = False
        resolution_last = None
        AudioBitrate_last = None
        mic_last = None
        speaker_last = None
        display_last = None
        cam0_flip_last = None
        self.Streaming_mode = 0
        warmup = 30

        while ConnectionData.connected is True:
            if cam0_flip_last != DEVICE_control.Cam0_Flip:
                cam0_flip_last = DEVICE_control.Cam0_Flip
                self.Rac_Stream.player_video_flip.set_property("method", DEVICE_control.Cam0_Flip)  # => "rotate"

            if CommunicationFFb is True:
                self.get_speed_and_direction()  # Keyboard input
                self.calculate_MotorPower()     # Set control variables
                self.mouseInput()               # Set mouse Variables

            if AudioBitrate[ConnectionData.Abitrate] != AudioBitrate_last:
                AudioBitrate_last = AudioBitrate[ConnectionData.Abitrate]
                self.Rac_Stream.sender_audio.set_state(Gst.State.READY)
                speaker_last = None

            if ConnectionData.mic is not mic_last:
                mic_last = self.conect_micstream(ConnectionData.mic)

            if ConnectionData.speakers is not speaker_last:
                speaker_last = self.conect_speakerstream(ConnectionData.speakers)

            if ConnectionData.display != display_last:
                if ConnectionData.display == True:
                    warmup -= 1
                    if warmup == 0:
                        warmup = 30
                        display_last = self.start_display_stream(ConnectionData.display)
                else:
                    display_last = self.start_display_stream(ConnectionData.display)

            if ConnectionData.resolution != resolution_last and self.FxQueue.empty() is True:
                resolution_last = ConnectionData.resolution

                self.FxMode  = 0
                self.FxValue = ConnectionData.resolution

                cam0_restart = bool(ConnectionData.resolution)
                if ConnectionData.resolution > 0:
                    Console.print("Requesting mode", ConnectionData.resolution, end='...')
                else:
                    Console.print("Pausing Video Stream")
                self.connect_camstream(False)

            if cam0_restart is True:
                if ConnectionData.Protocol == TCP:
                    if ConnectionData.resolution == self.Streaming_mode:
                        Console.print("OK!")
                        cam0_restart = self.connect_camstream(True)
                else:  # UDP connection
                    self.connect_camstream(True)
                    if ConnectionData.resolution == self.Streaming_mode:
                        Console.print("OK!")
                        cam0_restart = False

            if self.check_connection(None) is True:
                self.send_and_receive()

        self.Rac_Stream.player_video.set_state(Gst.State.NULL)
        self.Rac_Stream.player_audio.set_state(Gst.State.NULL)
        self.Rac_Stream.sender_audio.set_state(Gst.State.NULL)
        self.Display_Stream.sender_video.set_state(Gst.State.READY)
        self.Display_Stream.sender_video_sink_udp.set_property('host', 'localhost')
        self.Display_Stream.sender_video_sink_udp.set_property('port', 9999)

        self.close_connection()
        if ConnectionData.display is True:
            self.Display_Stream.sender_video.set_state(Gst.State.PLAYING)

        Console.print("Closing Thread.")
        exit_thread()

    def send_init_string(self, IP_addr):
        initstr = chr(ConnectionData.Protocol + 48) + chr(ConnectionData.Vcodec + 48) + chr(ConnectionData.TestMode + 48)  # Add 48(ASCII) to show integer in the log.
        ipint_list = map(int, findall('\d+', IP_addr))
        for ipint in ipint_list:
            initstr += chr(ipint)

        initstr.ljust(CLIMSGLEN - 2, chr(10))
        if Debug > 0:
            Console.print(">>> init message sent:", initstr)

        self.transmit_message(initstr)

    def send_and_receive(self):
        if ConnectionData.speed != "HALT":  # Todo

            request  = self.encode_message(self.FxMode, self.FxValue)

            checksum = self.transmit_message(request)

            if checksum is None:
                ConnectionData.connErr += 1
                if ConnectionData.connErr > RETRY_LIMIT:
                    ConnectionData.connErr = 0
                    ConnectionData.connected = False
                return
            else:
                ConnectionData.connErr = 0

            ###### Communication Clock! #####################
            time.sleep(RESP_DELAY)      # Wait for response #
            #################################################

            response = self.receive_message(RECMSGLEN)

            if response:
                if checksum == ord(response[0]):    # ************* MESSAGE CONFIRMED ******************
                    self.Streaming_mode = self.decode_message(response)
                    ConnectionData.motor_ACK = ConnectionData.motor_Power
                    if self.FxQueue.empty() is False:
                        FxMask = self.FxQueue.get()
                        # print("FXmode/FXvalue", self.FXmode, self.FXvalue)
                    else:
                        FxMask = (255, 0)
                    self.FxMode = int(FxMask[0])
                    self.FxValue = int(FxMask[1])
                else:
                    Console.print("Bad chksum:", checksum, ord(response[0]))
                if Debug > 1:
                    Console.print("CheckSum Sent/Received:", checksum, ord(response[0]))
        else:
# ToDo:
            self.transmit_message("HALTHALTHALT")
            ConnectionData.connected = False

    ###############################################################################
    ################   CONN LOOP END   ############################################
    ###############################################################################

    def start_display_stream(self, Connect):
        self.run_camera()
        if self.Display_Stream is not None:
            if Connect is True:
                retmsg = self.Display_Stream.sender_video.set_state(Gst.State.PLAYING)
            else:
                retmsg = self.Display_Stream.sender_video.set_state(Gst.State.READY)
        else:
            print("self.Display_Stream is None")
            return not Connect

        if retmsg == Gst.StateChangeReturn.FAILURE:
            return not Connect
        else:
            return Connect

    def connect_camstream(self, Connect):
        if Connect is True:
            time.sleep(0.1)
            retmsg = self.Rac_Stream.player_video.set_state(Gst.State.PLAYING)
        else:
            retmsg = self.Rac_Stream.player_video.set_state(Gst.State.NULL)

        if retmsg == Gst.StateChangeReturn.FAILURE:
            return True
        else:
            return False

    def conect_micstream(self, Connect):
        if Connect is True:
            retmsg = self.Rac_Stream.player_audio.set_state(Gst.State.PLAYING)
        else:
            retmsg = self.Rac_Stream.player_audio.set_state(Gst.State.READY)

        if retmsg == Gst.StateChangeReturn.FAILURE:
            retmsg = "AUDIO CONNECTION ERROR: Unable to set the pipeline to the playing state."
            success = not Connect
        else:
            retmsg = ""
            success = Connect

        if Debug > 1 and retmsg:
            Console.print(retmsg)
        return success

    def conect_speakerstream(self, Connect):
        if Connect is True:
            Console.print(" Speaker requested rate:", AudioBitrate[ConnectionData.Abitrate])
            caps = Gst.Caps.from_string("audio/x-raw, rate=" + AudioBitrate[ConnectionData.Abitrate].__str__())
            self.Rac_Stream.sender_audio_capsfilter.set_property("caps", caps)

            retmsg = self.Rac_Stream.sender_audio.set_state(Gst.State.PLAYING)
        else:
            retmsg = self.Rac_Stream.sender_audio.set_state(Gst.State.READY)
            Console.print(" Speaker muted")

        if retmsg == Gst.StateChangeReturn.FAILURE:
            retmsg = "AUDIO CONNECTION ERROR: Unable to set the pipeline to the playing state."
            success = not Connect
        else:
            retmsg = ""
            success = Connect

        if Debug > 1 and retmsg:
            Console.print(retmsg)
        return success

    def transmit_message(self, out_str):
        sendstr = str(chr(0) + out_str + chr(10)).encode(Encoding)
        if Debug > 1:
            print("CLISENT[len]: " + len(sendstr).__str__())

        if self.srv is None:
            Console.print("self.srv is NONE!")
            return None
        try:
            self.srv.sendall(sendstr)
        except BrokenPipeError:
            Console.print("transmit_message: BrokenPipeError")
            return None
        except AttributeError:
            Console.print("transmit_message: AttributeError")
            return None
        except OSError:
            Console.print("transmit_message: OSError (server lost)")
            return None

        return calc_checksum(sendstr)

    def receive_message(self, msglen):
        try:
            data = self.srv.recv(msglen).decode(Encoding)
        except ConnectionResetError:
            return None
        except OSError:
            return None

        if Debug > 2:
            Console.print("CLIRCVD[len]: " + len(data).__str__())

        try:
            data_end = data[msglen - 1]
        except IndexError:
            data_end = False
            Console.print(">>>DataIndexError>>>", len(data), data_end)

        if data_end == chr(255):
            ConnectionData.comm_link_idle = 0
            return data
        else:
            return None

    # @staticmethod
    # def update_server_list(combobox_host, port):
    #     list_iter = combobox_host.get_active_iter()
    #     if list_iter is not None:
    #         model = combobox_host.get_model()
    #         Host, Port = model[list_iter][:2]
    #         try:
    #             Port = Port[:Port.index('.')]
    #         except:
    #             Port = Port
    #
    #         # Console.print("Selected: Port=%s, Host=%s" % (int(Port), Host))
    #     else:
    #         entry = combobox_host.get_child()
    #         combobox_host.prepend(port.__str__(), entry.get_text())
    #         combobox_host.set_active(0)
    #
    #         Console.print("New entry: %s" % entry.get_text())
    #         Console.print("New port: %s" % port.__str__())
    #
    # def HostList_get(self, model, HostToFind):
    #     HostList = []
    #     for iter_x in range(0, model.iter_n_children()):
    #         if HostToFind is None:
    #             HostList.append(model[iter_x][0] + ":" + model[iter_x][1])
    #         else:
    #             if model[iter_x][0] == HostToFind:
    #                 return iter_x
    #
    #     if HostToFind is None:
    #         Console.print("HostList_str: [%d]" % model.iter_n_children(), HostList)
    #         return HostList
    #     else:
    #         return False
    #
    # @staticmethod
    # def load_HostList(combobox_host, HostList_str):
    #     x = 0
    #     for HostName in HostList_str:
    #         Host = HostName.split(":")[0]
    #         Port = HostName.split(":")[1]
    #         # Ssh  = HostName.split(":")[2]
    #         combobox_host.insert(x, Port, Host)
    #         x += 1

    @staticmethod
    def decode_message(resp):
        # checksum  - transmission checksum
        # Motor_PWR - power delivered to motors
        # Motor_RPM - Motor rotations
        # CheckSum = ord(resp[0])
        dataint = list()
        dataint.append(None)
        for xcr in range(1, 11):
            if ord(resp[xcr]) == 252:
                dataint.append(17)
            elif ord(resp[xcr]) == 253:
                dataint.append(19)
            else:
                dataint.append(ord(resp[xcr]))

        ConnectionData.motor_PWR[RIGHT] = dataint[1]                                 #2
        ConnectionData.motor_PWR[LEFT]  = dataint[2]                                 #3
        ConnectionData.motor_RPM[RIGHT] = dataint[3]                                 #4
        ConnectionData.motor_RPM[LEFT]  = dataint[4]                                 #5
        curr_sensor = 0.0048 * (dataint[5] * 250 + dataint[6])                       #6,7
        ConnectionData.current          = (2.48 - curr_sensor) * 5
        ConnectionData.voltage          = 0.0157 * (dataint[7] * 250 + dataint[8]) - 0.95  #8,9
        ConnectionData.distanceS1       = int((dataint[9] * 250 + dataint[10]) / 58)  #10,11

        CntrlMask1 = ord(resp[11])                                                  #12
        CntrlMask2 = ord(resp[12])                                                  #13
        ConnectionData.coreTemp = ord(resp[14]) * 0.5                               #15

        Streaming_mode = CntrlMask2

        return Streaming_mode

    @staticmethod
    def encode_message(FXmode, FXvalue):
        CntrlMask1 = 0
        for idx, x in enumerate([ConnectionData.AutoMode, ConnectionData.light, ConnectionData.speakers, ConnectionData.mic,
                                 ConnectionData.display, ConnectionData.laser, 0, 0]):
            CntrlMask1 |= (x << idx)

        BitrateMask  = 100 * ConnectionData.Abitrate + 10 * ConnectionData.Vbitrate + ConnectionData.Framerate

        # convert 16-bit values to 2 x 8-bit
        FxVal0 = int(FXvalue / 256)
        FxVal1 = FXvalue % 256

        reqMsgVal = list()
        reqMsgVal.append(ConnectionData.motor_Power[RIGHT] + 50)     # 1
        reqMsgVal.append(ConnectionData.motor_Power[LEFT] + 50)      # 2
        reqMsgVal.append(ConnectionData.camPosition[X_AXIS])         # 3
        reqMsgVal.append(ConnectionData.camPosition[Y_AXIS])         # 4
        reqMsgVal.append(CntrlMask1)                            # 5
        reqMsgVal.append(FXmode)                                # 6
        reqMsgVal.append(FxVal0)                                # 7
        reqMsgVal.append(FxVal1)                                # 8
        reqMsgVal.append(BitrateMask)                           # 9
        reqMsgVal.append(0)                                     # 10

        requestMsg = ""
        for i in range(10):
            requestMsg += chr(reqMsgVal[i])

        if Debug == 2:
            Console.print("requestMsg", requestMsg)

        return requestMsg

    @staticmethod
    def get_speed_and_direction():

        if KEY_control.Down is True:
            if ConnectionData.speed > -MAX_SPEED:
                ConnectionData.speed -= ACCELERATION

        if KEY_control.Up is True:
            if ConnectionData.speed < MAX_SPEED:
                ConnectionData.speed += ACCELERATION

        if KEY_control.Left is True:
            if ConnectionData.direction > -MAX_SPEED:
                ConnectionData.direction -= ACCELERATION
            else:
                ConnectionData.direction = MAX_SPEED - ACCELERATION

        if KEY_control.Right is True:
            if ConnectionData.direction < MAX_SPEED:
                ConnectionData.direction += ACCELERATION
            else:
                ConnectionData.direction = -MAX_SPEED + ACCELERATION

        return ConnectionData.speed, ConnectionData.direction

    @staticmethod
    def calculate_MotorPower():
        if -MAX_SPEED/2 < ConnectionData.direction < MAX_SPEED/2:
            direction = ConnectionData.direction
        else:
            offset = MAX_SPEED * (ConnectionData.direction / abs(ConnectionData.direction))
            direction = (-ConnectionData.direction + offset)

        ConnectionData.motor_Power = [int(ConnectionData.speed - direction), int(ConnectionData.speed + direction)]
        return ConnectionData.motor_Power

    @staticmethod
    def mouseInput():
        return ConnectionData.camPosition


class Console:
    if CONSOLE_GUI is True:
        TextQueue = queue.Queue()

    def __init__(self):
        pass

    @staticmethod
    def print(*args, **kwargs):
        if CONSOLE_GUI is True:
            l_args = list(args)
            if 'end' in kwargs:
                l_args.append(str(kwargs['end']))
            else:
                l_args.append("\n")

            Console.TextQueue.put(tuple(l_args))
        else:
            print(args, kwargs)

    def display_message(self, Console):
        if not CONSOLE_GUI:
            return

        TextBuffer = Console.get_buffer()
        if not self.TextQueue.empty():
            Text = self.TextQueue.get()
            for cText in Text:
                TextBuffer.insert_at_cursor(str(cText) + " ")

                Console.scroll_mark_onscreen(TextBuffer.get_insert())
