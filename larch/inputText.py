#!/usr/bin/env python
#
# InputText for  Larch

from __future__ import print_function
import os
import sys
import time
from collections import deque
from copy import copy
import io
FILETYPE = io.IOBase

OPENS  = '{(['
CLOSES = '})]'
PARENS = dict(zip(OPENS, CLOSES))
QUOTES = '\'"'
BSLASH = '\\'
COMMENT = '#'
DBSLASH = "%s%s" % (BSLASH, BSLASH)

BLOCK_FRIENDS = {'if':    ('else', 'elif'),
                 'for':   ('else',),
                 'def':   (),
                 'try':   ('else', 'except', 'finally'),
                 'while': ('else',),
                 None: ()}

STARTKEYS = ['if', 'for', 'def', 'try', 'while']


def find_eostring(txt, eos, istart):
    """find end of string token for a string"""
    while True:
        inext = txt[istart:].find(eos)
        if inext < 0:  # reached end of text before match found
            return eos, len(txt)
        elif (txt[istart+inext-1] == BSLASH and
              txt[istart+inext-2] != BSLASH):  # matched quote was escaped
            istart = istart+inext+len(eos)
        else: # real match found! skip ahead in string
            return '', istart+inext+len(eos)-1

def is_complete(text):
    """returns whether a text of code is complete
    for strings quotes and open / close delimiters,
    including nested delimeters.
    """
    itok = istart = 0
    eos = ''
    delims = []
    while itok < len(text):
        c = text[itok]
        if c in QUOTES:
            eos = c
            if text[itok:itok+3] == c*3:
                eos = c*3
            istart = itok + len(eos)
            # leap ahead to matching quote, ignoring text within
            eos, itok = find_eostring(text, eos, istart)
        elif c in OPENS:
            delims.append(PARENS[c])
        elif c in CLOSES and len(delims) > 0 and c == delims[-1]:
            delims.pop()
        elif c == COMMENT and eos == '': # comment char outside string
            jtok = itok
            if '\n' in text[itok:]:
                itok = itok + text[itok:].index('\n')
            else:
                itok = len(text)
        itok += 1
    return eos=='' and len(delims)==0 and not text.rstrip().endswith(BSLASH)

def strip_comments(text, char='#'):
    """return text with end-of-line comments removed"""
    out = []
    for line in text.split('\n'):
        if line.find(char) > 0:
            i = 0
            while i < len(line):
                tchar = line[i]
                if tchar == char:
                    line = line[:i]
                    break
                elif tchar in ('"',"'"):
                    eos = line[i+1:].find(tchar)
                    if eos > 0:
                        i = i + eos
                i += 1
        out.append(line.rstrip())
    return '\n'.join(out)

def get_key(text):
    """return keyword: first word of text,
    isolating keywords followed by '(' and ':' """
    t =  text.replace('(', ' (').replace(':', ' :').strip()
    return t.split(' ', 1)[0].strip()

def block_start(text):
    """return whether a complete-extended-line of text
    starts with a block-starting keyword, one of
    ('if', 'for', 'try', 'while', 'def')
    """
    txt = strip_comments(text)
    key = get_key(txt)
    if key in STARTKEYS and txt.endswith(':'):
        return key
    return False

def block_end(text):
    """return whether a complete-extended-line of text
    starts wih block-ending keyword,
    '#end' + ('if', 'for', 'try', 'while', 'def')
    """
    txt = text.strip()
    if txt.startswith('#end') or txt.startswith('end'):
        n = 3
        if txt.startswith('#end'):
            n = 4
        key = txt[n:].split(' ', 1)[0].strip()
        if key in STARTKEYS:
            return key
    return False

BLANK_TEXT = ('', '<incomplete input>', -1)


class HistoryBuffer(object):
    """
    command history buffer
    """
    def __init__(self, filename=None, maxlines=5000, title='larch history'):
        self.filename = filename
        self.maxlines = maxlines
        self.title = title
        self.session_start = 0
        self.buffer = []
        if filename is not None:
            self.load(filename=filename)

    def add(self, text=''):
        if len(text.strip()) > 0:
            self.buffer.append(text)

    def clear(self):
        self.buffer = []
        self.session_start = 0

    def load(self, filename=None):
        if filename is not None:
            self.filename = filename
        if os.path.exists(self.filename):
            self.clear()
            with open(self.filename, 'r') as fh:
                lines = fh.readlines()
                for hline in lines:
                    self.add(text=hline[:-1])
            self.session_start = len(self.buffer)

    def save(self, filename=None, session_only=False,
             trim_last=False, maxlines=None):
        if filename is None:
            filename = self.filename
        if maxlines is None:
            maxlines = self.maxlines
        start_ = -maxlines
        if session_only:
            start_ = self.session_start
        end_ = None
        if trim_last:
            end_ = -1

        comment = "# %s saved" % (self.title)
        out = ["%s %s" % (comment, time.ctime())]
        for bline in self.buffer[start_:end_]:
            if not (bline.startswith(comment) or len(bline) < 0):
                out.append(str(bline))
        out.append('')
        with open(filename, 'w') as fh:
            fh.write('\n'.join(out))

