#!/usr/bin/python
#
# test the MotorPanel

import sys
import os

import wx
import numpy

import larch

from readlinetextctrl import ReadlineTextCtrl
from larchfilling import Filling

from larch.plugins import plotter, shellutils

PLUGINS = [plotter.registerPlugin, shellutils.registerPlugin]

INFO = """  Larch version %s    using python %s  and numpy %s
  Copyright M. Newville, T. Trainor (2010)"""

INFO = INFO % (larch.__version__,
               "%i.%i.%i" % (sys.version_info[:3]),
               numpy.__version__)

BANNER = """
==================================================
                                     Welcome to Larch
%s
==================================================

"""  % (INFO)


def makeColorPanel(parent, color):
    p = wx.Panel(parent, -1)
    p.SetBackgroundColour(color)
    return p

class LarchWxShell(object):
    ps1 = 'Larch>'
    ps2 = ' ... >'
    def __init__(self, wxparent=None,   writer=None,
                 prompt=None, output=None, input=None):
        self.larch  = larch.Interpreter()
        self.inptext  = larch.InputText(prompt=self.ps1, interactive=False)
        self.symtable = self.larch.symtable
        self.prompt = prompt
        self.output = output
        self.larch.writer = self
        self.symtable.AddPlugins(PLUGINS, parent=wxparent,
                                 larch=self.larch)
        self.SetPrompt()

    def SetPrompt(self, partial=False):
        if self.prompt is not None:
            if partial:
                self.prompt.SetLabel(self.ps2)
                self.prompt.SetForegroundColour('#E00075')                
            else:
                self.prompt.SetLabel(self.ps1)
                self.prompt.SetForegroundColour('#000075')

            self.prompt.Refresh()
            
    def write(self, text, color=None):
        if self.output is not None:
            prev_color = self.output.GetForegroundColour()
            if color is not None:
                self.output.SetForegroundColour(color)
            self.output.WriteText(text)
            self.output.SetForegroundColour(prev_color)            
            # self.output.SetInsertionPointEnd()

            self.output.ShowPosition(self.output.GetLastPosition()-100)
            print 'Write ', color,self.output.GetLastPosition(),   self.output.GetNumberOfLines(), self.output.GetSize()
            # print self.output.PositionToXY()
            
            

            
            
    def execute(self, text=None):
        if text is not None:
            if  text.startswith('help'):
                arg = text[4:]
                if arg.startswith('(') and arg.endswith(')'): arg = arg[1:-1]
                if arg.startswith("'") and arg.endswith("'"): arg = arg[1:-1]
                if arg.startswith('"') and arg.endswith('"'): arg = arg[1:-1]
                text  = "help(%s)"% (repr(arg))
                print 'Would Show help: ', text
            if text.startswith('!'):
                return os.system(text[1:])
            else:
                self.inptext.put(text,lineno=0)
                
        if not self.inptext.input_complete:
            self.SetPrompt(partial = True)
            return None

        ret = None
        self.SetPrompt(partial = False)

        while len(self.inptext) > 0:
            block, fname, lineno = self.inptext.get()
            ret = self.larch.eval(block,
                                  fname=fname, lineno=lineno)
            
            if hasattr(ret, '__call__') and not isinstance(ret,type):
                try:
                    if 1 == len(block.split()):
                        ret = ret()
                except:
                    pass
            if self.larch.error:
                err = self.larch.error.pop(0)
                fname, lineno = err.fname, err.lineno
                self.write("%s:\n%s\n" % err.get_error(), color='red')
                for err in self.larch.error:
                    if ((err.fname != fname or err.lineno != lineno)
                        and err.lineno > 0 and lineno > 0):
                        self.write("%s\n" % (err.get_error()[1]), color='red')
            elif ret is not None:
                try:
                    self.write("%s\n" % repr(ret))
                except:
                    pass

class LarchFrame(wx.Frame):
    def __init__(self,  parent=None, **kwds):
        self.BuildFrame(parent=parent, **kwds)
        self.larchshell = LarchWxShell(wxparent=self,
                                       prompt = self.prompt,
                                       output  = self.output)

        self.datapanel.SetRootObject(self.larchshell.symtable)


    def InputPanel(self, parent):
        panel = wx.Panel(parent, -1)
        pstyle = wx.ALIGN_CENTER|wx.ALIGN_RIGHT
        self.prompt = wx.StaticText(panel, -1, 'Larch>',
                                    size = (65,-1),
                                    style = pstyle)
        self.input = ReadlineTextCtrl(panel, -1,  '', size=(500,-1),
                                 historyfile=None, mode='emacs',
                                 style=wx.ALIGN_LEFT|wx.TE_PROCESS_ENTER)
        
        self.input.Bind(wx.EVT_TEXT_ENTER, self.onText)
        self.input.notebooks = self.nbook
        
        sizer = wx.BoxSizer(wx.HORIZONTAL)

        sizer.Add(self.prompt,  0, wx.BOTTOM|wx.CENTER)
        sizer.Add(self.input,   1, wx.ALIGN_LEFT|wx.ALIGN_CENTER|wx.EXPAND)
        panel.SetSizer(sizer)
        sizer.Fit(panel)
        return panel
        
    def BuildFrame(self, parent=None, **kwds):
        wx.Frame.__init__(self, parent, -1, size=(600,400),
                          style= wx.DEFAULT_FRAME_STYLE)
        self.SetTitle('WXLarch')
        self.SetFont(wx.Font(11, wx.SWISS, wx.NORMAL, wx.BOLD, False))
        sfont = wx.Font(10, wx.SWISS, wx.NORMAL, wx.BOLD, False)
        sbar = self.CreateStatusBar(2, wx.CAPTION|wx.THICK_FRAME)

        self.SetStatusWidths([-2,-1])
        self.SetStatusText("Larch initializing...", 0)

        self.Bind(wx.EVT_CLOSE,  self.onClose)
        self.BuildMenus()
        
        nbook = wx.Notebook(self, -1, style=wx.BK_DEFAULT)
        nbook.SetBackgroundColour('#E9E9EA')
        self.SetBackgroundColour('#E9EEE0')        
        
        self.output = wx.TextCtrl(nbook, -1,  BANNER,
                             style=wx.TE_MULTILINE|wx.TE_RICH|wx.TE_READONLY)

        self.output.CanCopy()
        self.output.SetInsertionPointEnd()
        self.output.SetFont(sfont)
        
        self.helppanel = wx.TextCtrl(nbook, -1,  ' ',
                                     style=wx.TE_MULTILINE|wx.TE_RICH|wx.TE_READONLY)

        self.datapanel = Filling(nbook,  rootLabel='_main')

        nbook.AddPage(self.output,      'Output', select=1)
        nbook.AddPage(self.datapanel,   'Data')
        nbook.AddPage(self.helppanel,   'Help')        

        self.nbook = nbook
        
        sizer = wx.BoxSizer(wx.VERTICAL)
        opts = dict(flag=wx.ALIGN_CENTER_VERTICAL|wx.ALL|wx.EXPAND,
                    border=2)

        sizer.Add(nbook,  1, **opts)
        sizer.Add(self.InputPanel(self),  0, **opts)
        
        self.SetSizer(sizer)
        self.Refresh()

        self.SetStatusText("Ready", 0)
    
    def BuildMenus(self):
        ID_ABOUT = wx.NewId()
        ID_CLOSE  = wx.NewId()
        ID_FREAD = wx.NewId()
        ID_FSAVE = wx.NewId()

        ID_PSETUP  = wx.NewId()
        ID_PREVIEW = wx.NewId()
        ID_PRINT = wx.NewId()

        fmenu = wx.Menu()
        fmenu.Append(ID_FREAD, "&Read", "Read Configuration File")
        fmenu.Append(ID_FSAVE, "&Save", "Save Configuration File")        
        fmenu.AppendSeparator()
        fmenu.Append(ID_PSETUP, 'Page Setup...', 'Printer Setup')
        fmenu.Append(ID_PREVIEW, 'Print Preview...', 'Print Preview')
        fmenu.Append(ID_PRINT, "&Print\tCtrl+P", "Print Plot")
        fmenu.AppendSeparator()
        fmenu.Append(ID_CLOSE, "E&xit", "Terminate the program")

        hmenu = wx.Menu()
        hmenu.Append(ID_ABOUT, "&About",
                     "More information about this program")
        menuBar = wx.MenuBar()
        menuBar.Append(fmenu, "&File");
        menuBar.Append(hmenu, "&Help");
        self.SetMenuBar(menuBar)

        self.Bind(wx.EVT_MENU,  self.onAbout, id=ID_ABOUT)
        self.Bind(wx.EVT_MENU,  self.onClose, id=ID_CLOSE)

    def onText(self, event=None):
        text =  event.GetString()
        self.larchshell.write(">%s\n" % text)
        self.input.Clear()
        if text.lower() in ('quit', 'exit'):
            self.onClose()
        else:
            self.input.AddToHistory(text)
            wx.CallAfter(self.larchshell.execute, text) 
        event.Skip()
        
    def onResize(self, event=None):
        size = event.GetSize()
        nsize = self.notebooks.GetSize()        
        self.notebooks.SetSize(size)        
        self.notebooks.Refresh()
        nsize = self.notebooks.GetSize()

        # self.notebooks.SetBestFittingSize()
        self.notebooks.Refresh()
        nsize = self.notebooks.GetSize()
        #         o = []
        #         for i in dir(self.notebooks):
        #             if 'ize' in i:
        #                 o.append(i)
        #         print " | ".join(o)

        for k in range(self.notebooks.GetPageCount()):
            p = self.notebooks.GetPage(k)
            try:
                p.SetSize(size)
            except:
                print 'cannot set size'
            p.Refresh()
            
#             print p.SetSize.__doc__
#             print k, size, p
# # 
            
        event.Skip()

    def onAbout(self, event=None):
        about_msg =  """wxLarch:
        %s""" % (INFO)
            
        dlg = wx.MessageDialog(self, about_msg,
                               "About wxLarch", wx.OK | wx.ICON_INFORMATION)
        dlg.ShowModal()
        dlg.Destroy()

    def onClose(self,event=None):
        dlg = wx.MessageDialog(None, 'Really Quit?', 'Question',
                               wx.YES_NO | wx.NO_DEFAULT | wx.ICON_QUESTION)
        ret = dlg.ShowModal()
        if ret == wx.ID_YES:
            self.input.SaveHistory()
            self.Destroy()
        else:
            try:
                event.Veto()
            except:
                pass

if __name__ == '__main__':
    app = wx.PySimpleApp()
    f = LarchFrame(None)
    f.Show()
    app.MainLoop()


