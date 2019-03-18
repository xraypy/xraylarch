#!/usr/bin/env python
'''
Diffraction functions require for fitting and analyzing data.

mkak 2017.02.06 (originally written spring 2016)
'''

##########################################################################
# IMPORT PYTHON PACKAGES

import numpy as np

##########################################################################
# FUNCTIONS

def xy_file_reader(xyfile):
    '''
    Parses (x,y) data from xy text file.

    options:
    char - chararacter separating columns in data file (e.g. ',')
    '''

    units = None
    x, y = [], []
    with open(xyfile) as f:
        for line in f.readlines():
            if '#' not in line:
                fields = line.split()
                x += [float(fields[0])]
                y += [float(fields[1])]
            else:
                for opt in ['2th_deg','q_A^-1']:
                    if opt in line: units = opt

    return np.array(x),np.array(y),units

##########################################################################
def xy_file_writer(a,b,filename,char=None):

    if char:
        str = '%s' + char + '%s\n'
    else:
        str = '%s %s\n'

    with open(filename,'w') as f:
        for i,ai in a:
            f.write(str % (ai,b[i]))

    return()
