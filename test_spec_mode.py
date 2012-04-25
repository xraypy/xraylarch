import numpy as np
import lib
spec = lib.SpecScan()

spec.add_motors(x='13IDE:m9', y='13IDE:m10', z='13IDE:m11')

spec.add_detector('13IDE:scaler1', kind='scaler', use_calc=True)

spec.add_extra_pvs((('Ring Current', 'S:SRcurrentAI.VAL'),
                    ('Ring Lifetime', 'S:SRlifeTimeHrsCC.VAL')))


#spec.dscan('x', -0.1, 0.1, 11, 0.25)

#spec.a2scan('x', 10, 11, 'y', 0, 1, 11, 0.5)

spec.filename = 'mesh.dat'

spec.mesh('x', 10, 10.5, 11, 'y', 0, 0.5, 11, 0.5)
