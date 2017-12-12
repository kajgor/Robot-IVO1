import datetime
import socket
import queue
import time
import gi

gi.require_version('Gst', '1.0')
gi.require_version('Gdk', '3.0')
gi.require_version('GstVideo', '1.0')
from gi.repository import Gst, GstVideo, Gdk, GdkPixbuf

from sshtunnel import SSHTunnelForwarder
from paramiko import RSAKey
from cairo import ImageSurface
from math import pi
from re import findall
from _thread import *
from Common_vars import *
from Client_vars import *

Gst.init(None)


class MainLoop:
    ###############################################################################
    ################   MAIN LOOP START   ##########################################
    ###############################################################################
    def __init__(self, GUI):
        self.counter = 0
        self.GUI = GUI
        self.Console = Console()
        self.TextView_Log = self.GUI.TextView_Log
        self.last_MouseButtonR = False
        self.DispAvgVal = [0, 0]

    def on_timer(self):
        if COMM_vars.connected:
            self.counter += .05

        if COMM_vars.comm_link_idle > COMM_IDLE:
            self.GUI.Spinner_connection.stop()
            COMM_vars.comm_link_idle = COMM_IDLE  # Do not need to increase counter anymore
        else:
            self.GUI.Spinner_connection.start()

        # Idle timer for checking the link
        COMM_vars.comm_link_idle += 1
        if KEY_control.MouseBtn[RIGHT] is not self.last_MouseButtonR:
            self.GUI.Menu_CamOptions.popup(None, None, None, None, Gdk.BUTTON_SECONDARY, KEY_control.time)
            self.last_MouseButtonR = KEY_control.MouseBtn[RIGHT]

        # Any update tasks would go here (moving sprites, advancing animation frames etc.)
        self.UpdateControlData()
        self.UpdateMonitorData()
        self.Console.display_message(self.TextView_Log)

        self.GUI.StatusBar2.push(self.GUI.context_id2, str(datetime.timedelta(seconds=int(self.counter))))
        self.GUI.DrawingArea_control.queue_draw()

        if COMM_vars.connected is True:
            if CommunicationFFb is False:
                RacUio.get_speed_and_direction()  # Keyboard input
                RacUio.calculate_MotorPower()
                RacUio.mouseInput()               # Mouse input

        else:
            if self.GUI.ToggleButton_connect.get_active() is True:
                self.GUI.ToggleButton_connect.set_active(False)
                # self.GUI.on_ToggleButton_Connect_toggled(self.GUI.ToggleButton_Connect)

        return True

    def UpdateMonitorData(self):
        self.GUI.LabelRpmL.set_text(COMM_vars.motor_RPM[LEFT].__str__())
        self.GUI.LabelRpmR.set_text(COMM_vars.motor_RPM[RIGHT].__str__())
        self.GUI.LabelPowerL.set_text(COMM_vars.motor_PWR[LEFT].__str__())
        self.GUI.LabelPowerR.set_text(COMM_vars.motor_PWR[RIGHT].__str__())
        self.GUI.LabelRpmReqL.set_text(COMM_vars.motor_Power[LEFT].__str__())
        self.GUI.LabelRpmReqR.set_text(COMM_vars.motor_Power[RIGHT].__str__())
        self.GUI.LabelRpmAckL.set_text(COMM_vars.motor_ACK[LEFT].__str__())
        self.GUI.LabelRpmAckR.set_text(COMM_vars.motor_ACK[RIGHT].__str__())
        self.GUI.LabelCamPosH.set_text(COMM_vars.camPosition[X_AXIS].__str__())
        self.GUI.LabelCamPosV.set_text(COMM_vars.camPosition[Y_AXIS].__str__())

        self.GUI.LabelCoreTemp.set_text("{:.2f}".format(COMM_vars.coreTemp).__str__())
        self.GUI.LabelBattV.set_text("{:.2f}".format(COMM_vars.voltage).__str__())
        self.GUI.LabelPowerA.set_text("{:.2f}".format(COMM_vars.current).__str__())
        self.GUI.LabelS1Dist.set_text(COMM_vars.distanceS1.__str__())

        return

    def UpdateControlData(self):
        self.DispAvgVal[0] = (self.DispAvgVal[0] * 4 + COMM_vars.voltage) / 5
        self.DispAvgVal[1] = (self.DispAvgVal[1] * 4 + COMM_vars.current) / 5
        self.GUI.LevelBar_Voltage.set_value(self.DispAvgVal[0])
        self.GUI.LevelBar_Current.set_value(self.DispAvgVal[1])
        self.GUI.LeverBar_PowerL.set_value(COMM_vars.motor_PWR[LEFT])
        self.GUI.LeverBar_PowerR.set_value(COMM_vars.motor_PWR[RIGHT])
        # print("int(COMM_vars.Current * 10) - 70", int(COMM_vars.Current * 10))

        return
###############################################################################
################   MAIN LOOP END   ############################################
###############################################################################


