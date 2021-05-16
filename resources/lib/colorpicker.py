#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
import sys
import math
import xbmc
import xbmcaddon
import xbmcgui
import xbmcvfs
from traceback import format_exc
from contextlib import contextmanager
from xml.dom.minidom import parse

from .utils import ADDON_ID, COLORFILES_PATH, SKINCOLORFILES_PATH, SKINCOLORFILE, SKINCOLOR_PATH, setlog, setlogexception

SUPPORTS_PIL = False
PYTHON3 = True if sys.version_info.major == 3 else False

@contextmanager
def busy_dialog():
    xbmc.executebuiltin('ActivateWindow(busydialognocancel)')
    try:
        yield
    finally:
        xbmc.executebuiltin('Dialog.Close(busydialognocancel)')
        
@staticmethod
def waitforskinshortcutswindow():
    while not xbmc.Monitor().abortRequested() and not xbmc.getCondVisibility('Window.IsActive(DialogSelect.xml) | \
            Window.IsActive(script-skin_helper_service-ColorPicker.xml) | Window.IsActive(DialogKeyboard.xml)'):
        xbmc.Monitor().waitForAbort(0.1)

# IMPORT PIL/PILLOW ###################################

try:
    # prefer Pillow
    from PIL import Image
    img = Image.new('RGB', (1, 1))
    del img
    SUPPORTS_PIL = True
except Exception as exc:
    setlogexception(__name__, exc)
    try:
        # fallback to traditional PIL
        import Image
        img = Image.new('RGB', (1, 1))
        del img
        SUPPORTS_PIL = True
    except Exception as exc:
        setlogexception(__name__, exc)


