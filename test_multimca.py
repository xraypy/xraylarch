import numpy as np
import time
import lib as scan
sscan = scan.StepScan()

pos = scan.Positioner('13IDE:m9')

pos.array = 10 + np.arange(11)/20.0

sscan.add_positioner(pos)

sscan.add_counter(scan.MotorCounter('13IDE:m9', label='M9.RBV'))
sscan.add_detector(scan.ScalerDetector('13IDE:scaler1'))
sscan.add_detector(scan.MultiMcaDetector('dxpMercury', use_full=False))

sscan.set_dwelltime(1.25)
    
#
sscan.add_extra_pvs((('Ring Current',  'S:SRcurrentAI.VAL'),
                     ('Ring Lifetime', 'S:SRlifeTimeHrsCC.VAL')))

sscan.run(filename='mca_test.dat')
