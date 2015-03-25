#
#     == Makefile for Feff6 library ==
#
include Mk.config
include Mk.install

INSTALLNAME = feff6
STATICLIB   = $(DLLPRE)$(INSTALLNAME).a
SHAREDLIB   = $(DLLPRE)$(INSTALLNAME).$(DLLEXT)

.f.o:
	$(F77) -c $*.f

.PHONY: clean install default

default: $(SHAREDLIB)

SRC = sigms.f feff6_interfaces.c
OBJ = sigms.o feff6_interfaces.o

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


