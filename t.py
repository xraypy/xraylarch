import larch
import wx
import epics

larch.use_plugin_path('epics')

# wxMain = wx.App()
# a = larch.Interpreter()
from xrf_detectors import Epics_MultiXMAP, Epics_Xspress3
det = Epics_Xspress3(prefix='13QX4:', nmca=4)
det.connect()

mca1 = det.get_mca(mca=1)

print mca1
print det._xsp3.mcas

det.save_mcafile('out.mca')

        


