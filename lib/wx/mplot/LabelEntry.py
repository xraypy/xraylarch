#!/usr/bin/python
#
# simple extension of TextCtrl.  Typical usage:
#  entry = LabelEntry(self, -1, value='22',
#                     color='black',
#                     labeltext='X',labelbgcolor='green',
#                     style=wx.ALIGN_LEFT|wx.ST_NO_AUTORESIZE)
#  row   = wx.BoxSizer(wx.HORIZONTAL)
#  row.Add(entry.label, 1,wx.ALIGN_LEFT|wx.EXPAND)
#  row.Add(entry,    1,wx.ALIGN_LEFT|wx.EXPAND)        


import wx
import sys

class LabelEntry(wx.TextCtrl):
    """
    Simple extension of TextCtrl
    """
    def __init__(self,parent,value,size=-1,
                 font=None, action=None,
                 bgcolor=None, color=None, style=None,
                 labeltext=None, labelsize=-1,
                 labelcolor=None, labelbgcolor=None):

        if style  == None: style=wx.ALIGN_LEFT|wx.ST_NO_AUTORESIZE|wx.TE_PROCESS_ENTER
        if action == None: action = self.GetValue
        self.action = action
        
        if labeltext is not None:
            self.label = wx.StaticText(parent, -1, labeltext,
                                       size = (labelsize,-1),
                                       style = style)
            if labelcolor:   self.label.SetForegroundColour(labelcolor)
            if labelbgcolor: self.label.SetBackgroundColour(labelbgcolor)
            if font != None: self.label.SetFont(font)

        try:
            value = str(value)
        except:
            value = ' '

        wx.TextCtrl.__init__(self, parent, -1, value,
                             size=(size,-1),style=style)

        self.Bind(wx.EVT_TEXT_ENTER, self.__act)
        self.Bind(wx.EVT_KILL_FOCUS, self.__act)
        if font != None: self.SetFont(font)
        if color:   self.SetForegroundColour(color)
        if bgcolor: self.SetBackgroundColour(bgcolor)
        
    def __act(self,event=None):
        self.action(event=event)
        val = self.GetValue()
        event.Skip()
        return val
    
    
