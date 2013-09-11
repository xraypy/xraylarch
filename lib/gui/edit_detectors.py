
import sys
import time
import json
import wx
import wx.lib.scrolledpanel as scrolled

from ..ordereddict import OrderedDict
from ..detectors import DET_DEFAULT_OPTS, AD_FILE_PLUGINS

from .gui_utils import (GUIColors, set_font_with_children, YesNo, Closure,
                        add_button, add_choice, pack, SimpleText,FloatCtrl)

from ..utils import strip_quotes

# from .pvconnector import PVNameCtrl

LEFT = wx.ALIGN_LEFT|wx.ALIGN_CENTER_VERTICAL
CEN  = wx.ALIGN_CENTER|wx.ALIGN_CENTER_VERTICAL|wx.ALL

DET_CHOICES = ('scaler', 'mca', 'multimca', 'areadetector')
AD_CHOICES = ['None'] + list(AD_FILE_PLUGINS)

class DetectorDetailsDialog(wx.Dialog):
    """Full list of detector settings"""
    def __init__(self, parent, det=None):
        self.scandb = parent.scandb
        self.det = det
        title = "Settings for '%s'?" % (det.name)
        wx.Dialog.__init__(self, parent, wx.ID_ANY, title=title)
        self.build_dialog(parent)

    def build_dialog(self, parent):
        panel = wx.Panel(self)
        self.colors = GUIColors()
        panel.SetBackgroundColour(self.colors.bg)


        self.SetFont(parent.GetFont())
        titlefont  = self.GetFont()
        titlefont.PointSize += 2
        titlefont.SetWeight(wx.BOLD)

        sizer = wx.GridBagSizer(10, 3)

        labstyle  = wx.ALIGN_LEFT|wx.ALIGN_CENTER_VERTICAL|wx.ALL
        rlabstyle = wx.ALIGN_RIGHT|wx.ALIGN_CENTER_VERTICAL|wx.ALL
        tstyle    = wx.ALIGN_RIGHT|wx.ALIGN_CENTER_VERTICAL
        # title row
        i = 0
        for titleword in (' Setting ', 'Value'):
            txt =SimpleText(panel, titleword,
                            font=titlefont,
                            minsize=(100, -1),
                            style=tstyle)
            sizer.Add(txt, (0, i), (1, 1), labstyle, 1)
            i += 1

        sizer.Add(wx.StaticLine(panel, size=(150, -1),
                                style=wx.LI_HORIZONTAL),
                  (1, 0), (1, 4), wx.ALIGN_CENTER|wx.GROW|wx.ALL, 0)

        self.wids = {}
        prefix = self.det.pvname
        opts   = json.loads(self.det.options)
        optkeys = opts.keys()        
        optkeys.sort()
        irow = 2
        for key in optkeys:
            if key in ('use', 'kind', 'label'):
                continue
            val = opts[key]
            label = key
            for short, longw in (('_', ' '),
                                 ('chan', 'channels'),
                                 ('mcas', 'MCAs'),
                                 ('rois', 'ROIs')):
                label = label.replace(short, longw)
                                
            if label.startswith('n'):
                label = '# of %s' % (label[1:])
            label = label.title()
            # pvname = normalize_pvname(pvpos.pv.name)
            label = SimpleText(panel, label, style=tstyle)
            val = strip_quotes(val)

            if val in (True, False, 'Yes', 'No'):
                defval = val in (True, 'Yes')
                wid = YesNo(panel, defaultyes=defval)
            elif key.lower() == 'file_plugin':
                wid = add_choice(panel, AD_CHOICES, default=1)
            else:
                wid   = wx.TextCtrl(panel, -1, size=(80, -1),
                                    value=str(val))
            
            sizer.Add(label, (irow, 0), (1, 1), labstyle,  2)
            sizer.Add(wid,   (irow, 1), (1, 1), rlabstyle, 2)
            self.wids[key] = wid
            irow  += 1

        sizer.Add(wx.StaticLine(panel, size=(150, -1),
                                style=wx.LI_HORIZONTAL),
                  (irow, 0), (1, 4), wx.ALIGN_CENTER|wx.GROW|wx.ALL, 0)

        btnsizer = wx.StdDialogButtonSizer()
        btn = wx.Button(panel, wx.ID_OK)
        btn.SetDefault()
        btnsizer.AddButton(btn)
        btnsizer.AddButton(wx.Button(panel, wx.ID_CANCEL))

        btnsizer.Realize()
        sizer.Add(btnsizer, (irow+4, 0), (1, 2), CEN, 2)
        pack(panel, sizer)

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(panel, 0, 0, 0)
        pack(self, sizer)

