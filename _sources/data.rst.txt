.. include:: _config.rst


.. _data-io_chapter:

============================
Reading and Writing Data
============================

Larch has several built-in functions for reading and writing scientific
data.  The intention is that the types and varieties of supported files
will increase.  In addition, because standard Python modules can be used
from Larch, many types of standard data and image types can be used by
importing the appropriate Python module.  This chapter describes the Larch
functions for data handling.


.. module:: larch.io

.. _read_ascii_function:

Simple Plaintext (ASCII or UTF-8) Column Files
====================================================

A simple way to store small amounts of numerical data - and one that is widely used in
the XAFS community - is to store data in plaintext data files, with whitespaces
separating numbers layed out as a table, with a fix number of columns and rows indicated
by newlines. By "plaintext", we mean files that are not binary.  Many of these will
contain only "ASCII" characters (for basic English text without accents or non-Latin
characters), but they can also contain some characters representing non-English
language, as represented by "Latin-1" or "UTF-8" encodings.  Typically a comment
character such as "#" is used to signify header information.  For instance::

    # room temperature FeO
    # data from 20-BM, 2001, as part of NXS school
    # powder on tape, 4 layers
    # 2001-08-10T11:10:00
    # Si(111), d_spacing: 3.13553
    #------------------------
    #  energy       xmu             i0
      6911.7671   -0.35992590E-01  280101.00
      6916.8730   -0.39081634E-01  278863.00
      6921.7030   -0.42193483E-01  278149.00
      6926.8344   -0.45165576E-01  277292.00
      6931.7399   -0.47365589E-01  265707.00

This file has some lines of text which give human readable information about the data
collected, and then data for different arrays or channels arranged in columns, with each
line or row representing a new data point. While not a very specific description of a
data file (see, XDI below), such files are very common in the XAFS community.  Such files
can usually be read with the builtin :func:`read_ascii` function.   Which will turn each
column into an array, usually named by the column heading.  That often means that as you
read these files in, you also need to know and tell the program how to use those arrays.

.. autofunction:: read_ascii

.. autofunction:: write_ascii

.. autofunction:: write_group




.. _read_xdi_function:

Reading XAFS Data Interchange (XDI) Files
=================================================

The X-ray Data Interchange Format has been developed as part of an effort to standardize
the format of plaintext XAFS data files: see `XDI`_.  This eliminates some of the
challenges with plaintext files and allows consistent naming of arrays.  XDI files often
use the `.xdi` extension but are also identified by having a first line that includes
`XDI`.  These files should be considered to be "the normal way" to read X-ray Absorption
Spectroscopy Data into Larch. To read an XDI file with Larch, use :func:`read_xdi()`.
This will create a Group with several consistently named arrays and values that are
useful for processing XAS data. A more detailed description is given at `XDI metadata
dictionary`_.  The most important components read from an XDI file are give in the
:ref:`Table of XDI Attributes <xdi_attr_table>` below.


.. autofunction:: read_xdi


.. _xdi_attr_table:

**Table of XDI attributes** These are the standard names and meanings for arrays and
scalars values taken from XDI files.


  +---------------+------------+-------------------------------------------------------------------+
  | name          | type       |   meaning                                                         |
  +===============+============+===================================================================+
  | energy        | 1-D array  | X-ray energy in eV                                                |
  +---------------+------------+-------------------------------------------------------------------+
  | angle         | 1-D array  | rotation angle (degrees) for doube crystal monochromator          |
  +---------------+------------+-------------------------------------------------------------------+
  | i0            | 1-D array  | :math:`I_0`: measurement (arbitrary units) of incident flux       |
  +---------------+------------+-------------------------------------------------------------------+
  | mutrans       | 1-D array  | :math:`\mu` (unitless) for Transmission XAS data                  |
  +---------------+------------+-------------------------------------------------------------------+
  | itrans        | 1-D array  | :math:`I_1`: measurement (arbitrary units) of transmitted flux    |
  +---------------+------------+-------------------------------------------------------------------+
  | mufluor       | 1-D array  | :math:`\mu` (unitless) for Fluorescence XAS data                  |
  +---------------+------------+-------------------------------------------------------------------+
  | ifluor        | 1-D array  | :math:`I_f`: measurement (arbitrary units) of fluoresced flux     |
  +---------------+------------+-------------------------------------------------------------------+
  | data          | 2-D array  | raw data from data columns, shape=(narrays, npts)                 |
  +---------------+------------+-------------------------------------------------------------------+
  | narrays       | integer    | number of 1-D arrays                                              |
  +---------------+------------+-------------------------------------------------------------------+
  | npts          | integer    | number of points in each 1-D array                                |
  +---------------+------------+-------------------------------------------------------------------+
  | dspacing      | float      | :math:`d` spacing (in :math:`\unicode{x212B}`) of monoochromator  |
  +---------------+------------+-------------------------------------------------------------------+
  | dspacing      | float      | :math:`d` spacing (in :math:`{\AA}`) of monoochromator            |
  +---------------+------------+-------------------------------------------------------------------+
  | element       | string     | atomic symbol for absorbing element                               |
  +---------------+------------+-------------------------------------------------------------------+
  | edge          | string     | symbol for absorbing edge                                         |
  +---------------+------------+-------------------------------------------------------------------+
  | array_labels  | list       | list of strings holding labels for `narray` arrays                |
  +---------------+------------+-------------------------------------------------------------------+
  | array_units   | list       | list of strings describing units for `narray` arrays              |
  +---------------+------------+-------------------------------------------------------------------+
  | attrs         | dict       | dictionary of metadata, using XDI namespaces to nest values       |
  +---------------+------------+-------------------------------------------------------------------+
  | comments      | string     | additional user-supplied comments from XDI file                   |
  +---------------+------------+-------------------------------------------------------------------+
  | xdi_version   | string     | XDI version                                                       |
  +---------------+------------+-------------------------------------------------------------------+


