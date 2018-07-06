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
XANES spectra.  The first of these involves fitting of the so-called
pre-edge peaks that are (generally) due to hybridization of :math:`d`
electron bands of a transition metal with oxygen :math:`p` electrons.
These peaks are at energies just below the main (:math:`4p` for first row
transition metals) edge.  They are typically split into several distinct
multiplet energies corresponding to molecular orbitals of the hybridized
metal :math:`3d` (for firs-row transition metals) and (typically) oxygen
:math:`2p` orbitals.  These features are quite robustly correlated with
electronic and local atomic structure of the metal and its ligands, and
quite a rich literature makes use of such **pre-edge peak fitting** in a
variety of fields.  As the energy resolution of XANES measurement continues
to improve, thes pre-edge peaks become clearer and a richer resource for
spectral analysis.

The second general approach to XANES analysis is to treat experimental
XANES spectra as a linear mixture of the XANES spectra of idealized
components.  This works on the assumption that the XANES signature of a
collection of atoms is the linear sum of the XANES from individual
components, which is valid in all but the most extreme conditions. In this
sense **Linear Combination Analysis** is a very useful approach to XANES
analysis, and generally quite easy to do.  If done carefully, it can also
quite robust, though its sensitiviy can be somewhat limited.


What is not always clear in Linear Combination Analysis is what the proper
"standard" components should be, or even how many can be determined from a
collection of data.  In this sense standard spectroscopic methods such as
**Principal Component Analysis** (or PCA) and other linear-algebra based
analysis tools (which are nowadays often included in "Machine Learning"
methods) can be useful.  Strictly speaking, PCA is very limited in what it
can really tell you about a set of spectra -- it helps you identify how
many unique components make up a collection of spectra, and can help answer
if another spectrum is also explained well by those principal components,
and so "fits in" with the starting collecion of data.  This is admittedly
limited knowledge, but can be very useful in enabling further analysis.

These three of these approaches are exposed in the XAS Viewer application
described in Chapter :ref:`guis-xas_viewer`, and the documentation here
largely reflects the operations done there.

But first a note for all XANES analysis.  All these methods rely on
comparing the spectral intensities normalized to the main absorption edge.
Thus, in order to get accurate quantitative results, the spectra analyzed
need to be well-normalized. More importantly, they need to be consistently
normalized.  In addition, sample preparation and measurement issues such as
pinhole effects, over-absorption and detector saturation or deadtime can
systematically alter the XANES spectra.  None of the analytic methods
described here for XANES analysis can independently identify when spectra
are not properly normalized or when artifacts that suppress the spectral
features have occured.  It is up to the experimentalist and analyst to make
these decisions.


Pre-edge Peak fitting
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Pre-edge peaks can often be modeled as a simple sum of mathematical
functions such as :func:`gaussian`, :func:`lorentzian`, or :func:`voigt`.
Typically, no more than 4 functions are needed to model most pre-edge
peaks.  Still, it is not always so simple to identify several aspects of
pre-edge peak fitting.  These challenges include

 * identifying and removing the background due to the main absorption
   edge.
 * identifying the proper shape of the peaks.
 * making sure that the peaks overlap but do not exchange or become
   coincident.

The XAS Viewer application helps with many of the tasks, and it is highly
recommended that you start with this GUI.

Linear Combination Analysis
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Many XANES spectra are made on messy, heterogeneous systems or in
engineered samples in which a predictable if not completely understood
reaction is occuring.  In these cases and many related problems, using
linear combinations of spectra from known compounds to understand the
makeup of the unknown sample is an important analysis method.

.. module:: _math

..  function:: lincombo_fit(group, components, weights=None, minvals=None, maxvals=None, arrayname='norm', xmin=-np.inf, xmax=np.inf, sum_to_one=True)

    perform linear combination fitting for a group

    :param  group:       Group to be fitted
    :param  components:  List of groups to use as components (see Note 1)
    :param  weights:     array of starting  weights (see Note)
    :param  minvals:     array of min weights (or None to mean -inf)
    :param  maxvals:     array of max weights (or None to mean +inf)
    :param  arrayname:   string of array name to be fit  ['norm'] (see Note 2)
    :param  xmin:        x-value for start of fit range [-inf]
    :param  xmax:        x-value for end of fit range [+inf]
    :param  sum_to_one:  bool, whether to force weights to sum to 1.0 [True]

    :returns:  group with resulting weights and fit statistics

    Notes:

     1.  The names of Group members for the components must match those of the
         group to be fitted.
     2.  use ``None`` to use basic linear alg solution)
     3.  arrayname can be one of  `norm` or `dmude`


..  function:: lincombo_fitall(group, components, weights=None, minvals=None, maxvals=None, arrayname='norm', xmin=-np.inf, xmax=np.inf, sum_to_one=True)


    perform linear combination fittings for a group with all combinations
    of 2 or more of the components given

    :param  group: Group to be fitted
    :param  components: List of groups to use as components (see Note)
    :param  weights: array of starting  weights (see Note)
    :param  minvals: array of min weights (or None to mean -inf)
    :param  maxvals: array of max weights (or None to mean +inf)
    :param  arrayname: string of array name to be fit (see Note 2)
    :param  xmin: x-value for start of fit range [-inf]
    :param  xmax: x-value for end of fit range [+inf]
    :param  sum_to_one: bool, whether to force weights to sum to 1.0 [True]

    :return: list of groups with resulting weights and fit statistics,
     ordered by reduced chi-square (best first)

    See notes for :func:`lincombo_fit`.


Principal Component Analysis
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

..  function:: pca_train(groups, arrayname='norm', xmin=-np.inf, xmax=np.inf, sum_to_one=True)

    use a list of data groups to train a Principal Component Analysis model

    :param  groups:      list of groups to use as components
    :param  arrayname:   string of array name to be fit (see Note) ['norm']
    :param  xmin:        x-value for start of fit range [-inf]
    :param  xmax:        x-value for end of fit range [+inf]

    :return: group with trained PCA model, to be used with :func:`pca_fit`

     1.  The group members for the components must match each other
         in data content and array names.
     2.  arrayname can be one of  `norm` or `dmude`


.. function:: pca_fit(group, pca_model, ncomps=None, _larch=None)

    fit a spectrum from a group to a pca training model from pca_train()

    :param  group:       group with data to fit
    :param  pca_model:   PCA model as found from :func:`pca_train`
    :param  ncomps:      number of components to included

    :return: `None`.


    On success, the input group will have a subgroup name `pca_result`
    created with the following members:

          ============ ==================================================
           name             meaning
          ============ ==================================================
	  x              x or energy value from model
          ydat           input data interpolated onto `x`
          yfit           linear least-squares fit using model components
          weights        weights for PCA components
          chi_square     goodness-of-fit measure
          pca_model      the input PCA model
          ============ ==================================================