# noinspection PyPep8Naming
class RacStream:

    # TCP
    # SRV TEST TCP:
    # Source>Capsfilter>Payloader>Sink
    # CLI TEST TCP:
    # Source>Depayloader>Convert>Sink

    # SRV LIVE TCP:
    # Source>Capsfilter>Parser>Rtimer>Encoder>Sink
    # CLI LIVE TCP:
    # Source>Depayloader>Rtimer>Decoder>Convert>VideoFlip>Sink

    # UDP
    # SRV TEST UDP:
    # Source>Capsfilter>Encoder>Rtimer>Sink
    # CLI TEST UDP:
    # Source>Capsfilter>Rtimer>Decoder>Convert>Sink

    # SRV LIVE UDP:
    # Source>Capsfilter>Encoder>Rtimer>Sink
    # CLI LIVE UDP:
    # Source>Capsfilter>Rtimer>Decoder>Convert>VideoFlip>Sink

    Source_test = 0
    Source_h264 = 1

    def __init__(self, Protocol):
        self.Protocol = Protocol
        self.player_video = ([Gst.Pipeline.new("player_test"),
                              Gst.Pipeline.new("player")])

        self.player_audio      = ([Gst.Pipeline.new("player_audio_test"),
                                   Gst.Pipeline.new("player_audio")])

        self.sender_audio      = ([Gst.Pipeline.new("sender_audio_test"),
                                   Gst.Pipeline.new("sender_audio")])

        self.sender_audio_capsfilter = ([Gst.ElementFactory.make("capsfilter", "capsfilter_audio_test"),
                                         Gst.ElementFactory.make("capsfilter", "capsfilter_audio")])

        #   SET VIDEO
        self.video_flip = ([Gst.ElementFactory.make("videoflip", "flip_test"),
                            Gst.ElementFactory.make("videoflip", "flip")])

        self.capsfilter_video = [Gst.ElementFactory.make("capsfilter", "capsfilter_test"),
                                 Gst.ElementFactory.make("capsfilter", "capsfilter")]

        self.depayloader_video = [Gst.ElementFactory.make("gdpdepay", "depayloader_test"),
                                  Gst.ElementFactory.make("gdpdepay", "depayloader")]

        self.convert_video = ([Gst.ElementFactory.make("videoconvert"),
                               Gst.ElementFactory.make("videoconvert")])

        self.rtimer_video = ([Gst.ElementFactory.make("rtph264depay", "rtimer_test"),
                              Gst.ElementFactory.make("rtph264depay", "rtimer")])

        self.decoder_video = ([Gst.ElementFactory.make("avdec_h264", "avdec_test"),
                               Gst.ElementFactory.make("avdec_h264", "avdec")])

        # glimagesink(default)/gtksink/cacasink/autovideosink
        self.sink_video = ([Gst.ElementFactory.make("ximagesink", "sink_test"),
                            Gst.ElementFactory.make("ximagesink", "sink")])

        #   SET AUDIO RECEIVER
        #    udpsrc port=3333 ! application/x-rtp, media=audio, clock-rate=32000, encoding-name=SPEEX, payload=96 !
        #    rtpspeexdepay ! speexdec ! pulsesink sync=false
        self.player_audio_capsfilter = ([Gst.ElementFactory.make("capsfilter", "capsfilter_audio_test"),
                                         Gst.ElementFactory.make("capsfilter", "capsfilter_audio")])

        self.player_audio_depayloader = ([Gst.ElementFactory.make("rtpspeexdepay", "depayloader_audio_test"),
                                          Gst.ElementFactory.make("rtpspeexdepay", "depayloader_audio")])

        self.player_audio_decoder = ([Gst.ElementFactory.make("speexdec", "decoder_audio_test"),
                                      Gst.ElementFactory.make("speexdec", "decoder_audio")])

        # self.convert_audio = ([Gst.ElementFactory.make("audioresample"),
        #                        Gst.ElementFactory.make("audioresample")])
        #
        self.sink_audio = ([Gst.ElementFactory.make("pulsesink", "sink_audio_test"),
                            Gst.ElementFactory.make("pulsesink", "sink_audio")])

        # SET AUDIO SENDER
        self.sender_audio_source = ([Gst.ElementFactory.make("audiotestsrc", "audio-source_test"),
                                     Gst.ElementFactory.make("pulsesrc", "audio-source")])

        self.sender_audio_resample = ([Gst.ElementFactory.make("audioresample", "resample_audio_test"),
                                       Gst.ElementFactory.make("audioresample", "resample_audio")])

        self.sender_audio_encoder = ([Gst.ElementFactory.make("speexenc", "encoder_audio_test"),
                                      Gst.ElementFactory.make("speexenc", "encoder_audio")])

        self.sender_audio_rtimer = ([Gst.ElementFactory.make("rtpspeexpay", "rtimer_audio_test"),
                                     Gst.ElementFactory.make("rtpspeexpay", "rtimer_audio")])

        if self.Protocol == TCP:
            self.source_video = ([Gst.ElementFactory.make("tcpclientsrc", "source_test"),
                                  Gst.ElementFactory.make("tcpclientsrc", "source")])
            self.player_audio_source = ([Gst.ElementFactory.make("tcpclientsrc", "source_audio_test"),
                                         Gst.ElementFactory.make("tcpclientsrc", "source_audio")])
            self.sender_audio_sink = ([Gst.ElementFactory.make("tcpserversink", "sink_audio_test"),
                                       Gst.ElementFactory.make("tcpserversink", "sink_audio")])

            self.sender_audio_sink[self.Source_test].set_property("sync", False)
            self.sender_audio_sink[self.Source_h264].set_property("sync", False)
            self.gst_init_test()
            self.gst_init_live()
        else:
            self.source_video = ([Gst.ElementFactory.make("udpsrc", "source_test_udp"),
                                  Gst.ElementFactory.make("udpsrc", "source_udp")])
            self.player_audio_source = ([Gst.ElementFactory.make("udpsrc", "source_audio_test_udp"),
                                         Gst.ElementFactory.make("udpsrc", "source_audio_udp")])
            self.sender_audio_sink = ([Gst.ElementFactory.make("udpsink", "sink_audio_test_udp"),
                                       Gst.ElementFactory.make("udpsink", "sink_audio_udp")])

            self.sender_audio_sink[self.Source_test].set_property("sync", False)
            self.sender_audio_sink[self.Source_h264].set_property("sync", False)
            self.gst_init_test_udp()
            self.gst_init_live_udp()

        caps = Gst.Caps.from_string("application/x-rtp, encoding-name=H264, payload=96")
        self.capsfilter_video[self.Source_test].set_property("caps", caps)
        self.capsfilter_video[self.Source_h264].set_property("caps", caps)

        # glimagesink(default)/gtksink/cacasink/autovideosink
        self.sink_video[self.Source_test].set_property("sync", False)
        self.sink_video[self.Source_h264].set_property("sync", False)

        caps = Gst.Caps.from_string("application/x-rtp, media=audio, clock-rate=32000, encoding-name=SPEEX, payload=96")
        self.player_audio_capsfilter[self.Source_test].set_property("caps", caps)
        self.player_audio_capsfilter[self.Source_h264].set_property("caps", caps)

        self.sink_audio[self.Source_test].set_property("sync", False)
        self.sink_audio[self.Source_h264].set_property("sync", False)

        if not self.sink_video or not self.source_video:
            print("ERROR! GL elements not available.")
            exit()

        self.sender_audio_source[self.Source_test].set_property("wave", 0)
        self.sender_audio_source[self.Source_h264].set_property("device", MIC0_DEVICE)

    def gst_init_test(self):
        # receive raw test image generated by gstreamer server
        # --- Gstreamer setup begin ---
        self.player_video[self.Source_test].add(self.source_video[self.Source_test])
        self.player_video[self.Source_test].add(self.depayloader_video[self.Source_test])
        self.player_video[self.Source_test].add(self.convert_video[self.Source_test])
        self.player_video[self.Source_test].add(self.sink_video[self.Source_test])

        self.source_video[self.Source_test].link(self.depayloader_video[self.Source_test])
        self.depayloader_video[self.Source_test].link(self.convert_video[self.Source_test])
        self.convert_video[self.Source_test].link(self.sink_video[self.Source_test])

        #    tcpclientsrc host=x.x.x.x port=4552 ! application/x-rtp, media=audio, clock-rate=32000, encoding-name=SPEEX, payload=96 !
        #    rtpspeexdepay ! speexdec ! pulsesink sync=false
        self.player_audio[self.Source_test].add(self.player_audio_source[self.Source_test])
        self.player_audio[self.Source_test].add(self.player_audio_capsfilter[self.Source_test])
        self.player_audio[self.Source_test].add(self.player_audio_depayloader[self.Source_test])
        self.player_audio[self.Source_test].add(self.player_audio_decoder[self.Source_test])
        self.player_audio[self.Source_test].add(self.sink_audio[self.Source_test])

        self.player_audio_source[self.Source_test].link(self.player_audio_capsfilter[self.Source_test])
        self.player_audio_capsfilter[self.Source_test].link(self.player_audio_depayloader[self.Source_test])
        self.player_audio_depayloader[self.Source_test].link(self.player_audio_decoder[self.Source_test])
        self.player_audio_decoder[self.Source_test].link(self.sink_audio[self.Source_test])

        # SENDER (TCP)
        self.sender_audio[self.Source_test].add(self.sender_audio_source[self.Source_test])
        self.sender_audio[self.Source_test].add(self.sender_audio_capsfilter[self.Source_test])
        self.sender_audio[self.Source_test].add(self.sender_audio_resample[self.Source_test])
        self.sender_audio[self.Source_test].add(self.sender_audio_encoder[self.Source_test])
        self.sender_audio[self.Source_test].add(self.sender_audio_rtimer[self.Source_test])
        self.sender_audio[self.Source_test].add(self.sender_audio_sink[self.Source_test])

        self.sender_audio_source[self.Source_test].link(self.sender_audio_capsfilter[self.Source_test])
        self.sender_audio_capsfilter[self.Source_test].link(self.sender_audio_resample[self.Source_test])
        self.sender_audio_resample[self.Source_test].link(self.sender_audio_encoder[self.Source_test])
        self.sender_audio_encoder[self.Source_test].link(self.sender_audio_rtimer[self.Source_test])
        self.sender_audio_rtimer[self.Source_test].link(self.sender_audio_sink[self.Source_test])
        # --- Gstreamer setup end ---

    def gst_init_live(self):
        # --- Gstreamer setup begin ---
        self.player_video[self.Source_h264].add(self.source_video[self.Source_h264])
        self.player_video[self.Source_h264].add(self.depayloader_video[self.Source_h264])
        self.player_video[self.Source_h264].add(self.rtimer_video[self.Source_h264])
        self.player_video[self.Source_h264].add(self.decoder_video[self.Source_h264])
        self.player_video[self.Source_h264].add(self.convert_video[self.Source_h264])
        self.player_video[self.Source_h264].add(self.video_flip[self.Source_h264])
        self.player_video[self.Source_h264].add(self.sink_video[self.Source_h264])

        self.source_video[self.Source_h264].link(self.depayloader_video[self.Source_h264])
        self.depayloader_video[self.Source_h264].link(self.rtimer_video[self.Source_h264])
        self.rtimer_video[self.Source_h264].link(self.decoder_video[self.Source_h264])
        self.decoder_video[self.Source_h264].link(self.convert_video[self.Source_h264])
        self.convert_video[self.Source_h264].link(self.video_flip[self.Source_h264])
        self.video_flip[self.Source_h264].link(self.sink_video[self.Source_h264])

        #    tcpclientsrc host=x.x.x.x port=4552 ! application/x-rtp, media=audio, clock-rate=32000, encoding-name=SPEEX, payload=96 !
        #    rtpspeexdepay ! speexdec ! pulsesink sync=false
        self.player_audio[self.Source_h264].add(self.player_audio_source[self.Source_h264])
        self.player_audio[self.Source_h264].add(self.player_audio_capsfilter[self.Source_h264])
        self.player_audio[self.Source_h264].add(self.player_audio_depayloader[self.Source_h264])
        self.player_audio[self.Source_h264].add(self.player_audio_decoder[self.Source_h264])
        self.player_audio[self.Source_h264].add(self.sink_audio[self.Source_h264])

        self.player_audio_source[self.Source_h264].link(self.player_audio_capsfilter[self.Source_h264])
        self.player_audio_capsfilter[self.Source_h264].link(self.player_audio_depayloader[self.Source_h264])
        self.player_audio_depayloader[self.Source_h264].link(self.player_audio_decoder[self.Source_h264])
        self.player_audio_decoder[self.Source_h264].link(self.sink_audio[self.Source_h264])

        # SENDER (TCP)
        self.sender_audio[self.Source_h264].add(self.sender_audio_source[self.Source_h264])
        self.sender_audio[self.Source_h264].add(self.sender_audio_capsfilter[self.Source_h264])
        self.sender_audio[self.Source_h264].add(self.sender_audio_resample[self.Source_h264])
        self.sender_audio[self.Source_h264].add(self.sender_audio_encoder[self.Source_h264])
        self.sender_audio[self.Source_h264].add(self.sender_audio_rtimer[self.Source_h264])
        self.sender_audio[self.Source_h264].add(self.sender_audio_sink[self.Source_h264])

        self.sender_audio_source[self.Source_h264].link(self.sender_audio_capsfilter[self.Source_h264])
        self.sender_audio_capsfilter[self.Source_h264].link(self.sender_audio_resample[self.Source_h264])
        self.sender_audio_resample[self.Source_h264].link(self.sender_audio_encoder[self.Source_h264])
        self.sender_audio_encoder[self.Source_h264].link(self.sender_audio_rtimer[self.Source_h264])
        self.sender_audio_rtimer[self.Source_h264].link(self.sender_audio_sink[self.Source_h264])
        # --- Gstreamer setup end ---

    def gst_init_test_udp(self):
        # receive raw test image generated by gstreamer server
        # --- Gstreamer setup begin ---
        self.player_video[self.Source_test].add(self.source_video[self.Source_test])
        self.player_video[self.Source_test].add(self.capsfilter_video[self.Source_test])
        self.player_video[self.Source_test].add(self.rtimer_video[self.Source_test])
        self.player_video[self.Source_test].add(self.decoder_video[self.Source_test])
        self.player_video[self.Source_test].add(self.convert_video[self.Source_test])
        self.player_video[self.Source_test].add(self.sink_video[self.Source_test])

        self.source_video[self.Source_test].link(self.capsfilter_video[self.Source_test])
        self.capsfilter_video[self.Source_test].link(self.rtimer_video[self.Source_test])
        self.rtimer_video[self.Source_test].link(self.decoder_video[self.Source_test])
        # self.capsfilter_video[self.Source_test].link(self.decoder_video[self.Source_test])
        self.decoder_video[self.Source_test].link(self.convert_video[self.Source_test])
        self.convert_video[self.Source_test].link(self.sink_video[self.Source_test])

        #    udpsrc port=3333 ! application/x-rtp, media=audio, clock-rate=32000, encoding-name=SPEEX, payload=96 !
        #    rtpspeexdepay ! speexdec ! pulsesink sync=false
        self.player_audio[self.Source_test].add(self.player_audio_source[self.Source_test])
        self.player_audio[self.Source_test].add(self.player_audio_capsfilter[self.Source_test])
        self.player_audio[self.Source_test].add(self.player_audio_depayloader[self.Source_test])
        self.player_audio[self.Source_test].add(self.player_audio_decoder[self.Source_test])
        self.player_audio[self.Source_test].add(self.sink_audio[self.Source_test])

        self.player_audio_source[self.Source_test].link(self.player_audio_capsfilter[self.Source_test])
        self.player_audio_capsfilter[self.Source_test].link(self.player_audio_depayloader[self.Source_test])
        self.player_audio_depayloader[self.Source_test].link(self.player_audio_decoder[self.Source_test])
        self.player_audio_decoder[self.Source_test].link(self.sink_audio[self.Source_test])

        # SENDER (UDP)
        self.sender_audio[self.Source_test].add(self.sender_audio_source[self.Source_test])
        self.sender_audio[self.Source_test].add(self.sender_audio_capsfilter[self.Source_test])
        self.sender_audio[self.Source_test].add(self.sender_audio_resample[self.Source_test])
        self.sender_audio[self.Source_test].add(self.sender_audio_encoder[self.Source_test])
        self.sender_audio[self.Source_test].add(self.sender_audio_rtimer[self.Source_test])
        self.sender_audio[self.Source_test].add(self.sender_audio_sink[self.Source_test])

        self.sender_audio_source[self.Source_test].link(self.sender_audio_capsfilter[self.Source_test])
        self.sender_audio_capsfilter[self.Source_test].link(self.sender_audio_resample[self.Source_test])
        self.sender_audio_resample[self.Source_test].link(self.sender_audio_encoder[self.Source_test])
        self.sender_audio_encoder[self.Source_test].link(self.sender_audio_rtimer[self.Source_test])
        self.sender_audio_rtimer[self.Source_test].link(self.sender_audio_sink[self.Source_test])
        # --- Gstreamer setup end ---

    def gst_init_live_udp(self):
        # --- Gstreamer setup begin ---
        self.player_video[self.Source_h264].add(self.source_video[self.Source_h264])
        self.player_video[self.Source_h264].add(self.capsfilter_video[self.Source_h264])
        self.player_video[self.Source_h264].add(self.rtimer_video[self.Source_h264])
        self.player_video[self.Source_h264].add(self.decoder_video[self.Source_h264])
        self.player_video[self.Source_h264].add(self.convert_video[self.Source_h264])
        self.player_video[self.Source_h264].add(self.video_flip[self.Source_h264])
        self.player_video[self.Source_h264].add(self.sink_video[self.Source_h264])

        self.source_video[self.Source_h264].link(self.capsfilter_video[self.Source_h264])
        self.capsfilter_video[self.Source_h264].link(self.rtimer_video[self.Source_h264])
        self.rtimer_video[self.Source_h264].link(self.decoder_video[self.Source_h264])
        self.decoder_video[self.Source_h264].link(self.convert_video[self.Source_h264])
        self.convert_video[self.Source_h264].link(self.video_flip[self.Source_h264])
        self.video_flip[self.Source_h264].link(self.sink_video[self.Source_h264])

        #    udpsrc port=3333 ! application/x-rtp, media=audio, clock-rate=32000, encoding-name=SPEEX, payload=96 !
        #    rtpspeexdepay ! speexdec ! pulsesink sync=false
        # PLAYER
        self.player_audio[self.Source_h264].add(self.player_audio_source[self.Source_h264])
        self.player_audio[self.Source_h264].add(self.player_audio_capsfilter[self.Source_h264])
        self.player_audio[self.Source_h264].add(self.player_audio_depayloader[self.Source_h264])
        self.player_audio[self.Source_h264].add(self.player_audio_decoder[self.Source_h264])
        self.player_audio[self.Source_h264].add(self.sink_audio[self.Source_h264])

        self.player_audio_source[self.Source_h264].link(self.player_audio_capsfilter[self.Source_h264])
        self.player_audio_capsfilter[self.Source_h264].link(self.player_audio_depayloader[self.Source_h264])
        self.player_audio_depayloader[self.Source_h264].link(self.player_audio_decoder[self.Source_h264])
        self.player_audio_decoder[self.Source_h264].link(self.sink_audio[self.Source_h264])

        # SENDER (UDP)
        self.sender_audio[self.Source_h264].add(self.sender_audio_source[self.Source_h264])
        self.sender_audio[self.Source_h264].add(self.sender_audio_capsfilter[self.Source_h264])
        self.sender_audio[self.Source_h264].add(self.sender_audio_resample[self.Source_h264])
        self.sender_audio[self.Source_h264].add(self.sender_audio_encoder[self.Source_h264])
        self.sender_audio[self.Source_h264].add(self.sender_audio_rtimer[self.Source_h264])
        self.sender_audio[self.Source_h264].add(self.sender_audio_sink[self.Source_h264])

        self.sender_audio_source[self.Source_h264].link(self.sender_audio_capsfilter[self.Source_h264])
        self.sender_audio_capsfilter[self.Source_h264].link(self.sender_audio_resample[self.Source_h264])
        self.sender_audio_resample[self.Source_h264].link(self.sender_audio_encoder[self.Source_h264])
        self.sender_audio_encoder[self.Source_h264].link(self.sender_audio_rtimer[self.Source_h264])
        self.sender_audio_rtimer[self.Source_h264].link(self.sender_audio_sink[self.Source_h264])
        # --- Gstreamer setup end ---


