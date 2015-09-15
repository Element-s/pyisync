#!/usr/bin/python
# -*- coding: utf-8 -*-
'''
Created on 2015-09-14

@author: Elem

'''


from utils import SyncFiles, execute_cmd

from isync_logger import logger_init
LOGGER = logger_init('pyisync.isync_server')



class SyncServer(object):
    """Real-time sync server
    """

    def __init__(self, remote_ip_lst=None):
        """
        Constructor
        """
        self.sync_files = SyncFiles()
        if remote_ip_lst is None:
            self.remote_ip_lst = []
        self.remote_ip_lst = remote_ip_lst

    def start(self):
        """启动实时同步配置文件接受端"""
        # 初始化rsync配置文件
        self.sync_files.update_rsyncd_conf(self.remote_ip_lst)
        rsync_serv_cmd = ['rsync', '--daemon',
                           '--config=%s' % self.sync_files.rsync_cfg_path]
        execute_cmd(rsync_serv_cmd)


