#!/usr/bin/env python
"""
Enable wxPython to be used interacive by setting PyOS_InputHook.

Authors:  Robin Dunn and Brian Granger
tweaked by M Newville, based on reading modified inputhookwx from IPython
"""

import sys
import time
import wx
from time import sleep
from select import select
from ctypes import c_void_p, c_int, cast, CFUNCTYPE, pythonapi
import larch

def stdin_ready():
    inp, out, err = select([sys.stdin],[],[],0)
    return bool(inp)

if sys.platform == 'win32':
    from msvcrt import kbhit as stdin_ready

POLLTIME = 25 # milliseconds
ON_INTERRUPT = None
WXLARCH_SYM = None
UPDATE_VAR = '_builtin.force_wxupdate'
ID_TIMER = wx.NewId()

def update_requested():
    "check if update has been requested"
    global WXLARCH_SYM, UPDATE_VAR
    if WXLARCH_SYM is not None:
        return WXLARCH_SYM.get_symbol(UPDATE_VAR)
    return False

def clear_update_request():
    "clear update request"
    global WXLARCH_SYM, UPDATE_VAR
    if WXLARCH_SYM is not None:
        WXLARCH_SYM.set_symbol(UPDATE_VAR, False)

class EventLoopRunner(object):
    def __init__(self, parent):
        self.parent = parent

    def run(self, poll_time=None):
        global ID_TIMER
        if poll_time is None:
            poll_time = POLLTIME
        self.evtloop = wx.EventLoop()
        self.timer = wx.Timer(self.parent, ID_TIMER)
        wx.EVT_TIMER(self.parent, ID_TIMER, self.check_stdin)
        self.timer.Start(poll_time)
        self.evtloop.Run()

    def check_stdin(self, event=None):
        if stdin_ready() or update_requested():
            self.timer.Stop()
            self.evtloop.Exit()
            del self.timer, self.evtloop
            clear_update_request()

def input_handler1():
    """Run the wx event loop, polling for stdin.

    This version runs the wx eventloop for an undetermined amount of time,
    during which it periodically checks to see if anything is ready on
    stdin.  If anything is ready on stdin, the event loop exits.

    The argument to eloop.run controls how often the event loop looks at stdin.
    This determines the responsiveness at the keyboard.  A setting of 20ms
    gives decent keyboard response.  It can be shortened if we know the loop will
    exit (as from update_requested()), but CPU usage of the idle process goes up
    if we run this too frequently.
    """
    global POLLTIME, ON_INTERRUPT
    try:
        app = wx.GetApp()
        if app is not None:
            assert wx.Thread_IsMain()
            eloop = EventLoopRunner(parent=app)
            ptime = POLLTIME
            if update_requested(): ptime /= 5
            eloop.run(poll_time=ptime)
    except KeyboardInterrupt:
        if hasattr(ON_INTERRUPT, '__call__'):
            ON_INTERRUPT()
    return 0

def input_handler2():
    """Run the wx event loop by processing pending events only.

    This is like inputhook_wx1, but it keeps processing pending events
    until stdin is ready.  After processing all pending events, a call to
    time.sleep is inserted.  This is needed, otherwise, CPU usage is at 100%.
    This sleep time should be tuned though for best performance.
    """
    app = wx.GetApp()
    global POLLTIME, ON_INTERRUPT
    if app is not None:
        assert wx.Thread_IsMain()
        evtloop = wx.EventLoop()
        activator = wx.EventLoopActivator(evtloop)
        t0 = time.time()

        while update_requested() or not stdin_ready():
            while evtloop.Pending():
                evtloop.Dispatch()
            app.ProcessIdle()
            try:
                sleep(0.001*POLLTIME)
            except KeyboardInterrupt:
                # print 'INTERRUPT', ON_INTERRUPT, hasattr(ON_INTERRUPT, '__call__')
                if hasattr(ON_INTERRUPT, '__call__'):
                    ON_INTERRUPT()
            clear_update_request()

        activator = None
        # del activator
    return 0

def input_handler3():
    """Run the wx event loop by processing pending events only.

    This approach seems to work, but its performance is not great as it
    relies on having PyOS_InputHook called regularly.
    """
    global ON_INTERRUPT
    try:
        app = wx.GetApp()
        if app is not None:
            assert wx.Thread_IsMain()
            # Make a temporary event loop and process system events until
            # there are no more waiting, then allow idle events (which
            # will also deal with pending or posted wx events.)
            evtloop = wx.EventLoop()
            ea = wx.EventLoopActivator(evtloop)
            while evtloop.Pending():
                evtloop.Dispatch()
            app.ProcessIdle()
            del ea
    except KeyboardInterrupt:
        if hasattr(ON_INTERRUPT, '__call__'):
            ON_INTERRUPT()
    return 0

input_handler = input_handler1

input_hook = c_void_p.in_dll(pythonapi, 'PyOS_InputHook')
cback = CFUNCTYPE(c_int)(input_handler)
input_hook.value = cast(cback, c_void_p).value

