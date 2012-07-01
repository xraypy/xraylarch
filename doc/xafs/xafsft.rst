==============================================
XAFS: Fourier Transforms for XAFS
==============================================

.. module:: _xafs
   :synopsis: XAFS Fourier transform functions


..  function:: ftwindow(k, xmin=0, xmax=None, dk=1, ...)

    create a Fourier transform window function.


..  function:: xafsft(k, chi, group=None, ...)

    perform a forward XAFS Fourier transform, from :math:`\chi(k)` to
    :math:`\chi(R)`, using common XAFS conventions.


..  function:: xafsift(r, chir, group=None, ...)

    perform an inverse XAFS Fourier transform, from :math:`\chi(R)` to
    :math:`\chi(q)`, using common XAFS conventions.

..  function:: xafsft_fast(chi, nfft=2048, kstep=0.05)

    perform a forward XAFS Fourier transform, from :math:`\chi(k)` to
    :math:`\chi(R)`, using common XAFS conventions.  This version demands
    chi to represent :math:`\chi(k)` on a uniform :math:`k` grid, and
    returns the complex array of :math:`\chi(R)` without putting any
    values into a group.

..  function:: xafsift_fast(chi, nfft=2048, kstep=0.05)

    perform a reverse XAFS Fourier transform, from :math:`\chi(k)` to
    :math:`\chi(R)`, using common XAFS conventions.  This version demands
    chir to represent the complex :math:`\chi(R)` as created from
    :math:`\chi(k)` on a uniform :math:`k` grid, and returns the complex
    array of :math:`\chi(q)` without putting any values into a group.


