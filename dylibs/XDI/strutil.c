/* read XDI file in C */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <errno.h>

#include "strutil.h"
/*-------------------------------------------------------*/
/* read array of text lines from an open data file  */
int readlines(char *filename, char **textlines) {
  /* returns number of lines read, textlines should be pre-declared
      as char *text[MAX] */

  FILE *finp;
  char  thisline[MAX_LINE_LENGTH];
  char *text, *c;
  long file_length, index, i, ilen;
  int  is_newline;

  finp = fopen(filename, "r");
  if (finp == NULL) {
    printf("Error opening %s: %s\n", filename, strerror(errno));
    return -errno;
  }

  fseek(finp, 0L, SEEK_END);
  file_length = ftell(finp);
  rewind(finp);

  text = calloc(file_length + 1, sizeof(char));
  if (text == NULL ) {
    printf("\nnot enough memory to read file.\n");
    return -errno;
  }

  fread(text, file_length, 1, finp);
  fclose(finp);

  ilen = -1;
  while (*text) {
    index = 0;
    is_newline = 0;
    while (*text) {
      if (!is_newline) {
	if (*text == 13 || *text == 10) {
	  is_newline = 1;
	}
      } else if (*text != 13 && *text != 10) {
	break;
      }
      thisline[index++] = *text++;
    }
    thisline[index] = '\0';
    ++ilen;
    textlines[ilen]= calloc(strlen(thisline) + 1, sizeof(char));
    strcpy(textlines[ilen], thisline);
    if (ilen >= MAX_LINES) {
      printf("\nfile has too many lines.  Limit is %d %d\n " , MAX_LINES, EFBIG);
      return -EFBIG;
    }
  }
  return ilen;
}

int make_words(char *inp, char **out, int maxwords) {
  int  i, nwords;
  nwords = 0;
  for (i = 0; i < maxwords; i++) {
    /* skip leading whitespace */
    while (isspace(*inp)) {inp++; }

    if (*inp != '\0') {
      out[nwords++] = inp;
    } else {
      out[nwords] = 0;
      break;
    }
    while (*inp != '\0' && !isspace(*inp)) { inp++; }
    /* terminate arg: */
    if (*inp != '\0' && i < maxwords-1) {*inp++ = '\0'; }
  }
  return nwords;
}
/* split input string on delim, returning either 1 or 2 words to out */
int split_on(char *inp, char *delim, char **out) {
  int  i, nwords;
  nwords = 0;
  inp[strcspn(inp, CRLF)] = '\0';
  for (i = 0; i < 2; i++) {
    /* skip leading whitespace */
    while (isspace(*inp)) {inp++; }
    if (*inp != '\0') {
      out[nwords++] = inp;
    } else {
      out[nwords] = 0;
      break;
    }
    while (*inp != '\0' && *inp != *delim) {
      inp++;
    }
    /* terminate arg: */
    if (*inp != '\0' && i < 1){ *inp++ = '\0'; }
  }
  return nwords;
}

