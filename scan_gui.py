import wx
import epics
from lib.gui import ScanApp

#epics.ca.initialize_libca()
connection = dict(server='postgresql',
                  host='mini.cars.aps.anl.gov',
                  user='epics',
                  password='epics')

scanner = ScanApp(dbname='epics_scan', **connection)
scanner.MainLoop()
