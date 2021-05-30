#!/usr/bin/env python
"""
Enable wxPython to be used interacive by setting PyOS_InputHook.

based on inputhook.py and inputhookwx.py from IPython,
which has several authors, including
   Robin Dunn, Brian Granger, Ondrej Certik

tweaked by M Newville for larch
"""

import sys
import time
import signal
from select import select
from ctypes import c_void_p, c_int, cast, CFUNCTYPE, pythonapi

import wx

POLLTIME = 10 # milliseconds
ON_INTERRUPT = None
WXLARCH_SYM = None
WXLARCH_INP = None
UPDATE_GROUPNAME = '_sys.wx'
UPDATE_GROUP = None
UPDATE_VAR = 'force_wxupdate'
IN_MODAL_DIALOG = False

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

clock = time.time
sleep = time.sleep

def onCtrlC(*args, **kws):
    global WXLARCH_SYM
    try:
        WXLARCH_SYM.set_symbol('_sys.wx.keyboard_interrupt', True)
    except AttributeError:
        pass
    raise KeyboardInterrupt
    return 0

def capture_CtrlC():
    signal.signal(signal.SIGINT, onCtrlC)

def ignore_CtrlC():
    signal.signal(signal.SIGINT, signal.SIG_IGN)

def allow_idle():
    # allow idle (needed for Mac OS X)
    pass

def stdin_ready():
    inp, out, err = select([sys.stdin],[],[],0)
    return bool(inp)

if sys.platform == 'win32':
    from msvcrt import kbhit as stdin_ready
    clock = time.monotonic
    def ignore_CtrlC():
        pass
elif sys.platform == 'darwin':
    from .allow_idle_macosx import allow_idle


class EnteredModalDialogHook(wx.ModalDialogHook):
    """
    set Global flag IN_MODAL_DIALOG when in a Modal Dialog.

    this will allow the event loop to *not* try to read stdina
    when a modal dialog is blocking, which causes problems on MacOS
    """
    def __init__(self):
        wx.ModalDialogHook.__init__(self)

    def Enter(self, dialog):
        global IN_MODAL_DIALOG
        IN_MODAL_DIALOG = True
        return wx.ID_NONE

    def Exit(self, dialog):
        global IN_MODAL_DIALOG
        IN_MODAL_DIALOG = False


class EventLoopRunner(object):
    def __init__(self, parent):
        self.parent = parent

    def run(self, poll_time=None):
        if poll_time is None:
            poll_time = POLLTIME
        self.t0 = clock()
        self.evtloop = wx.GUIEventLoop()
        self.timer = wx.Timer()
        self.parent.Bind(wx.EVT_TIMER, self.check_stdin)
        self.timer.Start(poll_time)
        self.evtloop.Run()

    def check_stdin(self, event=None):
        try:
            if (not IN_MODAL_DIALOG and (stdin_ready() or
                                        update_requested() or
                                        (clock() - self.t0) > 5)):
                self.timer.Stop()
                self.evtloop.Exit()
                del self.timer, self.evtloop
                clear_update_request()

        except KeyboardInterrupt:
            print('Captured Ctrl-C!')
        except:
            print(sys.exc_info())


def inputhook_wx():
    """Run the wx event loop by processing pending events only.

    This keeps processing pending events until stdin is ready.
    After processing all pending events, a call to time.sleep is inserted.
    This is needed, otherwise, CPU usage is at 100%.
    This sleep time should be tuned though for best performance.
    """
    # We need to protect against a user pressing Control-C when IPython is
    # idle and this is running. We trap KeyboardInterrupt and pass.
    try:
        app = wx.GetApp()
        if app is not None:
            assert wx.IsMainThread()

            if not callable(signal.getsignal(signal.SIGINT)):
                signal.signal(signal.SIGINT, signal.default_int_handler)
            evtloop = wx.GUIEventLoop()
            ea = wx.EventLoopActivator(evtloop)
            t = clock()
            while not stdin_ready() and not update_requested():
                while evtloop.Pending():
                    t = clock()
                    evtloop.Dispatch()

                if callable(getattr(app, 'ProcessIdle', None)):
                    app.ProcessIdle()
                if callable(getattr(evtloop, 'ProcessIdle', None)):
                    evtloop.ProcessIdle()

                # We need to sleep at this point to keep the idle CPU load
                # low.  However, if sleep to long, GUI response is poor.
                used_time = clock() - t
                ptime = 0.001
                if used_time >  0.10: ptime = 0.05
                if used_time >  3.00: ptime = 0.25
                if used_time > 30.00: ptime = 1.00
                sleep(ptime)
            del ea
            clear_update_request()
    except KeyboardInterrupt:
        if callable(ON_INTERRUPT):
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
            assert wx.IsMainThread()
            modal_hook = EnteredModalDialogHook()
            modal_hook.Register()
            eloop = EventLoopRunner(parent=app)
            ptime = POLLTIME
            if update_requested():
                ptime /= 10
            eloop.run(poll_time=ptime)
    except KeyboardInterrupt:
        print(" See KeyboardInterrupt from darwin hook")
        if callable(ON_INTERRUPT):
            ON_INTERRUPT()
    return 0

if sys.platform == 'darwin':
    # On OSX, evtloop.Pending() always returns True, regardless of there being
    # any events pending. As such we can't use implementations 1 or 3 of the
    # inputhook as those depend on a pending/dispatch loop.
    inputhook_wx = inputhook_darwin

try:
    capture_CtrlC()
except:
    pass
cback = CFUNCTYPE(c_int)(inputhook_wx)
py_inphook = c_void_p.in_dll(pythonapi, 'PyOS_InputHook')
py_inphook.value = cast(cback, c_void_p).value

# import for Darwin!
allow_idle()

def ping(timeout=0.001):
    "ping wx"
    try:
        t0 = clock()
        app = wx.GetApp()
        if app is not None:
            assert wx.IsMainThread()
            # Make a temporary event loop and process system events until
            # there are no more waiting, then allow idle events (which
            # will also deal with pending or posted wx events.)
            evtloop = wx_EventLoop()
            ea = wx.EventLoopActivator(evtloop)
            t0 = clock()
            while clock()-t0 < timeout:
                evtloop.Dispatch()
            app.ProcessIdle()
            del ea
    except:
        pass
