import gi.repository

gi.require_version('Gst', '1.0')
gi.require_version('GstVideo', '1.0')
from gi.repository import Gst, GstVideo, GdkPixbuf

from Media_vars import *
from Client_vars import Debug
from Common_vars import TCP, ConnectionData

Gst.init(None)


class SenderStream:
    sender_video = None
    sender_audio = None

    def __init__(self, Sender_SXID):
        self.Sender_SXID = Sender_SXID

    def set_video_source(self, Proto):
        self.sender_video               = Gst.Pipeline.new("sender_video")

        self.sender_video_source        = Gst.ElementFactory.make("v4l2src", "video-source")
        self.sender_video_testsrc       = Gst.ElementFactory.make("videotestsrc", "test-video-source")

        # glimagesink(default)/gtksink/cacasink/autovideosink/ximagesink(working)
        #   SET VIDEO (SENDER)
        self.sender_video_videorate_udp = Gst.ElementFactory.make("videorate", "vr1")
        self.sender_video_queue_udp     = Gst.ElementFactory.make("queue", "queue1")
        self.sender_video_caps_udp      = Gst.ElementFactory.make("capsfilter", "capsfilter1")
        self.sender_video_convert_udp   = Gst.ElementFactory.make("videoconvert", "vc1")
        self.sender_video_encoder       = Gst.ElementFactory.make(H264_ENC, "encoder_udp")
        self.sender_video_rtimer        = Gst.ElementFactory.make("rtph264pay", "rtimer_udp")
        self.sender_video_sink_udp      = Gst.ElementFactory.make("udpsink", "udp-output")

        self.sender_video_videorate_xv  = Gst.ElementFactory.make("videorate", "vr2")
        self.sender_video_queue_xv      = Gst.ElementFactory.make("queue", "queue2")
        self.sender_video_caps_xv       = Gst.ElementFactory.make("capsfilter", "capsfilter2")
        self.sender_video_convert_xv    = Gst.ElementFactory.make("videoconvert", "vc2")
        self.sender_video_sink_xv       = Gst.ElementFactory.make("xvimagesink", "video-output")

        self.sender_video_tee           = Gst.ElementFactory.make("tee", "tee")

        if ConnectionData.Protocol == TCP:
            # ToDo:
            # self.gst_init_tcp_stream()
            pass
        else:
            self.sender_video_sink_udp.set_property("host", 'localhost')
            self.sender_video_sink_udp.set_property("port", 0)
            self.sender_video_sink_udp.set_property("sync", False)
            caps = "video/x-raw, width=320, height=240, frametrate=15/1"
            self.sender_video_caps_udp.set_property("caps", Gst.Caps.from_string(caps))

        self.sender_video_encoder.set_property("tune", "zerolatency")
        self.sender_video_encoder.set_property("pass", "qual")
        self.sender_video_encoder.set_property("bitrate", 300)
        self.sender_video_encoder.set_property("byte-stream", True)
        self.sender_video_encoder.set_property("b-pyramid", True)

        caps = "video/x-raw, width=320, height=240, frametrate=15/1"
        self.sender_video_caps_xv.set_property("caps", Gst.Caps.from_string(caps))
        self.sender_video_sink_xv.set_property("sync", False)

        self.gst_init_udp_video_stream()

    def link_video_source(self, Flag):
        if Flag is True:
            if DEVICE_control.DEV_Cam0 == "videotestsrc":
                self.sender_video.add(self.sender_video_testsrc)
                self.sender_video_testsrc.link(self.sender_video_tee)
            else:
                self.sender_video.add(self.sender_video_source)
                self.sender_video_source.link(self.sender_video_tee)
        else:
            if DEVICE_control.DEV_Cam0 == "videotestsrc":
                self.sender_video.remove(self.sender_video_testsrc)
            else:
                self.sender_video.remove(self.sender_video_source)

    def set_audio_source(self, Proto):
        self.sender_audio               = Gst.Pipeline.new("sender_audio")
        # SET AUDIO SENDER
        self.sender_audio_testsrc       = Gst.ElementFactory.make("audiotestsrc", "test_source_audio")
        self.sender_audio_source        = Gst.ElementFactory.make("pulsesrc", "local_source_audio")
        self.sender_audio_capsfilter    = Gst.ElementFactory.make("capsfilter", "capsfilter_audio")
        self.sender_audio_resample      = Gst.ElementFactory.make("audioresample", "resample_audio")
        self.sender_audio_encoder       = Gst.ElementFactory.make("speexenc", "encoder_audio")
        self.sender_audio_rtimer        = Gst.ElementFactory.make("rtpspeexpay", "rtimer_audio")

        # ToDo:
        # if ConnectionData.Protocol == TCP:
        #     self.sender_audio_sink = Gst.ElementFactory.make("tcpserversink", "remote_sink_audio")
        # else:
        self.sender_audio_sink          = Gst.ElementFactory.make("udpsink", "remote_sink_audio_udp")

        self.sender_audio_sink.set_property("host", 'localhost')
        self.sender_audio_sink.set_property("port", 0)
        self.sender_audio_sink.set_property("sync", False)

        caps = "audio/x-raw, rate=%i" % AudioBitrate[ConnectionData.Abitrate]
        self.sender_audio_capsfilter.set_property("caps", Gst.Caps.from_string(caps))

        self.gst_init_udp_audio_stream()

    def link_audio_source(self, Flag):
        if Flag is True:
            if DEVICE_control.DEV_AudioIn == "audiotestsrc":
                self.sender_audio.add(self.sender_audio_testsrc)
                self.sender_audio_testsrc.set_property("wave", 0)
                self.sender_audio_testsrc.link(self.sender_audio_capsfilter)
            else:
                AudioInDevice = DEVICE_control.DEV_AudioIn.split(":")[0]
                self.sender_audio.add(self.sender_audio_source)
                self.sender_audio_source.set_property("device", AudioInDevice)
                self.sender_audio_source.link(self.sender_audio_capsfilter)
        else:
            if DEVICE_control.DEV_AudioIn == "audiotestsrc":
                self.sender_audio.remove(self.sender_audio_testsrc)
            else:
                self.sender_audio.remove(self.sender_audio_source)

    def gst_init_tcp_stream(self):
        ####################################################################
        ### Build video pipeline as following:
        ####################################################################
        # SENDER VIDEO(TCP)
        # TdDo
        #
        # SENDER AUDIO(TCP)
        # self.sender_audio.add(self.sender_audio_source)
        self.sender_audio.add(self.sender_audio_capsfilter)
        self.sender_audio.add(self.sender_audio_resample)
        self.sender_audio.add(self.sender_audio_encoder)
        self.sender_audio.add(self.sender_audio_rtimer)
        self.sender_audio.add(self.sender_audio_sink)

        # self.sender_audio_source.link(self.sender_audio_capsfilter)
        self.sender_audio_capsfilter.link(self.sender_audio_resample)
        self.sender_audio_resample.link(self.sender_audio_encoder)
        self.sender_audio_encoder.link(self.sender_audio_rtimer)
        self.sender_audio_rtimer.link(self.sender_audio_sink)

    def gst_init_udp_video_stream(self):
        ####################################################################
        ### Build video pipeline as following:
        ####################################################################
        # SENDER VIDEO (UDP)
        # self.sender_video.add(self.sender_test_source)
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

    def gst_init_udp_audio_stream(self):
        # SENDER AUDIO (UDP)
        # self.sender_audio.add(self.sender_audio_source)
        self.sender_audio.add(self.sender_audio_capsfilter)
        self.sender_audio.add(self.sender_audio_resample)
        self.sender_audio.add(self.sender_audio_encoder)
        self.sender_audio.add(self.sender_audio_rtimer)
        self.sender_audio.add(self.sender_audio_sink)

        # self.sender_audio_source.link(self.sender_audio_capsfilter)
        self.sender_audio_capsfilter.link(self.sender_audio_resample)
        self.sender_audio_resample.link(self.sender_audio_encoder)
        self.sender_audio_encoder.link(self.sender_audio_rtimer)
        self.sender_audio_rtimer.link(self.sender_audio_sink)

    def initiate_streams(self, Host, Port_DSP0, Port_SPK0):
        self.sender_video_sink_udp.set_property('port', Port_DSP0)
        if Host:
            self.sender_video_sink_udp.set_property('host', Host)
        self.sender_video.set_state(Gst.State.NULL)

        self.sender_audio_sink.set_property("port", Port_SPK0)
        if Host:
            self.sender_audio_sink.set_property("host", Host)
        self.sender_audio.set_state(Gst.State.NULL)

    def run_video(self, flag):
        # flag 0 - Stop and drop Source
        # flag 1 - Link Source and play
        retmsg = None
        if flag is True:
            self.link_video_source(flag)
            retmsg = self.sender_video.set_state(Gst.State.PLAYING)
        else:
            if self.sender_video:
                retmsg = self.sender_video.set_state(Gst.State.READY)
                # time.sleep(0.1)
                self.link_video_source(flag)

        if retmsg == Gst.StateChangeReturn.FAILURE:
            print("VIDEO CONNECTION ERROR: Unable to set\nthe pipeline to the required state.")
            return False
        else:
            return True

    def run_audio(self, flag):
        # flag 0 - Stop and drop Source
        # flag 1 - Link Source and play
        retmsg = None
        if flag is True:
            self.link_audio_source(flag)
            retmsg = self.sender_audio.set_state(Gst.State.PLAYING)
        else:
            if self.sender_audio:
                retmsg = self.sender_audio.set_state(Gst.State.NULL)
                self.link_audio_source(flag)

        if retmsg == Gst.StateChangeReturn.FAILURE:
            print("AUDIO CONNECTION ERROR: Unable to set\nthe pipeline to the required state.")
            return False
        else:
            return True

    def CliCamera_gtksync(self):
        bus = self.sender_video.get_bus()
        bus.add_signal_watch()
        bus.enable_sync_message_emission()
        bus.connect("message", self.on_sender_message)
        bus.connect("sync-message::element", self.on_sender_sync_message)

    def on_sender_message(self, bus, message):
        retmsg = self.on_message(message)
        if retmsg is not None:
            print("retmsg:", retmsg)
            # self.ToggleButton_connect.set_active(False)
            # self.StatusBar.push(self.context_id, retmsg)

    def on_sender_sync_message(self, bus, message):
        self.on_sync_message(message, self.Sender_SXID)

    def on_message(self, message):
        msgtype = message.type
        if msgtype == Gst.MessageType.EOS:
            if Debug > 1:
                print ("EOS: SIGNAL LOST")
            return "VIDEO CONNECTION EOS: SIGNAL LOST"
        elif msgtype == Gst.MessageType.ERROR:
            err, debug = message.parse_error()
            debug_s = debug.split("\n")
            if Debug > 0:
                print ("ERROR:", debug_s)
            return debug_s[debug_s.__len__() - 1]
        elif msgtype == Gst.MessageType.CLOCK_LOST:
            # pause
            # play
            pass
        elif msgtype == Gst.MessageType.PROGRESS:
            pass
        elif msgtype == Gst.MessageType.STATE_CHANGED:
            # print('STATE_CHANGED')
            pass
        elif msgtype == Gst.MessageType.BUFFERING:
            # print('BUFFERING')
            pass
        else:
            return None

    def on_sync_message(self, message, SXID):
        if message.get_structure().get_name() == 'prepare-window-handle':
            imagesink = message.src
            imagesink.set_property("force-aspect-ratio", True)
            imagesink.set_window_handle(SXID.get_xid())

