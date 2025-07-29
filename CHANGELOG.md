# Changelog

Notable changes to this project should be documented in this file.
The GitHub Release Notes will also be useful

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [2025.2.1 - 2025-07-29]

### Larix improvements and bugfixes:
 -  allow adding feff paths without data
 -  cleanups for XAS auto-normalization, and avoiding overprocessing
 -  revert to using read_gsexdi for 'epics stepscan' data, cleanups
 -  exafs_panel: avoid reproccessing all groups with form
    values/setting for current group.
 -  move data processing tasks to separate module, and to use the file
    list from main window
 -  add register/run callbacks from controller for when the Larix
    Groupname changes -- used for data proceesing tasks
 -  fix bad_channels when reading in multi-element detector data
 -  editing plot preferences will push to current plot displays
 -  exafs_panel: better separation of plotting and processing parameters
 -  exafs_panel: better isolation of group processing parameters, and
    copy of parameters.
 -  lincombo: fix fits in k-space (thanks AJ Kropf), and LCF can now
    use chi*k**3
 -  lincombo: add popup warning when asking to fit data in k-space
    when chi(k) is not yet available
 -  feffit: add csv_path_report() method to FeffitDataset, use
    tabulate if installed.


## xraylarch library:
 - fix a bug in mback_norm method (tj-eldridge <thomas.eldridge@esrf.frr)
 - tolerate very short pre-edge and normalization ranges, reducing
   npre and nnorm if necessary
 - increase max size of column file
 - more uniform use of numpy asmatrix
 - general cleanups, force group to have a __name__ attribute
 - fix support older sessions/projects
 - fix error with polyfit and very short post-edge regions
 - fix Rixs bm16 update (Mauro Rovezzi <mauro.rovezzi@esrf.fr>)
 - better close for SQLite databases.
 - fix correlated Debye model: force path coords to float
 - xafsplots:  add scale_window to plot_chir()
 - add dict_report method to FeffPath to return plain dict of values

### Other GUIs:
 - XRF Map: read dtfactor directly from HDF5 if available, otherwise
   try to compute it.
 - XRF Map: even more straightforward Read Master
 - XRF Map: remove use of scandb in read_xrm master file, skip empty rows
 - XRF Map: dont trim sinograms on XRD data
 - Larch GUI: make sure larch buffer starts showing end of output text

### General development and maintenance:
 - add issue templates
 - add darkdetect to dependcies, update constructor script
 - make sure darkdetect dependency installs with plain pip install
 - update MANIFEST, using pyproject.toml, remove setup.cfg
 - update readme, change format
 - add function and `larch -n` CLI option to install nightly build.
 - add bash scripts to run tests with more care for temporary resources.


## [2025.2.0 - 2025-05-25]

### Larix improvements and bugfixes:

 - many improvements to importing and showing XY data
 - add initial working Curve Fitting Panel for XY and XAS data.
 - add "XAS MODE" when reading XAS data, including 'calculation'
 - better reading of FEFF/FDMNES calculated XAS spectra, use "mode=calculation" when reading these files.
 - re-arrange Plotting choices for XAS Normalization Panel
 - re-arrange Plotting choices for EXAFS  Panel
 - allow "Plot relative to E0" - either Group's E0 or elements nominal E0 in XAS Normalization Panel
 - allow "Plot-on-Choose Group" to be optional in XAS Normalization and EXAFS Panel
 - add colored console logger
 - add Constat+StepModel (arctan/error function) to pre-edge peak baselines, some related tweaks
 - tweak colors and how pre-edge baselines are plotted
 - fix exporting feffit results in filtered chi(k)
 - add plot theme of '<Auto>' to use system dark/light mode
 - add stderr columns to linear combination output files
 - save element/edge on selection, save in group config
 - fix identifying reference groups from Athena Project files.
 - better use of functions from xafsplots -- more reproducible plots.
 - better consistency of Panel form data and Group's config -- auto-saving when a Panel is hidden and re-exposed.
 - better saving og element/edge in XAS Normalization Panel
 - allow showing EK0 on EXAFS Panel
 - import and expand fit models from lmfit, defining step/rectangle functions by form (linear, atan, erf, ..)
 - show tracebacks but fail gracefully when trying to import broken analysis panels
 - make sure ynorm is defined before trying to plot in XY Data panel
 - setting Displayed Panels is now under Edit Preferences, and choices can be saved for future sessions.
 - fix setting energy range for linear Combo plots
 - when importing session, make sure the datatype-appropriate panel is shown
 - more consistent font weights, using Bold for all "results tables".

### Other GUIs:

 - XRF Map: fix adding highlighted areas, saving points
 - XRF Map: do not rescale tomo reconstruction with mean value
 - XRF Display/Control: add ROI countrates for each detector
 - XRF Display/Control: add color warnings for ROI, OCR, deadtime
 - XRF Display/Control: make sure to read xrf calibration if needed

