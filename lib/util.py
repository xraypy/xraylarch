#!/usr/bin/env python
"""utilities for larch
"""
from __future__ import print_function
import re
import sys

from .symboltable import Group

def PrintExceptErr(err_str, print_trace=True):
    " print error on exceptions"
    print('\n***********************************')
    print(err_str)
    #print 'PrintExceptErr', err_str
    try:
        print('Error: %s' % sys.exc_type)
        etype, evalue, tback = sys.exc_info()
        if print_trace == False:
            tback = ''
        sys.excepthook(etype, evalue, tback)
    except:
        print('Error printing exception error!!')
        raise
    print('***********************************\n')

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


RESERVED_WORDS = ('and', 'as', 'assert', 'break', 'continue', 'def',
                  'del', 'elif', 'else', 'except', 'finally', 'for',
                  'from', 'if', 'import', 'in', 'is', 'not', 'or',
                  'pass', 'print', 'raise', 'return', 'try', 'while',
                  'group', 'end', 'endwhile', 'endif', 'endfor',
                  'endtry', 'enddef', 'True', 'False', 'None')

NAME_MATCH = re.compile(r"[a-z_][a-z0-9_]*(.[a-z_][a-z0-9_]*)*$").match

def isValidName(name):
    "input is a valid name"
    tnam = name[:].lower()
    if tnam in RESERVED_WORDS:
        return False
    return NAME_MATCH(tnam) is not None

def isNumber(num):
    "input is a number"
    try:
        cnum = complex(num)
        return True
    except ValueError:
        return False

def isLiteralStr(inp):
    "is a literal string"
    return ((inp.startswith("'") and inp.endswith("'")) or
            (inp.startswith('"') and inp.endswith('"')))

##
class DefinedVariable(object):
    """defined variable: re-evaluate on access

    Note that the localGroup/moduleGroup are cached
    at compile time, and restored for evaluation.
    """
    def __init__(self, expr=None, larch=None):
        self.expr = expr
        self.larch = larch
        self.ast = None
        self._groups = None, None
        self.compile()

    def __repr__(self):
        return "<DefinedVariable: '%s'>" % (self.expr)
        
    def compile(self):
        """compile to ast"""
        if self.larch is not None and self.expr is not None:
            self.ast = self.larch.compile(self.expr)

    def evaluate(self):
        "actually evaluate ast to a value"
        if self.ast is None:
            self.compile()
        if self.ast is None:
            msg = "Cannot compile '%s'"  % (self.expr)
            raise Warning(msg)
            
        if hasattr(self.larch, 'interp'):
            # save current localGroup/moduleGroup 
            self.larch.symtable.save_frame()
            rval = self.larch.interp(self.ast, expr=self.expr)
            self.larch.symtable.restore_frame()
            return rval
        else:
            msg = "Cannot evaluate '%s'"  % (self.expr)
            raise ValueError(msg)

