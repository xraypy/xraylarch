import larch

from larch_plugins.std import parse_group_args
from inspect import getcallargs


#@call_args(attr_name,rem_ars_list=None)
def DefCallArgs(attr_name,rem_atr_list):
    def decorator(fcn):
        def wrapper(*args, **kwargs):
            fnc_return=fcn(*args, **kwargs)
            call_args=getcallargs(fcn, *args, **kwargs)
            #print call_args.keys()

            a1,a2,groupx= parse_group_args(call_args[rem_atr_list[0]], 
                                     members=(rem_atr_list[0], rem_atr_list[1]),
                                     defaults=(call_args[rem_atr_list[1]],),
                                     group=call_args['group'],
                                     fcn_name='wrapper') 
            
            rem_atr_list.extend(['group','_larch'])
            filtered_dict = {k:v for (k,v) in call_args.iteritems() if not(
                                                             k in rem_atr_list)}    
            if not hasattr(groupx, attr_name):
                setattr(groupx, attr_name, larch.Group())
            subject=getattr(groupx, attr_name)    
            setattr(subject, 'call_args', filtered_dict)
            return fnc_return
        wrapper.__doc__ = fcn.__doc__
        wrapper.__name__ = fcn.__name__
        wrapper._larchfunc_ = fcn
        wrapper.__filename__ = fcn.__code__.co_filename
        wrapper.__dict__.update(fcn.__dict__)    
        return wrapper
    return decorator    
