import pickle

def config_read(self, filename):
    with open(filename, "rb") as iniFile:
        self.Host = pickle.load(iniFile)
        self.Port_Comm = pickle.load(iniFile)
        self.Port_Video = pickle.load(iniFile)
        self.Port_Audio = pickle.load(iniFile)
        self.Gstreamer_Path = pickle.load(iniFile)
        self.Reserved_1  = pickle.load(iniFile)
        self.Reserved_2 = pickle.load(iniFile)
        self.Reserved_3 = pickle.load(iniFile)
        self.Reserved_4 = pickle.load(iniFile)
        self.Local_Test = pickle.load(iniFile)
        self.END_CFG = pickle.load(iniFile)
    print ("Configuration read.")

def config_save(self, filename):
    with open(filename, "wb") as iniFile:
        for item in [self.Host,
                     self.Port_Comm,
                     self.Port_Video,
                     self.Port_Audio,
                     self.Gstreamer_Path,
                     "X",
                     "X",
                     "X",
                     "X",
                     self.Local_Test,
                     "END"]:
            pickle.dump(item,iniFile)
    print ("Configuration saved.")

def reset_save(filename):
    with open(filename, "wb") as iniFile:
        for item in ("127.0.0.1",
                     5000,
                     5101,
                     5102,
                     "/usr/bin",
                     "X",
                     "X",
                     "X",
                     "X",
                     True,
                     "END"):
            pickle.dump(item,iniFile)
    print ("Configuration reset.")
