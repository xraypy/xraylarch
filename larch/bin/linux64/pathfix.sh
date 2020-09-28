patchelf --set-rpath '$ORIGIN' feff6l feff8l_*
patchelf --set-rpath '$ORIGIN' libfeff6.so libcldata.so libxdifile.so
patchelf --set-rpath '$ORIGIN' libfeff8lpath.so libfeff8lpotph.so
patchelf --set-rpath '$ORIGIN' libgfortran.so.3 libquadmath.so.0

# libgcc_s.so.1
