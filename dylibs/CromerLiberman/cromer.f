       subroutine cromer(iz,ener,nparms,norb,benaz,xnrg,xsc,f1,f2)
c modified from cowan-brennan routines      matt newville oct 1996
c this routine reads data for f' and f" according to an
c algorithm by cromer and liberman, given to fuoss.
c converted to direct access file by brennan
c converted to internal data 3-may-1993 smb
       implicit none
       integer        iz, irb, ipr, icount,i0,inxs, norb, nparms(24)
       double precision  benaz(24), xnrg(24,11), xsc(24,11)
       double precision  ener, f1, f2, zero, fourpi
       double precision  f1orb, f2orb, en_s(11), xs_s(11), aknint
       double precision  xlnnrg(11),xln_xs(11),en_int(5), xs_int(5)
       double precision  xsedga, f1corr, xlne, energa, bena, xsb
       double precision  var, au, kev2ry, fscinv, tiny, tinlog
       double precision  finepi, sigma0, sigma1, sigma2, sigma3, gauss
       parameter (zero=0, fourpi=12.56637061435917d0, tiny =  1.d-9)
       parameter (au = 2.80022d+7 ,kev2ry = 0.02721d0)
c finepi = 1/(4*alpha*pi**2)
       parameter (finepi = 3.47116243d0, fscinv =137.036d0 )
       common /gaus/ xsb,bena,xs_int, energa, xsedga,icount
       external sigma0,sigma1,sigma2,sigma3
       save
c      executable code
c ener is in kev
       xlne   = log(ener)
       energa = ener /  kev2ry
       f1     = zero
       f2     = zero
       tinlog = log(tiny)

c      main loop through the orbitals
       do 400 irb=1,norb
          icount= 6
          f1orb = zero
          f1corr= zero
          f2orb = zero
          xsb   = zero
          bena  = benaz(irb)
          if (nparms(irb) .eq. 11) xsedga = xsc(irb,11)/ au

c      also copy subset into second array
          do 110 ipr=6,10
             xs_int(ipr-5) = xsc(irb,ipr)/ au
             en_int(ipr-5) = xnrg(irb,ipr)
 110       continue

c   the sorting routine messes up subsequent calls with same energy
c   so copy to second array before sorting.
          do 150 ipr=1,nparms(irb)
             xs_s(ipr) = xsc(irb,ipr)
             en_s(ipr) = xnrg(irb,ipr)
 150       continue
          call sort(nparms(irb),en_s,xs_s)
          call sort(5,en_int,xs_int)
c      convert to log of energy,xsect
          do 190 ipr=1,nparms(irb)
             xlnnrg(ipr) = log(en_s(ipr))
             xln_xs(ipr) = log(max(tiny,xs_s(ipr)))
             if (xln_xs(ipr).le.tinlog) xln_xs(ipr) = zero
 190      continue
c
          if (bena .le. energa) then
             do 250 i0 = 1, nparms(irb)
                if (abs(xln_xs(i0)) .ge. tiny ) go to 255
 250         continue
 255         continue
             inxs = nparms(irb) - i0 + 1
             xsb  = exp(aknint(xlne,inxs,xlnnrg(i0),xln_xs(i0)))/au
             f2orb= fscinv * energa * xsb / fourpi
             var  = energa-bena
             if (abs(var). le. tiny) var = 1
             f1corr = - finepi * xsb * energa * log((energa+bena)/var)
          end if
c
          if((bena.gt.energa).and.(nparms(irb).eq.11)) then
             f1orb  = gauss(sigma3)
             f1corr = finepi * xsedga * bena**2 * log((-bena+energa)
     $            /(-bena-energa)) / energa
          else
             if (nparms(irb).eq.11)   then
                f1orb = gauss(sigma0)
             elseif ((nparms(irb).eq.10).and.
     $               (iz.ge.79).and.(irb.eq.1)) then
                f1orb = gauss(sigma1)
             else
                f1orb = gauss(sigma2)
             end if
          end if
          f1 = f1 + f1orb * 2 * finepi + f1corr
          f2 = f2 + f2orb
 400   continue
c      this is the end of the loop over orbits

c
c      note: the jensen correction to f' was subsequently shown to be incorrect
c      (see l. kissel and r.h. pratt, acta cryst. a46, 170 (1990))
c      and that the relativistic correction that ludwig used is also
c      wrong.  this section retained as comments for historical reasons.
c
c      jensen_cor = -0.5*float(iz)
c      1			*(energa/fscinv**2)**2
c
c      subtract relcor ala ludwig and change back to real*4
c
c      f1 = sumf1+jensen_cor-relcor(iz)
c
c      kissel and pratt give better corrections.  the relativistic correction
c      that ludwig used is (5/3)(e_tot/mc^2).  kissel and pratt say that this
c      should be simply (e_tot/mc^2), but their correction (kpcor) apparently
c      takes this into account.  so we can use the old relcor and simply add
c      the (energy independent) kpcor term:
c
       return
       end
