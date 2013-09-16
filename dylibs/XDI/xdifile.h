#if defined(WIN32) || defined(_WIN32) || defined(__WIN32__)
#define _EXPORT(a) __declspec(dllexport) a _stdcall
#else
#define _EXPORT(a) a
#endif

#define MAX_COLUMNS 64  /* maximum number of supported data columns */

typedef struct {
  long nmetadata;        /* number of metadata family/key/val metadata */
  long narrays;          /* number of arrays */
  long npts;             /* number of data points for all arrays */
  long narray_labels;    /* number of labeled arrays (may be < narrays) */
  long  error_lineno;    /* line numberfor any existing error */
  double dspacing;       /* monochromator d spacing */
  char *xdi_libversion;  /* XDI version of library */
  char *xdi_version;     /* XDI version string from file*/
  char *extra_version;   /* Extra version strings from first line of file */
  char *filename;        /* name of file */
  char *element;         /* atomic symbol for element */
  char *edge;            /* name of absorption edge: "K", "L1", ... */
  char *comments;        /* multi-line, user-supplied comment */
  char *error_line;      /* text of line with any existing error */
  char **array_labels;   /* labels for arrays */
  char **array_units;    /* units for arrays */
  char **meta_families;  /* family for metadata from file header */
  char **meta_keywords;  /* keyword for metadata from file header */
  char **meta_values;    /* value for metadata from file header */
  double **array;        /* 2D array of all array data */
} XDIFile;

_EXPORT(int) XDI_readfile(char *filename, XDIFile *xdifile) ;
_EXPORT(int) XDI_get_array_index(XDIFile *xdifile, long n, double *out);
_EXPORT(int) XDI_get_array_name(XDIFile *xdifile, char *name, double *out);

#define XDI_VERSION  "1.0.0"   /* XDI version marker */

/* Tokens used in XDI File */

#define TOK_VERSION  "XDI/"           /* version marker in file -- required on line 1 */
#define TOK_COMM     "#"              /* comment character, at start of line */
#define TOK_DELIM    ":"              /* delimiter between metadata name and value */
#define TOK_DOT      "."              /* delimiter between metadata family and key */
#define TOK_EDGE     "element.edge"   /* absorbption edge name */
#define TOK_ELEM     "element.symbol" /* atomic symbol of absorbing element */
#define TOK_COLUMN   "column."        /* column label (followed by integer <= 64) */
#define TOK_DSPACE   "mono.d_spacing" /* mono d_spacing, in Angstroms */
#define TOK_TIMESTAMP  "scan.start_time" /* scan time */
#define TOK_USERCOM_0 "///"           /* start multi-line user comment */
#define TOK_USERCOM_1 "---"           /* end multi-line user comment */
#define TOK_COL_ENERGY "energy"       /* name of energy column */
#define TOK_COL_ANGLE  "angle"        /* name of angle column */

#define FAMILYNAME "^[ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz_][ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz_0123456789]+$"
#define KEYNAME    "^[ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz_0123456789]+$"


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


/* error codes */
#define ERR_NOTXDI       -10
#define ERR_NOARR_NAME   -21
#define ERR_NOARR_INDEX  -22
#define ERR_NOELEM         1
#define ERR_NOEDGE         2
#define ERR_NODSPACE       4

#define ERR_META_FAMNAME -41
#define ERR_META_KEYNAME -42
#define ERR_META_FORMAT  -43

#define ERR_DATE_FORMAT  -51
#define ERR_DATE_RANGE   -52

#define ERR_NOMINUSLINE  -80
#define ERR_NCOLS_CHANGE -81
#define ERR_NONNUMERIC   -82

#define ERR_IGNOREDMETA -100


_EXPORT(char*) XDI_errorstring(int errcode);
