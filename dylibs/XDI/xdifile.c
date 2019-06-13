/* read XDI file in C */

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


#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <errno.h>
#include <math.h>

#ifndef max
#define max( a, b ) ( ((a) > (b)) ? (a) : (b) )
#endif
#ifndef min
#define min( a, b ) ( ((a) < (b)) ? (a) : (b) )
#endif

#include "slre.h"
#include "strutil.h"
#include "xdifile.h"

/* error string interpretation */
_EXPORT(char*)
XDI_errorstring(int errcode) {
  if (errcode == 0) { return ""; }
  if (errcode == ERR_NOTXDI) {
    return "not an XDI file";
  } else if (errcode == WRN_NOELEM) {
    return "element.symbol not given or not valid";
  } else if (errcode == WRN_NOEDGE) {
    return "element.edge not given or not valid";
  } else if (errcode == WRN_REFELEM) {
    return "element.reference not valid";
  } else if (errcode == WRN_REFEDGE) {
    return "element.ref_edge not valid";
  } else if (errcode == WRN_NOEXTRA) {
    return "extension fields used without versioning information";
  } else if (errcode == WRN_NODSPACE) {
    return "no mono.d_spacing given with angle array";
  } else if (errcode == ERR_META_FAMNAME) {
    return "invalid family name in meta-data";
  } else if (errcode == ERR_META_KEYNAME) {
    return "invalid keyword name in meta-data";
  } else if (errcode == ERR_META_FORMAT) {
    return "metadata not formatted as Family.Key: Value";
  } else if (errcode == WRN_DATE_FORMAT) {
    return "invalid timestamp: format should be YYYY-MM-DD HH:MM:SS";
  } else if (errcode == WRN_DATE_RANGE) {
    return "invalid timestamp: date out of valid range";
  } else if (errcode == WRN_NOMINUSLINE) {
    return "no line of minus signs '#-----' separating header from data";
  } else if (errcode == ERR_NCOLS_CHANGE) {
    return "number of columns changes in file";
  } else if (errcode == WRN_BAD_DSPACING) {
    return "non-numeric value for d-spacing";
  } else if (errcode == ERR_NONNUMERIC) {
    return "non-numeric value in data table";
  } else if (errcode == ERR_ONLY_ONEROW) {
    return "one or fewer rows in data table";
  } else if (errcode == WRN_IGNOREDMETA) {
    return "contains unrecognized header lines";
  }
  return "";
}


/* */
int xdi_strtod(char* inp, double *dval) {
  /* converts string containing number (double) to double
     returns 0 on success
     returns non-zero if string is NaN or not a valid number
   */
  char *end;
  *dval = strtod(inp, &end);
  if (*dval != (*dval+0) ) { /* tests for NaN */
    return -1;
  }
  return *end != '\0';
}

