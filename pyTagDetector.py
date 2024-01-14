from UDPReaderThread import *

import time
import logging
import numpy
from scipy import signal
from matplotlib import pyplot as plt
from mpl_toolkits.mplot3d import axes3d
from matplotlib import cm

def plotSingleFreqIndex(stftFreqs, stftBucketTimes, psdSpectr, freqIndex):
    plt.ylabel('Power')
    plt.xlabel('Time [sec]')
    plt.plot(stftBucketTimes, psdSpectr[freqIndex])
    plt.show()

def plotSurface(stftFreqs, stftBucketTimes, psdSpectro):
    plt.xlabel('Frequency [Hz]')
    plt.ylabel('Time [sec]')
    fig             = plt.figure()
    ax              = fig.add_subplot(projection='3d')
    nSTFTFreqs      = stftFreqs.shape[0]
    nSTFTBuckets    = stftBucketTimes.shape[0]
    ax.plot_surface(stftFreqs[:, None], stftBucketTimes[None, :], psdSpectro, cmap=cm.coolwarm, rcount=nSTFTFreqs, ccount=nSTFTBuckets)
    plt.show()        

def plotColorMesh(stftFreqs, stftBucketTimes, psdSpectro):
    plt.pcolormesh(stftBucketTimes, stftFreqs, psdSpectro, shading='gouraud')
    plt.ylabel('Frequency [Hz]')
    plt.xlabel('Time [sec]')
    plt.show()   

def plot(stftFreqs, stftBucketTimes, psdSpectro):
    plotColorMesh(stftFreqs, stftBucketTimes, psdSpectro)

def pyTagDetector():
    logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s |  %(filename)s:%(lineno)d')

    udpReader = UDPReaderThread()
    udpReader.start()

    notifyCondition = udpReader.decimatedBuffer().registerItemCountCondition(Config.nDecimatedForKPulsesWithOverlap)

    stftWindow = signal.windows.boxcar(Config.nSTFTSegmentForSinglePulse)

    logging.info("%d %d", Config.nDecimatedForKPulses, Config.nSTFTSegmentForSinglePulseOverlap)

    display = False
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
        #   rows are frequencies (axis = 0)
        #   columns are time windows (axis = 1)
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
            plot(stftFreqs, stftBucketTimes, psdSpectro)
        logging.info("stft shape(%s) %d %d %d", psdSpectro.shape, Config.nSTFTSegmentForSinglePulse, Config.nDecimatedIntraPulse, Config.nDecimatedForKPulses)

        # Calculate a noise average for each frequency row in the STFT. Excluding the pulse positions
        #   The noise average is calculated by averaging the power in each bucket in the row
            
        avgNoiseByFreq = numpy.average(psdSpectro, axis = 0)

        # Shift the STFT values up by the noise average such that we now have positive and negative values.
        # Then when we do the incoherent sum the random noise portions of the signal will cancel each other out to some extent.
        # Whereas the pulse portions of the signal will add up constructively.         


        # Create initial pulse position matrix:
        #   It is as large as there are stft buckets
        #   There is a 1 in the position of the buckets which may contain a possible pulse
        #   Iniitially, the first bucket of each pulse is the first bucket of the STFT

        pulseBucketPositions = numpy.zeros(nSTFTBuckets, dtype = numpy.int32)
        index = 0
        while index < nSTFTBuckets:
            pulseBucketPositions[index] = 1
            index += Config.nSTFTBucketsIntraPulse

        # Create two dimensional incoherent sum matrix by shifting the pulse position matrix by one bucket at a time
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
            plot(stftFreqs, stftBucketTimes[:incoSum.shape[1]], incoSum)

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
        moving = numpy.convolve(incoSumRow, numpy.ones(3), "valid") / 3
        sRow = psdSpectro[freqIndex]
        freq = stftFreqs[freqIndex]

        # Calculate the average noise level in incoSum at freqIndex
        # Mask out the position of the pulse using weights
        maxFreqData = incoSum[freqIndex, :]
        weights = numpy.ones(maxFreqData.shape)
        weights[max(0, timeIndex-1) : min(weights.shape[0], timeIndex+2)] = 0
        print(timeIndex, weights)
        avgNoise = numpy.average(maxFreqData)
        avgNoise = numpy.average(maxFreqData, weights=weights)

        maxPower = incoSum[freqIndex, timeIndex]
        logging.info("MAX freq: %f time: %f value: %e noise: %e snr: %e freqIndex: %d", freq, stftBucketTimes[timeIndex], maxPower, avgNoise, 10 * math.log((maxPower - avgNoise) / avgNoise), freqIndex)

        #plotSingleFreqIndex(stftFreqs, stftBucketTimes[0:incoSum.shape[1]], incoSum, freqIndex)
        plotSingleFreqIndex(stftFreqs, stftBucketTimes, psdSpectro, freqIndex)
        delta = 20
        #plotSurface(stftFreqs[freqIndex-delta:freqIndex+delta], stftBucketTimes, psdSpectro[freqIndex-delta:freqIndex+delta, :])

        # Look for the peak of the next pulse
        nextPulseTimeIndex = timeIndex + Config.nSTFTBucketsIntraPulse
        pulseBucketFudge = 5
        nextPulseBuckets = psdSpectro[freqIndex, nextPulseTimeIndex-pulseBucketFudge:nextPulseTimeIndex+pulseBucketFudge]
        maxIndex = numpy.argmax(nextPulseBuckets)
        nextPulseTimeIndex = nextPulseTimeIndex - pulseBucketFudge + maxIndex
        logging.info("NEXT time: %f delta: %f value: %e", stftBucketTimes[nextPulseTimeIndex], stftBucketTimes[timeIndex] - stftBucketTimes[nextPulseTimeIndex], nextPulseBuckets[maxIndex])

        # Reject pulse if it is not high enough above the noise floor
        
        pass

if __name__ == '__main__':
    pyTagDetector()