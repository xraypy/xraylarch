       double precision function sigma0( x)
       implicit none
       double precision  x, xsb, bena, xs_int(5)
       double precision  energa, d_prod, xsedga, tiny
       parameter(tiny=1.d-30)
       integer icount
       common /gaus/ xsb, bena, xs_int, energa, xsedga, icount
       save
c      executable code
       icount = icount-1
       sigma0 = xs_int(icount)* bena/(x*x)
       d_prod = (energa*x)**2 - bena**2
       if(abs( d_prod) .gt. tiny)
     $      sigma0 =bena * ( sigma0 * bena - xsb* energa**2)/ d_prod
       return
       end
c***********************************************************************
       double precision function sigma1( x)
       implicit none
       double precision  x, xsb, bena, xs_int(5)
       double precision  energa, xsedga, half
       parameter (half = 0.5d0)
       integer icount
       common /gaus/ xsb, bena, xs_int,
     $      energa, xsedga, icount
       save
c      executable code
       icount = icount-1
       sigma1 = half* bena**3* xs_int( icount)
     $ /( sqrt(x)*( energa**2* x**2- bena**2* x))
       return
       end
c***********************************************************************
       double precision function sigma2(x)
       implicit none
       double precision x, zero, tiny, p1, denom, eps
       double precision xsb, bena, xs_int(5), energa, xsedga
       integer icount
       common /gaus/ xsb, bena, xs_int, energa, xsedga,icount
       parameter (zero = 0, tiny = 1.d-18, eps = 1.d-5, p1 = 1.001d0)
       save
       icount=icount-1
c     code modified by chris t. chantler, may 12-1992
c     code modified by matt newville  oct 1996
       if ((abs(x).lt.tiny).or.(energa.lt.tiny)) then
          sigma2= zero
       elseif (abs(xs_int(icount)-xsb).lt.tiny) then
          sigma2=-2*xs_int(icount)*bena/x**3
       else
          denom= x**3*energa**2-bena**2/ x
          if (abs(denom).lt.eps) then
cc chantler:        sigma2=-2*xs_int(icount)*bena/x**3
             denom= x**3*(energa*p1)**2-bena**2/ x
cc             print*, ' weird point at e =  ', energa * 27.21d0
          end if
          sigma2= 2*(xs_int(icount)*(bena/x)**3/x-
     $         bena* xsb* energa**2)/ denom
       endif
       return
       end
c***********************************************************************
       double precision function sigma3( x)
       implicit none
       double precision  x, xsb, bena, xs_int(5), energa, xsedga
       integer icount
       common /gaus/ xsb,bena,xs_int, energa, xsedga,icount
       save
c      executable code
       icount = icount-1
       sigma3 = bena**3*( xs_int( icount)
     $      - xsedga* x**2)/( x**2*( x**2* energa**2- bena**2))
       return
       end
c***********************************************************************
       subroutine lgndr (index,dbb,dcc)
       implicit none
       integer index, ip
       double precision  dbb, dcc, const, d_x(2), d_a(3)
       double precision half,zero,one
       parameter(half = 0.5d0, zero = 0d0, one = 1d0)
       data d_x(1), d_x(2) /.04691007703067d0, .23076534494716d0/
       data d_a(1), d_a(2) /.11846344252810d0, .23931433524968d0/
       data d_a(3)         /.28444444444444d0/

c      executable code
c      warning! this routine has been stripped so it is only useful
c      with abs$cromer in this set of routines.
       dcc = half
       const=zero
       ip= index
c      ip limited to 1,2,3
       if ( ip .gt. 3) then
          ip   = 6 - ip
          const= -one
       end if
       dbb = d_a(ip)
       if( ip .eq. 3) return
       dcc= -const+ sign( d_x(ip), const)
       return
       end
c***********************************************************************
       double precision function gauss (sigma)
       implicit none
       integer i
       double precision  b, c, sigma, zero
       parameter (zero  = 0.d0)
       external sigma
       gauss = zero
       do 10 i=1,5
          call lgndr( i, b, c)
          gauss = gauss + b * sigma(c)
 10    continue
       return
       end
c*************************************************************
c***********************************************
c      bubble sort.  largest becomes last
       subroutine sort (n,a,b)
       implicit none
       integer i, n, j
       double precision  a(*), b(*), x, y

       do 11 i=1,n-1
          do 10 j=i+1,n
             if(a(j).lt.a(i)) then
        	x=a(j)
        	y=a(i)
        	a(i)=x
        	a(j)=y
        	x=b(j)
        	y=b(i)
        	b(i)=x
        	b(j)=y
             end if
 10       continue
 11    continue
       return
       end
c      aitken repeated interpolation
c      xlne   = abscissa at which interpolation is desired
c      xlnnrg = vector of n values of abscissa
c      xln_xs = vector of n values of ordinate
c      t      = temporary storage vector of 4*(m+1) locations)
       double precision function aknint( xlne, n, xlnnrg, xln_xs)
       implicit none
       integer n, i, ii, j
       double precision  t(20), xlne, xlnnrg(n), xln_xs( n)
c      executable code
       if(n .le. 2) then
          write(*,'(a)') ' aknint:  too few points, funct=y(1)'
          aknint = xln_xs(1)
          return
       end if
       if (xlnnrg(2) .gt. xlnnrg(1)) then
          do 10 i = 1, n
             if (xlnnrg(i) .ge. xlne) go to 30
 10       continue
       else
          do 20 i = 1, n
             if (xlnnrg(i) .le. xlne) go to 30
 20       continue
       end if
 30    continue
       ii = min(n-2, max(1, i-1))
       do 40 i= ii, ii+2
          t(i-ii+1) = xln_xs(i)
          t(i-ii+4) = xlnnrg(i)- xlne
 40    continue

       do 70 i=1,2
          do 60 j=i+1,3
             t(j) = ( t(i)*t(j+3)-t(j)*t(i+3))
     $            /( xlnnrg( j + ii - 1)- xlnnrg( i + ii - 1))
 60       continue
 70    continue
       aknint= t(3)
       return
       end
