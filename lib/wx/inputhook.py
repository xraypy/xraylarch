"""
Enable wxPython to be used interacive by setting PyOS_InputHook.

Authors:  Robin Dunn and Brian Granger

tweaked by M Newville, based on reading modified inputhookwx from IPython
"""

import sys
import wx
from time import sleep
from select import select
from ctypes import c_void_p, c_int, cast, CFUNCTYPE, pythonapi

def stdin_ready():
    inp, out, err = select([sys.stdin],[],[],0)
    return len(inp) > 0

if sys.platform == 'win32':
    from msvcrt import kbhit as stdin_ready

POLLTIME = 0.05
ON_INTERRUPT = None

def input_handler():
    """Run the wx event loop by processing pending events only.

    This is like inputhook_wx1, but it keeps processing pending events
    until stdin is ready.  After processing all pending events, a call to
    time.sleep is inserted.  This is needed, otherwise, CPU usage is at 100%.
    This sleep time should be tuned though for best performance.
    """
    app = wx.GetApp()
    global POLLTIME, ON_INTERRUPT
    if app is not None:
        if not wx.Thread_IsMain():
            raise Exception('wx thread is not the main thread')
        evtloop = wx.EventLoop()
        activator = wx.EventLoopActivator(evtloop)
        while not stdin_ready():
            while evtloop.Pending():
                evtloop.Dispatch()
            app.ProcessIdle()
            try:
                sleep(POLLTIME)
            except KeyboardInterrupt:
                if hasattr(ON_INTERRUPT, '__call__'):
                    ON_INTERRUPT()
        activator = None
        # del activator
    return 0

input_hook = c_void_p.in_dll(pythonapi, 'PyOS_InputHook')
cback = CFUNCTYPE(c_int)(input_handler)
input_hook.value = cast(cback, c_void_p).value
