from math import log10

def getfloat_attr(obj, attr, length=11):
    """Format an attribute of an object for printing."""
    val = getattr(obj, attr, None)
    if val is None:
        return 'unknown'
    if isinstance(val, int):
        return f'{val}'
    if isinstance(val, float):
        return gformat(val, length=length).strip()
    return repr(val)


def gformat(val, length=11):
    """Format a number with '%g'-like format.

    Except that:
        a) the length of the output string will be of the requested length.
        b) positive numbers will have a leading blank.
        b) the precision will be as high as possible.
        c) trailing zeros will not be trimmed.

    The precision will typically be ``length-7``.

    Parameters
    ----------
    val : float
        Value to be formatted.
    length : int, optional
        Length of output string (default is 11).

    Returns
    -------
    str
        String of specified length.

    Notes
    ------
    Positive values will have leading blank.

    """


    if val is None or isinstance(val, bool):
        return f'{repr(val):>{length}s}'
    try:
        expon = int(log10(abs(val)))
    except (OverflowError, ValueError):
        expon = 0
    length = max(length, 7)
    form = 'e'
    prec = length - 7
    ab_expon = abs(expon)
    if ab_expon > 99:
        prec -= 1
    elif ((expon >= 0 and expon < (prec+4))
          or (expon <= -1 and -expon < (prec-2))
          or (expon <= -1 and prec < 5 and abs(expon)<3 )):
        form = 'f'
        prec += 4
        if expon > 0:
            prec -= expon

    def fmt(val, length, prec, form):
        if prec < 0: prec = 0
        out = f'{val:{length}.{prec}{form}}'
        if form == 'e' and 'e+0' in out or 'e-0' in out:
            out = f'{val:{length+1}.{prec+1}{form}}'.replace('e-0', 'e-').replace('e+0', 'e+')

        return out

    prec += 1
    out = '_'*(length+2)
    while len(out) > length:
        prec -= 1
        out = fmt(val, length, prec, form)
    if '_' in out:
        out = fmt(val, length, prec, form)
    while len(out) < length:
        prec += 1
        out = fmt(val, length, prec, form)
    return out

def test_gformat():
    for x in range(-10, 12):
        for a in [0.2124312134, 0.54364253, 0.812312, .96341312124, 1.028456789]:
            v = a*(10**(x))
            print(f" :{gformat(v, length=13):s}::{gformat(v, length=12):s}::{gformat(v, length=11):s}::{gformat(v, length=10):s}::{gformat(v, length=9):s}::{gformat(v, length=8):s}:")
