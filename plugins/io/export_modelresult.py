#!/usr/bin/env python
#
# export a ModelResult
#
import numpy as np
from collections import OrderedDict
from lmfit.model import ModelResult
from lmfit.printfuncs  import gformat, getfloat_attr

def export_modelresult(result, filename='fitresult.xdi',
                       datafile=None, _larch=None, **kwargs):
    """
    export an lmfit ModelResult to an XDI data file

    Arguments
    ---------
     result       ModelResult, required
     filename     name of output file ['fitresult.xdi']
     datafile     name of data file (or `None`) [`None`]

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
    #endif
    header = ["XDI/1.1  Lmfit Result File"]
    hadd = header.append
    if datafile is not None:
        hadd(" Datafile.name:  %s " % datafile)
    else:
        hadd(" Datafile.name: <unknnown>")
    #endif
    ndata = len(result.best_fit)
    columns = OrderedDict()
    for aname in result.model.independent_vars:
        val = kwargs.get(aname, None)
        if val is not None and len(val) == ndata:
            columns[aname] = val
        #endif
    #endfor
    columns['best_fit'] = result.best_fit
    columns['init_fit'] = result.init_fit

    delta_fit = result.eval_uncertainty(result.params, **kwargs)

    columns['delta_fit'] = delta_fit
    if len(result.model.components) > 1:
        comps = result.eval_components(result.params, **kwargs)
        for name, val in comps.items():
            columns[name] = val
        #endfor
    #endif

    clabel = []
    for i, cname in enumerate(columns):
        hadd(" Column.%i:  %s" % (i+1, cname))
        clabel.append('%15s ' % cname)
    #endfor
    hadd("Fit.Statistics: Start here")
    hadd(" Fit.model_name:          %s" % result.model.name)
    hadd(" Fit.method:              %s" % result.method)
    hadd(" Fit.n_function_evals:    %s" % getfloat_attr(result, 'nfev'))
    hadd(" Fit.n_data_points:       %s" % getfloat_attr(result, 'ndata'))
    hadd(" Fit.n_variables:         %s" % getfloat_attr(result, 'nvarys'))
    hadd(" Fit.chi_square:          %s" % getfloat_attr(result, 'chisqr', fmt='%6g'))
    hadd(" Fit.reduced_chi_square:  %s" % getfloat_attr(result, 'redchi', fmt='%6g'))
    hadd(" Fit.akaike_info_crit:    %s" % getfloat_attr(result, 'aic', fmt='%6g'))
    hadd(" Fit.bayesian_info_crit:  %s" % getfloat_attr(result, 'bic', fmt='%6g'))

    hadd("Param.Statistics: Start here")
    namelen = max([len(p) for p in result.params])
    for name, par in result.params.items():
        space = ' '*(namelen+1-len(name))
        nout = "Param.%s:%s" % (name, space)
        inval = '(init= ?)'
        if par.init_value is not None:
            inval = '(init=% .7g)' % par.init_value
        #endif
        try:
            sval = gformat(par.value)
        except (TypeError, ValueError):
            sval = 'Non Numeric Value?'
        #endtry
        if par.stderr is not None:
            serr = gformat(par.stderr, length=9)
            sval = '%s +/-%s' % (sval, serr)
        #endif
        if par.vary:
            bounds = "[%s: %s]" % (gformat(par.min), gformat(par.max))
            hadd(" %s %s %s %s" % (nout, sval, bounds, inval))
        elif par.expr is not None:
            hadd(" %s %s  == '%s'" % (nout, sval, par.expr))
        else:
            hadd(" %s % .7g (fixed)" % (nout, par.value))
        #endif
    #endfor
    hadd("////////  Fit Report ////////")
    for r in result.fit_report().split('\n'):
        hadd("   %s" % r)
    #endfor

    hadd("-" * 77)

    hadd("".join(clabel)[1:])
    header[0] = "XDI/1.1  Lmfit Result File  %i header lines" % (len(header))
    dtable = []
    for dat in columns.values():
        dtable.append(dat)
    #endfor

    dtable = np.array(dtable).transpose()
    datatable = []
    for i in range(ndata):
        row = ["%15.8g" % col for col in dtable[i, :]]
        datatable.append(" ".join(row))
    #endfor
    datatable.append('')
    with open(filename, 'w') as fh:
        fh.write("\n".join(['#%s' % s for s in header]))
        fh.write("\n")
        fh.write("\n".join(datatable))

    print("wrote ", filename)
#enddef

def registerLarchPlugin():
    return ('_io', {'export_modelresult': export_modelresult,})
