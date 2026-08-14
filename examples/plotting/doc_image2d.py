## examples/plotting/doc_image2d.py
import numpy  as np
from wxmplot.interactive import imshow

def gauss2d(x, y, x0, y0, sx, sy):
    return np.outer(np.exp(-(((y-y0)/float(sy))**2)/2),
                    np.exp(-(((x-x0)/float(sx))**2)/2))

ny, nx = 350, 400
ix = np.arange(nx)
iy = np.arange(ny)
x  =  ix / 10.
y  = -2 + iy / 10.0

dat = 0.2 + (0.05*np.random.random(size=nx*ny).reshape(ny, nx) +
             2.0*gauss2d(ix, iy, 190,   176,  57,  69))

imshow(dat, x=x, y=y, colormap='coolwarm')

## end of examples/plotting/doc_image2d.py
