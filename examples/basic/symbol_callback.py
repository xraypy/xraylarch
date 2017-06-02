import larch
i = larch.Interpreter()
def onVarChange(group=None, symbolname=None, value=None, **kws):
    print( 'var changed ', group, symbolname, value, kws)

i('x = 100.0')
i.symtable.add_callback('x', onVarChange)

i.symtable.set_symbol('x', 30)
i.symtable.set_symbol('x', 'a string')
i('x = arange(7)')
