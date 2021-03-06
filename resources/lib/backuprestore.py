#!/usr/bin/python
# -*- coding: utf-8 -*-

import os, sys
import xbmc
import xbmcvfs
import xbmcgui
import xbmcaddon
from resources.lib.dialogselect import DialogSelect
from resources.lib.utils import log_msg, ADDON_ID, get_skin_name, ADDON_DATA, copy_file, delete_file
from resources.lib.utils import recursive_delete_dir, get_clean_image, normalize_string
from resources.lib.utils import zip_tofile, unzip_fromfile, try_encode, try_decode
from xml.dom.minidom import parse
from datetime import datetime


class BackupRestore:
    params = {}

    def __init__(self):
        '''Initialization and main code run'''
        self.addon = xbmcaddon.Addon(ADDON_ID)

    def __del__(self):
        '''Cleanup Kodi Cpython instances on exit'''
        del self.addon

    def backup(self, filters=None, backup_file="", silent=False):
        '''create skin backup'''
        if not filters:
            filters = []

        if not backup_file:
            return

        # create temp path
        temp_path = self.create_temp()
        zip_temp = '%s/skinbackup-%s.zip' % (temp_path, datetime.now().strftime('%Y-%m-%d %H.%M'))
        temp_path = temp_path + "skinbackup/"

        # backup skinshortcuts preferences
        if not filters or (filters and "skinshortcuts" in filters):
            self.backup_skinshortcuts(temp_path + "skinshortcuts/")

        # backup skin settings
        if "skinshortcutsonly" not in filters:
            skinsettings_path = os.path.join(temp_path, "guisettings.txt")
            self.backup_skinsettings(skinsettings_path, filters, temp_path)

        # zip the backup
        zip_temp = xbmcvfs.translatePath(zip_temp)
        zip_tofile(temp_path, zip_temp)

        # copy file to destination - wait untill it's really copied
        copy_file(zip_temp, backup_file, True)

        # cleanup temp
        recursive_delete_dir(temp_path)
        xbmcvfs.delete(zip_temp)

        # show success message
        if not silent:
            xbmcgui.Dialog().ok(self.addon.getLocalizedString(32004), self.addon.getLocalizedString(32005))

    def restore(self, filename="", silent=False):

        if not filename:
            filename = self.get_restorefilename()

        progressdialog = None
        if not silent:
            progressdialog = xbmcgui.DialogProgress(self.addon.getLocalizedString(32006))
            progressdialog.create(self.addon.getLocalizedString(32007))

        if filename and xbmcvfs.exists(filename):
            # create temp path
            temp_path = self.create_temp()
            if not filename.endswith("zip"):
                # assume that passed filename is actually a skinsettings file
                skinsettingsfile = filename
            else:
                # copy zip to temp directory and unzip
                skinsettingsfile = temp_path + "guisettings.txt"
                if progressdialog:
                    progressdialog.update(0, "unpacking backup...")
                zip_temp = u'%sskinbackup-%s.zip' % (ADDON_DATA, datetime.now().strftime('%Y-%m-%d-%H-%M'))
                copy_file(filename, zip_temp, True)
                unzip_fromfile(zip_temp, temp_path)
                delete_file(zip_temp)
                # copy skinshortcuts preferences
                self.restore_skinshortcuts(temp_path)
                # restore any custom skin images or themes
                for directory in ["custom_images/", "themes/"]:
                    custom_images_folder = "special://profile/addon_data/%s/%s" % (xbmc.getSkinDir(), directory)
                    custom_images_folder_temp = temp_path + directory
                    if xbmcvfs.exists(custom_images_folder_temp):
                        for file in xbmcvfs.listdir(custom_images_folder_temp)[1]:
                            xbmcvfs.copy(custom_images_folder_temp + file,
                                         custom_images_folder + file)
            # restore guisettings
            if xbmcvfs.exists(skinsettingsfile):
                self.restore_guisettings(skinsettingsfile, progressdialog)

            # cleanup temp
            recursive_delete_dir(temp_path)
            progressdialog.close()
        if not silent:
            xbmcgui.Dialog().ok(self.addon.getLocalizedString(32006), self.addon.getLocalizedString(32009))

    def backuprestore(self):
        listitems = []

        # create backup option
        label = self.addon.getLocalizedString(32013)
        listitem = xbmcgui.ListItem(label=label)
        listitem.setArt({'icon': "DefaultFolder.png"})
        listitem.setPath("backup")
        listitems.append(listitem)

        # list existing backups
        backuppath = self.get_backuppath()
        if backuppath:
            for backupfile in xbmcvfs.listdir(backuppath)[1]:
                backupfile = backupfile
                if "Skinbackup" in backupfile and backupfile.endswith(".zip"):
                    label = "%s: %s" % (self.addon.getLocalizedString(32015), backupfile)
                    listitem = xbmcgui.ListItem(label=label)
                    listitem.setArt({'icon': "DefaultFile.png"})
                    listitem.setPath(backuppath + backupfile)
                    listitems.append(listitem)

        # show dialog and list options
        header = self.addon.getLocalizedString(32016)
        extrabutton = self.addon.getLocalizedString(32012)
        dialog = DialogSelect("DialogSelect.xml", "", windowtitle=header,
                              extrabutton=extrabutton, richlayout=True, listing=listitems)
        dialog.doModal()
        result = dialog.result
        del dialog
        if result:
            if isinstance(result, bool):
                # show settings
                xbmc.executebuiltin("Addon.OpenSettings(%s)" % ADDON_ID)
            else:
                if result.getfilename() == "backup":
                    # create new backup
                    self.backup(backup_file=self.get_backupfilename())
                else:
                    # restore backup
                    self.restore(result.getfilename())
                # always open the dialog again
                self.backuprestore()

    def backup_skinsettings(self, dest_file, filters, temp_path):
        # save guisettings
        skinfile = xbmcvfs.File(dest_file, "w")
        skinsettings = self.get_skinsettings(filters)
        skinfile.write(repr(skinsettings))
        skinfile.close()
        # copy any custom skin images or themes
        for item in ["custom_images/", "themes/"]:
            custom_images_folder = "special://profile/addon_data/%s/%s" % (xbmc.getSkinDir(), item)
            if xbmcvfs.exists(custom_images_folder):
                custom_images_folder_temp = os.path.join(temp_path, item)
                for file in xbmcvfs.listdir(custom_images_folder)[1]:
                    source = os.path.join(custom_images_folder, file)
                    dest = os.path.join(custom_images_folder_temp, file)
                    copy_file(source, dest)

    def backup_skinshortcuts(self, dest_path):
        source_path = u'special://profile/addon_data/script.skinshortcuts/'
        if not xbmcvfs.exists(dest_path):
            xbmcvfs.mkdir(dest_path)
        for file in xbmcvfs.listdir(source_path)[1]:
            file = file
            sourcefile = source_path + file
            destfile = dest_path + file
            if xbmc.getCondVisibility("SubString(Skin.String(skinshortcuts-sharedmenu),false)"):
                # User is not sharing menu, so strip the skin name out of the destination file
                destfile = destfile.replace("%s." % (xbmc.getSkinDir()), "")
            if (file.endswith(".DATA.xml") and (not xbmc.getCondVisibility(
                    "SubString(Skin.String(skinshortcuts-sharedmenu),false)") or file.startswith(xbmc.getSkinDir()))):
                xbmcvfs.copy(sourcefile, destfile)
                # parse shortcuts file and look for any images - if found copy them to addon folder
                self.backup_skinshortcuts_images(destfile, dest_path)

            elif file.endswith(".properties") and xbmc.getSkinDir() in file:
                if xbmc.getSkinDir() in file:
                    destfile = dest_path + file.replace(xbmc.getSkinDir(), "SKINPROPERTIES")
                    copy_file(sourcefile, destfile)
                    self.backup_skinshortcuts_properties(destfile, dest_path)
            else:
                # just copy the remaining files
                copy_file(sourcefile, destfile)

    @staticmethod
    def backup_skinshortcuts_images(shortcutfile, dest_path):
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
                        if thumb and (thumb.endswith(".jpg") or thumb.endswith(".png") or thumb.endswith(".gif")):
                            thumb = get_clean_image(thumb)
                            extension = thumb.split(".")[-1]
                            newthumb = os.path.join(dest_path, "%s-thumb-%s.%s" %
                                                    (xbmc.getSkinDir(), normalize_string(defaultid), extension))
                            newthumb_vfs = "special://profile/addon_data/script.skinshortcuts/%s-thumb-%s.%s" % (
                                xbmc.getSkinDir(), normalize_string(defaultid), extension)
                            if xbmcvfs.exists(thumb):
                                copy_file(thumb, newthumb)
                                shortcut.getElementsByTagName('thumb')[0].firstChild.data = newthumb_vfs
        # write changes to skinshortcuts file
        shortcuts_file = xbmcvfs.File(shortcutfile, "w")
        shortcuts_file.write(doc.toxml(encoding='utf-8'))
        shortcuts_file.close()

    @staticmethod
    def backup_skinshortcuts_properties(propertiesfile, dest_path):
        # look for any backgrounds and translate them
        propfile = xbmcvfs.File(propertiesfile)
        data = propfile.read()
        propfile.close()
        allprops = eval(data) if data else []
        for count, prop in enumerate(allprops):
            if prop[2] == "background":
                background = prop[3] if prop[3] else ""
                defaultid = prop[1]
                if background.endswith(".jpg") or background.endswith(".png") or background.endswith(".gif"):
                    background = get_clean_image(background)
                    extension = background.split(".")[-1]
                    newthumb = os.path.join(dest_path, "%s-background-%s.%s" %
                                            (xbmc.getSkinDir(), normalize_string(defaultid), extension))
                    newthumb_vfs = "special://profile/addon_data/script.skinshortcuts/%s-background-%s.%s" % (
                        xbmc.getSkinDir(), normalize_string(defaultid), extension)
                    if xbmcvfs.exists(background):
                        copy_file(background, newthumb)
                        allprops[count] = [prop[0], prop[1], prop[2], newthumb_vfs]
        # write updated properties file
        propfile = xbmcvfs.File(propertiesfile, "w")
        propfile.write(repr(allprops))
        propfile.close()

    def get_backuppath(self):
        backuppath = self.addon.getSetting("backup_path")
        if not backuppath:
            backuppath = xbmcgui.Dialog().browse(3, self.addon.getLocalizedString(32002),
                                                 'files')
            self.addon.setSetting("backup_path", backuppath.encode)
        return backuppath

    def get_backupfilename(self, promptfilename=False):
        backupfile = "%s Skinbackup (%s)" % (
                get_skin_name().capitalize(),
                datetime.now().strftime('%Y-%m-%d %H.%M.%S'))
        if promptfilename:
            header = self.addon.getLocalizedString(32003)
            backupfile = xbmcgui.Dialog().input(header, backupfile).decode
        backupfile += ".zip"
        return self.get_backuppath() + backupfile

    @staticmethod
    def create_temp():
        temp_path = u'%stemp/' % ADDON_DATA
        # workaround weird slashes behaviour on some platforms.
        temp_path = temp_path.replace("//","/").replace("special:/","special://")
        if xbmcvfs.exists(temp_path):
            recursive_delete_dir(temp_path)
            xbmc.sleep(2000)
        xbmcvfs.mkdirs(temp_path)
        xbmcvfs.mkdirs(temp_path + "skinbackup/")
        return temp_path

    def get_restorefilename(self):
        filename = xbmcgui.Dialog().browse(1, self.addon.getLocalizedString(32008),
                                       'files')
        filename = filename.replace("//", "") # possible fix for strange path issue on atv/ftv ?
        return filename

    @staticmethod
    def get_skinsettings(filters=None):
        all_skinsettings = []
        guisettings_path = 'special://profile/addon_data/%s/settings.xml' % xbmc.getSkinDir()
        if xbmcvfs.exists(guisettings_path):
            doc = parse(xbmcvfs.translatePath(guisettings_path))
            skinsettings = doc.documentElement.getElementsByTagName('setting')
            for skinsetting in skinsettings:
                settingname = skinsetting.attributes['id'].nodeValue
                settingtype = skinsetting.attributes['type'].nodeValue
                # we must grab the actual values because the xml file only updates at restarts
                if settingtype == "bool":
                    if "$INFO" not in settingname and xbmc.getCondVisibility("Skin.HasSetting(%s)" % settingname):
                        settingvalue = "true"
                    else:
                        settingvalue = "false"
                else:
                    settingvalue = xbmc.getInfoLabel("Skin.String(%s)" % settingname)
                if not filters:
                    # no filter - just add all settings we can find
                    all_skinsettings.append((settingtype, settingname, settingvalue))
                else:
                    # only select settings defined in our filters
                    for filteritem in filters:
                        if filteritem.lower() in settingname.lower():
                            all_skinsettings.append((settingtype, settingname, settingvalue))
        return all_skinsettings

    def restore_guisettings(self, filename, progressdialog):
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
                                      '%s %s' % (self.addon.getLocalizedString(32033), setting))

            if skinsetting[0] == "string":
                if settingvalue:
                    xbmc.executebuiltin("Skin.SetString(%s,%s)" % (setting, settingvalue))
                else:
                    xbmc.executebuiltin("Skin.Reset(%s)" % setting)
            elif skinsetting[0] == "bool":
                if settingvalue == "true":
                    xbmc.executebuiltin("Skin.SetBool(%s)" % setting)
                else:
                    xbmc.executebuiltin("Skin.Reset(%s)" % setting)
            xbmc.sleep(30)

    @staticmethod
    def restore_skinshortcuts(temp_path):
        source_path = temp_path + "skinshortcuts/"
        if xbmcvfs.exists(source_path):
            dest_path = u'special://profile/addon_data/script.skinshortcuts/'
            for filename in xbmcvfs.listdir(source_path)[1]:
                filename = filename
                sourcefile = source_path + filename
                destfile = dest_path + filename
                if filename == "SKINPROPERTIES.properties":
                    destfile = dest_path + filename.replace("SKINPROPERTIES", xbmc.getSkinDir())
                elif xbmc.getCondVisibility("SubString(Skin.String(skinshortcuts-sharedmenu),false)"):
                    destfile = "%s-" % (xbmc.getSkinDir())
                copy_file(sourcefile, destfile)

    def reset(self, filters=None, silent=False):
        log_msg("filters: %s" % filters)
        if silent or (not silent and
                      xbmcgui.Dialog().yesno(heading=self.addon.getLocalizedString(32010),
                                             message=self.addon.getLocalizedString(32011))):
            if filters:
                # only restore specific settings
                skinsettings = self.get_skinsettings(filters)
                for setting in skinsettings:
                    xbmc.executebuiltin("Skin.Reset(%s)" % setting[1].encode("utf-8"))
            else:
                # restore all skin settings
                xbmc.executebuiltin("RunScript(script.skinshortcuts,type=resetall&warning=false)")
                xbmc.sleep(250)
                xbmc.executebuiltin("Skin.ResetSettings")
                xbmc.sleep(250)
                xbmc.executebuiltin("ReloadSkin")
            # fix default settings and labels
            xbmc.sleep(1500)
            xbmc.executebuiltin("RunScript(script.skin.helper.service,action=checkskinsettings)")

    def check_autobackup(self):
        if self.addon.getSetting("auto_backups") == "true":
            cur_date = datetime.now().strftime('%Y-%m-%d')
            last_backup = self.addon.getSetting("last_backup")
            if cur_date != last_backup and self.addon.getSetting("backup_path"):
                log_msg("Performing auto backup of skin settings...")
                backupfile = self.get_backupfilename()
                self.backup(backup_file=backupfile, silent=True)
                self.addon.setSetting("last_backup", cur_date)
                self.clean_oldbackups()

    def clean_oldbackups(self):
        backuppath = self.addon.getSetting("backup_path")
        max_backups = self.addon.getSetting("max_old_backups")
        if max_backups:
            max_backups = int(max_backups)
            all_files = []
            for filename in xbmcvfs.listdir(backuppath)[1]:
                if ".zip" in filename and "Skinbackup" in filename:
                    filename = filename
                    filepath = backuppath + filename
                    filestat = xbmcvfs.Stat(filepath)
                    modified = filestat.st_mtime()
                    del filestat
                    log_msg(modified)
                    all_files.append((filepath, modified))
            if len(all_files) > max_backups:
                from operator import itemgetter
                old_files = sorted(all_files, key=itemgetter(1), reverse=True)[max_backups - 1:]
                for backupfile in old_files:
                    delete_file(backupfile[0])
