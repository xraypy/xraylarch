#!/usr/bin/python
##
## MPlot PlotFrame: a wx.Frame for 2D line plotting, using matplotlib
##

import os
import time
import wx
import matplotlib

class Menu_IDs:
    def __init__(self):
        self.EXIT   = wx.NewId()        
        self.SAVE   = wx.NewId()
        self.CONFIG = wx.NewId()
        self.UNZOOM = wx.NewId()                
        self.HELP   = wx.NewId()
        self.ABOUT  = wx.NewId()
        self.PRINT  = wx.NewId()
        self.PSETUP = wx.NewId()
        self.PREVIEW= wx.NewId()
        self.CLIPB  = wx.NewId()
        self.SELECT_COLOR = wx.NewId()
        self.SELECT_SMOOTH= wx.NewId()
        
class BaseFrame(wx.Frame):
    """
    MatPlotlib 2D plot as a wx.Frame, using PlotPanel
    """
    help_msg =  """Quick help:

 Left-Click:   to display X,Y coordinates
 Left-Drag:    to zoom in on plot region
 Right-Click:  display popup menu with choices:
                Zoom out 1 level       
                Zoom all the way out
                --------------------
                Configure 
                Save Image

Also, these key bindings can be used
(For Mac OSX, replace 'Ctrl' with 'Apple'):

  Ctrl-S:     save plot image to file
  Ctrl-C:     copy plot image to clipboard
  Ctrl-K:     Configure Plot 
  Ctrl-Q:     quit

"""


    about_msg =  """MPlot  version 0.9 
Matt Newville <newville@cars.uchicago.edu>"""

    def __init__(self, parent=None, panel=None, size=(700,450),
                 exit_callback=None, **kwds):
        self.exit_callback = exit_callback
        self.parent = parent
        self.panel  = panel
        self.menuIDs = Menu_IDs()
        self.top_menus = {'File':None,'Help':None}
        self.Build_DefaultUserMenus()

    def write_message(self,s,panel=0):
        """write a message to the Status Bar"""
        self.SetStatusText(s, panel)

    def set_xylims(self,xylims,**kw):
        """overwrite data for trace t """
        if self.panel is not None: self.panel.set_xylims(xylims,**kw)

    def get_xylims(self):
        """overwrite data for trace t """
        if self.panel is not None:
            return self.panel.get_xylims()

    def clear(self):
        """clear plot """
        if self.panel is not None: self.panel.clear()

    def unzoom_all(self,event=None):
        """zoom out full data range """
        if self.panel is not None: self.panel.unzoom_all(event=event)

    def unzoom(self,event=None):
        """zoom out 1 level, or to full data range """
        if self.panel is not None: self.panel.unzoom(event=event)
        
    def set_title(self,s):
        "set plot title"
        if self.panel is not None: self.panel.set_title(s)
        
    def set_xlabel(self,s):
        "set plot xlabel"        
        if self.panel is not None: self.panel.set_xlabel(s)

    def set_ylabel(self,s):
        "set plot xlabel"
        if self.panel is not None: self.panel.set_ylabel(s)        

    def save_figure(self,event=None):
        """ save figure image to file"""
        if self.panel is not None: self.panel.save_figure(event=event)

    def configure(self,event=None):
        if self.panel is not None: self.panel.configure(event=event)

    ####
    ## create GUI 
    ####
    def BuildFrame(self, size=(700,450), **kwds):
        kwds['style'] = wx.DEFAULT_FRAME_STYLE
        kwds['size']  = size
        wx.Frame.__init__(self, self.parent, -1, self.title, **kwds)

        sbar = self.CreateStatusBar(2,wx.CAPTION|wx.THICK_FRAME)
        sfont = sbar.GetFont()
        sfont.SetWeight(wx.BOLD)
        sfont.SetPointSize(10)
        sbar.SetFont(sfont)

        self.SetStatusWidths([-3,-1])
        self.SetStatusText('',0)

        sizer = wx.BoxSizer(wx.VERTICAL)
        self.BuildMenu()
        if self.panel is not None:
            self.panel.BuildPanel()
            self.panel.messenger = self.write_message
            sizer.Add(self.panel, 1, wx.EXPAND)
            self.BindMenuToPanel()
            
        self.SetAutoLayout(True)
        self.SetSizer(sizer)
        self.Fit()
        
    def Build_DefaultUserMenus(self):
        mids = self.menuIDs
        m = wx.Menu()
        m.Append(mids.CONFIG, "Configure Plot\tCtrl+K",
                 "Configure Plot styles, colors, labels, etc")
        m.AppendSeparator()
        m.Append(mids.UNZOOM, "Zoom Out\tCtrl+Z",
                 "Zoom out to full data range")
        self.user_menus  = [('&Options',m)]

    def BuildMenu(self):
        mids = self.menuIDs
        m0 = wx.Menu()
        
        m0.Append(mids.SAVE, "&Save\tCtrl+S",   "Save PNG Image of Plot")
        m0.Append(mids.CLIPB, "&Copy\tCtrl+C",  "Copy Plot Image to Clipboard")
        m0.AppendSeparator()
        m0.Append(mids.PSETUP, 'Page Setup...', 'Printer Setup')
        m0.Append(mids.PREVIEW, 'Print Preview...', 'Print Preview')
        m0.Append(mids.PRINT, "&Print\tCtrl+P", "Print Plot")
        m0.AppendSeparator()
        m0.Append(mids.EXIT, "E&xit\tCtrl+Q", "Exit the 2D Plot Window")

        self.top_menus['File'] = m0

        mhelp = wx.Menu()
        mhelp.Append(mids.HELP, "Quick Reference",  "Quick Reference for MPlot")
        mhelp.Append(mids.ABOUT, "About", "About MPlot")
        self.top_menus['Help'] = mhelp
        
        mbar = wx.MenuBar()        

        mbar.Append(self.top_menus['File'], "File")
        for m in self.user_menus:
            title,menu = m
            mbar.Append(menu, title)
        mbar.Append(self.top_menus['Help'], "&Help")


        self.SetMenuBar(mbar)
        self.Bind(wx.EVT_MENU, self.onHelp,            id=mids.HELP)
        self.Bind(wx.EVT_MENU, self.onAbout,           id=mids.ABOUT)
        self.Bind(wx.EVT_MENU, self.onExit ,           id=mids.EXIT)
        self.Bind(wx.EVT_CLOSE,self.onExit)

    def BindMenuToPanel(self, panel=None):
        if panel is None: panel = self.panel
        if panel is not None:
            p = panel
            mids = self.menuIDs
            self.Bind(wx.EVT_MENU, panel.configure,    id=mids.CONFIG)
            self.Bind(wx.EVT_MENU, panel.unzoom_all,   id=mids.UNZOOM)

            self.Bind(wx.EVT_MENU, panel.save_figure,  id=mids.SAVE)
            self.Bind(wx.EVT_MENU, panel.Print,        id=mids.PRINT)        
            self.Bind(wx.EVT_MENU, panel.PrintSetup,   id=mids.PSETUP)
            self.Bind(wx.EVT_MENU, panel.PrintPreview, id=mids.PREVIEW)
            self.Bind(wx.EVT_MENU, panel.canvas.Copy_to_Clipboard,
                      id=mids.CLIPB)

    def onAbout(self, event=None):
        dlg = wx.MessageDialog(self, self.about_msg, "About MPlot",
                               wx.OK | wx.ICON_INFORMATION)
        dlg.ShowModal()
        dlg.Destroy()

    def onHelp(self, event=None):
        dlg = wx.MessageDialog(self, self.help_msg, "MPlot Quick Reference",
                               wx.OK | wx.ICON_INFORMATION)
        dlg.ShowModal()
        dlg.Destroy()

    def onExit(self, event=None):
        try:
            if callable(self.exit_callback):  self.exit_callback()
        except:
            pass
        try:
            if self.panel is not None: self.panel.win_config.Close(True)
            if self.panel is not None: self.panel.win_config.Destroy()            
        except:
            pass

        try:
            self.Destroy()
        except:
            pass
        
