"""
Utility functions used for xafs analysis
"""
import numpy as np

def nearest_index(array, value):
    "return index of array nearest value"
    return np.abs(array-value).argmin()

def realimag(arr, larch=None):
    "return real array of real/imag pairs from complex array"
    return np.array([(i.real, i.imag) for i in arr]).flatten()

def registerLarchPlugin():
    return ('_xafs', {'realimag': realimag})
