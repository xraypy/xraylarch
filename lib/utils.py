def strip_quotes(t):
    d3, s3, d1, s1 = '"""', "'''", '"', "'"
    if hasattr(t, 'startswith'):
        if ((t.startswith(d3) and t.endswith(d3)) or
            (t.startswith(s3) and t.endswith(s3))):
            t = t[3:-3]
        elif ((t.startswith(d1) and t.endswith(d1)) or
              (t.startswith(s1) and t.endswith(s1))):
            t = t[1:-1]
    return t

def normalize_pvname(name):
    """ make sure Epics PV name either ends with .VAL or .SOMETHING!"""
    if  '.' in name:
        return name
    return "%s.VAL" % name
