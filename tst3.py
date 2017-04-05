import time, socket
from class_console import *
from thread import *

print "IDENT: " + get_ident().__str__()
RConn = RacConnection()
ret = RConn.check_connection("127.0.0.1")
print "NONE " + ret.__str__()

print "Trying to connect:"
RConn.estabilish_connection("localhost", 5000)
# RConn.conoff = True
# thr = start_new_thread(RConn.estabilish_connection, ("localhost", 5000))
time.sleep(1)
ret = RConn.check_connection("127.0.0.1")
print "1CON " + ret.__str__()\
      # + "  thread " + thr.__str__()

time.sleep(3)

print "Disconnect:"
RConn.close_connection("")
# RConn.conoff = False
time.sleep(1)
ret = RConn.check_connection("127.0.0.1")
print "1DIS " + ret.__str__()

time.sleep(3)

print "Trying to connect:"
RConn.estabilish_connection("localhost", 5000)
# RConn.conoff = True
# thr = start_new_thread(RConn.estabilish_connection, ("localhost", 5000))
time.sleep(1)
ret = RConn.check_connection("127.0.0.1")
print "2CON " + ret.__str__()\
      # + "  thread " + thr.__str__()

time.sleep(1)

print "Disconnect:"
RConn.close_connection("")
# RConn.conoff = False
time.sleep(1)
ret = RConn.check_connection("127.0.0.1")
print "2DIS " + ret.__str__()
