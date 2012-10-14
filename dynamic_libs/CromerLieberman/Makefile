#
#     == Makefile for Cromer-Liberman library ==
#
# you may want to customize these two items:
#
# -1- how to invoke the fortran compiler
#     -A- on systems with a "real" fortran compiler, you may want
#         to add more options or more optimaztion, but the rest
#         should be OK

INSTALLDIR= /usr/local/lib/

# Mac OS X 10.6.8 build
F77 = gfortran -O2 -arch i386 -arch x86_64 -mmacosx-version-min=10.5 -isysroot/Developer/SDKs/MacOSX10.5.sdk -fPIC -Wall
AR     = ar
RANLIB = ranlib
CLLIB  = libcldata.a
SHAREDLIB = libcldata.dylib
CC   = cc -O2 -arch i386 -arch x86_64
LINK = gcc -O2 -arch i386 -arch x86_64 -mmacosx-version-min=10.5 -isysroot/Developer/SDKs/MacOSX10.5.sdk -fPIC -shared
LINK_FLAGS = -L/Users/Newville/Codes/ifeffit/local/lib -lgfortran -lgfortranbegin

.f.o:
	$(F77) -c $*.f

.PHONY: clean install default

default: $(SHAREDLIB)

SRC = clcalc.f cromer.f crolib.f cl_f1f2.c
INC = cldata.f
OBJ = clcalc.o cromer.o crolib.o cl_f1f2.o

clcalc.o:  cldata.f

$(SHAREDLIB): $(OBJ)
	$(LINK) -o $(SHAREDLIB) $(OBJ) $(LINK_FLAGS)

$(CLLIB): $(OBJ)
	$(AR) cru $(CLLIB) $(OBJ)
	$(RANLIB) $(CLLIB)

clean :
	rm -f $(OBJ)  $(CLLIB) $(SHAREDLIB)

install: $(CLLIB) $(SHAREDLIB)
	cp $(CLLIB) $(INSTALLDIR)/.
	cp $(SHAREDLIB) $(INSTALLDIR)/.

distrib:
	mkdir -p src/
	cp $(SRC) $(INC)  src/
	cp $(MAKEFILE) src/Makefile
	tar czvf CLlib.tar.gz src/


