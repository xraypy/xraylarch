#!/bin/sh
# build for Mac OS X
arch='-arch i386 -arch x86_64 -arch ppc'
make clean
./configure 
make CC="gcc -O2 $arch" LINK="gcc -O2 $arch"
mv libxdifile.so libxdifile.dylib
