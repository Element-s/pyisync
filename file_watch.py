#!/usr/bin/python
# -*- coding: utf-8 -*-
'''
Created on 2015-9-14

@author: Elem
'''
import re
import time
import threading
import subprocess
from collections import deque

from  pyinotify import  WatchManager, ThreadedNotifier, \
        ProcessEvent, ExcludeFilter, IN_DELETE, IN_CREATE, \
        IN_CLOSE_WRITE, IN_MOVED_FROM, IN_MOVED_TO

from utils import SyncFiles
from common import SyncConf
from isync_logger import logger_init
LOGGER = logger_init('pyisync.sync_utils')


class RetryThread(threading.Thread):
    """ sync retry thread
    """

    def __init__(self, name, retryq, remote_ip_lst=None,
                 retry_interval=120, crontab=3600):
        """ init func

        @param name: thread name
        @type name: str
        @param retryq: retry cmf queue
        @type retryq: Queue
        @param retry_interval: retry interval time
        @type retry_interval: int
        @param crontab: full sync crontab, default 1 hour
        @type crontab: int
        """
        threading.Thread.__init__(self, name=name)
        self.retryq = retryq
        if remote_ip_lst is None:
            self.remote_ip_lst = []
        self.remote_ip_lst = remote_ip_lst
        self.retry_interval = retry_interval
        self.crontab_interval = crontab
        self.crontab_start = int(time.time()) # 定时开始时间
        self._stop_event = threading.Event()
        self.full_threads = {}

    def stop(self):
        """
        Stop retry's loop. Join the thread.
        """
        LOGGER.info('Thread %s stop', self.name)
        self._stop_event.set()
        threading.Thread.join(self, 8)

    def run(self):
        self.loop()

    def loop(self):
        """ execute sync cmd loop
        """
        while not self._stop_event.isSet():
            try:
                now_time = int(time.time())
                if self.retryq.empty():
                    if now_time - self.crontab_start > self.crontab_interval:
                        # full sync
                        self.crontab_start = now_time
                        LOGGER.info('Start files full sync!peer ip:%s',
                                    str(self.remote_ip_lst))
                        for remote_ip in self.remote_ip_lst:
                            full_thread = self.full_threads.get(remote_ip)
                            if full_thread is not None \
                            and full_thread.isAlive():
                                full_thread.stop()
                                self.full_threads[remote_ip] = None
                            self.full_threads[remote_ip] = FullSyncThread(remote_ip)
                            self.full_threads[remote_ip].setDaemon(True)
                            self.full_threads[remote_ip].start()
                    time.sleep(0.5)
                else:
                    sync_dict = self.retryq.get(True)
                    old_time = sync_dict['time']
                    if now_time - old_time > self.retry_interval:
                        sync_cmd = sync_dict['time']
                        process = subprocess.Popen(sync_cmd, shell=True,
                                                   stderr=subprocess.PIPE)
                        retcode = process.wait()
                        if retcode != 0:
                            LOGGER.warning('Retry cmd failed:%s', sync_cmd)
                            LOGGER.warning('execute cmd failed:%s',
                                           process.stderr.read())
                    self.retryq.task_done()
            except Exception, exp:
                LOGGER.warning("Retry thead exception: %s", str(exp))
            finally:
                time.sleep(0.01)



class SyncThreadManager(object):
    """ sync thread manager, create and manage sync threads
    """
    def __init__(self, thread_num=5, cond=None, eventq=None, retryq=None,
                 remote_ip_lst=None):
        self.threads = []
        self.__init_thread_pool(thread_num, cond, eventq,
                                retryq, remote_ip_lst)

    def __init_thread_pool(self, thread_num, cond, eventq, retryq, remote_ip_lst):
        """ init thread pool
        """
        for i in range(thread_num):
            thread_name = "syncthread%d" % i
            self.threads.append(SyncThread(thread_name, cond=cond,
                                           eventq=eventq,
                                           retryq=retryq,
                                           remote_ip_lst=remote_ip_lst))

    def start_all(self):
        """ start all sync threads
        """
        for item in self.threads:
            item.setDaemon(True)
            item.start()

    def wait_allcomplete(self):
        """ wait all threads finished
        """
        for item in self.threads:
            if item.isAlive():
                item.join()

    def stop_all(self):
        """ stop all threads
        """
        for item in self.threads:
            if item.isAlive():
                item.stop()


