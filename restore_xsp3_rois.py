from larch  import use_plugin_path
use_plugin_path('epics')
from xspress3 import Xspress3

x = Xspress3('13QX4:')

out = x.roi_calib_info()


print '\n'.join(out)
#x.restore_rois('SAVEME_XSP3.roi')
#
#x.copy_rois_to_savearrays(('Mn Ka', 'Fe Ka', 'Ca Ka'))
