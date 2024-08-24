#!/usr/bin/env python
"""
  Larch column file reader: read_ascii
"""
import os
import sys
import time
import string
from pathlib import Path
from collections import namedtuple
import numpy as np
from dateutil.parser import parse as dateparse
from math import log10
from larch import Group
from larch.symboltable import isgroup
from ..utils import read_textfile, format_exception, gformat, fix_varname
from .xafs_beamlines import guess_beamline

nanresult = namedtuple('NanResult', ('file_ok', 'message', 'nan_rows',
                                     'nan_cols', 'inf_rows', 'inf_cols'))

TINY = 1.e-7
MAX_FILESIZE = 100*1024*1024  # 100 Mb limit
COMMENTCHARS = '#;%*!$'

def look_for_nans(path):
    """
    look for Nans and Infs in an ASCII data file

    Arguments:
         path (string):  full path to ASCII column file

    Returns:
       NanResult, named tuple with elements

        'file_ok' : bool, whether data is read and contains no Nans or Infs
        'message' : exception message if file cannot be read at all or
                   'has nans', 'has infs' or 'has nans and infs'
        `nan_rows`: list of rows containing Nans
        `nan_cols`: list of columns containing Nans
        `inf_rows`: list of rows containing Infs
        `inf_cols`: list of columns containing Infs
    """

    nan_rows, nan_cols, inf_rows, inf_cols = [], [], [], []
    try:
        dat = read_ascii(path)
    except:
        print(''.join(format_exception()))
        return nanresult(False, f'could not read file {path}',
                             nan_rows, nan_cols, inf_rows, inf_cols)
    if len(dat.data) < 1:
        return nanresult(False, f'no data in file {path}',
                             nan_rows, nan_cols, inf_rows, inf_cols)
    if np.all(np.isfinite(dat.data)):
        return nanresult(True, 'file ok',
                             nan_rows, nan_cols, inf_rows, inf_cols)

    msg = 'unknown'
    nanvals = np.where(np.isnan(dat.data))
    if len(nanvals[0]) > 0:
        msg = 'has nans'
        for icol in nanvals[0]:
            if icol not in nan_cols:
                nan_cols.append(icol)
        for irow in nanvals[1]:
            if irow not in nan_rows:
                nan_rows.append(irow)

    infvals = np.where(np.isinf(dat.data))
    if len(infvals[0]) > 0:
        if len(msg) == 0:
            msg = 'has infs'
        else:
            msg = 'has nans and infs'
        for icol in infvals[0]:
            if icol not in inf_cols:
                inf_cols.append(icol)
        for irow in infvals[1]:
            if irow not in inf_rows:
                inf_rows.append(irow)

    return nanresult(False, msg, nan_rows, nan_cols, inf_rows, inf_cols)


def getfloats(txt, allow_times=True):
    """convert a line of numbers into a list of floats,
    as for reading a file with columnar numerical data.

    Arguments
    ---------
      txt   (str) : line of text to parse
      allow_times  (bool): whether to support time stamps [True]

    Returns
    -------
      list with each entry either a float or None

    Notes
    -----
      The `allow_times` will try to support common date-time strings
      using the dateutil module, returning a numerical value as the
      Unix timestamp, using
          time.mktime(dateutil.parser.parse(word).timetuple())
    """
    words = [w.strip() for w in txt.replace(',', ' ').split()]
    mktime = time.mktime
    for i, w in enumerate(words):
        val = None
        try:
            val = float(w)
        except ValueError:
            try:
                val = mktime(dateparse(w).timetuple())
            except ValueError:
                pass
        words[i] = val
    return words

def colname(txt):
    return fix_varname(txt.strip().lower()).replace('.', '_')


def parse_labelline(labelline, header):
    """
    parse the 'label line' for an ASCII file.


    This is meant to handle some special cases of XAFS data collected at a variety of sources
    """
    pass