class InputText:
    """input text for larch, with history"""
    def __init__(self, _larch=None, historyfile=None, maxhistory=5000,
                 prompt='larch> ',prompt2 = ".....> "):
        self.deque = deque()
        self.filename = '<stdin>'
        self.lineno = 0
        self.curline = 0
        self.curtext = ''
        self.blocks = []
        self.buffer = []
        self.larch = _larch
        self.prompt = prompt
        self.prompt2 = prompt2
        self.saved_text = BLANK_TEXT
        self.history = HistoryBuffer(filename=historyfile,
                                     maxlines=maxhistory)

    def __len__(self):
        return len(self.deque)

    def get(self):
        """get compile-able block of python code"""
        out = []
        filename, linenumber = None, None
        if self.saved_text != BLANK_TEXT:
            txt, filename, lineno = self.saved_text
            out.append(txt)
        text, fn, ln, done = self.deque.popleft()
        out.append(text)
        if filename is None:
            filename = fn
        if linenumber is None:
            linenumber = ln

        while not done:
            if len(self.deque) == 0:
                self.saved_text = ("\n".join(out), filename, linenumber)
                return BLANK_TEXT
            text, fn, ln, done = self.deque.popleft()
            out.append(text)
        self.saved_text = BLANK_TEXT
        return ("\n".join(out), filename, linenumber)

    def clear(self):
        self.deque.clear()
        self.saved_text = BLANK_TEXT
        self.curtext = ''
        self.blocks = []

    def putfile(self, filename):
        """add the content of a file at the top of the stack
        that is, to be run next, as for   run('myscript.lar')

        Parameters
        ----------
        filename  : file object or string of filename

        Returns
        -------
        None on success,
        (exception, message) on failure
        """

        text = None
        try:
            if isinstance(filename, FILETYPE):
                text = filename.read()
                filename = filename.name
            else:
                text = open(filename).read()
        except:
            errtype, errmsg, errtb = sys.exc_info()
            return (errtype, errmsg)


        if text is None:
            return (IOError, 'cannot read %s' % filename)

        current = None
        if len(self.deque) > 0:
            current = copy(self.deque)
            self.deque.clear()
        self.put(text, filename=filename, lineno=0, add_history=False)

        if current is not None:
            self.deque.extend(current)

    def put(self, text, filename=None, lineno=None, add_history=True):
        """add a line of input code text"""
        if filename is not None:
            self.filename = filename
        if lineno is not None:
            self.lineno = lineno

        if self.larch is not None:
            getsym = self.larch.symtable.get_symbol
            self.valid_commands = getsym('_sys.valid_commands', create=True)

        if self.history is not None and add_history:
            self.history.add(text)

        for txt in text.split('\n'):
            self.lineno += 1
            if len(self.curtext) == 0:
                self.curtext = txt
                self.curline = self.lineno
            else:
                self.curtext = "%s\n%s" % (self.curtext, txt)

            blk_start = False
            if is_complete(self.curtext) and len(self.curtext)>0:
                blk_start =  block_start(self.curtext)
                if blk_start:
                    self.blocks.append((blk_start, self.lineno, txt))
                else:
                    blk_end = block_end(self.curtext)
                    if (blk_end and len(self.blocks) > 0 and
                        blk_end == self.blocks[-1][0]):
                        self.blocks.pop()
                        if self.curtext.strip().startswith('end'):
                            nblank = self.curtext.find(self.curtext.strip())
                            self.curtext = '%s#%s' % (' '*nblank,
                                                      self.curtext.strip())

                _delim = None
                if len(self.blocks) > 0:
                    _delim = self.blocks[-1][0]

                key = get_key(self.curtext)
                ilevel = len(self.blocks)
                if ilevel > 0 and (blk_start or
                                   key in BLOCK_FRIENDS[_delim]):
                    ilevel = ilevel - 1

                sindent = ' '*4*ilevel
                pytext = "%s%s" % (sindent, self.curtext.strip())
                # look for valid commands
                if key in self.valid_commands and '\n' not in self.curtext:
                    argtext = self.curtext.strip()[len(key):].strip()
                    if not (argtext.startswith('(') and
                            argtext.endswith(')') ):
                        pytext  = "%s%s(%s)" % (sindent, key, argtext)

                self.deque.append((pytext, self.filename,
                                   self.curline, 0==len(self.blocks)))

                self.curtext = ''

    @property
    def complete(self):
        return len(self.curtext)==0 and len(self.blocks)==0

    @property
    def next_prompt(self):
        if len(self.curtext)==0 and len(self.blocks)==0:
            return self.prompt
        return self.prompt2
