class Closure(object):
    """Give a reference to a function with arguments so that it 
    can be called later, optionally changing the argument list.  

    The class provids a simple callback function which is then
    executed when called as a function. It can be defined as:

       >>>def my_action(x=None):
       ...        print 'my action: x = ', x
       >>>c = Closure(my_action,x=1)
  
    and used as:
       >>>c()
       my action: x = 1
       >>>c(x=2)
        my action: x = 2

    The code is based on the Command class from
    J. Grayson's Tkinter book.
    """
    def __init__(self, func=None, **kwds):
        self.func = func
        self.kwds = kwds

    def __repr__(self):
        return "<function %s>" % (self.func.__name__)
    __str__ = __repr__

    def __doc__(self):
        return self.func.__doc__
    
    def __call__(self, *args, **c_kwds):
        if self.func is None:
            return None
        # avoid overwriting self.kwds here!!
        kwds = {}
        for key, val in list(self.kwds.items()):
            kwds[key] = val
        kwds.update(c_kwds)
        return self.func(*args, **kwds)
