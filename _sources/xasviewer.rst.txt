.. include:: _config.rst

.. _xasviewer_app:

XASViewer
=======================

The XAS Viewer Application gives a graphical user interface (GUI) for the
visualization and analyis of X-ray absorption spectroscopy (XAS) data, both
XANES and EXAFS. It is deliberately patterned after the Demeter Package
(Athena and Artemis programs), and shares many concepts and presentation
ideas from this package.  As a GUI Program, XAS Viewer should seem very
"Athena-like" though of course with many differences.   We hope that many of
these differences will be "improvements".

By using Larch for all of its analysis steps, XAS Viewer not only provides
interactive data visualization, exploration, and analysis, but records
those steps as Larch / Python commands that can be saved and reproduced
outside of the GUI, say to enable batch processing of large volumes of
data. This application is still in active development, with new features
driving the development and release of Larch version for the past year or
more.

At this writing (July, 2022, Larch version 0.9.65), the main feature goals
of XAS Viewer are met, though improvements continue to be made, and bugs
are being fixed as quickly as possible. Ideas for additions and
improvements are most welcome.

.. toctree::
   :maxdepth: 2

   xasviewer/overview.rst
   xasviewer/iodata.rst
   xasviewer/dialogs.rst
   xasviewer/preedge.rst
