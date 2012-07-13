"""
Read/Write CARS mca/med files


Authors/Modifications:
----------------------
* Mark Rivers, GSECARS
* See http://cars9.uchicago.edu/software/python/index.html
* Modified for Tdl, tpt

"""

#########################################################################

import numpy as np
import os

from mca import Mca
from med import Med
from roi import Roi

########################################################################
class Environment:
    """
    The "environment" or related parameters for a detector.  These might include
    things like motor positions, temperature, anything that describes the
    experiment.

    Attributes:
    -----------
    * name         # A string name of this parameter, e.g. "13IDD:m1"
    * description  # A string description of this parameter, e.g. "X stage"
    * value        # A string value of this parameter,  e.g. "14.223"
    """
    def __init__(self, name='', value='', description=''):
        self.name        = name
        self.value       = value
        self.description = description

##############################################################################
def read_med_files(file_prefix,start=0,end=100,nfmt=3,
                   bad_mca_idx=[],total=True,align=True,correct=True,tau=None):
    """
    Read multiple files given prefix, start and end numbers and fmt len
    """
    med = []
    format = '%' + str(nfmt) + '.' + str(nfmt) + 'd'
    for j in range(start,end+1):
        ext   = format % j
        file  = file_prefix + '.' + ext
        tmp   = read_med(file,bad_mca_idx=bad_mca_idx,total=total,
                         align=align, correct=correct,tau=tau)
        med.append(tmp)
    return med

##############################################################################
def read_med(file,bad_mca_idx=[],total=True,align=True,correct=True,tau=None):
    """
    Reads a disk file into an Med object. The file contains the information
    from the Med object which makes sense to store permanently, but does
    not contain all of the internal state information for the Med.

    Parameters:
    -----------
    * file: The name of the disk file to read.

    Notes:
    ------
    * If the file includes "Environment data" these wil lbe included
      in the returned object as med.environment
    * If the file includes ROI's the will be included with the mca's
      in the returned object as med.mca[i].rois

    """
    # read the file
    r = read_ascii_file(file)
    if r == None: return None

    # some info
    n_detectors = r['n_detectors']
    path, fname = os.path.split(file)

    # check for boge detectors
    check_det = True
    if check_det == True:
        for j in range(n_detectors):
            if r['mca'][j].total_counts < 1.:
                if j not in bad_mca_idx:
                    bad_mca_idx.append(j)
        bad_mca_idx.sort()

    # build the med object
    med = Med(name=fname, mca=r['mca'], bad_mca_idx=bad_mca_idx,
              total=total, align=align, correct=correct, tau=tau)

    # below are set only if defined in file
    if r['max_rois'] > 0:
        rois = r['rois']
        for d in range(n_detectors):
            med.mca[d].rois = rois[d]
    if len(r['environment']) > 0:
        med.environment = r['environment']

    return med

##############################################################################
def read_mca_files(file_prefix,start=0,end=100,nfmt=3,
                   detector=0,tau=None):
    """
    Read multiple files given prefix, start and end numbers and fmt len
    """
    data = []
    format = '%' + str(nfmt) + '.' + str(nfmt) + 'd'
    for j in range(start,end+1):
        ext   = format % j
        file  = file_prefix + '.' + ext
        tmp   = read_mca(file,detector=detector,tau=tau)
        data.append(tmp)
    return data

#############################################################################
def read_mca(file, detector=0, tau=None):
    """
    Reads a disk file into an MCA object.
    If the data file has multiple detectors then the detector
    keyword can be used to specify which detector data to return.

    Parameters:
    * file: The name of the disk file to read.
    * detector: Index of detector to read

    Notes.
    ------
    * If the file includes "Environment data" these wil lbe included
      in the returned object as mca.environment
    * If the file includes ROI's the will be included with the mca's
      in the returned object as mca.rois

    """
    r = read_ascii_file(file)
    if r == None: return None

    path, fname = os.path.split(file)
    data = r['mca'][detector]
    data.update_correction(tau=tau)

    # below are set only if defined in file
    if r['max_rois'] > 0:
        rois = r['rois']
        data.rois = rois[detector]
    if len(r['environment']) > 0:
        data.environment = r['environment']

    return data

