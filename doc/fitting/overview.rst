==================
Fitting Overview
==================

Modeling and fitting of experimental data is a key need for the analysis of
most scientific data.  There is an extensive literature on these topics,
with a wealth written on both the theoretical and practical aspects of
modeling data.  One of the more common and general approaches is to use a
least-squares analysis, in which a model is adjusted until it matches
experimental data such that the sum of squares of the difference between
data and model is as small as possible.  Mathematically, this is expressed
as

.. math::

    S = \sum_{i=1}^{N} \big[{y_i - f(x_i, \bf{\beta}) } \big]^2

where the experimental data is expressed as :math:`\bf{y}(\bf{x})` that is
discretely sampled at :math:`N` points, :math:`f(\bf{x}, \bf{\beta})` is a
model function, and :math:`\bf{\beta}` is a set of adjustable parameters in
the model.  For a simple linear model of data, for example, :math:`f =
\beta_0 + \beta_1 \bf{x}`, but the model can be arbitrary complex.  There
is good statistical justification for using this approach, and many
existing tools for helping to find the minimal values of :math:`S`.  These
justifcations are not without criticism or caveats, but we'll leave that
aside for now.

It is common to include a multiplicative factor to each component in in the
least-squares equation above, so that the different data points might be
given more or less weight.  Again, there are several approaches to this,
with one of the most common approaches to weight by the inverse of the
estimated uncertainty in the data value.  This then what is generally
called the chi-square goodness-of-fit parameter


.. math::

    \chi^2 = \sum_{i=1}^{N} \big[\frac{y_i - f(x_i, \bf{\beta})}{\epsilon_i} \big]^2

Here, :math:`\epsilon_i` represents the uncertainty in the value of :math:`y_i`.

As mentioned, the model function can be fairly complex. There is a large
literature on the cases where the model function :math:`f(\bf{x},
\bf{\beta})` depends linearly on its parameters :math:`\bf{\beta}`.  More
generally, the model function will not depend linearly on its parameters,
and the minimization is generally referred to a ''non-linear least-squares
optimization'' in the literature.  All the discussion here will assume that
the models can be non-linear.


It is convenient to define the **residual function**  as

.. math::

     r = \frac{y - f(x, \bf{\beta})}{\epsilon}


so that the sum to be minimized is a simple sum of this function, :math:`s
= \sum_i^{N} r_i^2`.   The fitting process can then be made very general
with a few key components required.  Specifically, for Larch, the
requirements are

  1. A set of Parameters, :math:`{\bf{\beta}}`, that are used in the model,
  and are to be adjusted to find the least-square value of the sum of
  squares of the residual.  These must be **parameters** (discussed below)
  that are held in a single **parameter group**.  This is a regular Larch
  group, and so can contain other values as well.  That makes it one possible
  way to pass in data to the objective function. Note that, as discussed
  later, the fit will write most of its outputs to this group.

  2. An **objective function** to calculate the residual function.  This
  will be a Larch function that takes the **parameter group** described
  above as its first argument, and an unlimited set of optional arguments.
  The arrays for the data should passed in by these optional arguments.
  This function should return the residual array, :math:`r` that will be
  minimized in the least-squares sense.

After the fit has completed, several statistical results describing the fit
quality and the values and uncertainties found for the parameters will be
available.  Though the description so far as been somewhat formal, the
process is not as hard as it sounds, and all the topics will be discussed
in more detail below.

As mentioned above, the objective function needs to follow fairly strict
guidelines.  The first argument must be a Larch group containing all the
Parameters for the mode, and the return value of the objective function
must be the fit residual -- the array to be minimized in the least-squares
sense.

We'll jump in with a simple example fit to a line, with this script::

    # create mock data for a line
    dat = group(x = linspace(0, 10, 51))
    dat.y = 1.0 + 2.5 * dat.x + random.normal(size=51, scale=1)

    # create a group of fit parameters
    params = group(off = guess(0), slope = guess(0))

    init = params.off + params.slope * dat.x

    # define objective function for fit residual
    def fitresid(p, data):
        return data.y - (p.off + p.slope * data.x)
    enddef

    # perform fit
    minimize(fitresid, params, args=(dat,))

    final = params.off + params.slope * dat.x

Here `params` is the parameter group, with both `params.off` and
`params.slope` as Parameters.  `fitresid` is the objective function that
calculates the model function from the values of the Parameters, and
returns the residual (data - model).  The :func:`minimize` function does
the actual fit, and will call the objective function many times with
different (and generally improved) values for the parameters.  Of course,
there are faster and more statistically sound methods for determining a
linear trend in a set of data, but the point of this example is to
illustrate the mechanisms for doing more complex, non-linear modeling of
data.
