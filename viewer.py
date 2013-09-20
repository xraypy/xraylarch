from lib.gui import ViewerApp
app = ViewerApp(dbname='epics_scan', server='postgresql',
                host = 'mini',  user = 'epics', 
                password = 'epics', create=True)
app.MainLoop()
