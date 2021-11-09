#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
import sys
import xbmc
import xbmcvfs
import xbmcgui
import xbmcaddon
from xml.dom.minidom import parse
from datetime import datetime

from .utils import setlog, ADDON_ID, getskinname, ADDON_DATA, copyfile, deletefile, recursivedeletedir, getcleanimage, normalizestring, ziptofile, unzipfromfile
from .dialogselect import DialogSelect

class BackupRestore:
    params = {}

    def __init__(self):
        self.addon = xbmcaddon.Addon(ADDON_ID)

    def __del__(self):
        del self.addon

    def backup(self, filters=None, backup_file='', silent=False):
        setlog('backup')
        setlog(backup_file)
        xbmc.executebuiltin('ActivateWindow(busydialognocancel)')
        if not filters:
            filters = []

        if not backup_file:
            return

        # create temp path
        temp_path = self.createtemp()
        zip_temp = '%sskinbackup-%s.zip' % (temp_path, datetime.now().strftime('%Y-%m-%d-%H-%M'))
        temp_path = temp_path + 'skinbackup/'

        # backup skinshortcuts preferences
        if not filters or (filters and 'skinshortcuts' in filters):
            self.backupskinshortcuts(temp_path + 'skinshortcuts/')

        # backup skin settings
        if "skinshortcutsonly" not in filters:
            skinsettings_path = os.path.join(temp_path, 'guisettings.txt')
            self.backupskinsettings(skinsettings_path, filters, temp_path)

        # zip the backup
        zip_temp = xbmcvfs.translatePath(zip_temp)
        ziptofile(temp_path, zip_temp)

        # copy file to destination - wait untill it's really copied
        copyfile(zip_temp, backup_file, True)

        # cleanup temp
        #recursivedeletedir(temp_path)
        #xbmcvfs.delete(zip_temp)
        xbmc.executebuiltin('Dialog.Close(busydialognocancel)')

        # show success message
        if not silent:
            xbmcgui.Dialog().ok(self.addon.getLocalizedString(32000), self.addon.getLocalizedString(32001))

    def restore(self, filename='', silent=False):
        setlog('backup')
        setlog(filename)
        xbmc.executebuiltin('ActivateWindow(busydialognocancel)')
        if not filename:
            filename = self.getrestorefilename()

        progressdialog = None
        if not silent:
            progressdialog = xbmcgui.DialogProgress(self.addon.getLocalizedString(32002))
            progressdialog.create(self.addon.getLocalizedString(32003))

        if filename and xbmcvfs.exists(filename):
            # create temp path
            temp_path = self.createtemp()
            if not filename.endswith('zip'):
                # assume that passed filename is actually a skinsettings file
                skinsettingsfile = filename
            else:
                # copy zip to temp directory and unzip
                skinsettingsfile = temp_path + 'guisettings.txt'
                if progressdialog:
                    progressdialog.update(0, 'unpacking backup...')
                zip_temp = u'%sskinbackup-%s.zip' % (ADDON_DATA, datetime.now().strftime('%Y-%m-%d-%H-%M'))
                copyfile(filename, zip_temp, True)
                unzipfromfile(zip_temp, temp_path)
                deletefile(zip_temp)
                # copy skinshortcuts preferences
                self.restoreskinshortcuts(temp_path)
                # restore any custom skin images or themes
                for directory in ['custom_images/', 'themes/']:
                    custom_images_folder = 'special://profile/addon_data/%s/%s' % (xbmc.getSkinDir(), directory)
                    custom_images_folder_temp = temp_path + directory
                    if xbmcvfs.exists(custom_images_folder_temp):
                        for file in xbmcvfs.listdir(custom_images_folder_temp)[1]:
                            xbmcvfs.copy(custom_images_folder_temp + file,
                                         custom_images_folder + file)
            # restore guisettings
            if xbmcvfs.exists(skinsettingsfile):
                self.restoreguisettings(skinsettingsfile, progressdialog)

            # cleanup temp
            recursivedeletedir(temp_path)
            progressdialog.close()
        xbmc.executebuiltin('Dialog.Close(busydialognocancel)')
        if not silent:
            xbmcgui.Dialog().ok(self.addon.getLocalizedString(32002), self.addon.getLocalizedString(32004))

    def backuprestore(self):
        listitems = []

        # create backup option
        label = self.addon.getLocalizedString(32005)
        listitem = xbmcgui.ListItem(label=label)
        listitem.setArt({'icon': 'DefaultFolder.png'})
        listitem.setPath('backup')
        listitems.append(listitem)

        # list existing backups
        backuppath = self.getbackuppath()
        if backuppath:
            for backupfile in xbmcvfs.listdir(backuppath)[1]:
                backupfile = backupfile
                if 'skinbackup' in backupfile and backupfile.endswith('.zip'):
                    label = '%s: %s' % (self.addon.getLocalizedString(32006), backupfile)
                    listitem = xbmcgui.ListItem(label=label)
                    listitem.setArt({'icon': 'DefaultFile.png'})
                    listitem.setPath(backuppath + backupfile)
                    listitems.append(listitem)

        # show dialog and list options
        header = self.addon.getLocalizedString(32007)
        extrabutton = self.addon.getLocalizedString(32008)
        dialog = DialogSelect('DialogSelect.xml', '', windowtitle=header,
                              extrabutton=extrabutton, richlayout=True, listing=listitems)
        dialog.doModal()
        result = dialog.result
        del dialog
        if result:
            if isinstance(result, bool):
                # show settings
                xbmc.executebuiltin('Addon.OpenSettings(%s)' % ADDON_ID)
            else:
                if result.getfilename() == 'backup':
                    # create new backup
                    self.backup(backup_file=self.getbackupfilename())
                else:
                    # restore backup
                    self.restore(result.getfilename())
                # always open the dialog again
                self.backuprestore()

    def backupskinsettings(self, dest_file, filters, temp_path):
        # save guisettings
        skinfile = xbmcvfs.File(dest_file, 'w')
        skinsettings = self.getskinsettings(filters)
        skinfile.write(repr(skinsettings))
        skinfile.close()
        # copy any custom skin images or themes
        for item in ['custom_images/', 'themes/']:
            custom_images_folder = 'special://profile/addon_data/%s/%s' % (xbmc.getSkinDir(), item)
            if xbmcvfs.exists(custom_images_folder):
                custom_images_folder_temp = os.path.join(temp_path, item)
                for file in xbmcvfs.listdir(custom_images_folder)[1]:
                    source = os.path.join(custom_images_folder, file)
                    dest = os.path.join(custom_images_folder_temp, file)
                    copyfile(source, dest)

    def backupskinshortcuts(self, dest_path):
        setlog('backupskinshortcuts')
        source_path = u'special://profile/addon_data/script.skinshortcuts/'
        if not xbmcvfs.exists(dest_path):
            xbmcvfs.mkdir(dest_path)
        for file in xbmcvfs.listdir(source_path)[1]:
            file = file
            sourcefile = source_path + file
            destfile = dest_path + file
            if 'settings.xml' in file:
                copyfile(sourcefile, destfile)
                
            if xbmc.getCondVisibility('SubString(Skin.String(skinshortcuts-sharedmenu),false)'):
                # User is not sharing menu, so strip the skin name out of the destination file
                destfile = destfile.replace('%s.' % (xbmc.getSkinDir()), '')
 
            if (file.endswith('.DATA.xml') and (not xbmc.getCondVisibility('SubString(Skin.String(skinshortcuts-sharedmenu),false)') or file.startswith(xbmc.getSkinDir()))):
                xbmcvfs.copy(sourcefile, destfile)
                # parse shortcuts file and look for any images - if found copy them to addon folder
                self.backupskinshortcutsimages(destfile, dest_path)
            elif file.endswith('.properties') and xbmc.getSkinDir() in file:
                if xbmc.getSkinDir() in file:
                    destfile = dest_path + file.replace(xbmc.getSkinDir(), 'SKINPROPERTIES')
                    copyfile(sourcefile, destfile)
                    self.backupskinshortcutsproperties(destfile, dest_path)
            elif file.endswith('.hash') and xbmc.getSkinDir() in file:
                if xbmc.getSkinDir() in file:
                    copyfile(sourcefile, destfile)

    @staticmethod
    def backupskinshortcutsimages(shortcutfile, dest_path):
        shortcutfile = xbmcvfs.translatePath(shortcutfile)
        doc = parse(shortcutfile)
        listing = doc.documentElement.getElementsByTagName('shortcut')
        for shortcut in listing:
            defaultid = shortcut.getElementsByTagName('defaultID')
            if defaultid:
                defaultid = defaultid[0].firstChild
                if defaultid:
                    defaultid = defaultid.data
                if not defaultid:
                    defaultid = shortcut.getElementsByTagName('label')[0].firstChild.data
                thumb = shortcut.getElementsByTagName('thumb')
                if thumb:
                    thumb = thumb[0].firstChild
                    if thumb:
                        thumb = thumb.data
                        if thumb and (thumb.endswith('.jpg') or thumb.endswith('.png') or thumb.endswith('.gif')):
                            thumb = getcleanimage(thumb)
                            extension = thumb.split('.')[-1]
                            newthumb = os.path.join(dest_path, '%s-thumb-%s.%s' %
                                                    (xbmc.getSkinDir(), normalizestring(defaultid), extension))
                            newthumb_vfs = 'special://profile/addon_data/script.skinshortcuts/%s-thumb-%s.%s' % (
                                xbmc.getSkinDir(), normalizestring(defaultid), extension)
                            if xbmcvfs.exists(thumb):
                                copyfile(thumb, newthumb)
                                shortcut.getElementsByTagName('thumb')[0].firstChild.data = newthumb_vfs
        # write changes to skinshortcuts file
        shortcuts_file = xbmcvfs.File(shortcutfile, 'w')
        shortcuts_file.write(doc.toxml(encoding='utf-8'))
        shortcuts_file.close()

    @staticmethod
    def backupskinshortcutsproperties(propertiesfile, dest_path):
        # look for any backgrounds and translate them
        propfile = xbmcvfs.File(propertiesfile)
        data = propfile.read()
        propfile.close()
        allprops = eval(data) if data else []
        for count, prop in enumerate(allprops):
            if prop[2] == 'background':
                background = prop[3] if prop[3] else ''
                defaultid = prop[1]
                if background.endswith('.jpg') or background.endswith('.png') or background.endswith('.gif'):
                    background = getcleanimage(background)
                    extension = background.split('.')[-1]
                    newthumb = os.path.join(dest_path, '%s-background-%s.%s' %
                                            (xbmc.getSkinDir(), normalizestring(defaultid), extension))
                    newthumb_vfs = 'special://profile/addon_data/script.skinshortcuts/%s-background-%s.%s' % (
                        xbmc.getSkinDir(), normalizestring(defaultid), extension)
                    if xbmcvfs.exists(background):
                        copyfile(background, newthumb)
                        allprops[count] = [prop[0], prop[1], prop[2], newthumb_vfs]
        # write updated properties file
        propfile = xbmcvfs.File(propertiesfile, 'w')
        propfile.write(repr(allprops))
        propfile.close()

    def getbackuppath(self):
        backuppath = self.addon.getSetting('backup_path')
        if not backuppath:
            backuppath = xbmcgui.Dialog().browse(3, self.addon.getLocalizedString(32009),
                                                 'files')
            self.addon.setSetting('backup_path', backuppath.encode)
        return backuppath

    def getbackupfilename(self, promptfilename=False):
        backupfile = '%s-skinbackup-%s' % (
                getskinname(),
                datetime.now().strftime('%Y-%m-%d-%H-%M'))
        if promptfilename:
            header = self.addon.getLocalizedString(32010)
            backupfile = xbmcgui.Dialog().input(header, backupfile).decode
        backupfile += '.zip'
        return self.getbackuppath() + backupfile

    @staticmethod
    def createtemp():
        temp_path = u'%stemp/' % ADDON_DATA
        # workaround weird slashes behaviour on some platforms.
        temp_path = temp_path.replace('//','/').replace('special:/','special://')
        if xbmcvfs.exists(temp_path):
            recursivedeletedir(temp_path)
            xbmc.sleep(2000)
        xbmcvfs.mkdirs(temp_path)
        xbmcvfs.mkdirs(temp_path + 'skinbackup/')
        return temp_path

    def getrestorefilename(self):
        filename = xbmcgui.Dialog().browse(1, self.addon.getLocalizedString(32011), 'files')
        filename = filename.replace('//', '') # possible fix for strange path issue on atv/ftv ?
        return filename

    @staticmethod
    def getskinsettings(filters=None):
        all_skinsettings = []
        guisettings_path = 'special://profile/addon_data/%s/settings.xml' % xbmc.getSkinDir()
        if xbmcvfs.exists(guisettings_path):
            doc = parse(xbmcvfs.translatePath(guisettings_path))
            skinsettings = doc.documentElement.getElementsByTagName('setting')
            for skinsetting in skinsettings:
                settingname = skinsetting.attributes['id'].nodeValue
                settingtype = skinsetting.attributes['type'].nodeValue
                # we must grab the actual values because the xml file only updates at restarts
                if settingtype == 'bool':
                    if '$INFO' not in settingname and xbmc.getCondVisibility('Skin.HasSetting(%s)' % settingname):
                        settingvalue = 'true'
                    else:
                        settingvalue = 'false'
                else:
                    settingvalue = xbmc.getInfoLabel('Skin.String(%s)' % settingname)
                if not filters:
                    # no filter - just add all settings we can find
                    all_skinsettings.append((settingtype, settingname, settingvalue))
                else:
                    # only select settings defined in our filters
                    for filteritem in filters:
                        if filteritem.lower() in settingname.lower():
                            all_skinsettings.append((settingtype, settingname, settingvalue))
        return all_skinsettings

    def restoreguisettings(self, filename, progressdialog):
        kodifile = xbmcvfs.File(filename, 'r')
        data = kodifile.read()
        importstring = eval(data)
        kodifile.close()
        xbmc.sleep(200)
        for count, skinsetting in enumerate(importstring):

            if progressdialog and progressdialog.iscanceled():
                return

            setting = skinsetting[1]
            settingvalue = skinsetting[2]

            if progressdialog:
                progressdialog.update((count * 100) // len(importstring),
                                      '%s %s' % (self.addon.getLocalizedString(32012), setting))

            if skinsetting[0] == 'string':
                if settingvalue:
                    xbmc.executebuiltin('Skin.SetString(%s,%s)' % (setting, settingvalue))
                else:
                    xbmc.executebuiltin('Skin.Reset(%s)' % setting)
            elif skinsetting[0] == 'bool':
                if settingvalue == 'true':
                    xbmc.executebuiltin('Skin.SetBool(%s)' % setting)
                else:
                    xbmc.executebuiltin('Skin.Reset(%s)' % setting)
            xbmc.sleep(30)

    @staticmethod
    def restoreskinshortcuts(temp_path):
        source_path = temp_path + 'skinshortcuts/'
        if xbmcvfs.exists(source_path):
            dest_path = u'special://profile/addon_data/script.skinshortcuts/'
            for filename in xbmcvfs.listdir(source_path)[1]:
                filename = filename
                sourcefile = source_path + filename
                destfile = dest_path + filename
                if filename == 'SKINPROPERTIES.properties':
                    destfile = dest_path + filename.replace('SKINPROPERTIES', xbmc.getSkinDir())
                elif xbmc.getCondVisibility('SubString(Skin.String(skinshortcuts-sharedmenu),false)'):
                    destfile = '%s-' % (xbmc.getSkinDir())
                copyfile(sourcefile, destfile)

    def reset(self, filters=None, silent=False):
        setlog('filters: %s' % filters)
        if silent or (not silent and
            xbmcgui.Dialog().yesno(heading=self.addon.getLocalizedString(32013), message=self.addon.getLocalizedString(32014))):
            if filters:
                # only restore specific settings
                skinsettings = self.getskinsettings(filters)
                for setting in skinsettings:
                    xbmc.executebuiltin('Skin.Reset(%s)' % setting[1].encode('utf-8'))
            else:
                # restore all skin settings
                xbmc.executebuiltin('RunScript(script.skinshortcuts,type=resetall&warning=false)')
                xbmc.sleep(250)
                xbmc.executebuiltin('Skin.ResetSettings')
                xbmc.sleep(250)
                xbmc.executebuiltin("ReloadSkin")
            # fix default settings and labels
            xbmc.sleep(1500)
            xbmc.executebuiltin('RunScript(script.skin.utils,action=checkskinsettings)')

    #
    def checkautobackup(self):
        if self.addon.getSetting('auto_backups') == 'true':
            cur_date = datetime.now().strftime('%Y-%m-%d')
            last_backup = self.addon.getSetting('last_backup')
            if cur_date != last_backup and self.addon.getSetting('backup_path'):
                setlog('Performing auto backup of skin settings...')
                backupfile = self.getbackupfilename()
                self.backup(backup_file=backupfile, silent=True)
                self.addon.setSetting('last_backup', cur_date)
                self.cleanoldbackups()

    def cleanoldbackups(self):
        backuppath = self.addon.getSetting('backup_path')
        max_backups = self.addon.getSetting('max_old_backups')
        if max_backups:
            max_backups = int(max_backups)
            all_files = []
            for filename in xbmcvfs.listdir(backuppath)[1]:
                if ".zip" in filename and 'skinbackup' in filename:
                    filename = filename
                    filepath = backuppath + filename
                    filestat = xbmcvfs.Stat(filepath)
                    modified = filestat.st_mtime()
                    del filestat
                    setlog(modified)
                    all_files.append((filepath, modified))
            if len(all_files) > max_backups:
                from operator import itemgetter
                old_files = sorted(all_files, key=itemgetter(1), reverse=True)[max_backups - 1:]
                for backupfile in old_files:
                    deletefile(backupfile[0])
