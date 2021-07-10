#!/usr/bin/env python
#
from __future__ import print_function
import sys

import wx
import os
import time

DEFAULT_HISTORYFILE = '.wxlarch_hist'
MAX_HISTORY = 5000

class ReadlineTextCtrl(wx.TextCtrl):
    def __init__(self, parent=None, value='', size=(400,-1),
                 historyfile=None,
                 style=wx.ALIGN_LEFT|wx.TE_PROCESS_ENTER, **kws):
        wx.TextCtrl.__init__(self, parent, -1, value=value,
                             size=size, style=style, **kws)

        self._val = value

        self.hist_file = historyfile
        self.hist_buff = []
        if self.hist_file is None:
            self.hist_file= os.path.join(os.environ.get('HOME','.'),
                                         DEFAULT_HISTORYFILE)
        # self.LoadHistory()
        self.hist_mark = len(self.hist_buff)
        self.hist_sessionstart = self.hist_mark

        if sys.platform == 'darwin':
            self.Bind(wx.EVT_KEY_UP,     self.onChar)
        else:
            self.Bind(wx.EVT_CHAR,       self.onChar)

        self.Bind(wx.EVT_SET_FOCUS,  self.onSetFocus)
        self.Bind(wx.EVT_KILL_FOCUS, self.onKillFocus)
        self.__GetMark()
        self.notebooks = None

    def __GetMark(self,  event=None):
        " keep track of cursor position within text"
        try:
            self.__mark = min(wx.TextCtrl.GetSelection(self)[0],
                              len(wx.TextCtrl.GetValue(self).strip()))
        except:
            self.__mark = 0

    def __SetMark(self, m=None):
        "set position of mark"
        if m is None:
            m = self.__mark
        self.SetSelection(m,m)

    def onKillFocus(self, event=None):
        self.__GetMark()
        # if event is not None:
        #    event.Skip()

    def onSetFocus(self, event=None):
        self.__SetMark()
        # if event is not None:
        #    event.Skip()

    def onChar(self, event):
        """ on Character event"""
        key   = event.GetKeyCode()
        entry = wx.TextCtrl.GetValue(self).strip()
        pos   = wx.TextCtrl.GetSelection(self)
        do_skip = True
        ctrl = event.ControlDown()
        # really, the order here is important:
        # 1. return sends to ValidateEntry
        if key == wx.WXK_RETURN and len(entry) > 0:
            pass
        # 2. other non-text characters are passed without change
        if key == wx.WXK_UP:
            self.hist_mark = max(0, self.hist_mark-1)
            try:
                self.SetValue(self.hist_buff[self.hist_mark])
            except:
                pass
            self.SetInsertionPointEnd()
            do_skip = False
        elif key == wx.WXK_DOWN:
            self.hist_mark += 1
            if self.hist_mark >= len(self.hist_buff):
                self.SetValue('')
            else:
                self.SetValue(self.hist_buff[self.hist_mark])
            self.SetInsertionPointEnd()
        elif key == wx.WXK_TAB:
            if self.notebooks is not None:
                self.notebooks.AdvanceSelection()
                self.SetFocus()

        elif key == wx.WXK_HOME or (ctrl and key == 1): # ctrl-a
            self.SetInsertionPoint(0)
            self.SetSelection(0,0)
            do_skip = False
        elif key == wx.WXK_END or (ctrl and key == 5):
            self.SetInsertionPointEnd()
        elif ctrl and  key == 2: # b
            mark = max(1, self.GetSelection()[1])
            self.SetSelection(mark-1, mark-1)
        elif ctrl and key== 3: # c
            cb_txt = wx.TextDataObject()
            wx.TheClipboard.Open()
            if wx.TheClipboard.IsOpened():
                cb_txt.SetData(str(entry))
                wx.TheClipboard.SetData(cb_txt)
                wx.TheClipboard.Close()
        elif ctrl and  key == 4: # d
            mark = self.GetSelection()[1]
            self.SetValue("%s%s" % (entry[:mark], entry[mark+1:]))
            self.SetSelection(mark, mark)
            do_skip = False
        elif ctrl and  key == 6: # f
            mark = self.GetSelection()[1]
            self.SetSelection(mark+1, mark+1)
        elif ctrl and  key == 8: # h
            mark = self.GetSelection()[1]
            self.SetValue("%s%s" % (entry[:mark-1], entry[mark:]))
            self.SetSelection(mark-1, mark-1)
        elif ctrl and  key == 11: # k
            mark = self.GetSelection()[1]
            self.SetValue("%s" % (entry[:mark]))
            self.SetSelection(mark, mark)
        elif ctrl and key == 22: # v
            cb_txt = wx.TextDataObject()
            wx.TheClipboard.Open()
            if wx.TheClipboard.IsOpened():
                wx.TheClipboard.GetData(cb_txt)
                wx.TheClipboard.Close()
                try:
                    self.SetValue(str(cb_txt.GetText()))
                except TypeError:
                    pass
                do_skip = False
        elif ctrl and key == 24: # x
            cb_txt = wx.TextDataObject()
            wx.TheClipboard.Open()
            if wx.TheClipboard.IsOpened():
                cb_txt.SetData(str(entry))
                wx.TheClipboard.GetData(cb_txt)
                wx.TheClipboard.Close()
                self.SetValue('')
        elif ctrl:
            pass
        self.Refresh()
        #if do_skip:
        #    event.Skip()
        return

    def AddToHistory(self, text=''):
        if len(text.strip()) > 0:
            self.hist_buff.append(text)
            self.hist_mark = len(self.hist_buff)

    def SaveHistory(self, filename=None, session_only=False):
        if filename is None:
            filename = self.hist_file
        try:
            fout = open(filename,'w')
        except IOError:
            print( 'Cannot save history ', filename)

        fout.write("# wxlarch history saved %s\n\n" % time.ctime())
        start_entry = -MAX_HISTORY
        if session_only:
            start_entry = self.hist_sessionstart
        fout.write('\n'.join(self.hist_buff[start_entry:]))
        fout.write("\n")
        fout.close()

    def LoadHistory(self):
        if os.path.exists(self.hist_file):
            self.hist_buff = []
            for txt in open(self.hist_file,'r').readlines():
                stxt = txt.strip()
                if len(stxt) > 0 and not stxt.startswith('#'):
                    self.hist_buff.append(txt[:-1])

    def def_onText(self, event=None):
        if event is None:
            return
        txt = event.GetString()
        if len(txt.strip()) > 0:
            self.hist_buff.append(txt)
            self.hist_mark = len(self.hist_buff)

        event.Skip()
