===========================================
X-ray Fluorescence Analysis with Larch
===========================================

X-ray Fluorescence Data can be manipulated and displayed with Larch.


.. function:: read_gsemca(filename)

   read a GSECARS MCA spectra file, returning a Group

   :param filename: name of GSECARS MCA file

   The returned Group has the following components:

      =================== ==========================================================
       component name        description
      =================== ==========================================================
       filename            name of file
       mcas                list of MCA objects for each MCA saved in the file
       rois                list of ROIs 
       environ             list of Environmental Variables
       energy              array of energy values
       counts              array of counts, deadtime corrected and summed over MCAs
       raw                 array of counts, summed over MCAs, not corrected.
       calib               dictionary of calibration values
       dt_factor           deadtime correction factor
       real_time           real time for data acquisition
       live_time           live time for data acquisition
       nchans              number of energy points in spectra
       get_roi_counts()    function to get counts for a named ROI
       save_mcafile()      function to save MCA to file
      =================== ==========================================================


.. function:: xrf_plot(energy, counts, mca=None)

   create an interactive window for displaying an X-ray Fluorescence spectra

   :param energy: array of energy values
   :param counts: array of counts
   :param mca:    MCA group (as read from :func:`read_gsemca`), containing
                  ROI definitions, calibration values, and related data.


An example plot is shown below

.. _xrf_fig1:

.. figure::  ../_images/xrf_display1.png
    :target: ../_images/xrf_display1.png
    :width: 75%

    Example XRF Display, showing X-ray Fluorescence spectra, defined ROIs
    (in red), and Periodic Table for showing predicted emission lines.

