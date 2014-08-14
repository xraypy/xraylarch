#!/usr/bin/env python
"""
Enable wxPython to be used interacive by setting PyOS_InputHook.

Authors:  Robin Dunn, Brian Granger, Ondrej Certik

tweaked by M Newville, based on reading modified inputhookwx from IPython
"""

import sys
import time
from timeit import default_timer as clock
import signal

if not hasattr(sys, 'frozen'):
    try:
        import wxversion
        wxversion.ensureMinimal('2.8')
    except:
        pass

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

POLLTIME = 10 # milliseconds
ON_INTERRUPT = None
WXLARCH_SYM = None
UPDATE_GROUPNAME = '_sys.wx'
UPDATE_GROUP = None
UPDATE_VAR = 'force_wxupdate'
ID_TIMER = wx.NewId()

def update_requested():
    "check if update has been requested"
    global WXLARCH_SYM, UPDATE_VAR, UPDATE_GROUP, UPDATE_GROUPNAME
    if WXLARCH_SYM is not None:
        if UPDATE_GROUP is None:
            UPDATE_GROUP = WXLARCH_SYM.get_symbol(UPDATE_GROUPNAME)
        return getattr(UPDATE_GROUP, UPDATE_VAR, False)
    return False

def clear_update_request():
    "clear update request"
    global WXLARCH_SYM, UPDATE_VAR, UPDATE_GROUP, UPDATE_GROUPNAME
    if UPDATE_GROUP is not None:
        setattr(UPDATE_GROUP, UPDATE_VAR, False)

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

def inputhook_wx():
    """Run the wx event loop by processing pending events only.

    This is like inputhook_wx1, but it keeps processing pending events
    until stdin is ready.  After processing all pending events, a call to
    time.sleep is inserted.  This is needed, otherwise, CPU usage is at 100%.
    This sleep time should be tuned though for best performance.
    """
    # We need to protect against a user pressing Control-C when IPython is
    # idle and this is running. We trap KeyboardInterrupt and pass.
    try:
        app = wx.GetApp()
        if app is not None:
            assert wx.Thread_IsMain()

            if not callable(signal.getsignal(signal.SIGINT)):
                signal.signal(signal.SIGINT, signal.default_int_handler)
            evtloop = wx.EventLoop()
            ea = wx.EventLoopActivator(evtloop)
            t = clock()
            while not stdin_ready() and not update_requested():
                while evtloop.Pending():
                    t = clock()
                    evtloop.Dispatch()
                app.ProcessIdle()
                # We need to sleep at this point to keep the idle CPU load
                # low.  However, if sleep to long, GUI response is poor.
                used_time = clock() - t
                ptime = 0.001
                if used_time > 0.25: ptime = 0.05
                if used_time > 5.00: ptime = 0.50
                time.sleep(ptime)
            del ea
            clear_update_request()            
    except KeyboardInterrupt:
        if hasattr(ON_INTERRUPT, '__call__'):
            ON_INTERRUPT()
    return 0

def inputhook_darwin():
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
            if update_requested():
                ptime /= 10
            eloop.run(poll_time=ptime)
    except KeyboardInterrupt:
        if hasattr(ON_INTERRUPT, '__call__'):
            ON_INTERRUPT()
    return 0



if sys.platform == 'darwin':
    # On OSX, evtloop.Pending() always returns True, regardless of there being
    # any events pending. As such we can't use implementations 1 or 3 of the
    # inputhook as those depend on a pending/dispatch loop.
    inputhook_wx = inputhook_darwin

input_hook = c_void_p.in_dll(pythonapi, 'PyOS_InputHook')
cback = CFUNCTYPE(c_int)(inputhook_wx)
input_hook.value = cast(cback, c_void_p).value

def ping(timeout=0.001):
    "ping wx"
    try:
        t0 = time.time()
        app = wx.GetApp()
        if app is not None:
            assert wx.Thread_IsMain()
            # Make a temporary event loop and process system events until
            # there are no more waiting, then allow idle events (which
            # will also deal with pending or posted wx events.)
            evtloop = wx.EventLoop()
            ea = wx.EventLoopActivator(evtloop)
            # t0 = time.time()
            #while time.time()-t0 < timeout:
            #    evtloop.Dispatch()
            app.ProcessIdle()
            del ea
    except:
        pass

