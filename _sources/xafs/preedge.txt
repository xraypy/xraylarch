==============================================
XAFS: Pre-edge Subtraction and Normalization
==============================================

.. module:: _xafs
   :synopsis: XAFS Pre-edge subtraction and normalization functions

..  function:: pre_edge(energy, mu, group=None, ...)

    Pre-edge subtraction and normalization.

    This performs a number of steps:
       1. determine :math:`E_0` (if not supplied) from max of deriv(mu)
       2. fit a line of polymonial to the region below the edge
       3. fit a polymonial to the region above the edge
       4. extrapolae the two curves to :math:`E_0` to determine the edge jump


    :param energy:  1-d array of x-ray energies, in eV
    :param mu:      1-d array of :math:`\mu(E)`
    :param group:   output group 
    :param e0:      edge energy, :math:`E_0` in eV.  If None, it will be determined here.
    :param step:    edge jump.  If None, it will be determined here.
    :param pre1:    low E range (relative to E0) for pre-edge fit
    :param pre2:    high E range (relative to E0) for pre-edge fit
    :param nvict:   energy exponent to use for pre-edg fit.  See Note below
    :param norm1:   low E range (relative to E0) for post-edge fit
    :param norm2:   high E range (relative to E0) for post-edge fit
    :param nnorm:   number of terms in polynomial (that is, 1+degree) for
                    post-edge, normalization curve. Default=3 (quadratic)

    For return values, if **group** is None, the return value is
    (edge_step, e0).

    If a **group** is supplied, return value is None, and the following
    data is put into the **group**:

       +-----------+----------------------------------------------------+
       | attribute | meaning                                            |
       +-----------+----------------------------------------------------+
       | e0        |  energy origin                                     |
       +-----------+----------------------------------------------------+
       | edge_step |  edge step                                         |
       +-----------+----------------------------------------------------+
       | norm      |  normalized mu(E)   (array)                        |
       +-----------+----------------------------------------------------+
       | pre_edge  |  pre-edge curve (array)                            |
       +-----------+----------------------------------------------------+
       | post_edge |  post-edge, normalization curve  (array)           |
       +-----------+----------------------------------------------------+

    Note:
       nvict gives an exponent to the energy term for the pre-edge fit.
       That is, a line :math:`(m E + b)` is fit to 
       :math:`\mu(E) E^{nvict}`   over the pr-edge region, E= [E0+pre1, E0+pre2].



..  function:: find_e0(energy, mu, group=None, ...)

    Determine :math:`E_0`, the energy threshold of the absorption edge, 
    from the arrays energy and mu for :math:`\mu(E)`.

    This finds the point with maximum derivative with some
    checks to avoid spurious glitches.
    

    :param energy:  1-d array of x-ray energies, in eV
    :param   mu:    1-d array of mu(E)
    :param group:   output group 


    Returns e0, the edge energy, :math:`E_0` in eV.  If a group is
    supplied, group.e0 will also be set to this value.
