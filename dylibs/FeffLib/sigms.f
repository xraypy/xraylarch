       double precision function sig2_corrdebye(natoms, tk, theta,
     $     rnorm, x, y, z, atwt)
c
c  copyright 2012  matt newville
c
c arguments:
c    natoms  *int, lengths for x, y, z, atwt        [in]
c    tk      *double, sample temperature (K)        [in]
c    theta   *double, Debye temperature (K)         [in]
c    rnorm   *double, Norman radius (Ang)           [in]
c    x       *double, array of x coord (Ang)        [in]
c    y       *double, array of y coord (Ang)        [in]
c    x       *double, array of z coord (Ang)        [in]
c    atwt    *double, array of atomic_weight (amu)  [in]
c ouput:
c    sig2_cordby  double, calculated sigma2
c
c Note:
c     natoms must be >= 2.
c
c  copyright 1993  university of washington
c                  john rehr, steve zabinsky, matt newville
c
c  the following routines calculate the debye-waller factor for a
c  path based on the temperature, debye temperature, average
c  norman radius, atoms in the path, and their positions.
c  these routines come courtesy of jj rehr and si zabinsky.
c  i changed them a bit.   matt n
c-------------------------------------------------------------------
c
c  from s i zabinsky.
c  inputs:
c       tk      temperature in degrees k
c       theta   debye temp in degrees k
c       rs      average wigner seitz or norman radius in bohr
c                     averaged over entire problem:
c                     (4pi/3)*rs**3 = sum( (4pi/3)rnrm**3 ) / n
c                     (sum is over all atoms in the problem)
c       nleg    nlegs in path
c       rat     positions of each atom in path (in bohr)
c       iz      atomic number of each atom in path
c output:
c       sig2    debye waller factor
c  notes:
c     all units of distance in this routine are angstroms
c     there are nleg atoms including the central atom.
c     index 0 and index nleg both refer to central atom.
       implicit none
       integer          natoms, i0, i1, j0, j1
       double precision tk, theta, rnorm, sig2
       double precision ri0j0, ri1j1, ri1j0, ri0i1, rj0j1, ri0j1
       double precision ci0j0, ci1j1, ci1j0, ci0j1, sig2ij
       double precision ridotj, corrfn, dist
       double precision  x(*), y(*), z(*), atwt(*)
       external dist, corrfn
c
       sig2 = 0.d0
       do 800 i0 = 1, natoms
          i1 = 1 + mod(i0, natoms)
          do 800 j0 = i0, natoms
             j1 = 1 + mod(j0, natoms)
c  calculate r_i-r_i-1 and r_j-r_j-1 and the rest of the
c  distances, and get the partial cosine term:
c       cosine(i,j) = r_i.r_j / ((r_i0- r_i-1) * (r_j - r_j-1))
           ri0j0  = dist(x(i0), y(i0), z(i0), x(j0), y(j0), z(j0))
           ri1j1  = dist(x(i1), y(i1), z(i1), x(j1), y(j1), z(j1))
           ri0j1  = dist(x(i0), y(i0), z(i0), x(j1), y(j1), z(j1))
           ri1j0  = dist(x(i1), y(i1), z(i1), x(j0), y(j0), z(j0))
           ri0i1  = dist(x(i0), y(i0), z(i0), x(i1), y(i1), z(i1))
           rj0j1  = dist(x(j0), y(j0), z(j0), x(j1), y(j1), z(j1))
           ridotj = ((x(i0) - x(i1)) * (x(j0) - x(j1)) +
     $               (y(i0) - y(i1)) * (y(j0) - y(j1)) +
     $               (z(i0) - z(i1)) * (z(j0) - z(j1)) )
c
c  call corrfn to get the correlations between atom pairs
           ci0j0 = corrfn(ri0j0, theta, tk, atwt(i0), atwt(j0), rnorm)
           ci1j1 = corrfn(ri1j1, theta, tk, atwt(i1), atwt(j1), rnorm)
           ci0j1 = corrfn(ri0j1, theta, tk, atwt(i0), atwt(j1), rnorm)
           ci1j0 = corrfn(ri1j0, theta, tk, atwt(i1), atwt(j0), rnorm)
c
c  combine outputs of corrfn to give the debye-waller factor for
c  this atom pair. !! note: don't double count (i.eq.j) terms !!!
           sig2ij = ridotj*(ci0j0 + ci1j1 - ci0j1 - ci1j0)/(ri0i1*rj0j1)
           if (j0.eq.i0) sig2ij = sig2ij / 2.d0
           sig2 = sig2 + sig2ij
 800   continue
       sig2_corrdebye = sig2/2.d0
       return
c  end subroutine sig2_corrdebye
       end
       double precision function corrfn(rij, theta, tk, am1, am2, rs)
