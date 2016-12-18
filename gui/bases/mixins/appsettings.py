# -*- coding: utf-8 -*-
# gui/bases/mixins/algorithmwidget.py

from __future__ import absolute_import # PEP328

from gui.qt import QtCore
from QtCore import QSettings

from utils.devtools import DBG

class AppSettings(object):
    _appSettings = None

    @property
    def appSettings(self):
        return self._appSettings

    @appSettings.setter
    def appSettings(self, settings):
        DBG(type(settings), isinstance(settings, QSettings))
        if isinstance(settings, QSettings):
            self._appSettings = settings

    def setRootGroup(self):
        if self.appSettings is None:
            return
        while len(self.appSettings.group()):
            self.appSettings.endGroup()

# vim: set ts=4 sts=4 sw=4 tw=0:
