.. _guis-xas_viewer:


XAS_Viewer
=======================

The XAS_Viewer GUI uses Larch to read and display XAFS spectra.  This is
still in active development, with more features planned with special
emphasis on helping users with XANES analysis.  Current features (as of
March, 2018, Larch version 0.9.36) include:

   * read XAFS spectra from simple data column files.
   * read XAFS spectra from Athena Project files.
   * XAFS pre-edge removal and normalization.
   * visualization of normalization steps.
   * fitting of pre-edge peaks.
   * saving of data to Athena Project files.
   * saving of data to CSV files.


.. _lmfit:    http://lmfit.github.io/lmfit-py


.. image:: ../_images/XYFit_GUI_Fit.png
    :target: ../_images/XYFit_GUI_Fit.png
    :width: 45%
.. image:: ../_images/XYFit_Plot_FitResidual.png
    :target: ../_images/XYFit_Plot_FitResidual.png
    :width: 45%

This GUI also includes an easy-to-use wrapper around `lmfit`_ for flexible
curve-fitting with the ability to constrain fitting Parameters.
