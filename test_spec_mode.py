import numpy as np
import lib
spec = lib.SpecScan()

spec.read_config('myspec.ini')
# add_motors(x='13IDE:m9', y='13IDE:m10', z='13IDE:m11')
# spec.add_detector('13IDE:scaler1', kind='scaler', use_calc=True)
# spec.add_counter('13IDE:scaler1.S1', label='raw scalertime')
# spec.add_counter('Py:ao1', label='foo')
# spec.add_detector('dxpMercury:', kind='med', use_full=False)

# spec.add_extra_pvs((('Ring Current', 'S:SRcurrentAI.VAL'),
#                    ('Ring Lifetime', 'S:SRlifeTimeHrsCC.VAL')))

spec.filename = 'spectest.001'

spec.lup('x', -0.2, 0.2, 41, 0.25)

# spec.d2scan('x', -1, 1, 'y', 0, 1, 101, 0.25)
# 
# spec.mesh('x', 10, 10.5, 11, 'y', 0, 0.5, 11, 0.5)
# 