Athena Project Files
============================

The popular Athena program for XAFS Analysis uses an "Athena Project File"
to store many XAFS spectra and some processing parameters as used in
Athena.  Larch can read and extract the :math:`\mu(E)` data from these
project files - it does not read :math:`\chi(k)` from these files.  Larch
and can also write :math:`\mu(E)` data to Athena Project files.

Larch does not read or support Artemis projects.

.. _read_athena_function:

Reading Athena Project Files
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. function:: read_athena(filename, match=None, do_preedge=True, do_bkg=True, do_fft=True, use_hashkey=False)

   open and read an Athena Project File, returning a group of groups, each
   subgroup corresponding to an Athena Group from the project file.

   :param filename:   name of Athena Project file
   :param match:      string pattern used to limit the imported groups (see Note)
   :param do_preedge: bool, whether to do pre-edge subtraction
   :param do_bkg:     bool, whether to do XAFS background subtraction
   :param do_fft:     bool, whether to do XAFS Fast Fourier transform
   :param use_hashkey: bool, whether to use Athena's hash key as the group name, instead of the Athena label.
   :return:  group of groups.

Notes:
     1. To limit the imported groups, use the pattern in `match`,
        using '*' to match 'all', '?' to match any single character,
        or [sequence] to match any of a sequence of letters.  The match
        will always be insensitive to case.
     2. `do_preedge`, `do_bkg`, and `do_fft` will attempt to reproduce the
        pre-edge, background subtraction, and FFT from Athena by using
        the parameters saved in the project file.
     3. `use_hashkey=True` will name groups from the internal 5 character
        string used by Athena, instead of the group label.

A simple example of reading an Athena Project file::

    larch> hg_prj = read_athena('Hg.prj')
    larch> show(hg_prj)
    == Group 0x11b001e50: 0 methods, 5 attributes ==
      HgO: <Group 0x1c2e6f48d0>
      HgS_black: <Group 0x1c2e6f49d0>
      HgS_red: <Group 0x1c2e6f4ad0>
      _athena_header: u'# Athena project file -- Demeter version 0.9.26\n# This file created at 2018-06-24T21:55:31\n# Using Demeter 0.9.26 with perl 5.026001 and using Larch X.xx on darwin'
      _athena_journal: [u'Hg 15nM in 50 mM Na Cacodylate (As-containing buffer) ', u'100 mM NaClO4, pH 6.10', u'Hg 15nM in 50 mM Na Cacodylate (As-containing buffer) ', u'100 mM NaClO4, pH 6.10']


.. function:: extract_athenagroup(datagroup)

   extracts a group out of an Athena Project File, allowing the file to be
   closed.

   :param datagroup:  group from athena project
   :return:  group with copy of data, allowing safe closing of project file

An example using this function to allow extracting 1 group from an Athena
Project would be::

    larch> hg_prj = read_athena('Hg.prj')
    larch> hgo = extract_athenagroup(hg_prj.HgO)
    larch> del hg_prj

Creating and Writing to Athena Project Files
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

You can create an Athena Project File with :func:`create_athena` and then
add a group of XAFS data to that pct with the :meth:`add_group`
method of that project file.  The group is expected to have array names of
`energy` and `i0`, and one of `mu`, `mutrans`, or `mufluor`.

