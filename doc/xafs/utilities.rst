==============================================
XAFS: Utility functions
==============================================

.. module:: _xafs

There are a few functions for XAFS analysis that do not fall neatly into
the pro



The :func:`ktoe` and :func:`etok` functions
=============================================

..  function:: etok(energies)

    Convert photo-electron energy in eV to wavenumber in :math:`\AA^{-1}`.
    energies can be a single number or array of numbers.

..  function:: ktoe(wavenumbers)

    Convert photo-electron wavenumber in :math:`\AA^{-1}` ot energy in eV.
    wavenumber can be a single number or array of numbers.

An example use would be to print out a table of energies and :math:`k` values::

    larch> kvals = linspace(0, 25, 26)
    larch> evals = ktoe(kvals)
    larch> for k,e in zip(kvals, evals)):
    larch>      print " %5.1f 1/Ang ->  %8.2f eV" %(k , e)
    larch> endfor
       0.0 1/Ang ->      0.00 eV
       1.0 1/Ang ->      3.81 eV
       2.0 1/Ang ->     15.24 eV
       3.0 1/Ang ->     34.29 eV
       4.0 1/Ang ->     60.96 eV
       5.0 1/Ang ->     95.25 eV
       6.0 1/Ang ->    137.16 eV
       7.0 1/Ang ->    186.69 eV
       8.0 1/Ang ->    243.84 eV
       9.0 1/Ang ->    308.61 eV
      10.0 1/Ang ->    381.00 eV
      11.0 1/Ang ->    461.01 eV
      12.0 1/Ang ->    548.64 eV
      13.0 1/Ang ->    643.89 eV
      14.0 1/Ang ->    746.76 eV
      15.0 1/Ang ->    857.25 eV
      16.0 1/Ang ->    975.36 eV
      17.0 1/Ang ->   1101.08 eV
      18.0 1/Ang ->   1234.43 eV
      19.0 1/Ang ->   1375.40 eV
      20.0 1/Ang ->   1523.99 eV
      21.0 1/Ang ->   1680.20 eV
      22.0 1/Ang ->   1844.03 eV
      23.0 1/Ang ->   2015.48 eV
      24.0 1/Ang ->   2194.55 eV
      25.0 1/Ang ->   2381.24 eV



The :func:`estimate_noise` function
==========================================

..  function:: estimate_noise(k, chi, group=None, rmin=15, rmax=30, ....)

    Automatically estimate the noise level in a :math:`\chi(k)` spectrum.


    :param k:       1-d array of :math:`k`
    :param chi:     1-d array of :math:`\chi`
    :param group:   output group.
    :param rmin:    minimum :math:`R` value for noise estimate.
    :param rmax:    maximum :math:`R` value for noise estimate.
    :param kweight:  exponent for weighting spectra by k**kweight [1]
    :param kmin:     starting k for FT Window [0]
    :param kmax:     ending k for FT Window  [20]
    :param dk:       tapering parameter for FT Window [4]
    :param dk2:      second tapering parameter for FT Window [None]
    :param window:   name of window type ['kaiser']
    :param nfft:     value to use for N_fft [2048].
    :param kstep:    value to use for delta_k ( Ang^-1) [0.05]


    The method uses an XAFS Fourier transform, and many of arguments
    (**kmin**, **kmax**, etc) are identical to those of :func:`xftf`.

    The following outputs are written to the supplied **group** (or _sys.xafsGroup if
    **group** is not supplied):

     ================= ===============================================================
      attribute         meaning
     ================= ===============================================================
      epsilon_k          estimated noise level in :math:`\chi(k)`.
      epsilon_r          estimated noise level in :math:`\chi(R)`.
      kmax_suggest       suggested highest :math:`k` value for which :math:`|\chi(k)| > \epsilon_k`
     ================= ===============================================================

This method uses the high-R portion of :math:`\chi(R)` (between **rmin**
and **rmax**) as a measure of the noise level in the :math:`\chi(R)` data
and uses Parseval's theorem to convert this noise level to that in
:math:`\chi(k)`.  This method implicitly assumes that there is no signal in
the high-R portion of the spectrum, and that the noise in the spectrum is
"white" (independent of :math:`R`) .  Each of these assumptions can be
legitimately questioned.  Then again, making the assertion that these
assumptions are invalid and disregarding the estimated noise level here
would require knowledge of the noise in an XAFS spectrum that most users do
not have.  At the very least, this estimate should be be interpreted as a
minimal estimate of the noise level in :math:`\chi(k)`.

The estimate for the output value **kmax_suggest** has a tendency to be
pessimistic in how far out the :math:`\chi(k)` data goes before being
dominated by noise, but has the advantage of being an impartial measure of
data quality. It is particularly pessimistic for extremely good data.  Then
again, considering that the estimate for :math:`\epslion` is probably too
small, the estimate may not be that bad.

