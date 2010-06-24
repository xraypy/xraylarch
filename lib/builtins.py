
import os
import sys
import copy
from glob import glob
import help

from . import inputText

helper = help.Helper()

# inherit these from python's __builtins__
from_builtin= ('ArithmeticError', 'AssertionError', 'AttributeError',
                'BaseException', 'BufferError', 'BytesWarning',
                'DeprecationWarning', 'EOFError', 'EnvironmentError',
                'Exception', 'False', 'FloatingPointError',
                'GeneratorExit', 'IOError', 'ImportError', 'ImportWarning',
                'IndentationError', 'IndexError', 'KeyError',
                'KeyboardInterrupt', 'LookupError', 'MemoryError',
                'NameError', 'None', 'NotImplemented',
                'NotImplementedError', 'OSError', 'OverflowError',
                'ReferenceError', 'RuntimeError', 'RuntimeWarning',
                'StandardError', 'StopIteration', 'SyntaxError',
                'SyntaxWarning', 'SystemError', 'SystemExit', 'True',
                'TypeError', 'UnboundLocalError', 'UnicodeDecodeError',
                'UnicodeEncodeError', 'UnicodeError',
                'UnicodeTranslateError', 'UnicodeWarning', 'ValueError',
                'Warning', 'ZeroDivisionError', 'abs', 'all', 'any',
                'apply', 'basestring', 'bin', 'bool', 'buffer',
                'bytearray', 'bytes', 'callable', 'chr', 'cmp', 'coerce',
                'complex', 'delattr', 'dict', 'dir', 'divmod', 'enumerate',
                'file', 'filter', 'float', 'format', 'frozenset',
                'getattr', 'hasattr', 'hash', 'hex', 'id', 'int',
                'isinstance', 'len', 'list', 'map', 'max', 'min', 
                'oct', 'open', 'ord', 'pow', 'property', 'range',
                'raw_input', 'reduce', 'repr', 'reversed', 'round', 'set',
                'setattr', 'slice', 'sorted', 'str', 'sum', 'tuple',
                'type', 'unichr', 'unicode', 'zip')

# inherit these from numpy

from_numpy = ('pi','e', 'array','sin','cos','tan','exp','log','log10',
               'sqrt','arange', 'arccos', 'arccosh', 'arcsin', 'arcsinh',
               'arctan', 'arctan2', 'arctanh', 'argmax', 'argmin',
               'argsort', 'array', 'cosh', 'fabs', 'floor', 'floor_divide',
               'fmod', 'tanh', 'sign', 'sinh', 'identity', 'take',
               'choose', 'add', 'allclose', 'alltrue', 'around', 'asarray',
               'average', 'bitwise_and', 'bitwise_or', 'bitwise_xor',
               'ceil', 'clip', 'compress', 'concatenate', 'conjugate',
               'convolve', 'cumproduct', 'cumsum', 'diagonal', 'divide',
               'dot', 'equal', 'greater', 'greater_equal', 'hypot',
               'indices', 'invert', 'left_shift', 'less', 'less_equal',
               'logical_and', 'logical_not', 'logical_or', 'logical_xor',
               'maximum', 'minimum', 'multiply', 'negative', 'nonzero',
               'not_equal', 'ones', 'outer', 'power', 'product', 'put',
               'putmask', 'rank', 'ravel', 'remainder', 'repeat',
               'reshape', 'resize', 'right_shift', 'searchsorted', 'shape',
               'size', 'sometrue', 'sort', 'subtract', 'sum', 'swapaxes',
               'trace', 'transpose', 'true_divide', 'vdot', 'where',
               'zeros','linspace')

numpy_renames ={'ln':'log',
                 'atan':'arctan',
                 'atan2':'arctan2',
                 'acos':'arccos',
                 'acosh':'arccosh',
                 'asin':'arcsin',
                 'asinh':'arcsinh'}
                 
##
## More builtin commands, to set up the larch language:
##
def _group(larch=None,**kw):
    """create a group"""
    # try:
    g = larch.symtable.create_group()
    for k,v in kw.items():
        setattr(g,k,v)
    return g
#     except:
#         return None

def _showgroup(gname=None,larch=None):
    if larch is None:
        raise Warning("cannot show group -- larch broken?")

    if gname is None:
        gname = '_main'
    return larch.symtable.show_group(gname)

def _copy(obj,**kw):
    return copy.deepcopy(obj)

