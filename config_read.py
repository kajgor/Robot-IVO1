import pickle

with open("rac.cfg", "r") as iniFile:
    Host = pickle.load(iniFile)
    Port_Comm = pickle.load(iniFile)
    Port_Video = pickle.load(iniFile)
    Port_Audio = pickle.load(iniFile)
    Gstreamer_Path = pickle.load(iniFile)
    Reserved_1 = pickle.load(iniFile)
    Reserved_2 = pickle.load(iniFile)
    Reserved_3 = pickle.load(iniFile)
    Reserved_4 = pickle.load(iniFile)
    Local_Test = pickle.load(iniFile)
    END_CFG = pickle.load(iniFile)
