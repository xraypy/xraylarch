#include "clcalc.h"

_EXPORT(int) f1f2(int *iz, int *np, double *en, double *f1, double *f2) {
  int ret;
  ret = clcalc_(iz, np, en, f1, f2);
  return ret;
}
