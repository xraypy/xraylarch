import numpy as np
import lib as scan
sscan = scan.StepScan()

pos0 = scan.Positioner('13IDE:m9')
sscan.add_counter(scan.MotorCounter('13IDE:m9', label='M9.RBV'))

npts = 31

pos0.array = 70 + np.arange(npts)/20.0

sscan.add_positioner(pos0)

pos1 = scan.Positioner('13IDE:scaler1.TP')
pos1.array = 0.3  + np.arange(npts)/200.0

sscan.add_positioner(pos1)
# sscan.add_counter(scan.Counter('13IDE:scaler1.T', label='ScalerCountTime'))
sscan.add_counter(scan.Counter('13IDE:scaler1.S1', label='Scaler1Counts'))
sscan.add_detector(scan.ScalerDetector('13IDE:scaler1'))

#
sscan.add_extra_pvs((('Ring Current', 'S:SRcurrentAI.VAL'),
                     ('Ring Lifetime', 'S:SRlifeTimeHrsCC.VAL')))



sscan.breakpoints = [10, 20]

# print sscan.extra_pvs

def my_status_report(breakpoint=None):
    print 'Status Report at breakpoint %i ' % breakpoint

sscan.at_break_methods.append(my_status_report)    
    
sscan.run(filename='out1.dat')
