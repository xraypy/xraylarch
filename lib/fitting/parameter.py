from numpy import arcsin, cos, inf, nan, sin, sqrt
import json
from ..larchlib import isNamedClass

# use local version of uncertainties package
from . import uncertainties

class Parameter(object):
    """returns a parameter object: a floating point value with bounds that can
    be flagged as a variable for a fit, or given an expression to use to
    automatically evaluate its value (as a thunk).

    >>> x = param(12.0, vary=True, min=0)
    will set the value to 12.0, and allow it be varied by changing x._val,
    but its returned value will never go below 0.

    >>> x = param(expr='sqrt(2*a)')
    will have a value of sqrt(2*a) even if the value of 'a' changes after
    the creation of x
    """
    __invalid = "Invalid expression for parameter: '%s'"

    def __init__(self, value=0, min=None, max=None, vary=False,
                 name=None, expr=None, stderr=None, correl=None,
                 units=None, decimals=5, _larch=None, **kws):
        self._val = self._initval = value
        self._uval = None
        self.vary = vary
        self.min = min
        self.max = max
        self.name = name
        self._expr = expr
        self.stderr = stderr
        self.correl = correl
        self.units = units
        self.decimals = decimals
        self._ast = None
        self._larch = None
        self._from_internal = lambda val: val
        if (hasattr(_larch, 'run') and
            hasattr(_larch, 'parse') and
            hasattr(_larch, 'symtable')):
            self._larch = _larch
        #if self._larch is not None and name is not None:
        #    self._larch.symtable.set_symbol(name, self)

    def __copy__(self):
        return Parameter(value=self._val, min=self.min, max=self.max,
                         vary=self.vary, expr=self.expr,
                         stderr=self.stderr, correl=self.correl,
                         name=self.name,  _larch=self._larch)

    def __deepcopy__(self, memo):
        return Parameter(value=self._val, min=self.min, max=self.max,
                         vary=self.vary, expr=self.expr,
                         stderr=self.stderr, correl=self.correl,
                         name=self.name,  _larch=self._larch)
    def asjson(self):
        val = self._val
        # if self.expr is not None: val = 0.
        return json.dumps({'name': self.name, 'val': val,
                           'min': self.min,   'max': self.max,
                           'vary': self.vary, 'expr': self.expr,
                           'stderr': self.stderr, 'correl': self.correl,
                           'units': self.units, 'decimals': self.decimals})

    @property
    def expr(self):
        return self._expr

    @expr.setter
    def expr(self, val):
        self._ast = None
        self._expr = val

    @property
    def uvalue(self):
        """get value with uncertainties (uncertainties.ufloat)"""
        return self._uval

    @uvalue.setter
    def uvalue(self, val):
        self._uval = val

    @property
    def value(self):
        return self._getval()

    @value.setter
    def value(self, val):
        self._val = val

    def _getval(self):
        if self._larch is not None and self._expr is not None and not self.vary:
            if self._ast is None:
                self._expr = self._expr.strip()
                self._ast = self._larch.parse(self._expr)
                if self._ast is None:
                    self._larch.writer.write(self.__invalid % self._expr)
            if self._ast is not None:
                self._val = self._larch.run(self._ast, expr=self._expr)
                # self._larch.symtable.save_frame()
                # self._larch.symtable.restore_frame()

        if self.min is None: self.min = -inf
        if self.max is None: self.max =  inf
        if self.max < self.min:
            self.max, self.min = self.min, self.max

        try:
            if self.min > -inf:
               self._val = max(self.min, self._val)
            if self.max < inf:
                self._val = min(self.max, self._val)
        except(TypeError, ValueError):
            self._val = nan
        if isinstance(self._val, Parameter):
            self._val = self._val.value
        return self._val

    def setup_bounds(self):
        """set up Minuit-style internal/external parameter transformation
        of min/max bounds.

        returns internal value for parameter from self.value (which holds
        the external, user-expected value).   This internal values should
        actually be used in a fit....

        As a side-effect, this also defines the self.from_internal method
        used to re-calculate self.value from the internal value, applying
        the inverse Minuit-style transformation.  This method should be
        called prior to passing a Parameter to the user-defined objective
        function.

        This code borrows heavily from JJ Helmus' leastsqbound.py
        """
        if self.min in (None, -inf) and self.max in (None, inf):
            self._from_internal = lambda val: val
            _val  = self._val
        elif self.max in (None, inf):
            self._from_internal = lambda val: self.min - 1 + sqrt(val*val + 1)
            _val  = sqrt((self._val - self.min + 1)**2 - 1)
        elif self.min in (None, -inf):
            self._from_internal = lambda val: self.max + 1 - sqrt(val*val + 1)
            _val  = sqrt((self.max - self._val + 1)**2 - 1)
        else:
            self._from_internal = lambda val: self.min + (sin(val) + 1) * \
                                  (self.max - self.min) / 2
            _val  = arcsin(2*(self._val - self.min)/(self.max - self.min) - 1)
        return _val

    def scale_gradient(self, val):
        """returns scaling factor for gradient the according to Minuit-style
        transformation.
        """
        if self.min in (None, -inf) and self.max in (None, inf):
            return 1.0
        elif self.max in (None, inf):
            return val / sqrt(val*val + 1)
        elif self.min in (None, -inf):
            return -val / sqrt(val*val + 1)
        else:
            return cos(val) * (self.max - self.min) / 2.0

    def __hash__(self):
        return hash((self._getval(), self.min, self.max,
                     self.vary, self._expr))

    def __repr__(self):
        val = self._getval()
        if isNamedClass(val, Parameter):
            val = val._getval()
        w = []
        if self.name is not None:
            w.append("name='%s'" % self.name)

        if self.decimals is not None and val is not None:
            fmtstr = "value=%." + str(self.decimals) + "f"
            string = fmtstr % float(repr(val))
            if self.stderr is not None:
                fmtstr = " +/- %." + str(self.decimals) + "f"
                string = string + fmtstr % self.stderr
            if self.units is not None:
                string = string + " %s" % self.units
            w.append(string)
        else:
            w.append("value=%s" % repr(val))

        w.append('vary=%s' % repr(self.vary))
        if self._expr is not None:
            w.append("expr='%s'" % self._expr)
        if self.min not in (None, -inf):
            w.append('min=%s' % repr(self.min))
        if self.max not in (None, inf):
            w.append('max=%s' % repr(self.max))
        return 'param(%s)' % ', '.join(w)

    #def __new__(self, value=0, **kws): return float.__new__(self, val)

    # these are more or less straight emulation of float,
    # but using _getval() to get current value
    def __str__(self):         return self.__repr__()

    def __abs__(self):         return abs(self._getval())
    def __neg__(self):         return -self._getval()
    def __pos__(self):         return +self._getval()
    def __nonzero__(self):     return self._getval() != 0

    def __int__(self):         return int(self._getval())
    def __long__(self):        return long(self._getval())
    def __float__(self):       return float(self._getval())
    def __trunc__(self):       return self._getval().__trunc__()

    def __add__(self, other):  return self._getval() + other
    def __sub__(self, other):  return self._getval() - other
    def __div__(self, other):  return self._getval() / other
    __truediv__ = __div__

    def __floordiv__(self, other):
        return self._getval() // other
    def __divmod__(self, other): return divmod(self._getval(), other)

    def __mod__(self, other):  return self._getval() % other
    def __mul__(self, other):  return self._getval() * other
    def __pow__(self, other):  return self._getval() ** other

    def __gt__(self, other):   return self._getval() > other
    def __ge__(self, other):   return self._getval() >= other
    def __le__(self, other):   return self._getval() <= other
    def __lt__(self, other):   return self._getval() < other
    def __eq__(self, other):   return self._getval() == other
    def __ne__(self, other):   return self._getval() != other

    def __radd__(self, other):  return other + self._getval()
    def __rdiv__(self, other):  return other / self._getval()
    __rtruediv__ = __rdiv__

    def __rdivmod__(self, other):  return divmod(other, self._getval())
    def __rfloordiv__(self, other): return other // self._getval()
    def __rmod__(self, other):  return other % self._getval()
    def __rmul__(self, other):  return other * self._getval()
    def __rpow__(self, other):  return other ** self._getval()
    def __rsub__(self, other):  return other - self._getval()

    #
    def as_integer_ratio(self):  return self._getval().as_integer_ratio()
    def hex(self):         return self._getval().hex()
    def is_integer(self):  return self._getval().is_integer()
    def real(self):        return self._getval().real
    def imag(self):        return self._getval().imag
    def conjugate(self):   return self._getval().conjugate()

    def __format__(self):  return format(self._getval())
    def fromhex(self, other):  self._val = other.fromhex()

    # def __getformat__(self, other):  return self._getval()
    # def __getnewargs__(self, other):  return self._getval()
    # def __reduce__(self, other):  return self._getval()
    # def __reduce_ex__(self, other):  return self._getval()
    # def __setattr__(self, other):  return self._getval()
    # def __setformat__(self, other):  return self._getval()
    # def __sizeof__(self, other):  return self._getval()
    # def __subclasshook__(self, other):  return self._getval()

def isParameter(x):
    return (isinstance(x, Parameter) or
            x.__class__.__name__ == 'Parameter')

def param_value(val):
    "get param value -- useful for 3rd party code"
    while isinstance(val, Parameter):
        val = val.value
    return val
