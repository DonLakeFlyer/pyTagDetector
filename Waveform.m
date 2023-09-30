from Config import *

import numpy
from scipy import signal

class Waveform:
    stftWindow = signal.windows.boxcar(Config.nSTFTSegment)

    def __init__(self, samples):
        self.stftFreqs, self.stftTimes, self.psdSpectro = 
            signal.spectrogram(
                samples, 
                Config.decimatedSampleRate, 
                nperseg         = Config.nSTFTSegment, 
                noverlap        = Config.nSTFTSegmentOverlap, 
                window          = stftWindow,
                scaling         = "density",
                mode            = "psd",
                return_onesided = False)

    # Vector with 1s in position of possible pulses given K grouping.
    # These posiotions are the starting point where the first pulse would
    # be found in the first STFT window.
    def _initialPulsePositionsInSTFTWindows(self):
        index = 0
        pulsePositions = numpy.zeros(psdSpectro.shape[1], dtype = numpy.int32)
        logging.info("Pulse positions %s", pulsePositions.shape)
        while index < pulsePositions.shape[0]:
            pulsePositions[index] = 1
            index += Config.nSTFTWindowsIntraPulse

    def _inchoerentSumMatrix(self):
        pulsePositions = self._initialPulsePositionsInSTFTWindows()
        # Create empty incoherent sum position matrix
        summationMatrix = numpy.zeros((self.psdSpectro.shape[1], Config.nSTFTWindowsIntraPulse), dtype = numpy.int32)
        index = 0
        while index < Config.nSTFTWindowsIntraPulse:
            summationMatrix[:, index] = pulsePositions
            pulsePositions = numpy.roll(pulsePositions, 1)
            index += 1
    