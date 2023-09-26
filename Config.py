import math

class Config:
    udpIP                       = "127.0.0.1"
    udpPort                     = 10000
    incomingSampleRate          = 3000000
    k                           = 3
    pulseWidthMSecs             = 150
    pulseWidthSecs              = pulseWidthMSecs / 1000.0
    intraPulseMSecs             = 2000
    intraPulseSecs              = intraPulseMSecs / 1000.0
    intraPulseUncertaintyMSecs  = 60
    intraPulseUncertaintySecs   = intraPulseUncertaintyMSecs / 1000.0
    intraPulseJittersMSecs      = 20
    intraPulseJittersSecs       = intraPulseJittersMSecs / 1000.0
    decimationFactor            = 800
    decimatedSampleRate         = incomingSampleRate / decimationFactor
    nDecimatedIntraPulse        = math.floor(intraPulseSecs * decimatedSampleRate)
    nDecimatedPulseWidth        = math.floor(pulseWidthSecs * decimatedSampleRate)
    nDecimatedPulseUncertainty  = math.floor(intraPulseUncertaintySecs * decimatedSampleRate)
    nDecimatedPulseJitter       = math.floor(intraPulseJittersSecs * decimatedSampleRate)
    stftOverlapFraction         = 0.5
    nSTFTSegment                = nDecimatedPulseWidth
    nSTFTSegmentOverlap         = math.floor(nSTFTSegment * stftOverlapFraction)
    nSTFTSegmentNotOverlapped   = nSTFTSegment - nSTFTSegmentOverlap
    nSTFTWindowsIntraPulse      = math.floor(nDecimatedIntraPulse / nSTFTSegmentNotOverlapped)
    nDecimatedForKPulses        = (k * (nDecimatedIntraPulse + nDecimatedPulseUncertainty)) + nDecimatedPulseJitter + nSTFTSegmentOverlap
    nDecimatedOverlap           = 2 * ((k * nDecimatedPulseUncertainty) + nDecimatedPulseJitter)
    nDecimatedForKPulsesWithOverlap = nDecimatedForKPulses + nDecimatedOverlap
    nIncomingForKPulses         = nDecimatedForKPulsesWithOverlap * decimationFactor
