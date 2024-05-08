# -*- coding: utf-8 -*-
# gui/rangelist.py

import logging
from QtCore import Qt, QFileInfo, QMargins
from QtGui import QPalette
from QtWidgets import (QWidget, QHBoxLayout, QVBoxLayout, QPushButton,
                   QLabel, QComboBox, QDialog, QSpinBox,
                   QCheckBox)
import numpy as np

from .bases.datalist import DataList
from .bases.mixins import AppSettings
from ..utils import isList, testfor
from ..utils.parameter import (ParameterBase, ParameterNumerical, Histogram,
                                   isFitParam, isActiveFitParam)
from .calc import Calculator

# do not remove, dialog will not work without this
from .scientrybox import SciEntryBox

from ..bases.model import ScatteringModel

# required for svg graphics support
from .qt import QtSvg, QtXml, pluginDirs
from .liststyle import setBackgroundStyleSheet
from ..main import makeAbsolutePath

def getItemIndex(comboBox, text):
    for i in range(comboBox.count()):
        if comboBox.itemText(i) == text:
            return i
    return -1 # select none, usually

class RangeDialog(QDialog):
    """Creates a modal dialog window to ask the user for a range to be
    added."""
    _model = None
    _labels = None

    def __init__(self, parent = None, model = None):
        QDialog.__init__(self, parent)
        assert isinstance(model, ScatteringModel)
        self._model = model
        self.setObjectName("AddRangeDialog")
        self.setWindowTitle("Add Range")
        self.setWindowModality(Qt.WindowModal)
        vlayout = QVBoxLayout(self)
        vlayout.setObjectName("vlayout")
        vlayout.addWidget(self._createEntries())
        vlayout.addWidget(self._createButtons())
        self.setLayout(vlayout)

    def _createEntries(self):
        entryWidget = QWidget(self)
        entryLayout = QHBoxLayout(entryWidget)
        inputWidgets = (self._createParamBox(), self._createAutoRange(),
                        self._createLower(), self._createUpper(),
                        self._createBins(),
                        self._createXScale(), self._createYWeight())
        self._labels = dict()
        # assumes same ordering of entryWidgets above and Histogram.displayData
        for col, inputWidget in zip(Histogram.displayData, inputWidgets):
            fieldWidget = QWidget(self) # combines label + input
            fieldLayout = QVBoxLayout(fieldWidget)
            fieldLayout.setContentsMargins(QMargins())
            # create label, text is set in _selectParam()
            self._labels[col] = QLabel(self)
            self._labels[col].setAlignment(Qt.AlignHCenter)
            # stack label + input
            fieldLayout.addWidget(self._labels[col])
            fieldLayout.addWidget(inputWidget)
            fieldWidget.setLayout(fieldLayout)
            # add field to row of inputs
            entryLayout.addWidget(fieldWidget)
        entryWidget.setLayout(entryLayout)
        self.pbox.setCurrentIndex(0)
        self.lentry.selectAll() # select the first input by default
        return entryWidget

    def _createAutoRange(self):
        autoRange = QCheckBox(self)
        autoRange.stateChanged.connect(self._onAutoRangeChange)
        self.autoRange = autoRange
        return autoRange

    def _onAutoRangeChange(self, isChecked):
        isChecked = (isChecked == Qt.Checked) # no tristate
        enableLimits = not isChecked
        self.lentry.setEnabled(enableLimits)
        self.uentry.setEnabled(enableLimits)
        self._setLimits()

    def _createLower(self):
        # add input for lower limit
        lentry = SciEntryBox(self)
        lentry.setPrefix("lower: ")
        self.lentry = lentry
        return lentry

    def _createUpper(self):
        # add input for upper limit
        uentry = SciEntryBox(self)
        uentry.setPrefix("upper: ")
        self.uentry = uentry
        return uentry

    def _createBins(self):
        # number of histogram bin input box
        bentry = QSpinBox(self)
        bentry.setRange(1, 200)
        bentry.setValue(50)
        bentry.setSingleStep(10)
        self.bentry = bentry
        return bentry

    def _createParamBox(self):
        # add a parameter choice list
        pbox = QComboBox(self)
        for p in self._model.params():
            if not hasattr(p, "isActive"):
                #not a fit parameter, a regular one
                continue
            if not p.isActive():
                continue
            # providing the internal param name as item data
            pbox.addItem(p.displayName(), p.name())
        # pbox.addItem("Test Dummy", "dummy")
        pbox.setCurrentIndex(-1)
        pbox.currentIndexChanged[int].connect(self._selectParam)
        self.pbox = pbox
        return pbox

    def _createXScale(self):
        # histogram scaling choice (X-axis only at this point)
        sentry = QComboBox(self)
        for name in Histogram.xscaling():
            sentry.addItem(name)
        # select a default x scaling, for DataObj aware settings, RangeList has
        # to be connected to DataList in MainWindow by an onDataSelected() slot
        sentry.setCurrentIndex(getItemIndex(sentry, "lin"))
        self.sentry = sentry
        return sentry

    def _createYWeight(self):
        # histogram weighting input
        wentry = QComboBox(self)
        for name in Histogram.yweighting():
            wentry.addItem(name)
        self.wentry = wentry
        return wentry

    def _getParam(self, index):
        pname = self.pbox.itemData(index)
        p = getattr(self._model, pname)
        # perhaps, use testfor() for that:
        assert p is not None, "Could not find parameter from selection box" 
        return p

    def _setLimits(self):
        p = self._getParam(self.pbox.currentIndex())
        lval, uval = p.activeRange()
        try:
            # account for units conversion
            lval, uval = p.toDisplay(lval), p.toDisplay(uval)
        except AttributeError:
            # raise # will break here, use it for debugging
            pass
        self.lentry.setValue(lval)
        self.uentry.setValue(uval)

    def _selectParam(self, index):
        """Gets the index within the selection box."""
        p = self._getParam(index)
        llim, ulim = p.valueRange()
        try:
            # account for units conversion
            llim, ulim = p.toDisplay(llim), p.toDisplay(ulim)
        except AttributeError:
            # raise # will break here, use it for debugging
            pass
        self.lentry.setRange(llim, ulim)
        self.uentry.setRange(llim, ulim)
        self.autoRange.setCheckState(Qt.Checked) # sets limits too
        # set labels
        for col, text in zip(Histogram.displayData, Histogram.displayDataDescr):
            if "lower" in col or "upper" in col:
                text = u"{t} ({u})".format(t = text, u = p.displayMagnitudeName())
            elif any([(l in text) for l in ("axis", "bins", "range")]):
                # break long descriptions to keep them short
                text = text.replace(" ", "\n", 1)
            self._labels[col].setText(text)

    def _createButtons(self):
        btnWidget = QWidget(self)
        btnLayout = QHBoxLayout(btnWidget)
        okBtn = QPushButton("add", self)
        okBtn.clicked.connect(self.accept)
        cancelBtn = QPushButton("cancel", self)
        cancelBtn.clicked.connect(self.reject)
        btnLayout.addWidget(okBtn)
        btnLayout.addWidget(cancelBtn)
        btnWidget.setLayout(btnLayout)
        return btnWidget

    def output(self):
        if not self.exec_() or self.lentry.value() == self.uentry.value():
            return None
        p = None
        try:
            pname = self.pbox.itemData(self.pbox.currentIndex())
            p = getattr(self._model, pname)
        except:
            return None
        lval, uval = (self.lentry.value(), self.uentry.value())
        try:
            # take units into account,
            # convert from display units to SI units for internal use
            lval, uval = (p.toSi(lval), p.toSi(uval))
        except AttributeError:
            pass

        hist = Histogram(p, lval, uval,
                self.bentry.value(), self.sentry.currentText(),
                self.wentry.currentText())
        hist.autoFollow = self.autoRange.isChecked()
        return hist

