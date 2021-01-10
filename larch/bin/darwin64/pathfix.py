import os
import os.path
pjoin = os.path.join

def fix_darwin_dylibs(debug=True):
    """
    fix dynamic libs on Darwin with install_name_tool
    """
    itool = '/usr/bin/install_name_tool'
    orig_gfortran_dir = '/usr/local/gfortran/lib'
    orig_gfortran_dir = '/usr/local/opt/gcc/lib/gcc/10/'
    
    gfortran_libs = ('libgcc_s.1.dylib','libquadmath.0.dylib',
                     # 'libgfortran.3.dylib',
                     'libgfortran.5.dylib')                     

    feff_libs = ('libfeff6.dylib', 'libcldata.dylib',
                 'libfeff8lpath.dylib', 'libfeff8lpotph.dylib')

    feff_exes = ('feff6l', 'feff8l_ff2x', 'feff8l_genfmt',
                 'feff8l_pathfinder', 'feff8l_pot', 'feff8l_rdinp',
                 'feff8l_xsph')

    cmds = ["# commands to fix dynamic libs"]

    for name in gfortran_libs + feff_libs:
        cmds.append('%s -id "@loader_path/./%s" %s' % (itool, name, name))

    cmds.append('# now change libs and exes to point to local versions ')

    for name in gfortran_libs + feff_libs + feff_exes:
        for gname in gfortran_libs:
            if gname != name:
                old = pjoin(orig_gfortran_dir, gname)
                new = '"@loader_path/./%s"' % gname
                cmds.append("%s -change %s %s %s" % (itool, old, new, name))

    if debug:
        print("\n".join(cmds))
    else:
        for cmd in cmds:
            os.system(cmd)

fix_darwin_dylibs()
