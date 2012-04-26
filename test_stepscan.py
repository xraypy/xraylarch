import time
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

sscan.add_detector(scan.ScalerDetector('13IDE:scaler1'))
sscan.add_counter(scan.Counter('13IDE:scaler1.S1', label='Scaler1Counts'))

#
sscan.add_extra_pvs((('Ring Current', 'S:SRcurrentAI.VAL'),
                     ('Ring Lifetime', 'S:SRlifeTimeHrsCC.VAL')))



### sscan.breakpoints = [15]

# print sscan.extra_pvs

def my_status_report(breakpoint=None):
    print 'Status Report at breakpoint %i ' % breakpoint

sscan.at_break_methods.append(my_status_report)    

def report(scan=None, cpt=0, **kws):
    npts = len(scan.positioners[0].array)
    npos_pts = len(scan.pos_actual)
    ndet_pts = len(scan.counters[0].buff)
    npos     = len(scan.pos_actual[0])
    ndet     = len(scan.counters)

    # print 'Point %i/%i, npos,ndet=%i, %i, npos_pts, ndet_pts = %i, %i' % (cpt, npts, npos, ndet, npos_pts, ndet_pts)
    time.sleep(0.7)
    print ' '.join(["%10f" % c.buff[ndet_pts-1] for c in scan.counters])

    
sscan.messenger  = report

    
sscan.run(filename='out1.dat')
