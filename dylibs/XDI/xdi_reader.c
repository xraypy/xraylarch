/* read XDI file in C */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <errno.h>
#include "strutil.h"
#include "xdifile.h"

#ifndef min
#define min( a, b ) ( ((a) < (b)) ? (a) : (b) )
#endif

void show_syntax(void) {
  /* show command line syntax */
  printf("\nSyntax: xdi_reader filename\n");
}

/*-------------------------------------------------------*/
int main(int argc, char **argv) {
  XDIFile *xdifile;
  long  file_length, ilen, index, i, j, ret;
  long  ncol, nrows, nheader, nwords, ndict, nout;
  int   is_newline, fnlen, k;
  double *tdat;

  /* require 2 arguments! */
  if (argc < 2) {
    show_syntax();
    return 1;
  }

  /* read xdifile */
  xdifile = malloc(sizeof(XDIFile));
  ret = XDI_readfile(argv[1], xdifile);

  /* react to a terminal error */
  if (ret < 0) {
    printf("Error reading XDI file '%s':\n     %s\t(error code = %ld)\n",
	   argv[1], xdifile->error_message, ret);
    XDI_cleanup(xdifile, ret);
    free(xdifile);
    return 1;
  }

  /* react to a warning */
  if (ret > 0) {
    printf("Warning reading XDI file '%s':\n     %s\t(warning code = %ld)\n\n",
	   argv[1], xdifile->error_message, ret);
  }

  /* print some basic information about the file to the screen */
  printf("#------\n# XDI FILE Read %s VERSIONS: |%s|%s|\n" ,
	 xdifile->filename, xdifile->xdi_version, xdifile->extra_version);
  printf("# Elem/Edge: %s|%s|\n", xdifile->element, xdifile->edge);
  printf("# User Comments:\n%s\n", xdifile->comments);

  /* print all the metadata to the screen, validate each item */
  printf("# Metadata(%ld entries):\n", xdifile->nmetadata);
  printf(" --- \n");
  for (i=0; i < xdifile->nmetadata; i++) {
    printf(" %s / %s => %s\n",
	   xdifile->meta_families[i],
	   xdifile->meta_keywords[i],
	   xdifile->meta_values[i]);

    j = XDI_validate_item(xdifile, xdifile->meta_families[i], xdifile->meta_keywords[i], xdifile->meta_values[i]);
    if (j!=0) {
      printf("-- Warning for %s.%s: %s\t(warning code = %ld)\n\t%s\n",
	     xdifile->meta_families[i], xdifile->meta_keywords[i], xdifile->meta_values[i], j, xdifile->error_message);
    }
  }

  /* do the test for REQUIRED metadata */
  j = XDI_required_metadata(xdifile);
  printf("\n# check for required metadata -- (requirement code %ld):\n%s\n", j, xdifile->error_message);

  /* do the test for RECOMMENDED metadata */
  j = XDI_recommended_metadata(xdifile);
  printf("\n# check for recommended metadata -- (recommendation code %ld):\n%s\n", j, xdifile->error_message);

  /* print the data table to the screen */
  nout = min(4, xdifile->npts - 2);
  printf("# Arrays Index, Name, Values: (%ld points total): \n", xdifile->npts);
  tdat = (double *)calloc(xdifile->npts, sizeof(double));
  for (j = 0; j < xdifile->narrays; j++ ) {
    ret = XDI_get_array_name(xdifile,xdifile->array_labels[j], tdat);
    printf(" %ld %9s: ", j, xdifile->array_labels[j]);
    for (k=0; k < nout; k++) {  printf("%.8g, ", tdat[k]); }
    /* printf("\n"); */
    printf("..., %.8g, %.8g\n", tdat[xdifile->npts-2], tdat[xdifile->npts-1]);
  }

  if ((strlen(xdifile->outer_label) > 0)&& xdifile->nouter > 1) {
    printf("OUTER Array (2D data): %ld, %s\n", xdifile->nouter, xdifile->outer_label);
    for (j = 0; j < 5; j++) { /*xdifile->nouter;  j++) {*/
      printf(" %ld/%g,  " , xdifile->outer_breakpts[j], xdifile->outer_array[j]);
    }
    printf(" ..., ");
    nout = xdifile->nouter;
    for (j = nout-4; j < nout; j++) { 
      printf(" %ld/%g,  " , xdifile->outer_breakpts[j], xdifile->outer_array[j]);
    }
    printf("\n");
  }

  /* free memory before leaving */
  free(tdat);
  XDI_cleanup(xdifile, 0);
  free(xdifile);
  return 0;
}
