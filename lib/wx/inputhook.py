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
    # return len(inp) > 0
    return bool(inp)

if sys.platform == 'win32':
    from msvcrt import kbhit as stdin_ready

POLLTIME = 10 # milliseconds
ON_INTERRUPT = None
WXLARCH_SYM = None


class EventLoopTimer(wx.Timer):

    def __init__(self, func):
        self.func = func
        wx.Timer.__init__(self)

    def Notify(self):
        try:
            self.func()
        except KeyboardInterrupt:
            print 'keyboard interrupt'

class EventLoopRunner(object):
    def __init__(self, larchsym=None):
        self.larchsym = larchsym

    def Run(self, time):
        self.evtloop = wx.EventLoop()
        self.timer = EventLoopTimer(self.check_stdin)
        self.timer.Start(time)
        self.evtloop.Run()

    def check_stdin(self, event=None):
        try:
            process = stdin_ready()
            if self.larchsym is not None:
                if self.larchsym.get_symbol('_builtin.force_wxupdate'):
                    process = True
            if process:
                self.timer.Stop()
                self.evtloop.Exit()
            if self.larchsym is not None:
                self.larchsym.set_symbol('_builtin.force_wxupdate', False)
        except KeyboardInterrupt:
            if hasattr(ON_INTERRUPT, '__call__'):
                ON_INTERRUPT()

def input_handler1():
    """Run the wx event loop, polling for stdin.

    This version runs the wx eventloop for an undetermined amount of time,
    during which it periodically checks to see if anything is ready on
    stdin.  If anything is ready on stdin, the event loop exits.

    The argument to elr.Run controls how often the event loop looks at stdin.
    This determines the responsiveness at the keyboard.  A setting of 1000
    enables a user to type at most 1 char per second.  I have found that a
    setting of 10 gives good keyboard response.  We can shorten it further,
    but eventually performance would suffer from calling select/kbhit too
    often.
    """
    try:
        app = wx.GetApp()
        if app is not None:
            assert wx.Thread_IsMain()
            elr = EventLoopRunner(larchsym=WXLARCH_SYM)
            # As this time is made shorter, keyboard response improves,
            # but idle CPU load goes up.
            # 10 ms seems like a good compromise.
            elr.Run(time=POLLTIME)
    except KeyboardInterrupt:
        pass
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
        if not wx.Thread_IsMain():
            raise Exception('wx thread is not the main thread')
        evtloop = wx.EventLoop()
        activator = wx.EventLoopActivator(evtloop)
        t0 = time.time()
        while not stdin_ready():
            while evtloop.Pending():
                evtloop.Dispatch()
            app.ProcessIdle()
            try:
                sleep(0.001*POLLTIME)
            except KeyboardInterrupt:
                # print 'INTERRUPT', ON_INTERRUPT, hasattr(ON_INTERRUPT, '__call__')
                if hasattr(ON_INTERRUPT, '__call__'):
                    ON_INTERRUPT()
        activator = None
        # del activator
    return 0

def input_handler3():
    """Run the wx event loop by processing pending events only.

    This approach seems to work, but its performance is not great as it
    relies on having PyOS_InputHook called regularly.
    """
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
        pass
    return 0

input_handler = input_handler1

input_hook = c_void_p.in_dll(pythonapi, 'PyOS_InputHook')
cback = CFUNCTYPE(c_int)(input_handler)
input_hook.value = cast(cback, c_void_p).value

