# !/usr/bin/env python

########################
# WINDOWS VERSION V2.0 #
# AUTHOR: IGOR         #
#         KOZLOWSKI    #
#     2017-06-19       #
########################

import socket, sys, time, atexit
from _thread import *
# from os import system
from init_variables import *

import gi
gi.require_version("Gst", "1.0")
from gi.repository import Gst

HOST = 'localhost'   # Symbolic name meaning all available interfaces
C_PORT = 5000  # Arbitrary non-privileged port
V_PORT = 12344
srv_address = (HOST, C_PORT)

# Function for handling connections. This will be used to create threads
def clientthread(conn):
    # Sending message to connected client
    conn.send('AWAITING CONNECTION: ENGINE\n'.encode('ascii'))  # send only takes string

    nodata_cnt = 0
    #infinite loop so that function do not terminate and thread do not end.
    while True:
        #Receiving from client
        try:
            data = conn.recv(6)
        except socket.error:
            data = ''
            print("Socket error!")

        if not data:
            nodata_cnt += 1
            if nodata_cnt >= 10:
                print("NO DATA - closing connection")
                break
        else:
            nodata_cnt = 0
            reply = data.ljust(15, chr(10).encode(Encoding))
            if Debug > 0:
                print("DATA_IN>> " + data.__str__())

            if Debug > 0:
                print("DATA_OUT>> " + reply.__str__())

            conn.sendall(reply)

    #came out of loop
    conn.close()
    print('Connection with ' + addr[0] + ':' + str(addr[1]) + " closed.")
    time.sleep(1)
    player.set_state(Gst.State.NULL)
    print('Video stream stopped!')


def closesrv():
    print("Closing socket[*]")
    player.set_state(Gst.State.NULL)
    srv.close()



############################ MAIN ##########################################
atexit.register(closesrv)

# --------- Gstreamer Setup begin --------------
Gst.init(None)
player = Gst.Pipeline.new("player")

source = Gst.ElementFactory.make("videotestsrc", "video-source")
source.set_property("pattern", "smpte")

caps = Gst.Caps.from_string("video/x-raw, width=800, height=600")
capsfilter = Gst.ElementFactory.make("capsfilter", "filter")
capsfilter.set_property("caps", caps)

encoder = Gst.ElementFactory.make("gdppay", "encoder")

sink = Gst.ElementFactory.make("tcpserversink", "video-output")
sink.set_property("host", HOST)
sink.set_property("port", V_PORT)

player.add(source, capsfilter, encoder, sink)

source.link(capsfilter)
capsfilter.link(encoder)
encoder.link(sink)
# STREAM:
# gst-launch-1.0 -v videotestsrc pattern=smpte ! video/x-raw,width=320,height=240 ! gdppay ! tcpserversink host=127.0.0.1 port=12344
# RECEIVE:
# Windows:  C:/gstreamer/1.0/x86_64/bin/gst-launch-1.0 -v tcpclientsrc host=127.0.0.1 port=1234 ! gdpdepay ! videoconvert ! autovideosink sync=false
# Linux:    gst-launch-1.0 videotestsrc pattern=smpte ! video/x-raw,width=320,height=240 ! ximagesink/gtksink/cacasink/glimagesink (default)

# --------- Gstreamer Setup end --------------

time.sleep(1)

# Create Socket
srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
print('Socket created')

# Bind socket to local host and port
try:
    srv.bind(srv_address)

except socket.error as msg:
    print('Bind failed. Error Code : ' + str(msg[0]) + ' Message ' + msg[1])
    sys.exit()

except OSError as msg:
    print('Bind failed. Error Code : ' + str(msg[0]) + ' Message ' + msg[1])
    print('Advice: check for python process to kill it!')
    sys.exit()

print('Socket bind complete')
# Start listening on socket
srv.listen(5)
print('Socket now listening')

# now keep talking with the client
while 1:
    #wait to accept a connection - blocking call
    try:
        conn, addr = srv.accept()
    except:
        print("User break")
        break

    print('Connected with ' + addr[0] + ':' + str(addr[1]))

    time.sleep(1)
    print('Starting video stream...')
    # print("GSTREAMER COMMAND: " + gstreamer_cmd)
    player.set_state(Gst.State.PLAYING)
    print('Video stream started!')

    #start new thread takes 1st argument as a function name to be run, second is the tuple of arguments to the function.
    start_new_thread(clientthread, (conn,))

