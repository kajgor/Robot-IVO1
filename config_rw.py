import pickle
from Common_vars import COMM_vars


def config_read(filename):
    with open(filename, "rb") as iniFile:
        HostList        = pickle.load(iniFile)
        Mask1           = pickle.load(iniFile)
        RSA_Key         = pickle.load(iniFile)
        Key_Pass        = pickle.load(iniFile)
        Ssh_User        = pickle.load(iniFile)
        Remote_Host     = pickle.load(iniFile)
        Compression     = pickle.load(iniFile)
        Reserved_6      = pickle.load(iniFile)
        Reserved_7      = pickle.load(iniFile)
        Local_Test      = pickle.load(iniFile)
        END_CFG         = pickle.load(iniFile)

        COMM_vars.resolution = Mask1[0]
        COMM_vars.light      = Mask1[1]
        COMM_vars.mic        = Mask1[2]
        COMM_vars.display    = Mask1[3]
        COMM_vars.speakers   = Mask1[4]
        COMM_vars.laser      = Mask1[5]
        COMM_vars.AutoMode   = Mask1[6]

    print ("Configuration read from", filename)
    return HostList,\
           Mask1,\
           RSA_Key,\
           Key_Pass,\
           Ssh_User,\
           Remote_Host,\
           Compression,\
           Reserved_6,\
           Reserved_7,\
           Local_Test


def config_save(filename, HostList, RSA_Key, Key_Pass, Ssh_User, Remote_Host,
                Compression, Reserved_6, Reserved_7, Local_Test):
    with open(filename, "wb") as iniFile:

        # print("HostList", HostList)

        Mask1 = (COMM_vars.resolution,
                 COMM_vars.light,
                 COMM_vars.mic,
                 COMM_vars.display,
                 COMM_vars.speakers,
                 COMM_vars.laser,
                 COMM_vars.AutoMode)

        for item in [HostList,
                    Mask1,
                    RSA_Key,
                    Key_Pass,
                    Ssh_User,
                    Remote_Host,
                    Compression,
                    Reserved_6,
                    Reserved_7,
                    Local_Test,
                    "END"]:
            pickle.dump(item, iniFile)
    print ("Configuration saved.")

def reset_save(filename):
    with open(filename, "wb") as iniFile:
        for item in (("localhost:4550:True", "10.0.0.23:4550:False", "athome106.hopto.org:222:True"),
                     (1, False, False, False, False, False, False, False),
                     "/home/igor/.ssh/id_rsa",
                     "nescape",
                     "igor",
                     "127.0.0.1",
                     True,
                     False,
                     False,
                     True,
                     "END"):
            pickle.dump(item, iniFile)
    print ("Configuration reset.")
