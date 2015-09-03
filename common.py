#!/usr/bin/python
# -*- coding: utf-8 -*-
'''
Created on 2014-10-24

@author: Elem

Common constants and global variables.
'''

class SyncConf(object):
    '''
    classdocs
    '''
    SYNC_CFG_FILE = 'sync_list.xml'
    RSYNC_CFG_FILE = 'rsyncd.conf'
    RSYNC_USER = 'rsyncuser'
    RSYNC_SECRET_FILE = 'rsyncd.secrets'
    SYNC_TMP_DIR = '/opt/synctmp'
    # rsync sync cmd
    RSYNC_CMD = "/bin/super bzyrsync -arz --timeout=30 --port=1532 --password-file=%s "
    RSYNCD_LOG = "/opt/log/rsyncd.log"
    RSYNCD_PID = "/opt/log/rsyncd.pid"
    RSYNCD_LOCK = "/opt/log/rsyncd.lock"
    RSYNC_PORT = 1532

    # rar encrypt cmd
    RAR_ARCHIVE_CMD = "/bin/rar a -hp\"123456\" "
    # rar decrypt cmd
    RAR_EXTRA_CMD = "/bin/rar -hp\"123456\" -o+ x "

    MAX_SEARCH_LENGTH = 20; # max search length
    MAX_QUEUE_LENGTH = 1000; # max event queue length

