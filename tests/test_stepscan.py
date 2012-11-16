import time
import numpy as np
import lib as scan
sscan = scan.StepScan()

pos0 = scan.Positioner('13IDE:m9')
sscan.add_counter(scan.MotorCounter('13IDE:m9', label='M9.RBV'))

npts = 81

pos0.array = np.linspace(70., 72.0, npts)

sscan.add_positioner(pos0)

pos1 = scan.Positioner('13IDE:scaler1.TP', label='CountTime')
pos1.array = np.linspace(0.2, 1.0, npts)

sscan.add_positioner(pos1)

sscan.add_detector(scan.ScalerDetector('13IDE:scaler1'))
sscan.add_counter(scan.Counter('13IDE:scaler1.S1', label='Scaler1Counts'))

#
# sscan.add_extra_pvs((('Ring Current', 'S:SRcurrentAI.VAL'),
#                      ('Ring Lifetime', 'S:SRlifeTimeHrsCC.VAL')))

sscan.add_extra_pvs((('Ring Current', 'Py:ao1'),
                     ('Ring Lifetime', 'Py:ao2')))

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
    time.sleep(1.2)

    # print 'Point %i/%i, npos,ndet=%i, %i, counter bufflen =  %i' % (cpt, npts, npos, ndet, bufflen)

    try:
        print cpt, ' '.join(["%10f" % c.buff[ndet_pts-1] for c in scan.counters])
    except:
        pass


sscan.messenger  = report
comments = '''This is a test scan
and this is the comment section
'''
sscan.run(filename='out1.dat', comments=comments)
