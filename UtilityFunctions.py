import numpy

def movingAverage(x, cWindow):
    return numpy.convolve(x, numpy.ones(cWindow), "valid") / cWindow
