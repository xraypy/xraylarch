from larch import Interpreter
linp = Interpreter()
def onVarChange(group=None, symbolname=None, value=None, **kws):
    print( 'var changed ', group, symbolname, value, kws)

linp('x = 100.0')
linp.symtable.add_callback('x', onVarChange)

linp.symtable.set_symbol('x', 30)
linp.symtable.set_symbol('x', 'a string')
linp('x = arange(7)')
