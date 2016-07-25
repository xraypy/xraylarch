#!/usr/bin/env python
"""Help topics for on-line documentation and help in larch

The data here contain python variable holding text that
are used as principle help topics.

M. Newville Univ of Chicago, T. Trainor, Univ of Alaska Fairbanks (2005,2006)

"""
##
## usage notes:
##    to add a new top level help topic, simply create a variable named '_h_%s' % topic
## where 'topic' is a unique (case-insensitive!) name for a help topic.
##
## when  help(topic)
##
_h_Shell = """Larch command-line shell help:

"""

_h_Help =  """
   ================================
   = Help options =
    help          # this help
    help topics   # list topics for additional help
    help name     # help on specific topic, variable, or procedure
   ================================
"""

_h_Overview = """
This is Larch (Matt Newville and Tom Trainor 2009).

Larch is a data processing language designed to be
  - easy to use for novices.
  - complete enough for intermediate to advanced data processing.
  - data-centric, so that arrays of data are easy to manage and use.
  - easily extendable with python.

Larch uses Numeric Python and SciPy for all its numerical functionality,
so that processing data in arrays is both easy and fast. There is a wide
range of 'advanced numeric capabilities' for Larch, including complex
numbers, FFTs and non-linear least squares minimization.

Larch Features:

==Simple Syntax:
  Variable and function names are simple, undecorated strings.  The
  syntax is deliberately close to Python, so that

==Data Types:

  Named variables can contain any of the following data types: ints,
  floats, complex, strings, lists, dictionaries (hashes), NumPy arrays,
  or any other python data types.

  Multi-dimensional data can be accessed either element-by-element or with
  more complicated "slices":
        larch> x   = 1             # int
        larch> y   = 7 + 2j        # complex number:  real + imag'j'
        larch> arr = arange(10)    # simple array
        larch> print arr
            [0 1 2 3 4 5 6 7 8 9 10]
        larch> print arr[3]
            3
        larch> print arr[2:8]
            [2 3 4 5 6 7]
        larch> str = 'here is a string'
        larch> print str[0:7]
            here is

==Full Featured, extensible:

  Many useful functions for numerical data processing are built in to
  Larch.  More importantly, it is easy to add more functions, either
  from Python or as Larch procedures.

==Namespaces and Groups:

  Each variable and function lives in Group, which can be nested much
  like a file directory structure -- Group.Subgroup.Variable.  These is
  no limit on the number of subgroups, within a group or the level of
  nesting of groups.  This allows you to organize data,
     print DataSet1.Energy
     print DataSet2.Energy

  and so on. To access a variable, you can always use the Full name:
     print Group1.SubgroupA.Variable

  If you ask for a name that is NOT a Full name, larch tries to look it up.

  It does this by always having a "local group" which is always looked in first.
  If

  Unqualified names (ie, a name without a 'group.' prefix) will use a default
  order to determine which Group to associate with a name:  There is always
  a "Default Data Group" and a "Default Function Group" each of which can be
  changed during a Larch session.  At startup, there are two pre-defined groups:
  "_builtin", which contains many built in functions and constants (sin and pi,
  for example), and "_main".  At startup, "_main" is empty, and is set as the
  "Default Data Group" and "Default Function Group".

  When creating or assigning a variable without an explicit group name, the default
  Data Group is used.  When creating or assigning a procedure without an explicit
  group name, the default Function Group is used.

  When using (say, on the right-hand side of a statement) a variable or function with
  an unqualified group name, the first matching name in the list
     (Default Data Group, Default Function Group, "_main", "_builtin")

  is used.  The Default Data Group can be changed with
        larch> datagroup('mydata')

  and the Default Function Group can be changed with
        larch> funcgroup('myfuncs')

  Assigning a fully qualified variable or function to a group that previously did
  not exist will create that group:
        larch> x = 1
        larch> group1.x = 3.3
        larch> print x
            1
        larch> datagroup('group1')
        larch> print x
            3.3
        larch> print _main.x, group1.x
            1 3.3
        larch> show groups
            Default Data Group = group1
            Default Function Group = _main
            All Groups:
                _main  _builtin  group1

==Functions and Commands.  Functions and commands have similiar name structure as
  data (group.func,group.cmd).
  The default group name for functions and commands is _main (functions and commands with
  this group name do not need full name qualification).
  Eg. you can also assign variables variable values with setvar() function:
        larch> setvar('v', 2.3, group='group1')
        larch> print group1.v

  The potential advantage here is that 'v' and 'group1' are string types,
  not literal variable names, so they can be computed or passed in a
  procedure.

==Clean syntax for programming:
  The syntax is "Python Inspired", with some notable exceptions.  Most
  importantly, indentation level is not significant, and blocks end with
  with explicit 'end' statements.  A typical for-block will look like this:

        for i in range(10):
            print i
        endfor

  There are also while blocks and if-elif-else blocks:
        n = 0
        while n<10:
           print ' n = ',n
           if n==3: print 'here is 3!!'
               n = n + 1
           endwhile

        if n > 10:
            print 'No'
        elif n > 5 and n < 8:
            print 'Maybe'
        else:
            print 'Yep'
        endif

  A design goal is that well-formed larch code should be very easy to
  translate into valid python (and vice versa).

==User-defined functions (aka procedures):
  User defined functions can be written in larch:
        def  myfunc(arg1, option='test'):
             'documentation string'
              print 'this is my funcition ', arg1
              print 'optional param = ', option
              if type(option) != 'string':
                  print 'option must be a string!!'
                  return False
              endif
              value = sqrt(arg1)
              x.tmp = value
              return value > 10.
        enddef

  which could be called as
        larch> ret = myfunc(3., option = 'xx')
        larch> print ret, x.tmp
          False 1.73205080757

==dofile() function:
  you can run a file of larch commands with the dofile() function:
        larch> dofile('myfile.larch')

==eval() function:
  you can construct a larch expression on the fly from strings and execute it:

        larch> eval("%s.value = %f" %  ['group', 10.2])
        larch> print group.value
          10.2

==read_ascii() function:
  you can read in ASCII column data files very easily.

        larch> read_ascii('my.dat', group='f')
          ['f', 'x', ''y']

  this read 2 columns (labeled 'x' and 'y') from the column file and
  created the array variables f.x and f.y.  Also created was f.titles
  to hold the titles in the data file (non-numeric content at the top of
  the file) and f.column_labels

==On-line help:
  well, this is in progress....

==Easy to add your python functions, including getting access to all
  the 'data groups' inside your python function.

==Differences between larch and Python (for python users):
  -  larch has many builtins and assumes Numerical data.
  -  larch has no tuples. Lists are used in their place.
  -  indentation does not matter. blocks are ended with 'end***'
     (if / endif , for /endfor, def/enddef)
  -  when in doubt, assignment makes a copy, and does not give a reference
  -  data types are NOT objects, and so have no methods.  You must use
     procedural approaches
       x = arange(100)
       reshape(x,[10,10])   instead of x.shape = (10,10)
"""