class RacDisplay:
    background_control = ImageSurface.create_from_png(Paths.background_file)

    def draw_arrow(self, message):
        message.set_source_surface(self.background_control, 0, 0)
        message.paint()

        message.set_line_width(1)
        message.translate(90, 81)

        if COMM_vars.speed >= 0:
            message.rotate(COMM_vars.direction / (pi * 5))
        else:
            message.rotate((COMM_vars.direction + MAX_SPEED) / (pi * 5))

        # Direction arrow
        message.set_source_rgb(0.25, 0.25, 0.25)
        for i in range(4):
            message.line_to(arrow.points[i][0], arrow.points[i][1])
        message.fill()
        message.set_source_rgb(0, 0.75, 0.75)
        for i in range(5):
            message.line_to(arrow.points[i][0], arrow.points[i][1])
        message.stroke()

        # Speed arrow (REQ)
        message.set_source_rgb(abs(COMM_vars.speed/MAX_SPEED), 1 - abs(COMM_vars.speed/MAX_SPEED), 0)
        message.line_to(arrow.points[0][0], arrow.points[0][1] + 60 - abs((COMM_vars.speed / MAX_SPEED) * 50))
        for i in range(1, 4):
                message.line_to(arrow.points[i][0], arrow.points[i][1])
        message.fill()

        # Speed arrow (ACK)
        message.set_source_rgb(0, 0.75, 0.75)
        speed_ACK = abs(COMM_vars.motor_ACK[0] + COMM_vars.motor_ACK[1]) * 0.5
        message.line_to(arrow.points[1][0], arrow.points[1][1])
        message.line_to(arrow.points[0][0], arrow.points[0][1] + 60 - speed_ACK)
        message.line_to(arrow.points[3][0], arrow.points[3][1])
        message.stroke()

    def on_message(self, message):
        msgtype = message.type
        if msgtype == Gst.MessageType.EOS:
            # RacStream.player_video[RacConnection.Video_Mode].set_state(Gst.State.NULL)
            if Debug > 1:
                # self.statusbar.push(self.context_id, "VIDEO CONNECTION EOS: SIGNAL LOST")
                Console.print ("EOS: SIGNAL LOST")
            return "VIDEO CONNECTION EOS: SIGNAL LOST"
        elif msgtype == Gst.MessageType.ERROR:
            # RacStream.player_video[RacConnection.Video_Mode].set_state(Gst.State.NULL)
            err, debug = message.parse_error()
            debug_s = debug.split("\n")
            if Debug > 0:
                # self.statusbar.push(self.context_id, debug_s[debug_s.__len__() - 1])
                Console.print ("ERROR:", debug_s)
            return debug_s[debug_s.__len__() - 1]
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
    Video_Mode = 0
    Video_Codec = 0
    FXmode = 0
    FXvalue = 0
    Host = None
    Port_Comm = None
    Last_Active = 0
    Rac_Display = RacDisplay()
    CtrlQueue = queue.Queue()

    def __init__(self, CAMXPROP):
        self.CAMXPROP       = CAMXPROP
        self.Rac_Stream     = None
        self.Streaming_mode = 0
        self.FXmode_sent    = 0

    def draw_arrow(self, message):
        self.Rac_Display.draw_arrow(message)

    def on_cam_message(self, bus, message):
        retmsg = self.Rac_Display.on_message(message)
        if retmsg is not None:
            print("retmsg:", retmsg)
            # self.ToggleButton_connect.set_active(False)
            # self.StatusBar.push(self.context_id, retmsg)

    def on_cam_sync_message(self, bus, message):
        self.Rac_Display.on_sync_message(message, self.CAMXPROP)

    def open_ssh_tunnel(self, Host, Port, rsa_file, rsa_password, username, remote_host, compression):
        if compression == 0:  # Auto
            Compression = not(bool(self.Video_Mode))
        elif compression == 1:
            Compression = True
        else:
            Compression = False

        Console.print("Tunneling mode started\n [Compression is %s]" % Compression)
        self.tunnel = SSHTunnelForwarder(
            (Host, Port),  # jump server address
            ssh_username=username,
            ssh_pkey=RSAKey.from_private_key_file(rsa_file, password=rsa_password),
            remote_bind_addresses=[(remote_host, Port_COMM), (remote_host, Port_CAM0)],  # storage box ip address
            local_bind_addresses=[('localhost', Port_COMM), ('127.0.0.1', Port_CAM0)],
            compression=Compression)

        try:
            self.tunnel.start()
            Console.print("SSH tunnels opened on ports:\n   ", self.tunnel.local_bind_ports)
            # self.tunnel.check_tunnels()
        except:
            Console.print("SSH Connection Error!!!")
            return None, None

        return "localhost", Port_COMM

    def establish_connection(self, Host, Port, Protocol):
        self.Rac_Stream = RacStream(Protocol)

        bus = self.Rac_Stream.player_video[False].get_bus()
        bus.add_signal_watch()
        bus.enable_sync_message_emission()
        bus.connect("message", self.on_cam_message)
        bus.connect("sync-message::element", self.on_cam_sync_message)

        bus_test = self.Rac_Stream.player_video[True].get_bus()
        bus_test.add_signal_watch()
        bus_test.enable_sync_message_emission()
        bus_test.connect("message", self.on_cam_message)
        bus_test.connect("sync-message::element", self.on_cam_sync_message)

        Console.print("Establishing connection with \n %s on port"  % Host, Port)

        # Gstreamer setup start
        if self.Rac_Stream.Protocol == TCP:
            self.Rac_Stream.source_video[self.Video_Mode].set_property("host", Host)
            self.Rac_Stream.player_audio_source[self.Video_Mode].set_property("host", Host)

        self.Rac_Stream.source_video[self.Video_Mode].set_property("port", Port_CAM0)
        self.Rac_Stream.player_audio_source[self.Video_Mode].set_property("port", Port_MIC0)
        self.Rac_Stream.sender_audio_sink[self.Video_Mode].set_property("host", Host)
        self.Rac_Stream.sender_audio_sink[self.Video_Mode].set_property("port", Port_SPK0)
        # Gstreamer setup end

        start_new_thread(self.connection_thread, (Host, Port))
        time.sleep(0.25)

        l_iter = 0
        while COMM_vars.connected is False and l_iter < 10:
            l_iter += 1
            Console.print("Retry:", l_iter)
            time.sleep(0.25)

        if COMM_vars.connected is True:
            retmsg = "Server connected! " + self.srv.getsockname().__str__()
            # if Debug > 2:
            Console.print(retmsg)
        else:
            retmsg = "Connection Error [" + (Host, Port).__str__() + "]"
            # if Debug > 0:
            Console.print(retmsg)

        return COMM_vars.connected, retmsg

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

        COMM_vars.connected = False
        # if Debug > 1:
        Console.print("Connection closed.")
        # print("Connection closed.")

    # @staticmethod
    def check_connection(self, HostIp):
        try:
            # status = self.srv.getsockname()
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

        COMM_vars.connected = True
        try:
            self.srv.connect(server_address)
        except ConnectionResetError:
            COMM_vars.connected = False
            Console.print("Server not responding.")
        except ConnectionRefusedError:
            COMM_vars.connected = False
            Console.print("Server refused connection.")
        except socket.gaierror:
            COMM_vars.connected = False
            Console.print("Invalid protocol.")
        except OSError:
            COMM_vars.connected = False
            Console.print("No route to host.")

        if COMM_vars.connected is True:
            Console.print("Link with", self.srv.getpeername(), "established.")
            time.sleep(1)
            IP_addr = socket.gethostbyname(Host)
            self.send_init_string(IP_addr)

        cam0_restart = False
        resolution_last = None
        AudioBitrate_last = None
        mic_last = not COMM_vars.mic
        speaker_last = not COMM_vars.speakers
        self.Streaming_mode = 0

        while COMM_vars.connected is True:
            self.Rac_Stream.video_flip[self.Video_Mode].set_property("method", CAM0_control.Flip)  # => "rotate"

            if CommunicationFFb is True:
                RacUio.get_speed_and_direction()  # Keyboard input
                RacUio.calculate_MotorPower()     # Set control variables
                RacUio.mouseInput()               # Set mouse Variables

            if AudioBitrate[COMM_vars.Abitrate] != AudioBitrate_last:
                AudioBitrate_last = AudioBitrate[COMM_vars.Abitrate]
                self.Rac_Stream.sender_audio[self.Video_Mode].set_state(Gst.State.READY)
                speaker_last = None

            if COMM_vars.mic is not mic_last:
                mic_last = self.conect_micstream(COMM_vars.mic)

            if COMM_vars.speakers is not speaker_last:
                speaker_last = self.conect_speakerstream(COMM_vars.speakers)

            if COMM_vars.resolution != resolution_last:
                resolution_last = COMM_vars.resolution

                self.FXmode = 0
                self.FXvalue = COMM_vars.resolution

                cam0_restart = bool(COMM_vars.resolution)
                if COMM_vars.resolution > 0:
                    Console.print("Requesting mode", COMM_vars.resolution, end='...')
                else:
                    Console.print("Pausing Video Stream")
                self.connect_camstream(False)

            # if self.FXmode < 255:
            #     print("*** self.FXmode", self.FXmode)

            if cam0_restart is True:
                if self.Rac_Stream.Protocol == TCP:
                    if COMM_vars.resolution == self.Streaming_mode:
                        Console.print("OK!")
                        cam0_restart = self.connect_camstream(True)
                else:  # UDP connection
                    self.connect_camstream(True)
                    if COMM_vars.resolution == self.Streaming_mode:
                        Console.print("OK!")
                        cam0_restart = False

            if self.check_connection(None) is True:
                self.send_and_receive()