class ColorPicker(xbmcgui.WindowXMLDialog):
    colors_list = None
    skinstring = None
    win_property = None
    shortcut_property = None
    colors_path = None
    saved_color = None
    current_window = None
    header_label = None
    colors_file = None
    all_colors = {}
    all_palettes = []
    colors_def_list = {}
    active_palette = None
    default_color = None

    def __init__(self, *args, **kwargs):
        super(xbmcgui.WindowXMLDialog, self).__init__()
        self.addon = xbmcaddon.Addon(ADDON_ID)
        self.win = xbmcgui.Window(10000)
        self.action_exitkeys_id = [10, 13]
        self.buildcolorslist()
        self.loadcolorsskin()
        self.result = -1

        # check paths
        if xbmcvfs.exists(SKINCOLORFILE) and not xbmcvfs.exists(SKINCOLORFILES_PATH):
            xbmcvfs.mkdirs(SKINCOLORFILES_PATH)
        if not xbmcvfs.exists(COLORFILES_PATH):
            xbmcvfs.mkdirs(COLORFILES_PATH)

    def __del__(self):
        del self.win
        del self.addon

    def addcolortolist(self, colorname, colorstring):
        if not colorname:
            colorname = colorstring
        color_image_file = self.createcolorswatchimage(colorstring)
        listitem = xbmcgui.ListItem(label=colorname)
        listitem.setArt({'icon': color_image_file})
        listitem.setProperty('colorstring', colorstring)
        self.colors_list.addItem(listitem)

    def buildcolorslist(self):
        # prefer skin colors file
        if xbmcvfs.exists(SKINCOLORFILE):
            colors_file = SKINCOLORFILE
            self.colors_path = SKINCOLORFILES_PATH
        else:
            colors_file = os.path.join(self.addon.getAddonInfo('path'), 'resources', 'colors', 'colors.xml')
            self.colors_path = COLORFILES_PATH

        doc = parse(colors_file)
        palette_listing = doc.documentElement.getElementsByTagName('palette')
        if palette_listing:
            # we have multiple palettes specified
            for item in palette_listing:
                palette_name = item.attributes['name'].nodeValue
                self.all_colors[palette_name] = self.getcolorsfromxml(item)
                self.all_palettes.append(palette_name)
        else:
            # we do not have multiple palettes
            self.all_colors['all'] = self.getcolorsfromxml(doc.documentElement)
            self.all_palettes.append('all')

    def loadcolorspalette(self, palette_name=''):
        self.colors_list.reset()
        if not palette_name:
            # just grab the first palette if none specified
            palette_name = self.all_palettes[0]
        # set window prop with active palette
        if palette_name != 'all':
            self.current_window.setProperty('palettename', palette_name)
        if not self.all_colors.get(palette_name):
            setlog('No palette exists with name %s' % palette_name, xbmc.LOGERROR)
            return
        for item in self.all_colors[palette_name]:
            self.addcolortolist(item[0], item[1])
            
    def loadcolorsskin(self):
        colors_def_file = os.path.join(SKINCOLOR_PATH, 'defaults.xml')
        if xbmcvfs.exists(colors_def_file):
            xmldoc = parse(colors_def_file)
            items = xmldoc.documentElement.getElementsByTagName('color')
            if items: 
                for elem in items:
                    name = elem.attributes['name'].nodeValue.lower()
                    colorstring = elem.childNodes[0].nodeValue.lower()
                    if name not in self.colors_def_list:
                            self.colors_def_list[name] = colorstring
        current_theme_name = xbmc.getInfoLabel('Skin.CurrentColourTheme')
        setlog(current_theme_name)
        if current_theme_name != 'SKINDEFAULT':
            colors_def_file = os.path.join(SKINCOLOR_PATH, current_theme_name + '.xml')
            if xbmcvfs.exists(colors_def_file):
                xmldoc = parse(colors_def_file)
                items = xmldoc.documentElement.getElementsByTagName('color')
                if items:
                    for elem in items:
                        name = elem.attributes['name'].nodeValue.lower()
                        colorstring = elem.childNodes[0].nodeValue.lower()
                        self.colors_def_list[name] = colorstring
                        
        setlog(self.colors_def_list)

    def onInit(self):
        with busy_dialog():
            self.current_window = xbmcgui.Window(xbmcgui.getCurrentWindowDialogId())
            self.colors_list = self.getControl(3110)
            # set header_label
            try:
                self.getControl(2).setLabel(self.header_label)
            except Exception:
                pass

            # get current color that is stored in the skin setting
            curvalue = ''
            curvalue_name = ''
            if self.skinstring:
                curvalue = xbmc.getInfoLabel('Skin.String(%s)' % self.skinstring)
                if curvalue == '' and self.default_color:
                    curvalue = self.colors_def_list[self.default_color]
                curvalue_name = xbmc.getInfoLabel('Skin.String(%s.name)' % self.skinstring)
                if curvalue_name == '' and self.default_color:
                    curvalue_name = self.default_color                
            if self.win_property:
                curvalue = self.win.getProperty(self.win_property)
                curvalue_name = xbmc.getInfoLabel('%s.name' % self.win_property)
            if curvalue:
                self.current_window.setProperty('colorstring', curvalue)
                if curvalue != curvalue_name:
                    self.current_window.setProperty('colorname', curvalue_name)
                self.current_window.setProperty('current.colorstring', curvalue)
                if curvalue != curvalue_name:
                    self.current_window.setProperty('current.colorname', curvalue_name)

            # load colors in the list
            self.loadcolorspalette(self.active_palette)

            # focus the current color
            if self.current_window.getProperty('colorstring'):
                self.current_window.setFocusId(3020)
            else:
                # no color setup so we just focus the colorslist
                self.current_window.setFocusId(3110)
                self.colors_list.selectItem(0)
                self.current_window.setProperty('colorstring', self.colors_list.getSelectedItem().getProperty('colorstring'))
                self.current_window.setProperty('colorname', self.colors_list.getSelectedItem().getLabel())

            # set opacity slider
            if self.current_window.getProperty('colorstring'):
                self.setopacityslider()

    def onFocus(self, controlId):
        pass

    def onAction(self, action):
        if action.getId() in (9, 10, 92, 216, 247, 257, 275, 61467, 61448, ):
            # exit or back called from kodi
            self.savecolorsetting(restoreprevious=True)
            self.closedialog()

    def closedialog(self):
        self.close()

    def setopacityslider(self):
        colorstring = self.current_window.getProperty('colorstring')
        try:
            if colorstring != '' and colorstring is not None and colorstring.lower() != 'none':
                a, r, g, b = colorstring[:2], colorstring[2:4], colorstring[4:6], colorstring[6:]
                a, r, g, b = [int(n, 16) for n in (a, r, g, b)]
                a = 100.0 * a / 255
                self.getControl(3033).setPercent(float(a))
        except Exception:
            pass

    def savecolorsetting(self, restoreprevious=False):
        if restoreprevious:
            colorname = self.current_window.getProperty('current.colorname')
            colorstring = self.current_window.getProperty('current.colorstring')
        else:
            colorname = self.current_window.getProperty('colorname')
            colorstring = self.current_window.getProperty('colorstring')

        if not colorname:
            colorname = colorstring

        self.createcolorswatchimage(colorstring)

        if self.skinstring and (not colorstring or colorstring == 'None'):
            if self.default_color:
                namecolor = self.default_color
            else:
                namecolor = self.addon.getLocalizedString(32032)
            xbmc.executebuiltin('Skin.SetString(%s.name, %s)' % (self.skinstring, namecolor))
            
            xbmc.executebuiltin('Skin.SetString(%s, "")' % self.skinstring)
            
            xbmc.executebuiltin('Skin.Reset(%s.base)' % self.skinstring)

        elif self.skinstring and colorstring:
            if self.default_color:
                namecolor = self.default_color
            else:
                namecolor = colorname            
            xbmc.executebuiltin('Skin.SetString(%s.name, %s)' % (self.skinstring, namecolor))
            
            xbmc.executebuiltin('Skin.SetString(%s, %s)' % (self.skinstring, colorstring))

            colorbase = 'ff' + colorstring[2:]
            xbmc.executebuiltin('Skin.SetString(%s.base, %s)' % (self.skinstring, colorbase))

        elif self.win_property:
            self.win.setProperty(self.win_property, colorstring)
            self.win.setProperty(self.win_property + '.name', colorname)

    def onClick(self, controlID):
        if controlID == 3010:
            # change color palette
            ret = xbmcgui.Dialog().select(self.addon.getLocalizedString(32030), self.all_palettes)
            self.loadcolorspalette(self.all_palettes[ret]) 
        elif controlID == 3020:
            # manual input
            dialog = xbmcgui.Dialog()
            colorstring = dialog.input(self.addon.getLocalizedString(32029), self.current_window.getProperty('colorstring'), type=xbmcgui.INPUT_ALPHANUM)
            if colorstring == '':
                colorstring = self.current_window.getProperty('colorstring')
            else:
                self.current_window.setProperty('colorname', self.addon.getLocalizedString(32031))
                self.current_window.setProperty('colorstring', colorstring)
                self.setopacityslider()
                self.savecolorsetting()   
        elif controlID == 3033:
            # opacity slider
            try:                
                colorstring = self.current_window.getProperty('colorstring')
                opacity = self.getControl(3033).getPercent()
                num = opacity / 100.0 * 255
                e = num - math.floor(num)
                a = e < 0.5 and int(math.floor(num)) or int(math.ceil(num))
                colorstring = colorstring.strip()
                r, g, b = colorstring[2:4], colorstring[4:6], colorstring[6:]
                r, g, b = [int(n, 16) for n in (r, g, b)]
                color = (a, r, g, b)
                colorstringvalue = '%02x%02x%02x%02x' % color
                self.current_window.setProperty('colorstring', colorstringvalue)
                self.savecolorsetting()
            except Exception:
                pass
        if controlID == 3050:
            # save button clicked or none
            if self.skinstring or self.win_property:
                self.closedialog()
            elif self.shortcut_property:
                self.result = (self.current_window.getProperty('colorstring'),
                               self.current_window.getProperty('colorname'))
                self.closedialog() 
        elif controlID == 3060:
            # none button
            self.current_window.setProperty('colorstring', '')
            self.savecolorsetting()
        elif controlID == 3110:    
            # color clicked
            item = self.colors_list.getSelectedItem()
            colorstring = item.getProperty('colorstring')
            self.current_window.setProperty('colorstring', colorstring)
            self.current_window.setProperty('colorname', item.getLabel())
            self.setopacityslider()
            self.current_window.setFocusId(3050)
            self.current_window.setProperty('color_chosen', 'true')
            self.savecolorsetting()

    def createcolorswatchimage(self, colorstring):
        color_image_file = None
        if colorstring:
            paths = []
            paths.append(u'%s%s.png' % (COLORFILES_PATH, colorstring))
            if xbmcvfs.exists(SKINCOLORFILE):
                paths.append(u'%s%s.png' % (SKINCOLORFILES_PATH, colorstring))
            for color_image_file in paths:
                if not xbmcvfs.exists(color_image_file):
                    if SUPPORTS_PIL:
                        # create image with PIL
                        try:
                            colorstring = colorstring.strip()
                            if colorstring[0] == '#':
                                colorstring = colorstring[1:]
                            a, r, g, b = colorstring[:2], colorstring[2:4], colorstring[4:6], colorstring[6:]
                            a, r, g, b = [int(n, 16) for n in (a, r, g, b)]
                            color = (r, g, b, a)
                            img = Image.new('RGBA', (16, 16), color)
                            img.save(color_image_file)
                            del img
                        except Exception as exc:
                            setlogexception(__name__, exc)
                    else:
                        # create image with online service if no pil support
                        xbmcvfs.copy( 'https://dummyimage.com/16/%s/%s.png' % (colorstring[2:],colorstring[2:]), color_image_file )
                        setlog('Local PIL module not available, generating color swatch image with online service', xbmc.LOGWARNING)
        return color_image_file

    @staticmethod
    def getcolorsfromxml(xmlelement):
        items = []
        listing = xmlelement.getElementsByTagName('color')
        for color in listing:
            name = color.attributes['name'].nodeValue.lower()
            colorstring = color.childNodes[0].nodeValue.lower()
            items.append((name, colorstring))
        return items
