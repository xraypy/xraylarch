from lib import SpecScan

spec = SpecScan(configfile='myspec.ini')
spec.filename = 'spectest.001'
spec.lup('x', -0.2, 0.2, 41, 0.25)

# spec.d2scan('x', -1, 1, 'y', 0, 1, 101, 0.25)
# 
# spec.mesh('x', 10, 10.5, 11, 'y', 0, 0.5, 11, 0.5)
# 
