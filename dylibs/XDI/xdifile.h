/* This file is free and unencumbered software released into the public domain. */
/*                                                                              */
/* Anyone is free to copy, modify, publish, use, compile, sell, or              */
/* distribute this software, either in source code form or as a compiled        */
/* binary, for any purpose, commercial or non-commercial, and by any            */
/* means.                                                                       */
/*                                                                              */
/* In jurisdictions that recognize copyright laws, the author or authors        */
/* of this software dedicate any and all copyright interest in the              */
/* software to the public domain.                                               */
/*                                                                              */
/* THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,              */
/* EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF           */
/* MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.       */
/* IN NO EVENT SHALL THE AUTHORS BE LIABLE FOR ANY CLAIM, DAMAGES OR            */
/* OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE,        */
/* ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR        */
/* OTHER DEALINGS IN THE SOFTWARE.                                              */

#if defined(WIN32) || defined(_WIN32) || defined(__WIN32__)
#define _EXPORT(a) __declspec(dllexport) a _stdcall
#else
#define _EXPORT(a) a
#endif

#include <math.h>

#define XDI_VERSION  "1.1.0"   /* XDI version marker */

#define MAX_COLUMNS 128  /* maximum number of supported data columns */

typedef struct {
  long nmetadata;        /* number of metadata family/key/val metadata */
  long narrays;          /* number of arrays */
  long npts;             /* number of data points for all arrays */
  long narray_labels;    /* number of labeled arrays (may be < narrays) */
  long nouter;           /* number of points in outer scan */
  long error_lineno;     /* line numberfor any existing error */
  double dspacing;       /* monochromator d spacing */
  char *xdi_libversion;  /* XDI version of library */
  char *xdi_version;     /* XDI version string from file*/
  char *extra_version;   /* Extra version strings from first line of file */
  char *filename;        /* name of file */
  char *element;         /* atomic symbol for element */
  char *edge;            /* name of absorption edge: "K", "L1", ... */
  char *comments;        /* multi-line, user-supplied comment */
  char *error_line;      /* text of line with any existing error */
  char *error_message;
  char **array_labels;   /* labels for arrays */
  char *outer_label;     /* labels for outer array */
  char **array_units;    /* units for arrays */
  char **meta_families;  /* family for metadata from file header */
  char **meta_keywords;  /* keyword for metadata from file header */
  char **meta_values;    /* value for metadata from file header */
  double **array;        /* 2D array of all array data */
  double *outer_array;   /* array of outer breakpoints for multi-dimensional data */
  long  *outer_breakpts; /* array of breakpoints for outer array */

} XDIFile;

_EXPORT(int)  XDI_readfile(char *filename, XDIFile *xdifile) ;
_EXPORT(void) XDI_writefile(XDIFile *xdifile, char *filename) ;
_EXPORT(int)  XDI_get_array_index(XDIFile *xdifile, long n, double *out);
_EXPORT(int)  XDI_get_array_name(XDIFile *xdifile, char *name, double *out);
_EXPORT(int)  XDI_required_metadata(XDIFile *xdifile);
_EXPORT(int)  XDI_recommended_metadata(XDIFile *xdifile);
_EXPORT(int)  XDI_defined_family(XDIFile *xdifile, char *family);
_EXPORT(int)  XDI_validate_item(XDIFile *xdifile, char *family, char *name, char *value);
int XDI_validate_facility(XDIFile *xdifile, char *name, char *value);
int XDI_validate_mono(XDIFile *xdifile, char *name, char *value);
int XDI_validate_sample(XDIFile *xdifile, char *name, char *value);
int XDI_validate_scan(XDIFile *xdifile, char *name, char *value);
int XDI_validate_column(XDIFile *xdifile, char *name, char *value);
int XDI_validate_element(XDIFile *xdifile, char *name, char *value);

_EXPORT(void) XDI_cleanup(XDIFile *xdifile, long err);

/* Tokens used in XDI File */

#define TOK_VERSION    "XDI/"            /* version marker in file -- required on line 1 */
#define TOK_COMM       "#"               /* comment character, at start of line */
#define TOK_DELIM      ":"               /* delimiter between metadata name and value */
#define TOK_DOT        "."               /* delimiter between metadata family and key */
#define TOK_EDGE       "element.edge"    /* absorbption edge name */
#define TOK_ELEM       "element.symbol"  /* atomic symbol of absorbing element */
#define TOK_COLUMN     "column."         /* column label (followed by integer <= 64) */
#define TOK_DSPACE     "mono.d_spacing"  /* mono d_spacing, in Angstroms */
#define TOK_TIMESTAMP  "scan.start_time" /* scan time */
#define TOK_TIMESTART  "scan.start_time" /* scan time */
#define TOK_TIMEEND    "scan.end_time"   /* scan time */
#define TOK_USERCOM_0  "///"             /* start multi-line user comment */
#define TOK_USERCOM_1  "---"             /* end multi-line user comment */
#define TOK_COL_ENERGY "energy"          /* name of energy column */
#define TOK_COL_ANGLE  "angle"           /* name of angle column */
#define TOK_OUTER_VAL  "outer.value"     /* value for outer scan position */
#define TOK_OUTER_NAME "outer.name"      /* name for outer scan position */

