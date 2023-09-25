from UDPReaderThread import *

import time
import logging

def pyTagTracker():
    logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s |  %(filename)s:%(lineno)d')

    udpReader = UDPReaderThread()
    udpReader.start()

    notifyCondition = udpReader.decimatedBuffer().registerItemCountCondition(Config.decimatedSampsForKPulses)

    while True:
        with notifyCondition:
            while udpReader.decimatedBuffer().unreadCount() < Config.decimatedSampsForKPulses:
                notifyCondition.wait()
        decimatedBuffer = udpReader.decimatedBuffer().read(Config.decimatedSampsForKPulses)

if __name__ == '__main__':
    pyTagTracker()