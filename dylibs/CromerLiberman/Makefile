#
#     == Makefile for Cromer-Liberman library ==
#
# you may want to customize these two items:
#
# -1- how to invoke the fortran compiler
#     -A- on systems with a "real" fortran compiler, you may want
#         to add more options or more optimaztion, but the rest
#         should be OK

include Mk.config
include Mk.install

INSTALLNAME = cldata
STATICLIB   = $(DLLPRE)$(INSTALLNAME).a
SHAREDLIB   = $(DLLPRE)$(INSTALLNAME).$(DLLEXT)

.f.o:
	$(F77) -c $*.f

.PHONY: clean install default

default: $(SHAREDLIB)

SRC = clcalc.f cromer.f crolib.f cl_f1f2.c
INC = cldata.f
OBJ = clcalc.o cromer.o crolib.o cl_f1f2.o

clcalc.o:  cldata.f

$(SHAREDLIB): $(OBJ)
	$(LINK) -o $(SHAREDLIB) $(OBJ) $(LINK_FFLAGS) $(LINK_CFLAGS)

$(STATICLIB): $(OBJ)
	$(AR) cru $(STATICLIB) $(OBJ)
	$(RANLIB) $(STATICLIB)

clean :
	rm -f $(OBJ)  $(STATICLIB) $(SHAREDLIB)

install: $(SHAREDLIB)
	cp $(SHAREDLIB) $(INSTALLDIR)/.

distrib:
	mkdir -p src/
	cp $(SRC) $(INC)  src/
	cp $(MAKEFILE) src/Makefile
	tar czvf $(INSTALLNAME)-src.tar.gz src/