_EXPORT(int)
XDI_readfile(char *filename, XDIFile *xdifile) {
  char *textlines[MAX_LINES];
  char *header[MAX_LINES];
  char *words[MAX_WORDS], *cwords[2];
  char *col_labels[MAX_COLUMNS], *col_units[MAX_COLUMNS];
  char *c, *line, *firstline, *interline, *fullline, *mkey,  *mval;
  char *reword;
  char tlabel[32] = {'\0'};
  char comments[1025] = {'\0'};
  char elem[4] = {'\0'};
  char edge[3] = {'\0'};
  char version_xdi[8] = {'\0'};
  char version_extra[MAX_LINE_LENGTH] = {'\0'};
  char errline[MAX_LINE_LENGTH] = {'\0'};
  char errmessage[2048] = {'\0'};
  char outerlabel[MAX_WORD_LENGTH] = {'\0'};
  double dval ;
  double *outer_arr, outer_arr0;
  long   *outer_pts;
  FILE *inpFile;
  long  file_length, ilen, index, i, j, k, nx, maxcol;
  long  npts_, ncols, icol, nheader, nwords, ndict;
  long  ignored_headerline, iret, code, ipt, nouter, iouter;
  int   is_newline, fnlen, mode, valid, stat;
  int   has_minusline, has_angle, has_energy;
  /* const char *regex_status; */
  int regex_status;
  struct slre_cap caps[1];

  int n_edges = sizeof(ValidEdges)/sizeof(char*);
  int n_elems = sizeof(ValidElems)/sizeof(char*);

  iret = 0;


  /* initialize string attributes of thr XDIFile struct */
  strcpy(comments, " ");
  xdifile->comments = calloc(1025, sizeof(char));
  strcpy(xdifile->comments, comments);

  strcpy(elem, "  ");
  xdifile->element = calloc(4, sizeof(char));
  strncpy(xdifile->element, elem, 3);

  strcpy(edge, "  ");
  xdifile->edge = calloc(3, sizeof(char));
  strncpy(xdifile->edge, edge, 2);

  xdifile->xdi_libversion = calloc(8, sizeof(char));
  strncpy(xdifile->xdi_libversion, XDI_VERSION, 7);

  strcpy(version_xdi, " ");
  xdifile->xdi_version = calloc(8, sizeof(char));
  strncpy(xdifile->xdi_version, version_xdi, 7);

  strcpy(version_extra, " ");
  xdifile->extra_version = calloc(MAX_LINE_LENGTH+1, sizeof(char));
  strncpy(xdifile->extra_version, version_extra, MAX_LINE_LENGTH);

  strcpy(errline, " ");
  xdifile->error_line = calloc(MAX_LINE_LENGTH+1, sizeof(char));
  strncpy(xdifile->error_line, errline, MAX_LINE_LENGTH);

  strcpy(errmessage, " ");
  xdifile->error_message = calloc(2049, sizeof(char));
  strncpy(xdifile->error_message, errmessage, 2048);

  strcpy(outerlabel, " ");
  xdifile->outer_label = calloc(MAX_LINE_LENGTH+1, sizeof(char));
  strncpy(xdifile->outer_label, outerlabel, MAX_LINE_LENGTH);

  /* initialize numeric attributes of thr XDIFile struct */

  xdifile->nouter = 1;
  xdifile->error_lineno = -1;
  xdifile->dspacing = -1.0;

  has_minusline = 0;
  ignored_headerline = -1;
  nheader = 0;
  ndict   = -1;
  maxcol  = 0;
  for (i = 0; i < MAX_COLUMNS; i++) {
    sprintf(tlabel, "col%ld", i+1);
    COPY_STRING(col_labels[i], tlabel);
    /* COPY_STRING(col_units[i], ""); */
    /* col_labels[i] = tlabel; */
    col_units[i] = "";
  }

  /* read file to text lines: an array of trimmed strings */
  ilen = readlines(filename, textlines);
  if (ilen < 0) {
    if (errno == 0) {
      errno = -ilen;
    }
    printf("%s\n", strerror(errno));
    return ilen;
  }
  /* check first line for XDI header, get version info */
  if (strncmp(textlines[0], TOK_COMM, 1) == 0)  {
    firstline = textlines[0]; firstline++;
    firstline[strcspn(firstline, CRLF)] = '\0';
    nwords = make_words(firstline, cwords, 2);
    if (nwords < 1) {
      strcpy(xdifile->error_message, "not an XDI file, no XDI versioning information in first line");
      for (j=0; j<=ilen; j++) {
	free(textlines[j]);
      }
      for (i = 0; i < MAX_COLUMNS; i++) {
	free(col_labels[i]);
      }
      return ERR_NOTXDI;
    }
    if (strncasecmp(cwords[0], TOK_VERSION, strlen(TOK_VERSION)) != 0)  {
      strcpy(xdifile->error_message, "not an XDI file, no XDI versioning information in first line");
      for (j=0; j<=ilen; j++) {
	free(textlines[j]);
      }
      for (i = 0; i < MAX_COLUMNS; i++) {
	free(col_labels[i]);
      }
      return ERR_NOTXDI;
    } else {
      firstline = firstline+5;
      strcpy(xdifile->xdi_version, firstline);
    }
    if (nwords > 1) { /* extra version tags */
      strcpy(xdifile->extra_version, cwords[1]);
    }
  }
  /* find number of header lines,
     nheader= index of first line that does not start with '#'
  */
  for (i = 1; i < ilen ; i++) {
    regex_status = slre_match(DATALINE, textlines[i], strlen(textlines[i]), NULL, 0, 0);
    if ((strlen(textlines[i]) > 3) && (regex_status >= 0)) {
  	/* (strncmp(textlines[i], TOK_COMM, 1) != 0))  { */
      break;
    }
  }
  nheader = i+1;
  if (nheader < 1) {nheader = 1;}
  xdifile->meta_families = calloc(nheader, sizeof(char *));
  xdifile->meta_keywords = calloc(nheader, sizeof(char *));
  xdifile->meta_values   = calloc(nheader, sizeof(char *));

  mode = 0; /*  metadata (Family.Member: Value) mode */
  for (i = 1; i < nheader; i++) {
    xdifile->error_lineno = i;
    strcpy(xdifile->error_line, textlines[i]);

    if (strncmp(textlines[i], TOK_COMM, 1) == 0)  {
      /* COPY_STRING(line, textlines[i]); */
      /* COPY_STRING(fullline, textlines[i]); */
      line = textlines[i];
      fullline = textlines[i];
      line++;
      fullline++;
      nwords = split_on(line, TOK_DELIM, words);
      if (nwords < 1) { continue; }
      COPY_STRING(mkey, words[0]);

      if ((mode==0) && (nwords == 2)) { /* metadata */
	/* COPY_STRING(mval, words[1]); */
	mval = words[1];
	nwords = split_on(words[0], TOK_DOT, words);
	if (nwords > 1) {
	  ndict++;
	  COPY_STRING(xdifile->meta_values[ndict],   mval);
	  /* need to test words[0] and words[1] as valid family/key names
	    family name cannot start with number
	    key cannot contain '.'
	   */
	  regex_status = slre_match(FAMILYNAME, words[0], strlen(words[0]), caps, 1, 0);
	  if (regex_status < 0) {
	    xdifile->nmetadata = ndict+1;
	    strcpy(xdifile->error_message, words[0]);
	    strcat(xdifile->error_message, " -- invalid family name in metadata");
	    free(mkey);
	    for (k=0; k<=ilen; k++) {
	      free(textlines[k]);
	    }
	    for (i = 0; i < MAX_COLUMNS; i++) {
	      free(col_labels[i]);
	    }
	    return ERR_META_FAMNAME;
	  }

	  regex_status = slre_match(KEYNAME,  words[1], strlen(words[1]), caps, 1, 0);
	  if (regex_status < 0) {
	    xdifile->nmetadata = ndict+1;
	    strcpy(xdifile->error_message, words[1]);
	    strcat(xdifile->error_message, " -- invalid keyword name in metadata");
	    free(mkey);
	    for (k=0; k<=ilen; k++) {
	      free(textlines[k]);
	    }
	    for (i = 0; i < MAX_COLUMNS; i++) {
	      free(col_labels[i]);
	    }
	    return ERR_META_KEYNAME;
	  }

	  COPY_STRING(xdifile->meta_families[ndict], words[0]);
	  COPY_STRING(xdifile->meta_keywords[ndict], words[1]);
	} else {
	  xdifile->nmetadata = ndict+1;
	  strcpy(xdifile->error_message, "\"");
	  strcat(xdifile->error_message, xdifile->error_line);
	  strcat(xdifile->error_message, "\" -- not formatted as Family.Key: Value");
	  free(mkey);
	  for (k=0; k<=ilen; k++) {
	    free(textlines[k]);
	  }
	  for (i = 0; i < MAX_COLUMNS; i++) {
	    free(col_labels[i]);
	  }
	  return ERR_META_FORMAT;
	}
	/* printf(" metadata:  %ld | %s | %s\n", ndict, mkey, mval); */
	/* ndict,  words[0], words[1],  xdifile->meta_valuesn[dict]);*/
	if (strncasecmp(mkey, TOK_COLUMN, strlen(TOK_COLUMN)) == 0) {
	  j = atoi(mkey+7)-1;
	  if ((j > -1) && (j < MAX_COLUMNS)) {
	    ncols = make_words(mval, cwords, 2);
	    free(col_labels[j]);
	    COPY_STRING(col_labels[j], cwords[0]);
	    if (ncols == 2) {
	      col_units[j] = cwords[1];
	    }
	    maxcol =  max(maxcol, j);
	  }

	/* ELEMENT EDGE (accept any twwo characters, validate later) */
	} else if (strcasecmp(mkey, TOK_EDGE) == 0) {
	  strncpy(xdifile->edge, mval, 2);

	/* ELEMENT NAME (accept any three characters, validate later) */
	} else if (strcasecmp(mkey, TOK_ELEM) == 0) {
	  strncpy(xdifile->element, mval, 3);

	/* MONO D-SPACING */
	} else if (strcasecmp(mkey, TOK_DSPACE) == 0) {
	  if (0 == xdi_strtod(mval, &dval)) {
	    xdifile->dspacing = dval;
	  } else {
	    xdifile->dspacing = -1.0;
	  };

	/* OUTER ARRAY NAME */
	} else if (strcasecmp(mkey, TOK_OUTER_NAME) == 0) {
	  strcpy(xdifile->outer_label, mval);

	/* OUTER ARRAY VALUE */
	} else if (strcasecmp(mkey, TOK_OUTER_VAL) == 0) {
	  if (0 != xdi_strtod(mval, &dval)) {
	    strcpy(xdifile->error_message, "non-numeric outer array value: ");
	    strcat(xdifile->error_message, mkey);
	    free(mval);
    	    return ERR_NONNUMERIC;
	  }
	  outer_arr0 = dval ;

	}

      } else if (strncasecmp(mkey, TOK_USERCOM_0, strlen(TOK_USERCOM_0)) == 0) {
	mode = 1;
      } else if (strncasecmp(mkey, TOK_USERCOM_1, strlen(TOK_USERCOM_1)) == 0) {
	mode = 2;
	has_minusline = 1;
      } else if (mode==1) {
	if ((strlen(comments) > 0) && strlen(comments) < sizeof(comments)) {
	  strncat(comments, "\n", sizeof(comments)-strlen(comments) - 1);
	}
	if (strlen(fullline) + 1 > sizeof(comments) - strlen(comments)) {
	  printf("Warning.... user comment may be truncated!\n");
	}
	strncat(comments, fullline, sizeof(comments) - strlen(comments) - 1);
      } else if (mode == 0) {
	xdifile->nmetadata = ndict+1;
	strcpy(xdifile->error_message, "\"");
	strcat(xdifile->error_message, xdifile->error_line);
	strcat(xdifile->error_message, "\" -- not formatted as Family.Key: Value");
	free(mkey);
	for (k=0; k<=ilen; k++) {
	  free(textlines[k]);
	}
	for (i = 0; i < MAX_COLUMNS; i++) {
	  free(col_labels[i]);
	}
	return ERR_META_FORMAT;
      }
      free(mkey);
    } else {
      if ((ignored_headerline < 0) && (has_minusline == 0)) {
	ignored_headerline = i;
      }
    }
  }
  if (ignored_headerline > 0) {
    strcpy(xdifile->error_message, "contains unrecognized header lines");
    iret = WRN_IGNOREDMETA;
  }
  if (has_minusline == 0)     {
    strcpy(xdifile->error_message, "no line of minus signs '#-----' separating header from data");
    iret = WRN_NOMINUSLINE;
  }

  npts_ = ilen - nheader + 1;
  nouter = npts_ - 1;
  if (nouter < 1) {
    return ERR_ONLY_ONEROW;
  }
  outer_arr = calloc(nouter, sizeof(double));
  outer_pts = calloc(nouter, sizeof(long));
  outer_arr[0] = outer_arr0;
  outer_pts[0] = 1;

  COPY_STRING(line, textlines[i]);
  ncols = make_words(line, words, MAX_WORDS);
  if (ncols < 2) {
    return ERR_ONLY_ONEROW;
  }
  strcpy(xdifile->comments, comments);
  COPY_STRING(xdifile->filename, filename);

  maxcol++;
  if (ncols < 1) {ncols = 1;}

  xdifile->array_labels = calloc(ncols, sizeof(char *));
  xdifile->array_units  = calloc(ncols, sizeof(char *));
  has_energy = 0;
  has_angle  = 0;
  for (j = 0; j < ncols; j++) {
    COPY_STRING(xdifile->array_labels[j], col_labels[j]);
    COPY_STRING(xdifile->array_units[j], col_units[j]);
    if (strcasecmp(TOK_COL_ENERGY, col_labels[j]) == 0) {
      has_energy = 1;
    } else if (strcasecmp(TOK_COL_ANGLE, col_labels[j]) == 0) {
      has_angle = 1;
    }
  }

  /* check for mono d-spacing if angle is given but not energy*/
  if ((has_angle == 1)  && (has_energy == 0) && (xdifile->dspacing < 0)) {
    strcpy(xdifile->error_message, "no mono.d_spacing given with angle array");
    iret = WRN_NODSPACE;
  }

  /* set size of data arrays */
  xdifile->array = calloc(ncols, sizeof(double *));
  if (npts_ < 0) {npts_ = 0;}
  for (j = 0; j < ncols; j++) {
    xdifile->array[j] = calloc(npts_+1, sizeof(double));
    if (0 != xdi_strtod(words[j], &dval)) {
      strcpy(xdifile->error_message, "non-numeric value in data table: ");
      strcat(xdifile->error_message, words[j]);
      free(line);
      free(outer_arr);
      free(outer_pts);
      xdifile->narrays = ncols;
      xdifile->nmetadata = ndict+1;
      for (i=0; i<=ilen; i++) {
         free(textlines[i]);
      }
      for (i = 0; i < MAX_COLUMNS; i++) {
         free(col_labels[i]);
      }
      return ERR_NONNUMERIC;
    }
    xdifile->array[j][0] = dval;
  }

  /* loop through data table, inserting data into xdifile->array */
  ipt = 0;
  iouter = 1;
  for (i = nheader-2; i <= ilen; i++) {
    /* may find a header line interspersed in array data */
    /* COPY_STRING(line, textlines[i]); */
    interline = textlines[i];
    xdifile->error_lineno = i;
    strcpy(xdifile->error_line, interline);

    if (strncmp(textlines[i], TOK_COMM, 1) == 0)  {
      interline++;
      nwords = split_on(interline, TOK_DELIM, words);
      if (nwords < 2) { continue; }
      COPY_STRING(mkey, words[0]);
      if (strcasecmp(mkey, TOK_OUTER_VAL) == 0) {
	if (0 != xdi_strtod(words[1], &dval)) {
	  strcpy(xdifile->error_message, "non-numeric value in data table: ");
	  strcat(xdifile->error_message, mkey);
	  free(outer_arr);
	  free(outer_pts);
	  return ERR_NONNUMERIC;
	}
	outer_arr[iouter] = dval;
	outer_pts[iouter] = ipt;
	++iouter;
      }
      free(mkey);
    } else {
      /* COPY_STRING(line, textlines[i]); */
      icol = make_words(textlines[i], words, MAX_WORDS);
      if (icol != ncols) {
	strcpy(xdifile->error_message, "number of columns changes in data table");
	free(line);
	free(outer_arr);
	free(outer_pts);
	xdifile->narrays = ncols;
	xdifile->nmetadata = ndict+1;
	for (j=0; j<=ilen; j++) {
	  free(textlines[j]);
	}
	for (i = 0; i < MAX_COLUMNS; i++) {
	  free(col_labels[i]);
	}
	return ERR_NCOLS_CHANGE;
      }
      icol = min(ncols, icol);
      for (j = 0; j < icol; j++) {
	if (0 != xdi_strtod(words[j], &dval)) {
	  strcpy(xdifile->error_message, "non-numeric value in data table: ");
	  strcat(xdifile->error_message, words[j]);
	  free(line);
	  free(outer_arr);
	  free(outer_pts);
	  xdifile->narrays = ncols;
	  xdifile->nmetadata = ndict+1;
	  for (j=0; j<=ilen; j++) {
	    free(textlines[j]);
	  }
	  for (i = 0; i < MAX_COLUMNS; i++) {
	    free(col_labels[i]);
	  }
	  return ERR_NONNUMERIC;
	}
	xdifile->array[j][ipt] = dval;
      }
      ++ipt;
    }
  }

  /* success */
  xdifile->error_lineno = 0;
  strcpy(xdifile->error_line, "");

  xdifile->npts = ipt;
  xdifile->nouter = iouter;
  xdifile->narrays = ncols;
  xdifile->narray_labels = min(ncols, maxcol);
  xdifile->nmetadata = ndict+1;
  if (iouter < 1) {iouter = 1;}
  xdifile->outer_array    = calloc(iouter, sizeof(double));
  xdifile->outer_breakpts = calloc(iouter, sizeof(long));
  for (j= 0; j < iouter; j++) {
    xdifile->outer_array[j] = outer_arr[j];
    xdifile->outer_breakpts[j] = outer_pts[j];
  }
  free(line);
  free(outer_arr);
  free(outer_pts);
  /* this was the space used to hold the lines of the file, allocated in readlines */
  for (j=0; j<=ilen; j++) {
    free(textlines[j]);
  }
  for (i = 0; i < MAX_COLUMNS; i++) {
    free(col_labels[i]);
  }
  return iret;

}

