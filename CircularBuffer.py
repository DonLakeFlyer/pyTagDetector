import numpy as np
import threading
import logging
import multiprocessing

class CircularBuffer:
    def __init__(self, name, capacity, dtype):
        self._name      = name
        self._capacity  = capacity
        self._dtype     = dtype
        self._buffer    = np.empty(capacity, dtype=dtype)
        self._headIndex = 0
        self._tailIndex = 0
        self._lock      = threading.Lock()
        self._itemCountCondition = multiprocessing.Condition()
        self._notifyItemCount    = 0
        logging.info("CircularBuffer: %s: %d", self._name, self._capacity)

    def capacity(self):
        return self._capacity
    
    def registerItemCountCondition(self, itemCount):
        self._notifyItemCount = itemCount
        return self._itemCountCondition

    def _read(self, nElements: int, peek):
        retIndex  = 0
        headIndex = self._headIndex
        ret       = np.empty(nElements, dtype = self._dtype)

        while nElements:
            cBufferLeft = self._capacity - headIndex
            elementsToRead = min(nElements, cBufferLeft)
            ret[retIndex: retIndex + elementsToRead] = self._buffer[headIndex : headIndex + elementsToRead]
            nElements   -= elementsToRead
            retIndex    += elementsToRead
            headIndex   += elementsToRead
            if headIndex == self._capacity:
                headIndex = 0

        if not peek:
            self._headIndex = headIndex
        return ret    

    def read(self, nElements: int, overlap: int = 0):
        logging.info("Reading samples from %s: readCount:unreadCount %d:%d", self._name, nElements, self.unreadCount())
        with self._lock:
            ret = np.empty(nElements, dtype = self._dtype)
            ret[:overlap] = self._read(overlap, True)
            nonOverlappedElements = nElements - overlap
            ret[overlap : overlap + nonOverlappedElements] = self._read(nonOverlappedElements, False)
        return ret

    def write(self, buffer):
        bufSize = len(buffer)
        #logging.info("Writing %d samples to %s", bufSize, self._name)
        with self._lock:
            if self._headIndex == self._tailIndex:
                roomLeft = self._capacity
            elif self._tailIndex > self._headIndex:
                roomLeft = self._headIndex + (self._capacity - self._tailIndex)
            else:
                roomLeft = self._headIndex - self._tailIndex
            if bufSize > roomLeft:
                logging.warning("Buffer overflow: %s Overwriting %d buffered samples %d:%d", self._name, bufSize - roomLeft, self._headIndex, self._tailIndex)
            bufIndex = 0
            while bufSize:
                cBufferLeft = self._capacity - self._tailIndex
                elementsToWrite = min(bufSize, cBufferLeft)
                self._buffer[self._tailIndex : self._tailIndex + elementsToWrite] = buffer[bufIndex : bufIndex + elementsToWrite]
                bufSize -= elementsToWrite
                bufIndex += elementsToWrite
                self._tailIndex += elementsToWrite
                if self._tailIndex == self._capacity:
                    self._tailIndex = 0
        if self._notifyItemCount and self.unreadCount() >= self._notifyItemCount:
            with self._itemCountCondition:
                self._itemCountCondition.notify()

    def reset(self):
        with self._lock:
            self._headIndex = 0
            self._tailIndex = 0

    def unreadCount(self):
        with self._lock:
            tailIndex = self._tailIndex
            if tailIndex < self._headIndex:
                tailIndex = self._capacity + tailIndex
            return tailIndex - self._headIndex
