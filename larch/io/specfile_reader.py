#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Read data in SPEC_ format via `silx.io.open`
===================================================

.. _SPEC: http://www.certif.com/content/spec

Requirements
------------
- silx (http://www.silx.org/doc/silx/dev/modules/io/specfilewrapper.html)

"""

__author__ = ["Mauro Rovezzi", "Matt Newville"]
__version__ = "2020.12.1_larch"

import os, sys
import copy
import datetime
import numpy as np
import h5py
from silx.io.utils import open as silx_open
from silx.io.convert import write_to_h5, _is_commonh5_group
from scipy.interpolate import interp1d
from scipy.ndimage import map_coordinates

from larch.math.utils import savitzky_golay
from larch import Group

# to grid X,Y,Z columnar data
HAS_GRIDXYZ = False
try:
    from larch.math.gridxyz import gridxyz

    HAS_GRIDXYZ = True
except:
    pass

HAS_SPECFILE = False
try:
    from silx.io import specfilewrapper as specfile

    HAS_SPECFILE = True
except ImportError:
    pass

# SimpleMath from PyMca5
HAS_SIMPLEMATH = False
try:
    from PyMca5.PyMcaMath import SimpleMath

    HAS_SIMPLEMATH = True
except ImportError:
    pass

# SG module from PyMca5
HAS_SGMODULE = False
try:
    from PyMca5.PyMcaMath import SGModule

    HAS_SGMODULE = True
except ImportError:
    pass

# specfile_writer
HAS_SFDW = False
try:
    from .specfile_writer import SpecfileDataWriter

    HAS_SFDW = True
except (ValueError, ImportError):
    pass

### UTILITIES (the class is below!)
def _str2rng(rngstr, keeporder=True, rebin=None):
    """simple utility to convert a generic string representing a compact
    list of scans to a sorted list of integers

    Parameters
    ----------
    rngstr : string with given syntax (see Example below)
    keeporder : boolean [True], to keep the original order
                keeporder=False turn into a sorted list
    rebin : integer [None], force rebinning of the final range

    Example
    -------
    > _str2rng('100, 7:9, 130:140:5, 14, 16:18:1')
    > [7, 8, 9, 14, 16, 17, 18, 100, 130, 135, 140]

    """
    _rng = []
    for _r in rngstr.split(", "):  # the space is important!
        if len(_r.split(",")) > 1:
            raise NameError("Space after comma(s) is missing in '{0}'".format(_r))
        _rsplit2 = _r.split(":")
        if len(_rsplit2) == 1:
            _rng.append(_r)
        elif len(_rsplit2) == 2 or len(_rsplit2) == 3:
            if len(_rsplit2) == 2:
                _rsplit2.append("1")
            if _rsplit2[0] == _rsplit2[1]:
                raise NameError("Wrong range '{0}' in string '{1}'".format(_r, rngstr))
            if int(_rsplit2[0]) > int(_rsplit2[1]):
                raise NameError("Wrong range '{0}' in string '{1}'".format(_r, rngstr))
            _rng.extend(range(int(_rsplit2[0]), int(_rsplit2[1]) + 1, int(_rsplit2[2])))
        else:
            raise NameError("Too many colon in {0}".format(_r))

    # create the list and return it (removing the duplicates)
    _rngout = [int(x) for x in _rng]

    if rebin is not None:
        try:
            _rngout = _rngout[:: int(rebin)]
        except:
            raise NameError("Wrong rebin={0}".format(int(rebin)))

    def uniquify(seq):
        # Order preserving uniquifier by Dave Kirby
        seen = set()
        return [x for x in seq if x not in seen and not seen.add(x)]

    if keeporder:
        return uniquify(_rngout)
    else:
        return list(set(_rngout))


def _mot2array(motor, acopy):
    """simple utility to generate a copy of an array containing a
    constant value (e.g. motor position)

    """
    a = np.ones_like(acopy)
    return np.multiply(a, motor)


def _make_dlist(dall, rep=1):
    """make a list of strings representing the scans to average

    Parameters
    ----------
    dall : list of all good scans
    rep : int, repetition

    Returns
    -------
    dlist : list of lists of int

    """
    dlist = [[] for d in range(rep)]
    for idx in range(rep):
        dlist[idx] = dall[idx::rep]
    return dlist


def _checkZeroDiv(num, dnum):
    """compatibility layer"""
    print("DEPRECATED: use '_check_zero_div' instead")
    return _check_zero_div(num, dnum)


def _check_zero_div(num, dnum):
    """simple division check to avoid ZeroDivisionError"""
    try:
        return num / dnum
    except ZeroDivisionError:
        print("ERROR: found a division by zero")


def _checkScans(scans):
    """compatibility layer"""
    print("DEPRECATED: use '_check_scans' instead")
    return _check_scans(scans)


def _check_scans(scans):
    """simple checker for scans input"""
    if scans is None:
        raise NameError("Provide a string or list of scans to load")
    if type(scans) is str:
        try:
            nscans = _str2rng(scans)
        except:
            raise NameError(
                "scans string '{0}' not understood by str2rng".format(scans)
            )
    elif type(scans) is list:
        nscans = scans
    else:
        raise NameError("Provide a string or list of scans to load")
    return nscans


def _numpy_sum_list(xdats, zdats):
    """sum list of arrays

    Parameters
    ----------
    xdats, zdats : lists of arrays

    Returns
    -------
    xdats[0], sum(zdats)
    """
    try:
        # sum element-by-element
        arr_zdats = np.array(zdats)
        return xdats[0], np.sum(arr_zdats, 0)
    except:
        # sum by interpolation
        xref = xdats[0]
        zsum = np.zeros_like(xref)
        for xdat, zdat in zip(xdats, zdats):
            fdat = interp1d(xdat, zdat)
            zsum += fdat(xref)
        return xref, zsum


def _pymca_average(xdats, zdats):
    """call to SimpleMath.average() method from PyMca/SimpleMath.py

    Parameters
    ----------
    - xdats, ydats : lists of arrays contaning the data to merge

    Returns
    -------
    - xmrg, zmrg : 1D arrays containing the merged data

    """
    if HAS_SIMPLEMATH:
        sm = SimpleMath.SimpleMath()
        print("Merging data...")
        return sm.average(xdats, zdats)
    else:
        raise NameError(
            "SimpleMath is not available -- this operation cannot be performed!"
        )


def _pymca_SG(ydat, npoints=3, degree=1, order=0):
    """call to symmetric Savitzky-Golay filter in PyMca

    Parameters
    ----------
    ydat : 1D array contaning the data to smooth
    npoints : integer [3], means that 2*npoints+1 values contribute
              to the smoother.
    degree : degree of fitting polynomial
    order : is degree of implicit differentiation
            0 means that filter results in smoothing of function
            1 means that filter results in smoothing the first
              derivative of function.
            and so on ...

    Returns
    -------
    ys : smoothed array

    """
    if HAS_SGMODULE:
        return SGModule.getSavitzkyGolay(
            ydat, npoints=npoints, degree=degree, order=order
        )
    else:
        raise NameError(
            "SGModule is not available -- this operation cannot be performed!"
        )

def is_specfile(filename):
    """tests whether file may be a Specfile (text or HDF5)"""
    with open(filename, 'rb') as fh:
        topbytes = fh.read(10)
    scans = None
    if (topbytes.startswith(b'\x89HDF\r') or # HDF5
        topbytes.startswith(b'#F ')):        # full specscan
        try:
            scans = DataSourceSpecH5(filename).get_scans()
        except:
            pass
    return scans is not None


### ==================================================================
### CLASS BASED ON SPECH5 (CURRENT/RECOMMENDED)
### ==================================================================
class DataSourceSpecH5(object):
    """Data source utility wrapper for a Spec file read as HDF5 object
    via silx.io.open"""

    def __init__(self, fname=None, logger=None, urls_fmt="silx", verbose=False):
        """init with file name and default attributes

        Parameters
        ----------
        fname : str
            path string of a file that can be read by silx.io.open() [None]
        logger : logging.getLogger() instance
            [None -> sloth.utils.logging.getLogger()]
        urls_fmt : str
            how the data are organized in the HDF5 container
            'silx' : default
            'spec2nexus' : as converted by spec2nexus
        """
        if logger is None:
            from larch.utils.logging import getLogger

            _logger_name = "larch.io.specfile_reader.DataSourceSpecH5"
            self._logger = getLogger(_logger_name, level="WARNING")
        else:
            self._logger = logger

        if verbose:
            self._logger.set_level("INFO")

        self.fname = fname
        self._scanfile = None
        if self.fname is not None:
            self._init_source_file()
        self._scan_n = None
        self._scan_str = None

        self._scan_kws = {  # to get data from scan
            "ax_name": None,
            "to_energy": None,
            "sig_name": None,
            "mon": None,
            "deglitch": None,
            "norm": None}
        self._scangroup = None  # ScanGroup

        self._mots_url = "instrument/positioners"
        self._cnts_url = "measurement"
        self._title_url = "title"
        self._time_url = "start_time"
        self._urls_fmt = "silx"

        if urls_fmt == "spec2nexus":
            self._mots_url = "positioners"
            self._cnts_url = "data"
            self._title_url = "title"
            self._urls_fmt = "spec2nexus"
        elif urls_fmt != "silx":
            self._urls_fmt = None
            self._logger.error("'urls_fmt' not understood")
        self.set_group()

    def _init_source_file(self):
        """init source file object"""
        #: source file object (h5py-like)
        try:
            self._scanfile = silx_open(self.fname)
        except OSError:
            self._logger.error(f"cannot open {self.fname}")
            self._scanfile = None

    def open(self, mode="r"):
        """Open the source file object with h5py in given mode"""
        try:
            self._scanfile = h5py.File(self.fname, mode)
        except OSError:
            self._logger.error(f"cannot open {self.fname}")
            pass

    def close(self):
        """Close source file silx.io.spech5.SpecH5"""
        self._scanfile.close()
        self._scanfile = None


    def get_scangroup(self, scan=None):
        """get current scan group

        Parameters
        ----------
        scan  : str, int, or None
             scan address
        """
        if scan is not None:
            self.set_scan(scan)
        if self._scangroup is None:
            raise AttributeError("Group/Scan not selected -> use 'self.set_scan()' first")
        else:
            return self._scangroup

    def set_group(self, group_url=None):
        """Select group url

        Parameters
        ----------
        group_url : str (optional)
            hdf5 url with respect to / where scans are stored [None -> /scans]

        Returns
        -------
        none: sets attribute self._group_url
        """
        self._group_url = group_url
        if self._group_url is not None and self.verbose:
            self._logger.info(f"Selected group {self._group_url}")

    def set_scan(self, scan_n, scan_idx=1, group_url=None, scan_kws=None):
        """Select a given scan number

        Parameters
        ----------
        scan_n : int or str
            scan number or address
        scan_idx : int (optional)
            scan repetition index [1]
        group_url : str
            hdf5 url with respect to / where scans are stored [None -> /scans]
        scan_kws : None or dict
            additional keyword arguments used to get data from scan

        Returns
        -------
        none: set attributes
            self._scan_n, self._scan_str, self._scan_url, self._scangroup
        """
        # check if scan_n is given already as "scan_n.scan_idx"
        if isinstance(scan_n, str):
            scan_split = scan_n.split(".")
            scan_n = scan_split[0]
            try:
                scan_idx = scan_split[1]
            except IndexError:
                self._logger.warning("'scan_idx' kept at 1")
                pass
            try:
                scan_n = int(scan_n)
                scan_idx = int(scan_idx)
            except ValueError:
                self._logger.error("scan not selected, wrong 'scan_n'!")
                return
        assert isinstance(scan_n, int), "'scan_n' must be an integer"
        assert isinstance(scan_idx, int), "'scan_idx' must be an integer"
        self._scan_n = scan_n
        if scan_kws is not None:
            from sloth.utils.dicts import update_nested

            self._scan_kws = update_nested(self._scan_kws, scan_kws)
        if self._urls_fmt == "silx":
            self._scan_str = f"{scan_n}.{scan_idx}"
        elif self._urls_fmt == "spec2nexus":
            self._scan_str = f"S{scan_n}"
        else:
            self._logger.error("wrong 'urls_fmt'")
            return
        if group_url is not None:
            self.set_group(group_url)
        if self._group_url is not None:
            self._scan_url = f"{self._group_url}/{self._scan_str}"
        else:
            self._scan_url = f"{self._scan_str}"
        try:
            self._scangroup = self._scanfile[self._scan_url]
            self._scan_title = self.get_title()
            self._scan_start = self.get_time()
            self._logger.info(
                f"selected scan {self._scan_url}: '{self._scan_title}' ({self._scan_start})"
            )
        except KeyError:
            self._scangroup = None
            self._scan_title = None
            self._logger.error(f"'{self._scan_url}' is not valid")

    def _list_from_url(self, url_str):
        """Utility method to get a list from a scan url

        .. warning:: the list is **not ordered**

        """
        try:
            return [i for i in self.get_scangroup()[url_str].keys()]
        except Exception:
            self._logger.error(f"'{url_str}' not found -> use 'set_scan' method first")

    # ================== #
    #: READ DATA METHODS
    # ================== #

    def _repr_html_(self):
        """HTML representation for Jupyter notebook"""

        scns = self.get_scans()
        html = ["<table>"]
        html.append("<tr>")
        html.append("<td><b>Scan</b></td>")
        html.append("<td><b>Title</b></td>")
        html.append("<td><b>Start_time</b></td>")
        html.append("</tr>")
        for scn, tlt, sct in scns:
            html.append("<tr>")
            html.append(f"<td>{scn}</td>")
            html.append(f"<td>{tlt}</td>")
            html.append(f"<td>{sct}</td>")
            html.append("</tr>")
        html.append("</table>")
        return "".join(html)

    def get_scans(self):
        """Get list of scans

        Returns
        -------
        list of strings: [['scan.n', 'title', 'start_time'], ... ]
        """
        allscans = []
        for sn, sg in self._scanfile.items():
            allscans.append([sn, sg[self._title_url][()], sg[self._time_url][()]])
        return allscans

    def get_motors(self, scan=None):
        """Get list of motors names

        Parameters
        ----------
        scan  : str, int, or None
             scan address
        """
        if scan is not None:
            self.set_scan(scan)
        return self._list_from_url(self._mots_url)

    def get_counters(self, scan=None):
        """Get list of motors names

        Parameters
        ----------
        scan  : str, int, or None
             scan address
        """
        if scan is not None:
            self.set_scan(scan)
        return self._list_from_url(self._cnts_url)

    def get_title(self, scan=None):
        """Get title str for the current scan

        Parameters
        ----------
        scan  : str, int, or None
             scan address

        Returns
        -------
        title (str): scan title self._scangroup[self._title_url][()]

        """
        sg = self.get_scangroup(scan)
        return sg[self._title_url][()]

    def get_time(self, scan=None):
        """Get start time str for the current scan

        Parameters
        ----------
        scan  : str, int, or None
             scan address

        Returns
        -------
        start_time (str): scan start time self._scangroup[self._time_url][()]
        """
        sg = self.get_scangroup(scan)
        return sg[self._time_url][()]

    def get_timestamp(self, scan=None):
        """ Get integer timestamp from the start time str

        Parameters
        ----------
        scan  : str, int, or None
             scan address
        """
        if scan is not None:
            self.set_scan(scan)
        d, t = self.get_time().split("T")
        dd = d.split("-")
        tt = t.split(":")
        ddd = [int(_dd) for _dd in dd]
        ttt = [int(_tt) for _tt in tt]
        dt = ddd + ttt
        return int(datetime.datetime(*dt).timestamp())

    def get_scan_info_from_title(self, scan=None):
        """Parser to get scan information from title

        Known types of scans
        --------------------
        'ascan'
        'Escan'
        'Emiscan'

        Returns
        -------
        iscn : dict of str
            {
             scan_type : "type of scan",
             scan_axis : "scanned axis",
             scan_start : "",
             scan_end : "",
             scan_pts : "",
             scan_ct : "",
            }
        """
        if scan is not None:
            self.set_scan(scan)

        iscn = dict(scan_type=None, scan_axis=None, scan_start=None,
                    scan_end=None, scan_pts=None, scan_ct=None)

        _title = self.get_title()
        if isinstance(_title, np.ndarray):
            _title = np.char.decode(_title)[0]
        _title_splitted = _title.split(" ")
        _iax = 0
        _scntype = _title_splitted[_iax]
        if _scntype == "ascan":
            iscn.update(
                dict(
                    scan_type=_scntype,
                    scan_axis=_title_splitted[2],
                    scan_start=_title_splitted[3],
                    scan_end=_title_splitted[4],
                    scan_pts=_title_splitted[6],
                    scan_ct=_title_splitted[7],
                )
            )
        if _scntype == "Escan":
            iscn.update(
                dict(
                    scan_type=_scntype,
                    scan_axis="Energy",
                    scan_start=_title_splitted[1],
                    scan_end=_title_splitted[2],
                    scan_pts=_title_splitted[3],
                    scan_ct=_title_splitted[4],
                )
            )
        if _scntype == "Emiscan":
            iscn.update(
                dict(
                    scan_type=_scntype,
                    scan_axis="Emi_Energy",
                    scan_start=_title_splitted[1],
                    scan_end=_title_splitted[2],
                    scan_pts=_title_splitted[3],
                    scan_ct=_title_splitted[4],
                )
            )
        return iscn

    def get_scan_axis(self, scan=None):
        """Get the name of the scanned axis from scan title"""
        if scan is not None:
            self.set_scan(scan)

        iscn = self.get_scan_info_from_title()
        _axisout = iscn["scan_axis"]
        _mots, _cnts = self.get_motors(), self.get_counters()
        if not (_axisout in _mots):
            self._logger.info(f"'{_axisout}' not in (real) motors")
        if not (_axisout in _cnts):
            self._logger.info(f"'{_axisout}' not in counters")
            _axisout = _cnts[0]
            self._logger.info(f"using the first counter: '{_axisout}'")
        return _axisout

    def get_array(self, cnt, scan=None):
        """Get array of a given counter

        Parameters
        ----------
        cnt : str or int
            counter name or index in the list of counters

        Returns
        -------
        array
        """
        sg = self.get_scangroup(scan)
        cnts = self.get_counters()
        if type(cnt) is int:
            cnt = cnts[cnt]
            self._logger.info("Selected counter %s", cnt)
        if cnt in cnts:
            sel_cnt = f"{self._cnts_url}/{cnt}"
            return copy.deepcopy(sg[sel_cnt][()])
        else:
            self._logger.error(f"'{cnt}' not found in available counters: {cnts}")
            sel_cnt = f"{self._cnts_url}/{cnts[0]}"
            return np.zeros_like(sg[sel_cnt][()])

    def get_motor_position(self, mot, scan=None):
        """Get motor position

        Parameters
        ----------
        mot : str or int
            motor name or index in the list of motors

        Returns
        -------
        value
        """
        sg = self.get_scangroup(scan)
        mots = self.get_motors()
        if type(mot) is int:
            mot = mots[mot]
            self._logger.info(f"Selected motor '{mot}'")
        if mot in mots:
            sel_mot = f"{self._mots_url}/{mot}"
            return copy.deepcopy(sg[sel_mot][()])
        else:
            self._logger.error(f"'{mot}' not found in available motors: {mots}")
            return None

    def get_scan(self, scan=None):
        """Get arrays for scan

        Parameters
        ----------
        scan  : str, int, or None
             scan address

        Returns
        -------
        larch Group with scan data
        """
        self.get_scangroup(scan)
        scan_index  = self._scan_n
        scan_name = self._scan_str
        scan_group = self._scangroup
        labels = self.get_counters()
        title = self.get_title()
        timestring = self.get_time()
        timestamp = self.get_timestamp()
        path, filename = os.path.split(self.fname)
        axis = self.get_scan_axis()
        out = Group(__name__=f"Spec file: {filename}, scan: {scan_name}",
                    path=path, filename=filename, datatype=None,
                    array_labels=labels, axis=axis,
                    scan_index=scan_index,
                    scan_name=scan_name,
                    title=title,
                    timestring=timestring,
                    timestamp=timestamp)

        data = []
        for label in labels:
            arr = self.get_array(label)
            setattr(out, label, arr)
            data.append(arr)
        out.data = np.array(data)
        return out


    # =================== #
    #: WRITE DATA METHODS
    # =================== #

    def write_scans_to_h5(self, scans, fname_out, scans_groups=None,
                           h5path=None, overwrite=False, conf_dict=None):
        """Export a selected list of scans to HDF5 file

        .. note:: This is a simple wrapper to
            :func:`silx.io.convert.write_to_h5`

        Parameters
        ----------
        scans : str, list of ints or list of lists (str/ints)
            scan numbers to export (parsed by _str2rng)
            if a list of lists, scans_groups is required
        fname_out : str
            output file name
        scans_groups : list of strings
            groups of scans
        h5path : str (optional)
            path inside HDF5 [None -> '/']
        overwrite : boolean (optional)
            force overwrite if the file exists [False]
        conf_dict : None or dict (optional)
            configuration dictionary saved as '{hdfpath}/.config'
        """
        self._fname_out = fname_out
        self._logger.info(f"output file: {self._fname_out}")
        if os.path.isfile(self._fname_out) and os.access(self._fname_out, os.R_OK):
            self._logger.info(f"output file exists (overwrite is {overwrite})")
            _fileExists = True
        else:
            _fileExists = False

        #: out hdf5 file
        if overwrite and _fileExists:
            os.remove(self._fname_out)
        h5out = h5py.File(self._fname_out, mode="a", track_order=True)

        #: h5path
        if h5path is None:
            h5path = "/"
        else:
            h5path += "/"

        #: write group configuration dictionary, if given
        if conf_dict is not None:
            from silx.io.dictdump import dicttoh5

            _h5path = f"{h5path}.config/"
            dicttoh5(
                conf_dict,
                h5out,
                h5path=_h5path,
                create_dataset_args=dict(track_order=True),
            )
            self._logger.info(f"written dictionary: {_h5path}")

        #: write scans
        def _loop_scans(scns, group=None):
            for scn in scns:
                self.set_scan(scn)
                _scangroup = self._scangroup
                if _scangroup is None:
                    continue
                if not _is_commonh5_group(_scangroup):
                    self._logger.error("scan '%s' is not commonh5 group", scn)
                if group is not None:
                    _h5path = f"{h5path}{group}/{self._scan_str}/"
                else:
                    _h5path = f"{h5path}{self._scan_str}/"
                write_to_h5(
                    _scangroup,
                    h5out,
                    h5path=_h5path,
                    create_dataset_args=dict(track_order=True),
                )
                self._logger.info(f"written scan: {_h5path}")

        if type(scans) is list:
            assert type(scans_groups) is list, "'scans_groups' should be a list"
            assert len(scans) == len(
                scans_groups
            ), "'scans_groups' not matching 'scans'"
            for scns, group in zip(scans, scans_groups):
                _loop_scans(_str2rng(scns), group=group)
        else:
            _loop_scans(_str2rng(scans))

        #: close output file
        h5out.close()


### ==================================================================
### CLASS BASED ON SPECILE (OLD/DEPRECATED)
### ==================================================================
class SpecfileData(object):
    """SpecfileData object"""
    def __init__(self, fname=None, cntx=1, cnty=None, csig=None, cmon=None,
                 csec=None, norm=None, verbosity=0):
        """reads the given specfile

        Parameters
        ----------
        fname : SPEC file name [string, None]
                if 'DUMMY!': return (used to get docstrings)
        cntx : counter for x axis, motor 1 scanned [string, 1]
        cnty : counter for y axis, motor 2 steps [string, None]
               used by get_map()
        csig : counter for signal [string, None]
        cmon : counter for monitor/normalization [string, None]
        csec : counter for time in seconds [string, None]
        scnt : scan type [string, None]
        norm : normalization [string, None]
               'max' -> z/max(z)
               'max-min' -> (z-min(z))/(max(z)-min(z))
               'area' -> (z-min(z))/trapz(z, x)
               'sum' -> (z-min(z)/sum(z)

        verbosity : level of verbosity [int, 0]

        Returns
        -------
        None, sets attributes.
        self.fname -> spec file name
        self.sf -> spec file object
        self.cntx/cnty/csig/cmon/csec/norm

        """
        self.verbosity = verbosity
        if fname == "DUMMY!":
            return
        if HAS_SPECFILE is False:
            if self.verbosity > 1:
                print("WARNING 'specfile' is missing -> check requirements!")
            return
        if fname is None:
            raise NameError("Provide a SPEC data file to load with full path")
        elif not os.path.isfile(fname):
            raise OSError("File not found: '%s'" % fname)
        else:
            if hasattr(self, "sf") and hasattr(self, "fname"):
                if self.fname == fname:
                    pass
            else:
                self.sf = specfile.Specfile(fname)  # sf = specfile file
                self.fname = fname
                if self.verbosity > 0:
                    print("Loaded: {0} ({1} scans)".format(fname, self.sf.scanno()))
        # if HAS_SIMPLEMATH: self.sm = SimpleMath.SimpleMath()
        # set common attributes
        self.cntx = cntx
        self.cnty = cnty
        self.csig = csig
        self.cmon = cmon
        self.csec = csec
        self.norm = norm

    def get_scan(self, scan=None, scnt=None, **kws):
        """get a single scan from a SPEC file

        Parameters
        ----------
        scan : scan number to get [integer]
        cntx : counter for x axis, motor 1 scanned [string]
        cnty : counter for y axis, motor 2 steps [string] - used by get_map()
        csig : counter for signal [string]
        cmon : counter for monitor/normalization [string]
        csec : counter for time in seconds [string]
        scnt : scan type [string]
        norm : normalization [string]
               'max' -> z/max(z)
               'max-min' -> (z-min(z))/(max(z)-min(z))
               'area' -> (z-min(z))/trapz(z, x)
               'sum' -> (z-min(z)/sum(z)

        Returns
        -------
        scan_datx : 1D array with x data (scanned axis)
        scan_datz : 1D array with z data (intensity axis)
        scan_mots : dictionary with all motors positions for the given scan
                    NOTE: if cnty is given, it will return only scan_mots[cnty]
        scan_info : dictionary with information on the scan

        """
        if HAS_SPECFILE is False:
            raise NameError("Specfile not available!")

        # get keywords arguments
        cntx = kws.get("cntx", self.cntx)
        cnty = kws.get("cnty", self.cnty)
        csig = kws.get("csig", self.csig)
        cmon = kws.get("cmon", self.cmon)
        csec = kws.get("csec", self.csec)
        norm = kws.get("norm", self.norm)
        # input checks
        if scan is None:
            raise NameError(
                "Give a scan number [integer]: between 1 and {0}".format(
                    self.sf.scanno()
                )
            )
        if cntx is None:
            raise NameError("Give the counter for x, the abscissa [string]")
        if cnty is not None and not (cnty in self.sf.allmotors()):
            raise NameError("'{0}' is not in the list of motors".format(cnty))
        if csig is None:
            raise NameError("Give the counter for signal [string]")

        # select the given scan number
        # NOTE: here impossible to catch an exception, if the next
        # fails, specfile will directly call sys.exit! the try: except
        # did not work!
        _scanstr = str(scan)
        if "." in _scanstr:
            _scansel = _scanstr
        else:
            _scansel = "{0}.1".format(_scanstr)
        self.sd = self.sf.select(_scansel)  # sd = specfile data

        # the case cntx is not given, the first counter is taken by default
        if cntx == 1:
            _cntx = self.sd.alllabels()[0]
        else:
            _cntx = cntx

        ## x-axis
        scan_datx = self.sd.data_column_by_name(_cntx)
        _xlabel = "x"
        _xscale = 1.0
        if scnt is None:
            # try to guess the scan type if it is not given
            # this condition should work in case of an energy scan
            if "ene" in _cntx.lower():
                # this condition should detect if the energy scale is keV
                if (scan_datx.max() - scan_datx.min()) < 3.0:
                    scan_datx = scan_datx * 1000
                    _xscale = 1000.0
                    _xlabel = "energy, eV"
                else:
                    scan_datx = self.sd.data_column_by_name(cntx)
                    _xscale = 1.0
                    _xlabel = "energy, keV"
        else:
            raise NameError("Wrong scan type string")

        ## z-axis (start with the signal)
        # data signal
        datasig = self.sd.data_column_by_name(csig)
        # data monitor
        if cmon is None:
            datamon = np.ones_like(datasig)
            labmon = "1"
        elif ("int" in str(type(cmon))) or ("float" in str(type(cmon))):
            # the case we want to divide by a constant value
            datamon = _mot2array(cmon, datasig)
            labmon = str(cmon)
        else:
            datamon = self.sd.data_column_by_name(cmon)
            labmon = str(cmon)
        # data cps
        if csec is not None:
            scan_datz = (
                (datasig / datamon) * np.mean(datamon)
            ) / self.sd.data_column_by_name(csec)
            _zlabel = "((signal/{0})*mean({0}))/seconds".format(labmon)
        else:
            scan_datz = datasig / datamon
            _zlabel = "signal/{0}".format(labmon)

        ### z-axis normalization, if required
        if norm is not None:
            _zlabel = "{0} norm by {1}".format(_zlabel, norm)
            if norm == "max":
                scan_datz = _check_zero_div(scan_datz, np.max(scan_datz))
            elif norm == "max-min":
                scan_datz = _check_zero_div(
                    scan_datz - np.min(scan_datz), np.max(scan_datz) - np.min(scan_datz)
                )
            elif norm == "area":
                scan_datz = _check_zero_div(
                    scan_datz - np.min(scan_datz), np.trapz(scan_datz, x=scan_datx)
                )
            elif norm == "sum":
                scan_datz = _check_zero_div(
                    scan_datz - np.min(scan_datz), np.sum(scan_datz)
                )
            else:
                raise NameError("Provide a correct normalization type string")

        ### z-axis replace nan and inf, in case
        scan_datz = np.nan_to_num(scan_datz)

        ## the motors dictionary
        try:
            scan_mots = dict(zip(self.sf.allmotors(), self.sd.allmotorpos()))
        except:
            if self.verbosity > 0:
                print("INFO: NO MOTORS IN {0}".format(self.fname))
            scan_mots = {}

        ## y-axis
        if cnty is not None:
            _ylabel = "motor {0} at {1}".format(cnty, scan_mots[cnty])
        else:
            _ylabel = _zlabel

        ## collect information on the scan
        scan_info = {
            "xlabel": _xlabel,
            "xscale": _xscale,
            "ylabel": _ylabel,
            "zlabel": _zlabel,
        }

        if cnty is not None:
            return scan_datx, scan_datz, scan_mots[cnty] * _xscale
        else:
            return scan_datx, scan_datz, scan_mots, scan_info

    def get_map(self, scans=None, **kws):
        """get a map composed of many scans repeated at different position of
        a given motor

        Parameters
        ----------
        scans : scans to load in the map [string]; the format of the
                string is intended to be parsed by '_str2rng()'
        **kws : see get_scan() method

        Returns
        -------
        xcol, ycol, zcol : 1D arrays representing the map

        """
        # get keywords arguments
        cntx = kws.get("cntx", self.cntx)
        cnty = kws.get("cnty", self.cnty)
        csig = kws.get("csig", self.csig)
        cmon = kws.get("cmon", self.cmon)
        csec = kws.get("csec", self.csec)
        norm = kws.get("norm", self.norm)
        # check inputs - some already checked in get_scan()
        nscans = _check_scans(scans)
        if cnty is None:
            raise NameError("Provide the name of an existing motor")
        #
        _counter = 0
        for scan in nscans:
            x, z, moty = self.get_scan(
                scan=scan,
                cntx=cntx,
                cnty=cnty,
                csig=csig,
                cmon=cmon,
                csec=csec,
                scnt=None,
                norm=norm,
            )
            y = _mot2array(moty, x)
            if self.verbosity > 0:
                print("INFO loading scan {0} into the map...".format(scan))
            if _counter == 0:
                xcol = x
                ycol = y
                zcol = z
            else:
                xcol = np.append(xcol, x)
                ycol = np.append(ycol, y)
                zcol = np.append(zcol, z)
            _counter += 1

        return xcol, ycol, zcol

    def grid_map(self, xcol, ycol, zcol, xystep=None, lib="scipy", method="cubic"):
        if HAS_GRIDXYZ is True:
            return gridxyz(xcol, ycol, zcol, xystep=xystep, lib=lib, method=method)
        else:
            return

    def get_scans(self, scans=None, motinfo=True, **kws):
        """get a list of scans

        Parameters
        ----------
        scans : string or list of scans to load [None]; the format of the
                string is intended to be parsed by '_str2rng()'

        motinfo : boolean [True] returns also motors and scaninfo
                  dictionaries (see self.get_scan())

        Returns
        -------
        xdats, zdats : list of arrays
        if motinfo: return also mdats, idats dictionaries

        """
        # get keywords arguments
        cntx = kws.get("cntx", self.cntx)
        csig = kws.get("csig", self.csig)
        cmon = kws.get("cmon", self.cmon)
        csec = kws.get("csec", self.csec)
        norm = kws.get("norm", self.norm)
        #
        nscans = _check_scans(scans)
        #
        _ct = 0
        xdats = []
        zdats = []
        mdats = []
        idats = []
        if self.verbosity > 0:
            print("INFO loading {0} scans from SPEC ...".format(len(nscans)))
        for scan in nscans:
            _x, _z, _m, _i = self.get_scan(
                scan=scan,
                cntx=cntx,
                cnty=None,
                csig=csig,
                cmon=cmon,
                csec=csec,
                scnt=None,
                norm=norm,
            )
            xdats.append(_x)
            zdats.append(_z)
            if motinfo:
                mdats.append(_m)
                idats.append(_i)
            print("Loading scan {0}...".format(scan))
            _ct += 1
        if motinfo:
            return xdats, zdats, mdats, idats
        else:
            return xdats, zdats

    def get_mrg(self, scans=None, action="average", **kws):
        """get a merged scan from a list of scans

        Parameters
        ----------
        scans : scans to load in the merge [string]
                the format of the string is intended to be parsed by '_str2rng()'
        action : action to perform on the loaded list of scans
                 'average' -> average the scans ( see _pymca_average() )
                 'sum' -> sum all zscans ( see _numpy_sum_list() )
                 'join' -> concatenate the scans
                 'single' -> scans_list[0] : equivalent to get_scan()
        **kws : see get_scan() method

        Returns
        -------
        xmrg, zmrg : 1D arrays

        """
        # check inputs - some already checked in get_scan()/get_scans()
        nscans = _check_scans(scans)

        actions = ["single", "average", "sum", "join"]
        if not action in actions:
            raise NameError("'action={0}' not in known actions {1}".format(actions))

        # moved to get_scans
        xdats, zdats = self.get_scans(scans=nscans, motinfo=False, **kws)

        # override 'action' keyword if it is only one scan
        if len(nscans) == 1:
            action = "single"
            if self.verbosity > 1:
                print("WARNING(get_mrg): len(scans)==1 -> 'action=single'")
        if action == "average":
            if self.verbosity > 0:
                print("INFO: merging data...")
            return _pymca_average(xdats, zdats)
        elif action == "sum":
            return _numpy_sum_list(xdats, zdats)
        elif action == "join":
            return np.concatenate(xdats, axis=0), np.concatenate(zdats, axis=0)
        elif action == "single":
            return xdats[0], zdats[0]

    def get_mrgs_by(self, scans="all", nbin=1, **kws):
        """get merge by groups of scans

        Parameters
        ----------
        scans : string ['all'] to pass to _str2rng, if 'all',
                sf.scanno() is taken
        nbin : int [1], number of scans to merge together

        Returns
        -------
        xmrgs, zmrgs : lists of merged arrays

        """
        # get keywords arguments
        cntx = kws.get("cntx", self.cntx)
        csig = kws.get("csig", self.csig)
        cmon = kws.get("cmon", self.cmon)
        csec = kws.get("csec", self.csec)
        norm = kws.get("norm", self.norm)
        action = kws.get("action", "average")
        #
        xmrgs = []
        zmrgs = []
        if scans == "all":
            scans = "{0}:{1}".format(1, self.sf.scanno())
        try:
            nScans = _str2rng(scans)
            nAvg = nScans[::nbin]
        except:
            raise NameError("wrong 'scans'/'nbin' parameters!")
        nScansLast = len(nScans) % nbin
        for iAvg, Avg in enumerate(nAvg):
            iStart = iAvg * nbin
            if Avg == nAvg[-1] and not nScansLast == 0:
                if self.verbosity > 1:
                    print(
                        "WARNING avg {0} is of {1} scans only".format(iAvg, nScansLast)
                    )
                nAdd = nScansLast
            else:
                nAdd = nbin
            mscans = nScans[iStart : iStart + nAdd]
            if self.verbosity > 0:
                print("INFO avg {0}: scans='{1}'".format(iAvg, str(mscans)))
            _xmrg, _zmrg = self.get_mrg(
                scans=mscans,
                action=action,
                cntx=cntx,
                cnty=None,
                csig=csig,
                cmon=cmon,
                csec=csec,
                scnt=None,
                norm=norm,
            )
            xmrgs.append(_xmrg)
            zmrgs.append(_zmrg)
        return xmrgs, zmrgs

    def get_mrgs_rep(self, scns, nrep=3, **kws):
        """get merge by groups of repetitions

        Parameters
        ----------

        scns : string
               string representing ALL the good scans (parsed by str2rng)

        """
        print("Not implemented yet!")

    def get_det_dt(self, zcts, tau, secs=None):
        """get detector signal corrected by dead time

        Parameters
        ----------
        zcts : array of floats
               detector [counts], if ysecs=None [counts/s]

        tau : float
              tau [s]

        secs : array of floats, None
               normalization time [s]

        Returns
        -------
        zcts_corr : array of floats
                    zcps = zcts/secs
                    zcps_corr = zcps / (1 - zcps * tau)
                    zcts_corr = zcps_corr * secs

        """
        if secs is not None:
            try:
                zcts = zcts / secs
            except:
                print("det_dtc ERROR")
                return zcts
        try:
            # import pdb
            # pdb.set_trace()
            # print(zcps)
            zcts_corr = zcts / (1 - zcts * tau)
        except:
            print("det_dtc ERROR step 2")
            return zcts
        if secs is not None:
            return zcts_corr * secs
        else:
            return zcts_corr

    def get_filter(self, ydats, method="scipySG", **kws):
        """get filtered data using a list of ydats and given method

        Parameters
        ----------
        ydats : list of 1D arrays

        method : 'scipySG' -> Savitsky Golay filter from Scipy
                              (see savitzky_golay())
                 'pymcaSG' -> Savitsky Golay filter from PyMca
                              (see _pymca_SG())

        Returns
        -------
        ysdats : list of 1D smoothed arrays

        """
        if method == "pymcaSG":
            npoints = kws.get("npoints", 9)
            degree = kws.get("degree", 4)
            order = kws.get("order", 0)
            ysdats = []
            if self.verbosity > 0:
                print("INFO smoothing data with Savitzky-Golay filter (pymca)...")
            for y in ydats:
                ysdats.append(_pymca_SG(y, npoints=npoints, degree=degree, order=order))
            return ysdats
        elif method == "scipySG":
            window_size = kws.get("window_size", 9)
            order = kws.get("order", 4)
            deriv = kws.get("deriv", 0)
            ysdats = []
            if self.verbosity > 0:
                print("INFO smoothing data with Savitzky-Golay filter (scipy)...")
            for y in ydats:
                ysdats.append(
                    savitzky_golay(y, window_size=window_size, order=order, deriv=deriv)
                )
            return ysdats
        else:
            raise NameError("method not known!")

    def write_ascii(self, scans, **kws):
        """export single scans to separate ascii files"""
        if not HAS_SFDW:
            raise ImportError("specfiledatawriter required for this method!!!")
        # get keywords arguments
        cntx = kws.get("cntx", self.cntx)
        csig = kws.get("csig", self.csig)
        cmon = kws.get("cmon", self.cmon)
        csec = kws.get("csec", self.csec)
        norm = kws.get("norm", self.norm)

        nscans = _check_scans(scans)
        for scn in nscans:
            x, y, m, i = self.get_scan(
                scan=scn,
                scnt=None,
                cntx=cntx,
                cnty=None,
                csig=csig,
                cmon=cmon,
                csec=csec,
                norm=norm,
            )
            fout = SpecfileDataWriter(
                "{0}_S{1}".format(self.fname, str(scn).rjust(3, "0"))
            )
            fout.wHeader(
                epoch=self.sf.epoch(),
                date=self.sf.date(),
                title="spec2spec",
                motnames=self.sf.allmotors(),
            )
            fout.wScan(
                ["Energy", "{0}".format(i["zlabel"])],
                [x, y],
                title="{0}".format(self.sd.command()),
                motpos=self.sd.allmotorpos(),
            )


### LARCH ###
def _specfiledata_getdoc(method):
    """to get the docstring of method inside a class"""
    s = SpecfileData("DUMMY!")
    head = "\n Docstring from {0}:\n -------------------\n".format(method)
    return head + getattr(getattr(s, method), "__doc__")


def spec_getscan2group(fname, scan=None, cntx=None, csig=None, cmon=None,
                       csec=None, scnt=None, norm=None):

    """*** simple mapping of SpecfileData.get_scan() to Larch group ***"""
    s = SpecfileData(fname)
    x, y, motors, infos = s.get_scan(scan=scan, cntx=cntx, csig=csig,
                                     cmon=cmon, csec=csec, scnt=scnt, norm=norm)
    return Group(__name__ = "SPEC data file %s" % fname,
                  x=x, y=y, motors=motors, infos=infos)

spec_getscan2group.__doc__ += _specfiledata_getdoc("get_scan")


def spec_getmap2group(fname, scans=None, cntx=None, cnty=None, csig=None,
                      cmon=None, csec=None, xystep=None, norm=None):

    """ *** simple mapping of SpecfileData.get_map() + grid_map () to Larch group *** """
    if _larch is None:
        raise Warning("larch broken?")

    s = SpecfileData(fname)
    xcol, ycol, zcol = s.get_map(scans=scans, cntx=cntx, cnty=cnty,
                                 csig=csig, cmon=cmon, csec=csec, norm=norm)
    x, y, zz = s.grid_map(xcol, ycol, zcol, xystep=xystep)
    return Group(__name__ = "SPEC data file %s" % fname, x=x, y=y, zz=zz)


spec_getmap2group.__doc__ += _specfiledata_getdoc("get_map")


def spec_getmrg2group(fname, scans=None, cntx=None, csig=None, cmon=None,
                      csec=None, norm=None, action="average"):

    """*** simple mapping of SpecfileData.get_mrg() to Larch group ***"""
    s = SpecfileData(fname)
    x, y = s.get_mrg(scans=scans, cntx=cntx, csig=csig, cmon=cmon,
                     csec=csec, norm=norm, action=action)

    title = "SPEC data file {0}; scans {1}; action {2}".format(fname, scans, action)
    return Group(__name__=title, x=x, y=y)


spec_getmrg2group.__doc__ += _specfiledata_getdoc("get_mrg")


def str2rng_larch(rngstr, keeporder=True):
    """ larch equivalent of _str2rng() """
    return _str2rng(rngstr, keeporder=keeporder)


str2rng_larch.__doc__ = _str2rng.__doc__


def open_specfile(filename):
    return DataSourceSpecH5(filename)

def read_specfile(filename, scan=None):
    """simple mapping of a Spec file to a larch group"""
    df = DataSourceSpecH5(filename)
    if scan is None:
        df.set_scan(df.get_scans()[0][0])
    else:
        df.set_scan(scan)
    return df.get_scan()
