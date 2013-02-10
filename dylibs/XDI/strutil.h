#define CR "\n"
#define CRLF "\n\r"

#define MAX_LINE_LENGTH 8192 /* Max chars in a line */
#define MAX_LINES 16384      /* Max number of lines */
#define MAX_WORDS 128

/* Read function */
int readlines(char *filename, char **lines);
int make_words(char *inp, char **out, int maxwords);
int split_on(char *inp, char *delim, char **out) ;

#define COPY_STRING(dest,src)  dest=calloc(strlen(src)+1, sizeof(char));\
  strcpy(dest, src);


