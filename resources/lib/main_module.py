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

from .utils import log_msg, KODI_VERSION, kodi_json, clean_string, getCondVisibility
from .utils import log_exception, get_current_content_type, ADDON_ID, recursive_delete_dir, try_decode
from .skinsettings import SkinSettings
from .backuprestore import BackupRestore
from .dialogselect import DialogSelect
from .colorpicker import ColorPicker

class MainModule:

    def __init__(self):
        self.win = xbmcgui.Window(10000)
        self.addon = xbmcaddon.Addon(ADDON_ID)

        self.params = self.get_params()
        log_msg('MainModule called with parameters: %s' % self.params)
        action = self.params.get('action', '')

        try:
            getattr(self, action)()
        except AttributeError:
            log_exception(__name__, "No such action: %s" % action)
        except Exception as exc:
            log_exception(__name__, exc)
        finally:
            xbmc.executebuiltin('dialog.Close(busydialog)')

        self.close()

    def close(self):
        del self.win
        del self.addon
        log_msg('MainModule exited')

    @classmethod
    def get_params(self):
        params = {}
        for arg in sys.argv[1:]:
            paramname = arg.split('=')[0]
            paramvalue = arg.replace(paramname + '=', '')
            paramname = paramname.lower()
            if paramname == 'action':
                paramvalue = paramvalue.lower()
            params[paramname] = paramvalue
        return params
        
    def selectimage(self):
        skinsettings = SkinSettings()
        skinstring = self.params.get('skinstring', '')
        skinshortcutsprop = self.params.get('skinshortcutsproperty', '')
        current_value = self.params.get('currentvalue', '')
        resource_addon = self.params.get('resourceaddon', '')
        allow_multi = self.params.get('allowmulti', 'false') == 'true'
        windowheader = self.params.get('header', '')
        label, value = skinsettings.select_image(
            skinstring, allow_multi=allow_multi, windowheader=windowheader, resource_addon=resource_addon, current_value=current_value)
        log_msg('selectimage 3') 
        if label:
            if skinshortcutsprop:
                # write value to skinshortcuts prop
                from .skinshortcuts import set_skinshortcuts_property
                set_skinshortcuts_property(skinshortcutsprop, value, label)
            else:
                # write the values to skin strings
                if value.startswith("$INFO"):
                    # we got an dynamic image from window property
                    skinsettings.set_skin_variable(skinstring, value)
                    value = '$VAR[%s]' % skinstring
                xbmc.executebuiltin('Skin.SetString(%s.label,%s)' % (skinstring, label))
                xbmc.executebuiltin('Skin.SetString(%s.name,%s)' % (skinstring, label))
                xbmc.executebuiltin('Skin.SetString(%s,%s)' % (skinstring, value))
                xbmc.executebuiltin('Skin.SetString(%s.path,%s)' % (skinstring, value))
        del skinsettings
        
    def getresourceaddondata(self, path):
        infoxml = os.path.join(path, 'info.xml')
        try:
            info = xbmcvfs.File(infoxml)
            data = info.read()
            info.close()
            xmldata = parseString(data)
            extension = xmldata.documentElement.getElementsByTagName('format')[0].childNodes[0].data
            subfolders = xmldata.documentElement.getElementsByTagName('subfolders')[0].childNodes[0].data
            return extension, subfolders
        except:
            return 'png', 'false'
        
    def getresourceaddon(self, addontype):
        listitems = []
        addons = kodi_json('Addons.GetAddons', {"type": "kodi.resource.images", "properties": ["name", "summary", "thumbnail", "path"]})
        for item in sorted(addons, key=itemgetter('name')):
            if item['addonid'].startswith(addontype):
                name = item['name']
                icon = item['thumbnail']
                addonid = item['addonid']
                path = item['path']
                summary = item['summary']
                extension, subfolders = self.getresourceaddondata(path)
                listitem = xbmcgui.ListItem(label=name, label2=addonid)
                listitem.setArt({'icon':'DefaultAddonImages.png', 'thumb':icon})
                listitem.setProperty('extension', extension)
                listitem.setProperty('subfolders', subfolders)
                listitem.setProperty('Addon.Summary', summary)
                listitems.append(listitem)
        return listitems

    @staticmethod
    def wait_for_skinshortcuts_window():
        while not xbmc.Monitor().abortRequested() and not xbmc.getCondVisibility('Window.IsActive(DialogSelect.xml) | \
                Window.IsActive(script-skin_helper_service-ColorPicker.xml) | Window.IsActive(DialogKeyboard.xml)'):
            xbmc.Monitor().waitForAbort(0.1)

    # -- ACTION --
    
    def splashscreen(self):
        import time
        splashfile = self.params.get('file', '')
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
        headertxt = clean_string(self.params.get('header', ''))
        bodytxt = clean_string(self.params.get('message', ''))
        dialog = xbmcgui.Dialog()
        dialog.ok(heading=headertxt, message=bodytxt)
        del dialog

    def dialogyesno(self):
        headertxt = clean_string(self.params.get('header', ''))
        bodytxt = clean_string(self.params.get('message', ''))
        yesactions = self.params.get('yesaction', '').split('|')
        noactions = self.params.get('noaction', '').split('|')
        if xbmcgui.Dialog().yesno(heading=headertxt, message=bodytxt):
            for action in yesactions:
                xbmc.executebuiltin(action)
        else:
            for action in noactions:
                xbmc.executebuiltin(action)

    def textviewer(self):
        headertxt = clean_string(self.params.get('header', ''))
        bodytxt = clean_string(self.params.get('message', ''))
        xbmcgui.Dialog().textviewer(headertxt, bodytxt)
        
    def setresourceaddon(self):
        addontype = self.params.get('addontype', '')
        skinstring = self.params.get('skinstring', '')
        header = self.params.get('header', xbmc.getLocalizedString(424))
        addonlist = self.getresourceaddon(addontype)
        listitem = xbmcgui.ListItem(xbmc.getLocalizedString(15109))
        listitem.setArt({'icon':'DefaultAddon.png'})
        addonlist.insert(0, listitem)
        listitem = xbmcgui.ListItem(xbmc.getLocalizedString(21452))
        listitem.setProperty('more', 'true')
        addonlist.append(listitem)
        num = xbmcgui.Dialog().select(header, addonlist, useDetails=True)
        if num == 0:
            xbmc.executebuiltin('Skin.Reset(%s)' % (skinstring + '.name'))
            xbmc.executebuiltin('Skin.Reset(%s)' % (skinstring + '.path'))
            xbmc.executebuiltin('Skin.Reset(%s)' % (skinstring + '.ext'))
            xbmc.executebuiltin('Skin.Reset(%s)' % (skinstring + '.multi'))
        elif num > 0:
            item = addonlist[num]
            if item.getProperty('more') == 'true':
                xbmc.executebuiltin('ActivateWindow(AddonBrowser, addons://repository.xbmc.org/kodi.resource.images/,return)')
            else:
                name = item.getLabel()
                addonid = item.getLabel2()
                extension = '.%s' % item.getProperty('extension')
                subfolders = item.getProperty('subfolders')
                xbmc.executebuiltin('Skin.SetString(%s,%s)' % ((skinstring + '.name'), name))
                xbmc.executebuiltin('Skin.SetString(%s,%s)' % ((skinstring + '.path'), 'resource://%s/' % addonid))
                if subfolders == 'true':
                    xbmc.executebuiltin('Skin.SetBool(%s)' % (skinstring + '.multi'))
                    xbmc.executebuiltin('Skin.Reset(%s)' % (skinstring + '.ext'))
                else:
                    xbmc.executebuiltin('Skin.Reset(%s)' % (skinstring + '.multi'))
                    xbmc.executebuiltin('Skin.SetString(%s,%s)' % ((skinstring + '.ext'), extension))
                    
    def setskinsetting(self):
        setting = self.params.get('setting', '')
        org_id = self.params.get('id', '')
        if '$' in org_id:
            org_id = try_decode(xbmc.getInfoLabel(org_id))
        header = self.params.get('header', '')
        SkinSettings().set_skin_setting(setting=setting, window_header=header, original_id=org_id)
        
    def busytexture(self):
        skinstring = self.params.get('skinstring', 'SkinUtils.SpinnerTexture')
        self.params['skinstring'] = skinstring
        self.params['resourceaddon'] = 'resource.images.busyspinners'
        self.params['customfolder'] = 'special://skin/extras/busy_spinners/'
        self.params['allowmulti'] = 'true'
        self.params['header'] = self.addon.getLocalizedString(32017)
        self.selectimage()
        
    def selectchannel(self):
        log_msg('selectchannel')
        
    def updatechannel(self):
        log_msg('updatechannel')
        
    def playchannel(self):
        log_msg('playchannel')
        
    def selectcolor(self):
        if self.params:
            colorpicker = ColorPicker('script-script_skin_utils-ColorPicker.xml', xbmcaddon.Addon(ADDON_ID).getAddonInfo('path'), 'Default', '1080i')
            colorpicker.skinstring = self.params.get('skinstring','')
            colorpicker.win_property = self.params.get('winproperty','')
            colorpicker.active_palette = self.params.get('palette','')
            colorpicker.header_label = self.params.get('header','')
            propname = self.params.get('shortcutproperty','')
            colorpicker.shortcut_property = propname
            colorpicker.doModal()
            #special action when we want to set our chosen color into a skinshortcuts property
            if propname and not isinstance(colorpicker.result, int):
                self.wait_for_skinshortcuts_window()
                xbmc.sleep(400)
                currentwindow = xbmcgui.Window(xbmcgui.getCurrentWindowDialogId())
                currentwindow.setProperty('customProperty', propname)
                currentwindow.setProperty('customValue',color_picker.result[0])
                xbmc.executebuiltin('SendClick(404)')
                xbmc.sleep(250)
                current_window.setProperty('customProperty', '%s.name' %propname)
                current_window.setProperty('customValue',color_picker.result[1])
                xbmc.executebuiltin('SendClick(404)')
            log_msg('selectcolor')
            del colorpicker
        
    def reset(self):
        backuprestore = BackupRestore()
        filters = self.params.get('filter', [])
        if filters:
            filters = filters.split('|')
        silent = self.params.get('silent', '') == 'true'
        backuprestore.reset(filters, silent)
        log_msg('reset')
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
            backup_file = backuprestore.get_backupfilename(promptfilename)
        backuprestore.backup(filters, backup_file, silent_backup)
        log_msg('backup')
        del backuprestore
        
    def restore(self):
        backuprestore = BackupRestore()
        silent = self.params.get('silent', '')
        if silent and not xbmcvfs.exists(silent):
            log_msg(
                'ERROR while restoring backup ! --> Filename invalid.'
                'Make sure you provide the FULL path, for example special://skin/extras/mybackup.zip',
                xbmc.LOGERROR)
            return
        backuprestore.restore(silent)
        log_msg('restore')

