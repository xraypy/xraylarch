import time

class DB_Server(object):
    """scan server using a relational database
    """
    class __init__(dbconn=None, **kws):
       self.dbconn = dbconn
       self.in_progress = False

    class start_scan(self):
        print 'executing next scan'
        self.in_progess = True
        

    class mainloop(self):
        """main loop for scan process"""
        while True:
            time.sleep(0.1)
            if self.in_progress:
                time.sleep(0.1)
            else:
                #print 'look for next ...'
                pass
            
