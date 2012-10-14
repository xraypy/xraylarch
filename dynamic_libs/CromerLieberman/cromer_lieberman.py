import os
import ctypes
import ctypes.util
import numpy as np

def add_dot2path():
    """add this folder to begninng of PATH environmental variable"""
    sep = ':'
    if os.name == 'nt': sep = ';'
    paths = os.environ.get('PATH','').split(sep)
    paths.insert(0, os.path.abspath(os.curdir))
    os.environ['PATH'] = sep.join(paths)

CLLIB = None
def get_cllib():
    """make initial connection to CL dll"""
    global CLLIB
    if CLLIB is None:
        add_dot2path()
        dllpath  = ctypes.util.find_library('cldata')
        load_dll = ctypes.cdll.LoadLibrary
        if os.name == 'nt':
            load_dll = ctypes.windll.LoadLibrary
        CLLIB = load_dll(dllpath)
    return CLLIB

def f1f2(z, energies):
    """return f1/f2 pairs for an array of energies
    uses f1/f2 calculation from Cromer-Lieberman
    """
    global CLLIB
    if CLLIB is None:
        CLLIB = get_cllib()
    npts   = len(energies)
    p_z    = ctypes.pointer(ctypes.c_int(int(z)))
    p_npts = ctypes.pointer(ctypes.c_int(npts))
    p_en   = (npts*ctypes.c_double)()
    p_f1   = (npts*ctypes.c_double)()
    p_f2   = (npts*ctypes.c_double)()
    for i in range(npts):
        p_en[i] = energies[i]
    nout = CLLIB.f1f2(p_z, p_npts, p_en, p_f1, p_f2)

    if nout == 0:
        f1 = np.array([i for i in p_f1[:npts]])
        f2 = np.array([i for i in p_f2[:npts]])
    return (f1, f2)

if __name__ == '__main__':
    en = np.linspace(8000, 9200, 51)
    f1, f2 = f1f2(29, en)
    print en
    print f1
    print f2
