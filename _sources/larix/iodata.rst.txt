.. include:: ../_config.rst

.. _larix_io:

Reading and Saving Data into Larix
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Larix can import XAS data in the following formats

   * XDI data files - the standard data format for XAS data.
   * plain text data data files with data arrays in column format.
   * Athena Project Files.
   * ESRF Spec/BLISS HDF5 files.
   * Larch Session files (:ref:`larix_sessionfiles`).

When reading data from plain text files with column of data (which is how most
beamlines and instruments will save data), it is possible to manipulate the
data in several ways:

   * columns of data can be assigned to make ``-log(I_transmission / I_0)`` or
     ``I_fluorescence/I_0`` for transmission or fluorescence data
   * a reference spectrum can be read in, also either in transmission or
     fluorescence.
   * a special dialog can be used to construct a sum of dead-time corrected
     fluorescence channels for files that record columns of un-corrected
     fluorescence, and also record columns for some variations of deadtime
     information such as InputCountRate, OutputCountRate, Live Time, and so
     forth.
   * multiple columns can be read in simultaneously into separate groups,
     as long as all the channels share a common ``I_0`` channel, as for
     multi-element fluorescence or files that contain multiple channels of
     :math:`\mu(E)`.
   * For data recorded with angle of the double-crystal monochromator in
     degrees, the angle can be converted to energy by setting the lattice
     constant of the monochromator.


For exporting or saving data, Larix can save multiple XAS spectra as:

   * Athena Project files. (:ref:`larix_sessionfiles`).
   * CSV files.
   * Larch Session files (:ref:`larix_sessionfiles`).

.. _larix_plaintext:

===============================================
Reading Plain text data files, including XDI
===============================================

Larix can read data from XDI files or from other plain text (ASCII)
data files using a GUI form shown in :numref:`fig_larix_dataimport`. This data
importer window will help you build XAFS :math:`\mu(E)` from the various
columns in your data file, and wraps some of the routines described in
Chapter :ref:`data-io_chapter`. With this form, the goal is to construct
:math:`\mu(E)` with the energy array :math:`E` in units of eV.  From this
window you can

 * visually inspect the resulting plot
 * inspect the text of the data file
 * specify whether the X axis has units of 'eV', 'keV', or 'degrees'
 * for data with X in 'degrees', setting the monochromator `d` spacing will
   allow energy to be calculated.
 * select the appropriate operations and arrays to build  :math:`\mu` ("-log(I1/I0)",
   "I2/IO", etc)
 * select a column or value for uncertainty in :math:`\mu`
 * select operations and arrays to build a reference :math:`\mu` array
 * select columns to add together (say, for multi-channel fluorescence
   data) into a new array.
 * edit the names of the columns that were automatically determined when
   reading the file
 * edit the displayed "file name" (used in the File List on the main Larix window)
 * edit the "group name" - the name of the group in the Larch programming session.


Once you have made selections for how to read in data, these will be
remembered the next time you read in data.  When reading in multiple files,
the array choices will be assumed to be the same for all files.

.. _fig_larix_dataimport:

.. figure:: ../_images/Larix_TextFileImport.png
    :target: ../_images/Larix_TextFileImport.png
    :width: 55%
    :align: center

    Plain text Data file importer.

.. _larix_athena:

=========================================
Reading Data from Athena Project Files
=========================================


XAS :math:`\mu(E)` data can also be read from Athena Project files, as
shown in :numref:`fig_larix_athenaimporter`. Multiple data groups can be selected
and read in.  When reading Athena Project files, many of the processing
parameters saved in the project for each Group will be read and used by Larix.

.. _fig_larix_athenaimporter:

.. figure:: ../_images/Larix_AthenaImporter.png
    :target: ../_images/Larix_AthenaImporter.png
    :width: 60%
    :align: center

    Athena Project importer.

.. _larix_blisshdf5:

===================================
Reading Spec/Bliss HDF5 Data
===================================

HDF5 and ASCII data files from Spec/Bliss format used at ESRF can be read.
These files support multiple "scans", some of which may be XAS scans, and
are typically ordered by the time at which they were collected.

For each scan, the operations and arrays to construct :math:`\mu(E)` can be
selected.  As for all XAS data, the energy is expected to be in eV: for
data with energy units of keV, be sure to specify the energy units!

.. _fig_larix_h5specimporter:

.. figure:: ../_images/Larix_H5SpecImporter.png
    :target: ../_images/Larix_H5SpecImporter.png
    :width: 75%
    :align: center

    Larch Session Importer for HDF5 Spec data files from the Bliss data
    collection at ESRF.

.. _larix_sessionfiles:

====================================
 Larch Session Files and Larix
====================================

Larch Session Files (using the `.larix` extension) save all of the user
data in to a single file that can be loaded at a later. This includes not
only the data as read into the session, but all of the processed arrays,
Journals, and analysis results, including fit histories each Group.  The
Session files are meant to be completely portable across different
computers and versions.  This effectively allows you to save your session
as a "Project" and be able to share it with someone else or come back to it
later, picking up the analysis where you left it.

For Larix, a saved Larch session file will include all of the XAS data
in the groups shown in the "list of Groups" on the left-hand side of the
main window.  It will also include all the interim processing data.  All
the commands issued in the Larch buffer in the existing session will be
saved, and some configuration information (machine type, versions, etc) for
the session are also saved.  See :ref:`larch_session_files` for further
details.

From Larix, you can save a Session file at any time using the File
Menu or "Ctrl-S" ("Apple-S" on macOS).  You can import data from a Session
file either with "Ctrl-R" ("Apple-R" on macOS) to browse and load Session
files, or with a more generic "Ctrl-O" ("Apple-O" on macOS) to load data
from the several known data formats.

When importing data from a saved Session, a Window as show below will allow
you to select which groups to import - you do not have to import every
group.  If there naming conflicts between the data to be imported and the
groups already in the current session, you will be able to specify whether
to overwrite or import with a new name.  Some common "internal working
groups" (notably, the cache of Feff Paths imported) will be *merged*, and
some will be overwritten.  When loading a Session file, you can also view
the configuration of the saved session (including computer name, operating
system, versions), and the command history from that session.  Those will
not be merged into the current session, but can be useful to inspect.

.. _fig_larix_larix1:

.. figure:: ../_images/Larix_SessionImport.png
    :target: ../_images/Larix_SessionImport.png
    :width: 75%
    :align: center

    Larch Session Importer for Larix, showing XAS groups to be read
    into the existing session.

===================================
 Auto-saving Larch Session Files
===================================

Larix will periodically save session files and keep a history of session files.
By default, these are saved every 15 minutes while Larix is running and while
the program is actually in use and data processing is actually happened (an
idle session will not continue to save data).  The most recent 5 of them will
be kept as files named (in order of most recent to oldest) of
`session_autosave.larix`, `session_autosave_1.larix`,
`session_autosave_2.larix`, and so on in the the `larix` folder in your Larch
user directory (typically `C:\Users\<YourName>\larch` on Windows,
`/Users/<YourName>/.larch` on macOS, and `/home/<YourName>/.larch` on Linux).
Several of these settings can be configured as part of the Larix User
Preferences.

When exiting Larix, you will be prompted with information about when
the last Session file was automatically saved, and asked if you want want
to save the Session before exiting.
