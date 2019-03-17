import os

def fix_linux_dylibs(debug=True):
    """
    fix dynamic libs on Linux with patchelf
    """

    feff_exes = ('feff6l', 'feff8l_ff2x', 'feff8l_genfmt',
                 'feff8l_pathfinder', 'feff8l_pot', 'feff8l_rdinp',
                 'feff8l_xsph')

    larchdlls = os.path.join(sys.prefix, 'share/larch/dlls/linux64')

    fixcmd = "%s/bin/patchelf --set-rpath "  % (sys.prefix)

    dylibs = ('libgcc_s.so.1','libquadmath.so.0', 'libgfortran.so.3',
              'libfeff6.so', 'libcldata.so', 'libfeff8lpath.so',
              'libfeff8lpotph.so')

    cmds = ["# commands to fix dynamic libs"]
    for lname in dylibs:
        cmds.append("%s '$ORIGIN' %s" % (fixcmd, os.path.join(larchdlls, lname)))

    for ename in feff_exes:
        cmds.append("%s %s %s/bin/%s" % (fixcmd, larchdlls, sys.prefix, ename))
    if debug:
        print("\n".join(cmds))
    else:
        for cmd in cmds:
            os.system(cmd)

fix_linux_dylibs()
