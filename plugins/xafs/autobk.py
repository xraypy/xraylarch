import numpy as np
import sys, os

import larch

sys.path.insert(0, os.path.join(larch.site_config.sys_plugins_dir, 'xafs'))
from xafsft import ftwindow, xafsft_fast

#
def splfun(e, y, xlarch=None):
    print 'hello from spline function'
    print ftwindow


def registerLarchPlugin():
    return ('_xafs', {'splfun': splfun})

