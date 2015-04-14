#!/usr/bin/env python

from epicsscan import ScanServer

connection = dict(server='postgresql',
                  host='mini.cars.aps.anl.gov',
                  user='epics',
                  password='epics')

s = ScanServer(dbname='epics_scan', **connection)
s.mainloop()



