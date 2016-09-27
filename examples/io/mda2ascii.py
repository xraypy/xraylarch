#!/usr/bin/env python

import sys, os
import string
import mda

def mdaAscii_2D(d,row=None):
    """
    mdaAscii_2D(d) - for input specified MDA scan data structure d, this function
    will automatically generate separate 2D ASCII text file for each extract 2D image array,
    it will return the last 2D ASCII text file name created

    e.g.
    The 2idd_0004.mda contains 2D array:

            from mdaAscii import *
            d = readMDA("2idd_0004.mda")
            fn = mdaAscii_2D(d)
    """
#       print d[0].keys()
    path,fname = os.path.split(d[0]['filename'])
    froot = string.split(fname,'.mda')
    if os.path.exists('ASCII') == 0 :
        os.mkdir('ASCII')
    dir = os.getcwd()
    ofname = dir+os.sep+'ASCII'+ os.sep + froot[0]+'.'

    # number of positioners, detectors
    np = d[2].np
    nd = d[2].nd
    if nd == 0 : return
    min_column_width = 16
    # make sure there's room for the names, etc.
    nx = d[2].curr_pt
    ny = d[1].npts
    for i in range(np):
        print i, d[2].p[i].name,d[2].p[i].desc,d[2].p[i].unit
#               print type(d[2].p[i].data)
    py = d[1].p[0].data
    px = d[2].p[0].data
    px = px[0]
    for i in range(nd):
        imfile = ofname+d[2].d[i].fieldName+'.txt'
        print imfile
        fo = open(imfile,"w")
        fo.write('# Image from: '+d[0]['filename'] +'\n')
        fo.write('# Detector: '+d[2].d[i].fieldName +', '+
                 d[2].d[i].name+', '+
                 d[2].d[i].desc+', '+
                 d[2].d[i].unit)
        fo.write('\n# dim('+ str(nx)+','+str(ny)+')\n')

        if row != None:
            fo.write(('# X:'),)
            for j in range(nx):
                fo.write( ('%18.7f' % px[j]),)
            fo.write('\n')

        fo.write(('#              (yvalues):'),)
        for j in range(ny):
            fo.write( ('%18.7f' % py[j]),)
        fo.write('\n')

        if row != None:
            fo.write(('# I:'),)
            for j in range(nx):
                fo.write( ('%18d' % j),)
            fo.write('\n')
            data = d[2].d[i].data
            for j in range(ny):
                for k in range(nx):
                    fo.write(('%18.7f' % data[j][k]),)
                fo.write('\n')
        else:
            fo.write(('#                   \ (J)'),)
            for j in range(ny):
                fo.write( ('%18d' % (j+1)),)
            fo.write(('\n#      (xvalues)    (I) \    '),)
            fo.write('\n')
            data = d[2].d[i].data
            for j in range(nx):
                fo.write( (('%18.7f %6d') % (px[j],(j+1))),)
                for k in range(ny):
                    if k < d[1].curr_pt:
                        fo.write(('%18.7f' % data[k][j]),)
                    else:
                        fo.write(('%18.7f' % 0.),)
                fo.write('\n')
        fo.close()
    return imfile


def mdaAscii_1D(d):
    """
    mdaAscii_1D(d) - for input specified MDA scan data structure d, this function
    will generate 1D ASCII text file for 1D data array detected,
    it returns the 1D ASCII text file name created

    e.g.
    The 2idd_0004.mda contains 1D array:

            from mdaAscii import *
            d = readMDA("2idd_0004.mda")
            fn = mdaAscii_1D(d)
    """
    # number of positioners, detectors
    np = d[1].np
    nd = d[1].nd

    min_column_width = 18
    # make sure there's room for the names, etc.
    phead_format = []
    dhead_format = []
    pdata_format = []
    ddata_format = []
    columns = 1
    for i in range(np):
        cw = max(min_column_width, len(d[1].p[i].name)+1)
        cw = max(cw, len(d[1].p[i].desc)+1)
        cw = max(cw, len(d[1].p[i].fieldName)+1)
        phead_format.append("%%-%2ds " % cw)
        pdata_format.append("%%- %2d.8f " % cw)
        columns = columns + cw + 1
    for i in range(nd):
        cw = max(min_column_width, len(d[1].d[i].name)+1)
        cw = max(cw, len(d[1].d[i].desc)+1)
        cw = max(cw, len(d[1].d[i].fieldName)+1)
        dhead_format.append("%%-%2ds " % cw)
        ddata_format.append("%%- %2d.8f " % cw)
        columns = columns + cw + 1

    path,fname = os.path.split(d[0]['filename'])
    froot = string.split(fname,'.mda')
    if os.path.exists('ASCII') == 0 :
        os.mkdir('ASCII')
    dir = os.getcwd()
    ofname = dir +os.sep+'ASCII'+ os.sep + froot[0]+'.1d.txt'
    print ofname

    cr = '\n'
    fo = open(ofname,'w')
    for i in d[0].keys():
        if (i != 'sampleEntry'):
            fo.write( "# "+ str(i)+ ' '+ str(d[0][i])+cr)

    fo.write( "#\n# "+ str(d[1])+cr)
    fo.write( "#  scan time: "+ d[1].time+cr)
    sep = "#"*columns
    fo.write( sep+cr)

    # print table head

    fo.write( "# ",)
    for j in range(np):
        fo.write( phead_format[j] % (d[1].p[j].fieldName),)
    for j in range(nd):
        fo.write( dhead_format[j] % (d[1].d[j].fieldName),)
    fo.write(cr)

    fo.write( "# ",)
    for j in range(np):
        fo.write( phead_format[j] % (d[1].p[j].name),)
    for j in range(nd):
        fo.write( dhead_format[j] % (d[1].d[j].name),)
    fo.write(cr)

    fo.write( "# ",)
    for j in range(np):
        fo.write( phead_format[j] % (d[1].p[j].desc),)
    for j in range(nd):
        fo.write( dhead_format[j] % (d[1].d[j].desc),)
    fo.write(cr)

    fo.write( "# ",)
    for j in range(np):
        fo.write( phead_format[j] % (d[1].p[j].unit),)
    for j in range(nd):
        fo.write( dhead_format[j] % (d[1].d[j].unit),)
    fo.write(cr)

    fo.write( sep+cr)

    for i in range(d[1].curr_pt):
        fo.write( "",)
        for j in range(d[1].np):
            fo.write( pdata_format[j] % (d[1].p[j].data[i]),)
        for j in range(d[1].nd):
            fo.write( ddata_format[j] % (d[1].d[j].data[i]),)
        fo.write(cr)
    fo.close()

    return ofname


