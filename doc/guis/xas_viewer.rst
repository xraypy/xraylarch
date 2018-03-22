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


..  _xasviewer_fig:

.. figure:: ../_images/XAS_Viewer_xasnorm.png
    :target: ../_images/XAS_Viewer_xasnorm.png
    :width: 65%
    :align: center

    Main XAFS pre-edge subtraction and normalization form.


The XAS Viewer GUI includes a simple form for basic pre-edge subtraction,
normalization, and de-convolution of XAFS spectra.  It can read data from
plain ASCII data files, using a GUI form to help build :math:`\mu(E)`, as
shown below.

.. subfigstart::

.. _fig_xasviewer_2a:

.. figure:: ../_images/DataImporter.png
    :target: ../_images/DataImporter.png
    :width: 65%
    :align: center

    ASCII data file importer.

.. _fig_xasviewer_2b:

.. figure:: ../_images/AthenaImporter.png
    :target: ../_images/AthenaImporter.png
    :width: 100%
    :align: center

    Athena Project importer.

.. subfigend::
    :width: 0.47
    :alt: data importers
    :label: fig_xasviewer_2

    Data importer for XAS Viewer.

Data read into XAS Viewer can also be exported to Athena Project files, or
to CSV files.


In addition to basic XAFS processing, the XAS Viewer program also ha


.. image:: ../_images/XAS_Viewer_plot_baseline.png
    :target: ../_images/XAS_Viewer_plot_baseline.png
    :width: 65%


also includes an easy-to-use wrapper around `lmfit`_ for flexible
curve-fitting with the ability to constrain fitting Parameters.