def sum_fluor_channels(dgroup, roi, icr=None, ocr=None, ltime=None, label=None,
                       add_data=True, **kws):
    """build summed, deadtime-corrected fluorescence spectrum for a Group

    Arguments
    ---------
    dgroup    data group
    roi       list in array indices for ROI
    icr       None or list of array indices for ICR   [None]
    ocr       None or list of array indices for OCR   [None]
    ltime     None or list of array indices for LTIME [None]
    label     None or label for the summed, corrected array [None]
    add_data  bool, whether to add label and data to datgroup [False]

    Returns
    -------
    label, ndarray   with summed, deadtime-corrected data

    if add_data is True, the ndarray will also be appended to `dgroup.data,
    and the label will be appended to dgroup.array_labels


    Notes
    ------
    1.  The output array will be  Sum[ roi*icr/(ocr*ltime) ]
    2.  The default label will be like the array label for the 'dtcN' + first ROI
    3.  icr, ocr, or ltime can be `None`, '1.0', '-1', or '1' to mean '1.0' or
        arrays of indices for the respective components: must be the same lenght as roi

    4.  an array index of -1 will indicate 'bad channel' and be skipped for ROI
        or set to 1.0 for icr, ocr, or ltime

    5. if the list of arrays in roi, icr, ocr, or ltime are otherwise out-of-range,
       the returned (label, data) will be (None, None)

    """
    nchans = len(roi)
    if icr in ('1.0', -1, 1, None):
        icr = [-1]*nchans
    if ocr in ('1.0', -1, 1, None):
        ocr = [-1]*nchans
    if ltime in ('1.0', -1, 1, None):
        ltime = [-1]*nchans
    if len(ltime) != nchans or len(icr) != nchans or len(ocr) != nchans:
        raise Value("arrays of indices for for roi, icr, ocr, and ltime must be the same length")

    narr, npts = dgroup.data.shape
    nused = 0
    sum = 0.0
    olabel = None
    def get_data(arr, idx):
        iarr = arr[idx]
        if iarr < 0:
            return iarr, 1.0
        if iarr > narr-1:
            return None, None
        return iarr, dgroup.data[iarr, :]

    for pchan in range(nchans):
        droi = dicr = docr = dltime = 1.0
        iarr, droi = get_data(roi, pchan)
        if isinstance(droi, np.ndarray):
            if olabel is None:
                olabel = dgroup.array_labels[iarr]
        elif iarr is None:
            return (None, None)
        else:  # index of -1 here means "skip"
            continue

        iarr, dicr = get_data(icr, pchan)
        if iarr is None: return (None, None)

        iarr, docr = get_data(ocr, pchan)
        if iarr is None:  return (None, None)

        iarr, docr = get_data(ocr, pchan)
        if iarr is None:  return (None, None)

        iarr, dltime= get_data(ltime, pchan)
        if iarr is None:  return (None, None)

        sum += droi*dicr/(docr*dltime)
        nused += 1

    if label is None:
        if olabel is None: olabel = 'ROI'
        label = olabel = f'dtc{nused}_{olabel}'
        n  = 1
        while label in dgroup.array_labels:
            n += 1
            label = f'{olabel}_{n}'
    if add_data:
        dgroup.array_labels.append(label)
        dgroup.data = np.append(dgroup.data, sum.reshape(1, len(sum)), axis=0)
    return (label, sum)



