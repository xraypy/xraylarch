import wx
import epics
from lib.gui import ScanApp

#epics.ca.initialize_libca()
scanner = ScanApp(dbname='epics_scan',
                  server='postgresql',
                  host='mini.cars.aps.anl.gov',
                  user='epics', password='epics')
scanner.MainLoop()
