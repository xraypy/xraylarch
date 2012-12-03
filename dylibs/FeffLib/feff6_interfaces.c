#include <stdio.h>
#include <stdlib.h>
#include "feff6_interfaces.h"

_EXPORT(double) sigma2_debye(int *natoms, double *tk, double *theta, double *rnorm,
                          double *x, double *y, double *z, double *atwt) {
  return sig2_corrdebye_(natoms, tk, theta, rnorm, x, y, z, atwt);
}


