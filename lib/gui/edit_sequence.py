#-----------------------------------------------------------------------------
# Name:        GridCombo.py
# Purpose:     Dynamic list updating with a wx.grid.GridCellChoiceEditor
#
# Author:      Thomas M Wetherbee
#
# Created:     2009/04/27
# RCS-ID:      $Id: GridCombo.py $
# Copyright:   (c) 2009
# Licence:     Distributed under the terms of the GNU General Public License
#-----------------------------------------------------------------------------
#!/usr/bin/env python


'''
Dynamic list updating with a wx.grid.GridCellChoiceEditor.

This example shows how to dynamically update the choices in a
GridCellChoiceEditor. This simple example creates a two column
grid where the top row in each column is a wx.grid.GridCellChoiceEditor.
The choices listed in the editor are created on the fly, and may change
with each selection. Text entered into the GridCellChoiceEditor cell
is appended as an additional choice.

In addition to appending new choices, this example also shows how to get
the selection index and client data from the choice.

Cell editor interactions are printed for every step.

This example is deliberately simple, lacking sizers and other useful but
confusing niceties.

Theory:

The GridCellChoiceEditor uses an underlying ComboBox to do the editing.
This underlying ComboBox is created when the cell editor is created. Normally
the ComboBox is completely hidden, but in this example we retrieve a reference
to the ComboBox and use it to load choices and retrieve index and client data.

The example starts with a GridCellChoiceEditor attached to the two top cells of
the grid. When the GridCellChoiceEditor is invoked for the first time, two
choice items are added to the choice list along with their associated user
data. The items are ('spam', 42) and ('eggs', 69), where spam is the text to
display and 42 is the associated client data. In this example 'spam' has an
index of 0 while eggs, being the second item of the list, has an index of 1.

Note that the index and user data are not required. The demonstrated method
works fine without either, but sometimes it is useful to know the index of a
selection, especially when the user is allowed to create choices. For example,
we might have the list ['spam', 'eggs', 'spam', 'spam'] where the three spam
items are different objects. In this case simply returning the item value
'spam' is ambiguous. We need to know the index, or perhaps some associated
client data.

In our example, when the user enters a new choice, the choice is appended to
the end of the choice list. A unique integer number is created for each new
choice, in succession, with the first number being 100. This number is used
for client data.

In this example we bind directly to the ComboBox events, rather than getting
the events through the frame. This is done to keep the grid from eating the
events. The difference in binding can be seen in the two binding methods:

    self.Bind(wx.EVT_BUTTON, self.OnButton, self.button)
    self.button.Bind(wx.EVT_BUTTON, self.OnButton)

The latter method binds directly to the widget, where the first method
receives the event up the chain through the parent.

Note that this example does not save the new choice list: it persists only
for the life of the program. In a real application, you will probably want
to save this list and reload it the next time the program runs.
'''

import wx
import wx.grid

##modules ={}