def read_ascii(filename, labels=None, simple_labels=False,
               sort=False, sort_column=0):
    """read a column ascii column file, returning a group
    containing the data extracted from the file.

    Arguments:
      filename (str):        name of file to read
      labels (ist or None) : list of labels to use for array labels [None]
      simple_labels (bool) : whether to force simple column labels (note 1) [False]
      sort (bool) :          whether to sort row data (note 2) [False]
      sort_column (int) :    column to use for sorting (note 2) [0]

    Returns:
      Group

      A data group containing data read from file, with several attributes:

         | filename     : text name of the file.
         | array_labels : array labels, names of 1-D arrays.
         | data         : 2-dimensional data (ncolumns, nrows) with all data.
         | header       : array of text lines of the header.
         | footer       : array of text lines of the footer (text after the numerical data)
         | attrs        : group of attributes parsed from header lines.

    Notes:
      1. array labels.  If `labels` is `None` (the default), column labels
         and names of 1d arrays will be guessed from the file header.  This often
         means parsing the final header line, but tagged column files from several XAFS
         beamlines will be tried and used if matching.  Column labels may be like 'col1',
         'col2', etc if suitable column labels cannot be guessed.
         These labels will be used as names for the 1-d arrays from each column.
         If `simple_labels` is  `True`, the names 'col1', 'col2' etc will be used
         regardless of the column labels found in the file.

      2. sorting.  Data can be sorted to be in increasing order of any column,
         by giving the column index (starting from 0).

      3. header parsing. If header lines are of the forms of

           | KEY : VAL
           | KEY = VAL

         these will be parsed into a 'attrs' dictionary in the returned group.

    Examples:

        >>> feo_data = read_ascii('feo_rt1.dat')
        >>> show(g)a
        == Group ascii_file feo_rt1.dat: 0 methods, 8 attributes ==
        array_labels: ['energy', 'xmu', 'i0']
        attrs: <Group header attributes from feo_rt1.dat>
        data: array<shape=(3, 412), type=dtype('float64')>
        energy: array<shape=(412,), type=dtype('float64')>
        filename: 'feo_rt1.dat'
        header: ['# room temperature FeO', '# data from 20-BM, 2001, as part of NXS school', ... ]
        i0: array<shape=(412,), type=dtype('float64')>
        xmu: array<shape=(412,), type=dtype('float64')>

    See Also:
        read_xdi, write_ascii

    """
    if not Path(filename).is_file():
        raise OSError("File not found: '%s'" % filename)
    if os.stat(filename).st_size > MAX_FILESIZE:
        raise OSError("File '%s' too big for read_ascii()" % filename)

    text = read_textfile(filename)
    lines = text.split('\n')

    ncol = None
    data, footers, headers = [], [], []

    lines.reverse()
    section = 'FOOTER'

    for line in lines:
        line = line.strip()
        if len(line) < 1:
            continue
        # look for section transitions (going from bottom to top)
        if section == 'FOOTER' and not None in getfloats(line):
            section = 'DATA'
        elif section == 'DATA' and None in getfloats(line):
            section = 'HEADER'

        # act of current section:
        if section == 'FOOTER':
            footers.append(line)
        elif section == 'HEADER':
            headers.append(line)
        elif section == 'DATA':
            rowdat  = getfloats(line)
            if ncol is None:
                ncol = len(rowdat)
            elif ncol > len(rowdat):
                rowdat.extend([np.nan]*(ncol-len(rowdat)))
            elif ncol < len(rowdat):
                for i in data:
                    i.extend([np.nan]*(len(rowdat)-ncol))
                ncol = len(rowdat)
            data.append(rowdat)

    # reverse header, footer, data, convert to arrays
    footers.reverse()
    headers.reverse()
    data.reverse()
    data = np.array(data).transpose()

    # try to parse attributes from header text
    header_attrs = {}
    for hline in headers:
        hline = hline.strip().replace('\t', ' ')
        if len(hline) < 1: continue
        if hline[0] in COMMENTCHARS:
            hline = hline[1:].strip()
        keywds = []
        if ':' in hline: # keywords in  'x: 22'
            words = hline.split(':', 1)
            keywds = words[0].split()
        elif '=' in hline: # keywords in  'x = 22'
            words = hline.split('=', 1)
            keywds = words[0].split()
        if len(keywds) == 1:
            key = colname(keywds[0])
            if key.startswith('_'):
                key = key[1:]
            if len(words) > 1:
                header_attrs[key] = words[1].strip()


    fpath = Path(filename).absolute()
    filename = fpath.as_posix()
    attrs = {'filename': filename}
    group = Group(name='ascii_file %s' % filename,
                  path=filename, filename=fpath.name,
                  header=headers, data=[], array_labels=[])

    if len(data) == 0:
        return group

    if sort and sort_column >= 0 and sort_column < ncol:
         data = data[:, np.argsort(data[sort_column])]

    group.data = data

    if len(footers) > 0:
        group.footer = footers

    group.attrs = Group(name='header attributes from %s' % filename)
    for key, val in header_attrs.items():
        setattr(group.attrs, key, val)

    if isinstance(labels, str):
        for bchar in ',#@%|:*':
            labels = labels.replace(bchar, '')
        labels = labels.split()
    if labels is None and not simple_labels:
        bldat = guess_beamline(headers)(headers)
        labels = bldat.get_array_labels()

        if getattr(bldat, 'energy_units', 'eV') != 'eV':
            group.energy_units = bldat.energy_units
        if getattr(bldat, 'energy_column', 1) != 1:
            group.energy_column = bldat.energy_column
        if getattr(bldat, 'mono_dspace', -1) > 0:
            group.mono_dspace = bldat.mono_dspace

    set_array_labels(group, labels=labels, simple_labels=simple_labels)
    return group

