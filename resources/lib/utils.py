#!/usr/bin/python
# -*- coding: utf-8 -*-

import os 
import sys
import xbmc
import xbmcvfs
import xbmcgui
import urllib.request, urllib.parse, urllib.error
import urllib
import traceback

try:
    import simplejson as json
except Exception:
    import json

ADDON_ID = 'script.skin.utils'
KODI_VERSION = int(xbmc.getInfoLabel('System.BuildVersion').split('.')[0])
KODILANGUAGE = xbmc.getLanguage(xbmc.ISO_639_1)
ADDON_DATA = 'special://profile/addon_data/%s/' % ADDON_ID

COLORFILES_PATH = xbmc.translatePath('special://profile/addon_data/%s/colors/' % ADDON_ID)
SKINCOLORFILES_PATH = xbmc.translatePath('special://profile/addon_data/%s/colors/' % xbmc.getSkinDir())
SKINCOLORFILE = xbmc.translatePath('special://skin/extras/colors/colors.xml')

def setlog(msg, loglevel=xbmc.LOGDEBUG):
    if sys.version_info.major < 3:
        if isinstance(msg, unicode):
            msg = msg.encode('utf-8')
    xbmc.log('Skin Utils --> %s' % msg, level=loglevel)

def setlogexception(modulename, exceptiondetails):
    if sys.version_info.major == 3:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        lines = traceback.format_exception(exc_type, exc_value, exc_traceback)
        setlog('Exception details: Type: %s Value: %s Traceback: %s' % (exc_type.__name__, exc_value, ''.join(line for line in lines)), xbmc.LOGWARNING)
    else:
        setlog(format_exc(sys.exc_info()), xbmc.LOGWARNING)
    setlog('Exception in %s ! --> %s' % (modulename, exceptiondetails), xbmc.LOGERROR)

def kodijson(jsonmethod, params=None, returntype=None):
    kodi_json = {}
    kodi_json['jsonrpc'] = '2.0'
    kodi_json['method'] = jsonmethod
    if not params:
        params = {}
    kodi_json['params'] = params
    kodi_json['id'] = 1
    json_response = xbmc.executeJSONRPC(tryencode(json.dumps(kodi_json)))
    json_object = json.loads(trydecode(json_response))

    # set the default returntype to prevent errors
    if 'details' in jsonmethod.lower():
        result = {}
    else:
        result = []
    if 'result' in json_object:
        if returntype and returntype in json_object['result']:
            # returntype specified, return immediately
            result = json_object['result'][returntype]
        else:
            # no returntype specified, we'll have to look for it
            if isinstance(json_object['result'], dict):
                if sys.version_info.major == 3:
                    for key, value in list(json_object['result'].items()):
                        if not key == 'limits':
                            result = value
                            break
                else:
                    for key, value in json_object['result'].items():
                        if not key == 'limits':
                            result = value
                            break
            else:
                return json_object['result']
    else:
        setlog(json_response)
        setlog(kodi_json)
    return result

def recursivedeletedir(fullpath):
    success = True
    dirs, files = xbmcvfs.listdir(fullpath)
    for file in files:
        file = file
        success = xbmcvfs.delete(os.path.join(fullpath, file))
    for directory in dirs:
        directory = directory
        success = recursivedeletedir(os.path.join(fullpath, directory))
    success = xbmcvfs.rmdir(fullpath)
    return success

def copyfile(source, destination, do_wait=False):
    if xbmcvfs.exists(destination):
        deletefile(destination)
    xbmcvfs.copy(source, destination)
    if do_wait:
        count = 20
        while count:
            xbmc.sleep(500)  # this first sleep is intentional
            if xbmcvfs.exists(destination):
                break
            count -= 1

def deletefile(filepath, do_wait=False):
    xbmcvfs.delete(filepath)
    if do_wait:
        count = 20
        while count:
            xbmc.sleep(500)  # this first sleep is intentional
            if not xbmcvfs.exists(filepath):
                break
            count -= 1

def getcleanimage(image):
    if image and 'image://' in image:
        image = image.replace('image://', '')
        image = urllib.unquote(tryencode(image))
        if image.endswith('/'):
            image = image[:-1]
    if 'music@' in image:
        # filter out embedded covers
        image = ''
    return image

def normalizestring(text):
    text = text.replace(':', '')
    text = text.replace('/', '-')
    text = text.replace('\\', '-')
    text = text.replace('<', '')
    text = text.replace('>', '')
    text = text.replace('*', '')
    text = text.replace('?', '')
    text = text.replace('|', '')
    text = text.replace('(', '')
    text = text.replace(')', '')
    text = text.replace("\"", '')
    text = text.strip()
    text = text.rstrip('.')
    return text

def addtozip(src, zip_file, abs_src):
    dirs, files = xbmcvfs.listdir(src)
    for filename in files:
        filename = filename
        setlog('zipping %s' % filename)
        filepath = xbmcvfs.translatePath(os.path.join(src, filename))
        absname = os.path.abspath(filepath)
        arcname = absname[len(abs_src) + 1:]
        try:
            # newer python can use unicode for the files in the zip
            zip_file.write(tryencode(absname), tryencode(arcname))
        except Exception:
            # older python version uses utf-8 for filenames in the zip
            zip_file.write(absname.encode('utf-8'), arcname.encode('utf-8'))
    for directory in dirs:
        addtozip(os.path.join(src, directory), zip_file, abs_src)
    return zip_file

def ziptofile(src, dst):
    import zipfile
    zip_file = zipfile.ZipFile(dst, 'w', zipfile.ZIP_DEFLATED)
    abs_src = os.path.abspath(xbmcvfs.translatePath(src))
    zip_file = addtozip(src, zip_file, abs_src)
    zip_file.close()

def unzipfromfile(zip_path, dest_path):
    import shutil
    import zipfile
    zip_path = xbmcvfs.translatePath(zip_path)
    dest_path = xbmcvfs.translatePath(dest_path)
    setlog('START UNZIP of file %s  to path %s ' % (zip_path, dest_path))
    zip_file = zipfile.ZipFile(zip_path, 'r')
    for fileinfo in zip_file.infolist():
        filename = fileinfo.filename
        setlog('unzipping: ' + filename)
        splitter = None
        if '\\' in filename:
            xbmcvfs.mkdirs(os.path.join(dest_path, filename.rsplit('\\', 1)[0]))
            splitter = '\\'
        elif "/" in filename:
            xbmcvfs.mkdirs(os.path.join(dest_path, filename.rsplit('/', 1)[0]))
            splitter = '/'
        filename = os.path.join(dest_path, filename)
        if not (splitter and filename.endswith(splitter)):
            try:
                # newer python uses unicode
                outputfile = open(tryencode(filename), 'wb')
            except Exception:
                # older python uses utf-8
                outputfile = open(filename.encode('utf-8'), 'wb')
            # use shutil to support non-ascii formatted files in the zip
            shutil.copyfileobj(zip_file.open(fileinfo.filename), outputfile)
            outputfile.close()
    zip_file.close()
    setlog('UNZIP DONE of file %s  to path %s ' % (zip_path, dest_path))

def getskinname():
    skin_name = xbmc.getSkinDir()
    skin_name = skin_name.replace('skin.', '')
    skin_name = skin_name.replace('.kryptonbeta', '')
    skin_name = skin_name.replace('.jarvisbeta', '')
    skin_name = skin_name.replace('.leiabeta', '')
    skin_name = skin_name.replace('.matrixbeta', '')
    return skin_name

def tryencode(text, encoding='utf-8'):
    if sys.version_info.major == 3:
        return text
    else:
        try:
            return text.encode(encoding, 'ignore')
        except Exception:
            return text

def trydecode(text, encoding='utf-8'):
    if sys.version_info.major == 3:
        return text
    else:
        try:
            return text.decode(encoding, 'ignore')
        except Exception:
            return text

def urlencode(text):
    if sys.version_info.major == 3:
        blah = urllib.parse.urlencode({'blahblahblah': tryencode(text)})
    else:
        blah = urllib.urlencode({'blahblahblah': tryencode(text)})
    blah = blah[13:]
    return blah

def getcurrentcontenttype(containerprefix=''):
    content_type = ''
    if not containerprefix:
        if getCondVisibility('Container.Content(episodes)'):
            content_type = 'episodes'
        elif getCondVisibility('Container.Content(movies) + !String.Contains(Container.FolderPath,setid=)'):
            content_type = 'movies'
        elif getCondVisibility('[Container.Content(sets) | '
                                    'String.IsEqual(Container.Folderpath,videodb://movies/sets/)] + '
                                    '!String.Contains(Container.FolderPath,setid=)'):
            content_type = 'sets'
        elif getCondVisibility('String.Contains(Container.FolderPath,setid=)'):
            content_type = 'setmovies'
        elif getCondVisibility('!String.IsEmpty(Container.Content) + !String.IsEqual(Container.Content,pvr)'):
            content_type = xbmc.getInfoLabel('Container.Content')
        elif getCondVisibility('Container.Content(tvshows)'):
            content_type = 'tvshows'
        elif getCondVisibility('Container.Content(seasons)'):
            content_type = 'seasons'
        elif getCondVisibility('Container.Content(musicvideos)'):
            content_type = 'musicvideos'
        elif getCondVisibility('Container.Content(songs) | '
                                    'String.IsEqual(Container.FolderPath,musicdb://singles/)'):
            content_type = 'songs'
        elif getCondVisibility('Container.Content(artists)'):
            content_type = 'artists'
        elif getCondVisibility('Container.Content(albums)'):
            content_type = 'albums'
        elif getCondVisibility('Window.IsActive(MyPVRChannels.xml) | Window.IsActive(MyPVRGuide.xml) | '
                                    'Window.IsActive(MyPVRSearch.xml) | Window.IsActive(pvrguideinfo)'):
            content_type = 'tvchannels'
        elif getCondVisibility('Window.IsActive(MyPVRRecordings.xml) | Window.IsActive(MyPVRTimers.xml) | '
                                    'Window.IsActive(pvrrecordinginfo)'):
            content_type = 'tvrecordings'
        elif getCondVisibility('Window.IsActive(programs) | Window.IsActive(addonbrowser)'):
            content_type = 'addons'
        elif getCondVisibility('Window.IsActive(pictures)'):
            content_type = 'pictures'
        elif getCondVisibility('Container.Content(genres)'):
            content_type = 'genres'
        elif getCondVisibility('Container.Content(files)'):
            content_type = 'files'
    # last resort: try to determine type by the listitem properties
    if not content_type and (containerprefix or getCondVisibility('Window.IsActive(movieinformation)')):
        if getCondVisibility('!String.IsEmpty(%sListItem.DBTYPE)' % containerprefix):
            content_type = xbmc.getInfoLabel('%sListItem.DBTYPE' % containerprefix) + 's'
        elif getCondVisibility('!String.IsEmpty(%sListItem.Property(DBTYPE))' % containerprefix):
            content_type = xbmc.getInfoLabel('%sListItem.Property(DBTYPE)' % containerprefix) + 's'
        elif getCondVisibility('String.Contains(%sListItem.FileNameAndPath,playrecording) | '
                                    'String.Contains(%sListItem.FileNameAndPath,tvtimer)'
                                    % (containerprefix, containerprefix)):
            content_type = 'tvrecordings'
        elif getCondVisibility('String.Contains(%sListItem.FileNameAndPath,launchpvr)' % (containerprefix)):
            content_type = 'tvchannels'
        elif getCondVisibility('String.Contains(%sListItem.FolderPath,pvr://channels)' % containerprefix):
            content_type = 'tvchannels'
        elif getCondVisibility('String.Contains(%sListItem.FolderPath,flix2kodi) + String.Contains(%sListItem.Genre,Series)'
                                    % (containerprefix, containerprefix)):
            content_type = 'tvshows'
        elif getCondVisibility('String.Contains(%sListItem.FolderPath,flix2kodi)' % (containerprefix)):
            content_type = 'movies'
        elif getCondVisibility('!String.IsEmpty(%sListItem.Artist) + String.IsEqual(%sListItem.Label,%sListItem.Artist)'
                                    % (containerprefix, containerprefix, containerprefix)):
            content_type = 'artists'
        elif getCondVisibility('!String.IsEmpty(%sListItem.Album) + String.IsEqual(%sListItem.Label,%sListItem.Album)'
                                    % (containerprefix, containerprefix, containerprefix)):
            content_type = 'albums'
        elif getCondVisibility('!String.IsEmpty(%sListItem.Artist) + !String.IsEmpty(%sListItem.Album)'
                                    % (containerprefix, containerprefix)):
            content_type = 'songs'
        elif getCondVisibility('!String.IsEmpty(%sListItem.TvShowTitle) + '
                                    'String.IsEqual(%sListItem.Title,%sListItem.TvShowTitle)'
                                    % (containerprefix, containerprefix, containerprefix)):
            content_type = 'tvshows'
        elif getCondVisibility('!String.IsEmpty(%sListItem.Property(TotalEpisodes))' % (containerprefix)):
            content_type = 'tvshows'
        elif getCondVisibility('!String.IsEmpty(%sListItem.TvshowTitle) + !String.IsEmpty(%sListItem.Season)'
                                    % (containerprefix, containerprefix)):
            content_type = 'episodes'
        elif getCondVisibility('String.IsEmpty(%sListItem.TvshowTitle) + !String.IsEmpty(%sListItem.Year)'
                                    % (containerprefix, containerprefix)):
            content_type = 'movies'
        elif getCondVisibility('String.Contains(%sListItem.FolderPath,movies)' % containerprefix):
            content_type = 'movies'
        elif getCondVisibility('String.Contains(%sListItem.FolderPath,shows)' % containerprefix):
            content_type = 'tvshows'
        elif getCondVisibility('String.Contains(%sListItem.FolderPath,episodes)' % containerprefix):
            content_type = 'episodes'
        elif getCondVisibility('!String.IsEmpty(%sListItem.Property(ChannelLogo))' % (containerprefix)):
            content_type = 'tvchannels'
    return content_type

def recursivedeletedir(path):
    success = True
    path = tryencode(path)
    dirs, files = xbmcvfs.listdir(path)
    for file in files:
        success = xbmcvfs.delete(os.path.join(path, file))
    for directory in dirs:
        success = recursivedeletedir(os.path.join(path, directory))
    success = xbmcvfs.rmdir(path)
    return success

if sys.version_info.major == 3:
    def preparewinprops(details, prefix='SkinUtils.ListItem.'):
        items = []
        if details:
            for key, value in list(details.items()):
                if value or value == 0:
                    key = '%s%s' % (prefix, key)
                    key = key.lower()
                    if isinstance(value, (bytes, str)):
                        items.append((key, value))
                    elif isinstance(value, int):
                        items.append((key, '%s' % value))
                    elif isinstance(value, float):
                        items.append((key, '%.1f' % value))
                    elif isinstance(value, dict):
                        for key2, value2 in list(value.items()):
                            if isinstance(value2, (bytes, str)):
                                items.append(('%s.%s' % (key, key2), value2))
                    elif isinstance(value, list):
                        list_strings = []
                        for listvalue in value:
                            if isinstance(listvalue, (bytes, str)):
                                list_strings.append(listvalue)
                        if list_strings:
                            items.append((key, ' / '.join(list_strings)))
                        elif len(value) == 1 and isinstance(value[0], (bytes, str)):
                            items.append((key, value))
        return items
else:
    def preparewinprops(details, prefix=u'SkinUtils.ListItem.'):
        items = []
        if details:
            for key, value in details.items():
                if value or value == 0:
                    key = u"%s%s" % (prefix, key)
                    key = key.lower()
                    if isinstance(value, (str, unicode)):
                        items.append((key, value))
                    elif isinstance(value, int):
                        items.append((key, '%s' % value))
                    elif isinstance(value, float):
                        items.append((key, '%.1f' % value))
                    elif isinstance(value, dict):
                        for key2, value2 in value.items():
                            if isinstance(value2, (str, unicode)):
                                items.append((u'%s.%s' % (key, key2), value2))
                    elif isinstance(value, list):
                        list_strings = []
                        for listvalue in value:
                            if isinstance(listvalue, (str, unicode)):
                                list_strings.append(trydecode(listvalue))
                        if list_strings:
                            items.append((key, u' / '.join(list_strings)))
                        elif len(value) == 1 and isinstance(value[0], (str, unicode)):
                            items.append((key, value))
        return items

def mergedict(dict_a, dict_b, allow_overwrite=False):
    if not dict_a and dict_b:
        return dict_b
    if not dict_b:
        return dict_a
    result = dict_a.copy()
    if sys.version_info.major == 3:
        for key, value in list(dict_b.items()):
            if (allow_overwrite or not key in dict_a or not dict_a[key]) and value:
                result[key] = value
    else:
        for key, value in dict_b.items():
            if (allow_overwrite or not key in dict_a or not dict_a[key]) and value:
                result[key] = value
    return result

def cleanstring(text):
    text = text.strip("'\"")
    text = text.strip()
    return text

def getCondVisibility(text):
    # temporary solution: check if strings needs to be adjusted for backwards compatability
    if KODI_VERSION < 17:
        text = text.replace('Integer.IsGreater', 'IntegerGreaterThan')
        text = text.replace('String.Contains', 'SubString')
        text = text.replace('String.IsEqual', 'StringCompare')
    return xbmc.getCondVisibility(text)