class Frame1(wx.Frame):
    def __init__(self, parent):
        wx.Frame.__init__(self, id=-1, name='', parent=None,
              pos=wx.Point(100, 100), size=wx.Size(480, 250),
              style=wx.DEFAULT_FRAME_STYLE, title='Spam & Eggs')
        self.SetClientSize(wx.Size(400, 250))

        self.scrolledWindow1 = wx.ScrolledWindow(id=-1,
              name='scrolledWindow1', parent=self, pos=wx.Point(0, 0),
              size=wx.Size(400, 250), style=wx.HSCROLL | wx.VSCROLL)

        self.grid1 = wx.grid.Grid(id=-1, name='grid1',
              parent=self.scrolledWindow1, pos=wx.Point(0, 0),
              size=wx.Size(400, 250), style=0)

        self.grid1.CreateGrid(4, 2)

        #Create the GridCellChoiceEditor with a blank list. Items will
        #be added later at runtime. "allowOthers" allows the user to
        #create new selection items on the fly.
        xchoices = [('a', 'an A'), ('b', 'b is the choice'), ('c', 'c this one')]
        tChoiceEditor = wx.grid.GridCellChoiceEditor([])
        self.grid1.list = xchoices
        #Assign the cell editors for the top row (row 0). Note that on a
        #larger grid you would loop through the cells or set a default.
        self.grid1.SetCellEditor(0, 0, tChoiceEditor)
        self.grid1.SetCellEditor(0, 1, tChoiceEditor)

        #Create a starter list to seed the choices. In this list the item
        #format is (item, ClientData), where item is the string to display
        #in the drop list, and ClientData is a behind-the-scenes piece of
        #data to associate with this item. A seed list is optional.
        #If this were a real application, you would probably load this list
        #from a file.
        # self.grid1.list = [('spam', 42), ('eggs', 69)]

        #Show the first item of the list in each ChoiceEditor cell. The
        #displayed text is optional. You could leave these cells blank, or
        #display 'Select...' or something of that nature.
        self.grid1.SetCellValue(0, 0, self.grid1.list[0][0])
        self.grid1.SetCellValue(0, 1, self.grid1.list[1][0])

        #The counter below will be used to automatically generate a new
        #piece of unique client data for each new item. This isn't very
        #useful, but it does let us demonstrate client data. Typically
        #you would use something meaningful for client data, such as a key
        #or id number.
        self.grid1.counter = 100

        #The following two objects store the client data and item index
        #from a choice selection. Client data and selection index are not
        #directly exposed to the grid object. We will get this information by
        #directly accessing the underlying ComboBox object created by the
        #GridCellChoiceEditor.
        self.grid1.data = None
        self.grid1.index = None


        self.grid1.Bind(wx.grid.EVT_GRID_CELL_CHANGE,
              self.OnGrid1GridCellChange)

        self.grid1.Bind(wx.grid.EVT_GRID_EDITOR_CREATED,
              self.OnGrid1GridEditorCreated)

        self.grid1.Bind(wx.grid.EVT_GRID_EDITOR_HIDDEN,
              self.OnGrid1GridEditorHidden)


    #This method fires when a grid cell changes. We are simply showing
    #what has changed and any associated index and client data. Typically
    #this method is where you would put your real code for processing grid
    #cell changes.
    def OnGrid1GridCellChange(self, event):
        Row = event.GetRow()
        Col = event.GetCol()

        #All cells have a value, regardless of the editor.
        print 'Changed cell: (%u, %u)' % (Row, Col)
        print 'value: %s' % self.grid1.GetCellValue(Row, Col)

        #Row 0 means a GridCellChoiceEditor, so we should have associated
        #an index and client data.
        if Row == 0:
            print 'index: %u' % self.grid1.index
            print 'data: %s' % self.grid1.data

        print ''            #blank line to make it pretty.
        event.Skip()


    #This method fires when the underlying GridCellChoiceEditor ComboBox
    #is done with a selection.
    def OnGrid1ComboBox(self, event):
        #Save the index and client data for later use.
        self.grid1.index = self.comboBox.GetSelection()
        self.grid1.data  = self.comboBox.GetClientData(self.grid1.index)

        print 'ComboBoxChanged: %s' % self.comboBox.GetValue()
        print 'ComboBox index: %u'  % self.grid1.index
        print 'ComboBox data: %s\n' % self.grid1.data
        event.Skip()


    #This method fires when any text editing is done inside the text portion
    #of the ComboBox. This method will fire once for each new character, so
    #the print statements will show the character by character changes.
    def OnGrid1ComboBoxText(self, event):
        #The index for text changes is always -1. This is how we can tell
        #that new text has been entered, as opposed to a simple selection
        #from the drop list. Note that the index will be set for each character,
        #but it will be -1 every time, so the final result of text changes is
        #always an index of -1. The value is whatever text that has been
        #entered. At this point there is no client data. We will have to add
        #that later, once all of the text has been entered.
        self.grid1.index = self.comboBox.GetSelection()

        print 'ComboBoxText: %s' % self.comboBox.GetValue()
        print 'ComboBox index: %u\n' % self.grid1.index
        event.Skip()


    #This method fires after editing is finished for any cell. At this point
    #we know that any added text is complete, if there is any.
    def OnGrid1GridEditorHidden(self, event):
        Row = event.GetRow()
        Col = event.GetCol()

        #If the following conditions are true, it means that new text has
        #been entered in a GridCellChoiceEditor cell, in which case we want
        #to append the new item to our selection list.
        if Row == 0 and self.grid1.index == -1:
            #Get the new text from the grid cell
            item = self.comboBox.GetValue()

            #The new item will be appended to the list, so its new index will
            #be the same as the current length of the list (origin zero).
            self.grid1.index = self.comboBox.GetCount()

            #Generate some unique client data. Remember this counter example
            #is silly, but it makes for a reasonable demonstration. Client
            #data is optional. If you can use it, this is where you attach
            #your real client data.
            self.grid1.data = self.grid1.counter

            #Append the new item to the selection list. Remember that this list
            #is used by all cells with the same editor, so updating the list
            #here updates it for every cell using this editor.
            self.comboBox.Append(item, self.grid1.data)

            #Update the silly client data counter
            self.grid1.counter = self.grid1.counter + 1

        print 'OnGrid1EditorHidden: (%u, %u)\n' % (Row, Col)

        event.Skip()

    #This method fires when a cell editor is created. It appears that this
    #happens only on the first edit using that editor.
    def OnGrid1GridEditorCreated(self, event):
        Row = event.GetRow()
        Col = event.GetCol()

        print 'OnGrid1EditorCreated: (%u, %u)\n' % (Row, Col)

        #In this example, all cells in row 0 are GridCellChoiceEditors,
        #so we need to setup the selection list and bindings. We can't
        #do this in advance, because the ComboBox control is created with
        #the editor.
        if Row == 0:
            #Get a reference to the underlying ComboBox control.
            self.comboBox = event.GetControl()

            #Bind the ComboBox events.
            self.comboBox.Bind(wx.EVT_COMBOBOX, self.OnGrid1ComboBox)
            self.comboBox.Bind(wx.EVT_TEXT, self.OnGrid1ComboBoxText)

            #Load the initial choice list.
            for (item, data) in self.grid1.list:
                self.comboBox.Append(item, data)

        event.Skip()


if __name__ == '__main__':
    app = wx.PySimpleApp()
    frame = Frame1(None)
    frame.Show(True)
    app.MainLoop()
