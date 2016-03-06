#!/usr/bin/env python
"""
handle input Text for Larch -- inclides translation to Python text
"""
from __future__ import print_function
from six.moves import input
from .utils import isValidName, isNumber, isLiteralStr, find_delims

def strip_comments(sinp, char='#'):
    "find character in a string, skipping over quoted text"
    if sinp.find(char) < 0:
        return sinp
    i = 0
    while i < len(sinp):
        tchar = sinp[i]
        if tchar in ('"',"'"):
            eoc = sinp[i+1:].find(tchar)
            if eoc > 0:
                i = i + eoc
        elif tchar == char:
            return sinp[:i].rstrip()
        i = i + 1
    return sinp

def get_DefVar(text):
    """
    looks for defined variable statement, of the form
       >>   def varname = exression

    returns (varname, expression) if this is a valid defvar statement
    or None, None if not a valid defvar statement
    """
    if text.find('=') > 0 and text.startswith('def '):
        t = text[4:].replace('=',' = ').strip()
        words = t.split()
        if len(words) > 2 and words[1] == '=':
            iequal = t.find('=')
            iparen = t.find('(')
            icolon = t.find(':')
            if iparen < 0 :
                iparen = len(t)+1
            if icolon < 0 :
                icolon = len(t)+1
            # print iequal, iparen, icolon, words[0], isValidName(words[0])
            if (iequal < iparen and iequal < icolon and
                isValidName(words[0])):
                return words[0], t[iequal+1:].strip()

    return None, None


OPENS, CLOSES, QUOTES, BSLASH, COMMENT = '{([', '})]', '\'"', '\\', '#'
DBSLASH = "%s%s" % (BSLASH, BSLASH)