def _run(filename, larch=None, new_module=None, printall=False):
    """execute the larch text in a file as larch code. options:
       larch:       larch interpreter instance
       new_module:  create new "module" frame
       printall:    whether to print all outputs
    """
    if larch is None:
        print "must provide interpreter!"
        raise Warning("cannot run file '%s' -- larch broken?" % name)

    symtable = larch.symtable
    Group    = symtable.create_group
    leval    = larch.eval
    st_sys   = symtable._sys
    text     = None
    if isinstance(filename, file):
        text = filename.read()
        filename = filename.name
    elif (isinstance(filename, str) and
          os.path.exists(filename) and
          os.path.isfile(filename)):
        text = open(filename).read()

    # print '-->_run: ', filename, len(text), leval
    output = None
    if text is not None:
        inptext = inputText.InputText()
        inptext.put(text, filename=filename)
    
        if new_module is not None:
            # save current module group
            #  create new group, set as moduleGroup and localGroup
            symtable.save_frame()
            thismod = Group(name=new_module)
            st_sys.modules[new_module] = thismod
            symtable.set_frame((thismod, thismod))

        output = []
        while inptext:
            block, fname, lineno = inptext.get()
            # print ': block:', block, fname, lineno
            ret = leval(block, fname=fname, lineno=lineno)
            if callable(ret) and not isinstance(ret, type):
                try:
                    if 1 == len(block.split()):
                        ret = ret()
                except:
                    pass
            if larch.error:
                err = larch.error.pop(0)
                fname, lineno = err.fname, err.lineno
                out.append("%s:\n%s" % err.get_error())
                for err in larch.error:
                    if ((err.fname != fname or err.lineno != lineno) and
                        err.lineno > 0 and lineno > 0):
                        output.append("%s" % (err.get_error()[1]))
                self.input.clear()
                break
            elif printall and ret is not None:
                output.append("%s" % ret)

        # for a "newly created module" (as on import),
        # the module group is the return value
        if new_module is not None:
            symtable.restore_frame()
            output = thismod
        elif len(output) > 0:
            output = "\n".join(output)
        else:
            output = None
    return output


def _which(name, larch=None, **kw):
    "print out fully resolved name of a symbol"
    if larch is None:
        raise Warning("cannot locate symobol '%s' -- larch broken?" % name)

    print("Find symbol %s" % name)
    print( larch.symbtable.get_parent(name))
    
    



def _reload(mod,larch=None,**kw):
    """reload a module, either larch or python"""
    if larch is None: return None
    modname = None
    if mod in larch.symtable._sys.modules.values():
        for k,v in larch.symtable._sys.modules.items():
            if v == mod: modname = k
    elif mod in sys.modules.values():
        for k,v in sys.modules.items():
            if v == mod: modname = k
    elif (mod in larch.symtable._sys.modules.keys() or
          mod in sys.modules.keys()):          
        modname = mod
    
    if modname is not None:
        return larch.import_module(modname,do_reload=True)

def show_more(text,filename=None,writer=None,pagelength=30,prefix=''):
    """show lines of text in the style of more """
    txt = text[:]
    if isinstance(txt,str): txt = txt.split('\n')
    if len(txt) <1: return
    prompt = '== hit return for more, q to quit'
    ps = "%s (%%.2f%%%%) == " % prompt
    if filename: ps = "%s (%%.2f%%%%  of %s) == " % (prompt,filename)

    if writer is None:  writer = sys.stdout

    i = 0
    for i in range(len(txt)):
        if txt[i].endswith('\n'):
            writer.write("%s%s" % (prefix,txt[i]))
        else:
            writer.write("%s%s\n" % (prefix,txt[i]))
        i = i + 1
        if i % pagelength == 0:
            try:
                x = raw_input(ps %  (100.*i/len(txt)))
                if x in ('q','Q'): return
            except KeyboardInterrupt:
                writer.write("\n")
                return

def _ls(dir='.', **kws):
    " return list of files in the current directory "
    dir.strip()
    if len(dir) == 0: arg = '.'
    if os.path.isdir(dir):
        ret = os.listdir(dir)
    else:
        ret = glob(dir)
    if sys.platform == 'win32':
        for i, r in enumerate(ret):
            ret[i] = ret[i].replace('\\','/')
    return ret


def _cwd(x=None, **kws):
    "return current working directory"
    ret = os.getcwd()
    if sys.platform == 'win32':
        ret = ret.replace('\\','/')
    return ret

def _cd(name,**kwds):
    "change directorty"
    name = name.strip()
    if name:
        os.chdir(name)

    ret = os.getcwd()
    if sys.platform == 'win32':
        ret = ret.replace('\\','/')
    return ret

def _more(name,pagelength=24,**kws):
    "list file contents"
    try:
        f = open(name)
        l = f.readlines()

    except IOError:
        print "cannot open file: %s." % name
        return
    finally:
        f.close()
    show_more(l,filename=name,pagelength=pagelength)

    
def _help(*args,**kws):
    "show help on topic or object"
    helper.buffer = []
    larch = kws.get('larch',None)
    if helper.larch is None and larch is not None:  helper.larch = larch
    if args == ('',):
        args = ('help',)
    if helper.larch is None:
        helper.addtext('cannot start help system!')
    else:
        [helper.help(a.strip()) for a in args]

    return helper.getbuffer()

    
local_funcs = {'group':_group,
               'showgroup':_showgroup,
               'reload':_reload,
               'copy': _copy,
               'more': _more,
               'ls': _ls,
               'cd': _cd,
               'run': _run,
               'which': _which,                
               'cwd': _cwd, 
               'help': _help,
               }

       
