import wx, sys, os, time, socket
from os import system
from config_rw import *
from init_variables import *
from class_console import RacConnection
MC_instance = RacConnection(socket)

# global srv

print MC_instance.srv

retmsg = MC_instance.estabilish_connection("127.0.0.1", 5000)

print retmsg

hde = MC_instance.transmit("hahaha")
print "output:" + hde.__str__()

pygame.font.init()
myfont = pygame.font.SysFont("monospace", 15)
out_text = myfont.render(str(rawtext), 1, f_color, b_color)
screen.blit(out_text, (x, y))
sceen.flip()

