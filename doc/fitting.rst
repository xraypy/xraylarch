.. _fitting-chapter:

=================================
Fitting and Modeling Data
=================================


.. _lmfit: https://lmfit.github.io/lmfit-py/

A key motivation for Larch's initial design was to provide easy and
robust ways to model data and perform complex fits of data to models.
These topics are not really specific to the kinds of data analyzed,


This chapter discusses the basic concepts
for building models, setting up and performing fits, and inspecting the
results.

The concepts presented here focus on modeling and fitting of general
spectra and data.  Of course, Larch can provides other, specific functions
for doing fits, such as the EXAFS procedures :func:`_xafs.autobk` and
:func:`_xafs.feffit`.  Many of these concepts (and the underlying fitting
algorithms) are used for those other functions as well.

.. toctree::
   :maxdepth: 2

   fitting_overview
   fitting_parameters
   fitting_minimize
   fitting_results
   fitting_lineshapes
   fitting_examples
   fitting_fitpeaks
   fitting_confidence
