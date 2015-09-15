#!/usr/bin/python
# -*- coding: utf-8 -*-
'''
Created on 2015-09-14

@author: Elem

'''


from common import SyncConf
from utils import SyncFiles

from isync_logger import logger_init
LOGGER = logger_init('pyisync.isync_server')



class SyncServer(object):
    """Real-time sync server
    """

    def __init__(self):
        """
        Constructor
        """
        self.sync_files = SyncFiles()

    def start(self):
        """启动实时同步配置文件接受端"""
        # 初始化rsync配置文件