class Procedure(object):
    """larch procedure:  function """
    def __init__(self, name, larch=None, doc=None,
                 fname='<StdInput>', lineno=0,
                 body=None, args=None, kwargs=None,
                 vararg=None, varkws=None):
        self.name     = name
        self.larch    = larch
        self.modgroup = larch.symtable._sys.moduleGroup
        self.body     = body
        self.argnames = args
        self.kwargs   = kwargs
        self.vararg   = vararg
        self.varkws   = varkws
        self.__doc__  = doc
        self.lineno   = lineno
        self.fname    = fname
        
    def __repr__(self):
        sig = ""
        if len(self.argnames) > 0:
            sig = "%s%s" % (sig, ', '.join(self.argnames))
        if self.vararg is not None:
            sig = "%s, *%s" % (sig, self.vararg)
        if len(self.kwargs) > 0:
            if len(sig) > 0:
                sig = "%s, " % sig            
            _kw = ["%s=%s" % (k, v) for k, v in self.kwargs]
            sig = "%s%s" % (sig, ', '.join(_kw))

        if self.varkws is not None:
            sig = "%s, **%s" % (sig, self.varkws)
        sig = "<Procedure %s(%s), file=%s>" % (self.name, sig, self.fname)
        if self.__doc__ is not None:
            sig = "%s\n  %s" % (sig, self.__doc__)
        return sig

    def __call__(self, *args, **kwargs):
        # msg = 'Cannot run Procedure %s' % self.name
        # self.larch.on_except(None, msg=msg, expr='<>',
        #                     fname=self.fname, lineno=self.lineno,
        #                     py_exc=sys.exc_info())

        stable  = self.larch.symtable
        lgroup  = Group()
        args   = list(args)
        n_args = len(args)
        n_expected = len(self.argnames)

        if n_args != n_expected:
            msg = None
            if n_args < n_expected:            
                msg = 'not enough arguments for Procedure %s' % self.name
                msg = '%s (expected %i, got %i)'% (msg,
                                                   n_expected,
                                                   n_args)
                self.larch.on_except(None, msg=msg, expr='<>',
                                     fname=self.fname, lineno=self.lineno,
                                     py_exc=sys.exc_info())
                
            msg = "too many arguments for Procedure %s" % self.name

        for argname in self.argnames:
            setattr(lgroup, argname, args.pop(0))

        if len(args) > 0 and self.kwargs is not None:
            msg = "got multiple values for keyword argument '%s' Procedure %s"
            for t_a, t_kw in zip(args, self.kwargs):
                if t_kw[0] in kwargs:
                    msg = msg % (t_kw[0], self.name)
                    self.larch.on_except(None, msg=msg, expr='<>',
                                         fname=self.fname,
                                         lineno=self.lineno,
                                         py_exc=sys.exc_info())
                else:
                    kwargs[t_a] = t_kw[1]

        try:
            if self.vararg is not None:
                setattr(lgroup, self.vararg, tuple(args))

            for key, val in self.kwargs:
                if key in kwargs:
                    val = kwargs.pop(key)
                setattr(lgroup, key, val)

            if self.varkws is not None:
                setattr(lgroup, self.varkws, kwargs)
            elif len(kwargs) > 0:
                msg = 'extra keyword arguments for Procedure %s (%s)'
                msg = msg % (self.name, ','.join(list(kwargs.keys())))
                self.larch.on_except(None, msg=msg, expr='<>',
                                     fname=self.fname, lineno=self.lineno,
                                     py_exc=sys.exc_info())
                
        except (ValueError, LookupError, TypeError, 
                NameError, AttributeError):
            msg = 'incorrect arguments for Procedure %s' % self.name
            self.larch.on_except(None, msg=msg, expr='<>',
                                 fname=self.fname,   lineno=self.lineno,
                                 py_exc=sys.exc_info())            
            
        stable.save_frame()
        stable.set_frame((lgroup, self.modgroup))
        retval = None
        self.larch.retval = None

        for node in self.body:
            self.larch.interp(node, expr='<>',
                              fname=self.fname, lineno=self.lineno)            
            if len(self.larch.error) > 0:
                break
            if self.larch.retval is not None:
                retval = self.larch.retval
                break
        stable.restore_frame()
        self.larch.retval = None
        del lgroup
        return retval
    
class LarchExceptionHolder:
    "basic exception handler"
    def __init__(self, node, msg='', fname='<StdInput>',
                 py_exc=(None, None),
                 expr=None, lineno=-3):
        self.node   = node
        self.fname  = fname
        self.expr   = expr
        self.msg    = msg
        self.py_exc = py_exc
        self.lineno = lineno
        self.exc_info = sys.exc_info()

    def get_error(self):
        "retrieve error data"
        node = self.node
        node_lineno = 0
        node_col_offset = 0

        if node is not None:
            try:
                node_lineno = node.lineno
                node_col_offset = self.node.col_offset
            except: 
                pass
            
        lineno = self.lineno + node_lineno 
        exc_text = str(self.exc_info[1])
        if exc_text in (None, 'None'):
            exc_text = ''
        expr = self.expr
        if expr == '<>': # denotes non-saved expression -- go fetch from file!
            try:
                ftmp = open(self.fname, 'r')
                expr = ftmp.readlines()[lineno-1][:-1]
                ftmp.close()
            except IOError:
                pass

        out = []
        if len(exc_text) > 0:
            out.append(exc_text)
        else:
            py_etype, py_eval = self.py_exc
            if py_etype is not None and py_eval is not None:
                out.append("%s: %s" % (py_etype, py_eval))
                
        if self.fname == '<StdInput>' and self.lineno <= 0:
            out.append('<StdInput>')
        else:
            out.append("%s, line number %i" % (self.fname, 1+self.lineno))
            
        out.append("    %s" % expr)
        if node_col_offset > 0:
            out.append("    %s^^^" % ((node_col_offset)*' '))
        return (self.msg, '\n'.join(out))

