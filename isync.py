#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
Created on 2015-9-14

@author: Elem
'''
from argparse import ArgumentParser

from isync_client import SyncClient

from isync_logger import logger_init
LOGGER = logger_init('pyisync')

if __name__ == '__main__':
    prog_desc = 'Real-time client command'
    parser = ArgumentParser(description=prog_desc)
    type_help = 'start type, client or server'
    parser.add_argument('--type', type=str, choices=['client', 'server'],
                        default='client', help=type_help)
    host_help = "Remote host address"
    parser.add_argument('--host', type=str, required=True, help=host_help)
    args = parser.parse_args()

    if args.type == 'client':
        LOGGER.info('start sync client...')
        client = SyncClient(remote_ip=args.host)
        client.start_monitor()



