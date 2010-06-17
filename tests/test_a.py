from inputText import InputText
from interpreter import Interpreter
import sys

inptext = InputText()
larch = Interpreter()


if len(sys.argv) == 1:
    infiles = ['tests/a.lar']
else:
    sys.argv.pop(0)
    infiles = sys.argv

for fname in infiles:
    print "==== reading '%s' ==== " % fname
    text = open(fname).read()

    inptext.put(text,filename=fname,lineno=1)
    
    print 'processing... :'
    while len(inptext)>0:
        block,fname,lno = inptext.get()
        ret = larch.eval(block)
    print '=== returned ' , ret
