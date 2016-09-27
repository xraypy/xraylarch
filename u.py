from __future__ import print_function

import larch
_larch = larch.Interpreter()
inp = larch.InputText(_larch)

text = """for x in range(10):
  print 'a1'
   if x > 2: print 'a2'
  print 'b'
#endfor
"""


inp.put(text)

while inp.queue.qsize() > 0:
    block, fname, lineno =  inp.get()
    # print(block)
    _larch.eval(block, fname=fname, lineno=lineno)
    
