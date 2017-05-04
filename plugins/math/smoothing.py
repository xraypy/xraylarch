#!/usr/bin/env python
"""
Smoothing routines
"""
from larch.utils import savitzky_golay, smooth, boxcar

def registerLarchPlugin():
    return ('_math', dict(savitzky_golay=savitzky_golay,
                          smooth=smooth,
                          boxcar=boxcar))
