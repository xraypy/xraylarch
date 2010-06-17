import larch

interp = larch.Interpreter()
stable = interp.symtable

stable.set_symbol('_main.a', value = 1)
stable.new_group('g1', s='a string', en=722)

stable.set_symbol('_sys.var', value=1)
stable.set_symbol('_main.b',  value='value of b')
stable.set_symbol('_main.g1.t', value='another string')
stable.set_symbol('_main.g1.d', value={'yes': 1, 'no': 0})

stable.new_group('g2')
stable.set_symbol('g2.data',value=[1,2,3])
stable.set_symbol('g2.a' ,value = 'hello')

stable.set_symbol('g2.subgroup' ,
                  value = larch.Group(__name__='subgroup x' , q=2, w=99))

print '<<< Groups: ' 
for g in stable._subgroups():
    if g not in ('_sys', '_math', '_builtin', 'moduleGroup', 'localGroup'):
        print stable.show_group(g)

print '>>>' 
