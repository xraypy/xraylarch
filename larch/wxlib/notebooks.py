import wx

import wx.lib.agw.flatnotebook as flat_nb

FNB_STYLE = flat_nb.FNB_NO_X_BUTTON|flat_nb.FNB_NO_NAV_BUTTONS

def flatnotebook(parent, paneldict, panelkws={},
                 on_change=None, drag_tabs=True, selection=0):
    style = FNB_STYLE
    if not drag_tabs:
        style |= flat_nb.FNB_NODRAG

    nb = flat_nb.FlatNotebook(parent, agwStyle=style)
    nb.SetTabAreaColour(wx.Colour(250, 250, 250))
    nb.SetActiveTabColour(wx.Colour(254, 254, 195))
    nb.SetNonActiveTabTextColour(wx.Colour(10, 10, 128))
    nb.SetActiveTabTextColour(wx.Colour(128, 0, 0))
    nb.SetPadding(wx.Size(4, -1))
    nb.DeleteAllPages()
    nb.pagelist = []
    grandparent = parent.GetParent()
    if grandparent is None:
        grandparent = parent
    for name, creator in paneldict.items():
        _page = creator(parent=grandparent, **panelkws)
        nb.AddPage(_page," %s " % name, True)
        nb.pagelist.append(_page)

    if callable(on_change):
        nb.Bind(wx.EVT_NOTEBOOK_PAGE_CHANGED, on_change)

    nb.SetSelection(selection)
    return nb
