from larch import isgroup

def parse_group_args(arg0, members=None, group=None, defaults=None,
                     fcn_name=None, check_outputs=True):
    """parse arguments for functions supporting First Argument Group convention

    That is, if the first argument is a Larch Group and contains members
    named in 'members', this will return data extracted from that group.

    Arguments
    ----------
    arg0:         first argument for function call.
    members:      list/tuple of names of required members (in order)
    defaults:     tuple of default values for remaining required
                  arguments past the first (in order)
    group:        group sent to parent function, used for outputs
    fcn_name:     name of parent function, used for error messages
    check_output: True/False (default True) setting whether a Warning should
                  be raised in any of the outputs (except for the final group)
                  are None.  This effectively checks that all expected inputs
                  have been specified
    Returns
    -------
     tuple of output values in the order listed by members, followed by the
     output group (which could be None).

    Notes
    -----
    This implements the First Argument Group convention, used for many Larch functions.
    As an example, the function _xafs.find_e0 is defined like this:
       find_e0(energy, mu=None, group=None, ...)

    and uses this function as
       energy, mu, group = parse_group_arg(energy, members=('energy', 'mu'),
                                           defaults=(mu,), group=group,
                                           fcn_name='find_e0', check_output=True)

    This allows the caller to use
         find_e0(grp)
    as a shorthand for
         find_e0(grp.energy, grp.mu, group=grp)

    as long as the Group grp has member 'energy', and 'mu'.

    With 'check_output=True', the value for 'mu' is not actually allowed to be None.

    The defaults tuple should be passed so that correct values are assigned
    if the caller actually specifies arrays as for the full call signature.
    """
    if members is None:
        members = []
    if isgroup(arg0, *members):
        if group is None:
            group = arg0
        out = [getattr(arg0, attr) for attr in members]
    else:
        out = [arg0] + list(defaults)

    # test that all outputs are non-None
    if check_outputs:
        _errmsg = """%s: needs First Argument Group or valid arguments for
  %s"""
        if fcn_name is None: fcn_name ='unknown function'
        for i, nam in enumerate(members):
            if out[i] is None:
                raise Warning(_errmsg % (fcn_name, ', '.join(members)))

    out.append(group)
    return out

def registerLarchPlugin():
    return ('_builtin', {'parse_group_arg': parse_group_arg})

