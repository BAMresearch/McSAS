# -*- coding: utf-8 -*-
# gui/algorithmwidget.py

from __future__ import absolute_import # PEP328
import logging

from gui.qt import QtCore, QtGui
from gui.utils.signal import Signal
from QtCore import Qt, QSettings, QRegExp
from QtGui import (QWidget, QHBoxLayout, QPushButton,
                   QLabel, QLayout, QGridLayout)
from gui.bases.datalist import DataList
from gui.bases.settingswidget import SettingsWidget
from gui.bases.mixins.titlehandler import TitleHandler
from bases.algorithm import AlgorithmBase, ParameterFloat # instance for test
from utils import isList, isString, testfor
from utils.parameter import (ParameterNumerical, FitParameterBase)
from gui.calc import Calculator
from gui.scientrybox import SciEntryBox

FIXEDWIDTH = 120

def isNotNone(lst):
    if not isList(lst):
        return False
    return all((a is not None for a in lst))

def rearrangeWidgets(layout, widgets, targetWidth):
    def getNumCols():
        width = 0
        for i, w in enumerate(widgets):
            width += w.sizeHint().width()
            if width > targetWidth:
                return i
        return len(widgets)

    AlgorithmWidget.clearLayout(layout)
    numCols = max(1, getNumCols())
    # add them again with new column count
    for i, w in enumerate(widgets):
        layout.addWidget(w, i / numCols, i % numCols, Qt.AlignTop)

