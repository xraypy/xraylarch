#!/usr/bin/python
#
# MPlot GUI to Configure (2D) Plots
#
import wx
import wx.lib.colourselect  as csel

import matplotlib
from matplotlib import rcParams
from matplotlib.colors import colorConverter
from matplotlib.font_manager import fontManager, FontProperties

from larch.closure import Closure
from PlotConfig import PlotConfig
from colors import hexcolor
from LabelEntry import LabelEntry

def mpl_color(c, default = (242,243,244)):
    try:
        r = map(lambda x: int(x*255), colorConverter.to_rgb(c))
        return tuple(r)
    except:
        return default

def autopack(panel,sizer):
    panel.SetAutoLayout(True)
    panel.SetSizer(sizer)
    sizer.Fit(panel)

class PlotConfigFrame(wx.Frame):
    """ GUI Configure Frame"""
    def __init__(self, config):
        if config is None: config = PlotConfig()
        self.conf   = config
        self.axes   = self.conf.axes
        self.canvas = self.conf.canvas
        
        self.conf.relabel()
        self.DrawPanel()

    def DrawPanel(self):
        style = wx.DEFAULT_FRAME_STYLE|wx.TAB_TRAVERSAL 
        wx.Frame.__init__(self, None,-1, 'Configure MPlot', style=style)
        wx.Frame.SetBackgroundColour(self,"#F8F8F0")
        
        panel = wx.Panel(self, -1)
        panel.SetBackgroundColour( "#F8F8F0")

        Font = wx.Font(13,wx.SWISS,wx.NORMAL,wx.NORMAL,False)
        panel.SetFont(Font)

        topsizer  = wx.GridBagSizer(5,5)
        labstyle= wx.ALIGN_LEFT|wx.ALIGN_CENTER_VERTICAL
        ltitle = wx.StaticText(panel, -1, 'MPlot Configuration',
                              style=labstyle)
        ltitle.SetFont(Font)
        ltitle.SetForegroundColour("Blue")

        topsizer.Add(ltitle,(0,0),(1,5),  labstyle,2)

        self.titl = LabelEntry(panel, self.conf.title, size=400,labeltext='Title: ',
                               action = Closure(self.onText,argu='title'))

        self.ylab = LabelEntry(panel, self.conf.ylabel, size=400,labeltext='Y Label: ',
                               action = Closure(self.onText,argu='ylabel'))

        self.xlab = LabelEntry(panel, self.conf.xlabel, size=400,labeltext='X Label: ',
                               action = Closure(self.onText,argu='xlabel'))
        

        topsizer.Add(self.titl.label, (1,0), (1,1), labstyle,5)
        topsizer.Add(self.titl,       (1,1), (1,5), labstyle,5)
        topsizer.Add(self.ylab.label, (2,0), (1,1), labstyle,5)
        topsizer.Add(self.ylab,       (2,1), (1,5), labstyle,5)
        topsizer.Add(self.xlab.label, (3,0), (1,1), labstyle,5)
        topsizer.Add(self.xlab,       (3,1), (1,5), labstyle,5)

        tcol = wx.StaticText(panel, -1, 'Colors',style=wx.ALIGN_LEFT|wx.ALIGN_CENTER_VERTICAL)

        bstyle=wx.ALIGN_LEFT|wx.ALIGN_CENTER_VERTICAL|wx.ST_NO_AUTORESIZE
        
        col = mpl_color(self.axes.get_axis_bgcolor(),default=(255,255,252))
        bgcol = csel.ColourSelect(panel,  -1, "Background", col, size=wx.DefaultSize)
       
        col = mpl_color(self.axes.get_xgridlines()[0].get_color(),default=(240,240,240))
        gridcol = csel.ColourSelect(panel, -1, "Grid",col, size=wx.DefaultSize)
 
        bgcol.Bind(csel.EVT_COLOURSELECT,  Closure(self.onColor,argu='bg'))
        gridcol.Bind(csel.EVT_COLOURSELECT,Closure(self.onColor,argu='grid')) 

        btnstyle= wx.ALIGN_LEFT|wx.ALIGN_CENTER_VERTICAL|wx.ALL
        
        tl1 = wx.StaticText(panel, -1, '   Show:', size=(-1,-1),style=labstyle)
        show_grid  = wx.CheckBox(panel,-1, 'Grid', (-1,-1),(-1,-1))
        show_grid.Bind(wx.EVT_CHECKBOX,self.onShowGrid)
        show_grid.SetValue(self.conf.show_grid)

        show_leg = wx.CheckBox(panel,-1, ' Legend', (-1,-1),(-1,-1))
        show_leg.Bind(wx.EVT_CHECKBOX,Closure(self.onShowLegend,argu='legend'))
        show_leg.SetValue(self.conf.show_legend)        

        show_lfr = wx.CheckBox(panel,-1, ' Legend Frame', (-1,-1),(-1,-1))
        show_lfr.Bind(wx.EVT_CHECKBOX,Closure(self.onShowLegend,argu='frame'))
        show_lfr.SetValue(self.conf.show_legend_frame)        

        midsizer  = wx.GridBagSizer(5,5)

        midsizer.Add(tcol,      (0,0), (1,1), labstyle,2)
        midsizer.Add(gridcol,   (0,1), (1,1), btnstyle,2)
        midsizer.Add(bgcol,     (0,2), (1,1), btnstyle,2)
        midsizer.Add(tl1,       (0,3), (1,1), labstyle,2)
        midsizer.Add(show_grid, (0,4), (1,1), labstyle,2)
        midsizer.Add(show_leg,  (0,5), (1,2), labstyle,2)
        midsizer.Add(show_lfr,  (0,7), (1,2), labstyle,2)
        
        tl1 = wx.StaticText(panel, -1, 'Legend Location:', size=(-1,-1),style=labstyle)
        leg_loc = wx.Choice(panel, -1, choices=self.conf.legend_locs, size=(130,-1))
        leg_loc.Bind(wx.EVT_CHOICE,Closure(self.onShowLegend,argu='loc'))
        leg_loc.SetStringSelection(self.conf.legend_loc)

        leg_onax = wx.Choice(panel, -1, choices=self.conf.legend_onaxis_choices,
                             size=(120,-1))
        leg_onax.Bind(wx.EVT_CHOICE,Closure(self.onShowLegend,argu='onaxis'))
        leg_onax.SetStringSelection(self.conf.legend_onaxis)

        tl2 = wx.StaticText(panel, -1, 'Text Size:', size=(-1,-1),style=labstyle)
        txt_size = wx.SpinCtrl(panel, -1, "", (-1,-1),(55,30))
        txt_size.SetRange(5, 30)
        txt_size.SetValue(self.conf.labelfont.get_size())
        txt_size.Bind(wx.EVT_SPINCTRL,Closure(self.onText,argu='size'))

        midsizer.Add(tl1,       (1,0), (1,2), wx.ALIGN_LEFT|wx.ALIGN_CENTER_VERTICAL,2)
        midsizer.Add(leg_loc,   (1,2), (1,2), labstyle,2)
        midsizer.Add(leg_onax,  (1,4), (1,2), labstyle,2)
        midsizer.Add(tl2,       (1,6), (1,2), labstyle,2)
        midsizer.Add(txt_size,  (1,8), (1,1), labstyle,2)                

        # main row 2: list of traces
        botsizer = wx.GridBagSizer(5, 5)
        i = 0
        irow = 0

        for t in ('#','Label','Color','Line Style',
                  'Thickness','Symbol',' Size'):
            x = wx.StaticText(panel,-1,t)
            x.SetFont(Font)
            botsizer.Add(x,(irow,i),(1,1),wx.ALIGN_LEFT|wx.ALL, 5)
            i = i+1
            
        self.trace_labels = []
        # print 'GUI CONFIG ', len(self.axes.get_lines()), self.conf.ntraces
        for i in range(1 + self.conf.ntrace): # len(self.axes.get_lines())):
            irow += 1
            argu  = "trace %i" % i
            lin  = self.conf.traces[i]
            dlab = lin.label
            dcol = lin.color
            dthk = lin.linewidth
            dmsz = lin.markersize
            dsty = lin.style
            dsym = lin.marker

            # tid = wx.StaticText(panel,-1,"%i" % (i+1)); x.SetFont(Font)
            #             lab = wx.TextCtrl(panel, -1, dlab, size=(140,-1),
            #                               style=wx.TE_PROCESS_ENTER)
            #             lab.Bind(wx.EVT_TEXT_ENTER, Closure(self.onText,argu=argu))

            lab = LabelEntry(panel, dlab, size=140,labeltext="%i" % (i+1),
                               action = Closure(self.onText,argu=argu))
            self.trace_labels.append(lab)
               
            col = csel.ColourSelect(panel,  -1, "", dcol, size=wx.DefaultSize)
            col.Bind(csel.EVT_COLOURSELECT,Closure(self.onColor,argu=argu))
            
            thk = wx.SpinCtrl(panel, -1, "", (-1,-1),(55,30))
            thk.SetRange(0, 20)
            thk.SetValue(dthk)
            thk.Bind(wx.EVT_SPINCTRL, Closure(self.onThickness, argu=argu))

            sty = wx.Choice(panel, -1, choices=self.conf.styles, size=(100,-1))
            sty.Bind(wx.EVT_CHOICE,Closure(self.onStyle,argu=argu))
            sty.SetStringSelection(dsty)

            msz = wx.SpinCtrl(panel, -1, "", (-1,-1),(55,30))
            msz.SetRange(0, 30)
            msz.SetValue(dmsz)
            msz.Bind(wx.EVT_SPINCTRL, Closure(self.onMarkerSize, argu=argu))
           
            sym = wx.Choice(panel, -1, choices=self.conf.symbols, size=(120,-1))
            sym.Bind(wx.EVT_CHOICE,Closure(self.onSymbol,argu=argu))
            
            sym.SetStringSelection(dsym)
            
            botsizer.Add(lab.label,(irow,0),(1,1),wx.ALIGN_LEFT|wx.ALL, 5)
            botsizer.Add(lab,(irow,1),(1,1),wx.ALIGN_LEFT|wx.ALL, 5)            
            botsizer.Add(col,(irow,2),(1,1),wx.ALIGN_LEFT|wx.ALL, 5)
            botsizer.Add(sty,(irow,3),(1,1),wx.ALIGN_LEFT|wx.ALL, 5)
            botsizer.Add(thk,(irow,4),(1,1),wx.ALIGN_LEFT|wx.ALL, 5)
            botsizer.Add(sym,(irow,5),(1,1),wx.ALIGN_LEFT|wx.ALL, 5)
            botsizer.Add(msz,(irow,6),(1,1),wx.ALIGN_LEFT|wx.ALL, 5)


        bok = wx.Button(panel, -1, 'OK',    size=(-1,-1))
        bok.Bind(wx.EVT_BUTTON,self.onExit)

        
        btnsizer = wx.BoxSizer(wx.HORIZONTAL)
        btnsizer.Add(bok,0, wx.ALIGN_LEFT|wx.ALIGN_CENTER|wx.LEFT, 2)

        #bxk = wx.Button(panel, -1, 'QUIT',    size=(-1,-1))
        #bxk.Bind(wx.EVT_BUTTON,self.onExit)        
        #btnsizer.Add(bxk,0, wx.ALIGN_LEFT|wx.ALIGN_CENTER|wx.LEFT, 1)
        
        mainsizer = wx.BoxSizer(wx.VERTICAL)
        a = wx.ALIGN_LEFT|wx.LEFT|wx.TOP|wx.BOTTOM|wx.EXPAND
        mainsizer.Add(topsizer,0, a, 5)
        mainsizer.Add(midsizer,0, a, 5)        
        mainsizer.Add(botsizer,0, a, 5)
        mainsizer.Add(btnsizer,0, a, 5)
        autopack(panel,mainsizer)

        s = wx.BoxSizer(wx.VERTICAL)
        s.Add(panel,   0, a, 5)
        autopack(self,s)
        
        self.Show()
        self.Raise()

    def onColor(self,event,argu='grid'):
        color = hexcolor( event.GetValue() )
        if (argu[:6] == 'trace '):
            self.conf.set_trace_color(color,trace=int(argu[6:]))
            self.redraw_legend()            
        elif argu == 'grid':
            for i in self.axes.get_xgridlines()+self.axes.get_ygridlines():
                i.set_color(color)
        elif argu == 'bg':
            self.axes.set_axis_bgcolor(color)

        self.canvas.draw()

        
    def onStyle(self,event,argu='grid'):
        try:
            self.conf.set_trace_style(event.GetString(),trace=int(argu[6:]))
            self.redraw_legend()            
            self.canvas.draw()
        except:
            return

    def onSymbol(self,event,argu='grid'):
        try:
            self.conf.set_trace_marker(event.GetString(),trace=int(argu[6:]))
            self.redraw_legend()            
            self.canvas.draw()            
        except:
            return

    def onMarkerSize(self, event,argu=''):
        try:
            self.conf.set_trace_markersize(event.GetInt(),trace=int(argu[6:]))
            self.redraw_legend()            
            self.canvas.draw()
        except:
            return

    def onThickness(self, event,argu=''):
        try:
            self.conf.set_trace_linewidth(event.GetInt(),trace=int(argu[6:]))
            self.redraw_legend()
            self.canvas.draw()
        except:
            return

    def onText(self, event,argu=''):
        if argu=='size':
            self.conf.labelfont.set_size(event.GetInt())
            self.conf.titlefont.set_size(event.GetInt()+2)
            for lab in self.axes.get_xticklabels()+self.axes.get_yticklabels():
                lab.set_fontsize( event.GetInt()-1)
            self.canvas.draw()            
            return

        s = ''
        if (wx.EVT_TEXT_ENTER.evtType[0] == event.GetEventType()):
            s = str(event.GetString()).strip()        
        elif (wx.EVT_KILL_FOCUS.evtType[0] == event.GetEventType()):
            if argu == 'title':
                s = self.titl.GetValue()
            if argu == 'ylabel':
                s = self.ylab.GetValue()
            if argu == 'xlabel':
                s = self.xlab.GetValue()
            elif (argu[:6] == 'trace '):
                s = self.trace_labels[int(argu[6:])].GetValue()

        try:
            s = str(s).strip()
        except TypeError:
            s = ''
            
        t = s
        if '"' not in s:
            t = r"%s" % s
        elif "'" not in s:
            t = r'%s' % s
        else:
            t = r"""%s""" % s
        
        if (argu == 'xlabel'):
            self.conf.xlabel = t
        elif (argu == 'ylabel'):
            self.conf.ylabel = t
        elif (argu == 'title'):
            self.conf.title = t            
        elif (argu[:6] == 'trace '):
            try:
                self.conf.set_trace_label(t,trace=int(argu[6:]))
                self.redraw_legend()
            except:
                pass
        self.conf.relabel()
        self.canvas.draw()

    def onShowGrid(self,event):
        self.conf.show_grid = event.IsChecked()
        self.axes.grid(event.IsChecked())
        self.canvas.draw()

    def onShowLegend(self,event,argu=''):
        if (argu == 'legend'):
            self.conf.show_legend  = event.IsChecked()
        elif (argu=='frame'):
            self.conf.show_legend_frame = event.IsChecked()
        elif (argu=='loc'):
            self.conf.legend_loc  = event.GetString()            
        elif (argu=='onaxis'):
            self.conf.legend_onaxis  = event.GetString()            
        self.redraw_legend()

            
    def redraw_legend(self):
        """redraw the legend"""
        # first erase the current legend
        try:
            lgn = self.conf.mpl_legend
            if lgn:
                for i in lgn.get_texts(): i.set_text('')
                for i in lgn.get_lines():
                    i.set_linewidth(0)
                    i.set_markersize(0)
                    i.set_marker('None')
                lgn.draw_frame(False)
                lgn.set_visible(False)
        except:
            pass

        labs = []
        lins = self.axes.get_lines()
        for l in lins:
            xl = l.get_label()
            if not self.conf.show_legend: xl = ''
            labs.append(xl)
        labs = tuple(labs)

        if (self.conf.legend_onaxis == 'off plot'):
            lgn = self.conf.fig.legend
        else:
            lgn = self.conf.axes.legend

        if (self.conf.show_legend):
            self.conf.mpl_legend = lgn(lins, labs, loc=self.conf.legend_loc)
            self.conf.mpl_legend.draw_frame(self.conf.show_legend_frame)
        self.canvas.draw()

    def onExit(self, event):
        self.Close(True)
