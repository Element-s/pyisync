#!/usr/bin/python
# -*- coding: utf-8 -*-
'''
Created on 2015-09-14

@author: Elem

'''

import os
import threading
from collections import deque
from Queue import Queue
import traceback

from  pyinotify import  WatchManager, ThreadedNotifier, ExcludeFilter, \
                        IN_DELETE, IN_CREATE, IN_CLOSE_WRITE, IN_MOVED_TO, \
                        IN_MOVED_FROM


from file_watch import EventHandler, SyncThreadManager, \
                RetryThread
from common import SyncConf
from utils import SyncFiles

from isync_logger import logger_init
LOGGER = logger_init('pyisync.isync_client')



class SyncClient(object):
    """Real-time sync client
    """

    def __init__(self, remote_ip_lst, local_ip=''):
        """
        Constructor
        """
        self.sync_files = SyncFiles()
        self.local_ip = local_ip
        self.remote_ip_lst = remote_ip_lst
        self.client_notifier = None
        self.sync_manager = None
        self.retry_thread = None
        self.server_notifier = None
        self.full_sync_thread = None

    def __watch_thread(self, root_lst, sync_list, cond, eventq):
        """
        初始化客户端监控文件变化的同步线程，根据同步的根目录列表和
        需要同步的文件目录白名单，获取需要监控的目录列表以及监控排除的文件列表添加到INotifier中

        @param root_lst: 监控的根目录列表
        @type root_lst: tuple
        @param sync_list: 需要同步的文件和目录的列表
        @type sync_list: tuple
        @param cond: 线程同步条件变量
        @type cond: threading.Condition
        @param eventq: 保存文件变化的事件队列
        @type eventq: pyinotify.Event
        @return: 初始化后的监控线程
        @rtype: pyinotify.ThreadedNotifier
        """
        wm = WatchManager()
        mask = IN_DELETE | IN_CLOSE_WRITE | IN_CREATE | IN_MOVED_FROM | IN_MOVED_TO
        thread_notifier = ThreadedNotifier(wm,
                        EventHandler(cond=cond, eventq=eventq,
                                     sync_list=sync_list),
                        read_freq=10, timeout=9)
        thread_notifier.coalesce_events() # Enable coalescing of events
        watch_lst = [] # INotifier watch direcory list
        exclude_lst = [] # INotifier exclude directory list
        LOGGER.debug('root:%s', str(root_lst))
        LOGGER.debug('sublist:%s', str(sync_list))
        for root_path in root_lst:
            # add root directory to watch list
            watch_lst.append(root_path['name'])
            if not root_path['is_all']:
                # get exclude sub direcory list
                for dirpath, _, _ in os.walk(root_path['name']):
                    if dirpath != root_path['name']:
                        for file_path in sync_list:
                            is_exclude = True
                            if file_path.startswith(dirpath) \
                            or dirpath.startswith(file_path):
                                # 遍历的目录为同步列表文件的父目录，
                                # 或者同步文件列表下的子目录，都不添加到排除目录列表
                                LOGGER.debug('dirpath:%s', dirpath)
                                LOGGER.debug('file_path:%s', file_path)
                                is_exclude = False
                                break
                        if is_exclude:
                            exclude_lst.append(dirpath)

        LOGGER.debug('watchlist:%s', str(watch_lst))
        LOGGER.debug('excludelist:%s', str(exclude_lst))
        excl = ExcludeFilter(exclude_lst)
        # 设置受监视的事件,（rec=True, auto_add=True）为递归处理
        wm_dict = wm.add_watch(watch_lst, mask, rec=True, auto_add=True,
                     exclude_filter=excl)
        LOGGER.debug('client monitor lst:%s', str(wm_dict))
        return thread_notifier

    def start_monitor(self):
        """
        初始化发送端，对监控的配置文件进行监控并发送到对端
        """
        try:
            LOGGER.info('Start client monitor threads...')
            if self.client_notifier is not None and self.client_notifier.isAlive():
                self.client_notifier.stop()
                self.client_notifier = None
            if self.retry_thread is not None and self.retry_thread.isAlive():
                self.retry_thread.stop()
                self.retry_thread = None
            if self.sync_manager is not None:
                self.sync_manager.stop_all()
                self.sync_manager = None

            # 初始化监控信息
            cond = threading.Condition()
            eventq = deque()
            retryq = Queue(SyncConf.MAX_QUEUE_LENGTH)
            monitor_list = self.sync_files.watch_lst
            sync_lst = self.sync_files.sync_lst

            # 初始化线程
            self.client_notifier = self.__watch_thread(tuple(monitor_list),
                                                    tuple(sync_lst),
                                                    cond, eventq)
            self.sync_manager = SyncThreadManager(thread_num=3, cond=cond,
                                    eventq=eventq, retryq=retryq,
                                    remote_ip_lst=self.remote_ip_lst)
            self.retry_thread = RetryThread('retrythread', retryq,
                                            self.remote_ip_lst)

            # 设置并启动线程
            self.client_notifier.setDaemon(True)
            self.retry_thread.setDaemon(True)
            self.client_notifier.start()
            self.sync_manager.start_all()
            self.retry_thread.start()
            self.client_notifier.join()
        except Exception, exp:
            LOGGER.warning('real-time monitor thread except:%s', str(exp))
            LOGGER.warning(traceback.format_exc())
            exit()



