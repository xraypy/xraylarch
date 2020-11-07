patchelf --set-rpath '$ORIGIN' libfeff6.so libcldata.so libxdifile.so

for F in libfeff6.so libcldata.so libxdifile.so ; do
  patchelf --replace-needed libgcc_s.so.1 libgcc_s_f8.so $F
  patchelf --replace-needed libquadmath.so.0 libquadmath_f8.so $F
  patchelf --replace-needed libgfortran.so.3 libgfortran_f8.so $F
done
# libgcc_s.so.1
