#!/usr/bin/python
# -*- coding: utf-8 -*-

import sys
import xbmcvfs
import xbmcgui
import xbmc
import xbmcaddon
import datetime
import time
import sqlite3
import json
from functools import reduce

from .utils import ADDON_ID, setlog

class SimpleCache(object):
    enable_mem_cache = True
    data_is_json = False
    global_checksum = None
    exit = False
    auto_clean_interval = datetime.timedelta(hours=4)
    win = None
    busy_tasks = []
    database = None

    def __init__(self):
        self.win = xbmcgui.Window(10000)
        self._monitor = xbmc.Monitor()
        self.checkcleanup()
        setlog('Initialized')

    def close(self):
        self.exit = True
        # wait for all tasks to complete
        while self.busy_tasks and not self._monitor.abortRequested():
            xbmc.sleep(25)
        del self.win
        del self._monitor
        setlog('Closed')

    def __del__(self):
        if not self.exit:
            self.close()

    def get(self, endpoint, checksum='', json_data=False):
        checksum = self.getchecksum(checksum)
        cur_time = self.gettimestamp(datetime.datetime.now())
        result = None
        # 1: try memory cache first
        if self.enable_mem_cache:
            result = self.getmemcache(endpoint, checksum, cur_time, json_data)

        # 2: fallback to database cache
        if result is None:
            result = self.getdbcache(endpoint, checksum, cur_time, json_data)

        return result

    def set(self, endpoint, data, checksum='', expiration=datetime.timedelta(days=30), json_data=False):
        task_name = 'set.%s' % endpoint
        self.busy_tasks.append(task_name)
        checksum = self.getchecksum(checksum)
        expires = self.gettimestamp(datetime.datetime.now() + expiration)

        # memory cache: write to window property
        if self.enable_mem_cache and not self.exit:
            self.setmemcache(endpoint, checksum, expires, data, json_data)

        # db cache
        if not self.exit:
            self.setdbcache(endpoint, checksum, expires, data, json_data)

        # remove this task from list
        self.busy_tasks.remove(task_name)

    def checkcleanup(self):
        cur_time = datetime.datetime.now()
        lastexecuted = self.win.getProperty('simplecache.clean.lastexecuted')
        if not lastexecuted:
            self.win.setProperty('simplecache.clean.lastexecuted', repr(cur_time))
        elif (eval(lastexecuted) + self.auto_clean_interval) < cur_time:
            # cleanup needed...
            self.docleanup()

    def getmemcache(self, endpoint, checksum, cur_time, json_data):
        result = None
        cachedata = self.win.getProperty(endpoint)

        if cachedata:
            if json_data or self.data_is_json:
                cachedata = json.loads(cachedata)
            else:
                cachedata = eval(cachedata)
            if cachedata[0] > cur_time:
                if not checksum or checksum == cachedata[2]:
                    result = cachedata[1]
        return result

    def setmemcache(self, endpoint, checksum, expires, data, json_data):
        cachedata = (expires, data, checksum)
        if json_data or self.data_is_json:
            cachedata_str = json.dumps(cachedata)
        else:
            cachedata_str = repr(cachedata)
        self.win.setProperty(endpoint, cachedata_str)


    def getdbcache(self, endpoint, checksum, cur_time, json_data):
        result = None
        query = 'SELECT expires, data, checksum FROM simplecache WHERE id = ?'
        cache_data = self.executesql(query, (endpoint,))
        if cache_data:
            cache_data = cache_data.fetchone()
            if cache_data and cache_data[0] > cur_time:
                if not checksum or cache_data[2] == checksum:
                    if json_data or self.data_is_json:
                        result = json.loads(cache_data[1])
                    else:
                        result = eval(cache_data[1])
                    # also set result in memory cache for further access
                    if self.enable_mem_cache:
                        self.setmemcache(endpoint, checksum, cache_data[0], result, json_data)
        return result

    def setdbcache(self, endpoint, checksum, expires, data, json_data):
        query = 'INSERT OR REPLACE INTO simplecache( id, expires, data, checksum) VALUES (?, ?, ?, ?)'
        if json_data or self.data_is_json:
            data = json.dumps(data)
        else:
            data = repr(data)
        self.executesql(query, (endpoint, expires, data, checksum))

    def docleanup(self):
        if self.exit or self._monitor.abortRequested():
            return
        self.busy_tasks.append(__name__)
        cur_time = datetime.datetime.now()
        cur_timestamp = self.gettimestamp(cur_time)
        setlog('Running cleanup...')
        if self.win.getProperty('simplecachecleanbusy'):
            return
        self.win.setProperty('simplecachecleanbusy', 'busy')

        query = 'SELECT id, expires FROM simplecache'
        for cache_data in self.executesql(query).fetchall():
            cache_id = cache_data[0]
            cache_expires = cache_data[1]

            if self.exit or self._monitor.abortRequested():
                return

            # always cleanup all memory objects on each interval
            self.win.clearProperty(cache_id)

            # clean up db cache object only if expired
            if cache_expires < cur_timestamp:
                query = 'DELETE FROM simplecache WHERE id = ?'
                self.executesql(query, (cache_id,))
                setlog('delete from db %s' % cache_id)

        # compact db
        self.executesql('VACUUM')

        # remove task from list
        self.busy_tasks.remove(__name__)
        self.win.setProperty('simplecache.clean.lastexecuted', repr(cur_time))
        self.win.clearProperty('simplecachecleanbusy')
        setlog('Auto cleanup done')

    def getdatabase(self):
        addon = xbmcaddon.Addon(ADDON_ID)
        dbpath = addon.getAddonInfo('profile')
        dbfile = xbmcvfs.translatePath('%s/simplecache.db' % dbpath)

        if not xbmcvfs.exists(dbpath):
            xbmcvfs.mkdirs(dbpath)
        del addon
        try:
            connection = sqlite3.connect(dbfile, timeout=30, isolation_level=None)
            connection.execute('SELECT * FROM simplecache LIMIT 1')
            return connection
        except Exception as error:
            # our database is corrupt or doesn't exist yet, we simply try to recreate it
            if xbmcvfs.exists(dbfile):
                xbmcvfs.delete(dbfile)
            try:
                connection = sqlite3.connect(dbfile, timeout=30, isolation_level=None)
                connection.execute(
                    """CREATE TABLE IF NOT EXISTS simplecache(
                    id TEXT UNIQUE, expires INTEGER, data TEXT, checksum INTEGER)""")
                return connection
            except Exception as error:
                setlog('Exception while initializing database: %s' % str(error), xbmc.LOGWARNING)
                self.close()
                return None

    def executesql(self, query, data=None):
        retries = 0
        result = None
        error = None
        # always use new db object because we need to be sure that data is available for other simplecache instances
        with self.getdatabase() as database:
            while not retries == 10 and not self._monitor.abortRequested():
                if self.exit:
                    return None
                try:
                    if isinstance(data, list):
                        result = database.executemany(query, data)
                    elif data:
                        result = database.execute(query, data)
                    else:
                        result = database.execute(query)
                    return result
                except sqlite3.OperationalError as error:
                    if 'database is locked' in error:
                        setlog('retrying DB commit...')
                        retries += 1
                        self._monitor.waitForAbort(0.5)
                    else:
                        break
                except Exception as error:
                    break
            setlog('database ERROR ! -- %s' % str(error), xbmc.LOGWARNING)
        return None

    @staticmethod
    def gettimestamp(date_time):
        return int(time.mktime(date_time.timetuple()))

    def getchecksum(self, stringinput):
        if not stringinput and not self.global_checksum:
            return 0
        if self.global_checksum:
            stringinput = '%s-%s' %(self.global_checksum, stringinput)
        else:
            stringinput = str(stringinput)
        return reduce(lambda x, y: x + y, map(ord, stringinput))


def usecache(cache_days=14):
    
    def decorator(func):

        def decorated(*args, **kwargs):
            method_class = args[0]
            method_class_name = method_class.__class__.__name__
            cache_str = "%s.%s" % (method_class_name, func.__name__)
            # cache identifier is based on positional args only
            # named args are considered optional and ignored
            for item in args[1:]:
                cache_str += u'.%s' % item
            cache_str = cache_str.lower()
            cachedata = method_class.cache.get(cache_str)
            global_cache_ignore = False
            try:
                global_cache_ignore = method_class.ignore_cache
            except Exception:
                pass
            if cachedata is not None and not kwargs.get('ignore_cache', False) and not global_cache_ignore:
                return cachedata
            else:
                result = func(*args, **kwargs)
                method_class.cache.set(cache_str, result, expiration=datetime.timedelta(days=cache_days))
                return result
        return decorated
    return decorator