_EXPORT(void)
XDI_writefile(XDIFile *xdifile, char *filename) {
  int i, j, count;

  char quote[1025];
  const char s[2] = "\n";
  char *token;

  int regex_status;
  struct slre_cap caps[3];

  FILE *fp;
  fp = fopen(filename, "w");

  /* version line */
  strcpy(quote, xdifile->comments);
  fprintf(fp, "# XDI/%s %s\n", xdifile->xdi_version, xdifile->extra_version);

  /* metadata section */
  for (i=0; i < xdifile->nmetadata; i++) {
        fprintf(fp, "# %s.%s: %s\n",
		xdifile->meta_families[i],
		xdifile->meta_keywords[i],
		xdifile->meta_values[i]);
  }

  /* user comments */
  fprintf(fp, "#////////////////////////\n");
  count = 0;
  token = strtok(quote, s);   /* get the first token */
  while( token != NULL ) {    /* walk through other tokens, skipping empty */
    if (count == 0) {	      /* take care with empty first token */
      regex_status = slre_match("^\\s*$", token, strlen(token), caps, 2, 0);
      if (regex_status < 0) {
	fprintf(fp, "#%s\n", token );
      }
    } else {
      fprintf(fp, "#%s\n", token );
    }
    ++count;
    token = strtok(NULL, s);
  }
  fprintf(fp, "#------------------------\n");

  /* column labels */
  fprintf(fp, "# ");
  for (i = 0; i < xdifile->narrays; i++) {
    fprintf(fp, " %s  ", xdifile->array_labels[i]);
  }
  fprintf(fp, "\n");

  /* data table */
  for (i = 0; i < xdifile->npts; i++ ) {
    for (j = 0; j < xdifile->narrays; j++ ) {
      fprintf(fp, "  %-12.8g", xdifile->array[j][i]);
    }
    fprintf(fp, "\n");
  }

}

