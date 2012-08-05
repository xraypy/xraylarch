#!/usr/bin/env python
from parameter import Parameter, isParameter, param_value
from minimizer import Minimizer, minimize, fit_report

def param(*args, **kws):
    "create a fitting Parameter as a Variable"
    if len(args) > 0 and isinstance(args[0], (str, unicode)):
        expr = args[0]
        args = args[1:]
        kws.update({'expr': expr})
    out = Parameter(*args, **kws)
    if 'name' not in kws:
        return out

def guess(value,  **kws):
    """create a fitting Parameter as a Variable.
    A minimum or maximum value for the variable value can be given:
       x = guess(10, min=0)
       y = guess(1.2, min=1, max=2)
    """
    kws.update({'vary':True})
    return param(value, **kws)