class DetectorFrame(wx.Frame) :
    """Frame to Setup Scan Detectors"""
    def __init__(self, parent, pos=(-1, -1)):
        self.parent = parent
        self.scandb = parent.scandb
        self.scanpanels = parent.scanpanels

        self.detectors = self.scandb.getall('scandetectors', orderby='id')
        self.counters = self.scandb.getall('scancounters', orderby='id')

        style    = wx.DEFAULT_FRAME_STYLE|wx.TAB_TRAVERSAL

        self.Font10=wx.Font(10, wx.SWISS, wx.NORMAL, wx.BOLD, 0, "")
        titlefont = wx.Font(13, wx.SWISS, wx.NORMAL, wx.BOLD, 0, "")

        wx.Frame.__init__(self, None, -1, 'Epics Scanning: Detector Setup')
        self.SetFont(self.Font10)

        sizer = wx.GridBagSizer(12, 5)
        panel = scrolled.ScrolledPanel(self) # , size=(675, 625))
        self.SetMinSize((650, 500))
        self.colors = GUIColors()
        panel.SetBackgroundColour(self.colors.bg)

        # title row
        title = SimpleText(panel, 'Detector Setup',  font=titlefont,
                           minsize=(130, -1),
                           colour=self.colors.title, style=LEFT)

        sizer.Add(title,        (0, 0), (1, 1), LEFT|wx.ALL, 2)

        desc = wx.StaticText(panel, -1, label='Detector Settling Time (sec): ',
                             size=(180, -1))
        
        self.settle_time = wx.TextCtrl(panel, size=(75, -1),
                            value=self.scandb.get_info('det_settle_time', '0.001'))
        sizer.Add(desc,              (1, 0), (1, 2), CEN,  3)
        sizer.Add(self.settle_time,  (1, 2), (1, 1), LEFT, 3)

        ir = 2
        sizer.Add(self.add_subtitle(panel, 'Available Detectors'),
                  (ir, 0),  (1, 5),  LEFT, 0)

        ir +=1
        sizer.Add(SimpleText(panel, label='Label',  size=(125, -1)),
                  (ir, 0), (1, 1), LEFT, 1)
        sizer.Add(SimpleText(panel, label='PV prefix', size=(175, -1)),
                  (ir, 1), (1, 1), LEFT, 1)  
        sizer.Add(SimpleText(panel, label='Use?',     size=(80, -1)),
                  (ir, 2), (1, 1), LEFT, 1)
        sizer.Add(SimpleText(panel, label='Kind',     size=(80, -1)),
                  (ir, 3), (1, 1), LEFT, 1)
        sizer.Add(SimpleText(panel, label='Details',  size=(60, -1)),
                  (ir, 4), (1, 1), LEFT, 1)
        sizer.Add(SimpleText(panel, label='Erase?',  size=(60, -1)),
                  (ir, 5), (1, 1), LEFT, 1)

        self.widlist = []
        for det in self.detectors:
            ir +=1
            dkind = strip_quotes(det.kind)
            dkind  = det.kind.title().strip()
            desc   = wx.TextCtrl(panel, value=det.name,   size=(125, -1))
            pvctrl = wx.TextCtrl(panel, value=det.pvname, size=(175, -1))
            use    = YesNo(panel, defaultyes=(det.use in ('True', 1, None)))
            detail = add_button(panel, 'Edit', size=(60, -1),
                                action=Closure(self.onDetDetails, det=det))
            kind = add_choice(panel, DET_CHOICES, size=(110, -1))
            kind.SetStringSelection(dkind)
            erase  = YesNo(panel, defaultyes=False)
            sizer.Add(desc,   (ir, 0), (1, 1),  CEN, 1)
            sizer.Add(pvctrl, (ir, 1), (1, 1), LEFT, 1)
            sizer.Add(use,    (ir, 2), (1, 1), LEFT, 1)
            sizer.Add(kind,   (ir, 3), (1, 1), LEFT, 1)
            sizer.Add(detail, (ir, 4), (1, 1), LEFT, 1)
            sizer.Add(erase,  (ir, 5), (1, 1), LEFT, 1)

            self.widlist.append(('old_det', det, desc, pvctrl, use, kind, erase))

        # select a new detector
        for i in range(2):
            ir +=1
            desc   = wx.TextCtrl(panel, value='',   size=(125, -1))            
            pvctrl = wx.TextCtrl(panel, value='',   size=(175, -1))
            use    = YesNo(panel)
            kind = add_choice(panel, DET_CHOICES, size=(110, -1))
            kind.SetStringSelection(dkind)            
            sizer.Add(desc,   (ir, 0), (1, 1), CEN, 1)
            sizer.Add(pvctrl, (ir, 1), (1, 1), LEFT, 1)
            sizer.Add(use,    (ir, 2), (1, 1), LEFT, 1)
            sizer.Add(kind,   (ir, 3), (1, 1), LEFT, 1)
            self.widlist.append(('new_det', None, desc, pvctrl, use, kind, False))

        ir += 1
        sizer.Add(self.add_subtitle(panel, 'Additional Counters'),
                  (ir, 0),  (1, 5),  LEFT, 1)

        ###
        ir += 1
        sizer.Add(SimpleText(panel, label='Label',  size=(125, -1)),
                  (ir, 0), (1, 1), LEFT, 1)
        sizer.Add(SimpleText(panel, label='PV name', size=(175, -1)),
                  (ir, 1), (1, 1), LEFT, 1)
        sizer.Add(SimpleText(panel, label='Use?', size=(80, -1)),
                  (ir, 2), (1, 1), LEFT, 1)
        sizer.Add(SimpleText(panel, label='Erase?', size=(80, -1)),
                  (ir, 3), (1, 2), LEFT, 1)

        for counter in self.counters:
            desc   = wx.TextCtrl(panel, -1, value=counter.name, size=(125, -1))
            pvctrl = wx.TextCtrl(panel, value=counter.pvname,  size=(175, -1))
            use     = YesNo(panel, defaultyes=(counter.use in ('True', 1, None)))
            erase  = YesNo(panel, defaultyes=False)
            ir +=1
            sizer.Add(desc,   (ir, 0), (1, 1), CEN, 1)
            sizer.Add(pvctrl, (ir, 1), (1, 1), LEFT, 1)
            sizer.Add(use,    (ir, 2), (1, 1), LEFT, 1)
            sizer.Add(erase,  (ir, 3), (1, 1), LEFT, 1)            
            self.widlist.append(('old_counter', counter, desc,
                                 pvctrl, use, None, erase))

        for i in range(2):
            desc   = wx.TextCtrl(panel, -1, value='', size=(125, -1))
            pvctrl = wx.TextCtrl(panel, value='', size=(175, -1))
            use     = YesNo(panel)
            ir +=1
            sizer.Add(desc,   (ir, 0), (1, 1), CEN, 1)
            sizer.Add(pvctrl, (ir, 1), (1, 1), LEFT, 1)
            sizer.Add(use,    (ir, 2), (1, 1), LEFT, 1)
            self.widlist.append(('new_counter', None, desc,
                                 pvctrl, use, None, False))
        ir += 1
        sizer.Add(wx.StaticLine(panel, size=(350, 3), style=wx.LI_HORIZONTAL),
                  (ir, 0), (1, 4), wx.ALIGN_LEFT|wx.EXPAND, 3)
        ###
        ir += 1
        sizer.Add(self.make_buttons(panel), (ir, 0), (1, 3), wx.ALIGN_LEFT, 1)

        pack(panel, sizer)
        panel.SetupScrolling()

        mainsizer = wx.BoxSizer(wx.VERTICAL)
        mainsizer.Add(panel, 1, wx.GROW|wx.ALL, 1)

        pack(self, mainsizer)
        self.Show()
        self.Raise()

    def onDetDetails(self, evt=None, det=None, **kws):
        dlg = DetectorDetailsDialog(self, det=det)
        dlg.Raise()
        if dlg.ShowModal() == wx.ID_OK:
            opts = {}
            for key, wid in dlg.wids.items():
                if isinstance(wid, wx.TextCtrl):
                    val = wid.GetValue()
                elif isinstance(wid, YesNo):
                    val =  {0:False, 1:True}[wid.GetSelection()]
                opts[key] = val
            det.options = json.dumps(opts)
            self.scandb.commit()
        dlg.Destroy()

    def opts_panel(self, parent, opts):
        pane = wx.Panel(parent)
        sizer  = wx.BoxSizer(wx.HORIZONTAL)
        kind = opts.get('kind', '').lower()
        wids = []
        if kind == 'scaler':
            sizer.Add(SimpleText(pane, '#Channels=', size=(100, -1)), 0,  LEFT, 0)
            nchan = FloatCtrl(pane, value=opts.get('nchan', 8),
                              size=(25, -1), precision=0, minval=0)
            sizer.Add(nchan, 0, LEFT, 0)
            sizer.Add(SimpleText(pane, 'Use Raw/Calc:', size=(120, -1)), 0,  LEFT, 0)
            val = {True:1, False:0}[opts.get('use_calc', True)]
            use_calc = YesNo(pane, choices=('Raw', 'Calc'))
            sizer.Add(use_calc, 0,  LEFT, 0)
            wids = [nchan, use_calc]
        elif kind.startswith('area'):
            sizer.Add(SimpleText(pane, 'Use File Plugin:', size=(120, -1)), 0,  LEFT, 0)
            plugin = wx.Choice(pane, choices=AD_File_plugins)
            plugin.SetStringSelection(opts.get('file_plugin', 'None'))
            sizer.Add(plugin, 0, LEFT, 0)
            wids = [plugin]
        elif kind == 'mca':
            sizer.Add(SimpleText(pane, '#ROIs=', size=(80, -1)), 0,  LEFT, 0)
            nrois = FloatCtrl(pane, value=opts.get('nrois', 32),
                              size=(25, -1), precision=0, minval=0)
            sizer.Add(nrois, 0, LEFT, 0)
            sizer.Add(SimpleText(pane, 'Use Sum/Net:', size=(120, -1)), 0,  LEFT, 0)
            val = {True:1, False:0}[opts.get('use_net', False)]
            use_net = YesNo(pane, choices=('Sum', 'Net'))
            sizer.Add(use_net, 0,  LEFT, 0)
            sizer.Add(SimpleText(pane, 'Save Full Spectra:', size=(120, -1)), 0,  LEFT, 0)
            val = {True:1, False:0}[opts.get('use_full', False)]
            use_full = YesNo(pane)
            sizer.Add(use_full, 0,  LEFT, 0)
            wids = [nrois, use_net, use_full]

        elif kind.startswith('multi'):
            sizer.Add(SimpleText(pane, '#MCAs=', size=(80, -1)), 0,  LEFT, 0)
            nchan = FloatCtrl(pane, value=opts.get('nmcas', 4),
                              size=(25, -1), precision=0, minval=0)
            sizer.Add(nchan, 0, LEFT, 0)
            sizer.Add(SimpleText(pane, '#ROIs=', size=(80, -1)), 0,  LEFT, 0)
            nrois = FloatCtrl(pane, value=opts.get('nrois', 32),
                              size=(25, -1), precision=0, minval=0)
            sizer.Add(nrois, 0, LEFT, 0)
            sizer.Add(SimpleText(pane, 'Use Sum/Net:', size=(120, -1)), 0,  LEFT, 0)
            val = {True:1, False:0}[opts.get('use_net', False)]
            use_net = YesNo(pane, choices=('Sum', 'Net'))
            sizer.Add(use_net, 0,  LEFT, 0)
            sizer.Add(SimpleText(pane, 'Save Full Spectra:', size=(120, -1)), 0,  LEFT, 0)
            val = {True:1, False:0}[opts.get('use_full', False)]
            use_full = YesNo(pane)
            sizer.Add(use_full, 0,  LEFT, 0)
            wids = [nchan, nrois, use_net, use_full]

        pack(pane, sizer)
        return pane, wids

    def add_subtitle(self, panel, text):
        p = wx.Panel(panel)
        s = wx.BoxSizer(wx.HORIZONTAL)
        s.Add(wx.StaticLine(p, size=(125, 3), style=wx.LI_HORIZONTAL), 0, LEFT, 5)
        s.Add(SimpleText(p, text,  colour='#333377', size=(175, -1)),  0, LEFT, 5)
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
        self.scandb.set_info('det_settle_time', float(self.settle_time.GetValue()))
        for w in self.widlist:
            wtype, obj, name, pvname, use, kind, erase = w
            if erase not in (None, False):
                erase = erase.GetSelection()
            else:
                erase = False


            use    = use.GetSelection()
            name   = name.GetValue().strip()
            pvname = pvname.GetValue().strip()
            if len(name) < 1 or len(pvname) < 1:
                continue
            if kind is not None:
                kind = kind.GetStringSelection()
            if erase and obj is not None:
                delete = self.scandb.del_detector
                if 'counter' in wtype:
                    delete = self.scan.del_counter
                delete(obj.name)
            elif obj is not None:
                obj.use    = use
                obj.name   = name
                obj.pvname = pvname
                if kind is not None:
                    obj.kind   = kind
            elif 'det' in wtype:
                opts = json.dumps(DET_DEFAULT_OPTS.get(kind, {}))
                self.scandb.add_detector(name, pvname, kind,
                                         options=opts, use=use)
            elif 'counter' in wtype:
                self.scandb.add_counter(name, pvname, use=use)

        self.scandb.commit()
        self.Destroy()
        
    def onClose(self, event=None):
        self.Destroy()

