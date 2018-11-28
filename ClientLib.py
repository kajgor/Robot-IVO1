import socket
import queue
import time

# from sshtunnel import SSHTunnelForwarder
# from paramiko import RSAKey
from re import findall
from _thread import *
from Common_vars import ConnectionData, MAX_SPEED, RETRY_LIMIT, CLIMSGLEN,\
    RECMSGLEN, Encoding, LEFT, RIGHT, calc_checksum, X_AXIS, Y_AXIS
from Client_vars import CONSOLE_GUI, RESP_DELAY, Debug, CommunicationFFb


class ConnectionThread:
    srv             = None
    tunnel          = None
    comm_link_idle  = 0

    FxQueue         = queue.Queue()

    def __init__(self):
        self.FxMode = 255, 0

    @staticmethod
    def get_streamer_ports(Port):
        Port_CAM0 = Port + 1
        Port_MIC0 = Port + 2
        Port_DSP0 = Port + 4
        Port_SPK0 = Port + 5

        return Port_CAM0, Port_MIC0, Port_DSP0, Port_SPK0

    def establish_connection(self, Host, Port, Receiver):
        Console.print("Establishing connection with \n %s on port"  % Host, Port)

        # self.start_media_streams(Host, Port)

        ##########################################################
        #              RUN CONNECTION THREAD LOOP                #
        ##########################################################
        start_new_thread(self.connection_thread, (Host, Port, Receiver))   #
        time.sleep(0.25)                                         #
        ##########################################################

        l_iter = 0
        while ConnectionData.connected is False and l_iter < 10:
            l_iter += 1
            Console.print("Retry: %i" % l_iter)
            time.sleep(0.25)

        if ConnectionData.connected is True:
            retmsg = "Client connected! %s" % self.srv.getsockname().__str__()
        else:
            retmsg = "Connection Error [%s:%i]" % (Host, Port)

        if Debug > 0:
            Console.print(retmsg)

        return ConnectionData.connected, retmsg

    def close_connection(self):
        Console.print("Closing connection...")
        try:
            self.tunnel.close()
        except:
            Console.print("tunnel not open")

        try:
            self.srv.shutdown(socket.SHUT_RDWR)
        except OSError:
            Console.print("...not connected!")
        except AttributeError:
            Console.print("...not connected!")

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
            if Debug > 2: Console.print("Connection status: %s" % status)
            return True
        else:
            if Debug > 2: Console.print("Not connected.")
            return False

    ###############################################################################
    ################   COMMUNICATION LOOP START   #################################
    ###############################################################################

    def connection_thread(self, Host, Port_Comm, Receiver):
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

        connErr = 0
        cam0_restart = False
        resolution_last = None
        ConnectionData.StreamMode = None
        self.comm_link_idle = 0

        while ConnectionData.connected is True:
            if CommunicationFFb is True:
                # self.get_speed_and_direction()  # Keyboard input
                self.calculate_MotorPower()     # Set control variables
                self.mouseInput()               # Set mouse Variables

            if resolution_last != [ConnectionData.resolution, ConnectionData.Framerate]:
                if self.FxQueue.empty() is True and ConnectionData.StreamMode is not None:
                    resolution_last = [ConnectionData.resolution, ConnectionData.Framerate]

                    self.FxMode = 0, ConnectionData.resolution  # Resolution Tag is 0

                    if ConnectionData.resolution > 0:
                        Console.print("Requesting mode", ConnectionData.resolution, end='...')
                        cam0_restart = True

                    if Receiver.player_video:
                        Console.print("Pausing Video Stream")
                        Receiver.run_video(False)

            if cam0_restart is True:
                if ConnectionData.resolution == ConnectionData.StreamMode:
                    Console.print("Player START")
                    Receiver.run_video(True)
                    cam0_restart = False

            if self.check_connection(None) is True:
                retcode = self.send_and_receive()
                if retcode is False:
                    connErr += 1
                    if connErr > RETRY_LIMIT:
                        ConnectionData.connected = False  # EXIT LOOP!
                else:
                    ConnectionData.connErr = 0

        Receiver.run_video(None)
        Receiver.run_audio(None)
        self.close_connection()

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

            request  = self.encode_message(self.FxMode)

            checksum = self.transmit_message(request)

            if checksum is None:
                return False

            ###### Communication Clock! #####################
            time.sleep(RESP_DELAY)      # Wait for response #
            #################################################

            response = self.receive_message(RECMSGLEN)

            if response:
                self.comm_link_idle = 0
                if checksum == ord(response[0]):    # ************* MESSAGE CONFIRMED ******************
                    self.decode_message(response)
                    ConnectionData.motor_ACK = ConnectionData.motor_Power
                    if self.FxQueue.empty() is False:
                        self.FxMode = self.FxQueue.get()
                    else:
                        self.FxMode = 255, 0
                else:
                    Console.print("Bad chksum:", checksum, ord(response[0]))
                if Debug > 1:
                    Console.print("CheckSum Sent/Received:", checksum, ord(response[0]))
            return True
        else:
# ToDo:
            self.transmit_message("HALTHALTHALT")
            ConnectionData.connected = False
            return False

    ###############################################################################
    ################   CONN LOOP END   ############################################
    ###############################################################################

    def transmit_message(self, out_str):
        sendstr = str(chr(0) + out_str + chr(10)).encode(Encoding)
        if Debug > 1:
            print("CLISENT[len]: %i" % len(sendstr))

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
            Console.print("CLIRCVD[len]: %i" % len(data))

        try:
            data_end = data[msglen - 1]
        except IndexError:
            data_end = False
            Console.print(">>>DataIndexError>>> %s [len=%i]" % (data_end, len(data)))

        if data_end == chr(255):
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
        for xcr in range(1, 11): # communication via serial port fix decode
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

        CntrlMask1                      = ord(resp[11])                             #12
        ConnectionData.StreamMode       = ord(resp[12])                             #13
        ConnectionData.coreTemp         = ord(resp[14]) * 0.5                       #15

    @staticmethod
    def encode_message(FxMode):
        FXtag, FXvalue = FxMode
        CntrlMask1 = 0
        for idx, x in enumerate([ConnectionData.AutoMode, ConnectionData.light, ConnectionData.speakers,
                                 ConnectionData.mic, ConnectionData.display, ConnectionData.laser, 0, 0]):
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
        reqMsgVal.append(FXtag)                                 # 6
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
