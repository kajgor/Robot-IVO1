########################
# WINDOWS VERSION V1.0 #
# AUTHOR: IGOR         #
#         KOZLOWSKI    #
#     2016-09-01       #
########################

import socket, sys, time, atexit
from _thread import *
from os import system

COMM_BITSHIFT = 30
HOST = 'localhost'   # Symbolic name meaning all available interfaces
C_PORT = 5000  # Arbitrary non-privileged port
V_PORT = 12344
srv_address = (HOST, C_PORT)

# STREAM:
# gst-launch-1.0 -v videotestsrc pattern=smpte ! video/x-raw,width=320,height=240 ! gdppay ! tcpserversink host=127.0.0.1 port=12344
gstreamer_cmd = "/usr/bin/gst-launch-1.0 videotestsrc pattern=smpte ! video/x-raw,width=512,height=384 " \
                "! gdppay ! tcpserversink host=" + HOST + " port=" + V_PORT.__str__()

# RECEIVE:
# Windows:  C:/gstreamer/1.0/x86_64/bin/gst-launch-1.0 -v tcpclientsrc host=127.0.0.1 port=1234 ! gdpdepay ! videoconvert ! autovideosink sync=false
# Linux:    gst-launch-1.0 videotestsrc pattern=smpte ! video/x-raw,width=320,height=240 ! ximagesink/gtksink/cacasink/glimagesink (default)

system("pkill -f '" + gstreamer_cmd + "'")
time.sleep(1)

srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
print('Socket created')
# Bind socket to local host and port
try:
    srv.bind(srv_address)

except socket.error as msg:
    print('Bind failed. Error Code : ' + str(msg[0]) + ' Message ' + msg[1])
    sys.exit()

print('Socket bind complete')
# Start listening on socket
srv.listen(5)
print('Socket now listening')

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
            print("DATA_IN>> " + data.__str__())
            nodata_cnt = 0
            # reply = chr(COMM_BITSHIFT - 1) + data
            reply = data.ljust(15, chr(10).encode('ascii'))
            print("DATA_OUT>> " + reply.__str__())
            conn.sendall(reply)

    #came out of loop
    conn.close()
    print('Connection with ' + addr[0] + ':' + str(addr[1]) + " closed.")
    time.sleep(1)
    system("pkill -f '" + gstreamer_cmd + "'")
    print('Video stream stopped!')


def closesrv():
    print("Closing socket[*]")
    system("pkill -f '" + gstreamer_cmd + "'")
    srv.close()

atexit.register(closesrv)

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
    print("GSTREAMER COMMAND: " + gstreamer_cmd)
    system(gstreamer_cmd + ' &')
    print('Video stream started!')

    #start new thread takes 1st argument as a function name to be run, second is the tuple of arguments to the function.
    start_new_thread(clientthread, (conn,))
