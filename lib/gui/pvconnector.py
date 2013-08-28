import time
import wx
import epics
from epics.wx import EpicsFunction, DelayedEpicsCallback

class PVNameCtrl(wx.TextCtrl):
    """Text Control for an Epics PV that should try to be connected.
    this must be used with a EpicsPVList

    on <<return>> or <<lose focus>>, this tries to connect to the
    PV named in the widget.  If provided, the action provided is run.
    """
    def __init__(self, panel, value='', pvlist=None,  action=None, **kws):
        self.pvlist = pvlist
        self.action = action
        wx.TextCtrl.__init__(self, panel, wx.ID_ANY, value=value, **kws)
        self.Bind(wx.EVT_CHAR, self.onChar)
        self.Bind(wx.EVT_KILL_FOCUS, self.onFocus)

    def onFocus(self, evt=None):
        if self.pvlist is not None:
            self.pvlist.connect_pv(self.Value, action=self.action,
                                   wid=self.GetId())
        evt.Skip()

    def onChar(self, event):
        key   = event.GetKeyCode()
        value = wx.TextCtrl.GetValue(self).strip()
        pos   = wx.TextCtrl.GetSelection(self)
        if key == wx.WXK_RETURN and self.pvlist is not None:
            self.pvlist.connect_pv(value, action=self.action,
                                   wid=self.GetId())
        event.Skip()

class EpicsPVList(object):
    """a wx class to hold a list of PVs, and
    handle the connection of new PVs.

    The main attribute is '.pvs', a dictionary of PVs, with
    pvname keys.

    The main way to use this is with the PVNameCtrl above

    """
    def __init__(self, parent, timeout=30):
        self.pvs = {}
        self.in_progress = {}
        self.timeout = timeout
        self.etimer = wx.Timer(parent)
        parent.Bind(wx.EVT_TIMER, self.onTimer, self.etimer)
        self.etimer.Start(75)

    def onTimer(self, event=None):
        "timer event handler: looks for in_progress, may timeout"
        time.sleep(0.001)
        if len(self.in_progress) == 0:
            return
        try:
            for pvname in self.in_progress:
                # print 'waiting for connect: ', pvname
                self.__connect(pvname)
                if time.time() - self.in_progress[pvname][2] > self.timeout:
                    self.in_progress.pop(pvname)
        except:
            pass

    @EpicsFunction
    def connect_pv(self, pvname, wid=None, action=None):
        """try to connect epics PV, executing
        action(wid=wid, pvname=pvname, pv=pv)
        """
        if pvname is None or len(pvname) < 1:
            return
        if '.' not in pvname:
            pvname = '%s.VAL' % pvname
        pvname = str(pvname)
        if pvname in self.pvs:
            return
        if pvname not in self.in_progress:
            self.pvs[pvname] = epics.PV(pvname)
            self.in_progress[pvname] = (wid, action, time.time())

    @EpicsFunction
    def add_pv(self, pv, wid=None, action=None):
        """add an already connected PV to the pvlist"""
        # print ' inprogress  = ', len(self.in_progress)
        if isinstance(pv, epics.PV) and pv not in self.pvs:
            self.pvs[pv.pvname] = pv

    @EpicsFunction
    def __connect(self, pvname):
        """if a new epics PV has connected, run the requested action"""
        # print ' __connect!! ', pvname
        if pvname not in self.pvs:
            self.pvs[pvname] = epics.PV(pvname)
        pv = self.pvs[pvname]
        time.sleep(0.002)

        if not self.pvs[pvname].connected:
            return

        try:
            wid, action, itime = self.in_progress.pop(pvname)
        except KeyError:
            wid, action, itime = None, None, 0
        pv.get_ctrlvars()
        # print 'PV connected: ', pv
        if hasattr(action, '__call__'):
            action(wid=wid, pvname=pvname, pv=self.pvs[pvname])
