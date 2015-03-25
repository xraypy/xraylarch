#
# Makefile for XDIFile C library
#

include Mk.config
include Mk.install

INSTALLNAME = xdifile
STATICLIB   = $(DLLPRE)$(INSTALLNAME).a
SHAREDLIB   = $(DLLPRE)$(INSTALLNAME).$(DLLEXT)

.f.o:
	$(F77) -c $*.f

.PHONY: clean install default

default: $(SHAREDLIB)

LINK_FFLAGS  =
LINK         = gcc -O2 $(ARCH_TARGS) -fPIC -shared
XDIHEADERS = strutil.h xdifile.h

OBJ  = xdifile.o strutil.o slre.o

SHARED = $(CCOPTS) -shared
LINKXDIF = -L$(libdir) -L. -lxdifile

strutil.o: strutil.h
xdifile.o: xdifile.h strutil.h slre.h
slre.o:  slre.h

$(SHAREDLIB): $(OBJ)
	@rm -f $@
	$(LINK) -o $(SHAREDLIB) $(OBJ) $(LINK_FFLAGS) $(LINK_CFLAGS)

$(STATICLIB): $(OBJ)
	$(AR) cru $(STATICLIB) $(OBJ)
	$(RANLIB) $(STATICLIB)

clean :
	rm -f $(OBJ)  $(STATICLIB) $(SHAREDLIB)

install: $(SHAREDLIB)
	cp $(SHAREDLIB) $(INSTALLDIR)/.