/* ============================================================================ */
/* array management section                                                     */

#define ENOUGH ((8 * sizeof(int) - 1) / 3 + 2)

_EXPORT(int)
XDI_get_array_index(XDIFile *xdifile, long n, double *out) {
  /* get array by index (starting at 0) from an XDIFile structure */
  long j;
  char str[ENOUGH];
  if (n < xdifile->narrays) {
    for (j = 0; j < xdifile->npts; j++) {
      out[j] = xdifile->array[n][j];
    }
    return 0;
  }
  strcpy(xdifile->error_message, "no array of index ");
  sprintf(str, "%ld", n);
  strcat(xdifile->error_message, str);
  return -1;
}

_EXPORT(int)
XDI_get_array_name(XDIFile *xdifile, char *name, double *out) {
  /* get array by name from an XDIFile structure */
  long i;
  for (i = 0; i < xdifile->narrays; i++) {
    if (strcasecmp(name, xdifile->array_labels[i]) == 0) {
      return XDI_get_array_index(xdifile, i, out);
    }
  }
  strcpy(xdifile->error_message, "no array of name ");
  strcat(xdifile->error_message, name);
  return -1;
}

/* ============================================================================ */



/* ============================================================================ */
/* metadata validation section                                                  */

_EXPORT(int)
XDI_defined_family(XDIFile *xdifile, char *family) {
  if ((strcasecmp(family, "facility") == 0) ||
      (strcasecmp(family, "beamline") == 0) ||
      (strcasecmp(family, "mono")     == 0) ||
      (strcasecmp(family, "detector") == 0) ||
      (strcasecmp(family, "sample")   == 0) ||
      (strcasecmp(family, "scan")     == 0) ||
      (strcasecmp(family, "element")  == 0) ||
      (strcasecmp(family, "column")   == 0))  {
    return 1;
  } else {
    return 0;
  };
}

