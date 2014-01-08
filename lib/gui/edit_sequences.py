
import sys
import time

import wx
import wx.lib.scrolledpanel as scrolled

from ..ordereddict import OrderedDict
from .gui_utils import GUIColors, set_font_with_children, YesNo
from .gui_utils import add_button, pack, SimpleText
import  wx.grid as gridlib

LEFT = wx.ALIGN_LEFT|wx.ALIGN_CENTER_VERTICAL|wx.ALL
CEN  = wx.ALIGN_CENTER|wx.ALIGN_CENTER_VERTICAL|wx.ALL

builtin_macros = """ (text = '<builtin>')
  name              arguments                         
  ca_put            'PVName:str, Value:str'
  ca_get            'PVName:str, OutputValue:str'
  do_scan           'ScanName:enum, OutputFile:str, Nrepeat:int'
  move_instrument   'InstName:enum, PosName:enum'
  move_sample       'SampleName:enum'
  scan_at           'ScanName:enum, SampleName:enum'
"""

colLabels = [' Status ', ' Update Time ', ' Action ', ' Output File ', ' Command ', '', '', '']
ACTIONS = ('Enable', 'Skip')

Buttons = ['Run', 'Pause', 'Cancel All', 'Abort Current Command', 
           'Insert Commands Here', 'Add Commands to End']



class SequencesFrame(wx.Frame) :
    """Edit/Manage/Run/View Sequences"""
    def __init__(self, parent, pos=(-1, -1)):

        self.parent = parent
        self.scandb = parent.scandb

        style    = wx.DEFAULT_FRAME_STYLE|wx.TAB_TRAVERSAL
        labstyle  = wx.ALIGN_LEFT|wx.ALIGN_CENTER_VERTICAL|wx.ALL
        rlabstyle = wx.ALIGN_RIGHT|wx.ALIGN_CENTER_VERTICAL|wx.ALL
        tstyle    = wx.ALIGN_LEFT|wx.ALIGN_CENTER_VERTICAL

        self.Font10=wx.Font(10, wx.SWISS, wx.NORMAL, wx.BOLD, 0, "")
        titlefont = wx.Font(13, wx.SWISS, wx.NORMAL, wx.BOLD, 0, "")

        wx.Frame.__init__(self, None, -1,
                          'Epics Scanning: Seuqences')

        self.SetFont(self.Font10)
        sizer = wx.GridBagSizer(10, 5)
        panel = scrolled.ScrolledPanel(self, size=(675, 500))
        self.colors = GUIColors()
        panel.SetBackgroundColour(self.colors.bg)

        # title row
        title = SimpleText(panel, 'Extra PVs Setup',  font=titlefont,
                           colour=self.colors.title, style=tstyle)

        sizer.Add(title,        (0, 0), (1, 3), LEFT, 5)

        ir = 1
        sizer.Add(SimpleText(panel, label='Description', size=(175, -1)),
                  (ir, 0), (1, 1), rlabstyle, 2)
        sizer.Add(SimpleText(panel, label='PV Name', size=(175, -1)),
                  (ir, 1), (1, 1), labstyle, 2)
        sizer.Add(SimpleText(panel, label='Use?', size=(60, -1)),
                  (ir, 2), (1, 1), labstyle, 2)
        sizer.Add(SimpleText(panel, label='Erase?', size=(60, -1)),
                  (ir, 3), (1, 1), labstyle, 2)

        self.widlist = []
        for this in self.scandb.getall('extrapvs'):
            desc   = wx.TextCtrl(panel, -1, value=this.name, size=(175, -1))
            pvctrl = wx.TextCtrl(panel, value=this.pvname,  size=(175, -1))
            usepv  = YesNo(panel, defaultyes=this.use)
            delpv  = YesNo(panel, defaultyes=False)
            
            ir +=1
            sizer.Add(desc,   (ir, 0), (1, 1), rlabstyle, 2)
            sizer.Add(pvctrl, (ir, 1), (1, 1), labstyle, 2)
            sizer.Add(usepv,  (ir, 2), (1, 1), labstyle, 2)
            sizer.Add(delpv,  (ir, 3), (1, 1), labstyle, 2)            
            self.widlist.append((this, desc, pvctrl, usepv, delpv))

        for i in range(3):
            desc   = wx.TextCtrl(panel, -1, value='', size=(175, -1))
            pvctrl = wx.TextCtrl(panel, value='', size=(175, -1))
            usepv  = YesNo(panel, defaultyes=True)
            ir +=1
            sizer.Add(desc,   (ir, 0), (1, 1), rlabstyle, 2)
            sizer.Add(pvctrl, (ir, 1), (1, 1), labstyle, 2)
            sizer.Add(usepv,  (ir, 2), (1, 1), labstyle, 2)
            self.widlist.append((None, desc, pvctrl, usepv, None))

        ir += 1
        sizer.Add(wx.StaticLine(panel, size=(350, 3), style=wx.LI_HORIZONTAL),
                  (ir, 0), (1, 4), wx.ALIGN_LEFT|wx.EXPAND, 3)
        #
        ir += 1
        sizer.Add(self.make_buttons(panel), (ir, 0), (1, 2), wx.ALIGN_LEFT, 3)

        pack(panel, sizer)

        panel.SetupScrolling()

        mainsizer = wx.BoxSizer(wx.VERTICAL)
        mainsizer.Add(panel, 1, wx.GROW|wx.ALL, 1)

        pack(self, mainsizer)
        self.Show()
        self.Raise()

    def add_subtitle(self, panel, text):
        p = wx.Panel(panel)
        s = wx.BoxSizer(wx.HORIZONTAL)
        s.Add(wx.StaticLine(p, size=(125, 3), style=wx.LI_HORIZONTAL), 0, LEFT, 5)
        s.Add(SimpleText(p, text,  colour='#333377'),  0, LEFT, 5)
        s.Add(wx.StaticLine(p, size=(185, 3), style=wx.LI_HORIZONTAL), 1, LEFT, 5)
        pack(p, s)
        return p

    def make_buttons(self, panel):
        btnsizer = wx.StdDialogButtonSizer()
        btn_ok = wx.Button(panel, wx.ID_OK)
        btn_no = wx.Button(panel, wx.ID_CANCEL)
        panel.Bind(wx.EVT_BUTTON, self.onApply, btn_ok)
        panel.Bind(wx.EVT_BUTTON, self.onClose, btn_no)
        btn_ok.SetDefault()
        btnsizer.AddButton(btn_ok)
        btnsizer.AddButton(btn_no)

        btnsizer.Realize()
        return btnsizer

    def onApply(self, event=None):
        for w in self.widlist:
            obj, name, pvname, usepv, erase = w
            if usepv is not None:
                usepv = usepv.GetSelection()
            else:
                usepv = True

            if erase is not None:
                erase = erase.GetSelection()
            else:
                erase = False
            name   = name.GetValue().strip()
            pvname = pvname.GetValue().strip()
            if len(name) < 1 or len(pvname) < 1:
                continue
            if erase and obj is not None:
                self.scandb.del_extrapv(obj.name)
            elif obj is not None:
                obj.name = name
                obj.pvname = pvname
                obj.use  = usepv
            elif obj is None:
                self.scandb.add_extrapv(name, pvname, use=usepv)

        self.scandb.commit()
        self.Destroy()


    def onClose(self, event=None):
        self.Destroy()