########################################################################
def read_ascii_file(file):
    """
    Reads a disk file.  The file is a tagged ASCII format.

    The file contains the information from the Mca object which it makes sense
    to store permanently, but does not contain all of the internal state
    information for the Mca.  This procedure reads files written with
    write_ascii_file().

    Parameters:
    -----------
    * file: The name of the disk file to read.

    Outputs:
    --------
    * Returns a dictionary of the following type:
      r['n_detectors'] = n_detectors
      r['mca'] = [Mca()]
      r['rois'] = [Roi.Roi()]
      r['environment'] = [Environment]

    Example:
    --------
    >>m = read_ascii_file('mca.001')
    >>m['elapsed'][0].real_time
    """
    try:
        fp = open(file, 'r')
        lines = fp.readlines()
        fp.close()
    except:
        print "File '%s' not found" % file
        return None

    rois = {}
    header = {}
    environment = []
    mcas = []
    data = []
    mode = None
    for line in lines:
        line = line[:-1].strip()
        if len(line) < 1:
            continue
        if mode == 'data':
            data.append([int(i) for i in line.split()])
            continue
        if ':' not in line:
            continue
        key, val = line.split(':', 1)
        key = key.lower()
        if key == 'data':
            mode = 'data'
        elif key in ('version', 'date'):
            header[key] = val
        elif key in ('elements', 'channels'):
            header[key]  = int(val)
        elif key == 'rois':
            header['rois']  = [int(v) for v in val.split()]
        elif key in ('real_time', 'live_time', 'input_counts', 'tau',
                     'cal_slope', 'cal_offset', 'cal_quad', 'two_theta'):
            header[key] = [float(v) for v in val.split()]
        elif key.startswith('roi_'):
            k, index, tag = key.split('_')
            index = int(index)
            if index not in rois: rois[index] = {}
            if tag in ('left', 'right'):
                rois[index][tag] = [float(v) for v in val.split()]
            elif tag == 'label':
                rois[index]['label'] = [v for v in val.split('&')]
        elif key == 'environment':
            env = Environment()
            env.name, val = val.split('="')
            val, desc  = val.split('"')
            desc.strip()
            if desc.startswith('(') and desc.endswith(')'):
                desc = desc[1:-1]
            env.value = val
            env.description = desc
            environment.append(env)
    ######
    data = np.array(data).transpose()

    for det in range(header['elements']):
        mcas.append(Mca(name='mca%i' % det, nchans=header['channels']))
        for key in ('real_time', 'live_time', 'input_counts', 'tau',
                    'cal_slope', 'cal_offset', 'cal_quad', 'two_theta'):
            if key in header:
                setattr(mcas[det], key, header[key][det])
        mcas[det].data = data[det]
        mcas[det].total_counts = data[det].sum()

#         try:
#             nrois = header['rois'][det]
#         except:
#             nrois = 0
#         for iroi in range(nrois):
#             print roisa
#
#
#             nrois = []
#             for d in range(n_detectors):
#                 rois.append([])
#                 nrois.append(int(values[d]))
#             max_rois = max(nrois)
#             if max_rois > 0:
#                 for d in range(n_detectors):
#                     for r in range(nrois[d]):
#                         rois[d].append(Roi())
#             #for d in range(n_detectors):
#         # Note 'ROIS' tag must come before the 'ROI_' tags!

    # Build dictionary to return
    r = {}
    r['n_detectors'] = header['elements']
    r['n_channels'] = header['channels']
    r['header'] = header
    r['mca'] = mcas
    r['max_rois'] = max(rois)
    r['rois'] = rois
    r['environment'] = environment
    return r

#########################################################################
def write_file(detector, file):
    """
    Writes Mca or Med objects to a disk file.

    Parameters:
    -----------
    * detector: An med or mca object
    * file: The name of the disk file to write.

    Example:
    --------
    >>write_file(mca,'mca.001')
    """
    # Make sure detector is type MED for simplicity...
    try:
        if detector.det_type != "MED":
            if has_attr(detector,'environment'):
                env = detector.environment
                del detector.environment
                #delattr(detector,'environment')
            else:
                env = None
            detector = Med(mca=[detector])
            if env: detector.environment = env
    except:
        return

    write_ascii_file(detector, file)