_EXPORT(int)
XDI_required_metadata(XDIFile *xdifile) {
  int ret;
  int i, j;
  char *word;

  ret = 0;

  j = XDI_validate_item(xdifile, "element", "symbol", xdifile->element);
  if (j != 0) {
    ret = ret + REQ_ELEM;
  }

  j = XDI_validate_item(xdifile, "element", "edge", xdifile->edge);
  if (j != 0) {
    ret = ret + REQ_EDGE;
  }

  word = "___notfound";
  for (i=0; i < xdifile->nmetadata; i++) {
    if ((strcasecmp(xdifile->meta_families[i], "mono") == 0) && (strcasecmp(xdifile->meta_keywords[i], "d_spacing") == 0)) {
      word = xdifile->meta_values[i];
      break;
    }
  }
  if (strcasecmp(word, "___notfound") == 0) {
    ret = ret + REQ_NO_DSPACING;
  } else {
    j = XDI_validate_item(xdifile, "mono", "d_spacing", word);
    if (j != 0) {
      ret = ret + REQ_INVALID_DSPACING;
    }
  }

  strcpy(xdifile->error_message, "");
  if (ret & REQ_ELEM)             { strcat(xdifile->error_message, "Element.symbol missing or not valid\n"); }
  if (ret & REQ_EDGE)             { strcat(xdifile->error_message, "Element.edge missing or not valid\n"); }
  if (ret & REQ_NO_DSPACING)      { strcat(xdifile->error_message, "Mono.d_spacing missing\n"); }
  if (ret & REQ_INVALID_DSPACING) { strcat(xdifile->error_message, "Non-numerical value fo Mono.d_spacing\n"); }

  return ret;
}


