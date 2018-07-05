====================================================================================================
XANES Analysis:  Linear Combination Analysis,  Principal Component Analysis, Pre-edge Peak Fitting
====================================================================================================

.. module:: _xafs
   :synopsis: XANES Linear Combination Analysis


XANES is extremely sensitive to oxidation state and coordination
environment of the absorbing atom, and spectral features can often be used
to qualitatively identify these characteristics.  On the other hand, the
physical origin of the spectal features are complicated enough that direct
and complete quantitative analysis is difficult.  As a result, "XANES
Analysis" of a spectrum typically involves making linear combinations of
spectra from known compounds or fitting the spectral features and
correlating trends in their positions and intensities to known changes in
spectral features with the desired characteristic such as oxidation state.
This approach to spectroscopy can be incredibly accurate and sensitive but
ultimately relies on comparisons to spectra of known materials.  In all
cases, XANES analysis uses *normalized* XAFS spectra, as done with either
the :func:`pre_edge` or :func:`mback` function.


Within the context of Larch, there are two basic approaches to analyzing
XANES spectra: fitting of so-called pre-edge peaks that are (generally) due
to hybridization of :math:`d` electron bands of a transition metal with
oxygen :math:`p` electrons.  These peaks are at energies just below the
main (:math:`4p` for first row transition metals) edge.


As it turns out, all three of these approaches are exposed in the
XAS Viewer application described in Chapter :ref:`guis-xas_viewer`.


urrently, this form is described in Chapter :ref:`data-io_chapter`.

Pre-edge Peak fitting
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Pre-edge peaks can often be modeled as a simple sum of mathematical
functions such as :func:`gaussian`, :func:`lorentzian`, or :func:`voigt`.
Typically, no more than 4 functions are needed to model most pre-edge
peaks,

It isThese



Linear Combination Analysis
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Principal Component Analysis
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