##Strings

_h_Strings = """
  Working with strings:

  strings are sequence of text characters. To specify a string, you enclose it in quotes,
  either single or double quotes:
      larch>  x = 'this is a string'
      larch>  x = "A string with a ' in it "

  There are a few special characters that can be included in strings by 'escaping' them with a
  backlash character "\\".  The most important of these are '\\n' to write a newline character,
  and '\\t' to write a tab character.  Other escaped characters are:
      \\n   newline
      \\r   carriage return
      \\f   form feed
      \\v   vertical tab
      \\b   backspace
      \\t   tab
      \\a   bell
      \\"   literal "
      \\'   literal '
      \\\   the backslach character itself.

  You can escape quote characters ('\\"' or '\\'') so that they do not mark the end of a
  string sequence:
      larch> x = 'a string\\'s string'
      larch> y = "\\"a string with a double quote\\", he said."


  ==Multi-line Strings with Triple Quotes

  Larch allows multi-line strings (that is strings that span lines).  One simple way to do this is
  to include a newline character ('\\n') character in the string, but this is not always sufficient.
  Another way is to use triple quotes (three quotes in a row: either ''' or  \"\"\") to enclose the
  string.  With this approach, the newlines of the enclosed string are preserved:

     larch> long_string = '''Here is a mult-line string
     ...> line #2
     ...> line #3 of the long string '''

     larch> print long_string
     Here is a mult-line string
     line #2
     line #3 of the long string

  As with single quote strings, you have the choice of using single or double quotes, and can
  use escaped character and escaped quotes.

  ==String Formatting

  It is often desirable to create strings from program data. To do this, you *format a string*.
  This is done by putting format codes in a string and supplying values to fill in.  Format
  codes use the '%' character to mark the formatting to do.

  Following normal conventions, a formatted string for a floating point number might look like this:

      larch> print "x = %8.4f" % sqrt(12)
      x =   3.4641

  The "%8.4f" tells the formatting to format a floating point number (the 'f') with 8 total numbers
  and 4 numbers after the decimal point.   A plain '%' is used to separate the format string and the
  value(s) to format.  Other format codes:

      ......

  ==Using a dictionary for string formatting

    Borrowing from Python, larch also allow you to format a string using a dictionary instead of a
    simple list.  This can be a big advantage when formatting many values or formatting data from
    complicated data structures.  In this method, you explicitly set the dictionary key to use by
    naming them between the '%' and the format code:

      larch> data  = {'name':'File 1', 'date':'Monday, April 3, 2006', 'x': 12.4}
      larch> print " %(name)s , x = %(x)f" % data
      File 1 , x = 12.4

"""

# dictionaries
_h_Dicts = """
  Working with dictionaries:

"""

# arrays
_h_Arrays = """
  Working with arrays:

"""

