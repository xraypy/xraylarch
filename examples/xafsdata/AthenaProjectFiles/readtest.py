from larch.io import read_athena
from glob import glob

passed = 0
for fname in sorted(glob('*.prj')):
    print("### ", fname)
    group = read_athena(fname)
    print('read ', group, list(group.groups.keys()))
    passed += 1


print(f"Read {passed:d} Athena Project files")
