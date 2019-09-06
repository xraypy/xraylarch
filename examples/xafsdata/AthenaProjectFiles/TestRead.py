import glob
from gzip import GzipFile

from larch.io import read_athena

def get_athena_version(fname):
    ftype = 'ascii'
    try:
        fh = GzipFile(fname)
        text = fh.read()
        ftype = 'gzip'
    except:
        text = None

    if text is None:
        text = open(fname, 'r').read()

    if isinstance(text, bytes):
        text = text.decode('utf-8')
    version = 'unknown'
    for line in text[:200].split('\n'):
        line = line.lower().replace('#', '').replace('--', '').strip()
        if 'athena project file' in line:
            line = line.replace('version', '')
            line = line.replace('_____header1', '')
            line = line.replace('athena project file', '')
            words = [a.strip() for a in line.split()]
            version = words.pop().replace('"', "").replace(',', "")
            parent = words.pop()
    return (ftype, parent, version)


OutFormat = "{:30s} {:8s} {:12s} {:s}"
print(OutFormat.format('FileName', 'Type', 'Version', '# Groups'))
print('-'*60)

for fname in glob.glob('*.prj'):
    ftype, parent, version = get_athena_version(fname)
    prj = read_athena(fname, do_preedge=True, do_bkg=True, do_fft=True)
    n = "{:3d}".format(len(prj._athena_groups.keys()))
    print(OutFormat.format(fname, ftype, version, n))