class RangeList(DataList, AppSettings):
    _calculator = None

    def __init__(self, calculator = None, appSettings = None, **kwargs):
        DataList.__init__(self, **kwargs)
        assert isinstance(calculator, Calculator)
        self._calculator = calculator
        self.appSettings = appSettings
        self.sigRemovedData.connect(self.onRemoval)
        self.listWidget.mouseDoubleClickEvent = self.mouseDoubleClickEvent

    def mouseDoubleClickEvent(self, event):
        """Shows RangeDialog on double click."""
        self.loadData()

    def itemUpdate(self, item, column):
        # handle autoFollow only, i.e. auto range update changes only
        if column != Histogram.displayData.index("autoFollow"):
            return
        # update histogram based on auto range update on/off
        hist = item.data()
        hist.autoFollow = (item.checkState(column) == Qt.Checked)
        if hist.autoFollow:
            hist.updateRange()
            item.update()

    def onRemoval(self, removedHistograms):
        for hist in removedHistograms:
            try:
                hist.param.histograms().remove(hist)
            except AttributeError:
                continue

    def append(self, histList):
        if histList is None:
            return
        if not isList(histList):
            histList = [histList]
        if not len(histList):
            return
        # put a copy of histograms into the ui list, otherwise comparison fails
        DataList.loadData(self, sourceList = histList, showProgress = False,
                processSourceFunc = lambda x: x)
        self.fitColumnsToContents()

    def loadData(self, ranges = None):
        """Overridden base class method for adding entries to the list."""
        # add only one item at a time into the list
        # set up dialog window for "add range"
        dialog = RangeDialog(self, self._calculator.model)
        newHist = dialog.output()
        if not isinstance(newHist, Histogram):
            return
        # do not add duplicates
        if newHist in self.data():
            return
        # add it to the actual histogram list of the parameter
        newHist.param.histograms().append(newHist) # hmm, funny here
        # update the GUI based on that
        self.updateHistograms()

    def _getParams(self):
        return self._calculator.model.params() if self._calculator.model else []

    def updateHistograms(self):
        """Called after UI update by sigBackendUpdated from an AlgorithmWidget."""
        lst = []
        for p in self._getParams():
            if not isActiveFitParam(p):
                continue # show the active fit parameters only
            lst += p.histograms()
        # finally, the RangeList gets the same hist instances which are in the
        # parameters, no copy, therefore just rebuild the UI to get in sync
        # comparison doesn't work: set(self.data()) == set(lst)
        # the data item has to same instance stored which comes in here
        self.clear()
        self.append(lst)

    def _beginHistogramGroup(self, model):
        """Sets the AppSettings group for the current model where histograms
        can be stored."""
        self.setRootGroup()
        self.appSettings.beginGroup("Model")
        self.appSettings.beginGroup(model.name())
        self.appSettings.beginGroup("histograms")

    def storeSession(self):
        if self.appSettings is None:
            return
        self._beginHistogramGroup(self._calculator.model)
        # remove all existing histograms from persistent storage
        for child in self.appSettings.childGroups():
            self.appSettings.remove(child)
        # store current histograms from parameters which may not be visible
        hists = []
        for p in self._getParams():
            if not isFitParam(p): continue # get all fitable parameters
            hists += p.histograms()
        for i, h in enumerate(hists):
            self.appSettings.beginGroup(str(i))
            for key in h.integralProps():
                value = getattr(h, key, None)
                if isinstance(value, ParameterBase):
                    value = value.name()
                if isinstance(value, float):
                    # avoid issues on restore with unequal floats
                    value = repr(value)
                self.appSettings.setValue(key, value)
            self.appSettings.endGroup()
        self.setRootGroup()

    def restoreSession(self):
        """Load last known user settings from persistent app settings."""
        if self.appSettings is None:
            return

        def parseHistogram(settings):
            initProps = []
            param = None
            for key in Histogram.integralProps():
                value = settings.value(key, None)
                if key == "param":
                    param = getattr(self._calculator.model, value, None)
                    # get FitParameters which might not be active
                    if param is None or not isFitParam(param):
                        return None
                    value = param
                initProps.append(value)
            return Histogram(*initProps)

        self.clear()
        self._beginHistogramGroup(self._calculator.model)
        histCfg = dict()
        for iKey in self.appSettings.childGroups():
            i = -1
            try:
                i = int(iKey)
            except ValueError:
                continue
            if i < 0 or str(i) != iKey:
                continue
            self.appSettings.beginGroup(iKey)
            # append the histogram to the temporary list of a parameter
            hist = parseHistogram(self.appSettings)
            self.appSettings.endGroup()
            if hist is not None and hist.param is not None:
                if hist.param.name() not in histCfg:
                    histCfg[hist.param.name()] = []
                histCfg[hist.param.name()].append(hist)
        self.setRootGroup()
        for pname, histLst in histCfg.items():
            if not len(histLst):
                continue
            param = histLst[0].param
            # parseHistogram() above return FitParameters only
            param.histograms().clear()
            param.histograms().extend(histLst)
        self.updateHistograms()

    def setupUi(self):
        setBackgroundStyleSheet(self, "./resources/background_ranges.svg")
        self.listWidget.setRootIsDecorated(False)
        self.listWidget.setUniformRowHeights(True)
        self.listWidget.setItemsExpandable(False)
        self.listWidget.setAlternatingRowColors(True)
        self.action("load").setText("add range") # fix default action name
        self.clearSelection()
        self.setHeader(Histogram.displayDataDescr)
        self.setToolTip(
            "Right-click to add additional ranges."
        )
        # self.addMenuEntry(name = "edit", text = "Edit selected", 
        #                   menuStates = "hasSelection",
        #                   callbacks = self.editEntry)
        # self.addMenuEntry(name = "recalc", text = "recalc histograms",
        #                   menuStates = "hasSelection",
        #                   callbacks = self.recalc)

    def editEntry(self):
        return
        # more on the TODO list... Will figure this out later.
    
    def recalc(self):
        return
        # this is not the _calculator instance I was looking for. 
        # self._calculator(recalc = True)
        # does not work yet! missing arguments for Hist.calc()
        DataList.updateData(self, selectedOnly = True, showProgress = False,
                updateFunc = Histogram.calc,
                stopFunc = None)

# vim: set ts=4 sts=4 sw=4 tw=0:
