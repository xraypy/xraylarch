#!/usr/bin/env python

import time
import threading

from ..scandb import ScanDB

class ScanServer():
    def __init__(self, dbname=None, **kws):
        self.db = None
        self.abort = False
        self.command_in_progress = False
        if dbname is not None:
            self.connect(dbname, **kws)

    def connect(self, dbname, **kws):
        """connect to Scan Database"""
        self.db = ScanDB(dbname, **kws)

    def sleep(self, t=0.05):
        try:
            time.sleep(t)
        except KeyboardInterrupt:
            self.abort = True

    def finish(self):
        print 'shutting down!'

    def execute_command(self, req):
        print 'EXECUTE Command ', req
        print 'req.command = ', req.command
        print 'req.arguments = ', req.arguments
        print 'req.status_id, req.status = ', req.status_id, req.status
        print 'req.scandefs = ', req.scandefs
        print 'req.request_time = ', req.request_time
        print 'req.start_time = ', req.start_time
        print 'req.modify_time = ', req.modify_time
        print 'req.output_value = ', req.output_value
        print 'req.output_file = ', req.output_file

        cmd_thread = Thread(target=self.do_command,
                            kwargs=dict(req=req),
                            name='cmd_thread')

        self.db.set_command_status(req.id, 'starting')
        self.command_in_progress = True
        cmd_thread.start()
        cmd_thread.join()
        self.db.set_command_status(req.id, 'finished')
        self.command_in_progress = False

    def do_command(self, req):
        print 'IN do_command ', req
        time.sleep(3.0)
        print 'command done!'

    def look_for_interrupt_requests(self):
        """set interrupt requests:
        abort / pause / resume
        it is expected that
        """
        get = self.db.get_info
        self.abort_request = get('request_command_abort') == '1'
        self.pause_request = get('request_command_pause') == '1'
        self.resume_request = get('request_command_resume') == '1'

    def mainloop(self):
        print "starting server"

        while True:
            self.sleep()
            print 'tick'
            if self.abort:   break
            reqs = self.db.get_commands('requested')
            if self.command_in_progress:
                self.look_for_interrupt_requests()
                self.sleep(t=0.10)
            if len(reqs) == 0 or self.command_in_progress:
                self.sleep(t=0.10)
            else:
                nextreq = reqs.pop()
                print 'Will do next request: ', nextreq
                self.execute_command(nextreq)

        # mainloop end
        self.finish()




if __name__  == '__main__':
    s = ScanServer(dbname='A.sdb')
    s.mainloop()


