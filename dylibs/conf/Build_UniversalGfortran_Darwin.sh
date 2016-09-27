#!/bin/sh

## NOTE: very outdated, and no longer neeeded

GF_VERSION=4.2.3

GF_LIBGFORTRAN=/usr/local/lib/libgfortran.2.dylib
GF_LIBGCC=/usr/local/lib/libgcc_s.1.dylib
GF_ARCH_i386=/usr/local/lib/gcc/i686-apple-darwin8/${GF_VERSION}
GF_ARCH_x86_64=/usr/local/lib/gcc/i686-apple-darwin8/${GF_VERSION}/x86_64
GF_ARCH_ppc=/usr/local/lib/gcc/powerpc-apple-darwin8/${GF_VERSION}
GF_ARCH_ppc64=/usr/local/lib/gcc/powerpc-apple-darwin8/${GF_VERSION}/ppc64

echo 'WARNING: universal binaries for Mac OS X are no longer needed.'
echo '         read script for historical details'

## mkdir -p build/F
## cd build/F
## cp -p $GF_LIBGFORTRAN $GF_LIBGCC .
## olist='crt3.o libgcc.a libgcov.a libgfortranbegin.a'
## for obj in $olist ; do
##    lipo $GF_ARCH_i386/$obj $GF_ARCH_x86_64/$obj $GF_ARCH_ppc/$obj  -output $obj  -create
## done
## cp -pr * ../../local/lib/.
