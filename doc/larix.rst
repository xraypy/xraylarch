.. include:: _config.rst

.. _larix_app:
.. _xasviewer_app:

Larix (was XAS Viewer)
===========================

The `Larix` Application gives a graphical user interface (GUI) for the
visualization and analysis of X-ray absorption spectroscopy (XAS) data, both
XANES and EXAFS.  A primary goal is to be deliberately patterned after the
Demeter Package (Athena and Artemis programs), and shares many concepts and
presentation ideas with these progrqms.  As a GUI Program, Larix should seem
very "Athena-like" though of course there will be several differences.  We hope
that many of these differences will be "improvements".  By using Larch for all
of its analysis steps, Larix not only provides interactive data visualization,
exploration, and analysis of XAS data, but also records those steps as Larch /
Python commands that can be saved and reproduced outside of the GUI, say to
enable batch processing of large volumes of data.

Larix is still in active development.  New features for Larix have been driving
much of the development and releases of Larch version for the past few
years. At this writing (July, 2024, Larch version 0.9.80), the main goals of
being feature-compatible with Athena and Artemis are basically met, though
improvements and new featutes continue to be made, and bugs are being fixed as
quickly as possible.  Ideas for additions and improvements are most welcome.
If you find problems with it or unexpected or missing functionality, please let
us know.  In addition, if you find any features from Athena, Artemis, Sixpack,
or other analysis programs that you would like to see in Larix, please let us
know.



.. toctree::
   :maxdepth: 2

   larix/overview.rst
   larix/iodata.rst
   larix/dialogs.rst
   larix/preedge.rst