.. function:: create_athena(filename)

   Open a new or existing Athena Project File, returning an
   :class:`AthenaProject` object.  That is, a new project file will be
   created if it does not exist, or an existing project will be opened for
   reading and writing.

   :param filename:   name of Athena Project file

.. class:: AthenaProject(filename)

   A representation of an Athena Project File

.. method:: AthenaProject.add_group(group, signal=None)

   add a group of XAFS data to an Athena Project

   :param group:   group to be added. See note
   :param signal:  string or ``None`` name of array to use as main signal

   if `signal` is not specified, it will be chosen as `mu`, `mutrans`, or
   `mufluor` (in that order).

.. method:: AthenaProject.save(use_gzip=True)

   save project to file

   :param use_gzip:  bool, whether to use gzip compression for file.

.. method:: AthenaProject.read(filename=None, match=None, do_preedge=True, do_bkg=True, do_fft=True, use_hashkey=False)

   read from project.

   :param filename:   name of Athena Project file
   :param match:      string pattern used to limit the imported groups (see Note)
   :param do_preedge: bool, whether to do pre-edge subtraction
   :param do_bkg:     bool, whether to do XAFS background subtraction
   :param do_fft:     bool, whether to do XAFS Fast Fourier transform
   :param use_hashkey: bool, whether to use Athena's hash key as the group name, instead of the Athena label.

The function :func:`read_athena` above is a wrapper around this method, and
the notes there apply here as well. An important difference is that for
this method the data is retained in the `groups` attribute which is a
Python list of groups for each group in the Athena Project.

.. method:: AthenaProject.as_group()

     Return the Athena Project `groups` attribute (as read by
     :meth:`read`) to a larch Group of groups.

As an example creating and saving an Athena Project file::

    larch> feo = read_ascii('feo_rt1.dat', label='energy mu i0')
    larch> autobk(feo, rbkg=1.0, kweight=1)
    larch> fe2o3 = read_ascii('fe2o3_rt1.xmu')
    larch> autobk(fe2o3, rbkg=1.0, kweight=1)
    larch> fe_project = create_athena('FeOxides.prj')
    larch> fe_project.add_group(feo)
    larch> fe_project.add_group(fe2o3)
    larch> fe_project.save()

Converting Athena Project Files to HDF5
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

An Athena Project File (.prj) can be easily converted to HDF5 (.h5) with the :func:`athena_to_hdf5`.

.. function:: athena_to_hdf5(filename, fileout=None, overwrite=False, match=None, do_preedge=True, do_bkg=True, do_fft=True, use_hashkey=False)

   convert read an Athena Project File to HDF5

   :param filename:   name of Athena Project file
   :param fileout:    name of the HDF5 file [None -> filename_root.h5]
   :param overwrite:  bool, whether to overwrite existing outputfile
   :param match:      string pattern used to limit the imported groups (see Note)
   :param do_preedge: bool, whether to do pre-edge subtraction
   :param do_bkg:     bool, whether to do XAFS background subtraction
   :param do_fft:     bool, whether to do XAFS Fast Fourier transform
   :param use_hashkey: bool, whether to use Athena's hash key as the group name, instead of the Athena label.
   :return:  None


Reading HDF5 Files
========================

HDF5 is an increasingly popular data format for scientific data, as it can
efficiently hold very large arrays in a heirarchical format that holds
"metadata" about the data, and can be explored with a variety of tools.
The interface used in Larch is based on `h5py`_, which should be consulted
for further documentation.

.. function:: h5_group(filename)

    opens and maps and HDF5 file to a Larch Group, with HDF5 Groups map as
    Larch Groups.  Note that the full set of data is not read and
    copied. Instead, the HDF5 file is kept open and data accessed from the
    file as needed.

An example using :func:`h5_group` shows that one can browse through the
data heirarchy of the HDF5 file, and pick out the needed data::

    larch> g = h5group('test.h5')
    larch> show(g)
    == Group test.h5: 3 symbols ==
      attrs: {u'Collection Time': ': Sat Feb 4 13:29:00 2012', u'Version': '1.0.0',
              u'Beamline': 'GSECARS, 13-IDC / APS', u'Title': 'Epics Scan Data'}
      data: <Group test.h5/data>
      h5_file: <HDF5 file "test.h5" (mode r)>
    larch>show(g.data)
    == Group test.h5/data: 5 symbols ==
      attrs: {u'scan_prefix': '13IDC:', u'start_time': ': Sat Feb 4 13:29:00 2012',
            u'correct_deadtime': 'True', u'dimension': 2,
            u'stop_time': ': Sat Feb 4 13:44:52 2009'}
      environ: <Group test.h5/data/environ>
      full_xrf: <Group test.h5/data/full_xrf>
      merged_xrf: <Group test.h5/data/merged_xrf>
      scan: <Group test.h5/data/scan>


    larch> g.data.scan.sums
    <HDF5 dataset "det": shape (15, 26, 26), type "<f8">

    larch> imshow(g.data.scan.sums[8:,:,:])