class InputText:
    """Input Larch Code:  handles loading and reading code text, and
    providing blocks of compile-able python code to be converted to AST.

    InputText accepts and stores single or multiple lines of input text,

    including as from an interactive prompt, watching for blocks of code,
    and keepin track of whether a block are complete.

    When asked for the next block of code, it emits blocks of valid
    (hopefully!) python code ready to parsed by 'ast.parse'

    Uses a FIFO (First In, First Out) buffer to allow mixing of input/output.
    Can read from a specified input source for 'interactive' mode

    usage:

    >>> text = InputText()
    >>> s = 'a statement'
    >>> text.put(s)   # add lines of text
    >>> text.get(s)   # get complete code block, ready for Compiler.eval


    the following translations are made from valid Larch to valid Python:

    1. Block Indentation:
        larch blocks may end with one of the tokens:
            ('end', 'endXXX', '#end', '#endXXX')
        for an 'XXX' block (one of 'if', 'for', 'while', 'try', and 'def')
        where the token starts a line of text, followed by whitespace or
        a comment starting with a '#'.

    2. Defined Parameters:
        larch uses 'def VarName = Expression' for Defined Parameters
        (the expression is stored and accessing the VarName causes the
        expression to be re-evaluated)

        The tokens are found with "def" "varname" "=" "text of expression"
        and then translated into
              param(name="varname", expr="text of expression")

    3. Command Syntax:
        larch allows lines of code which execute a function without return
        value to be viewed as "commands" and written without parentheses,
        so that the function call
             function(x, y)
        can be written as
             function x, y

        Note that 'function' must be in _sys.valid_commands for this to work.

    4. Print:
        as a special case of rule 3, and because Python is going through
        changes in the syntax of "print", print statements are translated
        from either "print(list)" or "print list" to
             _builtin._print(list)

    """
    indent = ' '*4
    ps1 = ' >'
    ps2 = '....>'
    block_friends = {'if':    ('else', 'elif'),
                     'for':   ('else',),
                     'def':   (),
                     'try':   ('else', 'except', 'finally'),
                     'while': ('else',) }

    defpar = "_builtin.param(expr='%s', name='%s')"

    nonkey = 'NONKEY'

    empty_frame = (None, None, -1)

    def __init__(self, prompt=None, interactive=True, input=None,
                 filename=None, _larch=None):
        if prompt is not None:
            self.ps1 = prompt
        self.input = None
        self._larch = _larch
        self.interactive = interactive
        self.lineno = 0
        self.filename = filename or '<stdin>'
        if interactive:
            self.input = input or self.__defaultInput
        self.clear()

    def readfile(self, fname):
        fh = open(fname, 'r')
        self.put(fh.read(), filename=fname, lineno=0)
        fh.close()

    def put(self, text, filename=None, lineno=None):
        """add line of input code text"""
        self.fname = filename or self.filename or '<stdin>'
        if lineno is not None:
            self.lineno = lineno

        def addTextInput(txt):
            complete = self.__isComplete(txt)
            self.input_buff.append((txt, complete,
                                    self.eos, self.fname, self.lineno))
            self.lineno += 1
            # print(' Add : ', self.lineno, complete, self.eos, self.delims, txt)
            return complete

        for t in text.split('\n'):
            self.input_complete = addTextInput(t)

        if self.interactive:
            self.prompt = self.ps2
            while not self.input_complete:
                t = self.input()
                if len(t) > 0:
                    self.input_complete = addTextInput(t)

        if self.input_complete:
            self.prompt = self.ps1
            nkeys, nblock = self.convert()

        return self.input_complete

    def get(self):
        """get compile-able block of python code"""
        if len(self) > 0:
            if not self._fifo[0]:
                self._fifo.reverse()
                self._fifo[0].reverse()
            try:
                return  self._fifo[0].pop()
            except IndexError:
                msg = 'InputText out of complete text'
                if self._larch is None:
                    raise IndexError(msg)
                else:
                    self._larch.raise_exception(None, exc=IndexError, msg=msg)
        return self.empty_frame

    def clean_text(self, text):
        """  clean up text: strip comments,etc"""
        text  = text.strip().rstrip()
        # here we replace '#end' with '&end' so that it is not removed
        # by strip_comments.  then below, we look for '&end' as an
        # end-of-block token.
        if text.startswith('#end'):
            text = '&end%s' % text[4:]
        return strip_comments(text)

    def convert(self):
        """
        Convert input buff (in self.input_buff) to valid python code
        and stores this (text, filename, lineno) into _fifo buffer
        """
        indent_level = 0
        oneliner  = False
        startkeys = self.block_friends.keys()
        self.input_buff.reverse()
        while self.input_buff:
            text, complete, eos, fname, lineno = self.input_buff.pop()

            text = self.clean_text(text)

            long_text = eos in '"\''
            sindent = self.indent*(indent_level+1)
            while not complete:
                tnext, complete, xeos, fname, lineno2 = self.input_buff.pop()
                text = self.clean_text(text)
                if long_text:
                    text = "%s\n%s" % (text, tnext)
                else:
                    text = "%s\n  %s%s" % (text, sindent, tnext)



            if text.startswith('"') or text.startswith("'"):
                delim = text[0]
                if text[0:3] == text[0]*3: # triple quote
                    delim = text[0:3]
                while not find_delims(text, delim=delim)[0]:
                    tnext, complete, eos, fname, lineno2 = self.input_buff.pop()
                    text = "%s\n %s%s" % (text, sindent, tnext)

            txt   = text.replace('(', ' (').replace(')', ' )')
            words = txt.split(' ', 1)
            thiskey = words.pop(0).strip()

            word2 = ''
            if len(words) > 0:
                word2 = words[0].replace(',', ' ').split()[0]

            if thiskey.endswith(':'):
                thiskey = thiskey[:-1]

            prefix, oneliner = '', False

            if thiskey in startkeys:
                # check for defined variables
                if thiskey == 'def':
                    dname, dexpr = get_DefVar(text)
                    if dname is not None and dexpr is not None:
                        if "'" in dexpr:
                            dexpr.replace("'", "\'")
                        text = self.defpar % (dexpr, dname)
                        thiskey = self.nonkey

                # note that we **re-test** here,
                # as thiskey may have changed above for defined variables
                if thiskey in startkeys:
                    if text.find(':') < 1:
                        msg = "%s statement needs a ':' at\n  %s" % (thiskey,
                                                                     text)
                        if self._larch is None:
                            raise SyntaxError(msg)
                        else:
                            self._larch.raise_exception(None, exc=SyntaxError, msg=msg, expr=text)
                    elif text.endswith(':'):
                        self.current = thiskey
                        self.keys.append(thiskey)
                        self.friends = self.block_friends[thiskey]
                        self.endkeys = ('end', 'end%s'% thiskey,
                                        '&end', '&end%s'% thiskey)
                    else: # one-liner form
                        oneliner = True
            elif thiskey in self.endkeys: # end of block
                if not thiskey.startswith('#'):
                    prefix = '#'
                if len(self.keys) != 0:
                    self.current = None
                    self.friends = ()
                    self.keys.pop()
                    if len(self.keys)>0:
                        self.current = self.keys[-1]
                        self.friends = self.block_friends[self.current]
                        self.endkeys = ('end',  'end%s'%self.current,
                                        '&end', '&end%s'%self.current)

            elif not text.endswith(')') and self.__isCommand(thiskey, word2):
                # handle 'command format', including 'print'
                text = '%s(%s)' % (thiskey, text[len(thiskey):].strip())
            indent_level = len(self.keys)
            if (not oneliner and len(thiskey)>0 and
                (thiskey == self.current or thiskey in self.friends)):
                indent_level = indent_level - 1

            if indent_level < 0:
                msg = 'impossible indent level!'
                if self._larch is None:
                    raise SyntaxError(msg)
                else:
                    self._larch.raise_exception(None, exc=SyntaxError, msg=msg)

            pytext = '%s%s%s' % (self.indent*indent_level,
                                 prefix, text)
            self.block.append(pytext)
            if len(self.keys) == 0:
                outtext = '\n'.join(self.block)
                if '\n' in outtext:  outtext = outtext  + '\n'
                self._fifo[1].append((outtext, fname,
                                      1+lineno-len(self.block)))
                self.block = []

        return len(self.keys), len(self.block)

    def clear(self):
        "clear the input"
        self.prompt = self.ps1
        self._fifo  = [[], []]
        self.block  = []
        self.keys   = []
        self.current = None
        self.endkeys = ()
        self.friends = ()
        self.parens = dict(zip(OPENS, CLOSES))
        self.delims = []
        self.eos = ''
        self.in_string   = False
        self.input_buff  = []
        self.input_complete = True

    def __isCommand(self, key, word2):
        """ decide if a keyword and next word are of the form
          'command arg, ...'
        which will get translated to
          'command(arg, ...)'
        to allow 'command syntax'
        """
        # this could be in one long test, but we simplify:
        # first test key:
        if (not isValidName(key) or
            key in self.friends or
            key.startswith('#') or
            len(key) < 1 or len(word2) < 1):
            return False


        if self._larch is not None:
            comms = self._larch.symtable.get_symbol('_sys.valid_commands',
                                                    create=True)
            if key not in comms:
                return False

        # next test word2
        return (isValidName(word2) or isNumber(word2) or
                isLiteralStr(word2) )

    def __isComplete(self, txt, verbose=False):
        """returns whether input text is a complete:
        completeness here means the text (possibly multiline)
        contains completed quotes, and parens, braces, brackets
        are matched (including nesting) and the text does not
        end with a backslash.

        state information from previous text_complete() are stored in:
           self.eos    = substring to look for 'end of string'
                        (self.eos == "" means string is complete)
           self.delims = current list of closing delims needed to match
                         opening delims seen so far.
        """

        def find_eostring(txt, eos, istart):
            while True:
                inext = txt[istart:].find(eos)
                if inext < 0:  # reached end of text before match found
                    return eos, len(txt)
                elif (txt[istart+inext-1] == BSLASH and
                      txt[istart+inext-2] != BSLASH):  # matched quote was escaped
                    istart = istart+inext+len(eos)
                else: # real match found! skip ahead in string
                    return '', istart+inext+len(eos)-1

        if self.eos != '':
            self.eos, i = find_eostring(txt, self.eos, 0)
            return self.eos == ''

        i = 0
        while i < len(txt):
            c = txt[i]
            if c in QUOTES:
                self.eos = c
                if txt[i:i+3] == c*3:
                    self.eos = c*3
                istart = i + len(self.eos)
                self.eos, i = find_eostring(txt, self.eos, istart)
            elif c in OPENS:
                self.delims.append(self.parens[c])
            elif c in CLOSES and len(self.delims)>0 and c == self.delims[-1]:
                self.delims.pop()
            elif c == COMMENT and self.eos == '': # comment char outside string
                i = len(txt)
            i += 1

        complete = (self.eos == '' and len(self.delims) == 0 and
                    not txt.rstrip().endswith(BSLASH))
        if verbose:
            print(' %s:%s:%i:%s ' % (complete, self.eos, len(self.delims), txt))
        return complete


    def __len__(self):
        return len(self._fifo[0]) + len(self._fifo[1])

    def __defaultInput(self, prompt=None):
        if prompt is None:
            prompt = self.prompt
        return input(prompt)

