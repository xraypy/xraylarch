==== Larch: a simple macro language for scientific programming ====

Larch is a macro language intended to be embedded in scientific
applications.

The symbol table is also much simpler.
The basic approach of this version of larch is to convert input larch
program text, and convert it to valid python code (inputText.py).
This python code is then parsed into an AST tree (compiler.py),
which is then interpreted using a simple interpreter that uses a
local symbol table (symbolTable.py) for name lookup and
resolution.

By itself, this gives several benefits:

   1. the intermediate python code can be saved so that code
      validation and translation of larch to python are now trivial

   2. the parsed AST tree is guaranteed (at least as far as python
      itself is) to be correct.

   3. Interpreting the AST tree is very simple, including all loop
      and control-flow code, and the resulting compiler.py is very
      much simpler than the earlier version.
 
In addition, the symbol table is simplified so that a symbolTable
contains python objects and Groups (simple containers for other
objects and Groups). Namespaces are built simply usin attributes
of the Group class.  That is, attribute lookup is heavily used,
and symbols just python objects.

Special Larch-specific objects (defined variable, procedures) are
just constructed as classes, and so no special Symbol class is
needed.


=== Syntax differences between LARCH and Python ====

1. larch does not use indentation level. Rather a block
   is ended with one of
      'end', '#end', 'endXXX', or '#endXXX' 
   for XXX  = 'if', 'for', 'def', 'while', 'try'

   The  '#end' version allows code to be both valid larch
   and python.

2. a Defined Variable can be defined with 
        def [symbol_name] = expression

   In larch->python translation, this is converted to 
     _builtin._definevar_('symbol_name','expression')
   which creates a DefinedVariable() instance that
   stores the ast representation of the expression.  

   On each name lookup for a DefinedVariable(), the 
   expression is re-evaluated and the appropriate 
   value inserted.

3. command syntax is allowed in some cases, so that parentheses
   are not required for all function calls.

   If the first word of a line of code contains a word that is
   is a valid symbol name (and not a reserved word) and the second 
   word that is either a valid name or a number, and if the line 
   does not end with a ')', the first word is taken as a function
   name and parentheses are added, so that 
      command arg1, arg2   => command(arg1, arg2)
   and so on.