This interface is general-purpose but somewhat low-level.  As HDF5 formats
and schemas become standardized, better interfaces can easily be made on
top of this approach.

Reading NetCDF Files
============================

NetCDF4 is an older and less flexible file format than HDF5, but is
efficient for storing array data and still in wide use.

.. function:: netcdf_group(filename)

  returns a group with data from a NetCDF4 file.

.. function:: netcdf_file(filename, mode='r')

  opens and returns a netcdf file.


Reading TIFF Images
============================

TIFF is a popular image format used by many cameras and detectors. The
interface used in Larch is based on code from Chrisoph Gohlke.

.. function:: read_tiff(fname)

   reads a TIFF image from a TIFF File.  This returns just the image data as an
   array, and does return any metadata.

.. function:: tiff_object(fname)

   opens and returns a TIFF file.  This is useful for extracting metadata
   and multiple series.


Working with Epics Channel Access
===================================

Many synchrotron facilities use the Epics control system.  If the Epics
Channel Access layer, which requires network access and configuration
discussed elsewhere, are set correcty, then Larch can read and write data
from Epics Process Variables (PVs).  The interface used in Larch is based
on `pyepics`_, which should be consulted for further documentation. The
access is encapsulated into three functions:

.. function:: caget(PV_name, as_string=False)

   get the value of the Process Variable.  The optional ``as_string``
   argument ensures the returned value is the string representation for the
   variable.

.. function:: caput(PV_name, value, wait=False)

   set the value of the Process Variable.  If the optional ``wait`` is
   ``True``, the function will not return until the put "completes". For
   some types of data, this may wait for some process (moving a motor,
   triggering a detector) to finish before returning.

.. function:: PV(PV_name)

   create and return an Epics PV object for a Process Variable.  This will
   have get() and put() methods, and allows you to add callback functions
   which will be run with new values everytime the PV value changes.

Reading Scan Data from APS Beamlines
===========================================

This list is minimal, but can be expanded easily to accomodate more
facilities and beamlines.

.. function:: read_gsescan(filename)

   read a (old-style) GSECARS Escan data file into a group.

.. function:: read_stepscan(filename)

   read a GSECARS StepScan data file into a group.




Reading Spec/BLISS files via `silx.io.open`
============================================

Spec ASCII files (see `spec`_) and BLISS HDF5 files (see `bliss`_) are read via
the `silx.io.open` module (see `silx`_).

.. function:: read_specfile(filename, scan=None)

   Get a Larch group for a given scan number. If `scan=None` the first scan is returned.

Reading FDMNES output files
============================

ASCII files from the [FDMNES](http://fdmnes.neel.cnrs.fr/) are read via

.. function:: read_fdmnes(filename)

   Return a Larch group

This function is a simple wrapper on top of `read_ascii`, parsing the header in
order to shift the energy scale to absolute values, according to the `E_edge`
variable. The parsed variables are stored in the `group.header_dict` dictionary.


.. _larch_session_files:

Saving and Loading Larch Session Files: `.larix` Files
=========================================================

A *Larch Session File*, with a `.larix` extension, contains all of the user-generated
data within a Larch session.  All of the data -- input data arrays, processed arrays,
dictionaries, Journals, etc -- from all of Groups, and all of processing parameters,
analysis results and fit histories will be included.  The Session file will also include
a list of all Larch commands executed in the current Larch session (GUI or Command-Line
Application), and also include configuration about the session (including versions of
Larch and Python, operating system, and so on).  Session Files effectively allows you to
save your session as a "Project" and be able to share it with someone else or come back
to it later, picking up the analysis where you left it. The Session files are meant to
be completely portable across different computers and versions.

For portability, Larch Session file is a simple gzipped set of plaintext.  JSON is to
use to serialize all of the data, including complex and nested Python data structures.
While all the data are stored using portable formats and well-supported libraries, it
would not necessarily be easy to open and use these files without the Python code in
Larch to read these files.

The :func:`save_session` function will simply save all the data in the current session.
The :func:`load_session` function will restore data from a Session file into the current
session.  On the other hand, :func:`read_session` will read the data but not install it
analysis session. Instead, it will return a new set of data that you might have to
unpack or extract the groups and arrays of interest.

.. autofunction:: save_session

.. autofunction:: read_session

.. autofunction:: load_session

.. autofunction:: clear_session
