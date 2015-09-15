#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
Created on 2015-9-14

@author: Elem
'''
from argparse import ArgumentParser

from isync_client import SyncClient
from isync_server import SyncServer

from isync_logger import logger_init
LOGGER = logger_init('pyisync')

if __name__ == '__main__':
    prog_desc = 'Real-time client command'
    parser = ArgumentParser(description=prog_desc)
    type_help = 'start type, client or server'
    parser.add_argument('--type', type=str, choices=['client', 'server'],
                        default='client', help=type_help)
    host_help = "Remote host address. e.g.:1.1.1.1,2.2.2.2"
    parser.add_argument('--host', type=str, required=True, help=host_help)
    args = parser.parse_args()

    hosts = args.host.split(',')
    if not hosts:
        print 'Err:host argument must be not null.'
        print parser.print_help()

    if args.type == 'client':
        LOGGER.info('start sync client...')
        client = SyncClient(remote_ip_lst=hosts)
        client.start_monitor()
    elif args.type == 'server':
        serv = SyncServer(remote_ip_lst=hosts)
        serv.start()
    else:
        print parser.print_help()



