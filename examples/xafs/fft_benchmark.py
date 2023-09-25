from time import time
import numpy as np
fft_numpy =  np.fft.fft

fft_mkln = fft_mkls = fft_ws = fft_wp = fft_wn = None

try:
    import mkl_fft
    from mkl_fft.interfaces.numpy_fft import fft as fft_mkln
    from mkl_fft.interfaces.scipy_fft import fft as fft_mkls
except ImportError:
    print("mkl not available")

try:
    from pyfftw.interfaces.scipy_fft import fft as fft_ws
    from pyfftw.interfaces.scipy_fftpack import fft as fft_wp
    from pyfftw.interfaces.numpy_fft import fft as fft_wn
except:
    print("pyfftw not available")

from scipy.fftpack import fft as fft_pack
from scipy.fft import fft as fft_scipy

from larch.io import read_ascii
from larch.xafs import pre_edge, autobk, xftf, xftf_prep


METHODS = {}
for key, val in {'numpy': fft_numpy, 'scipy': fft_scipy,
                 'fftpack': fft_pack,
                 'mkl_numpy': fft_mkln, 'mkl_scipy': fft_mkls,
                 'fftw_numpy': fft_wn, 'fftw_scipy': fft_ws,
                 'fftw_pack': fft_wp}.items():

    if callable(val):
        METHODS[key] = val

fname = '../xafsdata/feo_rt1.xdi'
dat = read_ascii(fname, labels='energy mu i0')

pre_edge(dat)
autobk(dat, rbkg=0.9, kweight=2)

xftf(dat, kmin=2, kmax=13, dk=3, window='hanning', kweight=2)

# plot_chir(dat, win=2)


xk = dat.k

xchi, win = xftf_prep(dat.k, dat.chi, kmin=2, kmax=13, dk=3, dk2=3,
                      kstep=0.05, window='hanning', kweight=2)

nfft = 2048
kstep = 0.05
rstep = np.pi /(nfft*kstep)

cchi = np.zeros(nfft, dtype='complex128')
cchi[0:len(xchi)] = xchi*win
r    = rstep * np.arange(nfft//2)

rscale = kstep/np.sqrt(np.pi)
results = {}
for key in METHODS:
    results[key] = None

out = {}
for key in METHODS:
    out[key] = []

#warm up
for name, meth in METHODS.items():
    for i in range(5):
        t0 = time()
        chir = rscale * meth(cchi)
        results[name] = chir.real

for name, meth in METHODS.items():
    for i in range(50):
        t0 = time()
        for j in range(25):
            chir = rscale * meth(cchi)
        out[name].append(1e4*(time() -t0))


k,m,s,x = 'Method', 'Mean', 'Std', 'Max'
print(f"{k:10s} :  {m:8s}   {s:8s} {x:8s}")
for k, v in out.items():
    vn = np.array(v)
    print(f"{k:10s} :  {vn.mean():8.3f}   {vn.std():8.3f} {vn.max():8.3f}")

print("done")