class SyncThread(threading.Thread):
    """
    Sync cmd thread ,get event from sync queue.(consumer thread)
    When sync failed, insert event into retry queue.
    """

    def __init__(self, name, **kwargs):
        threading.Thread.__init__(self, name=name)
        self.my_init(**kwargs)

    def my_init(self, cond=None, eventq=None, retryq=None, remote_ip_lst=None):
        """init vars

        @param cond: condition var
        @type cond: threading.Condition
        @param eventq: event queue
        @type eventq: collections.deque
        @param retryq: retry queue
        @type retryq: Queue.Queue
        """
        self.cond = cond
        self.eventq = eventq
        self.retryq = retryq # 同步重试命令队列
        self.remote_ip_lst = remote_ip_lst
        self._stop_event = threading.Event()
        self.sync_files = SyncFiles()
        self.encrypt_set = self.sync_files.encrypt_set


    def sync_file(self, event):
        """sync file or directory

        @param event: event
        @type event: pyinotify.Event
        """
        sync_cmds = []
        if event.mask & (IN_DELETE | IN_MOVED_FROM):
            # get sync delete remote file cmd
            for remote_ip in self.remote_ip_lst:
                sync_cmd = self.sync_files.combine_del_cmd(remote_ip,
                                                           event.pathname,
                                                           event.dir)
                sync_cmds.append(sync_cmd)
        else:
            # get sync create or modify file cmd
            is_crypt = self.sync_files.is_encrypt_file(event.pathname,
                                                     self.encrypt_set)
            for remote_ip in self.remote_ip_lst:
                sync_cmd = self.sync_files.combine_other_cmd(remote_ip,
                                                             event.pathname,
                                                             event.dir,
                                                             is_crypt)
                sync_cmds.append(sync_cmd)
        LOGGER.debug('sync_cmds: %s', sync_cmds)
        for sync_cmd in sync_cmds:
            if sync_cmd:
                process = subprocess.Popen(sync_cmd, shell=True,
                                        stderr=subprocess.PIPE)
                retcode = process.wait()
                if retcode != 0:
                    LOGGER.warning('sync failed:%s.Insert cmd into retry queue!',
                                 process.stderr.read())
                    sync_dict = {}
                    sync_dict['cmd'] = sync_cmd
                    sync_dict['time'] = int(time.time())
                    self.retryq.put(sync_dict)

    def stop(self):
        """
        Stop sync's loop. Join the thread.
        """
        LOGGER.info('Thread %s stop', self.name)
        self._stop_event.set()
        self.cond.acquire()
        self.cond.notify_all()
        self.cond.release()
        threading.Thread.join(self, 8)

    def loop(self):
        while not self._stop_event.isSet():
            self.cond.acquire()
            try:
                if not self.eventq:
                    LOGGER.debug("Nothing in queue, sync consumer %s is waiting.",
                                 self.name)
                    self.cond.wait()
                    LOGGER.debug("Producer added something to queue and notified"
                                " the consumer %s", self.name)
                else:
                    event = self.eventq.popleft()
                    self.cond.notify()
                    self.sync_file(event)
                    LOGGER.debug("%s is consuming. %s in the queue is consumed!/n" \
                        % (self.getName(), event.pathname))
            finally:
                self.cond.release()
                time.sleep(0.01)

        LOGGER.info("Thread %s exit monitoring", self.name)
        while 1:
            self.cond.acquire()
            try:
                if not self.eventq:
                    self.cond.notifyAll()
                    time.sleep(0.5)
                    break
                else:
                    event = self.eventq.popleft()
                    self.sync_file(event)
                    time.sleep(0.01)
                    LOGGER.debug("%s:%s is consuming. %s in the queue is consumed!/n" \
                        % (time.ctime(), self.name, event.pathname))
                    self.cond.notify()
            finally:
                self.cond.release()

    def run(self):
        self.loop()


