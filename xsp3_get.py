from larch import use_plugin_path
use_plugin_path('epics')
from xrf_detectors import Epics_Xspress3

d = Epics_Xspress3('13QX4:', nmca=4)

mca = d.get_mca(mca=1)
print len(mca.energy)
print len(mca.counts)


