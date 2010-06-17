#!/usr/bin/python
##
## MPlot BasePanel: a Basic Panel for 2D line and image plotting
##

import sys
import time
import os
import wx
import matplotlib
from Printer import Printer

class BasePanel(wx.Panel):
    """
    wx.Panel component shared by PlotPanel and ImagePanel.

    provides:
         Basic support Zooming / Unzooming 
         support for Printing
         popup menu
         bindings for keyboard short-cuts
    """
    def __init__(self, parent, messenger=None,
                 show_config_popup=True, **kw):
        self.is_macosx = False
        if os.name == 'posix':
            if os.uname()[0] == 'Darwin': self.is_macosx = True

        self.messenger = messenger
        if messenger is None: self.messenger = self.__def_messenger

        self.cursor_mode='cursor'
        self.cursor_save='cursor'
        self._yfmt = '%.4f'
        self._xfmt = '%.4f'
        self.use_dates = False
        self.ylog_scale = False
        self.show_config_popup = show_config_popup
        self.launch_dir  = os.getcwd()

        self.mouse_uptime= time.time()

        self.zoom_lims = [None]
        self.old_zoomdc= (None,(0,0),(0,0))
        self.parent    = parent
        self.printer = Printer(self)

    def addCanvasEvents(self):
        # use matplotlib events
        self.canvas.mpl_connect("motion_notify_event",  self.__onMouseMotionEvent)
        self.canvas.mpl_connect("button_press_event",   self.__onMouseButtonEvent)
        self.canvas.mpl_connect("button_release_event", self.__onMouseButtonEvent)
        self.canvas.mpl_connect("key_press_event",      self.__onKeyEvent)

        # build pop-up menu for right-click display
        self.popup_unzoom_all = wx.NewId()        
        self.popup_unzoom_one = wx.NewId()
        self.popup_config     = wx.NewId()
        self.popup_save   = wx.NewId()        
        self.popup_menu = wx.Menu()
        self.popup_menu.Append(self.popup_unzoom_one, 'Zoom out 1 level')
        self.popup_menu.Append(self.popup_unzoom_all, 'Zoom all the way out')
        self.popup_menu.AppendSeparator()
        if self.show_config_popup:
            self.popup_menu.Append(self.popup_config,'Configure')

        self.popup_menu.Append(self.popup_save,  'Save Image')
        self.Bind(wx.EVT_MENU, self.unzoom,       id=self.popup_unzoom_one)
        self.Bind(wx.EVT_MENU, self.unzoom_all,   id=self.popup_unzoom_all)
        self.Bind(wx.EVT_MENU, self.save_figure,  id=self.popup_save)
        self.Bind(wx.EVT_MENU, self.configure,    id=self.popup_config)

    def clear(self):
        """ clear plot """
        self.axes.cla()
        self.conf.ntrace = 0
        self.conf.xlabel = ''
        self.conf.ylabel = ''
        self.conf.title  = ''

    def unzoom_all(self,event=None):
        """ zoom out full data range """
        self.zoom_lims = [None]
        self.unzoom(event)
        
    def unzoom(self,event=None,set_bounds=True):
        """ zoom out 1 level, or to full data range """
        lims = None
        if len(self.zoom_lims) > 1:
            self.zoom_lims.pop()
            lims = self.zoom_lims[-1]

        if lims is None: # auto scale
            self.zoom_lims = [None]
            xmin,xmax,ymin,ymax = self.data_range
            self.axes.set_xlim((xmin,xmax),emit=True)
            self.axes.set_ylim((ymin,ymax),emit=True)
            if set_bounds:
                self.axes.update_datalim(((xmin,ymin),(xmax,ymax)))
                self.axes.set_xbound(self.axes.xaxis.get_major_locator().view_limits(xmin,xmax))
                self.axes.set_ybound(self.axes.yaxis.get_major_locator().view_limits(ymin,ymax))            
        else:
            self.axes.set_xlim(lims[:2])
            self.axes.set_ylim(lims[2:])
        self.old_zoomdc = (None,(0,0),(0,0))
        txt = ''
        if len(self.zoom_lims)>1:
            txt = 'zoom level %i' % (len(self.zoom_lims))
        self.write_message(txt)
        self.canvas.draw()
        
    def get_xylims(self):
        x = self.axes.get_xlim()
        y = self.axes.get_ylim()
        return (x,y)

    def set_title(self,s):
        "set plot title"
        self.conf.title = s
        self.conf.relabel()
        
    def set_xlabel(self,s):
        "set plot xlabel"
        self.conf.xlabel = s
        self.conf.relabel()

    def set_ylabel(self,s):
        "set plot ylabel"
        self.conf.ylabel = s
        self.conf.relabel()

    def write_message(self,s,panel=0):
        """ write message to message handler (possibly going to GUI statusbar)"""
        self.messenger(s, panel=panel)

    def save_figure(self,event=None):
        """ save figure image to file"""
        file_choices = "PNG (*.png)|*.png" 
        ofile = self.conf.title.strip()
        if len(ofile)>64: ofile=ofile[:63].strip()
        if len(ofile)<1:  ofile = 'plot'
        
        for c in ' :";|/\\': # "
            ofile = ofile.replace(c,'_')

        ofile = ofile + '.png'
        
        dlg = wx.FileDialog(self, message='Save Plot Figure as...',
                            defaultDir = os.getcwd(),
                            defaultFile=ofile,
                            wildcard=file_choices,
                            style=wx.SAVE|wx.CHANGE_DIR)

        if dlg.ShowModal() == wx.ID_OK:
            path = dlg.GetPath()
            self.canvas.print_figure(path,dpi=300)
            if (path.find(self.launch_dir) ==  0):
                path = path[len(self.launch_dir)+1:]
            self.write_message('Saved plot to %s' % path)
            
    def set_bg(self,color= None):
        if color is None: color = '#F7F7E0'
        self.fig.set_facecolor(color)

    ####
    ## GUI events
    ####
    def reportLeftDown(self,event=None,**kw):
        if event == None: return                
        self.write_message("%f, %f" % (event.xdata,event.ydata), panel=1)
        
    def onLeftDown(self,event=None):
        """ left button down: report x,y coords, start zooming mode"""
        if event == None: return
        self.conf.zoom_x = event.x
        self.conf.zoom_y = event.y
        # print 'LD: ', event.x, event.y,event.xdata,event.ydata,event.inaxes
        if event.inaxes is not None:
            self.conf.zoom_init = (event.xdata, event.ydata)
            self.reportLeftDown(event=event)
        else:
            self.conf.zoom_init = self.axes.transData.inverted().transform((event.x, event.y))                
        self.cursor_mode = 'zoom'
        self.__drawZoombox(self.old_zoomdc)
        self.old_zoomdc = (None, (0,0),(0,0))                                  
        self.ForwardEvent(event=event.guiEvent)

    def zoom_OK(self,start,stop):
        return True
    
    def onLeftUp(self,event=None):
        """ left button up: zoom in on selected region?? """
        if event == None: return
        # print 'onLeftUp ', event
        dx = abs(self.conf.zoom_x - event.x)
        dy = abs(self.conf.zoom_y - event.y)
        t0 = time.time()
        if ((dx > 6) and (dy > 6) and (t0-self.mouse_uptime)>0.1 and
            self.cursor_mode == 'zoom'):
            self.mouse_uptime = t0
            if event.inaxes is not None:
                _end = (event.xdata,event.ydata)
            else: # allows zooming in to go slightly out of range....
                _end =  self.axes.transData.inverted().transform((event.x, event.y))
            try:
                _ini = self.conf.zoom_init
                _lim = (min(_ini[0],_end[0]),max(_ini[0],_end[0]),
                        min(_ini[1],_end[1]),max(_ini[1],_end[1]))

                if self.zoom_OK(_ini, _end):
                    self.set_xylims(_lim, autoscale=False)
                    self.zoom_lims.append(_lim)
                    txt = 'zoom level %i ' % (len(self.zoom_lims)-1)
                    self.write_message(txt,panel=1)
            except:
                self.write_message("Cannot Zoom")
        self.old_zoomdc = (None,(0,0),(0,0))
        self.cursor_mode = 'cursor'
        self.canvas.draw()
        self.ForwardEvent(event=event.guiEvent)

    def ForwardEvent(self, event=None):
        """finish wx event, forward it to other wx objects"""
        if event is not None:
            event.Skip()
            if os.name == 'posix' or  self.HasCapture():
                try:
                    self.ReleaseMouse()
                except:
                    pass
        # 

    def onRightDown(self,event=None):
        """ right button down: show pop-up"""
        if event is None: return      
        self.cursor_mode = 'cursor'
        # note that the matplotlib event location have to be converted
        if event.inaxes:
            pos = event.guiEvent.GetPosition()
            wx.CallAfter(self.PopupMenu,self.popup_menu,pos)
        self.ForwardEvent(event=event.guiEvent)
            
    def onRightUp(self,event=None):
        """ right button up: put back to cursor mode"""
        if event is None: return
        self.cursor_mode = 'cursor'
        self.ForwardEvent(event=event.guiEvent)

    ####
    ## private methods
    ####
    def __def_messenger(self,s,panel=0):
        """ default, generic messenger: write to stdout"""
        sys.stdout.write(s)

    def __date_format(self,x):
        """ formatter for date x-data. primitive, and probably needs
        improvement, following matplotlib's date methods.        
        """
        interval = self.axes.xaxis.get_view_interval()
        ticks = self.axes.xaxis.get_major_locator()()
        span = max(interval) - min(interval)
        fmt = "%m/%d"
        if span < 1800:     fmt = "%I%p \n%M:%S"
        elif span < 86400*5:  fmt = "%m/%d \n%H:%M"
        elif span < 86400*20: fmt = "%m/%d"
        # print 'date formatter  span: ', span, fmt
        s = time.strftime(fmt,time.localtime(x))
        return s
        
    def xformatter(self,x,pos):
        " x-axis formatter "
        if self.use_dates:
            return self.__date_format(x)
        else:
            return self.__format(x,type='x')
    
    def yformatter(self,y,pos):
        " y-axis formatter "        
        return self.__format(y,type='y')

    def __format(self, x, type='x'):
        """ home built tick formatter to use with FuncFormatter():
        x     value to be formatted
        type  'x' or 'y' to set which list of ticks to get

        also sets self._yfmt/self._xfmt for statusbar
        """
        fmt,v = '%1.5g','%1.5g'
        if type == 'y':
            ax = self.axes.yaxis
        else:
            ax = self.axes.xaxis
            
        try:
            dtick = 0.1 * ax.get_view_interval().span()
        except:
            dtick = 0.2
        try:
            ticks = ax.get_major_locator()()
            dtick = abs(ticks[1] - ticks[0])
        except:
            pass
        # print ' tick ' , type, dtick, ' -> ', 
        if   dtick > 99999:     fmt,v = ('%1.6e', '%1.7g')
        elif dtick > 0.99:      fmt,v = ('%1.0f', '%1.2f')
        elif dtick > 0.099:     fmt,v = ('%1.1f', '%1.3f')
        elif dtick > 0.0099:    fmt,v = ('%1.2f', '%1.4f')
        elif dtick > 0.00099:   fmt,v = ('%1.3f', '%1.5f')
        elif dtick > 0.000099:  fmt,v = ('%1.4f', '%1.6e')
        elif dtick > 0.0000099: fmt,v = ('%1.5f', '%1.6e')


        s =  fmt % x
        s.strip()
        s = s.replace('+', '')
        while s.find('e0')>0: s = s.replace('e0','e')
        while s.find('-0')>0: s = s.replace('-0','-')
        if type == 'y': self._yfmt = v
        if type == 'x': self._xfmt = v
        return s

    def __drawZoombox(self,dc):
        """ system-dependent hack to call wx.ClientDC.DrawRectangle
        with the right arguments"""
        if dc[0] is None: return
        xpos  = dc[1]
        xsize = dc[2]
        dc[0].DrawRectangle(xpos[0],xpos[1],xsize[0],xsize[1])
        return (None, (0,0),(0,0))

    def __onKeyEvent(self,event=None):
        """ handles key events on canvas
        """
        if event is None: return
        # print 'KeyEvent ', event
        key = event.guiEvent.GetKeyCode()
        if (key < wx.WXK_SPACE or  key > 255):  return
        mod  = event.guiEvent.ControlDown()
        ckey = chr(key)
        if self.is_macosx: mod = event.guiEvent.MetaDown()
        if (mod and ckey=='C'): self.canvas.Copy_to_Clipboard(event)
        if (mod and ckey=='S'): self.save_figure(event)
        if (mod and ckey=='K'): self.configure(event)
        if (mod and ckey=='Z'): self.unzoom_all(event)
        if (mod and ckey=='P'): self.canvas.printer.Print(event)

    def __onMouseButtonEvent(self,event=None):
        """ general mouse press/release events. Here, event is
        a MplEvent from matplotlib.  This routine just dispatches
        to the appropriate onLeftDown, onLeftUp, onRightDown, onRightUp....
        methods.
        """
        if event is None: return
        # print 'MouseButtonEvent ', event, event.button
        button = event.button or 1
        handlers = {(1,'button_press_event'):   self.onLeftDown,
                   (1,'button_release_event'): self.onLeftUp,
                   (3,'button_press_event'):   self.onRightDown,
                    }
        # (3,'button_release_event'): self.onRightUp}

        handle_event = handlers.get((button,event.name),None)
        if callable(handle_event): handle_event(event)
        

    def __onMouseMotionEvent(self, event=None):
        """Draw a cursor over the axes"""
        if event is None: return
        
        if self.cursor_mode == 'cursor':
            if event.inaxes is not None:
                self.conf.zoom_init = (event.xdata, event.ydata)
                self.reportMotion(event=event)
            return
        try:
            x, y  = event.x, event.y
        except:
            self.cursor_mode == 'cursor'
            return
        
        self.__drawZoombox(self.old_zoomdc)
        self.old_zoomdc = (None, (0,0),(0,0))            
        x0     = min(x, self.conf.zoom_x)
        ymax   = max(y, self.conf.zoom_y)
        width  = abs(x -self.conf.zoom_x)
        height = abs(y -self.conf.zoom_y)
        y0     = self.canvas.figure.bbox.height - ymax

        zdc = wx.ClientDC(self.canvas)
        zdc.SetBrush(self.conf.zoombrush)
        zdc.SetPen(self.conf.zoompen)
        zdc.SetLogicalFunction(wx.XOR)
        self.old_zoomdc = (zdc, (x0, y0), (width, height))
        self.__drawZoombox(self.old_zoomdc)

    def reportMotion(self,event=None):
        fmt = "X,Y= %s, %s" % (self._xfmt, self._yfmt)
        self.write_message(fmt % (event.xdata,event.ydata), panel=1)
        
        
    def Print(self,event=None,**kw):
        self.printer.Print(event=event,**kw)

    def PrintPreview(self,event=None,**kw):
        self.printer.Preview(event=event, **kw)        
        
    def PrintSetup(self,event=None,**kw):
        self.printer.Setup(event=event, **kw)        
        
