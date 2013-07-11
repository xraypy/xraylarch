from lib import SpecScan

s = SpecScan()
s.add_detector('fake_detector', kind=None)
s.add_motors(x = 'fake_motor1', y='fake_motor2')
s.set_scanfile('tmpout.dat')
s.ascan('x', -1, 1, 21, 0.5)
