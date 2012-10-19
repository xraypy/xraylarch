#!/usr/bin/env python
# models for debye-waller factors for xafs

def sigma2_eins(t, teins, _larch=None):
    """calculate XAFS sigma2 using the Einstein model
    for the 'current path'"""

fortrancode = """
subroutine eins(x, nx, y, ny, ierr)
c
c calculate debye waller in einstein model
c  inputs
c     x  = theta on input, sigma2 on output
c     y  = temp
c
c  calculate sigma^2 in the eisntein model inputs:
c  returned:
c    x      sigma squared [AA^2]
c                = factor / (theta*rmass*tanh(theta/2t))
c    with factor = hbarc*hbarc/(two * boltz * amu2ev)
       integer function nptstk( n1, n2 )
c   number of vector points for a two-component math operation:
c   n1 = min(n1, n2) unless either n1 or n2 = 1, which
c   means one of the components is a constant, and
c   should be applied to all elements of vector 2
c
c  copyright (c) 1998  matt newville
c
       integer n1, n2
       nptstk = min ( n1, n2 )
       if ( (n1.le.1).or.(n2.le.1) ) nptstk = max ( n1, n2 )
       return
c  end function nptstk
       end


c
c  copyright (c) 1998  matt newville
       include 'consts.h'
       include 'arrays.h'
       include 'fefdat.h'
       include 'pthpar.h'
       integer   nx, ny, ierr, i, ipth, nx1, ny1, nptstk, ipt
       integer  u2ipth, inpath, jfeff
       double precision  x(*), y(*), tmp, getsca, theta, tk
       double precision  out(maxpts), a
       double precision small, big, factor, rminv, at_weight
       parameter(factor = 24.25423371d0, small =1.d-5, big =1.d10)
       external  getsca, at_weight, nptstk, u2ipth
       ierr  = -1

       nx1  = nx
       ny1  = ny
       nx   = nptstk (nx1, ny1)
       ipth = max(1, int ( getsca('path_index',0)))
c  construct reduced mass (in amu) using function at_weight
       inpath = u2ipth(max(1, ipth))
       rminv  = zero
       jfeff  = jpthff(inpath)
       do 50 i = 1, nlgpth(jfeff)
          a     = at_weight( izpth(i, jfeff))
          rminv = rminv +  one /max(one, a)
  50   continue
       rminv  = factor*max(small, min(big, rminv))
c
c       print*, ' eins: ', rminv, nx, ipth, x(1), y(1), y(2)
c       print*,  inpath, jfeff, nlgpth(jfeff), 1./rminv
       do 100 ipt = 1, nx
          ix     = min(nx1, ipt)
          iy     = min(ny1, ipt)
          theta  = max(small, min(big, x(ix)))
          tk     = max(small, min(big, y(iy)))
          out(ipt) = zero
          ierr   = 0
c evaluate sigma2 in einstein model, and overwrite x
          if (ipth.ne.0) then
             out(ipt)= rminv/(tanh(theta/(2*tk))*theta)
          endif
 100   continue
       do 120 ipt = 1, nx
          x(ipt) = out(ipt)
 120   continue
       return
c end subroutine eins
       end

"""
