from larch import use_plugin_path
use_plugin_path('xrfmap')
from xrm_mapfile import GSEXRM_MapFile

# x = GSEXRM_MapFile('T1.h5')
# m2 = x.get_mca_area('area_005')
#
def mycallback(step, total_steps, npts):
    print 'CALLBACK reading %i pixels (step %i/%i)' % (npts, step, total_steps)
x = GSEXRM_MapFile('seedmatrix.011.h5')
m2 = x.get_mca_area('area_001', det=None,
                    callback=mycallback)

m2.save_mcafile('x3.xrf')

print m2



# COUNTS  [   9.    9.   13. ...,  514.  467.  489.]
# <MCA mca, nchans=2048, counts=453216661, realtime=0>