# ToDo:
                if not self.CtrlQueue.empty():
                    OuText = self.CtrlQueue.get()


        self.Rac_Stream.player_video[self.Video_Mode].set_state(Gst.State.NULL)
        self.Rac_Stream.player_audio[self.Video_Mode].set_state(Gst.State.NULL)
        self.Rac_Stream.sender_audio[self.Video_Mode].set_state(Gst.State.NULL)

        self.close_connection()
        Console.print("Closing Thread.")
        exit_thread()

    def send_init_string(self, IP_addr):
        initstr = chr(self.Rac_Stream.Protocol + 48) + chr(self.Video_Codec + 48) + chr(
            self.Video_Mode + 48)  # Add 48(ASCII) to show integer in the log.
        ipint_list = map(int, findall('\d+', IP_addr))
        for ipint in ipint_list:
            initstr += chr(ipint)

        initstr.ljust(CLIMSGLEN - 2, chr(10))
        if Debug > 0:
            Console.print(">>> init message sent:", initstr)

        self.transmit_message(initstr)

    def send_and_receive(self):
        if COMM_vars.speed != "HALT":
            request  = self.encode_message(self.FXmode, self.FXvalue)
            checksum = self.transmit_message(request)
            if checksum is None:
                COMM_vars.connErr += 1
                if COMM_vars.connErr > RETRY_LIMIT:
                    COMM_vars.connErr = 0
                    COMM_vars.connected = False
                return
            else:
                COMM_vars.connErr = 0

            time.sleep(RESP_DELAY)
            resp = self.receive_message(RECMSGLEN)

            if resp is not None:
                if checksum == ord(resp[0]): # ************* MESSAGE CONFIRMED ******************
                    self.Streaming_mode = self.decode_message(resp)
                    COMM_vars.motor_ACK = COMM_vars.motor_Power
                    if self.FXmode == self.FXmode_sent < 255:
                        self.FXmode = 255

                    self.FXmode_sent = self.FXmode
                else:
                    Console.print("Bad chksum:", checksum, ord(resp[0]))
                if Debug > 1:
                    Console.print("CheckSum Sent/Received:", checksum, ord(resp[0]))
        else:
# ToDo:
            self.transmit_message("HALTHALTHALT")
            COMM_vars.connected = False

    ###############################################################################
    ################   CONN LOOP END   ############################################
    ###############################################################################

    def connect_camstream(self, Connect):
        if Connect is True:
            time.sleep(0.1)
            retmsg = self.Rac_Stream.player_video[self.Video_Mode].set_state(Gst.State.PLAYING)
        else:
            retmsg = self.Rac_Stream.player_video[self.Video_Mode].set_state(Gst.State.NULL)

        if retmsg == Gst.StateChangeReturn.FAILURE:
            return True
        else:
            return False

    def conect_micstream(self, Connect):
        if Connect is True:
            retmsg = self.Rac_Stream.player_audio[self.Video_Mode].set_state(Gst.State.PLAYING)
        else:
            retmsg = self.Rac_Stream.player_audio[self.Video_Mode].set_state(Gst.State.READY)

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
            Console.print(" Speaker requested rate:", AudioBitrate[COMM_vars.Abitrate])
            caps = Gst.Caps.from_string("audio/x-raw, rate=" + AudioBitrate[COMM_vars.Abitrate])
            self.Rac_Stream.sender_audio_capsfilter[self.Video_Mode].set_property("caps", caps)

            retmsg = self.Rac_Stream.sender_audio[self.Video_Mode].set_state(Gst.State.PLAYING)
        else:
            retmsg = self.Rac_Stream.sender_audio[self.Video_Mode].set_state(Gst.State.READY)
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
        # print("CLISENT: ", sendstr.__str__())

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
            COMM_vars.comm_link_idle = 0
            return data
        else:
            return None

    @staticmethod
    def update_server_list(combobox_host, port):
        list_iter = combobox_host.get_active_iter()
        if list_iter is not None:
            model = combobox_host.get_model()
            Host, Port = model[list_iter][:2]
            try:
                Port = Port[:Port.index('.')]
            except:
                Port = Port

            # Console.print("Selected: Port=%s, Host=%s" % (int(Port), Host))
        else:
            entry = combobox_host.get_child()
            combobox_host.prepend(port.__str__(), entry.get_text())
            combobox_host.set_active(0)

            Console.print("New entry: %s" % entry.get_text())
            Console.print("New port: %s" % port.__str__())

    def HostList_get(self, model, HostToFind):
        HostList = []
        for iter_x in range(0, model.iter_n_children()):
            if HostToFind is None:
                HostList.append(model[iter_x][0] + ":" + model[iter_x][1])
            else:
                if model[iter_x][0] == HostToFind:
                    return iter_x

        if HostToFind is None:
            Console.print("HostList_str: [%d]" % model.iter_n_children(), HostList)
            return HostList
        else:
            return False

    @staticmethod
    def load_HostList(combobox_host, HostList_str):
        x = 0
        for HostName in HostList_str:
            Host = HostName.split(":")[0]
            Port = HostName.split(":")[1]
            # Ssh  = HostName.split(":")[2]
            combobox_host.insert(x, Port, Host)
            x += 1

    @staticmethod
    def decode_message(resp):
        # checksum  - transmission checksum
        # Motor_PWR - power delivered to motors
        # Motor_RPM - Motor rotations
        # CheckSum = ord(resp[0])
        dataint = [None,0,0,0,0,0,0,0,0,0,0]
        for xcr in range(1, 11):
            if ord(resp[xcr]) == 252:
                dataint[xcr] = 17
            elif ord(resp[xcr]) == 253:
                dataint[xcr] = 19
            else:
                dataint[xcr] = ord(resp[xcr])

        COMM_vars.motor_PWR[RIGHT] = dataint[1]                                 #2
        COMM_vars.motor_PWR[LEFT]  = dataint[2]                                 #3
        COMM_vars.motor_RPM[RIGHT] = dataint[3]                                 #4
        COMM_vars.motor_RPM[LEFT]  = dataint[4]                                 #5
        curr_sensor = 0.0048 * (dataint[5] * 250 + dataint[6])                  #6,7
        COMM_vars.current          = (2.5 - curr_sensor) * 5
        COMM_vars.voltage          = 0.012 * (dataint[7] * 250 + dataint[8])    #8,9
        COMM_vars.distanceS1       = int((dataint[9] * 250 + dataint[10]) / 58) #10,11

        CntrlMask1 = ord(resp[11])                                              #12
        CntrlMask2 = ord(resp[12])                                              #13
        COMM_vars.coreTemp = ord(resp[14]) * 0.5                                #15

        Streaming_mode = CntrlMask2

        return Streaming_mode

    @staticmethod
    def encode_message(FXmode, FXvalue):
        CntrlMask1 = 0
        for idx, x in enumerate([COMM_vars.AutoMode, COMM_vars.light, COMM_vars.speakers, COMM_vars.mic,
                                 COMM_vars.display, COMM_vars.laser, 0, 0]):
            CntrlMask1 |= (x << idx)

        # COMM_vars.Framerate = 3
        BitrateMask  = 100 * COMM_vars.Abitrate + 10 * COMM_vars.Vbitrate + COMM_vars.Framerate
        # VideoCtlMask = 10 * FXmode + COMM_vars.resolution

        FxVal0 = int(FXvalue / 256)
        FxVal1 = FXvalue % 256

        reqMsgVal = []
        reqMsgVal.append(COMM_vars.motor_Power[RIGHT] + 50)     # 1
        reqMsgVal.append(COMM_vars.motor_Power[LEFT] + 50)      # 2
        reqMsgVal.append(COMM_vars.camPosition[X_AXIS])         # 3
        reqMsgVal.append(COMM_vars.camPosition[Y_AXIS])         # 4
        reqMsgVal.append(CntrlMask1)                            # 5
        reqMsgVal.append(FXmode)                                # 6
        reqMsgVal.append(FxVal0)                                # 7
        reqMsgVal.append(FxVal1)                                # 8
        reqMsgVal.append(BitrateMask)                           # 9
        reqMsgVal.append(0)                                     # 10

        requestMsg = ""
        # Convert chr(17) & chr(19) to chr(252) & chr(253) respectively
        # as above characters break Arduino serial communication
        for i in range(4):
            if reqMsgVal[i] == 17:
                requestMsg += chr(252)
            elif reqMsgVal[i] == 19:
                requestMsg += chr(253)
            else:
                requestMsg += chr(reqMsgVal[i])

        for i in range(4, 10):
            requestMsg += chr(reqMsgVal[i])

        if Debug == 2:
            Console.print("requestMsg", requestMsg)

        return requestMsg


