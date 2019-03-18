#!/usr/bin/env python
"""
   Main Larch interpreter

Safe(ish) evaluator of python expressions, using ast module.
The emphasis here is on mathematical expressions, and so
numpy functions are imported if available and used.
"""
from __future__ import division, print_function
import os
import sys
import types
import ast
import math
import numpy

from . import builtins
from . import site_config
from .symboltable import SymbolTable, Group, isgroup
from .inputText import InputText, BLANK_TEXT
from .larchlib import (LarchExceptionHolder, ReturnedNone,
                       Procedure, StdWriter, enable_plugins)
from .fitting  import isParameter
from .closure import Closure
from .utils import debugtime

UNSAFE_ATTRS = ('__subclasses__', '__bases__', '__globals__', '__code__',
                '__closure__', '__func__', '__self__', '__module__',
                '__dict__', '__class__', '__call__', '__get__',
                '__getattribute__', '__subclasshook__', '__new__',
                '__init__', 'func_globals', 'func_code', 'func_closure',
                'im_class', 'im_func', 'im_self', 'gi_code', 'gi_frame',
                '__asteval__', 'f_locals', '__mro__')


OPERATORS = {
    ast.Add:    lambda a, b: b.__radd__(a) if isParameter(b) else a + b,
    ast.Sub:    lambda a, b: b.__rsub__(a) if isParameter(b) else a - b,
    ast.Mult:   lambda a, b: b.__rmul__(a) if isParameter(b) else a * b,
    ast.Div:    lambda a, b: b.__rdiv__(a) if isParameter(b) else a / b,
    ast.FloorDiv: lambda a, b: b.__rfloordiv__(a) if isParameter(b) else a // b,
    ast.Mod:    lambda a, b: b.__rmod__(a) if isParameter(b) else a % b,
    ast.Pow:    lambda a, b: b.__rpow__(a) if isParameter(b) else a ** b,
    ast.Eq:     lambda a, b: b.__eq__(a)  if isParameter(b) else a == b,
    ast.Gt:     lambda a, b: b.__le__(a) if isParameter(b) else a > b,
    ast.GtE:    lambda a, b: b.__lt__(a) if isParameter(b) else a >= b,
    ast.Lt:     lambda a, b: b.__ge__(a) if isParameter(b) else a < b,
    ast.LtE:    lambda a, b: b.__gt__(a) if isParameter(b) else a <= b,
    ast.NotEq:  lambda a, b: b.__ne__(a) if isParameter(b) else a != b,
    ast.Is:     lambda a, b: a is b,
    ast.IsNot:  lambda a, b: a is not b,
    ast.In:     lambda a, b: a in b,
    ast.NotIn:  lambda a, b: a not in b,
    ast.BitAnd: lambda a, b: a & b,
    ast.BitOr:  lambda a, b: a | b,
    ast.BitXor: lambda a, b: a ^ b,
    ast.LShift: lambda a, b: a << b,
    ast.RShift: lambda a, b: a >> b,
    ast.And:    lambda a, b: a and b,
    ast.Or:     lambda a, b: a or b,
    ast.Invert: lambda a: ~a,
    ast.Not:    lambda a: not a,
    ast.UAdd:   lambda a: +a,
    ast.USub:   lambda a: -a}

PYTHON_RESERVED_WORDS = ('and', 'as', 'assert', 'break', 'class',
                         'continue', 'def', 'del', 'elif', 'else',
                         'except', 'exec', 'finally', 'for', 'from',
                         'global', 'if', 'import', 'in', 'is', 'lambda',
                         'not', 'or', 'pass', 'print', 'raise', 'return',
                         'try', 'while', 'with', 'yield', 'True', 'False',
                         'None', 'eval', 'execfile', '__import__',
                         '__package__')

