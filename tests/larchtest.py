#!/usr/bin/env python2.6

import lib as larch
import sys

interp = larch.interp()
input  = larch.input()

for arg in sys.argv[1:]:
    try:
        input.readfile(arg)
    except IOError:
        print "could not read %s" % arg

    while input:
        block,fname,lineno = input.get()
        ret = interp.eval(block,fname=fname,lineno=lineno)
        if callable(ret) and not isinstance(ret,type):
            try:
                if 1 == len(block.split()):
                    ret = ret()
            except:
                pass
        if interp.error:
            print '== Error =='
            err  = interp.error.pop(0)
            print "%s: %s" % err.get_error()
            for err in interp.error:
                err_type,err_msg =  err.get_error()
                if not (err_type.startswith('Extra Error')):
                    print err_msg
            print '==========='                    
            break
        if ret is not None:
            print ret
        
