from UDPReaderThread import *

import time
import logging
import numpy
from scipy import signal
from matplotlib import pyplot as plt
from mpl_toolkits.mplot3d import axes3d
from matplotlib import cm

def pyTagDetector():
    logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s |  %(filename)s:%(lineno)d')

    udpReader = UDPReaderThread()
    udpReader.start()

    notifyCondition = udpReader.decimatedBuffer().registerItemCountCondition(Config.nDecimatedForKPulsesWithOverlap)

    stftWindow = signal.windows.boxcar(Config.nSTFTSegmentForSinglePulse)

    logging.info("%d %d", Config.nDecimatedForKPulses, Config.nSTFTSegmentForSinglePulseOverlap)

    display = True
    waitCount = 1

    while True:
        # Wait for enough samples to be decimated to cover the K group
        with notifyCondition:
            while udpReader.decimatedBuffer().unreadCount() < Config.nDecimatedForKPulsesWithOverlap:
                notifyCondition.wait()

        decimatedBuffer = udpReader.decimatedBuffer().read(Config.nDecimatedForKPulses, Config.nDecimatedOverlap)
        if waitCount < 3:
            waitCount += 1
            continue 

        # Compute the STFT for the decimated samples:
        #   psdSpecro is a 2D array of shape (frequencies, windows)
        #   rows are frequencies
        #   columns are time windows
        stftFreqs, stftBucketTimes, psdSpectro = signal.spectrogram(
                                decimatedBuffer, 
                                Config.decimatedSampleRate, 
                                nperseg         = Config.nSTFTSegmentForSinglePulse, 
                                noverlap        = Config.nSTFTSegmentForSinglePulseOverlap, 
                                window          = stftWindow,
                                scaling         = "density",
                                mode            = "psd",
                                return_onesided =False)
        nSTFTFreqs      = stftFreqs.shape[0]
        nSTFTBuckets    = stftBucketTimes.shape[0]
        
        if display:
            #display = False
            #plt.pcolormesh  (stftBucketTimes, stftFreqs, psdSpectro, shading='gouraud')
            plt.xlabel      ('Frequency [Hz]')
            plt.ylabel      ('Time [sec]')
            fig = plt.figure()
            ax = fig.add_subplot(projection='3d')
            #ax = fig.gca(projection='3d')

            # Grab some test data.
            #X, Y, Z = axes3d.get_test_data(0.05)

            # Plot a basic wireframe.
            #ax.plot_wireframe(stftFreqs, stftBucketTimes, psdSpectro, rstride=10, cstride=10)
            ax.plot_surface(stftFreqs[:, None], stftBucketTimes[None, :], psdSpectro, cmap=cm.coolwarm)
            plt.show()        
        logging.info("stft shape(%s) %d %d %d", psdSpectro.shape, Config.nSTFTSegmentForSinglePulse, Config.nDecimatedIntraPulse, Config.nDecimatedForKPulses)

        # Create initial pulse position matrix:
        #   It is as large as there are stft buckets
        #   There is a 1 in the position of the buckets which may contain a possible pulse
        #   Iniitially, the first bucket of each pulse is the first bucket of the STFT

        pulseBucketPositions = numpy.zeros(nSTFTBuckets, dtype = numpy.int32)
        index = 0
        while index < nSTFTBuckets:
            pulseBucketPositions[index] = 1
            index += Config.nSTFTBucketsIntraPulse

        # Create two dimensional incoherent sum matrix:
        #   1, 0, ..., 0
        #   0, 1, ..., 0
        #   ...
        #   0, 0, ..., 1
        #
        #   There is a column for each possible pulse position k group in time

        summationMatrix = numpy.zeros((nSTFTBuckets, Config.nSTFTBucketsIntraPulse), dtype = numpy.int32)
        index = 0
        while index < Config.nSTFTBucketsIntraPulse:
            summationMatrix[:, index] = pulseBucketPositions
            pulseBucketPositions = numpy.roll(pulseBucketPositions, 1)  # Shift the pulse positions by one bucket
            index += 1

        incoSum = numpy.dot(psdSpectro, summationMatrix)

        if display:
            plt.pcolormesh  (stftBucketTimes[:incoSum.shape[1]], stftFreqs, incoSum, shading='gouraud')
            plt.ylabel      ('Frequency [Hz]')
            plt.xlabel      ('Time [sec]')
            plt.show        ()

        #plt.pcolormesh(t[:incoSum.shape[1]], stftFreqs, incoSum, shading='gouraud')
        #plt.ylabel('Frequency [Hz]')
        #plt.xlabel('Time [sec]')
        #plt.show()

        argmaxByFreq = numpy.argmax(incoSum, axis=1)
        maxFlattenedIndex = numpy.argmax(incoSum)
        sortedFlattenedIndex = numpy.argsort(incoSum, axis=None)[::-1]
        for index in range(10):
            maxIndex = sortedFlattenedIndex[index]
            maxFreqIndex = math.floor(maxIndex / incoSum.shape[1])
            maxTimeIndex = maxIndex % incoSum.shape[1]
            logging.info("SORTED freq: %f time: %f value: %e", stftFreqs[maxFreqIndex], stftBucketTimes[maxTimeIndex], incoSum[maxFreqIndex, maxTimeIndex])
        freqIndex = math.floor(maxFlattenedIndex / incoSum.shape[1])
        timeIndex = maxFlattenedIndex % incoSum.shape[1]
        incoSumRow = incoSum[freqIndex]
        slice = incoSum[freqIndex-5:freqIndex+5, :]
        #print(slice)
        moving = numpy.convolve(incoSumRow, numpy.ones(3), "valid") / 3
        sRow = psdSpectro[freqIndex]
        freq = stftFreqs[freqIndex]
        logging.info("MAX freq: %f time: %f value: %e", freq, stftBucketTimes[timeIndex], incoSum[freqIndex, timeIndex])

        meanPSD = numpy.mean(psdSpectro, axis=1)

        # Reject pulse if it is not high enough above the noise floor
        
        pass

if __name__ == '__main__':
    pyTagDetector()