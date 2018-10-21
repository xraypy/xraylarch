#!/usr/bin/env python
import time
from datetime import datetime
from collections import OrderedDict
from .paths import uname, nativepath, get_homedir
from .debugtime import debugtime
from .closure import Closure
from .strutils import (fixName, isValidName, isNumber, bytes2str,
                      isLiteralStr, strip_comments, find_delims, version_ge)

from .mathutils import (linregress, polyfit, realimag, as_ndarray,
                        complex_phase, deriv, interp, interp1d,
                        remove_dups, remove_nans2, index_of,
                        index_nearest, savitzky_golay, smooth, boxcar)

from .lineshapes import (gaussian, lorentzian, voigt, pvoigt, hypermet,
                         pearson7, lognormal, gammaln,
                         breit_wigner, damped_oscillator,
                         expgaussian, donaich, skewed_voigt,
                         students_t, logistic, erf, erfc, wofz)

def isotime(t=None):
    if t is None:
        t = time.time()
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(t))
