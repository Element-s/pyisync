#!/usr/bin/python
# -*- coding: utf-8 -*-
'''
Created on 2015-9-14

@author: Elem
'''
import os
import subprocess
from xml.etree import ElementTree

from common import SyncConf
from isync_logger import logger_init
LOGGER = logger_init('hasync.sync_utils')


def daemonize():
    """Turn the process into daemon.

    Goes background and disables all i/o.
    """
    # launch new process, kill parent
    pid = os.fork()
    if pid != 0:
        os._exit(0)

    # start new session
    os.setsid()

    # stop i/o
    fd = os.open("/dev/null", os.O_RDWR)
    os.dup2(fd, 0)
    os.dup2(fd, 1)
    os.dup2(fd, 2)
    if fd > 2:
        os.close(fd)

def execute_cmd(cmdline, log_stdout=True, log_stderr=True, stdin=None):
    """execute cmdline
    """
    shell = False
    if isinstance(cmdline, basestring):
        shell = True
    proc = subprocess.Popen(cmdline,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                            stdin=stdin,
                            shell=shell)
    stdout, stderr = proc.communicate()
    LOGGER.info('cmd:%s, retcode:%s', cmdline, proc.returncode)
    if log_stdout and stdout:
        LOGGER.info('%s stdout:\n%s', cmdline, stdout)
    if log_stderr and stderr:
        LOGGER.error('%s stderr:\n%s', cmdline, stderr)
    return stdout, stderr, proc


class ParseCfgFile(object):
    '''
    Parse sync cfg file, get sync file list
    '''

    def __init__(self, cfg_file):
        self.tree = ElementTree.ElementTree()
        self.tree.parse(cfg_file)

    def get_watch_list(self):
        """Get watch list

        @return: watch directory list
        @rtype: list,如：[{'name':'/opt/etc', 'is_all':False}，
                        {'name':'/home', 'is_all':True}]
        """
        watch_list = []
        dir_nodes = self.tree.findall('directories/directory')
        for node in dir_nodes:
            dir_info = {}
            is_all = node.get('include')
            dir_info['name'] = node.get('name')
            if is_all == '*':
                dir_info['is_all'] = True
            else:
                dir_info['is_all'] = False
            watch_list.append(dir_info)
        return watch_list

    def get_sync_fileinfos(self):
        """Get sync files and directories information list

        @return: files and directories information list
        @rtype: list,如：[{'name':'/etc/passwd', 'isdir':False]},
                        {'name':'/home', 'isdir':True}]
        """
        dir_list = []
        dir_nodes = self.tree.findall('directories/directory')
        for node in dir_nodes:
            dir_name = node.get('name')
            dir_include = node.get('include')
            if dir_include == "*":
                # '*' is sync root directory
                dir_info = {}
                dir_info['name'] = dir_name
                dir_info['isdir'] = True
                dir_list.append(dir_info)
            else:
                # add sync sub directory or file
                for sub_node in list(node):
                    dir_info = {}
                    sub_name = sub_node.get('name')
                    dir_info['name'] = os.path.join(dir_name, sub_name.strip())
                    if sub_node.get('isdir') == "yes":
                        dir_info['isdir'] = True
                    else:
                        dir_info['isdir'] = False
                    dir_list.append(dir_info)
        return dir_list

    def get_sync_filelist(self):
        """Get sync files and directories list

        @return: files and directories list
        @rtype: list,如：['/etc/group', '/home']
        """
        sync_list = []
        dir_nodes = self.tree.findall('directories/directory')
        for node in dir_nodes:
            dir_name = node.get('name')
            dir_include = node.get('include')
            if dir_include == "*":
                # # '*' is sync root directory
                sync_list.append(dir_name)
            else:
                # add sync sub directory or file
                for sub_node in list(node):
                    sub_name = sub_node.get('name')
                    sync_list.append(os.path.join(dir_name, sub_name.strip()))
        return sync_list

    def get_encrypt_filelist(self):
        """ Get crypt sync files list

        @return:  crypt sync files list
        @rtype: list,如：['/etc/shadow']
        """
        crypt_list = []
        safe_nodes = self.tree.findall('safefiles/safefile')
        for node in safe_nodes:
            crypt_list.append(node.get('name'))
        return crypt_list


