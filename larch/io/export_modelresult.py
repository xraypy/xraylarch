#!/usr/bin/env python
#
# export a ModelResult
#
import sys
import numpy as np
from lmfit.model import ModelResult
from larch.utils import gformat, getfloat_attr

def export_modelresult(result, filename='fitresult.xdi',
                       datafile=None, ydata=None, yerr=None,
                       xdata=None, label=None, **kwargs):
    """
    export an lmfit ModelResult to an XDI data file

    Arguments
    ---------
     result       ModelResult, required
     filename     name of output file ['fitresult.xdi']
     datafile     name of data file [`None`]
     ydata        data array used for fit [`None`]
     yerr         data error array used for fit [`None`]

    Notes
    -----
    keyword arguments should include independent variables

    Example
    -------
        result = model.fit(ydata, params, x=x)
        export_modelresult(result, 'fitresult_1.xdi', x=x,
                           datafile='XYData.txt')
    """
    if not isinstance(result, ModelResult):
        raise ValueError("export_fit needs a lmfit ModelReult")

    header = ["XDI/1.1  Lmfit Result File"]
    hadd = header.append
    if datafile is not None:
        hadd(f" Datafile.name:  {datafile}")
    else:
        hadd(" Datafile.name: <unknnown>")
    if label is not None:
        hadd(f" Fit.label:  {label}")

    ndata = len(result.best_fit)
    columns = {}
    if xdata is None:
        xdata = result.userkws['x']
    if ydata is None:
        ydata = result.data
    if yerr is None:
        yerr = np.ones(len(ydata), dtype='float64')

    columns['xdata'] = xdata
    columns['ydata'] = ydata
    columns['yerr'] = yerr

    columns['best_fit'] = result.best_fit
    columns['init_fit'] = result.init_fit
    delta_fit = 0.0*result.best_fit
    if not any([p.stderr is None for p in result.params.values()]):
        delta_fit = result.eval_uncertainty(result.params, **kwargs)

    columns['delta_fit'] = delta_fit
    if len(result.model.components) > 1:
        comps = result.eval_components(result.params, **kwargs)
        for name, val in comps.items():
            columns[name] = val

    clabel = []
    for i, cname in enumerate(columns):
        hadd(f" Column.{i+1}:  {cname}")
        clabel.append('%15s ' % cname)

    hadd("Param.Statistics: Start here")
    namelen = max([len(p) for p in result.params])
    for name, par in result.params.items():
        space = ' '*(namelen+1-len(name))
        nout = f"Param.{name}:{space}"
        inval = '(init= ?)'
        if par.init_value is not None:
            inval = f'(init={par.init_value: .7g})'

        try:
            sval = gformat(par.value)
        except (TypeError, ValueError):
            sval = 'Non Numeric Value?'
        if par.stderr is not None:
            sval = f"{sval} +/- {gformat(par.stderr, length=9)}"

        if par.vary:
            bounds = f"[{gformat(par.min)}: {gformat(par.max)}]"
            hadd(f" {nout} {sval} {bounds} {inval}")
        elif par.expr is not None:
            hadd(f" {nout} {sval} == '{par.expr}'")
        else:
            hadd(f" {nout} {par.value: .7g} (fixed)")

    hadd("////////  Fit Report ////////")
    for r in result.fit_report().split('\n'):
        hadd("   %s" % r)
    hadd("-" * 77)
    hadd("".join(clabel)[1:])
    header[0] = "XDI/1.1  Lmfit Result File  %i header lines" % (len(header))
    dtable = []
    for dat in columns.values():
        dtable.append(dat)
    dtable = np.array(dtable).transpose()
    datatable = []
    for i in range(ndata):
        col = dtable[i, :]*1.0
        row = []
        for cval in col:
            try:
                val = gformat(cval, length=15)
            except:
                val = repr(cval)
            row.append(val)
        datatable.append(" ".join(row))

    datatable.append('')
    with open(filename, 'w', encoding=sys.getdefaultencoding()) as fh:
        fh.write("\n".join(['#%s' % s for s in header]))
        fh.write("\n")
        fh.write("\n".join(datatable))
