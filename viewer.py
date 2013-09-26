from lib.gui import ScanViewerApp
import getopt
try:
    import psycopg2
    HAS_PG = True
except:
    HAS_PG = False

args = {}
if HAS_PG:
    args = dict(dbname='epics_scan', server='postgresql',
                host = 'mini',  user = 'epics',
                password = 'epics', create=True)

app = ScanViewerApp(**args)
app.MainLoop()
