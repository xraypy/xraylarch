# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [0.9.57 - 2021-12-02]
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
