import time
import sys
import json


def js2ascii(inp):
    """convert input unicode json text to pure ASCII/utf-8"""
    if isinstance(inp, dict):
        return dict([(js2ascii(k), js2ascii(v)) for k, v in inp.iteritems()])
    elif isinstance(inp, list):
        return [js2ascii(k) for k in inp]
    elif isinstance(inp, unicode):
        return inp.encode('utf-8')
    else:
        return inp