c
c  copyright 1993  university of washington
c                  john rehr, steve zabinsky, matt newville
c
c  subroutine calculates correlation function
c  c(ri, rj) = <xi xj> in the debye approximation
c
c            = (1/n)sum_k exp(ik.(ri-rj)) (1/sqrt(mi*mj))*
c                              (hbar/2w_k)*coth(beta hbar w_k/2)
c
c            = (3kt/mu w_d**2) * sqrt(mu**2/mi*mj) * int
c  where :
c       x        k_d*r (distance parameter)  r distance in angstroms
c       theta    debye temp in degrees k
c       tk       temperature in degrees k
c       temper   theta / tk = hbar omegad/kt
c       k_d      debye wave number = (6*pi**2 n/v)
c       n/v      free electron number density = 1/(4pi/3rs**3)
c       rs       wigner seitz or norman radius in bohr
c       ami      atomic mass at sites i in amu
c       amj      atomic mass at sites j in amu
c       int      int_0^1 (temper/x) dw sin(wx)coth(w*temper/2)
c
c  solution by numerical integration
c
c  parameters pi, bohr, con
c  con=hbar**2/kb*amu)*10**20   in ang**2 units
c    k_boltz = 8.6173324e-5  # [eV / K]
c    amu     = 931.494061e6  # [eV / (c*c)]
c    hbarc   = 1973.26938    # [eV * A]
c    bohr    = 0.52917721    # [A]
c conh = (3/2.)* hbar**2 / (kb*amu) ~= 72.76
c conr = (9*pi/2)**(1/3.0) / bohr   ~=  4.57
       implicit none
       double precision rs, theta, tk,  rij, rx, tx, am1, am2
       double precision conr, conh, rmass, debint
       parameter (conh = 72.7630804732553d0, conr = 4.5693349700844d0)
       external debint
c
c  theta in degrees k, t temperature in degrees k
       rx     = conr  * rij / rs
       tx     = theta / tk
       rmass  = theta * sqrt(am1 * am2)
       corrfn = conh  * debint(rx, tx) / rmass
       return
c  end subroutine corrfn
       end
       double precision function debfun(w, rx, tx)
c
c  copyright 1993  university of washington
c                  john rehr, steve zabinsky, matt newville
c
c  debfun = (sin(w*rx)/rx) * coth(w*tx/2)
c
       implicit none
       double precision  wmin, argmax, w, emwt
       parameter (wmin = 1.d-20, argmax = 50.d0)
       double precision rx, tx

c  allow t = 0 without bombing
       debfun = 2 / tx
       if (w.gt.wmin) then
          debfun = w
          if (rx.gt.0) debfun = sin(w*rx) / rx
          emwt   = exp(-min(w*tx,argmax))
          debfun = debfun * (1 + emwt) / (1 - emwt)
       end if
       return
c  end function debfun
       end
       double precision function debint (rx, tx)
c
c  copyright 1993  university of washington
c                  john rehr, steve zabinsky, matt newville
c
c  subroutine calculates integrals between [0,1]  b = int_0^1 f(z) dz
c  by trapezoidal rule and binary refinement  (romberg integration)
c  coded by j rehr (10 feb 92)   see, e.g., numerical recipes
c  for discussion and a much fancier version
c-----------------------------------------------
c     del=dz  itn=2**n tol=1.e-5
c     starting values
c      implicit double precision (a-h,o-z)
c     error is approximately 2**(-2n) ~ 10**(-.6n)
c     so nmax=10 implies an error of 1.e-6
c
       implicit none
       integer  nmax, n, itn, i
       double precision tol, zero, one, two, three, debfun
       double precision rx, tx
       parameter(nmax = 12, tol = 1.d-9)
       parameter(zero=0.d0, one=1.d0, two=2.d0, three=3.d0)
       double precision del, bn, bo, zi, sum, bnp1
       external debfun
c
       itn = 1
       del  = one
       debint = zero
       bn   = (debfun(zero,rx,tx) + debfun(one,rx,tx)) /2
       bo   = bn
       do 40 n = 1, nmax
c  nth iteration
c  b_n+1=(b_n)/2+deln*sum_0^2**n f([2n-1]deln)
         del = del / two
         sum = zero
         do 20 i= 1, itn
            zi  = (two * i - 1) * del
            sum = sum + debfun(zi,rx,tx)
 20      continue
c     bnp1=b_n+1 is current value of integral
c     cancel leading error terms b=[4b-bn]/3
c     note: this is the first term in the neville table - remaining
c           errors were found too small to justify the added code
         bnp1   = del * sum + (bn / two)
         debint = (4 * bnp1 - bn)/three
         if (abs( (debint - bo) / debint).lt.tol) goto 45
         bn   = bnp1
         bo   = debint
         itn  = itn * 2
 40    continue
 45    continue
       return
c end function debint
       end
       double precision function dist(x0, y0, z0, x1, y1, z1)
c  find distance between cartesian points (x, y, z)0 and (x, y, z)1
       double precision x0, y0, z0, x1, y1, z1
       dist = sqrt((x0-x1)**2 + (y0-y1)**2 + (z0-z1)**2)
       return
c  end function dist
       end
