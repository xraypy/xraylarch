#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Utility wrapper for h5py-like API to Spec files
===================================================

This is a wrapper on top of `silx.io.open` to read Spec_ files via an HDF5-like API.

.. _SPEC: http://www.certif.com/content/spec

Requirements
------------
- silx (http://www.silx.org/doc/silx/latest/modules/io/spech5.html)
"""

__author__ = ["Mauro Rovezzi", "Matt Newville"]
__version__ = "2024.1"

import os
import copy
import datetime
import six
import collections
import numpy as np
import h5py
from silx.io.utils import open as silx_open
from silx.io.h5py_utils import File as silx_h5py_file
from silx.io.convert import write_to_h5

# from scipy.interpolate import interp1d
# from scipy.ndimage import map_coordinates
# from larch.math.utils import savitzky_golay
from larch import Group
from larch.utils.strutils import bytes2str
from larch.math.normalization import norm1D
from larch.math.deglitch import remove_spikes_medfilt1d

#: Python 3.8+ compatibility
try:
    collectionsAbc = collections.abc
except Exception:
    collectionsAbc = collections

# UTILITIES (the class is below!)


def _str2rng(rngstr, keeporder=True, rebin=None):
    """simple utility to convert a generic string representing a compact
    list of scans to a (sorted) list of integers

    Parameters
    ----------
    rngstr : string
        with given syntax (see Example below)
    keeporder : boolean [True]
        to keep the original order
        keeporder=False turn into a sorted list
    rebin : integer [None]
        force rebinning of the final range

    Example
    -------
    > _str2rng('100, 7:9, 130:140:5, 14, 16:18:1')
    > [7, 8, 9, 14, 16, 17, 18, 100, 130, 135, 140]

    the string can also have file index prefix 

    > _str2rng('00019/100, 7:9, 130:140:5, 14, 16:18:1')
    > ('0019', [7, 8, 9, 14, 16, 17, 18, 100, 130, 135, 140])

    """

    try:
        file_idx, scan_str = rngstr.split("/")
        return file_idx, _str2rng(scan_str)
    except Exception:
        pass
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
        except Exception:
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


def is_specfile(filename, require_multiple_scans=True):
    """tests whether file may be a Specfile (text or HDF5)

    Parameters
    ----------
    require_multiple_scans: bool [True]
       for Text-based scans, return True only if the file contains
       multiple scans.

    """
    if not os.path.exists(filename):
        return False
    with open(filename, "rb") as fh:
        topbytes = fh.read(10)

    is_hdf5 = topbytes.startswith(b"\x89HDF\r")  # HDF5
    is_text_one = topbytes.startswith(b"#S ")  # partial Spec file (1 scan)
    is_text_full = topbytes.startswith(b"#F ")  # Full Spec File

    if not (is_hdf5 or is_text_full or is_text_one) or (
        is_text_one and require_multiple_scans
    ):
        return False

    try:
        scans = DataSourceSpecH5(filename)._scans
    except Exception:
        return False

    if is_text_full and require_multiple_scans and len(scans) < 2:
        return False
    return True


def update_nested(d, u):
    """Update a nested dictionary

    From: https://stackoverflow.com/questions/3232943/update-value-of-a-nested-dictionary-of-varying-depth
    """
    for k, v in six.iteritems(u):
        dv = d.get(k, {})
        if not isinstance(dv, collectionsAbc.Mapping):
            d[k] = v
        elif isinstance(v, collectionsAbc.Mapping):
            d[k] = update_nested(dv, v)
        else:
            d[k] = v
    return d


def _atoi(text):
    return int(text) if text.isdigit() else text


def natural_keys(text):
    """
    FROM: https://stackoverflow.com/questions/5967500/how-to-correctly-sort-a-string-with-a-number-inside

    alist.sort(key=natural_keys) sorts in human order
    http://nedbatchelder.com/blog/200712/human_sorting.html
    (See Toothy's implementation in the comments)

    Usage
    -----

    alist=[
        "something1",
        "something12",
        "something17",
        "something2",
        "something25",
        "something29"]

    alist.sort(key=natural_keys)
    print(alist)

    """
    import re

    return [_atoi(c) for c in re.split(r"(\d+)", text)]


# ==================================================================
# CLASS BASED ON SPECH5 (CURRENT/RECOMMENDED)
# ==================================================================
class DataSourceSpecH5(object):
    """Data source utility wrapper for a Spec/BLISS file read as HDF5 object
    via silx.io.open"""

    _file_types = ("Spec", "HDF5")

    def __init__(self, fname=None, logger=None, urls_fmt="silx", verbose=False):
        """init with file name and default attributes

        Parameters
        ----------
        fname : str
            path string of a file that can be read by silx.io.open() [None]
        logger : logging.getLogger() instance
            [None -> larch.utils.logging.getLogger()]
        urls_fmt : str
            how the data are organized in the HDF5 container
            'silx' : default
            'spec2nexus' : as converted by spec2nexus
        verbose : bool [False]
            if True it lowers the logger level to INFO
            if 'debug', it lowers the logger level to DEBUG (for testing)
            othewise WARNING by default
        """
        if logger is None:
            from larch.utils.logging import getLogger

            _logger_name = "DataSourceSpecH5"
            self._logger = getLogger(_logger_name, level="WARNING")
        else:
            self._logger = logger

        if verbose:
            self._logger.setLevel("INFO")

        if isinstance(verbose, str) and verbose.lower() == "debug":
            self._logger.setLevel("DEBUG")

        self._fname = fname
        self._fn = self._fname
        self._sourcefile = None
        self._sourcefile_type = None
        self._scans = None
        self._scans_names = None
        self._scan_n = None
        self._scan_str = None

        self._scan_kws = {  # to get data from scan
            "ax_name": None,
            "to_energy": None,
            "sig_name": None,
            "mon": None,
            "deglitch": None,
            "norm": None,
        }
        self._scangroup = None  # ScanGroup

        self._mots_url = "instrument/positioners"
        self._cnts_url = "measurement"
        self._title_url = "title"
        self._time_start_url = "start_time"
        self._time_end_url = "end_time"
        self._sample_url = "sample/name"
        self._plotcnts_url = "plotselect"
        self._scan_header_url = "instrument/specfile/scan_header"
        self._file_header_url = "instrument/specfile/file_header"
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

        if self._fname is not None:
            self._init_source_file()

    def __enter__(self):
        """enter method for with statement"""
        if h5py.is_hdf5(self._fname):
            self._sourcefile = silx_h5py_file(self._fname, mode="r")
        else:
            self._sourcefile = silx_open(self._fname)
        return self

    def __exit__(self):
        """exit method for with statement"""
        self.close()
        return self

    def _init_source_file(self):
        """init source file object"""
        #: source file object (h5py-like)
        if not os.path.exists(self._fname):
            _errmsg = f"{self._fname} does not exist"
            self._logger.error(_errmsg)
            raise FileNotFoundError(_errmsg)
        try:
            if h5py.is_hdf5(self._fname):
                self._sourcefile = silx_h5py_file(self._fname, mode="r")
                self._logger.debug("HDF5 open with silx.io.h5py_utils")
            else:
                self._sourcefile = silx_open(self._fname)
            for ft in self._file_types:
                if ft in str(self._sourcefile):
                    self._sourcefile_type = ft
            self._scans = self.get_scans()
            self._scans_names = [scn[0] for scn in self._scans]
            try:
                _iscn = 0
                self.set_scan(self._scans[_iscn][0])  # set the first scan at init
                while len(self.get_counters()) == 1:
                    self._logger.warning(
                        f"not enough data in scan {_iscn+1} '{self.get_title()}'"
                    )
                    _iscn += 1
                    self.set_scan(self._scans[_iscn][0])
            except Exception as e:
                self._logger.error(e)
            #self.close()
        except OSError:
            _errmsg = f"cannot open {self._fname}"
            self._logger.error(_errmsg)
            raise OSError(_errmsg)
        try:
            self._fn = self._fname.split(os.sep)[-1]
        except Exception:
            self._logger.debug(f"cannot split {self._fname}")
            pass

    def open(self, mode="r"):
        """Open the source file object with h5py in given mode"""
        try:
            if h5py.is_hdf5(self._fname):
                self._sourcefile = silx_h5py_file(self._fname, mode)
            else:
                _errmsg = f"{self._fname} is not HDF5 file"
                self._logger.error(_errmsg)
                raise ValueError(_errmsg)
        except OSError:
            _errmsg = f"cannot open {self._fname}"
            self._logger.error(_errmsg)
            raise OSError(_errmsg)

    def close(self):
        """Close the source file"""
        self._sourcefile.close()
        self._sourcefile = None

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
            raise AttributeError(
                "Group/Scan not selected -> use 'self.set_scan()' first"
            )
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
        if self._group_url is not None:
            self._logger.info(f"selected group {self._group_url}")

    def set_scan(self, scan, scan_idx=1, group_url=None, scan_kws=None):
        """Select a given scan

        Parameters
        ----------
        scan : int or str
            scan number or name
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
        if scan_kws is not None:
            self._scan_kws = update_nested(self._scan_kws, scan_kws)

        if isinstance(scan, int):
            scn = f"{scan}_"
            for slist in self._scans:
                sl0 = slist[0]
                if scn in sl0.lower():
                    self._logger.debug(f"scan '{scan}' -> '{sl0}'")
                    scan = sl0
                    break

        if scan in self._scans_names:
            self._scan_str = scan
            self._scan_n = self._scans_names.index(scan)
        else:
            scan_n = scan
            if isinstance(scan, str):
                scan_split = scan.split(".")
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
                    _errmsg = "scan not selected, wrong 'scan' parameter!"
                    self._logger.error(_errmsg)
                    raise ValueError(_errmsg)
            assert isinstance(scan_n, int), "'scan_n' must be an integer"
            assert isinstance(scan_idx, int), "'scan_idx' must be an integer"
            self._scan_n = scan_n
            if self._urls_fmt == "silx":
                self._scan_str = f"{scan_n}.{scan_idx}"
            elif self._urls_fmt == "spec2nexus":
                self._scan_str = f"S{scan_n}"
            else:
                _errmsg = "wrong 'urls_fmt'"
                self._logger.error(_errmsg)
                raise ValueError(_errmsg)
        if group_url is not None:
            self.set_group(group_url)
        if self._group_url is not None:
            self._scan_url = f"{self._group_url}/{self._scan_str}"
        else:
            self._scan_url = f"{self._scan_str}"
        try:
            self._scangroup = self._sourcefile[self._scan_url]
            self._scan_title = self.get_title()
            self._scan_start = self.get_time()
            self._logger.info(
                f"selected scan '{self._scan_url}' | '{self._scan_title}' | '{self._scan_start}'"
            )
        except KeyError:
            self._scangroup = None
            self._scan_title = None
            _errmsg = f"'{self._scan_url}' is not valid"
            self._logger.error(_errmsg)
            raise KeyError(_errmsg)

    def _list_from_url(self, url_str):
        """Utility method to get a list from a scan url

        .. warning:: the list is **not ordered**

        """
        try:
            return [i for i in self.get_scangroup()[url_str].keys()]
        except Exception:
            _errmsg = f"[{self._fn}//{self._scan_n}] '{url_str}' not found"
            self._logger.error(_errmsg)
            #raise ValueError(_errmsg)

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
        for sn in self._sourcefile["/"].keys():
            try:
                sg = self._sourcefile[sn]
            except KeyError:
                continue  # broken HDF5 link
            try:
                allscans.append(
                    [
                        sn,
                        bytes2str(sg[self._title_url][()]),
                        bytes2str(sg[self._time_start_url][()]),
                    ]
                )
            except KeyError:
                self._logger.error(f"'{sn}' is a datagroup!")
                # go one level below and try take first dataset only
                dt0 = list(sg.keys())[0]
                sgg = sg[dt0]
                try:
                    scname = f"{sn}/{dt0}"
                    allscans.append(
                        [
                            scname,
                            bytes2str(sgg[self._title_url][()]),
                            bytes2str(sgg[self._time_start_url][()]),
                        ]
                    )
                except Exception:
                    self._logger.error(
                        f"{scname} does not have standard title/time URLs"
                    )
                    allscans.append([None, None, None])

        # sort scan in natural/human order
        allscans.sort(key=lambda row: natural_keys(row[0]))

        return allscans

    def get_motors(self):
        """Get list of all available motors names"""
        return self._list_from_url(self._mots_url)

    def get_scan_motors(self):
        """Get list of motors names actually used in the scan"""
        all_motors = self._list_from_url(self._mots_url)
        counters = self._list_from_url(self._cnts_url)
        return [i for i in counters if i in all_motors]

    def get_counters(self, remove_motors=False):
        """Get list of counters names

        Parameters
        ----------
        remove_motors:  bool [False]
             whether to remove counters that would also be in the motors list
        """
        counters = self._list_from_url(self._cnts_url)
        if remove_motors:
            motors = self._list_from_url(self._mots_url)
            counters = [i for i in counters if i not in motors]
        return counters

    def get_title(self):
        """Get title str for the current scan

        Returns
        -------
        title (str): scan title self._scangroup[self._title_url][()]
        """
        sg = self.get_scangroup()
        return bytes2str(sg[self._title_url][()])

    def get_time(self):
        """Get start time str for the current scan

        Returns
        -------
        start_time (str): scan start time self._scangroup[self._time_start_url][()]
        """
        sg = self.get_scangroup()
        return bytes2str(sg[self._time_start_url][()])

    def get_timestamp(self):
        """Get timestamp from the current scan"""
        dt = np.datetime64(self.get_time())
        return dt.astype(datetime.datetime).timestamp()

    def get_scan_info_from_title(self):
        """Parser to get scan information from title

        Known types of scans
        --------------------
        Generic: <scan_type> <scan_axis> <start> <end> <npoints> <counting_time>
        'Escan'               (ESRF BM30/BM16 Spec -> Energy)
        'Emiscan'             (ESRF BM30/BM16 Spec -> Emi_Energy)
        'fscan'               (ESRF ID26 Spec -> mono_energy)
        'contscan.motor'      (ESRF ID24-DCM BLISS 2023-06 -> energy_enc)
        'contscan.EnergyCont' (ESRF BM16 BLISS 2023-09 -> energy_enc)
        'scans.exafs*'        (ESRF BM23 BLISS 2023-06 -> energy_cenc)

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
             scan_info : ""
            }
        """
        iscn = dict(
            scan_type=None,
            scan_axis=None,
            scan_start=None,
            scan_end=None,
            scan_pts=None,
            scan_ct=None,
            scan_info=None,
        )

        _title = self.get_title()
        if isinstance(_title, np.ndarray):
            _title = np.char.decode(_title)[0]
        _title_splitted = [s for s in _title.split(" ") if not s == ""]
        _scntype = _title_splitted[0]
        iscn.update(dict(scan_type=_scntype))
        try:
            iscn.update(
                dict(
                    scan_axis=_title_splitted[1],
                    scan_start=_title_splitted[2],
                    scan_end=_title_splitted[3],
                    scan_pts=_title_splitted[4],
                    scan_ct=_title_splitted[5],
                )
            )
        except IndexError:
            try:
                iscn.update(
                    dict(
                        scan_start=_title_splitted[1],
                        scan_end=_title_splitted[2],
                        scan_pts=_title_splitted[3],
                        scan_ct=_title_splitted[4],
                    )
                )
            except IndexError:
                pass

        # === CUSTOM SCANS -> TODO(move to NeXus)
        if _scntype == "Escan": 
            iscn.update(dict(scan_axis="Energy"))
            iscn.update(dict(scan_info="ESRF/BM30-BM16 Energy scans with Spec"))
        if _scntype == "Emiscan":
            iscn.update(dict(scan_axis="Emi_Energy"))
            iscn.update(dict(scan_info="ESRF/BM30-BM16 emission scans with Spec"))
        if _scntype == "fscan":
            iscn.update(dict(scan_axis="mono_energy"))
            iscn.update(dict(scan_info="ESRF/ID26 fscan"))
        if "scans.exafs" in _scntype:
            iscn.update(dict(scan_axis="energy_cenc"))
            iscn.update(dict(scan_info="ESRF/BM23 BLISS 2023-June"))
        if _scntype == "contscan.motor":
            iscn.update(dict(scan_axis="energy_enc"))
            iscn.update(dict(scan_info="ESRF/ID24-DCM BLISS 2023-June"))
        if _scntype == "contscan.EnergyCont":
            iscn.update(dict(scan_axis="energy_enc"))
            iscn.update(dict(scan_info="ESRF/BM16 BLISS 2023-Sept"))
        if _scntype == "trigscan":
            iscn.update(dict(scan_axis="energy_enc"))
            iscn.update(dict(scan_info="ESRF/BLISS 2023-Dec"))
        return iscn

    def get_scan_axis(self):
        """Get the name of the scanned axis from scan title"""
        iscn = self.get_scan_info_from_title()
        _axisout = iscn["scan_axis"]
        _mots, _cnts = self.get_motors(), self.get_counters()
        if not (_axisout in _mots):
            self._logger.debug(f"'{_axisout}' not in (real) motors")
        if not (_axisout in _cnts):
            self._logger.debug(f"'{_axisout}' not in counters")
            _axisout = _cnts[0]
            self._logger.info(f"using the first counter: '{_axisout}'")
        return _axisout

    def get_array(self, cnt=0):
        """Get array of a given counter

        Parameters
        ----------
        cnt : str or int
            counter name or index in the list of counters

        Returns
        -------
        array
        """
        sg = self.get_scangroup()
        cnts = self.get_counters()
        if type(cnt) is int:
            cnt = cnts[cnt]
            self._logger.info("Selected counter %s", cnt)
        if cnt in cnts:
            sel_cnt = f"{self._cnts_url}/{cnt}"
            return copy.deepcopy(sg[sel_cnt][()])
        else:
            errmsg = f"[{self._fn}//{self._scan_n}] '{cnt}' not found in available counters"
            self._logger.error(errmsg)
            raise ValueError(errmsg)

    def get_motor_position(self, mot):
        """Get motor position

        Parameters
        ----------
        mot : str or int
            motor name or index in the list of motors

        Returns
        -------
        value
        """
        sg = self.get_scangroup()
        mots = self.get_motors()
        if type(mot) is int:
            mot = mots[mot]
            self._logger.info(f"Selected motor '{mot}'")
        if mot in mots:
            sel_mot = f"{self._mots_url}/{mot}"
            return copy.deepcopy(sg[sel_mot][()])
        else:
            self._logger.error(f"[{self._fn}//{self._scan_n}] '{mot}' not found in available motors")
            return None

    def get_scan(self, scan=None, datatype=None):
        """Get Larch group for the current scan

        Parameters
        ----------
        scan  : str, int, or None
             scan address
        datatype : str
            type of data, e.g. 'raw', 'xas'

        Returns
        -------
        larch Group with scan data
        """
        scan_group = self.get_scangroup(scan)
        scan_index = self._scan_n
        scan_name = self._scan_str
        all_labels = self.get_counters()
        motor_names = self.get_scan_motors()
        title = self.get_title()
        timestring = self.get_time()
        timestamp = self.get_timestamp()
        path, filename = os.path.split(self._fname)
        axis = self.get_scan_axis()
        array_labels = [axis]
        array_labels.extend([i for i in motor_names if i not in array_labels])
        array_labels.extend([i for i in all_labels if i not in array_labels])

        scan_header = list(scan_group.get(self._scan_header_url, []))
        file_header = list(scan_group.get(self._file_header_url, []))
        file_type = self._sourcefile_type
        header = []
        for scanh in scan_header:
            if scanh.startswith("#CXDI "):
                header.append(scanh[6:].strip())
        out = Group(
            __name__=f"{file_type} file: {filename}, scan: {scan_name}",
            path=path,
            filename=filename,
            datatype=datatype,
            array_labels=array_labels,
            motor_names=motor_names,
            axis=axis,
            scan_index=scan_index,
            scan_name=scan_name,
            title=title,
            header=header,
            scan_header=scan_header,
            file_header=file_header,
            timestring=timestring,
            timestamp=timestamp,
        )

        arr_axis = self.get_array(axis).astype(np.float64)
        axis_size = arr_axis.size
        data = [arr_axis]
        ptsdiffs = [0]
        pop_labels = []
        self._logger.debug(f"X array (=scan axis): `{axis}` (size: {axis_size})")
        self._logger.debug("Y arrays >>> loading all arrays in array_labels (check size match with scan axis) <<<")
        for label in array_labels[1:]: #: avoid loading twice arr_axis
            arr = self.get_array(label).astype(np.float64)
            ptsdiff = axis_size - arr.size
            self._logger.debug(f"`{label}` ({arr.size}) -> {abs(ptsdiff)}")           
            if abs(ptsdiff) > 10 or ptsdiff < 0:
                ipop = array_labels.index(label)
                pop_labels.append(array_labels.pop(ipop))
            else:
                ptsdiffs.append(ptsdiff)
                data.append(arr)
                setattr(out, label, arr)
        assert len(array_labels) == len(data) == len(ptsdiffs), "length of array_labels and data do not match"
        if len(pop_labels):
            self._logger.info(f"Y arrays >>> not loaded: `{pop_labels}` [excessive size mismatch with `{axis}`]")
        #: in case of array shape mismatch strip last points
        ptsdiff_max = max(ptsdiffs)
        if ptsdiff_max > 0:
            out_size = axis_size - ptsdiff_max
            for iarr, (lab, arr) in enumerate(zip(array_labels, data)):
                ptsdiff = axis_size - arr.size
                arr = arr[:out_size]
                data[iarr] = arr
                setattr(out, lab, arr)
            self._logger.info(f"Y arrays >>> removed {ptsdiff_max} last points")
        out.data = np.array(data)
        return out

    def get_axis_data(self, ax_name=None, to_energy=None):
        """Get data for the scan axis

        Description
        -----------
        This method returns the data (=label and array) for a given axis of the
        selected scan. It is primarily targeted to a "scanning" axis, but any
        counter can be used. It is possible to control common conversions, like
        Bragg angle to energy.

        Parameters
        ----------
        ax_name : str or None

        to_energy : dict
            Controls the conversion of the signal to energy [None]

            .. note:: Bragg angle assumed in mrad, output in eV

            {
                "bragg_ax": "str",  #: name of counter used for Bragg angale
                "bragg_ax_type": "str",  #: 'motor' or 'counter'
                "bragg_enc_units": float, #: units to convert encoder to deg (bragg_ax should contain 'enc')
            }

        Returns
        -------
        label, data
        """
        if (ax_name is not None) and (ax_name not in self.get_counters()):
            self._logger.error("%s not a counter", ax_name)
            return None, None
        ax_label = ax_name or self.get_scan_axis()
        ax_data = self.get_array(ax_label)
        if to_energy is not None:
            try:
                from sloth.utils.bragg import ang2kev
            except ImportError:

                def ang2kev(theta, d):
                    from larch.utils.physical_constants import PLANCK_HC

                    theta = np.deg2rad(theta)
                    wlen = 2 * d * np.sin(theta)
                    return (PLANCK_HC / wlen) / 1000.0

            bragg_ax = to_energy["bragg_ax"]
            bragg_ax_type = to_energy["bragg_ax_type"]
            bragg_d = to_energy["bragg_d"]
            if bragg_ax_type == "counter":
                bragg_deg = self.get_array(bragg_ax).mean()
            elif bragg_ax_type == "motor":
                bragg_deg = self.get_value(bragg_ax)
            else:
                self._logger.error("wrong 'bragg_ax_type' (motor or counter?)")
            if "enc" in bragg_ax:
                bragg_deg = (np.abs(bragg_deg) / to_energy["bragg_enc_units"]) * 360
            ax_abs_deg = bragg_deg + np.rad2deg(ax_data) / 1000.0
            ax_abs_ev = ang2kev(ax_abs_deg, bragg_d) * 1000.0
            ax_data = ax_abs_ev
            ax_label += "_abs_ev"
            self._logger.debug("Converted axis %s", ax_label)
            xmin = ax_data.min()
            xmax = ax_data.max()
            self._logger.info("%s range: [%.3f, %.3f]", ax_label, xmin, xmax)
        return ax_label, ax_data

    def get_signal_data(self, sig_name, mon=None, deglitch=None, norm=None):
        """Get data for the signal counter

        Description
        -----------
        This method returns the data (=label and array) for a given signal of the
        selected scan. It is possible to control normalization and/or deglitching.

        Order followed in the basic processing:
            - raw data
            - divide by monitor signal (+ multiply back by average)
            - deglitch
            - norm

        Parameters
        ----------
        sig_name : str
        mon : dict
            Controls the normalization of the signal by a monitor signal [None]
            {
                "monitor": "str",  #: name of counter used for normalization
                "cps": bool,  #: multiply back to np.average(monitor)
            }
        deglitch : dict
            Controls :func:`larch.math.deglitch.remove_spikes_medfilt1d` [None]
        norm : dict
            Controls the normalization by given method

        Returns
        -------
        label, data
        """
        #: get raw data
        sig_data = self.get_array(sig_name)
        sig_label = sig_name
        #: (opt) divide by monitor signal + multiply back by average
        if mon is not None:
            if isinstance(mon, str):
                mon = dict(monitor=mon, cps=False)
            mon_name = mon["monitor"]
            mon_data = self.get_array(mon_name)
            sig_data /= mon_data
            sig_label += f"_mon({mon_name})"
            if mon["cps"]:
                sig_data *= np.average(mon_data)  #: put back in counts
                sig_label += "_cps"
        #: (opt) deglitch
        if deglitch is not None:
            sig_data = remove_spikes_medfilt1d(sig_data, **deglitch)
            sig_label += "_dgl"
        #: (opt) normalization
        if norm is not None:
            norm_meth = norm["method"]
            sig_data = norm1D(sig_data, norm=norm_meth, logger=self._logger)
            if norm_meth is not None:
                sig_label += f"_norm({norm_meth})"
        self._logger.info("Loaded signal: %s", sig_label)
        return sig_label, sig_data

    def get_curve(
        self,
        sig_name,
        ax_name=None,
        to_energy=None,
        mon=None,
        deglitch=None,
        norm=None,
        **kws,
    ):
        """Get XY data (=curve) for current scan

        Parameters
        ----------
        *args, **kws -> self.get_axis_data() and self.get_signal_data()

        Returns
        -------
        [ax_data, sig_data, label, attrs] : list of [array, array, str, dict]

        """
        ax_label, ax_data = self.get_axis_data(ax_name=ax_name, to_energy=to_energy)
        sig_label, sig_data = self.get_signal_data(
            sig_name, mon=mon, deglitch=deglitch, norm=norm
        )
        label = f"S{self._scan_n}_X({ax_label})_Y{sig_label}"
        attrs = dict(
            xlabel=ax_label,
            ylabel=sig_label,
            label=label,
            ax_label=ax_label,
            sig_label=sig_label,
        )
        return [ax_data, sig_data, label, attrs]

    # =================== #
    #: WRITE DATA METHODS
    # =================== #

    def write_scans_to_h5(
        self,
        scans,
        fname_out,
        scans_groups=None,
        h5path=None,
        overwrite=False,
        conf_dict=None,
    ):
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


def str2rng_larch(rngstr, keeporder=True):
    """larch equivalent of _str2rng()"""
    return _str2rng(rngstr, keeporder=keeporder)


str2rng_larch.__doc__ = _str2rng.__doc__


def open_specfile(filename):
    return DataSourceSpecH5(filename)


def read_specfile(filename, scan=None):
    """simple mapping of a Spec/BLISS file to a Larch group"""
    df = DataSourceSpecH5(filename)
    return df.get_scan(scan)
