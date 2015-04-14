import os
import larch
from larch_plugins.epics import EpicsXRFApp
os.chdir(larch.site_config.home_dir)
conf = dict(prefix='dxpMercury:', det_type='ME-4',
           is_xsp3=False, nmca=4)

EpicsXRFApp(**conf).MainLoop()
