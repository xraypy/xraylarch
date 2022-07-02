.. _xasviewer_sessionfiles:

====================================
 Larch Session Files and XAS Viewer
====================================

Larch Session Files (using the `.larix` extension) save all of the user
data in to a single file that can be loaded later. This includes not only
the data as read into the session, but all of the processed arrays,
Journals, and analysis results, including fit histories each Group.  This
effectively allows you to save your session as a "Project" and be able to
share it with someone else or come back to it later, picking up the
analysis where you left it. The Session files are meant to be completely
portable across different computers and versions.

For XAS Viewer, a saved Larch session file will include all of the XAS data
in the data Groups.  It will also include all the interim processing data.
All the commands issued in the Larch buffer in the existing session will be
saved, and some configuration information (machine type, versions, etc) for
the session are also saved.

Larch Session file is a simple gzipped set of plain text.  JSON is to use
to serialize all of the data, including complex data structures.  While all
the data are stored using portable formats and well-supported libraries, it
would not necessarily be easy to open and use these files without the
Python code in Larch to read these files.


From XAS Viewer, you can save a Session file at any time using the File
Menu or "Ctrl-S" ("Apple-S" on macOS).  You can import an



The files themselves

.. _fig_xasviewer_larix1:

.. figure:: _images/XASViewer_Main.png
    :target: _images/XASViewer_Main.png
    :width: 75%
    :align: center

    XASViewer showing the File/Group list on the left-hand side and the
    the XAFS pre-edge subtraction and normalization panel on the right.

The right-hand portion of the XAS Viewer window shows multiple forms for
more specialized XAFS data processing tasks, each on a separate Notebook

=================================
 Auto-saving Larch Session Files
=================================
