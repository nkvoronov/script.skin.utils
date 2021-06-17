#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
import sys
import xbmc
import xbmcvfs
import xbmcgui
import xbmcaddon

from .utils import ADDON_ID, setlog, kodijson, getCondVisibility

class WinProperties:
    
    def __init__(self):
        self.addon = xbmcaddon.Addon(ADDON_ID)
        self.win = xbmcgui.Window(10000)        

    def __del__(self):
        del self.win
        del self.addon
        
    def update(self):
        # GET TOTAL ADDONS COUNT
        addons_count = len(kodijson('Addons.GetAddons'))
        self.win.setProperty('SkinUtils.TotalAddons', '%s' % addons_count)

        addontypes = []
        addontypes.append(('executable', 'SkinUtils.TotalProgramAddons'))
        addontypes.append(('video', 'SkinUtils.TotalVideoAddons'))
        addontypes.append(('audio', 'SkinUtils.TotalAudioAddons'))
        addontypes.append(('image', 'SkinUtils.TotalPicturesAddons'))
        addontypes.append(('game', 'SkinUtils.TotalGamesAddons'))
        for addontype in addontypes:
            media_array = kodijson('Addons.GetAddons', {"content": addontype[0]})
            self.win.setProperty(addontype[1], str(len(media_array)))

        # GET FAVOURITES COUNT
        favs = kodijson('Favourites.GetFavourites')
        if favs:
            self.win.setProperty('SkinUtils.TotalFavourites', '%s' % len(favs))
            
        # GET TV CHANNELS COUNT
        if getCondVisibility('Pvr.HasTVChannels'):
            tv_channels = kodijson('PVR.GetChannels', {"channelgroupid": "alltv"})
            self.win.setProperty('SkinUtils.TotalTVChannels', '%s' % len(tv_channels))
            
        # GET MOVIE SETS COUNT
        movieset_movies_count = 0
        moviesets = kodijson('VideoLibrary.GetMovieSets')
        for item in moviesets:
            for item in kodijson('VideoLibrary.GetMovieSetDetails', {"setid": item["setid"]}):
                movieset_movies_count += 1
        self.win.setProperty('SkinUtils.TotalMovieSets', '%s' % len(moviesets))
        self.win.setProperty('SkinUtils.TotalMoviesInSets', '%s' % movieset_movies_count)

        # GET RADIO CHANNELS COUNT
        if getCondVisibility('Pvr.HasRadioChannels'):
            radio_channels = kodijson('PVR.GetChannels', {"channelgroupid": "allradio"})
            self.win.setProperty('SkinUtils.TotalRadioChannels', '%s' % len(radio_channels))