if __name__ == '__main__':
    inp = InputText()
    inp.interactive = False
    inp.put("x = 1;a = x/3.;b = sqrt(")
    inp.put("a)")

    while inp:
        print( inp.get())
    print( 'done')

    buff = ['x = 1',
            'y = x /2',
            'for i in range(10):',
            ' print i',
            '    j = x *y * i',
            '#endfor',
            'print j ',
            'def x1a = x + y ',
            'if x < 1: ',
            '  u = x/2',
            '  if u < 1:  u = 2 ',
            'else: ',
            '  u = x/3',
            '#endif ',
            'set y = 22, z=29',
                 '# comment!',
                 '"quote"',
                 '"escaped \\""',
                 'x = "escaped \\" quote!"',
                 '"""triple quote!"""',
                 'x = """triple quote %s """ % ("x")',
                 "x = {'H': 1, 'He':2}",
                 '''""" this is a
                 multiline
                 triple-quote"""
                 ''',

                 '''""" this is a
                 multiline with 'quotes'
                 of both 'single' and "double" flavors!
                 and # a single commented 'quote
                 and a non-comment single quote:
                 we're on in this together quote...
                 nice, huh!
                 """
                 ''',
                 """x = {'a': '''multiline
                  dict value''',
                  'b':10,
                 'c':20} """,

            ]
    buff = ['''  """x = {'a': 'value',
    'b':10,
    'c':20} """
    ''']


    for t in buff:
        inp.put(t)

    import ast
    while inp:
        text, fname, lineno = inp.get()
        text.rstrip()
        print( '=====')
        print( '%s' % text)
        a = ast.parse(text)
        print( ast.dump(a, include_attributes=False))

    must_fail = [' " ',
                 " we're all in this together ",
                 ' ( # )',  ' {',
                 'x = "e x\\"',
                 'x = " a # and a () ',
                 ]

#
#     testcode = """
#  y = 4
#  z = 1
# # start my for loop
# for i in range(100):
# y = y * (1 + i) / 7.
#    while y < 9:
#
#       y = y + 3
# # comment in a nested block
#       print 'XXX ', y
#       endwhile
#    if y > 4000: break
#    if (y < 20 and
#        y != 7):
#       y = y-2
#     endif
# print i, y
# endfor
# print 'final y = ', y
# """
# #    for i in testcode.split('\n'):     inp.put(i.strip())
#
