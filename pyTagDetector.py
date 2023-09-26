from UDPReaderThread import *

import time
import logging
import numpy
from scipy import signal
from matplotlib import pyplot as plt

def pyTagDetector():
    logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s |  %(filename)s:%(lineno)d')

    udpReader = UDPReaderThread()
    udpReader.start()

    notifyCondition = udpReader.decimatedBuffer().registerItemCountCondition(Config.nDecimatedForKPulsesWithOverlap)

    stftWindow = signal.windows.boxcar(Config.nSTFTSegment)

    logging.info("%d %d", Config.nDecimatedForKPulses, Config.nSTFTSegmentOverlap)

    display = False
    while True:
        with notifyCondition:
            while udpReader.decimatedBuffer().unreadCount() < Config.nDecimatedForKPulsesWithOverlap:
                notifyCondition.wait()
        decimatedBuffer = udpReader.decimatedBuffer().read(Config.nDecimatedForKPulses, Config.nDecimatedOverlap)
        stftFreqs, stftWindowTimes, psdSpectro = signal.spectrogram(
                                decimatedBuffer, 
                                Config.decimatedSampleRate, 
                                nperseg=Config.nSTFTSegment, 
                                noverlap=Config.nSTFTSegmentOverlap, 
                                window=stftWindow,
                                scaling="density",
                                mode="psd",
                                return_onesided=False)
        if display:
            display = False
            plt.pcolormesh(t, f, psdSpectro, shading='gouraud')
            plt.ylabel('Frequency [Hz]')
            plt.xlabel('Time [sec]')
            plt.show()
        logging.info("stft %s %d %d %d", psdSpectro.shape, Config.nSTFTSegment, Config.nDecimatedIntraPulse, Config.nDecimatedForKPulses)

        index = 0
        pulsePositions = numpy.zeros(psdSpectro.shape[1], dtype = numpy.int32)
        logging.info("Pulse positions %s", pulsePositions.shape)
        while index < pulsePositions.shape[0]:
            pulsePositions[index] = 1
            index += Config.nSTFTWindowsIntraPulse

        # Create empty incoherent sum position matrix
        summationMatrix = numpy.zeros((psdSpectro.shape[1], Config.nSTFTWindowsIntraPulse), dtype = numpy.int32)
        index = 0
        while index < Config.nSTFTWindowsIntraPulse:
            summationMatrix[:, index] = pulsePositions
            pulsePositions = numpy.roll(pulsePositions, 1)
            index += 1

        #allFreqs = numpy.sum(S, axis = 0)
        #incoSum = numpy.dot(allFreqs, summationMatrix)
        incoSum = numpy.dot(psdSpectro, summationMatrix)

        #plt.pcolormesh(t[:incoSum.shape[1]], stftFreqs, incoSum, shading='gouraud')
        #plt.ylabel('Frequency [Hz]')
        #plt.xlabel('Time [sec]')
        #plt.show()

        argmaxByFreq = numpy.argmax(incoSum, axis=1)
        maxFlattenedIndex = np.argmax(incoSum)
        row = math.floor(maxFlattenedIndex / incoSum.shape[1])
        col = maxFlattenedIndex % incoSum.shape[1]
        incoSumRow = incoSum[row]
        moving = numpy.convolve(incoSumRow, numpy.ones(3), "valid") / 3
        sRow = psdSpectro[row]
        freq = stftFreqs[row]
        logging.info("freq: %f time: %f", freq, stftWindowTimes[col])

        meanPSD = numpy.mean(psdSpectro, axis=1)

        # Reject pulse if it is not high enough above the noise floor
        
        pass

if __name__ == '__main__':
    pyTagDetector()