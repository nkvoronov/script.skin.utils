#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
import sys
import xbmc
import xbmcvfs
import xbmcgui
import xbmcaddon
from operator import itemgetter

from .utils import ADDON_ID, setlog, kodijson

class PVRFavourites:
    typepvr = None
    skinstring = None
    channelid = None
    
    def __init__(self, *args, **kwargs):
        self.addon = xbmcaddon.Addon(ADDON_ID)
        self.win = xbmcgui.Window(10000)

    def __del__(self):
        del self.win
        del self.addon
        
    def getchannelslist(self):
        listitems = []
        if self.typepvr == '0':
            channels = kodijson('PVR.GetChannels', {"channelgroupid": "alltv", "properties": [ "thumbnail", "channeltype", "hidden", "locked",  "lastplayed" ]})
        else:
            channels = kodijson('PVR.GetChannels', {"channelgroupid": "allradio", "properties": [ "thumbnail", "channeltype", "hidden", "locked",  "lastplayed" ]})
        for item in sorted(channels, key=itemgetter('channelid')):            
            channelid = item['channelid']
            channeltype = item['channeltype']
            name = item['label']
            icon = item['thumbnail']
            if self.typepvr == '0':
                channeltype = self.addon.getLocalizedString(32038)
            else:
                channeltype = self.addon.getLocalizedString(32039)
            listitem = xbmcgui.ListItem(label=name, label2=str(channelid) + ' (' + channeltype + ')')
            listitem.setArt({'icon':'DefaultAddonImages.png', 'thumb':icon})
            listitem.setProperty('channelid', str(channelid))
            listitems.append(listitem)
        return listitems
        
    def select(self):
        if self.typepvr == '0':
            header = self.addon.getLocalizedString(32034)
        else:
            header = self.addon.getLocalizedString(32035)
        channelslist = self.getchannelslist()
        listitem = xbmcgui.ListItem(xbmc.getLocalizedString(231),xbmc.getLocalizedString(24040))
        listitem.setArt({'icon':'DefaultAddonNone.png'})
        listitem.setProperty('channelid', '0')
        channelslist.insert(0, listitem)
        num = xbmcgui.Dialog().select(header, channelslist, useDetails=True)
        if num == 0:
            xbmc.executebuiltin('Skin.Reset(%s)' % (self.skinstring + '.label'))
            xbmc.executebuiltin('Skin.Reset(%s)' % (self.skinstring + '.icon'))
            xbmc.executebuiltin('Skin.Reset(%s)' % (self.skinstring + '.channelid'))
        elif num > 0:
            item = channelslist[num]
            name = item.getLabel()
            icon = item.getArt('thumb')
            channelid = item.getProperty('channelid')
            xbmc.executebuiltin('Skin.SetString(%s,%s)' % ((self.skinstring + '.label'), name))
            xbmc.executebuiltin('Skin.SetString(%s,%s)' % ((self.skinstring + '.icon'), icon))
            xbmc.executebuiltin('Skin.SetString(%s,%s)' % ((self.skinstring + '.channelid'), channelid))
        
    def update(self):
        result = kodijson('PVR.GetChannelDetails', {"channelid": self.channelid, "properties" : [ "broadcastnow" ]})
        return result
        
    def play(self):
        result = kodijson('Player.Open', {"item": { "channelid": self.channelid }})
        return result