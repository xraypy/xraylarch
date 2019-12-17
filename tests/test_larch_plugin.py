import numpy as np

def fcn0():
    """0 arg  """
    return True

def fcn1(x):
    """1 arg  """
    return x

def add2(x, y):
    """2 args  """
    return 2*x + y

def add_scale(x, y, scale=1):
    """2 pos args, 1 var  """
    return (2*x + y)*scale

def f1_larch(x, option=False):
    """1 arg, with an option="""
    if option:
        return x
    else:
        return 2*x

def f1_kwargs(x, **kws):
    """1 arg, with **kws"""
    if x:
        return 2*x
    else:
        return len(kws)

def f1_varargs(x, *args): # , **kws):
    """1 arg, with *args"""
    print(" f1 varargs ", args, kws)
    return 2*x

def registerLarchPlugin():
    return ('_tests', dict(fcn0=fcn0, fcn1=fcn1,
                           add2=add2,
                           add_scale=add_scale,
                           f1_larch=f1_larch,
                           f1_kwargs=f1_kwargs,
                           f1_varargs=f1_varargs))