class RacUio:
    def on_key_press(self, event):
        keybuffer_set(event, True)
        return True

    def on_key_release(self, event):
        key_name = keybuffer_set(event, False)
        return key_name

    def on_mouse_press(self, mouse_event):
        mousebuffer_set(mouse_event, True)

    def on_mouse_release(self, mouse_event):
        mousebuffer_set(mouse_event, False)

    def on_motion_notify(self, mouse_event):
        mouseX = int(mouse_event.x)
        mouseY = int(mouse_event.y)
        if KEY_control.MouseBtn[LEFT] is True:
            tmp = (KEY_control.MouseXY[X_AXIS] - mouseX) / 2
            if abs(tmp) >= 1:
                if COMM_vars.camPosition[X_AXIS] + tmp > MOUSE_MAX[X_AXIS]:
                    COMM_vars.camPosition[X_AXIS] = MOUSE_MAX[X_AXIS]
                elif COMM_vars.camPosition[X_AXIS] + tmp < MOUSE_MIN[X_AXIS]:
                    COMM_vars.camPosition[X_AXIS] = MOUSE_MIN[X_AXIS]
                else:
                    COMM_vars.camPosition[X_AXIS] += int(tmp)

            tmp = (mouseY - KEY_control.MouseXY[Y_AXIS]) / 2
            if abs(tmp) >= 1:
                if COMM_vars.camPosition[Y_AXIS] + tmp > MOUSE_MAX[Y_AXIS]:
                    COMM_vars.camPosition[Y_AXIS] = MOUSE_MAX[Y_AXIS]
                elif COMM_vars.camPosition[Y_AXIS] + tmp < MOUSE_MIN[Y_AXIS]:
                    COMM_vars.camPosition[Y_AXIS] = MOUSE_MIN[Y_AXIS]
                else:
                    COMM_vars.camPosition[Y_AXIS] += int(tmp)

            KEY_control.MouseXY = [mouseX, mouseY]

        # if KEY_control.MouseBtn[RIGHT] is True:
        #     Console.print("KEY_control.MouseXY[right]", KEY_control.MouseXY)

    @staticmethod
    def get_speed_and_direction():

        if KEY_control.Down is True:
            if COMM_vars.speed > -MAX_SPEED:
                COMM_vars.speed -= ACCELERATION

        if KEY_control.Up is True:
            if COMM_vars.speed < MAX_SPEED:
                COMM_vars.speed += ACCELERATION

        if KEY_control.Left is True:
            if COMM_vars.direction > -MAX_SPEED:
                COMM_vars.direction -= ACCELERATION
            else:
                COMM_vars.direction = MAX_SPEED - ACCELERATION

        if KEY_control.Right is True:
            if COMM_vars.direction < MAX_SPEED:
                COMM_vars.direction += ACCELERATION
            else:
                COMM_vars.direction = -MAX_SPEED + ACCELERATION

        return COMM_vars.speed, COMM_vars.direction

    @staticmethod
    def calculate_MotorPower():
        if COMM_vars.direction < MAX_SPEED/2 and COMM_vars.direction > -MAX_SPEED/2:
            direction = COMM_vars.direction
        else:
            offset = MAX_SPEED * (COMM_vars.direction / abs(COMM_vars.direction))
            direction = (-COMM_vars.direction + offset)

        COMM_vars.motor_Power = [int(COMM_vars.speed - direction), int(COMM_vars.speed + direction)]
        return COMM_vars.motor_Power

    @staticmethod
    def mouseInput():
        return COMM_vars.camPosition


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


