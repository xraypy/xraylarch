from larch  import use_plugin_path
use_plugin_path('epics')
from xspress3 import Xspress3

x = Xspress3('13QX4:')


x.select_rois_to_save(('Mn Ka', 'Fe Ka', 'Ca Ka'))

print x._save_rois
