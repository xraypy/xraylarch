/* header file for C interface to Feff6 routines */

#if defined(WIN32) || defined(_WIN32) || defined(__WIN32__)
#define _EXPORT(a) __declspec(dllexport) a _stdcall
#define _INTERN(a) a _stdcall
#else
#define _EXPORT(a) a
#define _INTERN(a) a
#endif

_EXPORT(double) sigma2_debye(int *, double *, double *, double *, double *, double *, double *, double *);
double sig2_corrdebye_(int *, double *, double *, double *, double *, double *, double *, double *);
