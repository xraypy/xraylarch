==============================================
XAFS: Fourier Transforms for XAFS
==============================================

:synopsis: XAFS Fourier transform functions

Fourier transforms are central to understanding and using
XAFS. Consequently, many of the XAFS functions in Larch use XAFS Fourier
transforms as part of their processing.  For example, but :func:`autobk`
and :func:`feffit` rely on XAFS Fourier transforms, as well as the specific
XAFS Fourier transform function described in this section.  The details of
these transforms will be described in detail in this section.  Many of
these functions share parametersa and arguments with similar names and
meanings.


Overview of XAFS Fourier transforms
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Standard Fourier transform of a signal :math:`f(t)` can be written as

.. math::
   :nowrap:

   \begin{eqnarray*}
         {\tilde{f}}(\omega) &=& \frac{1}{\sqrt{2\pi}} \int_{-\infty}^{\infty}
       f(t) e^{-i{\omega}t} dt \\
       f(t) &=& \frac{1}{\sqrt{2\pi}} \int_{-\infty}^{\infty}
       {\tilde{f}}(\omega) e^{i{\omega}t} d{\omega} \\
   \end{eqnarray*}

where the symmetric normalization is one of the more common choices of
conventions.  This gives conjugate variables of :math:`\omega` and
:math:`t`. Because XAFS goes as

.. math::

  \chi(k) \sim \sin[2kR + \delta(k)]

the conjugate variables in XAFS are generally taken to be :math:`k` and
:math:`2R`.  Thus, getting  a properly normalized :math:`\tilde\chi(R)`
from  a Fourier transform of :math:`\chi(k)` depends on the conventions
used.


Fourier transform windows
~~~~~~~~~~~~~~~~~~~~~~~~~~

..  function:: ftwindow(k, xmin=0, xmax=None, dk=1, ...)

    create a Fourier transform window function.


Forward XAFS Fourier transforms (:math:`k{\rightarrow}R`)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The forward Fourier transform converts :math:`\chi(k)` to :math:`\chi(R)`
and is of primary importance for XAFS analysis.  In Larch, this is
encapsulated in the :func:`xafsft` function.

..  function:: xafsft(k, chi, group=None, ...)

    perform a forward XAFS Fourier transform, from :math:`\chi(k)` to
    :math:`\chi(R)`, using common XAFS conventions.


..  function:: xafsft_fast(chi, nfft=2048, kstep=0.05)

    perform a forward XAFS Fourier transform, from :math:`\chi(k)` to
    :math:`\chi(R)`, using common XAFS conventions.  This version demands
    chi to represent :math:`\chi(k)` on a uniform :math:`k` grid, and
    returns the complex array of :math:`\chi(R)` without putting any
    values into a group.

Inverse XAFS Fourier transforms (:math:`R{\rightarrow}q`)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Inverse Fourier transforms convert :math:`\chi(R)` back to filtered
:math:`\chi(k)`.  We refer to the filtered :math:`k` space as :math:`q` to
emphasize the distinction between the two.


..  function:: xafsift(r, chir, group=None, ...)

    perform an inverse XAFS Fourier transform, from :math:`\chi(R)` to
    :math:`\chi(q)`, using common XAFS conventions.


..  function:: xafsift_fast(chi, nfft=2048, kstep=0.05)

    perform a reverse XAFS Fourier transform, from :math:`\chi(k)` to
    :math:`\chi(R)`, using common XAFS conventions.  This version demands
    chir to represent the complex :math:`\chi(R)` as created from
    :math:`\chi(k)` on a uniform :math:`k` grid, and returns the complex
    array of :math:`\chi(q)` without putting any values into a group.


