==============================================
XAFS: Post-edge Background Subtraction
==============================================

.. module:: _xafs
   :synopsis: XAFS Pre-edge subtraction and normalization functions

..  function:: autobk(energy, mu, group=None, rbkg=1.0, ...)

    Determine the post-edge background function, :math:`\mu_0(E)`,
    according the the "AUTOBK" algorithm, in which a spline function is
    matched to the low-*R* components of the resulting :math:`\chi(k)`.


