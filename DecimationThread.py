from Config import *
from CircularBuffer import *

import threading
import numpy
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
            rawBuffer = self._incomingBuffer.read(self._samplesPerDecimation)
            decimatedBuffer = np.empty(self._countAfterDecimation, dtype=np.single)
            self._decimatedBuffer.write(decimatedBuffer)