class EventHandler(ProcessEvent):
    """ files event's handler
    """
    def my_init(self, cond=None, eventq=None, sync_list=None):
        """init func

        @param cond: condition var
        @type cond: Condition
        @param eventq: event queeu
        @type eventq: deque
        """
        self.cond = cond
        self.eventq = eventq
        self.sync_list = sync_list

    def insert_events(self, event):
        """insert event into queue

        @param event: event
        @type event: pyinotify.Event
        """
        self.cond.acquire()

        try:
            if event.name is not None and event.name.startswith('.wh..wh.'):
                # '.wh..wh.user.1bbc' temp file not insert into queue
                return

            is_sync = False
            for sync_path in self.sync_list:
                if event.pathname.startswith(sync_path) \
                and event.pathname != (sync_path + '+') \
                and event.pathname != (sync_path + '-') \
                and event.pathname != (sync_path + '.lock'):
                    # '+’，'-'和'.lock' temp file，such as：
                    # /etc/passwd+ or /etc/passwd-，not sync;
                    # file in sync files list, set is_sync is True
                    pattern = "^%s\.\d+$" % sync_path
                    match_obj = re.match(pattern, event.pathname)
                    if match_obj is None:
                        # "/etc/group.9869" temp file, not sync
                        is_sync = True
                        break

            if is_sync:
                # filter event
                if event.dir and (event.mask & (IN_DELETE | IN_MOVED_FROM)):
                    eventq_tmp = deque()
                    eventq_tmp.extend(self.eventq)
                    dir_path = event.pathname + "/"
                    for elem in eventq_tmp:
                        if elem.pathname.startswith(dir_path):
                            # dir_path is parent, remove its sub file or dir event
                            LOGGER.debug("insert event pathname:%s, maskname:%s",
                                         elem.pathname, elem.maskname)
                            self.eventq.remove(elem)

                search_distance = 0
                is_insert = True
                for elem in self.eventq:
                    search_distance += 1
                    if search_distance < SyncConf.MAX_SEARCH_LENGTH \
                    and elem.pathname == event.pathname:
                        # update event's mask
                        LOGGER.debug("update event pathname:%s, maskname:%s",
                                         event.pathname, event.maskname)
                        elem.mask = event.mask
                        elem.maskname = event.maskname
                        is_insert = False
                        break

                if is_insert:
                    # insert into event
                    if len(self.eventq) == SyncConf.MAX_QUEUE_LENGTH:
                        self.cond.wait()
                    LOGGER.debug("insert event pathname:%s, maskname:%s",
                                 event.pathname, event.maskname)
                    self.eventq.append(event)
                    self.cond.notify()
        finally:
            self.cond.release()

    def process_event(self, event):
        """process event"""
        self.insert_events(event)

    def process_IN_CREATE(self, event):
        LOGGER.debug("CREATE event:%s", event.pathname)
        self.process_event(event)

    def process_IN_DELETE(self, event):
        LOGGER.debug("DELETE event:%s", event.pathname)
        self.process_event(event)

    def process_IN_CLOSE_WRITE(self, event):
        LOGGER.debug("CLOSE_WRITE event:%s", event.pathname)
        self.process_event(event)

    def process_IN_MOVED_FROM(self, event):
        LOGGER.debug("MOVED_FROM event:%s", event.pathname)
        self.process_event(event)

    def process_IN_MOVED_TO(self, event):
        LOGGER.debug("MOVED_TO event:%s", event.pathname)
        self.process_event(event)

    def process_default(self, event):
        LOGGER.debug('defalut eventmask:%s, pathname:%s' \
                    % (event.maskname, event.pathname))


class FullSyncThread(threading.Thread):
    """Sync full files thread
    """

    def __init__(self, remote_ip, name='FullSyncThread'):
        threading.Thread.__init__(self, name=name)
        self.remote_ip = remote_ip
        self.is_stoped = False

    def run(self):
        LOGGER.info('Start Full sync thread...')
        try:
            def full_sync(remote_ip):
                LOGGER.debug('Start full sync...')
                sync_files = SyncFiles()
                sync_files.sync_full_files(remote_ip)

            sub_thread = threading.Thread(target=full_sync,
                                    args=(self.remote_ip,))
            sub_thread.setDaemon(True)
            sub_thread.start()
        except Exception, exp:
            LOGGER.info('Full sync except')
            LOGGER.exception(exp)

        while not self.is_stoped:
            sub_thread.join(1)
            if not sub_thread.is_alive():
                break
        LOGGER.info('End Full sync thread...')

    def stop(self):
        LOGGER.info('Thread %s stop', self.name)
        self.is_stoped = True
        threading.Thread.join(self, 8)





