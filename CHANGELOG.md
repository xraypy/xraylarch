# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [0.9.53 - 2021-07-02]


## Fixed

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

### Changed


### Removed

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

