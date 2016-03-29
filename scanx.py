import time
import glob
import os
from lib import Interpreter

_larch = Interpreter()

moddir = 'T:/xas_user/scan_config/13ide/macros'
_sys = _larch.symtable._sys

os.chdir(moddir)
for name in glob.glob('*.lar'):
    modname = name[:-4]
    _larch.error = []
    
    _larch.eval('import %s' % modname)
    if len(_larch.error) > 0:
        emsg = '\n'.join(_larch.error[0].get_error())
        print '==Import Error %s/%s' % (modname, emsg)
    else:
        if modname not in _sys.searchGroups:
            _sys.searchGroups.append(modname)
        thismod  = _larch.symtable.get_symbol(modname)
        _sys.searchGroupObjects.append(thismod)


def run(cmd):
    time.sleep(1.0)
    out = _larch.eval(cmd)
    print 'Run output: ', out
    if len(_larch.error) > 0:
        err = _larch.error[0]
        print '_________  ', err
        # for attr in dir(err):
        #     if not attr.startswith('_'):
        #         print(attr, getattr(err, attr))

class InvalidName: pass

def getsym(_larch, name):
    stab = _larch.symtable
    if not hasattr(stab, '__invalid_name'):
        stab.__invalid_name = InvalidName()
    print( '_getsym ', name, stab)

    print '_math' in stab._sys.searchGroups, 'instruments' in stab._sys.searchGroups
    # print len(stab._sys.searchGroupObjects)
    # print dir(stab)

    searchGroups = stab._fix_searchGroups()
    stab.__parents = []
    
    if stab not in searchGroups:
        searchGroups.append(stab)
    def public_attr(grp, name):
        return (hasattr(grp, name)  and
                not (grp is stab and name in stab._private))

    parts = name.split('.')

    # print searchGroups
    # print stab._private
    # print [g.__name__ for g in searchGroups]
    print 'instruments' in [g.__name__ for g in searchGroups]
    if len(parts) == 1:
        for grp in searchGroups:
            if public_attr(grp, name):
                stab.__parents.append(grp)
                print("  FOUND!  ", grp, name)
                return getattr(grp, name)

    # more complex case: not immediately found in Local or Module Group
    parts.reverse()
    top   = parts.pop()
    # print('__ get sym2 ',  stab, top, parts)
    out   = stab.__invalid_name
    if top == stab.top_group:
        out = stab
    else:
        for grp in searchGroups:
            # if  grp.__name__.startswith('inst'):
            #     print dir(grp), top, public_attr(grp, top)
            if public_attr(grp, top):
                stab.__parents.append(grp)
                out = getattr(grp, top)
    if out is stab.__invalid_name:
        raise NameError("'%s' is not defined" % name)
    
    # print 'GetSym OUT:  ', out, len(searchGroups)


# print'=================='
#print 'GetSym: sin '
#print getsym(_larch, 'sin')

#print 'GetSym: detector_distance '
#print getsym(_larch, 'detector_distance')


## run('print sin(33)')
print '============================'
print '============================'
run('detector_distance(55)')


# print _larch.symtable._sys.searchGroups
print '_math' in _larch.symtable._sys.searchGroups
print 'instruments' in _larch.symtable._sys.searchGroups


run('detector_distance(58)')

## print 'GetSym: sin ', getsym(_larch, 'sin')

# print 'GetSym: detector_distance '
# print getsym(_larch, 'detector_distance')
#

#print _larch.symtable.get_symbol('sin')


#print getsym(_larch, 'sin')

#print getsym(_larch, 'detector_distance')



## .get_symbol('detector_distance')


# time.sleep(2)

# _larch.run('dxd(12)')


## larchi.run('print sin(33)')

###  time.sleep(2)

## larchi.run('detector_distance(50)')