# noinspection PyPep8Naming
class ReceiverStream:
    player_video = None
    player_audio = None

    def __init__(self, Player_SXID):
        self.Player_SXID = Player_SXID

    def set_video_source(self):
        self.player_video       = Gst.Pipeline.new("player_video")
        #   SET VIDEO (PLAYER)
        # VIDEO receiver pipe:
        # source>capsfilter>rtimer>queue>decoder>convert>fpsadj>fpsadjcaps>flip>sink
        self.player_video_flip          = Gst.ElementFactory.make("videoflip")
        self.player_video_capsfilter    = Gst.ElementFactory.make("capsfilter", "capsfilter")
        self.player_video_depayloader   = Gst.ElementFactory.make("gdpdepay")
        self.player_video_convert       = Gst.ElementFactory.make("videoconvert")
        self.player_video_rtimer        = Gst.ElementFactory.make("rtph264depay")
        self.player_video_queue         = Gst.ElementFactory.make("queue")
        self.player_video_decoder       = Gst.ElementFactory.make("avdec_h264")
        self.player_video_fpsadj        = Gst.ElementFactory.make("videorate")
        self.player_video_scale         = Gst.ElementFactory.make("videoscale")
        self.player_video_adjcaps       = Gst.ElementFactory.make("capsfilter", "screenadj")
        self.player_video_sink          = Gst.ElementFactory.make("ximagesink", "sink")
        # self.player_video_scalecaps     = Gst.ElementFactory.make("capsfilter", "scalecaps")

        if ConnectionData.Protocol == TCP:
            self.player_video_source  = Gst.ElementFactory.make("tcpclientsrc", "remote_source_video")
        else:
            self.player_video_source  = Gst.ElementFactory.make("udpsrc", "remote_source_video_udp")

        # ToDo: Hud sync
        #         caps = Gst.Caps.from_string("video/x-raw, framerate=30/1")
        #         self.fpsadjcaps_video.set_property("caps", caps)
        #         self.fpsadj_video.set_property("max-rate", 30)

        caps = "application/x-rtp, encoding-name=H264, payload=96"
        self.player_video_capsfilter.set_property("caps", Gst.Caps.from_string(caps))

        if ConnectionData.TestMode is False:
            self.gst_init_testvideo_udp()
        else:
            self.gst_init_video_udp()

    def set_audio_source(self):
        self.player_audio       = Gst.Pipeline.new("player_audio")
        #   SET AUDIO RECEIVER
        #    udpsrc port=3333 ! application/x-rtp, media=audio, clock-rate=32000, encoding-name=SPEEX, payload=96 !
        #    rtpspeexdepay ! speexdec ! pulsesink sync=false
        self.player_audio_capsfilter   = Gst.ElementFactory.make("capsfilter", "capsfilter_audio")
        self.player_audio_depayloader  = Gst.ElementFactory.make("rtpspeexdepay", "depayloader_audio")
        self.player_audio_decoder      = Gst.ElementFactory.make("speexdec", "decoder_audio")
        # self.convert_audio = Gst.ElementFactory.make("audioresample")
        self.player_audio_sink         = Gst.ElementFactory.make("pulsesink", "local_sink_audio")

        # print("DEVICE_control.DEV_AudioOut: %s" % DEVICE_control.DEV_AudioOut)
        # self.player_audio_sink.set_property("device", DEVICE_control.DEV_AudioOut)

        if ConnectionData.Protocol == TCP:
            self.player_audio_source = Gst.ElementFactory.make("tcpclientsrc", "remote_source_audio")
            if ConnectionData.TestMode is False:
                # self.gst_init_testaudio_tcp()
                pass
            else:
                # self.gst_init_audio_tcp()
                pass
        else:
            self.player_audio_source  = Gst.ElementFactory.make("udpsrc", "remote_source_audio_udp")

        caps = "application/x-rtp, media=audio, clock-rate=32000, encoding-name=SPEEX, payload=96"
        self.player_audio_capsfilter.set_property("caps", Gst.Caps.from_string(caps))
        self.player_audio_sink.set_property("sync", True)
        # self.player_video_sink.set_property("sync", False)
        # self.player_video_sink.set_property("set_clock", "100")
        # self.player_audio_source.set_property("port", Port_MIC0)

        if ConnectionData.TestMode is False:
            self.gst_init_testaudio_udp()
        else:
            self.gst_init_audio_udp()

    def gst_init_test_tcp(self):
        # receive raw test image generated by gstreamer server
        # --- Gstreamer setup begin ---
        self.player_video.add(self.player_video_source)
        self.player_video.add(self.player_video_depayloader)
        self.player_video.add(self.player_video_convert)
        self.player_video.add(self.player_video_fpsadj)
        self.player_video.add(self.player_video_adjcaps)
        self.player_video.add(self.player_video_sink)

        self.player_video_source.link(self.player_video_depayloader)
        self.player_video_depayloader.link(self.player_video_convert)
        self.player_video_convert.link(self.player_video_fpsadj)
        self.player_video_fpsadj.link(self.player_video_adjcaps)
        self.player_video_adjcaps.link(self.player_video_sink)

        #    tcpclientsrc host=x.x.x.x port=4552 ! application/x-rtp, media=audio, clock-rate=32000, encoding-name=SPEEX, payload=96 !
        #    rtpspeexdepay ! speexdec ! pulsesink sync=false
        self.player_audio.add(self.player_audio_source)
        self.player_audio.add(self.player_audio_capsfilter)
        self.player_audio.add(self.player_audio_depayloader)
        self.player_audio.add(self.player_audio_decoder)
        self.player_audio.add(self.player_audio_sink)

        self.player_audio_source.link(self.player_audio_capsfilter)
        self.player_audio_capsfilter.link(self.player_audio_depayloader)
        self.player_audio_depayloader.link(self.player_audio_decoder)
        self.player_audio_decoder.link(self.player_audio_sink)
        # --- Gstreamer setup end ---

    def gst_init_live_tcp(self):
        # --- Gstreamer setup begin ---
        self.player_video.add(self.player_video_source)
        self.player_video.add(self.player_video_depayloader)
        self.player_video.add(self.player_video_rtimer)
        self.player_video.add(self.player_video_decoder)
        self.player_video.add(self.player_video_convert)
        self.player_video.add(self.player_video_flip)
        self.player_video.add(self.player_video_fpsadj)
        self.player_video.add(self.player_video_adjcaps)
        self.player_video.add(self.player_video_sink)

        self.player_video_source.link(self.player_video_depayloader)
        self.player_video_depayloader.link(self.player_video_rtimer)
        self.player_video_rtimer.link(self.player_video_decoder)
        self.player_video_decoder.link(self.player_video_convert)
        self.player_video_convert.link(self.player_video_flip)
        self.player_video_flip.link(self.player_video_fpsadj)
        self.player_video_fpsadj.link(self.player_video_adjcaps)
        self.player_video_adjcaps.link(self.player_video_sink)

        #    tcpclientsrc host=x.x.x.x port=4552 ! application/x-rtp, media=audio, clock-rate=32000, encoding-name=SPEEX,
        #    payload=96 ! rtpspeexdepay ! speexdec ! pulsesink sync=false
        self.player_audio.add(self.player_audio_source)
        self.player_audio.add(self.player_audio_capsfilter)
        self.player_audio.add(self.player_audio_depayloader)
        self.player_audio.add(self.player_audio_decoder)
        self.player_audio.add(self.player_audio_sink)

        self.player_audio_source.link(self.player_audio_capsfilter)
        self.player_audio_capsfilter.link(self.player_audio_depayloader)
        self.player_audio_depayloader.link(self.player_audio_decoder)
        self.player_audio_decoder.link(self.player_audio_sink)
        # --- Gstreamer setup end ---

    def gst_init_testvideo_udp(self):
        # receive raw test image generated by gstreamer server
        # --- Gstreamer setup begin ---
        self.player_video.add(self.player_video_source)
        self.player_video.add(self.player_video_capsfilter)
        self.player_video.add(self.player_video_rtimer)
        self.player_video.add(self.player_video_decoder)
        self.player_video.add(self.player_video_convert)
        self.player_video.add(self.player_video_fpsadj)
        self.player_video.add(self.player_video_scale)
        self.player_video.add(self.player_video_adjcaps)
        self.player_video.add(self.player_video_sink)

        self.player_video_source.link(self.player_video_capsfilter)
        self.player_video_capsfilter.link(self.player_video_rtimer)
        self.player_video_rtimer.link(self.player_video_decoder)
        self.player_video_decoder.link(self.player_video_convert)
        self.player_video_convert.link(self.player_video_fpsadj)
        self.player_video_fpsadj.link(self.player_video_scale)
        self.player_video_scale.link(self.player_video_adjcaps)
        self.player_video_adjcaps.link(self.player_video_sink)

    def gst_init_testaudio_udp(self):
        #    udpsrc port=3333 ! application/x-rtp, media=audio, clock-rate=32000, encoding-name=SPEEX, payload=96 !
        #    rtpspeexdepay ! speexdec ! pulsesink sync=false
        self.player_audio.add(self.player_audio_source)
        self.player_audio.add(self.player_audio_capsfilter)
        self.player_audio.add(self.player_audio_depayloader)
        self.player_audio.add(self.player_audio_decoder)
        self.player_audio.add(self.player_audio_sink)

        self.player_audio_source.link(self.player_audio_capsfilter)
        self.player_audio_capsfilter.link(self.player_audio_depayloader)
        self.player_audio_depayloader.link(self.player_audio_decoder)
        self.player_audio_decoder.link(self.player_audio_sink)
        # --- Gstreamer setup end ---

    def gst_init_video_udp(self):
        # --- Gstreamer setup begin ---
        self.player_video.add(self.player_video_source)
        self.player_video.add(self.player_video_capsfilter)
        self.player_video.add(self.player_video_rtimer)
        self.player_video.add(self.player_video_queue)
        self.player_video.add(self.player_video_decoder)
        self.player_video.add(self.player_video_convert)
        self.player_video.add(self.player_video_fpsadj)
        self.player_video.add(self.player_video_scale)
        self.player_video.add(self.player_video_adjcaps)
        self.player_video.add(self.player_video_flip)
        self.player_video.add(self.player_video_sink)

        self.player_video_source.link(self.player_video_capsfilter)
        self.player_video_capsfilter.link(self.player_video_rtimer)
        self.player_video_rtimer.link(self.player_video_queue)
        self.player_video_queue.link(self.player_video_decoder)
        self.player_video_decoder.link(self.player_video_convert)
        self.player_video_convert.link(self.player_video_fpsadj)
        self.player_video_fpsadj.link(self.player_video_scale)
        self.player_video_scale.link(self.player_video_adjcaps)
        self.player_video_adjcaps.link(self.player_video_flip)
        self.player_video_flip.link(self.player_video_sink)

    def gst_init_audio_udp(self):
        #    udpsrc port=3333 ! application/x-rtp, media=audio, clock-rate=32000, encoding-name=SPEEX, payload=96 !
        #    rtpspeexdepay ! speexdec ! pulsesink sync=false
        # PLAYER
        self.player_audio.add(self.player_audio_source)
        self.player_audio.add(self.player_audio_capsfilter)
        self.player_audio.add(self.player_audio_depayloader)
        self.player_audio.add(self.player_audio_decoder)
        self.player_audio.add(self.player_audio_sink)

        self.player_audio_source.link(self.player_audio_capsfilter)
        self.player_audio_capsfilter.link(self.player_audio_depayloader)
        self.player_audio_depayloader.link(self.player_audio_decoder)
        self.player_audio_decoder.link(self.player_audio_sink)
        # --- Gstreamer setup end ---

    def initiate_streams(self, Host, Port_Video, Port_Audio):
        self.set_video_source()
        self.player_video_source.set_property("port", Port_Video)
        if Host:
            self.player_video_source.set_property("host", Host)
        self.player_video.set_state(Gst.State.NULL)
        self.CliDisplay_gtksync()

        self.set_audio_source()
        self.player_audio_source.set_property("port", Port_Audio)
        if Host:
            self.player_audio_source.set_property("host", Host)
        self.player_audio.set_state(Gst.State.NULL)

    def run_video(self, flag):
        # flag 0 - Stop and be ready for Play (restart mode)
        # flag 1 - Play
        # flag 2 - Stop and release resources (exit mode)
        if self.player_video is None:
            return True

        if flag is True:   # Play
            retmsg = self.player_video.set_state(Gst.State.PLAYING)
        else:
            retmsg = self.player_video.set_state(Gst.State.NULL)  # in order to blank the screen
            if flag is False:  # Restart (get ready for Play)
                # time.sleep(0.1)
                retmsg = self.player_video.set_state(Gst.State.READY)

        # time.sleep(0.1)
        if retmsg == Gst.StateChangeReturn.FAILURE:
            print("AUDIO CONNECTION ERROR: Unable to set the pipeline to the playing state.")
            return False
        else:
            return True

    def run_audio(self, flag):
        # flag 0 - Stop and be ready for Play (restart mode)
        # flag 1 - Play
        # flag 2 - Stop and release resources (exit mode)
        if self.player_audio is None:
            return True

        if flag is True:
            retmsg = self.player_audio.set_state(Gst.State.PLAYING)
        else:
            if flag is False:
                retmsg = self.player_audio.set_state(Gst.State.READY)
            else:
                retmsg = self.player_audio.set_state(Gst.State.NULL)

        if retmsg == Gst.StateChangeReturn.FAILURE:
            return False
        else:
            return True

    def resize_screen(self, width, height):
        caps = "video/x-raw, width=%i, height=%i" % (width, height)
        self.player_video_adjcaps.set_property("caps", Gst.Caps.from_string(caps))

    def CliDisplay_gtksync(self):
        bus = self.player_video.get_bus()
        bus.add_signal_watch()
        bus.enable_sync_message_emission()
        bus.connect("message", self.on_player_message)
        bus.connect("sync-message::element", self.on_player_sync_message)

    def on_player_message(self, bus, message):
        retmsg = self.on_message(message)
        if retmsg is not None:
            print("retmsg:", retmsg)
            return False
        else:
            return True

    def on_player_sync_message(self, bus, message):
        self.on_sync_message(message, self.Player_SXID)
        return True

    def on_message(self, message):
        msgtype = message.type
        if msgtype == Gst.MessageType.EOS:
            if Debug > 1:
                print("EOS: SIGNAL LOST")
            return "VIDEO CONNECTION EOS: SIGNAL LOST"

        elif msgtype == Gst.MessageType.ERROR:
            err, debug = message.parse_error()
            debug_s = debug.split("\n")
            if Debug > 0:
                print ("ERROR:", debug_s)
            # return debug_s[debug_s.__len__() - 1]

        elif msgtype == Gst.MessageType.STATE_CHANGED:
            # print('STATE_CHANGED')
            pass

        elif msgtype == Gst.MessageType.BUFFERING:
            # print('BUFFERING')
            pass

        return None

    def on_sync_message(self, message, SXID):
        if message.get_structure().get_name() == 'prepare-window-handle':
            imagesink = message.src
            imagesink.set_property("force-aspect-ratio", True)
            imagesink.set_window_handle(SXID.get_xid())