def set_array_labels(group, labels=None, simple_labels=False,
                     save_oldarrays=False):

    """set array names for a group from its 2D `data` array.

    Arguments
    ----------
      labels (list of strings or None)  array of labels to use
      simple_labels (bool):   flag to use ('col1', 'col2', ...) [False]
      save_oldarrays (bool):  flag to save old array names [False]


    Returns
    -------
       group with newly named attributes of 1D array data, and
       an updated `array_labels` giving the mapping of `data`
       columns to attribute names.

    Notes
    ------
      1. if `simple_labels=True` it will overwrite any values in `labels`

      3. Array labels must be valid python names. If not enough labels
         are specified, or if name clashes arise, the array names may be
         modified, often by appending an underscore and letter or by using
         ('col1', 'col2', ...) etc.

      4. When `save_oldarrays` is `False` (the default), arrays named in the
         current `group.array_labels` will be erased.  Other arrays and
         attributes will not be changed.

    """
    write = sys.stdout.write
    if not hasattr(group, 'data'):
        write("cannot set array labels for group '%s': no `data`\n" % repr(group))
        return

    # clear old arrays, if desired
    oldlabels = getattr(group, 'array_labels', None)
    if oldlabels is not None and not save_oldarrays:
        for attr in oldlabels:
            if hasattr(group, attr):
                delattr(group, attr)

    ncols, nrow = group.data.shape

    ####
    # step 1: determine user-defined labels from input options
    # generating array `tlabels` for test labels
    #
    # generate simple column labels, used as backup
    clabels = ['col%d' % (i+1) for i in range(ncols)]

    if isinstance(labels, str):
        labels = labels.split()


    tlabels = labels
    # if simple column names requested or above failed, use simple column names
    if simple_labels or tlabels is None:
        tlabels = clabels

    ####
    # step 2: check input and correct problems
    # 2.a: check for not enough and too many labels
    if len(tlabels) < ncols:
        for i in range(len(tlabels), ncols):
            tlabels.append("col%i" % (i+1))
    elif len(tlabels) > ncols:
        tlabels = tlabels[:ncols]

    # 2.b: check for names that clash with group attributes
    # or that are repeated, append letter.
    reserved_names = ('data', 'array_labels', 'filename',
                      'attrs', 'header', 'footer')
    extras = string.ascii_lowercase
    labels = []
    for i in range(ncols):
        lname = tlabels[i]
        if lname in reserved_names or lname in labels:
            lname = lname + '_a'
            j = 0
            while lname in labels:
                j += 1
                if j == len(extras):
                    break
                lname = "%s_%s" % (tlabels[i], extras[j])
        if lname in labels:
            lname = clabels[i]
        labels.append(lname)

    ####
    # step 3: assign attribue names, set 'array_labels'
    for i, name in enumerate(labels):
        setattr(group, name, group.data[i])
    group.array_labels = labels
    return group