def mdaAscii_2D1D(d,start=None,stop=None):
    """
        mdaAscii_2D1D(d,start=None,stop=None) - for input specified MDA scan data structure d,
        based on user specified index range this function will generate sequential
        1D ASCII text files extrcated from 2D data array detected in data stucture d,
        it returns the last 1D ASCII text file name created

        where
          start - specifies the beginning sequence number, default 0
          stop  - specifies the ending sequence number, default the last

        e.g.
        The 2idd_0004.mda contains 2D array:

                from mdaAscii import *
                d = readMDA("2idd_0004.mda")
                fn = mdaAscii_2D1D(d)
    """
    if d[0]['rank'] < 2 : return
    # number of positioners, detectors
    else:
        np = d[2].np
        nd = d[2].nd
        if nd == 0: return

        min_column_width = 18
        # make sure there's room for the names, etc.
        phead_format = []
        dhead_format = []
        pdata_format = []
        ddata_format = []
        columns = 1
        for i in range(np):
            cw = max(min_column_width, len(d[2].p[i].name)+1)
            cw = max(cw, len(d[2].p[i].desc)+1)
            cw = max(cw, len(d[2].p[i].fieldName)+1)
            phead_format.append("%%-%2ds " % cw)
            pdata_format.append("%%- %2d.8f " % cw)
            columns = columns + cw + 1
        for i in range(nd):
            cw = max(min_column_width, len(d[2].d[i].name)+1)
            cw = max(cw, len(d[2].d[i].desc)+1)
            cw = max(cw, len(d[2].d[i].fieldName)+1)
            dhead_format.append("%%-%2ds " % cw)
            ddata_format.append("%%- %2d.8f " % cw)
            columns = columns + cw + 1

    if start == None: start=0
    if stop == None: stop = d[1].curr_pt
    for k in range(start,stop):
        path,fname = os.path.split(d[0]['filename'])
        froot = string.split(fname,'.mda')
        if os.path.exists('ASCII') == 0 :
            os.mkdir('ASCII')
        dir = os.getcwd()
        ofname = dir +os.sep+'ASCII'+ os.sep + froot[0]+'.1d_'+str(k+1)+'.txt'
        print ofname

        cr = '\n'
        fo = open(ofname,'w')
        for i in d[0].keys():
            if (i != 'sampleEntry'):
                fo.write( "# "+ str(i)+ ' '+ str(d[0][i])+cr)

        fo.write( "#\n# "+ str(d[2])+cr)
        fo.write( "# 2D SCAN (zero based) Line Sequence # ="+str(k) + cr)
        fo.write( "#  scan time: "+ d[2].time+cr)
        sep = "#"*columns
        fo.write( sep+cr)

        # print table head

        fo.write( "# ",)
        for j in range(np):
            fo.write( phead_format[j] % (d[2].p[j].fieldName),)
        for j in range(nd):
            fo.write( dhead_format[j] % (d[2].d[j].fieldName),)
        fo.write(cr)

        fo.write( "# ",)
        for j in range(np):
            fo.write( phead_format[j] % (d[2].p[j].name),)
        for j in range(nd):
            fo.write( dhead_format[j] % (d[2].d[j].name),)
        fo.write(cr)

        fo.write( "# ",)
        for j in range(np):
            fo.write( phead_format[j] % (d[2].p[j].desc),)
        for j in range(nd):
            fo.write( dhead_format[j] % (d[2].d[j].desc),)
        fo.write(cr)

        fo.write( "# ",)
        for j in range(np):
            fo.write( phead_format[j] % (d[2].p[j].unit),)
        for j in range(nd):
            fo.write( dhead_format[j] % (d[2].d[j].unit),)
        fo.write(cr)

        fo.write( sep+cr)

        for i in range(d[2].curr_pt):
            fo.write( "",)
            for j in range(d[2].np):
                fo.write( pdata_format[j] % (d[2].p[j].data[k][i]),)
            for j in range(d[2].nd):
                fo.write( ddata_format[j] % (d[2].d[j].data[k][i]),)
            fo.write(cr)

        fo.close()

    return ofname

def mdaAsciiReport(fname):
    d = readMDA(fname,2)
    dim = d[0]['rank']
    if dim == 1:
        if d[1].nd > 0:
            ofname = mdaAscii_1D(d)
            return ofname
    if dim > 1:
        if d[1].nd > 0:
            ofname = mdaAscii_1D(d)
        if d[2].nd > 0:
            ofname = mdaAscii_2D(d)
            return ofname


def convert_to_ASCII(filename, dim=1):
    mdadata = mda.readMDA(filename)
    converter =  mdaAscii_1D
    if dim == 2:
        converter = mdaAscii_2D
    return converter(mdadata)

    
if __name__ == '__main__':
    import mda
    import sys
    for fname in sys.argv[1:]:
        convert_to_ASCII(fname)
        
    