class AlgorithmWidget(SettingsWidget):
    _algo = None
    _appSettings = None
    sigRangeChanged = Signal()
    sigBackendUpdated = Signal()

    def __init__(self, parent, algorithm):
        super(AlgorithmWidget, self).__init__(parent)
        self.algorithm = algorithm
        self.sigValueChanged.connect(self.updateParam)
        self.sigBackendUpdated.connect(self.onBackendUpdate)

    @property
    def algorithm(self):
        """Retrieves AlgorithmBase object containing all parameters
        for this settings."""
        return self._algo

    @algorithm.setter
    def algorithm(self, algo):
        assert algo is None or isinstance(algo, AlgorithmBase)
        self._algo = algo

    @property
    def appSettings(self):
        return self._appSettings

    @appSettings.setter
    def appSettings(self, settings):
        assert isinstance(settings, QSettings)
        self._appSettings = settings

    # create inputs for a subset of algorithm parameters
    # allowed parameters could be configurable from file too
    def makeWidgets(self, *args):
        for p in args:
            p = getattr(self.algorithm, p, None)
            if p is None: continue
            yield self.makeSetting(p)

    @property
    def inputWidgets(self):
        """Returns all existing input names (for store/restore)."""
        if self.algorithm is None:
            return
        children = []
        for p in self.algorithm.params():
            query = p.name()
            try:
                p.isActive() # fails for non-FitParameters
                query = QRegExp("^" + p.name() + ".*")
            except AttributeError:
                pass
            children.extend(self.findChildren(QWidget, query))
        children.extend(self.uiWidgets)
        return children

    @property
    def uiWidgets(self):
        """May return a list of input widgets compatible but not associated to
        a parameter, e.g. for UI configuration. To be overridden in subclasses.
        """
        return []

    @property
    def keys(self):
        for w in self.inputWidgets:
            yield w.objectName()

    def storeSession(self, section = None):
        """Stores current UI configuration to persistent application settings.
        """
        if self.appSettings is None:
            return
        if section is None:
            section = self.objectName()
        self.appSettings.beginGroup(section)
        for key in self.keys:
            value = self.get(key)
            self.appSettings.setValue(key, value)
        self.appSettings.endGroup()

    def restoreSession(self, section = None):
        if self.appSettings is None:
            return
        if section is None:
            section = self.objectName()
        self.appSettings.beginGroup(section)
        for key in self.keys:
            value = self.appSettings.value(key)
            try:
                self.set(key, value)
            except StandardError, e:
                logging.warn(e)
        self.appSettings.endGroup()

    def _paramFromWidget(self, widget):
        if self.algorithm is None:
            return
        p = None
        try:
            p = getattr(self.algorithm, widget.parameterName)
        except AttributeError:
            p = None
        return p

    def updateParamRange(self, param, newRange):
        if (not isNotNone(newRange) or
            not isinstance(param, FitParameterBase) or
            not param.isActive()):
            return None
        displayRange = None
        try:
            param.setDisplayActiveRange(newRange)
            displayRange = param.displayActiveRange() # get updated values
        except AttributeError:
            param.setActiveRange(newRange)
            displayRange = param.activeRange()
        param.histograms().updateRanges()
        return displayRange

    def updateParam(self, widget, emitBackendUpdated = True):
        """Write UI settings back to the algorithm."""
        if widget in self.uiWidgets:
            return # skip ui input widgets without a Parameter backend
        p = self._paramFromWidget(widget)
        if p is None:
            logging.error("updateParam({}) could not find associated parameter!"
                          .format(widget.objectName()))
            return
        # disable signals during ui updates
        self.sigValueChanged.disconnect(self.updateParam)
        # persistent name due to changes to the class instead of instance
        key = p.name()
        # get the parent of the updated widget and other input for this param
        parent = widget.parent()
        valueWidget = parent.findChild(QWidget, key)
        minWidget = parent.findChild(QWidget, key+"min")
        maxWidget = parent.findChild(QWidget, key+"max")
        # get changed value range if any
        minValue = self.get(key+"min")
        maxValue = self.get(key+"max")
        # update value range for numerical parameters
        newRange = self.updateParamRange(p, (minValue, maxValue))
        if isNotNone(newRange):
            minWidget.setValue(min(newRange))
            maxWidget.setValue(max(newRange))
        # update the value input widget itself
        newValue = self.get(key)
        if newValue is not None:
            # clipping function in bases.algorithm.parameter def
            p.setDisplayValue(newValue)
            clippedVal = p.displayValue()
            try: 
                valueWidget.setValue(clippedVal)
            except AttributeError:
                pass
        # fit parameter related updates
        newActive = self.get(key+"active")
        if isinstance(newActive, bool): # None for non-fit parameters
            # update active state for fit parameters
            p.setActive(newActive)
            if p.isActive():
                valueWidget.hide()
                minWidget.show()
                maxWidget.show()
        if not isinstance(newActive, bool) or not newActive:
            valueWidget.show()
            try:
                minWidget.hide()
                maxWidget.hide()
            except: pass
        # enable signals again after ui updates
        self.sigValueChanged.connect(self.updateParam)
        # param internals could have changed, update ui accordingly
        if emitBackendUpdated:
            self.sigBackendUpdated.emit() # update other widgets possibly
        if isNotNone(newRange):
            # the range was updated
            self.sigRangeChanged.emit()

    def updateAll(self):
        """Called in MainWindow on calculation start."""
        for w in self.inputWidgets:
            self.updateParam(w, emitBackendUpdated = False)
        # emit sigBackendUpdated after updating all widgets,
        # because they may be removed in the meantime
        try:
            self.sigBackendUpdated.emit()
        # RuntimeError: Internal C++ object (SettingsGridWidget) already
        except RuntimeError: pass

    def onBackendUpdate(self):
        self.updateUi()

    def updateUi(self):
        """Update input widgets according to possibly changed backend data."""
        # disable signals during ui updates
        self.sigValueChanged.disconnect(self.updateParam)
        for p in self.algorithm.params():
            if self.get(p.name()) in (p.displayValue(), None):
                continue
            self.set(p.name(), p.displayValue())
        # enable signals again after ui updates
        self.sigValueChanged.connect(self.updateParam)

    def setStatsWidget(self, statsWidget):
        """Sets the statistics widget to use for updating ranges."""
        assert(isinstance(statsWidget, DataList))
        self._statsWidget = statsWidget

    @staticmethod
    def _makeLabel(name):
        lbl = QLabel(name + ":")
        lbl.setAlignment(Qt.AlignLeft|Qt.AlignVCenter)
        lbl.setWordWrap(True)
        return lbl

    def _makeEntry(self, name, dtype, value, minmax = None,
                   widgetType = None, parent = None, **kwargs):

        testfor(name not in self.keys, KeyError,
            "Input widget '{w}' exists already in '{s}'"
            .format(w = name, s = self.objectName()))
        if widgetType is None:
            if dtype is float:
                widgetType = SciEntryBox
            else:
                widgetType = self.getInputWidget(dtype)
        if parent is None:
            parent = self
        widget = widgetType(parent, **kwargs)
        widget.setObjectName(name)
        if dtype is bool:
            widget.setCheckable(True)
            widget.setChecked(value)
        else:
            widget.setAlignment(Qt.AlignRight|Qt.AlignVCenter)
            if isList(minmax) and len(minmax):
                widget.setMinimum(min(minmax))
                widget.setMaximum(max(minmax))
            widget.setValue(value)
        # update tooltip with help text about valid input values
        decimals = getattr(widget, "decimals", None)
        if decimals is not None:
            decimals = decimals()
        try:
            SciEntryBox.updateToolTip(widget, decimals)
        except:
            pass # for non-float input widgets
        self.connectInputWidgets(widget)
        return widget

    def makeSetting(self, param, activeBtns = False):
        """Creates an input widget for the provided Parameter and configures
        it appropriately.
        """
        if param is None:
            return None
        widget = QWidget(self)
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addStretch()

        try:
            suffix = param.suffix()
        except AttributeError:
            suffix = None

        if suffix is None:
            layout.addWidget(self._makeLabel(param.displayName()))
        else:
            layout.addWidget(self._makeLabel(u"{} ({})".format(
                param.displayName(), suffix)))

        widget.setLayout(layout)
        if isString(param.__doc__):
            # word wrapping by rich text: https://stackoverflow.com/a/4796057
            txt = "<span>{0}</span>".format(param.__doc__)
            # add description as tooltip if available for parameter
            widget.setToolTip(txt)

        # create scalar value input widget with min/max limits
        minmaxValue, widgets = None, []
        if isinstance(param, ParameterNumerical):
            minmaxValue = param.min(), param.max()
        if isinstance(param, ParameterFloat):
            minmaxValue = param.displayValueRange()

        w = self._makeEntry(param.name(), param.dtype, param.displayValue(),
                                      minmax = minmaxValue, parent = widget)
        try: # set special value text for lower bound, simple solution
            special = param.displayValues(w.minimum())
            w.setSpecialValueText(special)
        except: 
            pass
        w.setFixedWidth(FIXEDWIDTH)
        widgets.insert(len(widgets)/2, w)

        # Special widget settings for active fitting parameters:
        activeBtns = activeBtns and isinstance(param, FitParameterBase)
        if activeBtns:
            # create input boxes for user specified active fitting range
            # within default upper/lower from class definition
            # minmaxValue = type(param).min(), type(param).max()
            activeRange = {"min": param.displayActiveRange()[0],
                           "max": param.displayActiveRange()[1] }
            for bound in "min", "max":
                w = self._makeEntry(param.name() + bound, param.dtype,
                                    activeRange[bound],
                                    minmax = minmaxValue, parent = widget)
                w.setPrefix(bound + ": ")
                w.setFixedWidth(FIXEDWIDTH)
                widgets.append(w)
            # create *active* buttons for FitParameters only
            w = self._makeEntry(param.name()+"active", bool,
                                param.isActive(),
                                widgetType = QPushButton,
                                parent = widget)
            w.setText("Active")
            w.setFixedWidth(FIXEDWIDTH*.5)
            widgets.append(w)

        # add input widgets to the layout
        for w in widgets:
            layout.addWidget(w)
            # store the parameter name
            w.parameterName = param.name()
        # configure UI accordingly (hide/show widgets)
        self.updateParam(widgets[-1])
        return widget

    @staticmethod
    def clearLayout(layout, newParent = None):
        """Removes all widgets from the given layout and reparents them if
        *newParent* is a sub class of QWidget"""
        if layout is None:
            return
        assert isinstance(layout, QLayout)
        if not isinstance(newParent, QWidget):
            newParent = None
        for i in reversed(range(layout.count())):
            # reversed removal avoids renumbering eventually
            item = layout.takeAt(i)
            if newParent is not None:
                try:
                    item.widget().setParent(newParent)
                except: pass

    @staticmethod
    def removeWidgets(widget):
        """Removes all widgets from the layout of the given widget."""
        AlgorithmWidget.clearLayout(widget.layout(), QWidget())

    def resizeEvent(self, resizeEvent):
        """Resizes widget based on available width."""
        # basically, reacts to the size change by spawned scroll bar
        targetWidth = resizeEvent.size().width()
        self.resizeWidgets(targetWidth)

    def resizeWidgets(self, targetWidth):
        pass

class SettingsGridWidget(AlgorithmWidget):
    """Base class for displaying simple input boxes of various settings
    arranged on a grid dynamically based on the width of the window."""

    def __init__(self, parent, algorithm, showParams = None):
        """Additional arguments: *showParams* is a list of parameter names to
        show in this widget. If not specified it shows all available parameters
        by default."""
        super(SettingsGridWidget, self).__init__(parent, algorithm)
        self.title = TitleHandler.setup(self, self.algorithm.name())
        layout = QGridLayout(self)
        layout.setObjectName("configLayout")
        layout.setContentsMargins(0, 0, 0, 0)
        self.gridLayout = layout

        if not isList(showParams) or not len(showParams):
            showParams = self.algorithm.showParams
        self._widgets = tuple(self.makeWidgets(*showParams))

    def resizeWidgets(self, targetWidth):
        """Creates a new layout with appropriate row/column count."""
        rearrangeWidgets(self.gridLayout, self._widgets, targetWidth)

# vim: set ts=4 sts=4 sw=4 tw=0:
