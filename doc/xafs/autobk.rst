==============================================
XAFS: Post-edge Background Subtraction
==============================================

.. module:: _xafs
   :synopsis: XAFS Pre-edge subtraction and normalization functions

..  function:: autobk(energy, mu, group=None, rbkg=1.0, ...)

    Determine the post-edge background function, :math:`\mu_0(E)`, and
    corresponding :math:`\chi(k)`.

    :param energy:  1-d array of x-ray energies, in eV
    :param mu:      1-d array of :math:`\mu(E)`
    :param group:   output group
    :param rbkg:    distance (in :math:`\rm\AA`) for :math:`\chi(R)` above
                     which the signal is ignored. Default = 1.
    :param e0:      edge energy, in eV. If `None`, it will be determined.
    :param edge_step:    edge step.  If `None`, it will be determined here.
    :param nknots:   number of knots in spline.  If `None`, it will be determined.
    :param kmin:     minimum :math:`k` value   [0]
    :param kmax:     maximum :math:`k` value   [full data range].
    :param kweight:  :math:`k` weight for FFT.  [1]
    :param dk:       FFT window window parameter.  [0]
    :param win:      FFT window function name.     ['hanning']
    :param k_std:    optional :math:`k` array for standard :math:`chi(k)`.
    :param chi_std:  optional :math:`\chi` array for standard :math:`chi(k)`.
    :param nfft:     array size to use for FFT [2048]
    :param kstep:    :math:`k` step size to use for FFT [0.05]
    :param pre_edge_kws:  keyword arguments to pass to :func:`pre_edge`.

The background subtraction method used is the **AUTOBK** algorithm, in
which a spline function is matched to the low-*R* components of the
resulting :math:`\chi(k)`.

For reference, :math:`k = \sqrt{2m_e (E-E_0)/\hbar^2}` is the wavenumber of
the ejected photo-electron, where :math:`E_0` is the absorption threshold
energy (the 0 of photo-electron energy).  For :math:`k` in units of
:math:`\rm \AA^{-1}` and :math:`E` in units of eV, :math:`k \approx
\sqrt{(E-E_0)/3.81}`.  With this conversion of energy to wavenumber,
:math:`\chi(k)` is defined from

    :math:`\chi(E) = \frac{\mu(E)-\mu_0(E)}{\Delta\mu}` 

where :math:`\mu_0(E)` is the post-edge background function determined
here, and :math:`\Delta\mu` is the edge step, determined from the
:func:`pre_edge`.