# lists
_h_Lists = """
  Working with lists:

"""

# data types
_h_DataTypes = """
   Supported data types:
"""

# data types
_h_Groups = """
Working with groups:
"""

# python
_h_Python = """
Working with python and python modules:
"""

#
_h_Control = """
   Help on Programming Control structures (conditionals, loops, etc)

   Program Control structures are important for controlling what parts of
   a program are run.  If you're familiar with other programming languages,
   the concepts and syntax here should be fairly straightforward.

   The basic concept here is to define blocks of code (that is multiple lines
   of code) to be run as a group.  This allows the block of code to be run
   only under some conditions, or to be run repeatedly with different values
   for some variables in the block.

   The syntax of larch uses a colon ':' and a small number of keywords to define
   the blocks of code:
       if x==0:
          print 'cannot divide by zero'
       else:
          x = 2 /x
       endif


 = If statements:

   if statements run a block of code only if some condition is met.  Since this
   is so common, there are a few variations allowed in larch.  First is the
   one line version:

       if x<0:  x = -x

   which will set x to -x (that is, this will make sure x>=0).  In general, the
   if statement looks like:
       if condition:

   where the ending ':' is important (to indicate where the condition end).
   The "condition" is a statement that is evaluated as a boolean value (either
   True or False -- all numeric values are True except 0.0).  The boolean
   operations 'and', 'or' , and 'not' to construct complex conditions:

       if x>0 and x<10:

       if (x>0 and (b>1 or c>1)):


   A warning: in many programming languages multiple conditions can be relied upon
   to only evaluate until the truth of the statement can be determined.  This is NOT
   the case in larch: the entire statement may be evaluated.

   The second version uses the same 'if condition:', but on a line by itself, followed
   by  multiple statements.  This version ends with 'endif' to indicate how far the
   block of code extends:
       if x < 0  :
           x = -x
           print ' x set to ',x
       endif

   Next, there's the 'if-else-endif' version which runs either one block or the
   other, and looks like this (note the
       if x<0:
           x = -x
           print ' x set to ',x
       else:
           print ' x was positive to begin with'
       endif

   The final and most complete variation uses 'elif' (pronounced "else if") to allow
   multiple conditions to be tested:

       if x<0:
           x = -x
           print ' x set to ',x
       elif x>10:
           x = 10
           print ' x was too big, set to ', x
       else:
           print ' x was OK to begin with'
       endif

   Multiple 'elif' blocks can be given, though all 'elif' statements must be
   after the 'if' statements, and an 'else' statement (if present) must be last.
   And the entire construct must end with an 'endif'

   In such constructs, the first block with a condition that is True, and no other
   blocks will be run.

 = For loops:

   for loops repeat a block of code, usually incrementing some value used in
   the loop.  Usually, a for loop runs a predictable number of times (see the
   section below on Break and Continue for when it does not!). A for loop
   looks like:

       for i in [1,2,3]:
           print i, i*i
       endfor

   The basic syntax for the first line is 'for <variable> in <list>:'  The list
   can be either a real list or a numerical array -- a very common approach is to
   use the range() function to generate a list of numbers:
       for i in range(10):
           print i, 10-i, i*(10-i)
           if i < 2: print ' i < 2!! '
       endfor

   The block is run repeatedly with the loop variable i set to each value in the
   list.

   There is also a 'one-line' version of the for loop:

       for i in [1,2,3]: call_some_function(i)


 = While loops:

   while loops are similar to for loops, repeatedly running a block of code
   as long as some condition is true:

      x = 1
      while x<4:
         print x
         x = x + 1
      endwhile

   prints
     1.0
     2.0
     3.0

   Beware that a while loop makes it easy to make an "infinite loop" (for example, if
   the value of x had not been increased in the block).

 = Break and Continue in For and While loops

   In both for loops and while loops, the block can be exited with a 'break' statement.


 = Try / Except blocks:

   Sometimes error happen, and it is desirable to run some block of code

       x = 0
       a = 2.
       try:
           y = a/ x
       except:
           print "OK,  that did not work so well!"
       endtry
"""

_h_If = ""
_h_For = ""
_h_While = ""
_h_Try = ""
_h_Builtin = ""
_h_Functions = ""
_h_Procedures = ""
_h_String_Formatting = "String Formatting"

def generate():
    topics = {'':_h_Help}
    for key,val in globals().items():
        if key.startswith('_h_'):
            name = key[3:].lower().replace('_',' ')
            topics[name] = val

    tnames = ['== Help topics ==']
    s = ''

    topnames = sorted(topics.keys())
    nx= 2 + sorted([len(i) for i in topnames])[-1]

    fmt = "%%%i.%is" % (nx,nx)
    for t in topnames:
        s = "%s %s" % (s,fmt%(t+(' '*nx)))
        if len(s) > 50:
            tnames.append(s)
            s = ''
    tnames.append(s)
    topics['topics'] = '\n'.join(tnames)

    return topics
