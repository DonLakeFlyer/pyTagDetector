from Config import *
from CircularBuffer import *
from DecimationThread import *

import threading
import numpy
import socket
import sys

class UDPReaderThread(threading.Thread):
    def __init__ (self):
        super().__init__()

        self._incomingBuffer    = CircularBuffer("Reader", Config.nIncomingForKPulses * 2, np.csingle)
        self.udpRXSocket        = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._decimationThread  = DecimationThread(self._incomingBuffer)

        self.udpRXSocket.bind((Config.udpIP, Config.udpPort))
        self._decimationThread.start()

    def run(self):
        while True:
            bytes = self.udpRXSocket.recvfrom(4096 * sys.getsizeof(numpy.csingle()))[0]
            buffer = numpy.frombuffer(bytes, dtype = numpy.csingle)
            self._incomingBuffer.write(buffer)

    def decimatedBuffer(self):
        return self._decimationThread.decimatedBuffer()
