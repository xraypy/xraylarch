=================================
Spec-like Scans with StepScan
=================================

Spec is a commonly used program for collecting data at synchrotrons, as it
can not only communicate with Motors and Detectors, but can also work in
the geometries needed to run diffractometers, and includes a convenient
macro language.  Spec is not without limitations, and a reasonable goal of
StepScan would be to replace some uses of Spec. Of course, Python can
replace the macro language, and Epics Channel Access can control Motor and
Detectors.


.. module:: spec_emulator

To better enable a transition of some scanning away from Spec and toward
Python, StepScan has a :mod:`spec_emulator` module that provides Spec-like
functionality, with scanning methods :meth:`ascan`, :meth:`dscan`,
:meth:`a2scan`, :meth:`d2scan`, :meth:`lup`, and :meth:`mesh` that closely
match the Spec routines of the same name.

Setting up and Configuring the spec emulation layer
======================================================

To emulate Spec, one creates a :class:`SpecScan` object::

   >>> from epicsapps.stepscan import SpecScan
   >>> spec = SpecScan()

This creates an empty SpecScan object, which does not have any
configuration information about Motors and Detectors to use during a scan.
Motors can be added to the configuration with::

   >>> spec.add_motors(x='XXX:m1', y='XXX:m2', theta='XXX:m3')

where you can add as many *label=PV_NAME* keyword arguments as you like.
Later on, when scanning, you'll use the labels to mean the underlying PVs.
As with all of StepScan, the PVs are not required to be motors.

We'll also need to add some detectors.  StepScan supports many kinds of
detectors, but for simple scans with point-detectors, an Epics Scaler
record usually suffices, so we'll start with that::

   >>> spec.add_detector('XXX:scaler1', kind='scaler', nchan=8, use_calc=False)

By saying `kind='scaler'`, StepScan will know what to use for a Trigger,
how to set the dwell time, and what Counters to count -- all the channels 1
through 8 that have a non-blank name will be collected.  There is also the
option to set `use_calc=True` to use the calc record associated with the
Scan Record, which can be used to support offset values and simple
calculations.

As with other parts of StepScan, we can add *extra PVs* -- values to be
recorded at the start of each scan, with a list of (description, pvname)
tuples::

   >>> spec.add_extra_pvs((('Ring Current', 'S:SRcurrentAI.VAL'),
                           ('Ring Lifetime', 'S:SRlifeTimeHrsCC.VAL')))


We haven't yet set the name of the output file.   This is still a
work-in-progress, but currently, the Spec file is not emulated in detail,
but an ASCII file is written to for each scan.  We can change this anytime
with::

   >>> spec.filename = 'myoutput.dat'

At this point, we have a fully configured (if minimal) Spec emulator, and
can start running scans. It is likely

Using the spec emulation layer
===============================

To perform a simple absolute scan, we can use :meth:`ascan`, which would be
as simple as::

   >>> spec.ascan('x', 0, 0.5, 51, 0.5)

which scans Motor 'x' between 0 and 0.5 in 21 steps, counting for 0.5
second per point.

Other supported scan routines are :meth:`dscan`, which is like
:meth:`ascan` but with start and stop positions relative to the current
position::

   >>> spec.dscan('x', -0.1, 0.1, 41, 0.25)

The routines :meth:`a2scan` and :meth:`d2scan` simultaneously moves 2
Motors (in absolute and relative coordinates, respectively)::

   >>> spec.a2scan('x', 0, 1.0, 'y', 0, 0.2, 21, 0.5)
   >>> spec.d2scan('x', -0.5, 0.5, 'y', -0.1, 0.1, 21, 0.5)

That is, these move along a line in 'x'-'y' space.

The routines :meth:`a3scan` and :meth:`d3scan` simultaneously moves 3
Motors (in absolute and relative coordinates, respectively)::

   >>> spec.a3scan('x', 0, 1.0, 'y', 0, 0.2, 'theta', 10.0, 10.1, 21, 0.5)



Finally, :meth:`mesh` will make a 2-dimensional mesh, or map::

   >>> spec.mesh('x', 10, 11, 21, theta', 10.0, 10.1, 11,  0.25)

This will make a 21 x 11 pixel map, moving 'x' between 10 and 11 for each
'theta' value, so that 'theta' scans slowly.


