#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
import sys
import xbmcgui
import xbmc

from .utils import getCondVisibility, trydecode

class DialogSelect(xbmcgui.WindowXMLDialog):

    def __init__(self, *args, **kwargs):
        xbmcgui.WindowXMLDialog.__init__(self)
        self.listing = kwargs.get('listing')
        self.windowtitle = kwargs.get('windowtitle')
        self.multiselect = kwargs.get('multiselect')
        self.richlayout = kwargs.get('richlayout', False)
        self.getmorebutton = kwargs.get('getmorebutton', '')
        self.autofocus_id = kwargs.get('autofocusid', 0)
        self.autofocus_label = kwargs.get('autofocuslabel', '')
        self.totalitems = 0
        self.result = None

    def closedialog(self, cancelled=False):
        if cancelled:
            self.result = False
        elif self.multiselect:
            # for multiselect we return the entire listing
            items_list = []
            itemcount = self.totalitems - 1
            while itemcount != -1:
                items_list.append(self.list_control.getListItem(itemcount))
                itemcount -= 1
            self.result = items_list
        else:
            self.result = self.list_control.getSelectedItem()
        self.close()

    def onInit(self):

        # set correct list
        self.setlistcontrol()

        # set window header
        self.getControl(1).setLabel(self.windowtitle)

        self.list_control.addItems(self.listing)
        self.setFocus(self.list_control)
        self.totalitems = len(self.listing)
        self.autofocuslistitem()

    def autofocuslistitem(self):
        if self.autofocus_id:
            try:
                self.list_control.selectItem(self.autofocus_id)
            except Exception:
                self.list_control.selectItem(0)
        if self.autofocus_label:
            try:
                for count, item in enumerate(self.listing):
                    if trydecode(item.getLabel()) == self.autofocus_label:
                        self.list_control.selectItem(count)
            except Exception:
                self.list_control.selectItem(0)

    def onAction(self, action):
        if action.getId() in (9, 10, 92, 216, 247, 257, 275, 61467, 61448, ):
            self.closedialog(True)

        # an item in the list is clicked
        if (action.getId() == 7 or action.getId() == 100) and getCondVisibility(
                'Control.HasFocus(3) | Control.HasFocus(6)'):
            if self.multiselect:
                # select/deselect the item
                item = self.list_control.getSelectedItem()
                if item.isSelected():
                    item.select(selected=False)
                else:
                    item.select(selected=True)
            else:
                # no multiselect so just close the dialog (and return results)
                self.closedialog()

    def onClick(self, controlID):

        if controlID == 6 and self.multiselect:
            pass

        elif controlID == 5:
            # OK button
            if not self.getmorebutton:
                self.closedialog()
            else:
                # OK button
                if sys.version_info.major == 3:
                    from .resourceaddons import downloadresourceaddons
                else:
                    from resourceaddons import downloadresourceaddons
                downloadresourceaddons(self.getmorebutton)
                self.result = True
                self.close()
        # Other buttons (including cancel)
        else:
            self.closedialog(True)

    def setlistcontrol(self):

        # set list id 6 if available for rich dialog
        if self.richlayout:
            self.list_control = self.getControl(6)
            self.getControl(3).setVisible(False)
        else:
            self.list_control = self.getControl(3)
            self.getControl(6).setVisible(False)

        self.list_control.setEnabled(True)
        self.list_control.setVisible(True)

        # enable cancel button
        self.setcancelbutton()

        # show get more button
        if self.getmorebutton:
            self.getControl(5).setVisible(True)
            self.getControl(5).setLabel(xbmc.getLocalizedString(21452))
        elif not self.multiselect:
            self.getControl(5).setVisible(False)

    def setcancelbutton(self):
        try:
            self.getControl(7).setLabel(xbmc.getLocalizedString(222))
            self.getControl(7).setVisible(True)
            self.getControl(7).setEnabled(True)
        except Exception:
            pass
