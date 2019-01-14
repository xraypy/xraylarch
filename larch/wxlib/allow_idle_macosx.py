#-----------------------------------------------------------------------------
#  adopted from IPython.lib.external._nope.py from IPython
#     [ Copyright (C) 2013 Min RK
#       Distributed under the terms of the 2-clause BSD License.
#     ]
#-----------------------------------------------------------------------------

from contextlib import contextmanager

import ctypes
import ctypes.util

void_p = ctypes.c_void_p
uint64 = ctypes.c_uint64

objc = ctypes.cdll.LoadLibrary(ctypes.util.find_library('objc'))

objc.objc_getClass.restype = void_p
objc.sel_registerName.restype = void_p
objc.objc_msgSend.restype = void_p
objc.objc_msgSend.argtypes = [void_p, void_p]

msgSend = objc.objc_msgSend

def as_utf8(s):
    """ensure utf8 bytes"""
    if not isinstance(s, bytes):
        s = s.encode('utf8')
    return s

def SelName(name):
    """create a selector name (for methods)"""
    return objc.sel_registerName(as_utf8(name))

def GetClass(classname):
    """get an ObjC Class by name"""
    return objc.objc_getClass(as_utf8(classname))

# constants from Foundation

NSActivityIdleDisplaySleepDisabled             = (1 << 40)
NSActivityIdleSystemSleepDisabled              = (1 << 20)
NSActivitySuddenTerminationDisabled            = (1 << 14)
NSActivityAutomaticTerminationDisabled         = (1 << 15)
NSActivityUserInitiated                        = (0x00FFFFFF | NSActivityIdleSystemSleepDisabled)
NSActivityUserInitiatedAllowingIdleSystemSleep = (NSActivityUserInitiated & ~NSActivityIdleSystemSleepDisabled)
NSActivityBackground                           = 0x000000FF
NSActivityLatencyCritical                      = 0xFF00000000

_activity = None

def allow_idle():
    """disable App Nap by setting NSActivityUserInitiatedAllowingIdleSystemSleep"""
    global _activity

    reason = msgSend(GetClass('NSString'),
                     SelName("stringWithUTF8String:"),
                     as_utf8('reason'))
    info   = msgSend(GetClass('NSProcessInfo'),
                     SelName('processInfo'))
    options = uint64(NSActivityUserInitiatedAllowingIdleSystemSleep)
    _activity = msgSend(info,
                        SelName('beginActivityWithOptions:reason:'),
                        options, void_p(reason))
