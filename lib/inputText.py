from __future__ import print_function

from .util import isValidName, isNumber, isLiteralStr, strip_comments

def get_DefVar(text):
    """
    looks for defined variable statement, of the form
       >>   def varname = exression

    returns (varname, expression) if this is a valid defvar statement
    or None,None if not a valid defvar statement
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
        for an 'XXX' block (one of 'if','for','while','try', and 'def')
        where the token starts a line of text, followed by whitespace or
        a comment starting with a '#'.

    2. Defined Variables:
        larch uses 'def VarName = Expression' for a Defined Variable
        (the expression is stored and accessing the VarName causes the
        expression to be re-evaluated)

        The tokens are found with "def" "varname" "=" "text of expression"
        and then translated into
             _builtin._definevar_("varname","text of expression")

    3. Command Syntax:
        larch allows lines of code which execute a function without return
        value to be viewed as "commands" and written without parentheses,
        so that the function call 
             function(x, y)
        can be written as
             function x, y
             
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
                     'for':   ('else'),
                     'def':   (),
                     'try':   ('else', 'except', 'finally'),
                     'while': ('else') }

    parens = {'{':'}', '(':')', '[':']'}
    fcn_defvar= "_builtin.definevar"
    fcn_print = "_builtin._print_"
    nonkey    = 'NONKEY'

    empty_frame = (None, None, -1)
    
    def __init__(self, prompt=None,
                 interactive=True, input=None,
                 filename=None):
        self.prompt = prompt or self.ps1
        self.input = None
        self.interactive = interactive
        self.lineno   = 0
        self.filename = filename or '<StdInput>'
        if interactive:
            self.input = input or self.__defaultInput
        self._fifo     = [[],[]]
        self.block     = []
        self.keys      = []
        self.current   = None
        self.endkeys   = ()
        self.friends   = ()

        self.delims = []
        self.in_string   = False
        self.eos         = ''
        self.input_buff  = []
        self.input_complete = True
                
    def readfile(self,fname):
        fh = open(fname,'r')
        self.put(fh.read(),filename=fname,lineno=0)
        fh.close()

    def put(self, text, filename=None, lineno=None ):
        """add line of input code text"""
        fname = filename or self.filename or '<StdInput>'
        if lineno is not None:
            self.lineno = lineno

        def addText(text, lineno=None):
            self.input_complete = self.__isComplete(text)                    
            for txt in text.split('\n'):
                self.input_buff.append((txt, self.input_complete,
                                        fname, self.lineno))
                self.lineno += 1

        addText(text)
        self.prompt = self.ps2
        if self.interactive:
            while not self.input_complete :
                t = self.input()
                t0 = t.strip()
                if len(t0) > 0:
                    addText(t)

        if self.input_complete:
            self.prompt = self.ps1            
            nkeys, nblock = self.convert()

    def get(self):
        """get compile-able block of python code"""
        if len(self) > 0:
            if not self._fifo[0]:
                self._fifo.reverse()
                self._fifo[0].reverse()
            try:
                return  self._fifo[0].pop()
            except IndexError:
                raise IndexError('InputText out of complete text')

        return self.empty_frame
    
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
            text,complete,fname,lineno = self.input_buff.pop()
            while not complete:
                tnext,complete,fname,lineno2 = self.input_buff.pop()
                text = "%s\n  %s%s" % (text,self.indent*(indent_level+1),tnext)

            text  = text.strip().rstrip()
            txt   = text.replace('(',' (').replace(')',' )')

            # note here the trick of replacing '#end' with '&end' so
            # that it is not removed by strip_comments.  then below,
            # we look for '&end' as an end-of-block token.
            if txt.startswith('#end'): txt = '&end%s\n' % txt[4:]

            txt   = strip_comments(txt)
            # thiskey, word2 = (txt.split() + [''])[0:2]
            words = txt.split(' ', 1)
            thiskey = words.pop(0)
            word2 = ''
            if len(words) > 0:
                word2 = words[0].replace(',', ' ').split()[0]

            if thiskey.endswith(':'):
                thiskey = thiskey[:-1]

            prefix,oneliner = '',False

            if thiskey in startkeys:
                # check for defined variables
                if thiskey == 'def':
                    dname,dexpr = get_DefVar(text)
                    if dname is not None and dexpr is not None:
                        if "'" in dexpr: dexpr.replace("'","\'")
                        text = "%s('%s','%s')" % (self.fcn_defvar,
                                                  dname,dexpr)
                        thiskey = self.nonkey
                    
                # note that we **re-test** here,
                # as thiskey may have changed above for defined variables
                if thiskey in startkeys:
                    if text.find(':') < 1:
                        raise SyntaxError(
                            "%s statement needs a ':' at\n    %s" % (thiskey, text))
                    elif text.endswith(':'): 
                        self.current = thiskey
                        self.keys.append(thiskey)
                        self.friends = self.block_friends[thiskey]
                        self.endkeys = ('end',  'end%s'% thiskey,
                                   '&end','&end%s'% thiskey)
                    else: # one-liner form 
                        oneliner = True

            elif thiskey in self.endkeys: # end of block
                if not thiskey.startswith('&'): # note '#end' name mangling
                    prefix = '#'
                if len(self.keys) != 0:
                    self.current = None
                    self.friends = ()
                    self.keys.pop()
                    if len(self.keys)>0:
                        self.current = self.keys[-1]
                        self.friends = self.block_friends[self.current]
                        self.endkeys = ('end',  'end%s'%self.current,
                                        '&end','&end%s'%self.current)
                
            elif not text.endswith(')') and self.__isCommand(thiskey,word2):
                # handle 'command format', including 'print'
                text = '%s(%s)'% (thiskey,text[len(thiskey):].strip())

            indent_level = len(self.keys)
            if (not oneliner and len(thiskey)>0 and
                (thiskey == self.current or thiskey in self.friends)):
                indent_level = indent_level - 1
 
            if indent_level < 0:
                raise SyntaxError('impossible indent level!')

            self.block.append('%s%s%s' % (self.indent*indent_level,prefix,text))
            if len(self.keys) == 0:
                outtext = '\n'.join(self.block)
                if '\n' in outtext:  outtext = outtext  + '\n'
                self._fifo[1].append((outtext,fname,1+lineno-len(self.block)))
                self.block=[]
        return len(self.keys), len(self.block)

    def clear(self):
        "clear the input"
        self._fifo  = [[],[]]
        
    def __isCommand(self,key,word2):
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
            len(key)<1 or len(word2)<1):
            return False

        # next test word2
        return (isValidName(word2) or
                isNumber(word2) or
                isLiteralStr(word2) )
    
    def __isComplete(self,text):
        """returns whether input text is a complete:
        that is: does not contains unclosed parens or quotes
        and does not end with a backslash
        tores state information from previous textline in
            self.eos    = char(s) to look for 'end of string' ("" == string complete)
            self.delims = current list of closing delims being waited for
        """
        parens  = self.parens
        opens   = ''.join(parens.keys())
        closes  = ''.join(parens.values())
        quotes,bslash = '\'"', '\\'
        prev_char = ''

        txt  = strip_comments(text)
        ends_without_bslash = not txt.rstrip().endswith(bslash)
        for i,c in enumerate(txt):
            if c in opens + closes + quotes:
                if self.eos != '':
                    if (prev_char != bslash and
                        txt[i:i+1] == self.eos):
                        self.eos = ''
                elif c in quotes:
                    self.eos = c
                elif c in opens:
                    self.delims.append(parens[c])
                elif c in closes and len(self.delims)>0 and \
                     c == self.delims[-1]:
                    self.delims.pop()
            prev_char = c
            
        return (self.eos == '' and ends_without_bslash and                
                len(self.delims) == 0)


    def __len__(self):
        return len(self._fifo[0])+len(self._fifo[1])

    def __defaultInput(self,prompt=None):
        if prompt is None:  prompt = self.prompt
        return raw_input(prompt)

if __name__ == '__main__':
    inp = InputText()
    inp.interactive = False
    inp.put("x = 1;a = x/3.;b = sqrt(")
    inp.put("a)")

    
    buff = [('x = 1', True, '<In>', 1),
        ('y = x /2', True, '<In>', 2),
        ('for i in range(10):', True, '<In>', 3),
        (' print i', True, '<In>', 4),
        ('    j = x *y * i', True, '<In>', 5),
        ('#endfor', True, '<In>', 6),
        ('print j ', True, '<In>', 7),
        ('def x1a = x + y ', True, '<In>', 8),
        ('if x < 1: ', True, '<In>', 9),
        ('  u = x/2', True, '<In>', 10),
        ('  if u < 1:  u = 2 ', True, '<In>', 11),
        ('else: ', True, '<In>', 12),
        ('  u = x/3', True, '<In>', 13),
        ('end ', True, '<In>', 14),
        ('set y = 22, z=29', True, '<In>', 15),
        ]

    for t,x,y,z in buff: inp.put(t)

    import ast
    while inp:
        text,fname,lineno = inp.get()
        text.rstrip()
        print( '=====')
        print( '%s' % text)
        a = ast.parse(text)  
        print( ast.dump(a,include_attributes=False))
        
    testcode = """
 y = 4
 z = 1
# start my for loop
for i in range(100):
y = y * (1 + i) / 7.
   while y < 9:
   
      y = y + 3
# comment in a nested block
      print 'XXX ', y
      endwhile
   if y > 4000: break
   if (y < 20 and
       y != 7):
      y = y-2
    endif
print i, y
endfor
print 'final y = ', y
"""
#    for i in testcode.split('\n'):     inp.put(i.strip())

