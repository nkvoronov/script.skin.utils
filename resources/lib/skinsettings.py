#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
import sys
import xbmc
import xbmcvfs
import xbmcgui
import xbmcaddon
import xml.etree.ElementTree as xmltree
import time
from xml.dom.minidom import parse

from .utils import ADDON_ID, trydecode, tryencode, getCondVisibility
from .dialogselect import DialogSelect

class SkinSettings:
    skinsettings = {}

    def __init__(self):
        self.win = xbmcgui.Window(10000)
        self.addon = xbmcaddon.Addon(ADDON_ID)
        self.skinsettings = self.getskinsettings()
        self.skin_constants, self.skin_variables = self.getskinconstants()

    def __del__(self):
        del self.win
        del self.addon

    def writeskinconstants(self, constants=None, variables=None):
        if sys.version_info.major == 3:
            addonpath = trydecode(xbmcvfs.translatePath(tryencode(os.path.join('special://skin/', 'addon.xml'))))
        else:
            addonpath = trydecode(xbmc.translatePath(tryencode(os.path.join('special://skin/', 'addon.xml'))))
        addon = xmltree.parse(addonpath)
        extensionpoints = addon.findall('extension')
        for extensionpoint in extensionpoints:
            if extensionpoint.attrib.get('point') == 'xbmc.gui.skin':
                resolutions = extensionpoint.findall('res')
                for resolution in resolutions:
                    if sys.version_info.major == 3:
                        includes_file = trydecode(xbmcvfs.translatePath(
                            tryencode(os.path.join(
                                'special://skin/',
                                trydecode(
                                    resolution.attrib.get('folder')),
                                'script-skin_utils_service-includes.xml')))) #???
                    else:
                        includes_file = trydecode(xbmc.translatePath(
                            tryencode(os.path.join(
                                'special://skin/',
                                trydecode(
                                    resolution.attrib.get("folder")),
                                'script-skin_utils_service-includes.xml')))) #???
                    tree = xmltree.ElementTree(xmltree.Element('includes'))
                    root = tree.getroot()
                    if constants:
                        for key, value in list(constants.items()):
                            if value:
                                child = xmltree.SubElement(root, 'constant')
                                child.text = value
                                child.attrib['name'] = key
                                # also write to skin strings
                                xbmc.executebuiltin(
                                    'Skin.SetString(%s,%s)' %
                                    (tryencode(key), tryencode(value)))
                    if variables:
                        for key, value in list(variables.items()):
                            if value:
                                child = xmltree.SubElement(root, 'variable')
                                child.attrib['name'] = key
                                child2 = xmltree.SubElement(child, 'value')
                                child2.text = value
                    self.indentxml(tree.getroot())
                    xmlstring = xmltree.tostring(tree.getroot(), encoding='utf-8')
                    fileobj = xbmcvfs.File(includes_file, 'w')
                    fileobj.write(xmlstring)
                    fileobj.close()
        xbmc.executebuiltin('ReloadSkin()')

    @staticmethod
    def getskinconstants():
        all_constants = {}
        all_variables = {}
        if sys.version_info.major == 3:
            addonpath = trydecode(xbmcvfs.translatePath(tryencode(os.path.join('special://skin/', 'addon.xml'))))
        else:
            addonpath = trydecode(xbmc.translatePath(tryencode(os.path.join('special://skin/', 'addon.xml'))))

        addon = xmltree.parse(addonpath)
        extensionpoints = addon.findall('extension')
        for extensionpoint in extensionpoints:
            if extensionpoint.attrib.get('point') == 'xbmc.gui.skin':
                resolutions = extensionpoint.findall("res")
                for resolution in resolutions:
                    if sys.version_info.major == 3:
                        includes_file = trydecode(xbmcvfs.translatePath(
                            tryencode(os.path.join(
                                'special://skin/',
                                trydecode(
                                    resolution.attrib.get('folder')),
                                'script-skin_utils_service-includes.xml')))) #???
                    else:
                        includes_file = trydecode(xbmc.translatePath(
                            tryencode(os.path.join(
                                'special://skin/',
                                trydecode(
                                    resolution.attrib.get('folder')),
                                'script-skin_utils_service-includes.xml')))) #???

                    if xbmcvfs.exists(includes_file):
                        doc = parse(includes_file)
                        listing = doc.documentElement.getElementsByTagName('constant')
                        # constants
                        for item in listing:
                            name = trydecode(item.attributes['name'].nodeValue)
                            value = trydecode(item.firstChild.nodeValue)
                            all_constants[name] = value
                        # variables
                        listing = doc.documentElement.getElementsByTagName('variable')
                        for item in listing:
                            name = trydecode(item.attributes['name'].nodeValue)
                            value_item = item.getElementsByTagName('value')[0]
                            value = trydecode(value_item.firstChild.nodeValue)
                            all_variables[name] = value
        return all_constants, all_variables

    def updateskinconstants(self, new_constants):
        update_needed = False
        if new_constants:
            for key, value in list(new_constants.items()):
                if key in self.skin_constants:
                    if self.skin_constants.get(key) != value:
                        update_needed = True
                        self.skin_constants[key] = value
                else:
                    update_needed = True
                    self.skin_constants[key] = value
        if update_needed:
            self.writeskinconstants(self.skin_constants, self.skin_variables)

    def setskinconstant(self, setting='', window_header='', value=''):
        cur_values = self.skin_constants
        if not value:
            cur_value = cur_values.get(setting, "emptyconstant")
            value = self.setskinsetting(setting, window_header, '', cur_value)[0]
        result = {setting: value}
        self.updateskinconstants(result)

    def setskinconstants(self, settings, values):
        result = {}
        for count, setting in enumerate(settings):
            result[setting] = values[count]
        self.updateskinconstants(result)

    def setskinvariable(self, key, value):
        if self.skin_variables.get(key, '') != value:
            self.skin_variables[key] = value
            self.writeskinconstants(self.skin_constants, self.skin_variables)

    @staticmethod
    def getskinsettings():
        all_skinsettings = {}
        if sys.version_info.major == 3:
            settings_file = trydecode(xbmcvfs.translatePath('special://skin/extras/skinsettings.xml'))
        else:
            settings_file = trydecode(xbmc.translatePath('special://skin/extras/skinsettings.xml'))
        if xbmcvfs.exists(settings_file):
            doc = parse(settings_file)
            listing = doc.documentElement.getElementsByTagName('setting')
            for item in listing:
                skinsetting_id = trydecode(item.attributes['id'].nodeValue)
                if "$" in skinsetting_id:
                    skinsetting_id = trydecode(xbmc.getInfoLabel(skinsetting_id))
                if all_skinsettings.get(skinsetting_id):
                    skinsetting_values = all_skinsettings[skinsetting_id]
                else:
                    skinsetting_values = []
                skinsettingvalue = {}
                skinsettingvalue['value'] = trydecode(item.attributes['value'].nodeValue)
                # optional attributes
                for key in ['label', 'condition', 'description', 'default', 'icon', 'constantdefault']:
                    value = ''
                    try:
                        value = item.attributes[key].nodeValue
                        if '$' in value:
                            value = trydecode(xbmc.getInfoLabel(value))
                        else:
                            value = value
                    except Exception:
                        pass
                    skinsettingvalue[key] = value

                # optional onselect actions for this skinsetting value
                onselectactions = []
                for action in item.getElementsByTagName('onselect'):
                    selectaction = {}
                    selectaction['condition'] = trydecode(action.attributes['condition'].nodeValue)
                    command = action.firstChild.nodeValue
                    if '$' in command:
                        command = trydecode(xbmc.getInfoLabel(command))
                    else:
                        command = trydecode(command)
                    selectaction['command'] = command
                    onselectactions.append(selectaction)
                skinsettingvalue['onselectactions'] = onselectactions

                # optional multiselect options for this skinsetting value
                settingoptions = []
                for option in item.getElementsByTagName('option'):
                    settingoption = {}
                    for key in ['id', 'label', 'condition', 'description', 'default', 'icon', 'value']:
                        value = ''
                        try:
                            value = option.attributes[key].nodeValue
                            if value.startswith('$'):
                                value = trydecode(xbmc.getInfoLabel(value))
                            else:
                                value = trydecode(value)
                        except Exception:
                            pass
                        settingoption[key] = value
                    settingoptions.append(settingoption)
                skinsettingvalue['settingoptions'] = settingoptions

                skinsetting_values.append(skinsettingvalue)
                all_skinsettings[skinsetting_id] = skinsetting_values
        return all_skinsettings

    def setskinsetting(self, setting='', window_header='', sublevel='',
                         cur_value_label='', skip_skin_string=False, original_id='', cur_value=''):
        if not cur_value_label:
            cur_value_label = trydecode(xbmc.getInfoLabel('Skin.String(%s.label)' % setting))
        if not cur_value:
            cur_value = trydecode(xbmc.getInfoLabel('Skin.String(%s)' % setting))
        rich_layout = False
        listitems = []
        if sublevel:
            listitem = xbmcgui.ListItem(label='..')
            listitem.setProperty('icon', 'DefaultFolderBack.png')
            listitem.setProperty('value', '||BACK||')
            listitems.append(listitem)
            all_values = self.skinsettings.get(sublevel, [])
        elif original_id:
            all_values = self.skinsettings.get(original_id, [])
        else:
            all_values = self.skinsettings.get(setting, [])
        for item in all_values:
            if not item['condition'] or getCondVisibility(item['condition']):
                value = item['value']
                icon = item['icon']
                if icon:
                    rich_layout = True
                label = item['label']
                if '%' in label:
                    label = label % value
                if value == '||MULTISELECT||' or item['settingoptions']:
                    return self.multiselect(item['settingoptions'], window_header)
                listitem = xbmcgui.ListItem(label, label2=item['description'])
                listitem.setArt({'icon': icon})
                listitem.setProperty('value', value)
                listitem.setProperty('icon', icon)
                listitem.setProperty('description', item['description'])
                listitem.setProperty('onselectactions', repr(item['onselectactions']))
                listitems.append(listitem)

        # show select dialog
        dialog = DialogSelect('DialogSelect.xml', '', listing=listitems, windowtitle=window_header,
                              richlayout=rich_layout, autofocuslabel=cur_value_label)
        dialog.doModal()
        selected_item = dialog.result
        del dialog
        # process the results
        if selected_item:
            value = trydecode(selected_item.getProperty('value'))
            label = trydecode(selected_item.getLabel())
            if value.startswith('||SUBLEVEL||'):
                sublevel = value.replace('||SUBLEVEL||', '')
                self.setskinsetting(setting, window_header, sublevel)
            elif value == '||BACK||':
                self.setskinsetting(setting, window_header)
            else:
                if value == '||BROWSEIMAGE||':
                    value = self.saveskinimage(setting, True, label)
                if value == '||BROWSESINGLEIMAGE||':
                    value = self.saveskinimage(setting, False, label)
                if value == '||BROWSEMULTIIMAGE||':
                    value = self.saveskinimage(setting, True, label)
                if value == '||PROMPTNUMERIC||':
                    value = trydecode(xbmcgui.Dialog().input(label, cur_value, 1))
                if value == '||PROMPTSTRING||':
                    value = trydecode(xbmcgui.Dialog().input(label, cur_value, 0))
                if value == '||PROMPTSTRINGASNUMERIC||':
                    validinput = False
                    while not validinput:
                        try:
                            value = trydecode(xbmcgui.Dialog().input(label, cur_value, 0))
                            valueint = int(value)
                            validinput = True
                            del valueint
                        except Exception:
                            value = xbmcgui.Dialog().notification('Invalid input', 'Please enter a number...')

                # write skin strings
                if not skip_skin_string and value != '||SKIPSTRING||':
                    xbmc.executebuiltin('Skin.SetString(%s,%s)' %
                                    (tryencode(setting), tryencode(value)))
                    xbmc.executebuiltin('Skin.SetString(%s.label,%s)' %
                                    (tryencode(setting), tryencode(label)))
                # process additional actions
                onselectactions = selected_item.getProperty('onselectactions')
                if onselectactions:
                    for action in eval(onselectactions):
                        if not action['condition'] or getCondVisibility(action['condition']):
                            xbmc.executebuiltin(action['command'])
                return (value, label)
        else:
            return (None, None)

    def correctskinsettings(self):
        skinconstants = {}
        for settingid, settingvalues in list(self.skinsettings.items()):
            curvalue = trydecode(xbmc.getInfoLabel('Skin.String(%s)' % settingid))
            curlabel = trydecode(xbmc.getInfoLabel('Skin.String(%s.label)' % settingid))
            # first check if we have a sublevel
            if settingvalues and settingvalues[0]['value'].startswith('||SUBLEVEL||'):
                sublevel = settingvalues[0]['value'].replace('||SUBLEVEL||', '')
                settingvalues = self.skinsettings.get(sublevel)
            for settingvalue in settingvalues:
                value = settingvalue['value']
                label = settingvalue['label']
                if "%" in label:
                    label = label % value

                # only correct the label if value already set
                if value and value == curvalue:
                    xbmc.executebuiltin(
                        'Skin.SetString(%s.label,%s)' %
                        (tryencode(settingid), tryencode(label)))

                # set the default value if current value is empty
                if not (curvalue or curlabel):
                    if settingvalue["default"] and getCondVisibility(settingvalue['default']):
                        xbmc.executebuiltin(
                            'Skin.SetString(%s.label,%s)' %
                            (tryencode(settingid), tryencode(label)))
                        xbmc.executebuiltin(
                            'Skin.SetString(%s,%s)' %
                            (tryencode(settingid), tryencode(value)))
                        # additional onselect actions
                        for action in settingvalue['onselectactions']:
                            if action['condition'] and getCondVisibility(action['condition']):
                                command = action['command']
                                if '$' in command:
                                    command = xbmc.getInfoLabel(command)
                                xbmc.executebuiltin(tryencode(command))


                # process any multiselects
                for option in settingvalue['settingoptions']:
                    settingid = option["id"]
                    if (not xbmc.getInfoLabel('Skin.String(defaultset_%s)' % settingid) and option['default'] and
                            getCondVisibility(option['default'])):
                        xbmc.executebuiltin('Skin.SetBool(%s)' % settingid)
                    xbmc.executebuiltin('Skin.SetString(defaultset_%s,defaultset)' % settingid)

                # set the default constant value if current value is empty
                if (not curvalue and settingvalue['constantdefault'] and
                        getCondVisibility(settingvalue['constantdefault'])):
                    skinconstants[settingid] = value

        # update skin constants if needed only
        if skinconstants:
            self.updateskinconstants(skinconstants)

    def saveskinimage(self, skinstring='', multi_image=False, header='', allow_copy=False):
        cur_value = trydecode(xbmc.getInfoLabel('Skin.String(%s)' % skinstring))
        cur_value_org = trydecode(xbmc.getInfoLabel('Skin.String(%s.org)' % skinstring))

        if not multi_image:
            # single image (allow copy to addon_data)
            value = trydecode(xbmcgui.Dialog().browse(2, header, 'files', '', True, True, cur_value_org))
            if value and allow_copy:
                ext = value.split('.')[-1]
                newfile = ('special://profile/addon_data/%s/custom_images/%s.%s'
                           % (xbmc.getSkinDir(), skinstring + time.strftime('%Y%m%d%H%M%S', time.gmtime()), ext))
                if 'special://profile/addon_data/%s/custom_images/' % xbmc.getSkinDir() in cur_value:
                    xbmcvfs.delete(cur_value)
                xbmcvfs.copy(value, newfile)
                xbmc.executebuiltin('Skin.SetString(%s.org,%s)' % (tryencode(skinstring), tryencode(value)))
                value = newfile
        else:
            # multi image
            if not cur_value_org.startswith('$'):
                delim = '\\' if '\\' in cur_value_org else '/'
                curdir = cur_value_org.rsplit(delim, 1)[0] + delim
            else:
                curdir = ''
            value = trydecode(xbmcgui.Dialog().browse(0, header, 'files', '', True, True, curdir))
                                            
        return value

    def setskinshortcutsproperty(self, setting='', window_header='', property_name=''):
        cur_value = trydecode(xbmc.getInfoLabel(
            '$INFO[Container(211).ListItem.Property(%s)]' %
            property_name))
        cur_value_label = trydecode(xbmc.getInfoLabel(
            '$INFO[Container(211).ListItem.Property(%s.name)]' %
            property_name))
        if setting == '||IMAGE||':
            # select image
            label, value = self.selectimage(setting, allow_multi=True, windowheader=windowheader)
        if setting:
            # use skin settings select dialog
            value, label = self.setskinsetting(
                setting, window_header=window_header, sublevel='', cur_value_label=cur_value_label,
                skip_skin_string=True, cur_value=cur_value)
        else:
            # manually input string
            if not cur_value:
                cur_value = 'None'
            value = trydecode(xbmcgui.Dialog().input(window_header, cur_value, type=xbmcgui.INPUT_ALPHANUM))
            label = value
        #if label:
        #    from .skinshortcuts import set_skinshortcuts_property
        #    set_skinshortcuts_property(property_name, value, label)

    def selectimage(self, skinstring, allow_multi=True, windowheader='', resource_addon='', current_value=''):
        images = []
        if not windowheader:
            windowheader = self.addon.getLocalizedString(32026)
        if not current_value:
            current_value = trydecode(xbmc.getInfoLabel('Skin.String(%s.label)' % skinstring))

        # none option
        images.append((xbmc.getLocalizedString(231), '', xbmc.getLocalizedString(24040), 'DefaultAddonNone.png'))
        # custom single
        images.append((xbmc.getLocalizedString(561), '', self.addon.getLocalizedString(32027), 'DefaultFile.png'))
        # custom multi
        if allow_multi:
            images.append((xbmc.getLocalizedString(19076), '', self.addon.getLocalizedString(32021), 'DefaultFolder.png'))

        # backgrounds supplied in our special skinsettings.xml file
        skinimages = self.skinsettings
        if skinimages.get(skinstring):
            for item in skinimages[skinstring]:
                if not item['condition'] or getCondVisibility(item['condition']):
                    images.append((item['label'], item['value'], item['description'], item['icon']))

        # resource addon images
        if resource_addon:
            from .resourceaddons import getresourceimages
            images += getresourceimages(resource_addon)

        # create listitems
        listitems = []
        for label, imagepath, label2, icon in images:
            listitem = xbmcgui.ListItem(label=label, label2=label2)
            listitem.setArt({'icon': icon})
            listitem.setPath(imagepath)
            listitems.append(listitem)

        # show select dialog with choices
        dialog = DialogSelect('DialogSelect.xml', '', listing=listitems, windowtitle=windowheader, richlayout=True,
                              getmorebutton=resource_addon, autofocuslabel=current_value)
        dialog.doModal()
        result = dialog.result
        del dialog
        if isinstance(result, bool):
            if result:
                # refresh listing requested by getmore button
                return self.selectimage(skinstring, allow_multi, windowheader, resource_addon, current_value)
        elif result:
            label = trydecode(result.getLabel())
            if label == xbmc.getLocalizedString(561):
                # browse for single image
                custom_image = SkinSettings().saveskinimage(skinstring, False, self.addon.getLocalizedString(32027))
                if custom_image:
                    result.setPath(custom_image)
                else:
                    return self.selectimage()
            elif label == xbmc.getLocalizedString(19076):
                # browse for image path
                custom_image = SkinSettings().saveskinimage(skinstring, True, self.addon.getLocalizedString(32021))
                if custom_image:
                    result.setPath(custom_image)
                else:
                    return self.selectimage()
            # return values
            return (trydecode(result.getLabel()), trydecode(result.getPath()))
        # return empty values
        return ('', '')

    @staticmethod
    def multiselect(options, window_header=''):
        listitems = []
        for option in options:
            if not option["condition"] or getCondVisibility(option['condition']):
                listitem = xbmcgui.ListItem(label=option['label'], label2=option['description'])
                listitem.setProperty('id', option['id'])
                if getCondVisibility('Skin.HasSetting(%s)' % option['id']) or (not xbmc.getInfoLabel(
                        'Skin.String(defaultset_%s)' % option['id']) and getCondVisibility(option['default'])):
                    listitem.select(selected=True)
                listitems.append(listitem)
        # show select dialog
        dialog = DialogSelect('DialogSelect.xml', '', listing=listitems, windowtitle=window_header, multiselect=True)
        dialog.doModal()
        result = dialog.result
        if result:
            for item in result:
                if item.isSelected():
                    # option is enabled
                    xbmc.executebuiltin('Skin.SetBool(%s)' % item.getProperty('id'))
                else:
                    # option is disabled
                    xbmc.executebuiltin('Skin.Reset(%s)' % item.getProperty('id'))
            # always set additional prop to define the defaults
            xbmc.executebuiltin('Skin.SetString(defaultset_%s,defaultset)' % item.getProperty('id'))
        del dialog

    def indentxml(self, elem, level=0):
        text_i = '\n' + level * '\t'
        if len(elem):
            if not elem.text or not elem.text.strip():
                elem.text = text_i + '\t'
            if not elem.tail or not elem.tail.strip():
                elem.tail = text_i
            for elem in elem:
                self.indentxml(elem, level + 1)
            if not elem.tail or not elem.tail.strip():
                elem.tail = text_i
        else:
            if level and (not elem.tail or not elem.tail.strip()):
                elem.tail = text_i