#######################################################################
def write_ascii_file(med, file):
    """
    Writes Med data to a disk file.

    The file format is a tagged ASCII format.  The file contains
    the information which it makes sense to store permanently, but
    does not contain all of the internal state information for the detector.
    Files written with this routine can be read with read_ascii_file().

    Parameters:
    -----------
    * med: Instance of Med object
    * file: The name of the disk file to write.
    """
    # Get raw (uncorrected) data as a list,
    data = []
    for m in med.mca:
        data.append(m.data)
        if hasattr(m,'rois'):
            rois.append(m.rois)

    # Note we assume all mca data are the same length!
    # Also assume that mca.channels = [0.....len(mca.data)]
    # ie we dont write channels to file
    nchans = len(data[0])

    # Write header stuff
    n_det      = med.n_detectors
    start_time = med.mca[0].start_time

    fformat = '%f ' * n_det
    eformat = '%e ' * n_det
    iformat = '%d ' * n_det
    sformat = '%s ' * n_det
    fp = open(file, 'w')
    fp.write('VERSION:    '+'3.1'+'\n')
    fp.write('ELEMENTS:   '+str(n_det)+'\n')
    fp.write('DATE:       '+str(start_time)+'\n')
    fp.write('CHANNELS:   '+str(nchans)+'\n')

    # count times and related
    real_time=[]; live_time=[] ; input_counts=[]; tau=[]
    for m in med.mca:
        real_time.append(m.real_time)
        live_time.append(m.live_time)
        input_counts.append(m.input_counts)
        tau.append(m.tau)
    fp.write('REAL_TIME:    '+(fformat % tuple(real_time))+'\n')
    fp.write('LIVE_TIME:    '+(fformat % tuple(live_time))+'\n')
    fp.write('INPUT_COUNTS: '+(fformat % tuple(input_counts))+'\n')
    fp.write('TAU:          '+(fformat % tuple(tau))+'\n')

    # calibration data
    offset=[]; slope=[]; quad=[]; two_theta=[]
    for m in med.mca:
        offset.append(m.offset)
        slope.append(m.slope)
        quad.append(m.quad)
        two_theta.append(m.two_theta)
    fp.write('CAL_OFFSET: '+(eformat % tuple(offset))+'\n')
    fp.write('CAL_SLOPE: '+(eformat % tuple(slope))+'\n')
    fp.write('CAL_QUAD: '+(eformat % tuple(quad))+'\n')
    fp.write('TWO_THETA: '+(fformat % tuple(two_theta))+'\n')

    # Write ROIS
    # note ROIS should always be in channel units!
    # Write number of rois for each mca
    nrois = []
    for d in range(n_det):
        if hasattr(med.mca[d],'rois'):
            nrois.append(len(med.mca[d].rois))
        else:
            nrois.append(0)
    fp.write('ROIS:       '+(iformat % tuple(nrois))+'\n')
    if max(nrois) > 0:
        for i in range(max(nrois)):
            num = str(i)
            left=[]; right=[]; label=[]
            for d in range(n_det):
                if (i < nrois[d]):
                    left.append(med.mca[d].rois[i].left)
                    right.append(med.mca[d].rois[i].right)
                    label.append(med.mca[d].rois[i].label + '&')
                else:
                    left.append(0)
                    right.append(0)
                    label.append(' &')
            fp.write('ROI_'+num+'_LEFT:   '+(iformat % tuple(left))+'\n')
            fp.write('ROI_'+num+'_RIGHT:  '+(iformat % tuple(right))+'\n')
            fp.write('ROI_'+num+'_LABEL:  '+(sformat % tuple(label))+'\n')
    # Write environment
    if has_attr(med,'environment'):
        for e in med.environment:
            fp.write('ENVIRONMENT: '       + str(e.name) +
                                            '="'  + str(e.value) +
                                            '" (' + str(e.description) + ')\n')

    # Write data
    fp.write('DATA: \n')
    counts = np.zeros(n_det)
    for i in range(nchans):
        for d in range(n_det):
            counts[d]=data[d][i]
        fp.write((iformat % tuple(counts))+'\n')

    # All done
    fp.close()

#########################################################################
def increment_filename(old_file):
    """
    Increments the file extension if it is numeric.  It preserves the number of
    characters in the extension.

    Examples:
    ---------
    >>print increment_filename('test.001')
      test.002
    >>print increment_filename('test')
      test
    >>print increment_filename('file.1')
      file.2
    """
    dot = old_file.rfind('.')
    if (dot == -1): return old_file
    if (dot+1 == len(old_file)): return old_file

    ext  = old_file[dot+1:]
    file = old_file[0:dot+1]
    nc   = str(len(ext))
    try:
        # Convert to number, add one, catch error
        ext = int(ext)+1
        format = '%' + nc + '.' + nc + 'd'
        ext = (format % ext)
        new_file = file + ext
        return new_file
    except:
        return old_file

#########################################################################
#########################################################################
def test():
    return read_med('test.xrf')

