       integer function clcalc(iz, npts, energy, fp, fpp)
c cromer-libermann calculation of anomalous scattering factors
c arguments:
c   iz      atomic number of element                       [in]
c   npts    number of elements in energy array             [in]
c   energy  array of energies at which to calculate f'/f'' [in]
c   fp      real part of anomalous scattering   (f')       [out]
c   fpp     imag part of anomalous scattering   (f'')      [out]
c
c notes:
c   1  energy array is in eV
c   2  this code is based on, and modified from the cowan-brennan
c      routines.  data statements were simplified and rearranged,
c      code was cleaned up to be more in keeping with f77 standard
c
c  matthew newville oct 1996
       implicit none
       integer  iz, npts
       integer  i, j, k, nxpts, maxpts
       integer  nparms(92,24), norb(92), nparmz(24), norbz
       parameter  (maxpts = 65536)
       double precision  binden(92,24), xnrg(92,24,11), xsc(92,24,11)
       double precision  benaz(24),    xnrgz(24,11),   xscz(24,11)
       double precision  relcor(92), kpcor(92), xnrdat(5), kev2ry
       double precision  energy(maxpts), fp(maxpts), fpp(maxpts)
       double precision  ener, f1, f2
       parameter (kev2ry = 0.02721d0)
       include "cldata.f"

       clcalc = 0
c  initialize the trivial parts of xnrg:
c  (non-trivial parts are given in the data statements above)
       if (iz .gt. 92) return
       nxpts = min(maxpts, npts)
       norbz = norb(iz)
       do 50 k = 1, 5
          do 30 j = 1, norbz
             xnrg(iz,j,k) = xnrdat(k)
 30       continue
 50    continue
       if (iz.gt.3) then
c look-up coefficients for this element
          do 100 i = 1, 24
             nparmz(i) = nparms(iz,i)
             benaz(i)  = binden(iz,i)/ kev2ry
             do 80 j = 1, 11
                xnrgz(i,j) = xnrg(iz,i,j)
                xscz(i,j)  = xsc(iz,i,j)
 80          continue
 100      continue
c calculate fp and fpp for each energy point
          do 200 i = 1, nxpts
             ener = energy(i) / 1000
             call cromer(iz,ener,nparmz,norbz,benaz,xnrgz,xscz,f1,f2)
             fp(i)  = f1 - relcor(iz) + kpcor(iz)
             fpp(i) = f2
 200      continue
       end if
       return
       end
