==============================================
XAFS: Post-edge Background Subtraction
==============================================

.. module:: _xafs
   :synopsis: XAFS Pre-edge subtraction and normalization functions

..  function:: autobk(energy, mu, group=None, rbkg=1.0, ...)

    Determine the post-edge background function, :math:`\mu_0(E)`,
    according the the "AUTOBK" algorithm, in which a spline function is
    matched to the low-*R* components of the resulting :math:`\chi(k)`.

def autobk(energy, mu, group=None, rbkg=1, nknots=None,
           e0=None, edge_step=None, kmin=0, kmax=None, kweight=1,
           dk=0, win=None, vary_e0=True, k_std=None, chi_std=None,
           nfft=2048, kstep=0.05, pre_edge_kws=None,
           debug=False, _larch=None, **kws):

    """Use Autobk algorithm to remove XAFS background
    Options are:
      rbkg -- distance out to which the chi(R) is minimized
    """
    if _larch is None:

