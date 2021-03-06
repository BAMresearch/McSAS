# -*- coding: utf-8 -*-
# log/__init__.py

from __future__ import absolute_import
import logging
from .log import (timestampFormat, timestamp, timestampFormatted,
                  replaceStdOutErr, replaceHandler, addHandler, removeHandler)
from .widgethandler import WidgetHandler

log = logging.getLogger()

def getWidgetHandlers():
    """Returns all active WidgetHandlers for logging."""
    return list((h for h in log.handlers if isinstance(h, WidgetHandler)))

# vim: set ts=4 sw=4 sts=4 tw=0:
