/* header file for C interface to Cromer Liberman routines */

#if defined(WIN32) || defined(_WIN32) || defined(__WIN32__)
#define _EXPORT(a) __declspec(dllexport) a _stdcall
#define _INTERN(a) a _stdcall
#else
#define _EXPORT(a) a
#define _INTERN(a) a
#endif

_EXPORT(int) f1f2(int *, int *, double *, double *, double *);
int clcalc_(int *, int *, double *, double *, double *);
