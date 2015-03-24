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
#include <ctype.h>

#include "strutil.h"

char *strtrim(char *str) {
  /* trim leading and ending whitespace from a string */
  char *end;

  /* removing leading whitespace */
  while (isspace(*str)) {str++;}

  if (*str == 0)  return str;

  /* find then trim ending whitespace */
  end = str + strlen(str) - 1;
  while (end > str && isspace(*end)) {end--;}

  /* put null at new end of string */
  *(end+1) = 0;
  return str;
}

/*-------------------------------------------------------*/
/* read array of text lines from an open data file  */
int readlines(char *filename, char **textlines) {
  /* returns number of lines read, textlines should be pre-declared
      as char *text[MAX] */

  FILE *finp;
  char *thisline;
  char *text;
  long file_length, index, i, ilen;
  int  is_newline;
  char *orig_text, *orig_thisline;

  finp = fopen(filename, "r");
  if (finp == NULL) {
    printf("Error opening %s: %s\n", filename, strerror(errno));
    return -errno;
  }

  fseek(finp, 0L, SEEK_END);
  file_length = ftell(finp);
  rewind(finp);

  text = calloc(file_length + 1, sizeof(char));
  thisline = calloc(MAX_LINE_LENGTH, sizeof(char));
  /* need to save a pointers to the beginning of the original strings so they can be freed at the end of this function */
  orig_text = text;
  orig_thisline = thisline;

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
    thisline = strtrim(thisline);
    ++ilen;
    textlines[ilen]= calloc(strlen(thisline) + 1, sizeof(char));
    strcpy(textlines[ilen], thisline);
    if (ilen >= MAX_LINES) {
      printf("\nfile has too many lines.  Limit is %d %d\n " , MAX_LINES, EFBIG);
      return -EFBIG;
    }
  }
  /* free strings */
  text = orig_text;
  thisline = orig_thisline;
  free(text);
  free(thisline);
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

