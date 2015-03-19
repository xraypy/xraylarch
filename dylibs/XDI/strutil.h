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

#define CR "\n"
#define CRLF "\n\r"

#define MAX_WORD_LENGTH 8192 /* Max length of an interpretable word */
#define MAX_LINE_LENGTH 8192 /* Max chars in a line */
#define MAX_LINES 16384      /* Max number of lines */
#define MAX_WORDS 128

/* Read function */
int readlines(char *filename, char **lines);
int make_words(char *inp, char **out, int maxwords);
int split_on(char *inp, char *delim, char **out) ;

#define COPY_STRING(dest,src)  dest=calloc(strlen(src)+1, sizeof(char));\
  strcpy(dest, src);


