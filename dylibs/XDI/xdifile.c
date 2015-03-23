/* read XDI file in C */

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
  } else if (errcode == ERR_NOELEM) {
    return "no element.symbol given";
  } else if (errcode == ERR_NOEDGE) {
    return "no element.edge given";
  } else if (errcode == ERR_NODSPACE) {
    return "no mono.d_spacing given with angle array";
  } else if (errcode == ERR_META_FAMNAME) {
    return "invalid family name in meta-data";
  } else if (errcode == ERR_META_KEYNAME) {
    return "invalid keyword name in meta-data";
  } else if (errcode == ERR_META_FORMAT) {
    return "metadata not formatted as Family.Key: Value";
  } else if (errcode == ERR_DATE_FORMAT) {
    return "invalid timestamp: format should be YYYY-MM-DD HH:MM:SS";
  } else if (errcode == ERR_DATE_RANGE) {
    return "invalid timestamp: date out of valid range";
  } else if (errcode == ERR_NOMINUSLINE) {
    return "no line of minus signs '#-----' separating header from data";
  } else if (errcode == ERR_NCOLS_CHANGE) {
    return "number of columns changes in file";
  } else if (errcode == ERR_NONNUMERIC) {
    return "non-numeric value in data table or for d-spacing";
  } else if (errcode == ERR_IGNOREDMETA) {
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

int xdi_is_datestring(char *inp) {
  /* tests if input string is a valid datetime timestamp.
     This uses regular expression to check format and validates
     range of values, though not exhaustively.
  */
  const char *regex_status;
  int year, month, day, hour, minute, sec;
  regex_status = slre_match(1, "^(\\d\\d\\d\\d)-(\\d\\d?)-(\\d\\d?)[T ](\\d\\d?):(\\d\\d):(\\d\\d).*$",
			    inp, strlen(inp),
			    SLRE_INT, sizeof(sec), &year,
			    SLRE_INT, sizeof(sec), &month,
			    SLRE_INT, sizeof(sec), &day,
			    SLRE_INT, sizeof(sec), &hour,
			    SLRE_INT, sizeof(sec), &minute,
			    SLRE_INT, sizeof(sec), &sec);

  if (regex_status != NULL) { return ERR_DATE_FORMAT;}
  if ((year < 1900) || (month < 1) || (month > 12) ||
      (day < 1) || (day > 31) ||  (hour < 0) || (hour > 23) ||
      (minute < 0) || (minute > 59) ||  (sec < 0) || (sec > 59)) {
    return ERR_DATE_RANGE;
  }
  return 0;
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
  char elem[3] = {'\0'};
  char edge[3] = {'\0'};
  char version_xdi[8] = {'\0'};
  char version_extra[MAX_LINE_LENGTH] = {'\0'};
  char errline[MAX_LINE_LENGTH] = {'\0'};
  char outerlabel[MAX_WORD_LENGTH] = {'\0'};
  double dval ;
  double *outer_arr, outer_arr0;
  long   *outer_pts;
  FILE *inpFile;
  long  file_length, ilen, index, i, j, k, nx, maxcol;
  long  npts_, ncols, icol, nheader, nwords, ndict;
  long  ignored_headerline, iret, ipt, nouter, iouter;
  int   is_newline, fnlen, mode, valid, stat;
  int   has_minusline, has_angle, has_energy;
  const char *regex_status;

  int n_edges = sizeof(ValidEdges)/sizeof(char*);
  int n_elems = sizeof(ValidElems)/sizeof(char*);

  iret = 0;


  /* initialize string attributes of thr XDIFile struct */

  strcpy(comments, " ");
  xdifile->comments = calloc(1025, sizeof(char));
  strcpy(xdifile->comments, comments);

  strcpy(elem, "  ");
  xdifile->element = calloc(3, sizeof(char));
  strncpy(xdifile->element, elem, 2);

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
    /* COPY_STRING(col_labels[i], tlabel); */
    /* COPY_STRING(col_units[i], ""); */
    col_labels[i] = tlabel;
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
      for (j=0; j<=ilen; j++) {
	free(textlines[j]);
      }
      return ERR_NOTXDI;
    }
    if (strncasecmp(cwords[0], TOK_VERSION, strlen(TOK_VERSION)) != 0)  {
      for (j=0; j<=ilen; j++) {
	free(textlines[j]);
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
    regex_status = slre_match(1, DATALINE, textlines[i], strlen(textlines[i]));
    if ((strlen(textlines[i]) > 3) && (regex_status == NULL)) {
  	/* (strncmp(textlines[i], TOK_COMM, 1) != 0))  { */
      break;
    }
  }
  nheader = i+1;
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
	  regex_status = slre_match(1, FAMILYNAME, words[0], strlen(words[0]));
	  if (regex_status != NULL) {
	    xdifile->nmetadata = ndict+1;
	    free(mkey);
	    for (k=0; k<=ilen; k++) {
	      free(textlines[k]);
	    }
	    return ERR_META_FAMNAME;
	  }

	  regex_status = slre_match(1, KEYNAME,  words[1], strlen(words[1]));
	  if (regex_status != NULL) {
	    xdifile->nmetadata = ndict+1;
	    free(mkey);
	    for (k=0; k<=ilen; k++) {
	      free(textlines[k]);
	    }
	    return ERR_META_KEYNAME;
	  }

	  COPY_STRING(xdifile->meta_families[ndict], words[0]);
	  COPY_STRING(xdifile->meta_keywords[ndict], words[1]);
	} else {
	  xdifile->nmetadata = ndict+1;
	  free(mkey);
	  for (k=0; k<=ilen; k++) {
	    free(textlines[k]);
	  }
	  return ERR_META_FORMAT;
	}
	/* printf(" metadata:  %ld | %s | %s\n", ndict, mkey, mval); */
	/* ndict,  words[0], words[1],  xdifile->meta_valuesn[dict]);*/
	if (strncasecmp(mkey, TOK_COLUMN, strlen(TOK_COLUMN)) == 0) {
	  j = atoi(mkey+7)-1;
	  if ((j > -1) && (j < MAX_COLUMNS)) {
	    ncols = make_words(mval, cwords, 2);
	    col_labels[j] = cwords[0];
	    if (ncols == 2) {
	      col_units[j] = cwords[1];
	    }
	    maxcol =  max(maxcol, j);
	  }
	} else if (strcasecmp(mkey, TOK_EDGE) == 0) {
	  for (j = 0; j < n_edges; j++) {
	    if (strcasecmp(ValidEdges[j], mval) == 0) {
	      strcpy(xdifile->edge, mval);
	      break;
	    }
	  }
	/* ELEMENT NAME */
	} else if (strcasecmp(mkey, TOK_ELEM) == 0) {
	  for (j = 0; j < n_elems; j++) {
	    if (strcasecmp(ValidElems[j], mval) == 0) {
	      /* COPY_STRING(xdifile->element, mval); */
	      strncpy(xdifile->element, mval, 2);
	      break;
	    }
	  }
	/* MONO D-SPACING */
	} else if (strcasecmp(mkey, TOK_DSPACE) == 0) {
	  if (0 != xdi_strtod(mval, &dval)) {
	    xdifile->nmetadata = ndict+1;
	    free(mkey);
	    for (k=0; k<=ilen; k++) {
	      free(textlines[k]);
	    }
	    return ERR_NONNUMERIC;
	  }
	  xdifile->dspacing = dval;
	/* OUTER ARRAY NAME */
	} else if (strcasecmp(mkey, TOK_OUTER_NAME) == 0) {
	  strcpy(xdifile->outer_label, mval);
	/* OUTER ARRAY VALUE */
	} else if (strcasecmp(mkey, TOK_OUTER_VAL) == 0) {
	  if (0 != xdi_strtod(mval, &dval)) {  free(mval); return ERR_NONNUMERIC;}	
	  outer_arr0 = dval ;
	} else if (strcasecmp(mkey, TOK_TIMESTAMP) == 0) {
	  j = xdi_is_datestring(mval);
	  if (0 != j) {
	    xdifile->nmetadata = ndict+1;
	    free(mkey);
	    for (k=0; k<=ilen; k++) {
	      free(textlines[k]);
	    }
	    return j;
	  }
	}
	/* free(mval); */
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
	free(mkey);
	for (k=0; k<=ilen; k++) {
	  free(textlines[k]);
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
  if (ignored_headerline > 0) { iret = ERR_IGNOREDMETA; }
  if (has_minusline == 0)     { iret = ERR_NOMINUSLINE; }

  /* check edge, element, return error code if invalid */
  valid = 0;
  for (j = 0; j < n_edges; j++) {
    if (strcasecmp(ValidEdges[j], xdifile->edge) == 0) {
      valid = 1;
      break;
    }
  }
  if (valid == 0) {  iret = ERR_NOEDGE; }

  valid = 0;
  for (j = 0; j < n_elems; j++) {
    if (strcasecmp(ValidElems[j], xdifile->element) == 0) {
      valid = 1;
      break;
    }
  }
  if (valid == 0) { iret =  ERR_NOELEM;}

  npts_ = ilen - nheader + 1;

  nouter = npts_ - 1;
  outer_arr = calloc(nouter, sizeof(double));
  outer_pts = calloc(nouter, sizeof(long));
  outer_arr[0] = outer_arr0;
  outer_pts[0] = 1;

  COPY_STRING(line, textlines[i]);
  ncols = make_words(line, words, MAX_WORDS);
 
  strcpy(xdifile->comments, comments);
  COPY_STRING(xdifile->filename, filename);

  maxcol++;

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
    iret = ERR_NODSPACE;
  }

  /* set size of data arrays */
  xdifile->array = calloc(ncols, sizeof(double *));
  for (j = 0; j < ncols; j++) {
    xdifile->array[j] = calloc(npts_+1, sizeof(double));
    if (0 != xdi_strtod(words[j], &dval)) {
      free(line);
      free(outer_arr);
      free(outer_pts);
      xdifile->narrays = ncols;
      xdifile->nmetadata = ndict+1;
      for (j=0; j<=ilen; j++) {
	free(textlines[j]);
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
	free(line);
	free(outer_arr);
	free(outer_pts);
	xdifile->narrays = ncols;
	xdifile->nmetadata = ndict+1;
	for (j=0; j<=ilen; j++) {
	  free(textlines[j]);
	}
	return ERR_NCOLS_CHANGE;
      }
      icol = min(ncols, icol);
      for (j = 0; j < icol; j++) {
	if (0 != xdi_strtod(words[j], &dval)) {
	  free(line);
	  free(outer_arr);
	  free(outer_pts);
	  xdifile->narrays = ncols;
	  xdifile->nmetadata = ndict+1;
	  for (j=0; j<=ilen; j++) {
	    free(textlines[j]);
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
  return iret;

}

_EXPORT(int)
XDI_get_array_index(XDIFile *xdifile, long n, double *out) {
  /* get array by index (starting at 0) from an XDIFile structure */
  long j;
  if (n < xdifile->narrays) {
    for (j = 0; j < xdifile->npts; j++) {
      out[j] = xdifile->array[n][j];
    }
    return 0;
  }
  return ERR_NOARR_INDEX;
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
  return ERR_NOARR_NAME;
}


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
  free(xdifile->outer_label);

  if ((err != -32) && (err != -128) && (err != -128)) {
    free(xdifile->filename);
  };

  if ((err < -1) || (err == 0)) {

    if ((err == 0) || (err < -128)) {
      for (j = 0; j < xdifile->narrays; j++) {
	free(xdifile->array[j]);
	free(xdifile->array_labels[j]);
	free(xdifile->array_units[j]);
      }
      free(xdifile->array);
      free(xdifile->array_labels);
      free(xdifile->array_units);
    };

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
    };
  }

  free(xdifile);
}
