
from larch import isgroup

def firstarg_group(grp, members, defaults):
    """tests whether first argument to a function contains members"""
    if isgroup(grp, *members):
        
