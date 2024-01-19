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
    #plt.show()

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

def buildSummationMatrix(nSTFTBuckets):
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
    summationMatrix = numpy.zeros((nSTFTBuckets, nSTFTBuckets), dtype = numpy.int32)
    index = 0
    while index < nSTFTBuckets:
        summationMatrix[:, index] = pulseBucketPositions
        pulseBucketPositions = numpy.roll(pulseBucketPositions, 1)  # Shift the pulse positions by one bucket
        index += 1
    
    return summationMatrix

def pyTagDetector():
    logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s |  %(filename)s:%(lineno)d')

    udpReader = UDPReaderThread()
    udpReader.start()

    notifyCondition = udpReader.decimatedBuffer().registerItemCountCondition(Config.nDecimatedForOnePulse)

    stftWindow = signal.windows.boxcar(Config.nSTFTSegmentForSinglePulse)

    display = False
    k = 1

    while True:
        # Wait for enough samples to be decimated to cover one pulse group
        with notifyCondition:
            while udpReader.decimatedBuffer().unreadCount() < Config.nDecimatedForOnePulse:
                notifyCondition.wait()

        decimatedSamples = udpReader.decimatedBuffer().read(Config.nDecimatedForOnePulse, Config.nDecimatedOverlap)

        # Compute the STFT for the decimated samples:
        #   psdSpecro is a 2D array of shape (frequencies, windows)
        #   rows are frequencies (axis = 0)
        #   columns are time windows (axis = 1)
        stftFreqs, stftBucketTimes, psdSpectro = signal.spectrogram(
                                decimatedSamples, 
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
        #logging.info("stft shape(%s) %d %d %d", psdSpectro.shape, Config.nSTFTSegmentForSinglePulse, Config.nDecimatedIntraPulse, Config.nDecimatedForOnePulse)

        if k > 1:
            summationMatrix = buildSummationMatrix(nSTFTBuckets) # Can we move this outside the loop?
            numpy.concatenate((incoherentSum, psdSpectro), axis=1)
            incoherentSum = numpy.dot(psdSpectro, summationMatrix)
        else:
            incoherentSum = psdSpectro

        if display:
            plot(stftFreqs, stftBucketTimes[:incoherentSum.shape[1]], incoherentSum)

        maxFlattenedIndex = numpy.argmax(incoherentSum)
        #sortedFlattenedIndex = numpy.argsort(incoherentSum, axis=None)[::-1]
        #for index in range(10):
        #    maxIndex = sortedFlattenedIndex[index]
        #    maxFreqIndex = math.floor(maxIndex / incoherentSum.shape[1])
        #    maxTimeIndex = maxIndex % incoherentSum.shape[1]
        #    logging.info("SORTED freq: %f time: %f value: %e", stftFreqs[maxFreqIndex], stftBucketTimes[maxTimeIndex], incoherentSum[maxFreqIndex, maxTimeIndex])
        freqIndex = math.floor(maxFlattenedIndex / incoherentSum.shape[1])
        timeIndex = maxFlattenedIndex % incoherentSum.shape[1]
        incoherentSumRow = incoherentSum[freqIndex]
        slice = incoherentSum[freqIndex-5:freqIndex+5, :]
        moving = numpy.convolve(incoherentSumRow, numpy.ones(3), "valid") / 3
        sRow = psdSpectro[freqIndex]
        freq = stftFreqs[freqIndex]

        # Calculate the average noise level in incoherentSum at freqIndex
        # Mask out the position of the pulse using weights
        maxFreqData = incoherentSum[freqIndex, :]
        weights = numpy.ones(maxFreqData.shape)
        weights[max(0, timeIndex-1) : min(weights.shape[0], timeIndex+2)] = 0
        avgNoise = numpy.average(maxFreqData)
        avgNoise = numpy.average(maxFreqData, weights=weights)

        maxPower = incoherentSum[freqIndex, timeIndex]
        logging.info("MAX k: %d freq: %f time: %f value: %e noise: %e snr: %e freqIndex: %d", k, freq, stftBucketTimes[timeIndex], maxPower, avgNoise, 10 * math.log((maxPower - avgNoise) / avgNoise), freqIndex)

        plotSingleFreqIndex(stftFreqs, stftBucketTimes[0:incoherentSum.shape[1]], incoherentSum, 133) #freqIndex)
        #plotSingleFreqIndex(stftFreqs, stftBucketTimes, psdSpectro, freqIndex)
        delta = 20
        #plotSurface(stftFreqs[freqIndex-delta:freqIndex+delta], stftBucketTimes, psdSpectro[freqIndex-delta:freqIndex+delta, :])

        # Look for the peak of the next pulse
        #nextPulseTimeIndex = timeIndex + Config.nSTFTBucketsIntraPulse
        #pulseBucketFudge = 5
        #nextPulseBuckets = psdSpectro[freqIndex, nextPulseTimeIndex-pulseBucketFudge:nextPulseTimeIndex+pulseBucketFudge]
        #maxIndex = numpy.argmax(nextPulseBuckets)
        #nextPulseTimeIndex = nextPulseTimeIndex - pulseBucketFudge + maxIndex
        #logging.info("NEXT time: %f delta: %f value: %e", stftBucketTimes[nextPulseTimeIndex], stftBucketTimes[timeIndex] - stftBucketTimes[nextPulseTimeIndex], nextPulseBuckets[maxIndex])

        # Reject pulse if it is not high enough above the noise floor
        
        # Restart summation grouping after specific number of groups
        k += 1
        if k > 2: #Config.kEnd:
            plt.show()
            k = 1

if __name__ == '__main__':
    pyTagDetector()