.. _guis-chapter:

=====================
Larch GUIs
=====================

.. _wxmplot:  http://newville.github.io/wxmplot
.. _matplotlib: http://matplotlib.org/
.. _lmfit:    http://lmfit.github.io/lmfit-py


.. module:: guis
   :synopsis: Graphical User Interfaces


Larch provides several Graphical User Interfaces for easier manipulating,
viewing, and processing of data.  Many of the GUI displays are
inter-related, so that they can bring up the other windows for displaying,
interacting, and processing data.  The main window views are

  * `larch_gui`: simple command-line + data browser for Larch.
  * `GSE_Mapviewer`: viewing XRF maps from  X-ray microprobes.
  * `XYFit`: read and view data from generic 1D datasets, with special support for XAFS spectra, and including peak fitting with `lmfit`_.

More details and screenshots are shown in the following pages.

.. toctree::
   :maxdepth: 2
 
   larch_gui
   mapviewer
   xyfit
