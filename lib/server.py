#!/usr/bin/env python

import time
from .scandb import ScanDB

dbname = 'N1.sdb'


class ScanServer():
    def __init__(self, dbname='N1.sdb', **kws):
        self.db = ScanDB(dbname, **kws)
        
        self.abort = False

    def sleep(self, t=0.025):
        try:
            time.sleep(t)
        except KeyboardInterrupt:
            self.abort = True

    def finish(self):
        print 'shutting down!'

    def execute_command(self, req):
        print 'EXECUTE Command ', req
        time.sleep(0.5)
        self.scandb.set_command_status(req.id, 'finished')
        
    def mainloop(self):
        print "starting server"

        while True:
            self.sleep()
            if self.abort:   break
            reqs = self.scandb.get_commands('requested')
            if len(reqs) == 0:
                self.sleep(t=0.05)
            else:
                nextreq = reqs.pop()
                print 'Will do next request: ', nextreq
                self.execute_command(nextreq)
                
        # mainloop end
        self.finish()
        
        
    
    
if __name__  == '__main__':
    s = ScanServer(dbname='N1.sdb')
    s.mainloop()
    
    