### xraylarch library:

 - fix typos in rebin
 - more error-checking for pre-edge details
 - force polyfit to always return a list of coefficients
 - add step models to pre_edge prepeaks models
 - return smoothing default method back to "boxcar"
 - use read_ascii for epics scanfiles
 - many improvements to `xafsplots` functions
 - refactor xyz2struct: Use vectorized np.max for coordinate calculation
 - better error checking for encoding ndarrays
 - xafs/autobk.py: reduce impact of spline clamps by a factor of 10
 - xafs/pre_edge.py: add 'iscalc' option to set tiny pre-edge range, and pre_edge=constant for calculated XAS.
 - fix autorange for plot_bkg() with multiple traces

### General development and maintenance:

 - refactoring and cleanup of some tests
 - update numpy.testing usage
 - remove support of pymca from deglitch
 - remove pandas dependencies
 - using scipy-based spike removal in place of numpy and pandas
 - more usage of pathlib where possible for Path names and removing files
 - better use of GitHub Actions on Pull Requests
 - improve tests to allow DISPLAY for some preliminary GUI testing
 - add darkdetect dependency, working toward better support for DARK v LIGHT mode
 - allow numpy>2 and Python 3.13, using Python 3.13 by default.
 - update license and pointers to license


## [2025.1.1 - 2025-01-12]

### Fixes

 - bugfix for generating and running Feff for XAFS calculations -- fixed PRINT flag
 - more error checking in find_e0 for coercing to numpy arrays.
 - add spline interpolation option for XAFS re-binning
 - updated the binary Installers and GetLarch Installation scripts to use the latest conda/mamba packages.
 - some doc updates

## [0.9.66 - not released]

