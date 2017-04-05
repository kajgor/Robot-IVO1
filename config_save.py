import pickle

with open("rac.cfg", "w") as iniFile:
    print "+++++++++++" + str(Host)
    print "+++++++++++" + str(self.Host)
    for item in (self.Host,
                 Port_Comm,
                 Port_Video,
                 Port_Audio,
                 Gstreamer_Path,
                 "X",
                 "X",
                 "X",
                 "X",
                 Local_Test,
                 "END"):
        pickle.dump(item,iniFile)
