import os

HAS_PWD = True
try:
    import pwd
except ImportError:
    HAS_PWD = False

def unixpath(d):
    return d.replace('\\', '/')

def winpath(d):
    "ensure path uses windows delimiters"
    if d.startswith('//'): d = d[1:]
    d = d.replace('/','\\')
    return d

nativepath = unixpath
if os.name == 'nt':
    nativepath = winpath

def get_homedir():
    "determine home directory"

    homedir = None

    def check(method, s):
        "check that os.path.expanduser / expandvars gives a useful result"
        try:
            if method(s) not in (None, s):
                return method(s)
        except:
            pass
        return None

    # for Unixes, allow for sudo case
    susername = os.environ.get("SUDO_USER", None)
    if HAS_PWD and susername is not None and homedir is None:
        homedir = pwd.getpwnam(susername).pw_dir

    # try expanding '~' -- should work on most Unixes
    if homedir is None:
        homedir = check(os.path.expanduser, '~')

    # try the common environmental variables
    if homedir is  None:
        for var in ('$HOME', '$HOMEPATH', '$USERPROFILE', '$ALLUSERSPROFILE'):
            homedir = check(os.path.expandvars, var)
            if homedir is not None:
                break

    # For Windows, ask for parent of Roaming 'Application Data' directory
    if homedir is None and os.name == 'nt':
        try:
            from win32com.shell import shellcon, shell
            homedir = shell.SHGetFolderPath(0, shellcon.CSIDL_APPDATA, 0, 0)
        except ImportError:
            pass

    # finally, use current folder
    if homedir is None:
        homedir = os.path.abspath('.')
    return nativepath(homedir)