/* Facility.name:             1 */
/* Facility.xray_source:      2 */
/* Beamline.name:             4 */
/* Scan.start_time:           8 */
/* Column.1: (energy|angle): 16 */

_EXPORT(int)
XDI_recommended_metadata(XDIFile *xdifile) {
  int ret, i, n, errcode, found;
  int n_rec = sizeof(RecommendedMetadata)/sizeof(char*);
  char *words[2];
  char thisword[100] = {'\0'};
  int nwords;

  /* ret = pow(2,n_rec+1)-1; */
  ret = (1<<(n_rec)) - 1;
  strcpy(xdifile->error_message, "");


  for (n=0; n<n_rec; n++) {
    found = 0;
    /* errcode = pow(2,n); */
    errcode = 1<<n;
    /* printf("%d  %d  %s\n", ret, errcode, RecommendedMetadata[n]); */
    strcpy(thisword, RecommendedMetadata[n]);
    nwords = split_on(thisword, TOK_DOT, words);

    for (i=0; i < xdifile->nmetadata; i++) {
      if ((strcasecmp(xdifile->meta_families[i], words[0]) == 0) && (strcasecmp(xdifile->meta_keywords[i], words[1]) == 0)) {
    	ret = ret-errcode;
	found = 1;
    	break;
      }
    }
    if (found == 0) {
      strcat(xdifile->error_message, "Missing recommended metadata field: ");
      strcat(xdifile->error_message, RecommendedMetadata[n]);
      strcat(xdifile->error_message, "\n");
    }
  }

  return ret;
}


_EXPORT(int)
XDI_validate_item(XDIFile *xdifile, char *family, char *name, char *value) {
  int regex_status;
  int err, j;
  int n_edges = sizeof(ValidEdges)/sizeof(char*);
  int n_elems = sizeof(ValidElems)/sizeof(char*);
  struct slre_cap caps[1];

  /* printf("======== %s %s %s\n", family, name, value); */

  if (strcasecmp(family, "facility") == 0) {
    err = XDI_validate_facility(xdifile, name, value);

  } else if (strcasecmp(family, "beamline") == 0) {
    err = 0;

  } else if (strcasecmp(family, "mono") == 0) {
    err = XDI_validate_mono(xdifile, name, value);

  } else if (strcasecmp(family, "detector") == 0) {
    err = 0;

  } else if (strcasecmp(family, "sample") == 0) {
    err = XDI_validate_sample(xdifile, name, value);

  } else if (strcasecmp(family, "scan") == 0) {
    err = XDI_validate_scan(xdifile, name, value);

  } else if (strcasecmp(family, "element") == 0) {
    err = XDI_validate_element(xdifile, name, value);

  } else if (strcasecmp(family, "column") == 0) {
    err = XDI_validate_column(xdifile, name, value);

  } else {
    err = 0;
    regex_status = slre_match(family, xdifile->extra_version, strlen(xdifile->extra_version), caps, 1, 0);
    if (regex_status < 0) {
      err = WRN_NOEXTRA;
      strcpy(xdifile->error_message, "extension field used without versioning information");
    };
  }

  return err;
}


