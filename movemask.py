import numpy as np

m1 = np.ones((2, 3)).astype(bool)

out = np.zeros((7, 8)).astype(bool)

xoff = 5
yoff = 5

ym, xm = m1.shape
for iy in range(ym):
    out[iy+yoff, xoff:xoff+xm] = m1[iy]


print out
