#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
import sys
import xbmc
import xbmcvfs
import xbmcgui
import xbmcaddon
import urllib.parse
from xml.dom.minidom import parse
from operator import itemgetter

from .utils import ADDON_ID, setlog, setlogexception, kodijson, cleanstring, trydecode, getCondVisibility
from .skinsettings import SkinSettings
from .backuprestore import BackupRestore
from .resourceaddons import setresourceaddon
from .colorpicker import ColorPicker, waitforskinshortcutswindow
from .pvrfavourites import PVRFavourites
from .winproperties import WinProperties

class MainModule:

    def __init__(self):
        self.win = xbmcgui.Window(10000)
        self.addon = xbmcaddon.Addon(ADDON_ID)

        self.params = self.getparams()
        setlog('MainModule called with parameters: %s' % self.params)
        action = cleanstring(self.params.get('action', ''))

        try:
            getattr(self, action)()
        except AttributeError:
            setlogexception(__name__, 'No such action: %s' % action)
        except Exception as exc:
            setlogexception(__name__, exc)
        finally:
            xbmc.executebuiltin('dialog.Close(busydialog)')

        self.close()

    def close(self):
        del self.win
        del self.addon
        setlog('MainModule exit')

    @classmethod
    def getparams(self):
        params = {}
        for arg in sys.argv[1:]:
            paramname = arg.split('=')[0]
            paramvalue = arg.replace(paramname + '=', '')
            paramname = paramname.lower()
            if paramname == 'action':
                paramvalue = paramvalue.lower()
            params[paramname] = paramvalue
        return params

    # -- ACTION --
    
    def splashscreen(self):
        import time
        splashfile = cleanstring(self.params.get('file', ''))
        duration = int(self.params.get('duration', 5))
        if (splashfile.lower().endswith('jpg') or splashfile.lower().endswith('gif') or
                splashfile.lower().endswith('png') or splashfile.lower().endswith('tiff')):

            self.win.setProperty('SkinUtils.SplashScreen', splashfile)
            
            start_time = time.time()
            while (time.time() - start_time) <= duration:
                xbmc.sleep(500)
        else:

            xbmc.Player().play(splashfile, windowed=True)
            xbmc.sleep(500)
            while getCondVisibility('Player.HasMedia'):
                xbmc.sleep(150)

        startupwindow = xbmc.getInfoLabel('System.StartupWindow')
        xbmc.executebuiltin('ReplaceWindow(%s)' % startupwindow)
        autostart_playlist = xbmc.getInfoLabel('$ESCINFO[Skin.String(autostart_playlist)]')
        if autostart_playlist:
            xbmc.executebuiltin("PlayMedia(%s)" % autostart_playlist) 
            
    def dialogok(self):
        headertxt = cleanstring(self.params.get('header', ''))
        bodytxt = cleanstring(self.params.get('message', ''))
        dialog = xbmcgui.Dialog()
        dialog.ok(heading=headertxt, message=bodytxt)
        del dialog

    def dialogyesno(self):
        headertxt = cleanstring(self.params.get('header', ''))
        bodytxt = cleanstring(self.params.get('message', ''))
        yesactions = self.params.get('yesaction', '').split('|')
        noactions = self.params.get('noaction', '').split('|')
        if xbmcgui.Dialog().yesno(heading=headertxt, message=bodytxt):
            for action in yesactions:
                xbmc.executebuiltin(action)
        else:
            for action in noactions:
                xbmc.executebuiltin(action)

    def textviewer(self):
        headertxt = cleanstring(self.params.get('header', ''))
        bodytxt = cleanstring(self.params.get('message', ''))
        xbmcgui.Dialog().textviewer(headertxt, bodytxt)
        
    def setresourceaddon(self):
        addontype = cleanstring(self.params.get('addontype', ''))
        skinstring = cleanstring(self.params.get('skinstring', ''))
        header = cleanstring(self.params.get('header', xbmc.getLocalizedString(424)))        
        setresourceaddon(addontype=addontype, skinstring=skinstring, header=header)
                    
    def setskinsetting(self):
        setting = cleanstring(self.params.get('setting', ''))
        org_id = cleanstring(self.params.get('id', ''))
        if '$' in org_id:
            org_id = trydecode(xbmc.getInfoLabel(org_id))
        header = cleanstring(self.params.get('header', ''))
        SkinSettings().setskinsetting(setting=setting, window_header=header, original_id=org_id)
        
    def setbusytexture(self):
        skinsettings = SkinSettings()
        skinstring = cleanstring(self.params.get('skinstring', 'skinutils.spinnertexture'))
        current_value = cleanstring(self.params.get('currentvalue', ''))
        resource_addon = cleanstring(self.params.get('resourceaddon', 'resource.images.busyspinners'))
        allow_multi = self.params.get('allowmulti', 'true') == 'true'
        windowheader = cleanstring(self.params.get('header', self.addon.getLocalizedString(32017)))
        label, value = skinsettings.selectimage(
            skinstring, allow_multi=allow_multi, windowheader=windowheader, resource_addon=resource_addon, current_value=current_value)
        if label:
            if value.startswith('$INFO'):
                # we got an dynamic image from window property
                skinsettings.setskinvariable(skinstring, value)
                value = '$VAR[%s]' % skinstring
            xbmc.executebuiltin('Skin.SetString(%s.name,%s)' % (skinstring, label))
            xbmc.executebuiltin('Skin.SetString(%s.path,%s)' % (skinstring, value))
        del skinsettings
        
    def setbackground(self):
        skinsettings = SkinSettings()
        skinstring = cleanstring(self.params.get('skinstring', ''))
        allow_multi = self.params.get('allowmulti', 'true') == 'true'
        windowheader = cleanstring(self.params.get('header', xbmc.getLocalizedString(33069)))
        label, value = skinsettings.selectimage(
            skinstring, allow_multi=allow_multi, windowheader=windowheader, resource_addon='', current_value='')
        if label:
            xbmc.executebuiltin('Skin.SetString(%s,%s)' % (skinstring, value))
        del skinsettings

    def selectchannel(self):
        pvrfavourites = PVRFavourites()
        pvrfavourites.typepvr = cleanstring(self.params.get('typepvr','0'))
        pvrfavourites.skinstring = cleanstring(self.params.get('skinstring',''))
        pvrfavourites.select()
        setlog('selectchannel')
        del pvrfavourites
        
    def updatechannel(self):
        pvrfavourites = PVRFavourites()
        pvrfavourites.typepvr = cleanstring(self.params.get('typepvr','0'))
        pvrfavourites.skinstring = cleanstring(self.params.get('skinstring',''))
        pvrfavourites.channelid = cleanstring(self.params.get('channelid',''))
        pvrfavourites.update()
        setlog('updatechannel')
        del pvrfavourites
        
    def playchannel(self):
        pvrfavourites = PVRFavourites()
        pvrfavourites.typepvr = cleanstring(self.params.get('typepvr','0'))
        pvrfavourites.skinstring = cleanstring(self.params.get('skinstring',''))
        pvrfavourites.channelid = cleanstring(self.params.get('channelid',''))
        pvrfavourites.play()
        setlog('playchannel')
        del pvrfavourites
        
    def updateproperties(self):
        winproperties = WinProperties()
        winproperties.update()
        setlog('updateproperties')
        del winproperties
        
    def selectcolor(self):
        if self.params:
            colorpicker = ColorPicker('script-skin-utils-ColorPicker.xml', xbmcaddon.Addon(ADDON_ID).getAddonInfo('path'), 'Default', '1080i')
            colorpicker.skinstring = cleanstring(self.params.get('skinstring',''))
            colorpicker.win_property = cleanstring(self.params.get('winproperty',''))
            colorpicker.active_palette = cleanstring(self.params.get('palette',''))
            colorpicker.header_label = cleanstring(self.params.get('header',''))
            colorpicker.default_color = cleanstring(self.params.get('defcolor',''))
            propname = cleanstring(self.params.get('shortcutproperty',''))
            colorpicker.shortcut_property = propname
            colorpicker.doModal()
            #special action when we want to set our chosen color into a skinshortcuts property
            if propname and not isinstance(colorpicker.result, int):
                self.waitforskinshortcutswindow()
                xbmc.sleep(400)
                currentwindow = xbmcgui.Window(xbmcgui.getCurrentWindowDialogId())
                currentwindow.setProperty('customProperty', propname)
                currentwindow.setProperty('customValue',color_picker.result[0])
                xbmc.executebuiltin('SendClick(404)')
                xbmc.sleep(250)
                current_window.setProperty('customProperty', '%s.name' %propname)
                current_window.setProperty('customValue',color_picker.result[1])
                xbmc.executebuiltin('SendClick(404)')
            setlog('selectcolor')
            del colorpicker
        
    def reset(self):
        backuprestore = BackupRestore()
        filters = self.params.get('filter', [])
        if filters:
            filters = filters.split('|')
        silent = self.params.get('silent', '') == 'true'
        backuprestore.reset(filters, silent)
        setlog('reset')
        xbmc.Monitor().waitForAbort(2)
        
    def backup(self):
        backuprestore = BackupRestore()
        filters = self.params.get('filter', [])
        if filters:
            filters = filters.split('|')
        silent = self.params.get('silent', '')
        promptfilename = self.params.get('promptfilename', '') == 'true'
        if silent:
            silent_backup = True
            backup_file = silent
        else:
            silent_backup = False
            backup_file = backuprestore.getbackupfilename(promptfilename)
        backuprestore.backup(filters, backup_file, silent_backup)
        setlog('backup')
        del backuprestore
        
    def restore(self):
        backuprestore = BackupRestore()
        silent = self.params.get('silent', '')
        if silent and not xbmcvfs.exists(silent):
            setlog(
                'ERROR while restoring backup ! --> Filename invalid.'
                'Make sure you provide the FULL path, for example special://skin/extras/mybackup.zip',
                xbmc.LOGERROR)
            return
        backuprestore.restore(silent)
        setlog('restore')
    
    def checkskinsettings(self):
        SkinSettings().correctskinsettings()
        setlog('checkskinsettings')

