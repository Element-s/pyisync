#!/usr/bin/python
# -*- coding: utf-8 -*-
'''
Created on 2015-9-14

@author: Elem
'''
import logging

# Logging
def logger_init(name='pyisync'):
    """Initialize logger instance."""
    log = logging.getLogger(name)
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(
        logging.Formatter("[%(asctime)s %(name)s %(levelname)s] (L:%(lineno)d P:%(process)d) %(message)s"))
    log.addHandler(console_handler)
    log.setLevel(10)
    log.propagate = False
    return log

