import socket

HOST = "localhost"
PORT = 2331
Encoding = 'latin_1'
Debug = 3

def create_socket():
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_address = (HOST, PORT)
    IP_addr = socket.gethostbyname(HOST)
    print(server_address, "[", IP_addr, "]")
    try:
        srv.connect(server_address)
        connected = True
        if Debug > 2: print("Connected! self.srv.getpeername()", srv.getpeername())
    except ConnectionResetError:
        connected = False
        if Debug > 0: print("Server not responding <", connected, ">")
    except ConnectionRefusedError:
        connected = False
        if Debug > 0: print("Server refused connection <", connected, ">")
    except socket.gaierror:
        connected = False
        if Debug > 0: print("Invalid protocol <", connected, ">")

    if connected is True:
        for iter_x in range(0, 255):
            sendstr = str(chr(iter_x)).encode(Encoding)
            sendstr = sendstr.ljust(3, chr(10).encode(Encoding))
            if Debug > 1:
                print("CLISENT[len]: " + len(sendstr).__str__(), sendstr)

            if srv is None:
                print("self.srv is NONE!")
                return None
            try:
                srv.sendall(sendstr)
            except BrokenPipeError:
                print("transmit_message: BrokenPipeError")
                return None
            except AttributeError:
                print("transmit_message: AttributeError")
                return None
            except OSError:
                print("transmit_message: OSError (server lost)")
                return None


create_socket()
