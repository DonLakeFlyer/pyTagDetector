from Config import *
from CircularBuffer import *

import threading
import numpy
import scipy
import math

class DecimationThread(threading.Thread):
    def __init__ (self, incomingBuffer: CircularBuffer):
        super().__init__()

        self._incomingBuffer        = incomingBuffer
        self._samplesPerDecimation  = Config.decimationFactor * 1000
        logging.info("DecimationThread: %d:%d", self._samplesPerDecimation, Config.incomingSampsForKPulses)
        self._countAfterDecimation  = math.floor(self._samplesPerDecimation / Config.decimationFactor)
        self._decimatedBuffer       = CircularBuffer("Decimator", Config.decimatedSampsForKPulses * 3, np.csingle)
        self._notifyCondition       = incomingBuffer.registerItemCountCondition(self._samplesPerDecimation)

    def decimatedBuffer(self):
        return self._decimatedBuffer
    
    def run(self):
        while True:
            with self._notifyCondition:
                while self._incomingBuffer.unreadCount() < self._samplesPerDecimation:
                    logging.info("DecimationThread: waiting for samples: unreadCount: %d", self._incomingBuffer.unreadCount())
                    self._notifyCondition.wait()
            decimatedBuffer = self._incomingBuffer.read(self._samplesPerDecimation)
            logging.info("DecimationThread: pre decimatedBuffer: %s", decimatedBuffer.shape)
            decimatedBuffer = scipy.signal.decimate(decimatedBuffer, 10, ftype='fir')
            decimatedBuffer = scipy.signal.decimate(decimatedBuffer, 10, ftype='fir')
            decimatedBuffer = scipy.signal.decimate(decimatedBuffer, 8, ftype='fir')
            logging.info("DecimationThread: decimatedBuffer: %s", decimatedBuffer.shape)
            self._decimatedBuffer.write(decimatedBuffer)
