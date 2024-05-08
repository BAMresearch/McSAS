# -*- coding: utf-8 -*-
# gui/algorithmwidget.py

import logging

from .utils.signal import Signal, tryDisconnect
from QtCore import Qt, QSettings, QRegExp
from QtWidgets import (QWidget, QHBoxLayout, QPushButton,
                   QLabel, QLayout, QGridLayout)
from .bases.datalist import DataList
from .bases.settingswidget import SettingsWidget
from .bases.mixins import TitleHandler, AppSettings
from ..bases.algorithm import AlgorithmBase, ParameterFloat # instance for test
from ..utils import isList, isString, testfor
from ..utils.parameter import ParameterNumerical, FitParameterBase
from .calc import Calculator
from .scientrybox import SciEntryBox

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
        layout.addWidget(w, i // numCols, i % numCols, Qt.AlignTop)

class AlgorithmWidget(SettingsWidget, AppSettings):
    _algo = None
    sigBackendUpdated = Signal()

    def __init__(self, parent, algorithm, appSettings):
        super(AlgorithmWidget, self).__init__(parent)
        self.algorithm = algorithm
        self.appSettings = appSettings
        self.sigValueChanged.connect(self.updateWidget)
        self.sigBackendUpdated.connect(self.onBackendUpdate)

    def blockSigValueChanged(self):
        tryDisconnect(self.sigValueChanged, self.updateWidget)

    def unblockSigValueChanged(self):
        self.sigValueChanged.connect(self.updateWidget)

    @property
    def algorithm(self):
        """Retrieves AlgorithmBase object containing all parameters
        for this settings."""
        return self._algo

    @algorithm.setter
    def algorithm(self, algo):
        assert algo is None or isinstance(algo, AlgorithmBase)
        self._algo = algo

    # allowed parameters could be configurable from file too
    def makeWidgets(self, *args):
        lst = []
        for p in args:
            p = getattr(self.algorithm, p, None)
            if p is None: continue
            w = self.makeSetting(p)
            if w is not None:
                lst.append(w)
        return lst

    @property
    def inputWidgets(self):
        """Returns all existing input names (for store/restore)."""
        children = []
        if self.algorithm is None:
            return children
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
        return [w.objectName() for w in self.inputWidgets]

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
        self.blockSigValueChanged() # block signals, update UI only first
        if section is None:
            section = self.objectName()
        self.appSettings.beginGroup(section)
        for key in self.keys:
            value = self.appSettings.value(key)
            try:
                self.set(key, value)
            except Exception as e:
                logging.warn(e)
        self.appSettings.endGroup()
        self.unblockSigValueChanged() # unblock signals
        self.updateAll() # update backend data from UI, emits sigBackendUpdated

    def _paramFromWidget(self, widget):
        if self.algorithm is None:
            return
        p = None
        try:
            p = getattr(self.algorithm, widget.parameterName)
        except AttributeError:
            p = None
        return p

    def updateWidget(self, widget, emitBackendUpdated = True):
        """Write UI settings back to the algorithm. Gets the parameter
        associated with a certain widget and processes all related widgets as
        well."""
        if widget in self.uiWidgets:
            return # skip ui input widgets without a Parameter backend
        param = self._paramFromWidget(widget)
        if param is None:
            logging.error("updateParam({}) could not find associated parameter!"
                          .format(widget.objectName()))
            return
        # get the parent of the updated widget and other input for this param
        self.updateParam(param, emitBackendUpdated)

    def updateParam(self, param, emitBackendUpdated = True):
        """Write UI settings back to the algorithm. Processes all input
        widgets which belong to a certain parameter."""
        if param is None:
            return
        key = param.name()
        valueWidget = self.getWidget(key)
        if valueWidget is None: # no input widgets for this parameter
            return
        # disable signals during ui updates
        self.blockSigValueChanged()
        # update the value input widget itself
        newValue = self.getValue(valueWidget)
        if newValue is not None:
            # clipping function in bases.algorithm.parameter def
            param.setDisplayValue(newValue)
            # set the possibly clipped value
            self.setValue(valueWidget, param.displayValue())
        self._updateFitParam(param, valueWidget)
        # enable signals again after ui updates
        self.unblockSigValueChanged()
        # param internals could have changed, update ui accordingly
        if emitBackendUpdated:
            self.sigBackendUpdated.emit() # update other widgets possibly

    def _updateFitParam(self, param, valueWidget):
        if not isinstance(param, FitParameterBase):
            return
        keymin, keymax = param.name() + "min", param.name() + "max"
        minWidget = self.getWidget(keymin)
        maxWidget = self.getWidget(keymax)
        # get changed value range if any
        minValue = self.getValue(minWidget)
        maxValue = self.getValue(maxWidget)
        # update value range for numerical parameters
        if None not in (minValue, maxValue):
            param.setDisplayActiveRange((minValue, maxValue))
            displayRange = param.displayActiveRange() # get updated values
            if isList(displayRange) and None not in displayRange:
                self.setValue(minWidget, min(displayRange))
                self.setValue(maxWidget, max(displayRange))
        newActive = self.get(param.name() + "active")
        if not isinstance(newActive, bool): # None for non-fit parameters
            return
        # update active state for fit parameters
        param.setActive(newActive)
        if None in (valueWidget, minWidget, maxWidget):
            return
        if param.isActive():
            valueWidget.hide()
            minWidget.show()
            maxWidget.show()
        else:
            valueWidget.show()
            minWidget.hide()
            maxWidget.hide()

    def updateAll(self):
        """Called in MainWindow on calculation start."""
        for p in self.algorithm.params():
            self.updateParam(p, emitBackendUpdated = False)
        # emit sigBackendUpdated after updating all widgets,
        # because they may be removed in the meantime
        self.sigBackendUpdated.emit()

    def onBackendUpdate(self):
        self.updateUi()

    def updateUi(self):
        """Update input widgets according to possibly changed backend data."""
        if self.algorithm is None:
            return
        # disable signals during ui updates
        self.blockSigValueChanged()
        for p in self.algorithm.params():
            if self.get(p.name()) in (p.displayValue(), None):
                continue
            self.set(p.name(), p.displayValue())
        # enable signals again after ui updates
        self.unblockSigValueChanged()

    @staticmethod
    def _makeLabel(name):
        lbl = QLabel(name + ":")
        lbl.setAlignment(Qt.Alignment(int(Qt.AlignLeft) | int(Qt.AlignVCenter)))
        lbl.setWordWrap(True)
        return lbl

    def _makeEntry(self, name, dtype, value, minmax = None,
                   widgetType = None, parent = None, decimals = None,
                   **kwargs):
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
        if decimals is not None: # set precision before the value is set
            widget.setDecimals(decimals)
        if dtype is bool:
            widget.setCheckable(True)
            widget.setChecked(value)
        else:
            widget.setAlignment(Qt.Alignment(int(Qt.AlignRight)|int(Qt.AlignVCenter)))
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
        decimals = None
        if hasattr(param, "decimals"):
            decimals = param.decimals()
        w = self._makeEntry(param.name(), param.dtype, param.displayValue(),
                            decimals = decimals, minmax = minmaxValue,
                            parent = widget)
        try: # set special value text for lower bound, simple solution
            special = param.displayValues(w.minimum())
            w.setSpecialValueText(special)
        except: 
            pass
        w.setFixedWidth(FIXEDWIDTH)
        widgets.insert(len(widgets)//2, w)

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
                                    activeRange[bound], decimals = decimals,
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
        # no backend update, ui was just built, data is still in sync
        self.updateParam(param, emitBackendUpdated = False)
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
        for i in reversed(list(range(layout.count()))):
            # reversed removal avoids renumbering possibly
            item = layout.takeAt(i)
            if newParent is None or item.widget() is None:
                continue
            item.widget().setParent(newParent)
            item.widget().deleteLater()

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

    def __init__(self, parent, algorithm, appSettings = None, showParams = None):
        """Additional arguments: *showParams* is a list of parameter names to
        show in this widget. If not specified it shows all available parameters
        by default."""
        super(SettingsGridWidget, self).__init__(parent, algorithm, appSettings)
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
