.. include:: ../_config.rst

.. |pin| image:: ../_images/pin_icon.png
    :width: 18pt
    :height: 18pt

.. _larix_preedge:

Pre-edge subtraction and Normalization
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

As shown above in :numref:`fig_larix_top`, the main analysis panel for
the Larix program is the "XAS Normalization" Panel.  This panel helps
you do pre-edge subtraction and normalization of XAFS data using the
:func:`find_e0`, :func:`pre_edge`, or :func:`mback_norm` functions.  This
processing step is important for getting normalized XAFS spectra that is
used for further analysis of both XANES and EXAFS.  In general, the idea is
to get the main step of each XAS spectrum to go from 0 below the main edge
to 1 above the edge, so that the normalized spectrum represents the average
absorption of each absorbing element in the sample.

The first step in the process is to identify :math:`E_0`, the absorption
threshold energy.  This is typically (and by default) chosen as the energy
point where the first derivative :math:`d\mu(E)/dE` has a maximum.  This
may not necessarily reflect the onset of absorption or the Fermi level, but
it is easy to identify reliably for any spectrum.  At this point, the value
does not have to be highly accurate, so that predictability and
reproducibility are favored.  You can set the value of :math:`E_0` or allow
it to be determined automatically.


The next step is to measure how large the jump in absorption is. This
process can be somewhat trickier, so that there are some heuristics built
in to Larix (and :func:`pre_edge`) to help make this more robust.
You can explicitly set the the value of the edge step, or allow it to be
calculated from the spectra in one of two ways.

The classic way for determining the edge step is encapsulated in the
:func:`pre_edge` function.  Default values for ranges for the fitted
pre-edge line and post-edge normalization curve can be set, or you can rely
on the default settings for these values.  In general, the default settings
give pretty good results, but the value for the edge step or the fitting
ranges and curve forms can be altered here.

Consult with :func:`pre_edge` and :func:`mback_norm` function for more
details on these parameters.  Note that you can copy processing parameters
from one group to other groups with the set of "copy" buttons that will
copy the corresponding parameters to all the selected groups.

Finally, from the normalization panel, you can plot the data for the one
currently selected group or for all selected groups in a few different
ways: Raw :math:`\mu(E)`, normalized :math:`\mu(E)`, the derivative
:math:`d\mu(E)/dE`, flattened :math:`\mu(E)`.  For the current group there
are even mor options, including the raw :math:`\mu(E)` with the pre-edge
line and post-edge normalization curve, or compare with the
MBACK-calculation for normalization.


.. _larix_dialogs:

Common XAS Processing Dialogs
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

When importing and normalizing XAS data, it is sometimes necessary to make some
corrections of manipulate the data in a few well-defined ways.  These
can include:

  * copying, removing, and renaming data groups.
  * merging of data groups -- summing similar or repeated spectra.
  * de-glitching spectra.
  * recalibrating or aligning spectra.
  * smoothing of noisy spectra.
  * re-binning of spectra onto a "normal" XAFS energy grid.
  * de-convolving spectra.
  * correcting over-absorption in fluorescence XANES spectra.

There are several dialogs available in Larix, each designed to guide
through the steps needs for these corrections or manipulations.  Each of
these is described in more detail below.

.. _larix_energy_calib:

===============================================
Energy Calibration and alignment
===============================================

Each XAS spectra Group has

.. _fig_larix_dialog_cal:

.. figure:: ../_images/Larix_calibrate_dialog.png
    :target: ../_images/Larix_calibrate_dialog.png
    :width: 50%
    :align: center

    Energy calibration dialog.


.. _larix_deglitch:

===============================================
Deglitching and Truncating Data
===============================================

.. _fig_larix_dialog_deglitch:

.. figure:: ../_images/Larix_deglitch_dialog.png
    :target: ../_images/Larix_deglitch_dialog.png
    :width: 50%
    :align: center

    De-glitching dialog

.. _larix_smooth:

===============================================
Smoothing Data
===============================================


.. _fig_larix_dialog_smooth:

.. figure:: ../_images/Larix_smooth_dialog.png
    :target: ../_images/Larix_smooth_dialog.png
    :width: 50%
    :align: center

    Energy smoothing dialog.


.. _larix_deconv:

===============================================
De-convolving XAS  Data
===============================================

.. _fig_larix_dialog_deconv:

.. figure:: ../_images/Larix_deconvolve_dialog.png
    :target: ../_images/Larix_deconvolve_dialog.png
    :width: 50%
    :align: center

    Deconvolution dialog.


.. _larix_rebin:

===============================================
Re-binning XAS  Data
===============================================


.. _fig_larix_dialog_rebin:

.. figure:: ../_images/Larix_rebin_dialog.png
    :target: ../_images/Larix_rebin_dialog.png
    :width: 50%
    :align: center

    Energy re-binning dialog.



.. _larix_overabsorb:

===============================================
Correcting for Over-Absorption in XAS Data
===============================================

.. _fig_larix_dialog_overabs:

.. figure:: ../_images/Larix_overabsorption_dialog.png
    :target: ../_images/Larix_overabsorption_dialog.png
    :width: 50%
    :align: center

    Over-absorption correction dialog
