from Config import *
from CircularBuffer import *

import threading
import numpy
from scipy import signal
import math

class DecimationThread(threading.Thread):
    def __init__ (self, incomingBuffer: CircularBuffer):
        super().__init__()

        self._incomingBuffer        = incomingBuffer
        self._samplesPerDecimation  = Config.decimationFactor * 1000
        self._countAfterDecimation  = math.floor(self._samplesPerDecimation / Config.decimationFactor)
        self._decimatedBuffer       = CircularBuffer("Decimator", Config.nDecimatedForOnePulse * 2, np.csingle)
        self._notifyCondition       = incomingBuffer.registerItemCountCondition(self._samplesPerDecimation)

    def decimatedBuffer(self):
        return self._decimatedBuffer
    
    def run(self):
        while True:
            with self._notifyCondition:
                while self._incomingBuffer.unreadCount() < self._samplesPerDecimation:
                    logging.debug("DecimationThread: waiting for samples: unreadCount: %d", self._incomingBuffer.unreadCount())
                    self._notifyCondition.wait()
            decimatedBuffer = self._incomingBuffer.read(self._samplesPerDecimation)
            decimatedBuffer = signal.decimate(decimatedBuffer, 10, ftype='fir')
            decimatedBuffer = signal.decimate(decimatedBuffer, 10, ftype='fir')
            decimatedBuffer = signal.decimate(decimatedBuffer, 8, ftype='fir')
            #decimatedBuffer = signal.decimate(decimatedBuffer, 2, ftype='fir')
            self._decimatedBuffer.write(decimatedBuffer)
