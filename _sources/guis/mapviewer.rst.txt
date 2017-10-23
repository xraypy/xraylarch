.. _guis-mapviewer:

==========================
GSECARS Mapviewr
==========================

.. _wxmplot:  http://newville.github.io/wxmplot
.. _matplotlib: http://matplotlib.org/


The main Larch GUI gives a simple view of a Larch session.


.. image:: ../_images/Mapviewer_3ColorSelect.png
    :target: ../_images/Mapviewer_3ColorSelect.png
    :width: 45%
.. image:: ../_images/Mapviewer_ImageDisplayColormap.png
    :target: ../_images/Mapviewer_ImageDisplayColormap.png
    :width: 45%

The GSECARS Mapviewer is a main GUI for Larch, allowing users to read and
display HDF5 files containing X-ray fluorescence maps from synchrotron
X-ray microprobes. In the main frame (left), the user can select what map
files and what portions of the data set to view.  On the right, is one of
the views of XRF map, shown in a false-color image (using using `wxmplot`_
and `matplotlib`_).  Images are interactive, allowing zooming, changing
color thresholds, and drawing lasso boxes to extract full X-ray
fluorescence spectra, show below.

.. image:: ../_images/XRFDisplay.png
    :target: ../_images/XRFDisplay.png
    :width: 75%

The X-ray fluorescence spectra extracted from a XRF Map.


.. image:: ../_images/Mapviewer_3ColorImageDisplay.png
    :target: ../_images/Mapviewer_3ColorImageDisplay.png
    :width: 45%
.. image:: ../_images/Mapviewer_correlation_maps.png
    :target: ../_images/Mapviewer_correlation_maps.png
    :width: 45%

Other displays of the same XRF Map data.  On the left, 3 different elements are
encoded into Red, Green, and Blue. On the right, an interactive display of
the correlation of two maps is shown.

.. image:: ../_images/Mapviewer_XRD_Display.png
    :target: ../_images/Mapviewer_XRD_Display.png
    :width: 75%

Larch can also handle micro-X-ray Diffraction maps, with a simple view of a
diffraction pattern shown here.


