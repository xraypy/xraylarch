from larch import parse_group_args
from inspect import getcallargs

def DefCallArgs(subgroupname, skipped_attrs):
    def wrap(fcn):
        def wrapper(*args, **kwargs):
            call_args=getcallargs(fcn, *args, **kwargs)
            result = fcn(*args, **kwargs)
            a1,a2,groupx= parse_group_args(call_args[skipped_attrs[0]],
                                           members=skipped_attrs,
                                           defaults=(call_args[skipped_attrs[1]],),
                                           group=call_args['group'],
                                           fcn_name='wrapper')

            skipped_attrs.extend(['group','_larch'])
            args = {k:v for (k,v) in call_args.iteritems() if not(
                k in skipped_attrs)}
            if not hasattr(groupx, subgroupname):
                setattr(groupx, subgroupname, larch.Group())
            subgroup=getattr(groupx, subgroupname)
            setattr(subgroup, 'call_args', filtered_dict)
            return result
        wrapper.__doc__ = fcn.__doc__
        wrapper.__name__ = fcn.__name__
        wrapper._larchfunc_ = fcn
        wrapper.__filename__ = fcn.__code__.co_filename
        wrapper.__dict__.update(fcn.__dict__)
        return wrapper
    return wrap
