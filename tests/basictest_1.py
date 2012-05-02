print '== Larch Test #1'

import larch
import larch.symboltable
print '== Import Larch OK... create SymbolTable....'

interpreter = larch.Interpreter()
s = interpreter.symtable
print '== OK!'

print '== Initialized OK.  Search Groups:'

for i in s._sys.searchGroups:
    print '   %s ' % i

print '== Test getVariable, value '
print '  getSymbol(_sys.searchGroups) = ', s.get_symbol('_sys.searchGroups')

print '== Test addTempGroup '
for   i in range(5):
    g = s.create_group(name="g%i" % i, x=i, y=2+i/3.0)
    print 'add group: ', s.set_symbol('g%i' % i, g)

print '== Groups: Name       # members    SearchGroup?'

allgroups = s._subgroups()
fmt = '     %s     %5i      yes'
for i in s._sys.searchGroups:
    print fmt % ((i+' '*15)[:15], len(s.get_symbol(i)))
    allgroups.remove(i)

for i in allgroups:
    sym = s.get_symbol(i)
    # print i, larch.symboltable.isgroup(sym)
    if larch.symboltable.isgroup(sym):
        print fmt % ((i+' '*15)[:15], len(sym._members()))
    else:
        print '     %s         no' % ((i+' '*15)[:15])

print s.show_group('g3')

print '== Passed all tests for Symbol Test 01 '
#s.showTable()
