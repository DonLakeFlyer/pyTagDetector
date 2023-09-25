import math

class Config:
    udpIP                       = "127.0.0.1"
    udpPort                     = 10000
    incomingSampleRate          = 3000000
    k                           = 3
    intraPulseMSecs             = 2000
    intraPulseSecs              = intraPulseMSecs / 1000.0
    intraPulseUncertaintyMSecs  = 100
    intraPulseUncertaintySecs   = intraPulseUncertaintyMSecs / 1000.0
    intraPulseJittersMSecs      = 100
    intraPulseJittersSecs       = intraPulseJittersMSecs / 1000.0
    incomingSampsForKPulses     = math.ceil(k * intraPulseSecs * incomingSampleRate)
    decimationFactor            = 800
    decimatedSampsForKPulses    = math.floor(incomingSampsForKPulses / decimationFactor)