def keybuffer_set(event, value):
    key_name = Gdk.keyval_name(event.keyval)
    if key_name == "Left" or key_name.replace("A", "a", 1) == "a":
        KEY_control.Left = value

    elif key_name == "Right" or key_name.replace("D", "d", 1) == "d":
        KEY_control.Right = value

    elif key_name == "Up" or key_name.replace("W", "w", 1) == "w":
        KEY_control.Up = value

    elif key_name == "Down" or key_name.replace("S", "s", 1) == "s":
        KEY_control.Down = value

    elif key_name == "space":
        COMM_vars.speed = 0
        COMM_vars.direction = 0
        KEY_control.Space = value

    if event.state is True and Gdk.KEY_Shift_L is not KEY_control.Shift:
        KEY_control.Shift = Gdk.KEY_Shift_L
        Console.print("SHIFT!!!")

    return key_name


def mousebuffer_set(mouse_event, value):
    if mouse_event.button == Gdk.BUTTON_PRIMARY:
        KEY_control.MouseBtn[LEFT] = value
        if value is True:
            KEY_control.MouseXY = [int(mouse_event.x),
                                   int(mouse_event.y)]

    if mouse_event.button == Gdk.BUTTON_SECONDARY:
        KEY_control.time = mouse_event.time
        KEY_control.MouseBtn[RIGHT] = value