class SyncFiles(object):
    '''combine rsync's cmd
    '''

    def __init__(self):
        '''
        Constructor
        '''
        self.__init_cfg_file_path()
        self.parse_file = ParseCfgFile(self.file_path)
        self.watch_lst = self.parse_file.get_watch_list()
        self.sync_lst = self.parse_file.get_sync_filelist()
        self.sync_fileinfos = self.parse_file.get_sync_fileinfos()
        self.encrypt_set = set(self.parse_file.get_encrypt_filelist())

    def __init_cfg_file_path(self):
        cwd_dir = os.getcwd()
        self.cfg_dir = os.path.join(cwd_dir, 'syncconf')
        self.file_path = os.path.join(self.cfg_dir, SyncConf.SYNC_CFG_FILE)
        self.rsync_cfg_path = os.path.join(self.cfg_dir, SyncConf.RSYNC_CFG_FILE)
        self.rsync_secret_path = os.path.join(self.cfg_dir, SyncConf.RSYNC_SECRET_FILE)

    def get_watch_path(self, file_path):
        """Get file's root directory

        @param file_path: file path
        @return: file's root path
        """
        root_path = ""
        for dir_info in self.watch_lst:
            if file_path.startswith(dir_info['name']):
                root_path = dir_info['name']
                break
        return root_path

    def combine_del_cmd(self, remote_ip, file_path, is_dir=False):
        """ combine delete remote file or directory's cmd

        @param peer_ip: remote IP
        @param file_path: delete file path
        @param is_dir: is directory
        @return: combine cmd
        @rtype: str
        """
        sync_cmd = ""
        root_path = self.get_watch_path(file_path)
        if root_path:
            sync_cmd = SyncConf.RSYNC_CMD % self.rsync_secret_path
            dst_node = root_path[1:].replace('/', '_') # 远程模块名称
            sub_path = file_path[len(root_path) + 1:]
            pos = sub_path.find('/')
            while pos != -1:
                sync_cmd += " --include='%s'" % sub_path[:pos + 1]
                pos = sub_path.find('/', pos + 1)
            sync_cmd += " --include='%s" % sub_path
            if is_dir:
                sync_cmd += "/***"
            sync_cmd += "' --exclude='*' --delete %s/ " % root_path
            sync_cmd += "%s@%s::%s" % (SyncConf.RSYNC_USER, remote_ip, dst_node)
        return sync_cmd

    def combine_other_cmd(self, remote_ip, file_path, is_dir=False, is_encrypt=False):
        """combine create or modify file or directory's cmd

        @param peer_ip: remote IP
        @param file_path: delete file path
        @param is_dir: is directory
        @return: combine cmd
        @rtype: str
        """
        sync_cmd = ""
        if is_encrypt:
            # crypt files by rar cmd
            file_name = file_path.replace('/', '_')
            dst_path = "%s/%s.rar" % (SyncConf.SYNC_TMP_DIR, file_name)
            tar_cmd = "%s %s %s" % (SyncConf.RAR_ARCHIVE_CMD, dst_path, file_path)
            if os.path.exists(file_path):
                execute_cmd(tar_cmd, shell=True)
                file_path = dst_path

        root_path = self.get_watch_path(file_path)
        if root_path:
            dst_node = root_path[1:].replace('/', '_') # remote module name
            sync_cmd = SyncConf.RSYNC_CMD % self.rsync_secret_path
            sync_cmd = "cd %s && %s -R " % (root_path, sync_cmd)
            sync_cmd += ' .' + file_path[len(root_path):]
            if is_dir:
#                    sync_cmd += "/*"
                # for delete not empty sub directory
                sync_cmd += " --delete-excluded "
            sync_cmd += " %s@%s::%s" \
            % (SyncConf.RSYNC_USER, remote_ip, dst_node)
        return sync_cmd

    def sync_files(self, peer_ip, file_path, is_dir=False, is_encrypt=False):
        """ sync file or direcory to remote

        @param file_path: file or directory
        @type file_path: str
        @param is_encrypt: is encrypt
        @type is_encrypt: bool
        """
        if os.path.exists(file_path):
            # sync create or modify file to remote
            sync_cmd = self.combine_other_cmd(peer_ip, file_path, is_dir, is_encrypt)
        else:
            # delete file cmd from remote
            sync_cmd = self.combine_del_cmd(peer_ip, file_path, is_dir)

        LOGGER.debug('sync_file cmd: %s', sync_cmd)
        execute_cmd(sync_cmd, shell=True)

    def is_encrypt_file(self, file_name, encrypt_set):
        """ file is encrypt

        @param file_name: file name
        @param encrypt_set: encrypt files set
        @type encrypt_set: set
        """
        is_crypt = False
        for encrypt_name in encrypt_set:
            if file_name.startswith(encrypt_name):
                is_crypt = True
                break
        return is_crypt

    def sync_full_files(self, remote_ip):
        """sync full files"""
        if not os.path.isdir(SyncConf.SYNC_TMP_DIR):
            # make temp direcory
            os.makedirs(SyncConf.SYNC_TMP_DIR)

        # Sync full files
        LOGGER.debug('Sync full files...')
        for file_info in self.sync_fileinfos:
            is_encrypt = self.is_encrypt_file(file_info['name'], self.encrypt_set)
            self.sync_files(remote_ip, file_info['name'], file_info['isdir'],
                            is_encrypt, True)

    def update_rsyncd_conf(self, remote_ip_lst):
        """ 更新rsyncd.conf文件

        @param remote_ip_lst: 远端IP地址列表
        """
        sec_names = {}
        for dir_info in self.watch_lst:
            dir_name = dir_info['name']
            # 替换目录名称中的斜线，作为配置文件中module options的section名称
            sec_names[dir_name[1:].replace('/', '_')] = dir_name

        with open(self.rsync_cfg_path, 'w') as fp:
            fp.write('port=%s\r\n' % SyncConf.RSYNC_PORT)
            fp.write('uid=0\r\n')
            fp.write('gid=0\r\n')
            fp.write('max connections=10\r\n')
            fp.write('use chroot=yes\r\n')
            fp.write('log file=%s\r\n' % SyncConf.RSYNCD_LOG)
    #            fp.write('pid file=%s\r\n' % HAConf.RSYNCD_PID)
            fp.write('lock file=%s\r\n' % SyncConf.RSYNCD_LOCK)
            remote_ips = ' '.join(remote_ip_lst)
            fp.write('hosts allow = %s\r\n' % remote_ips)
            fp.write('hosts deny = *\r\n')
            fp.write('secrets file = %s\r\n' % self.rsync_secret_path)
            fp.write('list = no\r\n')
            fp.write('ignore errors = yes\r\n')
            fp.write('auth users = %s\r\n' % SyncConf.RSYNC_USER)
            fp.write('read only = no\r\n')
            fp.write('timeout = 300\r\n')
            fp.write('reverse lookup = no\r\n')
            # 设备同步的目录路径
            for key in sec_names:
                fp.write('[%s]\r\n' % key)
                fp.write('path = %s\r\n' % sec_names[key])