#define FAMILYNAME "^[ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz_][ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz_0123456789]+$"
#define KEYNAME    "^[ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz_0123456789]+$"

/* #define FAMILYNAME "(?i)^[a-z_][a-z0-9_]+$" */
/* #define KEYNAME    "(?i)^[a-z0-9_]+$" */

#define DATALINE "^([ \\t]*[-+]*?[0-9\\.])"

/* Notes:
   1. The absorption edge must be one of those listed in ValidEdges below
   2. The element symbol must be one of those listed in ValidElems below
*/
static char *ValidEdges[] =
  {"K", "L", "L1", "L2", "L3",
   "M", "M1", "M2", "M3", "M4", "M5",
   "N", "N1", "N2", "N3", "N4", "N5", "N6", "N7",
   "O", "O1", "O2", "O3", "O4", "O5", "O6", "O7"};

/* "P", "P1", "P2", "P3", "P4", "P5", "P6", "P7" */

static char *ValidElems[] =
  {"H",  "He", "Li", "Be", "B",  "C",  "N",  "O",
   "F",  "Ne", "Na", "Mg", "Al", "Si", "P",  "S",
   "Cl", "Ar", "K",  "Ca", "Sc", "Ti", "V",  "Cr",
   "Mn", "Fe", "Co", "Ni", "Cu", "Zn", "Ga", "Ge",
   "As", "Se", "Br", "Kr", "Rb", "Sr", "Y",  "Zr",
   "Nb", "Mo", "Tc", "Ru", "Rh", "Pd", "Ag", "Cd",
   "In", "Sn", "Sb", "Te", "I",  "Xe", "Cs", "Ba",
   "La", "Ce", "Pr", "Nd", "Pm", "Sm", "Eu", "Gd",
   "Tb", "Dy", "Ho", "Er", "Tm", "Yb", "Lu", "Hf",
   "Ta", "W",  "Re", "Os", "Ir", "Pt", "Au", "Hg",
   "Tl", "Pb", "Bi", "Po", "At", "Rn", "Fr", "Ra",
   "Ac", "Th", "Pa", "U",  "Np", "Pu", "Am", "Cm",
   "Bk", "Cf", "Es", "Fm", "Md", "No", "Lr", "Rf",
   "Db", "Sg", "Bh", "Hs", "Mt", "Ds", "Rg", "Cn",
   "Uut", "Fl", "Uup", "Lv", "Uus", "Uuo"};


/* errors in XDI_required_metadata */
#define REQ_ELEM              1
#define REQ_EDGE              2
#define REQ_NO_DSPACING       4
#define REQ_INVALID_DSPACING  8

/* warnings from reading the XDI file */
#define WRN_NODSPACE          1
#define WRN_NOMINUSLINE       2
#define WRN_IGNOREDMETA       4
/* warnings from metadata value validation, these are not use bitwise */
#define WRN_NOELEM          100
#define WRN_NOEDGE          101
#define WRN_REFELEM         102
#define WRN_REFEDGE         103
#define WRN_NOEXTRA         104
#define WRN_BAD_COL1        105
#define WRN_DATE_FORMAT     106
#define WRN_DATE_RANGE      107
#define WRN_BAD_DSPACING    108
#define WRN_BAD_SAMPLE      109
#define WRN_BAD_FACILITY    110

/* errors reading the XDI file */
#define ERR_NOTXDI           -1	/* used */
#define ERR_META_FAMNAME     -2	/* used */
#define ERR_META_KEYNAME     -4	/* used */
#define ERR_META_FORMAT      -8	/* used */
#define ERR_NCOLS_CHANGE    -16	/* used */
#define ERR_NONNUMERIC      -32	/* used */
#define ERR_ONLY_ONEROW     -64	/* used */
#define ERR_MEMERROR       -128 /* NOT used */

/* _EXPORT(char*) XDI_errorstring(int errcode); */


/* List of recommended metadata items */
static char *RecommendedMetadata[] =
  {                             /* these are the bits of the errorcode returned by XDI_recommended_metadata */
    "Element.symbol",		/* 2^0 */
    "Element.edge",     	/* 2^1 */
    "Mono.d_spacing",		/* 2^2 */
    "Facility.name",		/* 2^3 */
    "Facility.xray_source",	/* 2^4 */
    "Beamline.name",		/* 2^5 */
    "Scan.start_time",		/* 2^6 */
    "Column.1",			/* 2^7 */
  };
