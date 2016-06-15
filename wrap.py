import inspect

def ValidateLarchPlugin(fcn):
    """function decorator to ensure that _larch is included in keywords,
    and that it is a valid Interpeter"""
    errmsg = "plugin function '%s' needs a valid '_larch' argument"

    def wrapper(*args, **keywords):
        "ValidateLarchPlugin"
        #if ('_larch' not in keywords or
        #    ('Interpreter' not in keywords['_larch'].__class__.__name__)):
        #    raise LarchPluginException(errmsg % fcn.__name__)
        return fcn(*args, **keywords)
    wrapper.__doc__ = fcn.__doc__
    wrapper.__args__ = fcn.__name__
    wrapper.__name__ = fcn.__name__
    wrapper._larchfunc_ = fcn
    wrapper.__filename__ = fcn.__code__.co_filename
    wrapper.__dict__.update(fcn.__dict__)
    return wrapper


@ValidateLarchPlugin
def f1(x, y, opt1=True, _larch=None):
    print 'Wrapped fcn ', x, y, opt1


def f2(x, y, opt1=True, _larch=None):
    print 'UnWrapped fcn ', x, y, opt1