/***************************************************************************/
/* all tests in the Facility family should return WRN_BAD_FACILITY if the  */
/* value does not match the definition.  error_message should explain	   */
/* the problem in a way that is appropruiate to the metadata item	   */
/***************************************************************************/
int XDI_validate_facility(XDIFile *xdifile, char *name, char *value) {
  int err;
  int regex_status;
  struct slre_cap caps[3];

  err = 0;
  strcpy(xdifile->error_message, "");

  if (strcasecmp(name, "current") == 0) {
    regex_status = slre_match("^\\d+(\\.\\d*)?\\s+m?[aA].*$", value, strlen(value), caps, 2, 0);
    if (regex_status < 0) {
      strcpy(xdifile->error_message, "Facility.current not interpretable as a beam current");
      err = WRN_BAD_FACILITY;
    }
  } else if (strcasecmp(name, "energy") == 0) {
    regex_status = slre_match("^\\d+(\\.\\d*)?\\s+[gmGM][eE][vV].*$", value, strlen(value), caps, 2, 0);
    if (regex_status < 0) {
      strcpy(xdifile->error_message, "Facility.energy not interpretable as a storage ring energy");
      err = WRN_BAD_FACILITY;
    }
  }

  return err;
}


int XDI_validate_mono(XDIFile *xdifile, char *name, char *value) {
  int err;
  double dval;

  strcpy(xdifile->error_message, "");
  err = 0;

  if (strcasecmp(name, "d_spacing") == 0) {
    if (0 == xdi_strtod(value, &dval)) {
      xdifile->dspacing = dval;
      if (dval < 0) {
	err = WRN_BAD_DSPACING;
	strcpy(xdifile->error_message, "negative value for d-spacing");
      }
    } else {
      err = WRN_BAD_DSPACING;
      strcpy(xdifile->error_message, "non-numeric value for d-spacing");
    }
  }

  return err;
}

/***********************************************************************/
/* all tests in the Sample family should return WRN_BAD_SAMPLE if the  */
/* value does not match the definition.  error_message should explain  */
/* the problem in a way that is appropruiate to the metadata item      */
/***********************************************************************/
int XDI_validate_sample(XDIFile *xdifile, char *name, char *value) {
  int err;
  int regex_status;
  struct slre_cap caps[2];

  err = 0;
  strcpy(xdifile->error_message, "");

  if (strcasecmp(name, "temperature") == 0) {
    regex_status = slre_match("^\\d+(\\.\\d*)?\\s+[CcFfKk].*$", value, strlen(value), caps, 2, 0);
    if (regex_status < 0) {
      strcpy(xdifile->error_message, "Sample.temperature not interpretable as a temperature");
      err = WRN_BAD_SAMPLE;
    }
  } else if (strcasecmp(name, "stoichiometry") == 0) {
    /* TODO */
    /* need a chemical formula parser to validate Sample.stoichiometry */
    err = 0;
  }

  return err;
}


/**************************************************************/
/* tests if input string is a valid datetime timestamp.	      */
/* This uses regular expression to check format and validates */
/* range of values, though not exhaustively.		      */
/**************************************************************/
int xdi_is_datestring(char *inp) {
  int regex_status;
  struct slre_cap caps[6];
  int year, month, day, hour, minute, sec;
  char word[5] = {'\0'};
  regex_status = slre_match("^(\\d\\d\\d\\d)-(\\d\\d?)-(\\d\\d?)[Tt ](\\d\\d?):(\\d\\d):(\\d\\d).*$",
			    inp, strlen(inp), caps, 6, 0);
			    /* SLRE_INT, sizeof(sec), &year, */
			    /* SLRE_INT, sizeof(sec), &month, */
			    /* SLRE_INT, sizeof(sec), &day, */
			    /* SLRE_INT, sizeof(sec), &hour, */
			    /* SLRE_INT, sizeof(sec), &minute, */
			    /* SLRE_INT, sizeof(sec), &sec); */

  if (regex_status < 0) { return WRN_DATE_FORMAT;}

  sprintf(word, "%.*s", caps[0].len, caps[0].ptr);
  year = atoi(word);
  sprintf(word, "%.*s", caps[1].len, caps[1].ptr);
  month = atoi(word);
  sprintf(word, "%.*s", caps[2].len, caps[2].ptr);
  day = atoi(word);
  sprintf(word, "%.*s", caps[3].len, caps[3].ptr);
  hour = atoi(word);
  sprintf(word, "%.*s", caps[4].len, caps[4].ptr);
  minute = atoi(word);
  sprintf(word, "%.*s", caps[5].len, caps[5].ptr);
  sec = atoi(word);

  if ((year   < 1900) ||
      (month  < 1)    || (month  > 12) ||
      (day    < 1)    || (day    > 31) ||
      (hour   < 0)    || (hour   > 23) ||
      (minute < 0)    || (minute > 59) ||
      (sec    < 0)    || (sec    > 59))  {
    return WRN_DATE_RANGE;
  }
  return 0;
}


