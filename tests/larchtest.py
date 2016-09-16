#!/usr/bin/env python2.6

import larch
import sys
import time
t0  = time.time()
print('---')
session = larch.Interpreter()
print('session ready; %0.3f s' % time.time()-t0)
input = larch.InputText()
for arg in sys.argv[1:]:
    try:
        input.readfile(arg)
    except IOError:
        print("could not read %s" % arg)

    while input:
        block,fname,lineno = input.get()
        ret = session.eval(block,fname=fname,lineno=lineno)
        if callable(ret) and not isinstance(ret,type):
            try:
                if 1 == len(block.split()):
                    ret = ret()
            except:
                pass
        if session.error:
            print('== Error ==')
            err  = session.error.pop(0)
            print("%s: %s" % err.get_error())
            break
        if ret is not None:
            print(ret)