### Added

  - XAS_Viewer/CSV export: add EXAFS arrays and the possiblity to save individual files (#393)
  - examples/Jupyter: notebook showing a simple reading and visualization of RIXS data
  - `larch.io.rixs_esrf_id26` to read RIXS data from ESRF/ID26 beamline (old Spec format)
  - `larch.plot.plot_rixsdata` to visualize RIXS planes and cuts in pure Matplotlib

### Changed

  - improved `larch.io.rixsdata.RixsData` for taking line cuts and crop the RIXS plane

### Fixed

## [0.9.65 - 2022-07-05]

### Changed

- LCF: eliminate combinations with very low weight (#387)
- XAS Viewer:  Add "Clear Session" menu item

### Fixed

- XAS_Viewer/normalization: fix Y offset (#389)
- XAS_Viewer/normalization: avoid plotting errors for "Plot Selected" with >100 Spectra selected.
- XAS_Viewer/exafs: Make sure that E0 and Rbkg are correctly copied to other group
- XAS_Viewer/exafs: "copy to selected" now forces re-processing of selected groups.
- XAS_VIewer/session file: Importing of only selected groups from Session file now works properly.
- XAS_VIewer/session file: better merging of top-level data, especially feff cache on import.
- XAS_Viewer/Linux: better checks to avoid initialiing wx objects with 0 size.
- better docstrings for some data/io functions, starting to use `autodoc` in docs.
- doc: fix Angstrom rendering in HTML
- doc: work toward better XAS Viewer doc.



## [0.9.64 - 2022-06-22]

### Fixed

- Fix launching of gse_mapviewer (#386)

## [0.9.63 - 2022-06-21]

### Fixed

- Many bug fixes and improvements (#383, #382, #381, #379, #357, plus others)

## [0.9.62 - 2022-06-08]

### Fixed

  - XAS_Viewer: Feff-fitting paths (and so also parameters) are refreshed for
    each fit (#377, #374)
  - XAS_Viewer: most main windows are now resizable (#372)
  - Better checking and auto-pip-installing of wxutls and wxmplot (#376)

## [0.9.61 - 2022-05-26]

### Added

  - XAS Viewer: Entries for the fit histories of pre-edge peak fitting and Feff
    fitting can now be erased.

### Fixed

  - XAS Viewer: the merging of groups now works ;).
  - XAS Viewer: setting and energy shift for a group will copy that shift to
    other groups with the same energy reference. There is a preference setting
    to turn off this automated copying of energy shifts.
  - XAS Viewer: fixed very slow plotting -- now just back to normal "not fast".
  - XAS Viewer: dialogs have generally better sizes.
  - XAS Viewer: fixes for plotting of Pre-edge peak fits.
  - XAS Viewer: improvements in Journal entries for some processed groups.
  - XAS Viewer: fixes for combining default and per-group configuration.

## [0.9.60 - 2022-05-23]

### Added

  - each Group of XAFS data will have a Journal - a list of entries with (label,
    value, timestamp) that will be used to record processing steps. The XAFS
    processing functions will write the parameters they were called with to this
    Journal. Users can add notes as Journal entries too.

  - XAS Viewer allows editing of program-wide Preferences, that set the default
    values and settings for the various analysis steps and program behavior.

  - In many windows showing analysis results, XAS Viewer supports setting the
    plot window number (1 through 9) so that more than one or two plot windows
    can be shown at a time.

  - Session-wide Project files (.larix extension) can now be saved and reloaded.
    These files contain essentially all the arrays for each Group of data,
    including Journals, processing results, and fit histories. The "processing
    workspaces" for pre-edge peak fitting, PCA, Linear Combinations,
    Regressions, and Feff fitting. These Session files can be saved/loaded by
    plain Python commands. When loading these into XAS Viewer, the fit histories
    and workspaces will be available. To allow better debugging and tracking of
    provenance, these Session Files include "configuration" data about the
    Session (python, larch version, etc) and a complete set of Larch commands
    for the session, though session commands are not "restored". The files are
    compressed and use a customized JSON encoding.

  - These Session files are now auto-saved by XAS Viewer periodically (every 15
    minutes of activity, by default, and rotated so that a small number (3, by
    default) of the most recent auto-saved files are kept. On startup, "restore
    the last session" is available (Ctrl-I).

### Fixed

  - XAS Viewer PCA fixed.
  - XAS Viewer now displays how each Group was created, for example
    "-log(i1/i0)".
  - XAS Viewer panels have more uniform energy range settings, relative to E0,
    per group.
  - XAS Viewer has more consistent coloring and font sizes.
  - XAS Viewer Quit dialog now lists the last saved Session file.
  - XAS Viewer now works even harder to keep _xasgroups correct.
  - pycifrw added as a dependency from conda-forge
  - copying parameters from one group to another is much improved.
  - rebinning of EXAFS data better avoids duplicate energies.
  - a few bugs with the handling of some CIFs were improved
  - Feff calculations now default to L3 edge for Z>= 60.
  - Python 3.10 is better supported, Python 3.7 seems to still work.

## [0.9.59 - 2022-04-01]

[Release announcement]()

### Added
 - Reading files from [FDMNES](http://fdmnes.neel.cnrs.fr/).
 - XAS Viewer allows reading in a reference spectrum from the same file as a spectrum.
 - XAS_Viewer better supports each spectrum having an "energy reference spectrum". This
    can be set on reading spectra, or afterwards.  Recalibratng energies can propogate
    calibrations to spectra that share a reference.
 - XAS Viewer better supports an "energy shift" for each spectrum -- this can be copied
    to other spectra or "undone" to go back to the original  (as read-in) data.
 - XAS Viewer: data can be deglitched while plotting in "k" space"
 - XAS Viewer: "flattened" spectra can be used for linear analysis in more places.
 - Example using Jupyter and Fe pre-edge peaks.

### Changed
 - XAS Viewer: the action of the "pin icon" for selecting points from a plot has now changed.
    Previously hitting the pin icon meant "use most recently clicked point on plot".  Now,
    hitting the pin icon starts a timer which will look for mouse clicks *after* hitting
    the pin icon:
       a) if there are new mouse clicks on the plot, wait at least 3 seconds, and return
          the most recent position.
       b) if there are no mouse clicks after 15 seconds, return the most recent position
           (even before clicking on the pin)


### Fixed
 - Reading columns names from one line header, and for files that announce as XDI but
    break XDI specs (say, by having >128 columns).
 - Better handling of CIFs with partial occupancy when generating feff.inp.
 - NLEG is set to 6 by default when generating feff.inp.
 - By default, hydrogen atoms are removed when generating feff.inp (XAS Viewer and cif2feff)
 - Athena project files with very long journals are better supported.
 - Some permission problems for installation of Applicatons on MacOS have been avoided.
 - "get current working directory" is now tested uniformly for permission errors.
 - MapViewer: more robust and flexible search for tomographic rotation axis.
 - Fix for spec/HDF5 files with broken "scan" link.
 - XRF Display spectral fiitting: faster, better guesss for parameter scales, and show
    filled eigenvectors (wxmplot 0.9.49)
 - MapViewer / XRF Display: much improved ADD ROIs, including pushing XRF ROIs added in
    XRF Display back to the list in Mapviewer.
 - MapViewer: The order of ROIs added is now preserved, including for work arrays and
    Abundances from XRF analysis.


### Removed
 - Plugins are now completely removed
 - 32-bit  Windows is no longer supported: libraries and executables have been removed.
 - Cromer-Libermann is more deprecated and hidden (but not completely gone, yet)

## [0.9.58 - 2022-01-16]

[Release announcement](https://millenia.cars.aps.anl.gov/pipermail/ifeffit/2022-January/010373.html)

### Added
 - [xas_viewer] add '-' operator in file reader

### Fixed
 - bug in `larch.io.specfile_reader` with the upgrade to `silx==1.0.0` ([#332](https://github.com/xraypy/xraylarch/issues/332))
 - bug with loading deprecated `numpy` functions ([#335](https://github.com/xraypy/xraylarch/issues/335))
 - installation instructions in documentation ([#333](https://github.com/xraypy/xraylarch/issues/333))

### Removed
 - deprecated plugins mechanism

## [0.9.57 - 2021-12-02]

[Release announcement](https://millenia.cars.aps.anl.gov/pipermail/ifeffit/2021-December/010345.html)

### Added
 - Read RIXS files from BM16 at ESRF.
 - Option `--devel` in `GetLarch.sh` to install from source.
 - xas_viewer
   - `File->Save as`

### Changed
 - Module `rixsdata` moved from `larch.qtrixs` to `larch.io`
 - Force UTF8 encoding in `read_ascii`
 - xas_viewer
   - `File->Save` overwrites by default.
   - Better deglitching dialog, including viewing data as chi(E).
   - Loading a Peak Model is now allowed at any time.
   - Default Project filenames are taken from timestamp.

### Fixed
  - Problem with yaml load in `GetLarch.sh`
  - Problem in interpolation with nearly repeated x values
  - Messages reporting progress when processing XRF Maps
  - Reading Athena Project files with non-ASCII characters


## [0.9.56 - 2021-10-20]
[Release announcement](https://millenia.cars.aps.anl.gov/pipermail/ifeffit/2021-October/010319.html)

## [0.9.55 - 2021-07-19]
[Release announcement](https://millenia.cars.aps.anl.gov/pipermail/ifeffit/2021-July/010261.html)

### Fixed
 - Larch's GUI applications on non-US Windows 10 machines.
 - There was a serious bug (possibly since Larch 0.9.52) for using wxPython applications with Python>=3.8 and wxPython>=4.1.0.
 - Fixes for turning CIF structures into Feff inputs and running Feff:
    - more external CIF files from Crystallography Open Database and Materials Project can be converted to Feff.inp.
    - external Feff.inp files can be loaded and run.
    - the name of the folder created for any Feff calculation can be renamed before running Feff.
 - Fixed a bug on the EXAFS / background subtraction panel on "copied groups" to ensure that processing parameters (kweight, rbkg, etc) are kept separate.

### Changed
 - the plot selection choice in the XAS normalization panel for "one group" and "selected groups" are no longer reset each time a data set is selected.

### Added
 - A reference spectrum can now be set for any XAFS spectrum.
 - For linear combination fitting, a single energy shift can be varied during the fit, shifting the unknown data to match the combination of a (presumably aligned) set of standards.
 - For pre-edge peak fitting and Feff Path fitting, entries in the "fit history" can have user-specified labels which can be more meaningful than the default "Fit #1", "Fit #2", etc.
 - testing is now done only with Github Actions, not with the appveyor service.

## [0.9.53 - 2021-07-02]
[Release message](https://millenia.cars.aps.anl.gov/pipermail/ifeffit/2021-July/010251.html)

### Fixed
- XAS viewer
  - fixed various bugs in Spec/BLISS files importer -- silx version 0.15.2 is now required.
  - "GetLarch.sh" and "GetLarch.bat" scripts now use "miniforge", should provide faster downloads and installs.
  - fixed (hopefully) random Text controls events on startup on Windows.
  - several small improvement feffpath and feffit functions for better  managing Path Parameters with lmfit

### Added
- XAS viewer
  - Add GUI Browser for CIF Files from American Mineralogist Crystal Structure Database
  - Code for converting CIF files to feff6/8 input files, GUI form to run Feff, organize results in users .larch/feff folder
  - Feff Path Browser for import Feff.dat files from .larch/feff
  - Feffit Tab added to XAS Viewer for (1 data set) Feff Fitting, with history  of fits, saving of fit script.
  - EXAFS Panel can show chi(q) data.

## [0.9.52 - 2021-06-13]
### Added
- XAS viewer
  - support for ESRF BLISS HDF5 files

## [0.9.51 - 2021-04-22]
### Fixed
- XAS viewer
  - Parameters saved in an Athena Project File are now correctly saved and read
    into XAS Viewer (thanks Tyler Valentine!)

### Added
- XAS viewer
  - "Apply to all marked groups" feature for pre-edge peak fitting.
  - import multiple scans from a Spec file.
- There are binary installers for Windows, MacOSX, and Linux.
- "GetLarch.sh" and "GetLarch.bat" scripts.
