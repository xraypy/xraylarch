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
:math:`2R`.  The normalizaion of :math:`\tilde\chi(R)` from a Fourier
transform of :math:`\chi(k)` is a matter of convention, but we follow the
symmetric case above (with :math:`t` replaced by :math:`k` and
:math:`\omega` replaced by :math:`2R`, and of course :math:`f` by
:math:`\chi`).

But there are two more important issues to mention.  First, an XAFS Fourier
transform mutiplies :math:`\chi(k)` by a power of :math:`k`, :math:`k^n`
and by a window function :math:`\Omega(k)` before doing the Fourier
transform.  The power-law weighting allow the oscillations in :math:`k` to
emphasize different portions of the spectra, or to give a uniform intensity
to the oscillations.  The window function acts to smooth the resulting
Fourier transform and remove ripple and ringing in it that would result
from a sudden truncation of :math:`\chi(k)` at the end of the data range.

The second important issue is that the continuous Fourier transform
described above is replaced by a discrete transform.  This better matches
the discrete sampling of energy and :math:`k` values of the data, and
allows Fast Fourier Transform techinques to be used.  It does change the
definitions of the transforms used somewhat. First, the :math:`\chi(k)`
data must be on *uniformly spaced* set of :math:`k` values.  The default
:math:`k` spacing used in Larch (including as output from :func:`autobk`)
is :math:`\delta k` = 0.05 :math:`\rm\AA^{-1}`.  Second, the array size for
:math:`\chi(k)` used in the Fourier transform should be a power of 2. The
default used in Larch is :math:`N_{\rm fft}` = 2048.   Together, these
allow :math:`\chi(k)` data to 102.4 :math:`\rm\AA^{-1}`.  Of course, real
data doesn't extend that far, so the array to be transformed is
*zero-padded* to the end of the range.  Since the spacing :math:`\delta R`
of the resulting discrete :math:`\chi(R)` is given as
:math:`\pi/{(N_{\rm fft} \delta k )}`, the extended range and zero-padding
will increase the density of points in :math:`\chi(R)`, smoothly
interpolating the values.   For :math:`N_{\rm fft}` = 2048 and
:math:`\delta k` =  0.05 :math:`\rm\AA^{-1}`, the :math:`R` spacing is
approximately :math:`\delta R` =  0.0307 :math:`\rm\AA`.

For the discrete Fourier transforms with samples of :math:`\chi(k)` at the
points :math:`k_n = n \, \delta k`, and samples of :math:`\chi(R)` at the
points :math:`R_m = m \, \delta R`, the definitions become:

.. math::
   :nowrap:

   \begin{eqnarray*}
   \tilde\chi(R_m) &=& \frac{i \delta k}{\sqrt{\pi N_{\rm fft}}} \,
   		       \sum_{n=1}^{N_{\rm fft}} \chi(k_n) \,
                       \Omega(k_n) \, k_n^w e^{2i\pi n m/N_{\rm fft}} \\
   \tilde\chi(k_n) &=& \frac{2 i \delta R}{\sqrt{\pi N_{\rm fft}}} \,
                       \sum_{m=1}^{N_{\rm fft}} \tilde\chi(R_m) \,
                       \Omega(R_m) \, e^{-2i\pi n m/N_{\rm fft}} \\
   \end{eqnarray*}


These normalizations preserve the symmetry properties of the Fourier
Transforms with conjugate variables :math:`k` and :math:`2R`.

A final complication in using Fourier transforms for XAFS is that the
measured :math:`\mu(E)` and :math:`\chi(k)` are a strictly real values,
while the Fourier transform inherently treats :math:`\chi(k)` and
:math:`\chi(R)` as complex values. This leads to an ambiguity about how to
construct the complex :math:`\tilde\chi(k)`.  In many formal treatments,
XAFS is written as the imaginary part of a complex function.  This might
lead one to assume that constructing :math:`\tilde\chi(k)` as :math:`0 +
i\chi(k)` would be the natural choice.  For historical reasons, Larch uses
the opposite convention, constructing :math:`\tilde\chi(k)` as
:math:`\chi(k) + i*0`.   As we'll see below, you can easily change this
convention.  The effect of this choice is minor unless one is
concerned about the differences of the real and imaginary parts of
:math:`\chi(R)` or one is intending to filter and back-transform the
:math:`\chi(R)` and compare the filtered and unfiltered data.


Forward XAFS Fourier transforms (:math:`k{\rightarrow}R`)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The forward Fourier transform converts :math:`\chi(k)` to :math:`\chi(R)`
and is of primary importance for XAFS analysis.  In Larch, this is
encapsulated in the :func:`xafsft` function.

..  function:: xftf(k, chi, group=None, ...)

    perform a forward XAFS Fourier transform, from :math:`\chi(k)` to
    :math:`\chi(R)`, using common XAFS conventions.


..  function:: xftf_fast(chi, nfft=2048, kstep=0.05)

    perform a forward XAFS Fourier transform, from :math:`\chi(k)` to
    :math:`\chi(R)`, using common XAFS conventions.  This version demands
    chi to represent :math:`\chi(k)` on a uniform :math:`k` grid, and
    returns the complex array of :math:`\chi(R)` without putting any
    values into a group.

Reverse XAFS Fourier transforms (:math:`R{\rightarrow}q`)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Reverse Fourier transforms convert :math:`\chi(R)` back to filtered
:math:`\chi(k)`.  We refer to the filtered :math:`k` space as :math:`q` to
emphasize the distinction between the two.


..  function:: xftr(r, chir, group=None, ...)

    perform a revers XAFS Fourier transform, from :math:`\chi(R)` to
    :math:`\chi(q)`, using common XAFS conventions.


..  function:: xftr_fast(chi, nfft=2048, kstep=0.05)

    perform a reverse XAFS Fourier transform, from :math:`\chi(k)` to
    :math:`\chi(R)`, using common XAFS conventions.  This version demands
    chir to represent the complex :math:`\chi(R)` as created from
    :math:`\chi(k)` on a uniform :math:`k` grid, and returns the complex
    array of :math:`\chi(q)` without putting any values into a group.



Fourier transform windows
~~~~~~~~~~~~~~~~~~~~~~~~~~

As mentioned above, a Fourier transform window will smooth the resulting
Fourier transformed spectrum, removing ripple and ringing in it that would
result from a sudden truncation data at the end of it range.  There is an
extensive literature on such windows, and a lot of choices and parameters
available for constructing windows.  A sampling of windows is shown below.


..  function:: ftwindow(k, xmin=0, xmax=None, dk=1, ...)

    create a Fourier transform window function.


Examples: Fourier transform windows
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
