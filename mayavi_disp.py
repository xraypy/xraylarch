import numpy as np
import larch
import larch_plugins
from mayavi import mlab
from skimage.transform import iradon

from larch_plugins import xrmmap

map = xrmmap.GSEXRM_MapFile(filename='T:/xas_user/2017.2/Koker/Maps/sinomap_arabseed1_y_030.h5')

fe = map.return_roimap('mcasum', 'Fe Ka') 
fe = fe/fe.max()
_x = map.get_pos('Fine X')
_t = map.get_pos('Theta')

_x = _x/max(_x)
_t = _t/max(_t)

t, x= np.meshgrid(_t, _x)
mlab.surf(x, t, fe)

npts = len(_x)
cntr = 118
xslice = slice(npts-2*cntr, -1) if cntr < npts/2. else slice(0, npts-2*cntr)
tomo = iradon(fe[xslice], theta=_t, filter='shepp-logan', interpolation='linear', circle=True)