class Interpreter:
    """larch program compiler and interpreter.
  Thiso module compiles expressions and statements to AST representation,
  using python's ast module, and then executes the AST representation
  using a custom SymbolTable for named object (variable, functions).
  This then gives a restricted version of Python, with slightly modified
  namespace rules.  The program syntax here is expected to be valid Python,
  but that may have been translated as with the inputText module.

  The following Python syntax is not supported:
      Exec, Lambda, Class, Global, Generators, Yield, Decorators

  In addition, Function is greatly altered so as to allow a Larch procedure.
  """

    supported_nodes = ('arg', 'assert', 'assign', 'attribute', 'augassign',
                       'binop', 'boolop', 'break', 'bytes', 'call',
                       'compare', 'continue', 'delete', 'dict', 'ellipsis',
                       'excepthandler', 'expr', 'expression', 'extslice',
                       'for', 'functiondef', 'if', 'ifexp', 'import',
                       'importfrom', 'index', 'interrupt', 'list',
                       'listcomp', 'module', 'name', 'nameconstant', 'num',
                       'pass', 'print', 'raise', 'repr', 'return', 'slice',
                       'starred', 'str', 'subscript', 'try', 'tryexcept',
                       'tryfinally', 'tuple', 'unaryop', 'while')

    def __init__(self, symtable=None, input=None, writer=None,
                 with_plugins=True, historyfile=None, maxhistory=5000):
        self.symtable   = symtable or SymbolTable(larch=self)

        self.input      = input or InputText(_larch=self,
                                             historyfile=historyfile,
                                             maxhistory=maxhistory)
        self.writer     = writer or StdWriter(_larch=self)
        self._interrupt = None
        self.error      = []
        self.expr       = None
        self.retval     = None
        self.func       = None
        self.fname      = '<stdin>'
        self.lineno     = 0
        builtingroup    = self.symtable._builtin
        mathgroup       = self.symtable._math
        setattr(mathgroup, 'j', 1j)

        # system-specific settings
        enable_plugins()
        site_config.system_settings()
        for sym in builtins.from_math:
            setattr(mathgroup, sym, getattr(math, sym))

        for sym in builtins.from_builtin:
            setattr(builtingroup, sym, __builtins__[sym])

        for sym in builtins.from_numpy:
            try:
                setattr(mathgroup, sym, getattr(numpy, sym))
            except AttributeError:
                pass
        for fname, sym in list(builtins.numpy_renames.items()):
            setattr(mathgroup, fname, getattr(numpy, sym))

        core_groups = ['_main', '_sys', '_builtin', '_math']
        for groupname, entries in builtins.init_builtins.items():
            if groupname not in core_groups:
                core_groups.append(groupname)
            if self.symtable.has_group(groupname):
                group = getattr(self.symtable, groupname, None)
            else:
                group = self.symtable.set_symbol(groupname,
                                                 value=Group(__name__=groupname))
            for fname, fcn in list(entries.items()):
                setattr(group, fname,
                        Closure(func=fcn, _larch=self, _name=fname))

        self.symtable._sys.core_groups = core_groups
        self.symtable._fix_searchGroups(force=True)

        # set valid commands from builtins
        for cmd in builtins.valid_commands:
            self.symtable._sys.valid_commands.append(cmd)

        # run any initialization routines
        for fcn in builtins.init_funcs:
            if callable(fcn):
                fcn(_larch=self)

        for grp in builtins.init_groups:
            self.symtable._sys.saverestore_groups.append(grp)

        for groupname, docstring in builtins.init_moddocs.items():
            group = self.symtable.get_group(groupname)
            group.__doc__ = docstring

        self.on_try = self.on_tryexcept
        self.on_tryfinally = self.on_tryexcept
        self.node_handlers = dict(((node, getattr(self, "on_%s" % node))
                                   for node in self.supported_nodes))

        if with_plugins: # add all plugins in standard plugins folder
            plugins_dir = os.path.join(site_config.usr_larchdir, 'plugins')
            loaded_plugins = []
            for pname in sorted(os.listdir(plugins_dir)):
                if pname not in loaded_plugins:
                    pdir = os.path.join(plugins_dir, pname)
                    if os.path.isdir(pdir):
                        builtins.add_plugin(pdir, _larch=self)
                        loaded_plugins.append(pname)

        reset_fiteval = getattr(mathgroup, 'reset_fiteval', None)
        if callable(reset_fiteval):
            reset_fiteval(_larch=self)

    def add_plugin(self, mod, **kws):
        """add plugin components from plugin directory"""
        builtins.add_plugin(mod, _larch=self, **kws)

    def unimplemented(self, node):
        "unimplemented nodes"
        self.raise_exception(node, exc=NotImplementedError,
                             msg="'%s' not supported" % (node.__class__.__name__))

    def raise_exception(self, node, exc=None, msg='', expr=None,
                        fname=None, lineno=None, func=None):
        "add an exception"
        if self.error is None:
            self.error = []
        if expr  is None:
            expr  = self.expr
        if fname is None:
            fname = self.fname
        if lineno is None:
            lineno = self.lineno

        if func is None:
            func = self.func

        if len(self.error) > 0 and not isinstance(node, ast.Module):
            msg = '%s' % msg
        err = LarchExceptionHolder(node=node, exc=exc, msg=msg, expr=expr,
                                   fname=fname, lineno=lineno, func=func)
        self._interrupt = ast.Break()
        self.error.append(err)
        self.symtable._sys.last_error = err
        #raise RuntimeError

    # main entry point for Ast node evaluation
    #  parse:  text of statements -> ast
    #  run:    ast -> result
    #  eval:   string statement -> result = run(parse(statement))
    def parse(self, text, fname=None, lineno=-1):
        """parse statement/expression to Ast representation    """
        self.expr  = text
        try:
            return ast.parse(text)
        except:
            etype, exc, tb = sys.exc_info()
            if (isinstance(exc, SyntaxError) and
                exc.msg == 'invalid syntax'):
                rwords = []
                for word in PYTHON_RESERVED_WORDS:
                    if (text.startswith('%s ' % word) or
                        text.endswith(' %s' % word) or
                        ' %s ' % word in text):
                        rwords.append(word)
                if len(rwords) > 0:
                    rwords = ", ".join(rwords)
                    text = """May contain one of Python's reserved words:
   %s"""  %  (rwords)
            self.raise_exception(None, exc=SyntaxError, msg='Syntax Error',
                                 expr=text, fname=fname, lineno=lineno)

    def run(self, node, expr=None, func=None,
            fname=None, lineno=None, with_raise=False):
        """executes parsed Ast representation for an expression"""
        # Note: keep the 'node is None' test: internal code here may run
        #    run(None) and expect a None in return.
        if node is None:
            return None
        if isinstance(node, str):
            node = self.parse(node)
        if lineno is not None:
            self.lineno = lineno
        if fname  is not None:
            self.fname  = fname
        if expr  is not None:
            self.expr   = expr
        # if func is not None:
        self.func = func

        # get handler for this node:
        #   on_xxx with handle nodes of type 'xxx', etc
        if node.__class__.__name__.lower() not in self.node_handlers:
            return self.unimplemented(node)
        handler = self.node_handlers[node.__class__.__name__.lower()]
        # run the handler:  this will likely generate
        # recursive calls into this run method.
        try:
            out = handler(node)
        except:
            self.raise_exception(node, expr=self.expr,
                                 fname=self.fname, lineno=self.lineno)
        else:
            # for some cases (especially when using Parameter objects),
            # a calculation returns an otherwise numeric array, but with
            # dtype 'object'. fix here, trying (float, complex, list).
            if isinstance(out, numpy.ndarray):
                if out.dtype == numpy.object:
                    try:
                        out = out.astype(float)
                    except (ValueError, TypeError):
                        try:
                            out = out.astype(complex)
                        except TypeError:
                            out = list(out)
            # enumeration objects are list-ified here...
            if isinstance(out, enumerate):
                out = list(out)
            return out

    def __call__(self, expr, **kw):
        return self.eval(expr, **kw)

    def eval(self, expr, fname=None, lineno=0, add_history=True):
        """evaluates an expression
        really: puts expression to input buffer, and if the
        input buffer is complete, it executes all the code in
        that buffer.
        """
        self.input.put(expr, filename=fname, lineno=lineno,
                       add_history=add_history)
        if self.input.complete and len(self.input) > 0:
            return self.execute_input()

    def execute_input(self):
        """executes the text in the input buffer"""
        self.error = []
        if not hasattr(self.symtable._sys, 'call_stack'):
            self.symtable._sys.call_stack = []
        call_stack = self.symtable._sys.call_stack
        call_stack.append(None)

        ret = None

        while len(self.input) > 0:
            text, fname, lineno = self.input.get()
            # print("EXEC ", text, fname, lineno)
            # self.input.buffer.append(text)
            if len(self.input.curtext) > 0 or len(self.input.blocks) > 0:
                continue
            call_stack[-1] = (text, fname, lineno)
            try:
                node = self.parse(text, fname=fname, lineno=lineno)
                ret =  self.run(node, expr=text, fname=fname, lineno=lineno)
            except RuntimeError:
                pass

        self.input.clear()
        call_stack.pop()
        return ret

    def runfile(self, filename, new_module=None):
        """
        run the larch code held in a file, possibly as 'module'
        """
        ret = self.input.putfile(filename)
        if ret is not None:
            exc, msg = ret
            err = LarchExceptionHolder(node=None, exc=IOError,
                                       msg='Cannot read %s' % filename)
            self.error.append(err)
            self.symtable._sys.last_error = err
            return

        # self.input.put(text, filename=filename, lineno=0, add_history=add_history)
        if not self.input.complete:
            msg = "File '%s' ends with incomplete input" % (filename)
            text = None
            lineno = 0
            if len(self.input.blocks) > 0 and filename is not None:
                blocktype, lineno, text = self.input.blocks[0]
                msg = "File '%s' ends with un-terminated '%s'" % (filename,
                                                                  blocktype)
            elif self.input.saved_text is not BLANK_TEXT:
                text, fname, lineno = self.input.saved_text
                msg = "File '%s' ends with incomplete statement" % (filename)
            self.input.clear()
            err = LarchExceptionHolder(node=None, exc=SyntaxError, msg=msg,
                                       expr=text, fname=filename,
                                       lineno=lineno)

            self.error.append(err)
            self.symtable._sys.last_error = err
            return

        thismod = None
        if new_module is not None:
            # save current module group
            #  create new group, set as moduleGroup and localGroup
            self.symtable.save_frame()
            thismod = self.symtable.create_group(name=new_module)
            self.symtable._sys.modules[new_module] = thismod
            self.symtable.set_frame((thismod, thismod))

        ret = self.execute_input()

        if new_module is not None:
            # for a "newly created module" (as on import),
            # the module group is the return value
            self.symtable.restore_frame()
        return thismod



    def show_errors(self):
        """show errors """
        if self.error:
            call_stack = self.symtable._sys.call_stack
            writer = self.writer
            fname = self.fname
            lineno = self.lineno

            writer.write('Traceback (most recent calls last): \n')
            for eblock, efname, elineno in call_stack:
                text = "File %s, line %i" % (efname, elineno)
                if efname != fname and elineno != lineno:
                    text =  "%s\n    %s" % (text, eblock.split('\n')[0])
                writer.write('   %s\n' % (text))

            errors_seen = []
            for err in self.error:
                exc_name, errmsg = err.get_error()
                file_lineno = errmsg.split('\n')[0].strip()
                if file_lineno in errors_seen:
                    continue
                errors_seen.append(file_lineno)
                writer.write(errmsg)
            self.error = []

    def run_init_scripts(self):
        for fname in site_config.init_files:
            if os.path.exists(fname):
                try:
                    self.runfile(fname)
                except:
                    self.raise_exception(None, exc=RuntimeError,
                                         msg='Initialization Error')

    def dump(self, node, **kw):
        "simple ast dumper"
        return ast.dump(node, **kw)

    # handlers for ast components
    def on_expr(self, node):
        "expression"
        return self.run(node.value)  # ('value',)

    def on_index(self, node):
        "index"
        return self.run(node.value)  # ('value',)

    def on_return(self, node): # ('value',)
        "return statement: look for None, return special sentinal"
        ret = self.run(node.value)
        if ret is None: ret = ReturnedNone
        self.retval = ret
        return

    def on_repr(self, node):
        "repr "
        return repr(self.run(node.value))  # ('value',)

    def on_module(self, node):    # ():('body',)
        "module def"
        out = None
        for tnode in node.body:
            out = self.run(tnode)
        return out

    def on_expression(self, node):
        "basic expression"
        return self.on_module(node) # ():('body',)

    def on_pass(self, node):
        "pass statement"
        return None  # ()

    def on_ellipsis(self, node):
        "ellipses"
        return Ellipsis

    # for break and continue: set the instance variable _interrupt
    def on_interrupt(self, node):    # ()
        "interrupt handler"
        self._interrupt = node
        return node

    def on_break(self, node):
        "break"
        return self.on_interrupt(node)

    def on_continue(self, node):
        "continue"
        return self.on_interrupt(node)

    def on_arg(self, node):
        "arg for function definitions"
        return node.arg

    def on_assert(self, node):    # ('test', 'msg')
        "assert statement"
        testval = self.run(node.test)
        if not testval:
            self.raise_exception(node, exc=AssertionError, msg=node.msg)
        return True

    def on_list(self, node):    # ('elt', 'ctx')
        "list"
        return [self.run(e) for e in node.elts]

    def on_tuple(self, node):    # ('elts', 'ctx')
        "tuple"
        return tuple(self.on_list(node))

    def on_dict(self, node):    # ('keys', 'values')
        "dictionary"
        nodevals = list(zip(node.keys, node.values))
        run = self.run
        return dict([(run(k), run(v)) for k, v in nodevals])

    def on_num(self, node):
        'return number'
        return node.n  # ('n',)

    def on_str(self, node):
        'return string'
        return node.s  # ('s',)

    def on_bytes(self, node):
        'return bytes'
        return node.s  # ('s',)

    def on_nameconstant(self, node):    # ('value')
        """ Name Constant node (new in Python3.4)"""
        return node.value

    def on_name(self, node):    # ('id', 'ctx')
        """ Name node """
        ctx = node.ctx.__class__
        if ctx == ast.Del:
            val = self.symtable.del_symbol(node.id)
        elif ctx == ast.Param:  # for Function Def
            val = str(node.id)
        else:
            try:
                val = self.symtable.get_symbol(node.id)
            except (NameError, LookupError):
                msg = "name '%s' is not defined" % node.id
                val = None
                self.raise_exception(node, msg=msg)
        return val

    def on_starred(self, node):    # ('value', 'ctx')
        """ Starred node """
        ctx = node.ctx.__class__
        if ctx != ast.Load:
            msg = "can only load starargs"
            self.raise_exception(node, msg=msg)
        return self.run(node.value)

    def node_assign(self, node, val):
        """here we assign a value (not the node.value object) to a node
        this is used by on_assign, but also by for, list comprehension, etc.
        """
        if len(self.error) > 0:
            return
        if node.__class__ == ast.Name:
            sym = self.symtable.set_symbol(node.id, value=val)
        elif node.__class__ == ast.Attribute:
            if node.ctx.__class__  == ast.Load:
                errmsg = "cannot assign to attribute %s" % node.attr
                self.raise_exception(node, exc=AttributeError, msg=errmsg)

            setattr(self.run(node.value), node.attr, val)

        elif node.__class__ == ast.Subscript:
            sym    = self.run(node.value)
            xslice = self.run(node.slice)
            if isinstance(node.slice, ast.Index):
                sym[xslice] = val
            elif isinstance(node.slice, ast.Slice):
                i = xslice.start
                sym[slice(xslice.start, xslice.stop)] = val
            elif isinstance(node.slice, ast.ExtSlice):
                sym[(xslice)] = val
        elif node.__class__ in (ast.Tuple, ast.List):
            if len(val) == len(node.elts):
                for telem, tval in zip(node.elts, val):
                    self.node_assign(telem, tval)
            else:
                raise ValueError('too many values to unpack')

    def on_attribute(self, node):    # ('value', 'attr', 'ctx')
        "extract attribute"
        ctx = node.ctx.__class__
        if ctx == ast.Del:
            return delattr(sym, node.attr)

        sym = self.run(node.value)
        if node.attr not in UNSAFE_ATTRS:
            try:
                return getattr(sym, node.attr)
            except AttributeError:
                pass

        obj = self.run(node.value)
        fmt = "%s does not have member '%s'"
        if not isgroup(obj):
            obj = obj.__class__
            fmt = "%s does not have attribute '%s'"
        msg = fmt % (obj, node.attr)
        self.raise_exception(node, exc=AttributeError, msg=msg)

    def on_assign(self, node):    # ('targets', 'value')
        "simple assignment"
        val = self.run(node.value)
        if len(self.error) > 0:
            return
        for tnode in node.targets:
            self.node_assign(tnode, val)
        return

    def on_augassign(self, node):    # ('target', 'op', 'value')
        "augmented assign"
        val = ast.BinOp(left=node.target,  op=node.op, right=node.value)
        return self.on_assign(ast.Assign(targets=[node.target], value=val))

    def on_slice(self, node):    # ():('lower', 'upper', 'step')
        "simple slice"
        return slice(self.run(node.lower), self.run(node.upper),
                     self.run(node.step))

    def on_extslice(self, node):    # ():('dims',)
        "extended slice"
        return tuple([self.run(tnode) for tnode in node.dims])

    def on_subscript(self, node):    # ('value', 'slice', 'ctx')
        "subscript handling -- one of the tricky parts"
        val    = self.run(node.value)
        nslice = self.run(node.slice)
        ctx = node.ctx.__class__
        if ctx in ( ast.Load, ast.Store):
            if isinstance(node.slice, (ast.Index, ast.Slice, ast.Ellipsis)):
                return val.__getitem__(nslice)
            elif isinstance(node.slice, ast.ExtSlice):
                return val[(nslice)]
        else:
            msg = "subscript with unknown context"
            self.raise_exception(node, msg=msg)

    def on_delete(self, node):    # ('targets',)
        "delete statement"
        for tnode in node.targets:
            if tnode.ctx.__class__ != ast.Del:
                break
            children = []
            while tnode.__class__ == ast.Attribute:
                children.append(tnode.attr)
                tnode = tnode.value

            if tnode.__class__ == ast.Name:
                children.append(tnode.id)
                children.reverse()
                self.symtable.del_symbol('.'.join(children))
            else:
                msg = "could not delete symbol"
                self.raise_exception(node, msg=msg)

    def on_unaryop(self, node):    # ('op', 'operand')
        "unary operator"
        return OPERATORS[node.op.__class__](self.run(node.operand))

    def on_binop(self, node):    # ('left', 'op', 'right')
        "binary operator"
        return OPERATORS[node.op.__class__](self.run(node.left),
                                            self.run(node.right))

    def on_boolop(self, node):    # ('op', 'values')
        "boolean operator"
        val = self.run(node.values[0])
        is_and = ast.And == node.op.__class__
        if (is_and and val) or (not is_and and not val):
            for n in node.values[1:]:
                val =  OPERATORS[node.op.__class__](val, self.run(n))
                if (is_and and not val) or (not is_and and val):
                    break
        return val

    def on_compare(self, node):    # ('left', 'ops', 'comparators')
        "comparison operators"
        lval = self.run(node.left)
        out  = True
        for oper, rnode in zip(node.ops, node.comparators):
            comp = OPERATORS[oper.__class__]
            rval = self.run(rnode)
            out  = comp(lval, rval)
            lval = rval
            if not hasattr(out, 'any') and not out:
                break
        return out

    def on_print(self, node):    # ('dest', 'values', 'nl')
        """ note: implements Python2 style print statement, not
        print() function.  Probably, the 'larch2py' translation
        should look for and translate print -> print_() to become
        a customized function call.
        """
        dest = self.run(node.dest) or self.writer
        end = ''
        if node.nl:
            end = '\n'
        out = [self.run(tnode) for tnode in node.values]
        if out and len(self.error)==0:
            print(*out, file=dest, end=end)

    def on_if(self, node):    # ('test', 'body', 'orelse')
        "regular if-then-else statement"
        block = node.body
        if not self.run(node.test):
            block = node.orelse
        for tnode in block:
            self.run(tnode)

    def on_ifexp(self, node):    # ('test', 'body', 'orelse')
        "if expressions"
        expr = node.orelse
        if self.run(node.test):
            expr = node.body
        return self.run(expr)

    def on_while(self, node):    # ('test', 'body', 'orelse')
        "while blocks"
        while self.run(node.test):
            self._interrupt = None
            for tnode in node.body:
                self.run(tnode)
                if self._interrupt is not None:
                    break
            if isinstance(self._interrupt, ast.Break):
                break
        else:
            for tnode in node.orelse:
                self.run(tnode)
        self._interrupt = None

    def on_for(self, node):    # ('target', 'iter', 'body', 'orelse')
        "for blocks"
        for val in self.run(node.iter):
            self.node_assign(node.target, val)
            if len(self.error) > 0:
                return
            self._interrupt = None
            for tnode in node.body:
                self.run(tnode)
                if len(self.error) > 0:
                    return
                if self._interrupt is not None:
                    break
            if isinstance(self._interrupt, ast.Break):
                break
        else:
            for tnode in node.orelse:
                self.run(tnode)
        self._interrupt = None

    def on_listcomp(self, node):    # ('elt', 'generators')
        "list comprehension"
        out = []
        for tnode in node.generators:
            if tnode.__class__ == ast.comprehension:
                for val in self.run(tnode.iter):
                    self.node_assign(tnode.target, val)
                    if len(self.error) > 0:
                        return
                    add = True
                    for cond in tnode.ifs:
                        add = add and self.run(cond)
                    if add:
                        out.append(self.run(node.elt))
        return out

    def on_excepthandler(self, node): # ('type', 'name', 'body')
        "exception handler..."
        # print("except handler %s / %s " % (node.type, ast.dump(node.name)))
        return (self.run(node.type), node.name, node.body)

    def on_tryexcept(self, node):    # ('body', 'handlers', 'orelse')
        "try/except blocks"
        no_errors = True
        for tnode in node.body:
            self.run(tnode)
            no_errors = no_errors and len(self.error) == 0
            if self.error:
                e_type, e_value, e_tb = self.error[-1].exc_info
                this_exc = e_type()

                for hnd in node.handlers:
                    htype = None
                    if hnd.type is not None:
                        htype = __builtins__.get(hnd.type.id, None)
                    if htype is None or isinstance(this_exc, htype):
                        self.error = []
                        self._interrupt = None
                        if hnd.name is not None:
                            self.node_assign(hnd.name, e_value)
                        for tline in hnd.body:
                            self.run(tline)
                        break
        if no_errors and hasattr(node, 'orelse'):
            for tnode in node.orelse:
                self.run(tnode)

        if hasattr(node, 'finalbody'):
            for tnode in node.finalbody:
                self.run(tnode)

    def on_raise(self, node):    # ('type', 'inst', 'tback')
        "raise statement"
        out  = self.run(node.exc)
        msg = ' '.join(out.args)
        msg2 = self.run(node.cause)
        if msg2 not in (None, 'None'):
            msg = "%s: %s" % (msg, msg2)
        self.raise_exception(None, exc=out.__class__, msg=msg, expr='')

    def on_call(self, node):
        "function/procedure execution"
        #  ('func', 'args', 'keywords', 'starargs', 'kwargs')
        func = self.run(node.func)
        if not callable(func):
            msg = "'%s' is not callable!!" % (func)
            self.raise_exception(node, exc=TypeError, msg=msg)

        args = []
        for narg in node.args:
            aadd = args.append
            if isinstance(narg, ast.Starred):
                aadd = args.extend
            aadd(self.run(narg))

        starargs = getattr(node, 'starargs', None)
        if starargs is not None:
            args = args + self.run(starargs)

        keywords = {}
        if func == print:
            keywords['file'] = self.writer

        for key in node.keywords:
            if not isinstance(key, ast.keyword):
                msg = "keyword error in function call '%s'" % (func)
                self.raise_exception(node, msg=msg)
            if key.arg is None:   # Py3 **kwargs !
                keywords.update(self.run(key.value))
            else:
                keywords[key.arg] = self.run(key.value)

        kwargs = getattr(node, 'kwargs', None)
        if kwargs is not None:
            keywords.update(self.run(kwargs))

        try:
            return func(*args, **keywords)
        except:
            self.raise_exception(node, msg="Error running %s" % (func))

    def on_functiondef(self, node):
        "define procedures"
        # ('name', 'args', 'body', 'decorator_list')
        if node.decorator_list != []:
            raise Warning("decorated procedures not supported!")
        kwargs = []
        offset = len(node.args.args) - len(node.args.defaults)
        for idef, defnode in enumerate(node.args.defaults):
            defval = self.run(defnode)
            keyval = self.run(node.args.args[idef+offset])
            kwargs.append((keyval, defval))
        # kwargs.reverse()
        args = [tnode.arg for tnode in node.args.args[:offset]]
        doc = None
        if (isinstance(node.body[0], ast.Expr) and
            isinstance(node.body[0].value, ast.Str)):
            docnode = node.body[0]
            doc = docnode.value.s

        vararg = self.run(node.args.vararg)
        varkws = self.run(node.args.kwarg)
        proc = Procedure(node.name, _larch=self, doc= doc,
                         body   = node.body,
                         fname  = self.fname,
                         lineno = self.lineno,
                         args   = args,
                         kwargs = kwargs,
                         vararg = vararg,
                         varkws = varkws)
        self.symtable.set_symbol(node.name, value=proc)

    # imports
    def on_import(self, node):    # ('names',)
        "simple import"
        for tnode in node.names:
            self.import_module(tnode.name, asname=tnode.asname)

    def on_importfrom(self, node):    # ('module', 'names', 'level')
        "import/from"
        fromlist, asname = [], []
        for tnode in node.names:
            fromlist.append(tnode.name)
            asname.append(tnode.asname)
        self.import_module(node.module,
                           asname=asname, fromlist=fromlist)


    def import_module(self, name, asname=None,
                      fromlist=None, do_reload=False):
        """
        import a module (larch or python), installing it into the symbol table.
        required arg:
            name       name of module to import
                          'foo' in 'import foo'
        options:
            fromlist   list of symbols to import with 'from-import'
                          ['x','y'] in 'from foo import x, y'
            asname     alias for imported name(s)
                          'bar' in 'import foo as bar'
                       or
                          ['s','t'] in 'from foo import x as s, y as t'

        this method covers a lot of cases (larch or python, import
        or from-import, use of asname) and so is fairly long.
        """
        st_sys = self.symtable._sys
        for idir in st_sys.path:
            if idir not in sys.path and os.path.exists(idir):
                sys.path.append(idir)

        # step 1  import the module to a global location
        #   either sys.modules for python modules
        #   or  st_sys.modules for larch modules
        # reload takes effect here in the normal python way:

        thismod = None
        if name in st_sys.modules:
            thismod = st_sys.modules[name]
        elif name in sys.modules:
            thismod = sys.modules[name]

        if thismod is None or do_reload:
            # first look for "name.lar"
            islarch = False
            larchname = "%s.lar" % name
            for dirname in st_sys.path:
                if not os.path.exists(dirname):
                    continue
                if larchname in sorted(os.listdir(dirname)):
                    islarch = True
                    modname = os.path.abspath(os.path.join(dirname, larchname))
                    try:
                        thismod = self.runfile(modname, new_module=name)
                    except:
                        thismod = None

                    # we found a module with the right name,
                    # so break out of loop, even if there was an error.
                    break

            if len(self.error) > 0 and name in st_sys.modules:
                st_sys.modules.pop(name)

            # or, if not a larch module, load as a regular python module
            if thismod is None and not islarch and name not in sys.modules:
                try:
                    __import__(name)
                    thismod = sys.modules[name]
                except:
                    thismod = None

        if thismod is None:
            self.raise_exception(None, exc=ImportError, msg='Import Error')
            return

        # now we install thismodule into the current moduleGroup
        # import full module
        if fromlist is None:
            if asname is None:
                asname = name
            parts = asname.split('.')
            asname = parts.pop()
            targetgroup = st_sys.moduleGroup
            while len(parts) > 0:
                subname = parts.pop(0)
                subgrp  = Group()
                setattr(targetgroup, subname, subgrp)
                targetgroup = subgrp
            setattr(targetgroup, asname, thismod)
        # import-from construct
        else:
            if asname is None:
                asname = [None]*len(fromlist)
            targetgroup = st_sys.moduleGroup
            for sym, alias in zip(fromlist, asname):
                if alias is None:
                    alias = sym
                setattr(targetgroup, alias, getattr(thismod, sym))
    # end of import_module
