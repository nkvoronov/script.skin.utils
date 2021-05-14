#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
import sys
import xbmc
import xbmcvfs
import xbmcgui
import xbmcaddon
import re
import urllib.request, urllib.error, urllib.parse

from .utils import ADDON_ID, KODI_VERSION, setlogexception, kodijson, trydecode, getCondVisibility
from .dialogselect import DialogSelect
from .simplecache import SimpleCache

def setresourceaddon(addontype, skinstring='', header='', custom=False, morebutton=False):
    xbmc.executebuiltin('ActivateWindow(busydialog)')
    cur_value = trydecode(xbmc.getInfoLabel('Skin.String(%s.name)' % skinstring))
    listing = []
    addon = xbmcaddon.Addon(ADDON_ID)
    if not header:
        header = addon.getLocalizedString(32018)

    # none option
    listitem = xbmcgui.ListItem(xbmc.getLocalizedString(231),xbmc.getLocalizedString(24040))
    listitem.setArt({'icon': 'DefaultAddonNone.png'})
    listitem.setProperty('addonid', 'none')
    listing.append(listitem)

    # custom path
    if custom:
        listitem = xbmcgui.ListItem(label=xbmc.getLocalizedString(19076),label2=addon.getLocalizedString(32020))
        listitem.setArt({'icon': 'DefaultFolder.png'})
        listitem.setProperty('addonid', 'custom')
        listing.append(listitem)

    # available resource addons
    for item in getresourceaddons(addontype):
        name = item['name']
        icon = item['thumbnail']
        addonid = item['addonid']
        path = item['path']
        summary = item['summary']
        author = item['author']
        listitem = xbmcgui.ListItem(label=name, label2=summary)
        listitem.setArt({'icon':'DefaultAddonImages.png', 'thumb':icon})
        listitem.setProperty('addonid', addonid)
        listitem.setProperty('author', author)
        listitem.setProperty('Addon.Summary', summary)
        listing.append(listitem)
    
    if not morebutton:
        listitem = xbmcgui.ListItem(xbmc.getLocalizedString(21452))
        listitem.setProperty('addonid', 'more')
        listing.append(listitem)

    # show select dialog with choices
    dialog = DialogSelect('DialogSelect.xml', '', listing=listing, windowtitle=header,
                          richlayout=True, getmorebutton=morebutton, autofocuslabel=cur_value)
    dialog.doModal()
    result = dialog.result
    del dialog

    # process selection...
    if isinstance(result, bool) and result:
        # refresh listing requested by getmore button
        del addon
        return setresourceaddon(addontype, skinstring)
    elif result:
        addon_id = result.getProperty('addonid')
        addon_name = result.getLabel()
        if addon_id == 'more':
            xbmc.executebuiltin('ActivateWindow(AddonBrowser, addons://repository.xbmc.org/kodi.resource.images/,return)')
        elif addon_id == 'none' and skinstring:
            # None
            xbmc.executebuiltin('Skin.Reset(%s)' % skinstring)
            xbmc.executebuiltin('Skin.Reset(%s.ext)' % skinstring)
            xbmc.executebuiltin('Skin.SetString(%s.name,%s)' % (skinstring, addon_name))
            xbmc.executebuiltin('Skin.SetString(%s.label,%s)' % (skinstring, addon_name))
            xbmc.executebuiltin('Skin.Reset(%s.path)' % skinstring)
            xbmc.executebuiltin('Skin.Reset(%s.multi)' % skinstring)
        else:
            if addon_id == 'custom':
                # custom path
                dialog = xbmcgui.Dialog()
                custom_path = dialog.browse(0, addon.getLocalizedString(32021), 'files')
                del dialog
                result.setPath(custom_path)
            addonpath = result.getLabel()
            if addonpath:
                is_multi, extension = getmultiextension(addonpath)
                xbmc.executebuiltin('Skin.SetString(%s,%s)' % (skinstring, addonpath))
                xbmc.executebuiltin('Skin.SetString(%s.path,%s)' % (skinstring, addonpath))
                xbmc.executebuiltin('Skin.SetString(%s.name,%s)' % (skinstring, addon_name))
                xbmc.executebuiltin('Skin.SetString(%s.label,%s)' % (skinstring, addon_name))
                xbmc.executebuiltin('Skin.SetString(%s.ext,%s)' % (skinstring, extension))
                if is_multi:
                    xbmc.executebuiltin('Skin.SetBool(%s.multi)' % skinstring)
                else:
                    xbmc.executebuiltin('Skin.Reset(%s.multi)' % skinstring)
    del addon

def downloadresourceaddons(addontype):
    xbmc.executebuiltin('ActivateWindow(busydialog)')
    listitems = []
    addon = xbmcaddon.Addon(ADDON_ID)
    for item in getreporesourceaddons(addontype):
        if not getCondVisibility('System.HasAddon(%s)' % item["addonid"]):
            label2 = '%s: %s' % (xbmc.getLocalizedString(21863), item['author'])
            listitem = xbmcgui.ListItem(label=item["name"], label2=label2)
            listitem.setArt({'icon':'DefaultAddonImages.png', 'thumb':item['thumbnail']})
            listitem.setProperty('addonid', item['addonid'])
            listitems.append(listitem)
    # if no addons available show OK dialog..
    if not listitems:
        dialog = xbmcgui.Dialog()
        dialog.ok(addon.getLocalizedString(32022), addon.getLocalizedString(32023))
        del dialog
    else:
        # show select dialog with choices
        dialog = DialogSelect('DialogSelect.xml', '', listing=listitems,
                              windowtitle=addon.getLocalizedString(32022), richlayout=True)
        dialog.doModal()
        result = dialog.result
        del dialog
        del addon
        # process selection...
        if result:
            addon_id = result.getProperty('addonid')
            # trigger install...
            monitor = xbmc.Monitor()
            if KODI_VERSION > 16:
                xbmc.executebuiltin('InstallAddon(%s)' % addon_id)
            else:
                xbmc.executebuiltin('RunPlugin(plugin://%s)' % addon_id)
            count = 0
            # wait (max 2 minutes) untill install is completed
            install_succes = False
            while not monitor.waitForAbort(1) and not install_succes and count < 120:
                install_succes = getCondVisibility('System.HasAddon(%s)' % addon_id)
            del monitor
            if install_succes:
                return True
    return False

def checkresourceaddons(addonslist):
    addon = xbmcaddon.Addon(ADDON_ID)
    for item in addonslist:
        setting = item.split(';')[0]
        addontype = item.split(';')[1]
        addontypelabel = item.split(';')[2]
        skinsetting = trydecode(xbmc.getInfoLabel('Skin.String(%s.path)' % setting))
        if not skinsetting or (skinsetting and
                               getCondVisibility('!System.HasAddon(%s)' %
                                                      skinsetting.replace('resource://', '').replace('/', ''))):
            # skin setting is empty or filled with non existing addon...
            if not checkresourceaddon(setting, addontype):
                ret = xbmcgui.Dialog().yesno(
                    heading=addon.getLocalizedString(32024) % addontypelabel,
                    message=addon.getLocalizedString(32025) % addontypelabel)
                xbmc.executebuiltin('Skin.Reset(%s.path)' % setting)
                if ret:
                    downloadresourceaddons(addontype)
                    checkresourceaddon(setting, addontype)
    del addon

def checkresourceaddon(skinstring='', addontype=''):
    if not addontype:
        addontype = params.get('addontype')
    if not skinstring:
        skinstring = params.get('skinstring')
    if addontype and skinstring:
        for item in getresourceaddons(addontype):
            xbmc.executebuiltin('Skin.SetString(%s,%s)' % (skinstring, item['path']))
            xbmc.executebuiltin('Skin.SetString(%s.path,%s)' % (skinstring, item['path']))
            xbmc.executebuiltin('Skin.SetString(%s.name,%s)' % (skinstring, item['name']))
            xbmc.executebuiltin('Skin.SetString(%s.label,%s)' % (skinstring, item['name']))
            is_multi, extension = getmultiextension(item['path'])
            if is_multi:
                xbmc.executebuiltin('Skin.SetBool(%s.multi)' % (skinstring))
            xbmc.executebuiltin('Skin.SetString(%s.ext,%s)' % (skinstring, extension))
            return True
    return False

def getresourceaddons(filterstr=''):
    result = []
    params = {'type': 'kodi.resource.images',
              'properties': ['name', 'thumbnail', 'path', 'author', 'summary']}
    for item in kodijson('Addons.GetAddons', params, 'addons'):
        if not filterstr or item['addonid'].lower().startswith(filterstr.lower()):
            item['path'] = 'resource://%s/' % item['addonid']
            result.append(item)

    return result

def getmultiextension(filepath):
    is_multi = False
    extension = ''
    dirs, files = xbmcvfs.listdir(filepath)
    if len(dirs) > 0:
        is_multi = True
    if not is_multi:
        for item in files:
            extension = '.' + item.split('.')[-1]
            break
    return (is_multi, extension)

def getreporesourceaddons(filterstr=''):
    result = []
    simplecache = SimpleCache()
    for item in xbmcvfs.listdir('addons://all/kodi.resource.images/')[1]:
        if not filterstr or item.lower().startswith(filterstr.lower()):
            addoninfo = getrepoaddoninfo(item, simplecache)
            if not addoninfo.get('name'):
                addoninfo = {'addonid': item, 'name': item, 'author': ''}
                addoninfo['thumbnail'] = 'http://mirrors.kodi.tv/addons/krypton/%s/icon.png' % item
            addoninfo['ath'] = 'resource://%s/' % item
            result.append(addoninfo)
    simplecache.close()
    return result

def getrepoaddoninfo(addonid, simplecache=None):
    if simplecache:
        cache = simplecache
        cachestr = 'skinutils.addoninfo.%s' % addonid
        info = simplecache.get(cachestr)
    if not info:
        info = {'addonid': addonid, 'name': '', 'thumbnail': '', 'author': ''}
        mirrorurl = 'http://addons.kodi.tv/show/%s/' % addonid
        try:
            if sys.version_info.major == 3:
                req = urllib.request.Request(mirrorurl)
                req.add_header('User-Agent',
                           'Mozilla/5.0 (Windows; U; Windows NT 5.1; en-GB; rv:1.9.0.3) Gecko/2008092417 Firefox/3.0.3')
                response = urllib.request.urlopen(req)
            else:
                req = urllib2.Request(mirrorurl)
                req.add_header('User-Agent',
                           'Mozilla/5.0 (Windows; U; Windows NT 5.1; en-GB; rv:1.9.0.3) Gecko/2008092417 Firefox/3.0.3')
                response = urllib2.urlopen(req)
            body = response.read()
            response.close()
            body = body.replace('\r', '').replace('\n', '').replace('\t', '')
            for addondetail in re.compile('<div id="addonDetail">(.*?)</div>').findall(body):
                for h2_item in re.compile('<h2>(.*?)</h2>').findall(addondetail):
                    info["name"] = h2_item
                    break
                for thumbnail in re.compile('src="(.*?)"').findall(addondetail):
                    icon = 'http://addons.kodi.tv/%s' % thumbnail
                    info['thumbnail'] = icon
                    break
                authors = []
                for addonmetadata in re.compile('<div id="addonMetaData">(.*?)</div>').findall(body):
                    for author in re.compile('<a href="(.*?)">(.*?)</a>').findall(addonmetadata):
                        authors.append(author[1])
                info['author'] = ','.join(authors)
                break
        except Exception as exc:
            if 'HTTP Error 404' not in exc:  # ignore not found exceptions
                setlogexception(__name__, exc)
        if simplecache:
            cache.set(cachestr, info)
    return info

def getresourceimages(addontype, recursive=False):
    images = []
    for addon in getresourceaddons(addontype):
        addonpath = addon['path']
        if xbmcvfs.exists('special://home/addons/%s/resources/' % addon['addonid']):
            addonpath = 'special://home/addons/%s/resources/' % addon['addonid']
        images += walkdirectory(addonpath, recursive, addon['name'])
    return images

def walkdirectory(browsedir, recursive=False, label2=''):
    images = []
    if xbmcvfs.exists(browsedir):
        dirs = xbmcvfs.listdir(browsedir)[0]
        subdirs = [browsedir]
        for directory in dirs:
            directory = trydecode(directory)
            cur_dir = '%s%s/' % (browsedir, directory)
            if recursive:
                subdirs.append(cur_dir)
            else:
                label = directory
                images.append((label, cur_dir, label2, 'DefaultFolder.png'))
        for subdir in subdirs:
            for imagefile in xbmcvfs.listdir(subdir)[1]:
                imagefile = trydecode(imagefile)
                label = imagefile
                imagepath = subdir + imagefile
                images.append((label, imagepath, label2, imagepath))
    return images
