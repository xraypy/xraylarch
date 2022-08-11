# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

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
