#!/usr/bin/env python

import wx
import time
import os

MODNAME = '_sys.wx'

def SafeWxCall(fcn):
    """decorator to wrap function in a wx.CallAfter() so that
    calls can be made in a separate thread, and asynchronously.
    """
    def wrapper(*args, **kwargs):
        "callafter wrapper"
        try:
            wx.CallAfter(fcn, *args, **kwargs)
        except PyDeadObjectError:
            pass
    wrapper.__doc__ = fcn.__doc__
    wrapper.__name__ = fcn.__name__
    wrapper.__dict__.update(fcn.__dict__)
    return wrapper

def ensuremod(_larch, modname=None):
    if _larch is not None:
        symtable = _larch.symtable
        if modname is not None and not symtable.has_group(modname):
            symtable.newgroup(modname)
        return symtable

# @SafeWxCall
def _gcd(wxparent=None, _larch=None, **kws):
    """Directory Browser to Change Directory"""
    symtable = ensuremod(_larch, '_sys')
    symtable = ensuremod(_larch, '_sys.wx')
    if wxparent is None:
        wxparent = symtable.get_symbol('_sys.wx.wxapp').TopWindow

    dlg = wx.DirDialog(wxparent, message='Choose Directory',
                       style = wx.DD_DEFAULT_STYLE)
    path = None
    symtable.set_symbol('_sys.wx.force_wxupdate', True)
    if dlg.ShowModal() == wx.ID_OK:
        path = dlg.GetPath()

    dlg.Destroy()
    if path is not None:
        os.chdir(path)
    return os.getcwd()

def _wxupdate(_larch=None, **kws):
    """force an update of wxPython windows"""
    symtable = ensuremod(_larch, '_sys')
    symtable = ensuremod(_larch, '_sys.wx')
    input_handler = symtable.get_symbol('_sys.wx.inputhook').input_handler
    if input_handler is not None:
        symtable.set_symbol("_sys.wx.force_wxupdate", True)
        input_handler()

# @SafeWxCall
def _fileprompt(wxparent=None, _larch=None,
                mode='open', multi=True,
                message = None,
                fname=None, choices=None, **kws):
    """Bring up File Browser for opening or saving file.
    Returns name of selected file.

    options:
       mode:  one of 'open' or 'save'
       message: text to display in top window bar

    """
    symtable = ensuremod(_larch)
    if wxparent is None:
        wxparent = symtable.get_symbol('_sys.wx.parent')
    if fname is None:
        try:
            fname = symtable.get_symbol("%s.default_filename" % MODNAME)
        except:
            fname = ''
    if choices  is None:
        try:
            choices = symtable.get_symbol("%s.ext_choices" % MODNAME)
        except:
            choices = 'All Files (*.*)|*.*'

    if mode == 'open':
        style = wx.OPEN|wx.CHANGE_DIR
        if multi:
            style = style|wx.MULTIPLE
        if message is None:
            message = 'Open File '
    else:
        style = wx.SAVE|wx.CHANGE_DIR
        if message is None:
            message = 'Save As '
    # print 'FileDialog ', wxparent, message, fname , choices, style
    dlg = wx.FileDialog(parent=wxparent, message=message,
                        defaultDir = os.getcwd(),
                        defaultFile= fname,
                        wildcard = choices,
                        style=style)
    path = None
    if dlg.ShowModal() == wx.ID_OK:
        path = dlg.GetPath()
    dlg.Destroy()

    return path

def registerLarchPlugin():
    return (MODNAME, {'gcd': _gcd,
                      'fileprompt': _fileprompt,
                      'wx_update': _wxupdate})