def write_ascii(filename, *args, commentchar='#', label=None, header=None):
    """
    write a list of items to an ASCII column file

    Arguments:
      args (list of groups):     list of groups to write.
      commentchar (str) :        character for comment ('#')
      label (str on None):       array label line (autogenerated)
      header (list of strings):  array of strings for header

    Returns:
      None

    Examples:
       >>> write_ascii('myfile',  group.energy, group.norm, header=['comment1', 'comment2']

    """
    ARRAY_MINLEN = 2
    write = sys.stdout.write
    com = commentchar
    label = label
    if header is None:
        header = []

    arrays = []
    arraylen = None

    for arg in args:
        if isinstance(arg, np.ndarray):
            if len(arg) > ARRAY_MINLEN:
                if arraylen is None:
                    arraylen = len(arg)
                else:
                    arraylen = min(arraylen, len(arg))
                arrays.append(arg)
            else:
                header.append(repr(arg))

        else:
            header.append(repr(arg))

    if arraylen is None:
        raise ValueError("write_ascii() need %i or more elements in arrays." % ARRAY_MINLEN)

    buff = []
    if header is None:
        buff = ['%s Output from Larch %s' % (com, time.ctime())]
    for s in header:
        buff.append('%s %s' % (com, s))
    buff.append('%s---------------------------------'% com)
    if label is None:
        label = (' '*13).join(['col%d' % (i+1) for i in range(len(arrays))])
    buff.append('#  %s' % label)

    arrays = np.array(arrays)
    for i in range(arraylen):
        w = [" %s" % gformat(val[i], length=14) for val in arrays]
        buff.append('  '.join(w))
    buff.append('')

    with open(filename, 'w', encoding=sys.getdefaultencoding()) as fout:
        fout.write('\n'.join(buff))
    sys.stdout.write("wrote to file '%s'\n" % filename)


def write_group(filename, group, scalars=None, arrays=None,
                arrays_like=None, commentchar='#'):
    """(deprecated) write components of a group to an ASCII column file


    Warning:
       This is pretty minimal and may work poorly for large groups of complex data.
       Use `save_session` instead.

    """

    items = dir(group)
    npts = 0
    if arrays is None:
        arrays = []
    if scalars is None:
        scalars = []

    if arrays_like is not None and arrays_like in items:
        array = getattr(group, arrays_like)
        if isinstance(array, np.ndarray):
            npts = len(array)

    for name in items:
        val = getattr(group, name)
        if isinstance(val, np.ndarray):
            if npts != 0 and npts == len(val) and name not in arrays:
                arrays.append(name)

    header =[]
    for s in scalars:
        if s in items:
            val = getattr(group, s)
            header.append("%s = %s" % (s, val))

    label = '  '.join(arrays)

    args = []
    for name in arrays:
        if name in items:
            args.append(getattr(group, name))

    write_ascii(filename, *args, commentchar=commentchar,
                label=label, header=header)


def read_fdmnes(filename, **kwargs):
    """read [FDMNES](http://fdmnes.neel.cnrs.fr/) ascii files"""
    group = read_ascii(filename, **kwargs)
    group.header_dict = dict(filetype='FDMNES', energy_units='eV')
    for headline in group.header:
        if ("E_edge" in headline):
            if headline.startswith("#"):
                headline = headline[1:]
            vals = [float(v) for v in headline.split(" = ")[0].split(" ") if v]
            vals_names = headline.split(" = ")[1].split(", ")
            group.header_dict.update(dict(zip(vals_names, vals)))
    group.name = f'FDMNES file {filename}'
    group.energy += group.header_dict["E_edge"]
    #fix _arrlabel -> arrlabel
    for ilab, lab in enumerate(group.array_labels):
        if lab.startswith("_"):
            fixlab = lab[1:]
            group.array_labels[ilab] = fixlab
            delattr(group, lab)
            setattr(group, fixlab, group.data[ilab])
    return group

def guess_filereader(path, return_text=False):
    """guess function name to use to read a data file based on the file header

    Arguments
    ---------
    path (str) : file path to be read

    Returns
    -------
    name of function (as a string) to use to read file
    if return_text: text of the read file
    """
    text = read_textfile(path)
    lines = text.split('\n')
    line1 = lines[0].lower()
    reader = 'read_ascii'
    if 'epics scan' in line1:
        reader = 'read_gsescan'
    if 'xdi' in line1:
        reader = 'read_xdi'
    if 'epics stepscan file' in line1 :
        reader = 'read_gsexdi'
    if ("#s" in line1) or ("#f" in line1):
        reader = 'read_specfile'
    if 'fdmnes' in line1:
        reader = 'read_fdmnes'
    if return_text:
        return reader, text
    else:
        return reader
