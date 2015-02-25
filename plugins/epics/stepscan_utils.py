#!/usr/bin/python 
import epics
import time
import os

class mapper(epics.Device):
    """ 
    Fast Map Database
    """
    _attrs = ('Start', 'Abort', 'scanfile', 'info', 'status', 'message',
             'filename', 'basedir', 'workdir',
             'nrow', 'maxrow', 'npts', 'TSTAMP','UNIXTS')
    
    def __init__(self,prefix,filename=None):
        self._prefix = prefix
        epics.Device.__init__(self, self._prefix,
                              attrs=self._attrs)
        
    def StartScan(self,filename=None,scanfile=None):
        if filename is not None:
            self.filename=filename
        if scanfile is not None:
            self.scanfile=scanfile

        epics.poll()
        self.put('message','starting...')
        self.put('Start',1)

    def AbortScan(self,filename=None):
        self.Abort = 1
        self.status = 4

    def ClearAbort(self):
        self.Abort = 0
        time.sleep(.025)
        self.Start = 0
        self.status = 0
        
    def setTime(self):
        "Set Time"
        self.put('UNIXTS',  time.time())
        self.put('TSTAMP',  time.strftime('%d-%b-%y %H:%M:%S'))

    def setMessage(self,msg):
        "Set message"
        self.put('message',  msg)

    def setNrow(self,nrow,maxrow=None):
        self.put('nrow', nrow)
        if maxrow is not None: self.put('maxrow', maxrow)

    def setNpoints(self,npts):
        self.put('npts', npts)
        
    def setInfo(self,msg):
        self.put('info',  msg)
        
    def __Fget(self, attr):
        return self.get(attr, as_string=True)

    def __Fput(self, attr, val):
        return self.put(attr, val)
    
    def pv_property(attr):
        return property(lambda self:     self.__Fget(attr), 
                        lambda self, val: self.__Fput(attr, val),
                        None, None)

    basedir  = pv_property('basedir')
    status   = pv_property('status')    
    workdir  = pv_property('workdir')
    filename = pv_property('filename')
    scanfile = pv_property('scanfile')
    info     = pv_property('info')
    message  = pv_property('message')


class EpicsScanDB(epics.Device):
    """interface for scan server status via larchscan.db"""

    _attrs = ('status', 'message', 'last_error', 'command',
              'filename', 'basedir', 'workdir', 'TSTAMP',
              'cmd_id', 'Shutdown', 'Abort')

    def __init__(self, prefix):
        self._prefix = prefix
        epics.Device.__init__(self, self._prefix, attrs=self._attrs)

    def AbortScan(self):
        self.Abort = 1
        self.status = 4

    def setTime(self, ts=None):
        "Set Time"
        if ts is None:
            ts = time.strftime('%d-%b-%y %H:%M:%S')
        self.TSTAMP =  ts

    def __Fget(self, attr):      return self.get(attr, as_string=True)
    def __Fput(self, attr, val): return self.put(attr, val)

    def pv_property(attr):
        return property(lambda self:     self.__Fget(attr),
                        lambda self, val: self.__Fput(attr, val),
                        None, None)

    status   = pv_property('status')
    message  = pv_property('message')
    last_error = pv_property('last_error')
    command  = pv_property('command')
    filename = pv_property('filename')
    basedir  = pv_property('basedir')
    workdir  = pv_property('workdir')
    cmd_id   = pv_property('cmd_id')


