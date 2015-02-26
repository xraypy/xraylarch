===========================================================
XAFS: Computing anomalous scattering factors from XAFS data
===========================================================

.. module:: _xafs
   :synopsis: Differential Kramers-Kronig transforms

.. _CARD: http://www.esrf.eu/computing/scientific/CARD/CARD.html


An input XAFS spectra is used to generate energy-dependent, anomlous
scattering factors.  This is used to improve upon the bare atom
anomalous scattering factors of :cite:ts:`Cromer_Liberman`,
:cite:ts:`Chantler`, and others near the absorption edge.

Since XAFS is sensitive to the atomic environment of the resonant atom
(through the variations of the absorption coefficient), the scattering
factors from the differential KK ttransform will also be sensitive to
the local atomic structure of the resonant atom.  These scattering
factors, which are sensitive to chemical state and atomic environment,
may be useful for many x-ray scattering and imaging experiments near
resonances.  The primary application is for the interpretation of
fixed-q absorption experiments, such diffraction anomalous
fine-structure (DAFS) or reflectively-EXAFS (sometimes known as
ReflEXAFS).

This performs the same algorithm as the venerable DIFFKK program
described in :cite:ts:`diffkk`.  This uses the MacLaurin series
algorithm to compute the differential (i.e. difference between the
data and the tabulated :math:`f''(E)`) Kramers-Kronig transform.  This
algorithm is described in :cite:ts:`Ohta:88`.  This implementation
casts the MacLaurin series algorithm in vectorized form using numpy,
so it is quite a bit faster that the earlier Fortran implementation or
the scalar python implementation used in `CARD`_.

The input :math:`\mu(E)` data are first matched to the tabulated
:math:`f''(E)` using the MBACK algorithm of :cite:ts:`Weng` with an
option of using the modification proposed by :cite:ts:`lee-xiang`.
This scales the measured :math:`\mu(E)` to the size of the tabulated
function and adjusts the overall slope of the data to best match the
tabulated value.  This is seen at the top of Figure
:num:`fig-cu-diffkk`.

The difference between the scaled :math:`\mu(E)` and the tabulated
:math:`f''(E)` is then subjected to the KK transform.  The reuslt is
added to the tabulated :math:`f'(E)` spectrum to produce the resulting
real part of the energy-dependent complex scattering factor.  This is
shown at the bottom of :num:`fig-cu-diffkk`.

.. _fig-cu-diffkk:

.. figure::  ../_images/cu_diffkk.png
    :target: ../_images/cu_diffkk.png
    :width: 65%
    :align: center

    The anomalous scattering factors determined fpr copper metal from
    a copper foil, compared with the bare-atom, Cromer-Liberman values.


..  function:: diffkk(energy=None, xmu=None, e0=None, z=None, edge='K', order=3, form='mback')

    create a diffKK Group.

    :param energy:    an array containing the energy axis of the measurement
    :param xmu:       an array containing the measured :math:`mu(E)`
    :param e0:        the edge energy of the measured data
    :param z:         the Z number of the absorber element
    :param edge:      the edge measured, usually K or L3
    :param order:     the order of the polynomial used to normalize the data to the tabulated :math:`f''(E)`
    :param form:      the form of the normalization function ('mback' or 'lee')
    :returns: a diffKK Group.

..  function:: diffkk.kktrans(energy=None, xmu=None, e0=None, z=None, edge='K', order=3, form='mback')

    Perform the KK transform.

    :param energy:    an array containing the energy axis of the measurement
    :param xmu:       an array containing the measured :math:`mu(E)`
    :param e0:        the edge energy of the measured data
    :param z:         the Z number of the absorber element
    :param edge:      the edge measured, usually K or L3
    :param order:     the order of the polynomial used to normalize the data to the tabulated :math:`f''(E)`
    :param form:      the form of the normalization function ('mback' or 'lee')
    :returns:         None


The following data is put into the diffKK group:

       ================= ===============================================================
        attribute         meaning
       ================= ===============================================================
        f2                array of tabulated :math:`f''(E)`
        f1                array of tabulated :math:`f'(E)`
        fpp               array of normalized :math:`f''(E)`
        fp                array of KK transformed :math:`f'(E)`
       ================= ===============================================================

All four arrays are on the same energy grid as the input data.

Here is an example script to make the figure shown above:

.. code:: python

  print 'Reading copper foil data'
  a=read_ascii('../xafsdata/cu_10k.xmu')
  dkk=diffkk(a.energy, a.mu, e0=8979, z=29, order=4, form='mback')

  print 'Doing diff KK transform'
  dkk.kktrans()

  newplot(dkk.energy, dkk.f2, label='f2', xlabel='Energy (eV)', ylabel='scattering factors',
          show_legend=True, legend_loc='lr')
  plot(dkk.energy, dkk.fpp, label='f"(E)')
  plot(dkk.energy, dkk.f1,  label='f1')
  plot(dkk.energy, dkk.fp,  label='f\'(E)')


Need to discuss L edge data...