int XDI_validate_scan(XDIFile *xdifile, char *name, char *value) {
  int err;

  err = 0;
  strcpy(xdifile->error_message, "");

  if (strcasecmp(name, "start_time") == 0) {
    err = xdi_is_datestring(value);
    if (err==WRN_DATE_FORMAT) { strcpy(xdifile->error_message, "invalid timestamp: format should be ISO 8601 (YYYY-MM-DD HH:MM:SS)"); }
    if (err==WRN_DATE_RANGE)  { strcpy(xdifile->error_message, "invalid timestamp: date out of valid range"); }

  } else if (strcasecmp(name, "end_time") == 0) {
    err = xdi_is_datestring(value);
    if (err==WRN_DATE_FORMAT) { strcpy(xdifile->error_message, "invalid timestamp: format should be ISO 8601 (YYYY-MM-DD HH:MM:SS)"); }
    if (err==WRN_DATE_RANGE)  { strcpy(xdifile->error_message, "invalid timestamp: date out of valid range"); }

  } else if (strcasecmp(name, "edge_energy") == 0) {
    /* TODO */
    /* float + units, units can be eV|keV|inverse Angstroms (the last one is kind of tough ...)  */
    err = 0;
  } else {
    err = 0;
  }

  return err;
}

int XDI_validate_element(XDIFile *xdifile, char *name, char *value) {
  int err, j;
  int n_edges = sizeof(ValidEdges)/sizeof(char*);
  int n_elems = sizeof(ValidElems)/sizeof(char*);

  err = 0;
  strcpy(xdifile->error_message, "");

  if (strcasecmp(name, "symbol") == 0) {
    err = WRN_NOELEM;
    for (j = 0; j < n_elems; j++) {
      if (strcasecmp(ValidElems[j], value) == 0) {
	err = 0;
	break;
      }
    }
    if (err>0) { strcpy(xdifile->error_message, "element.symbol missing or not valid"); }

  } else if (strcasecmp(name, "edge") == 0) {
    err = WRN_NOEDGE;
    for (j = 0; j < n_edges; j++) {
      if (strcasecmp(ValidEdges[j], value) == 0) {
	err = 0;
	break;
      }
    }
    if (err!=0) { strcpy(xdifile->error_message, "element.edge missing or not valid"); }

  } else if (strcasecmp(name, "reference") == 0) {
    err = WRN_REFELEM;
    for (j = 0; j < n_elems; j++) {
      if (strcasecmp(ValidElems[j], value) == 0) {
	err = 0;
	break;
      }
    }
    if (err!=0) { strcpy(xdifile->error_message, "element.reference not valid"); }

  } else if (strcasecmp(name, "ref_edge") == 0) {
    err = WRN_REFEDGE;
    for (j = 0; j < n_edges; j++) {
      if (strcasecmp(ValidEdges[j], value) == 0) {
	err = 0;
	break;
      }
    }
    if (err!=0) { strcpy(xdifile->error_message, "element.ref_edge not valid"); }

  } else {
    err = 0;
  }

  return err;
}

int XDI_validate_column(XDIFile *xdifile, char *name, char *value) {
  int err, re1, re2;
  struct slre_cap caps[2];

  err = 0;
  strcpy(xdifile->error_message, "");

  if (strcasecmp(name, "1") == 0) {
    re1 = slre_match("energy", value, strlen(value), caps, 2, 0);
    re2 = slre_match("angle",  value, strlen(value), caps, 2, 0);
    if ((re1 < 0) && (re2 < 0)) {
      err = err + WRN_BAD_COL1;
      strcpy(xdifile->error_message, "Column.1 is not \"energy\" or \"angle\"");
    }
  }

  return err;
}


/* ============================================================================ */


/* ============================================================================ */
/* cleanup and destruction section                                              */

_EXPORT(void)
XDI_cleanup(XDIFile *xdifile, long err) {
  /* free each part of the struct, mindful of the error code reported by the library */
  long j;

  free(xdifile->xdi_libversion);
  free(xdifile->xdi_version);
  free(xdifile->extra_version);
  free(xdifile->element);
  free(xdifile->edge);
  free(xdifile->comments);
  free(xdifile->error_line);
  free(xdifile->error_message);
  free(xdifile->outer_label);

  /* printf("%ld\n", err); */
  if ((err != ERR_NOTXDI)       &&
      (err != ERR_META_FAMNAME) &&
      (err != ERR_META_KEYNAME) &&
      (err != ERR_META_FORMAT))    {
    free(xdifile->filename);
  }

  if ((err < -1) || (err == 0)) {

    if ((err != ERR_META_FAMNAME) && (err != ERR_META_KEYNAME) && (err != ERR_META_FORMAT)) {
      for (j = 0; j < xdifile->narrays; j++) {
	free(xdifile->array[j]);
	free(xdifile->array_labels[j]);
	free(xdifile->array_units[j]);
      }
      free(xdifile->array);
      free(xdifile->array_labels);
      free(xdifile->array_units);
    }

    for (j = 0; j < xdifile->nmetadata; j++) {
      free(xdifile->meta_families[j]);
      free(xdifile->meta_keywords[j]);
      free(xdifile->meta_values[j]);
    }
    free(xdifile->meta_families);
    free(xdifile->meta_keywords);
    free(xdifile->meta_values);

    /* for (j = 0; j < xdifile->nouter; j++) { */
    /*   free(xdifile->outer_array[j]); */
    /*   free(xdifile->outer_breakpts[j]); */
    /* } */
    if (err == 0) {
      free(xdifile->outer_array);
      free(xdifile->outer_breakpts);
    }
  }
}
