# -*- coding: utf-8 -*-
# mainwindow.py

# sorry, this file is not well structured atm and is subject to change
# (the author)

import os.path
import re
import sys
import logging
from cutesnake.qt import QtCore, QtGui
from cutesnake.utils.signal import Signal
from QtCore import Qt, QSettings, QRegExp
from QtGui import (QWidget, QHBoxLayout, QVBoxLayout, QPushButton,
                   QLabel, QCheckBox, QSizePolicy, QSpacerItem, QLayout,
                   QGroupBox, QComboBox, QApplication, QGridLayout,
                   QTreeWidgetItem, QTreeWidget)
from cutesnake.widgets.mainwindow import MainWindow as MainWindowBase
from cutesnake.widgets.logwidget import LogWidget
from cutesnake.widgets.datalist import DataList
from cutesnake.utilsgui.filedialog import getOpenFiles
from cutesnake.widgets.settingswidget import SettingsWidget
from cutesnake.utils.lastpath import LastPath
from cutesnake.utils import isList
from cutesnake.utilsgui.displayexception import DisplayException
from cutesnake.algorithm import ParameterNumerical
from version import version
from calc import SASData, Calculator
from McSAS import McSAS

INFOTEXT = """One or more selected files are read in and passed to Brian Pauws Monte-Carlo size distribution analysis program for 1D SAXS data.

The convergence criterion can be set by the user. If it is not reached no output is generated, just this log is saved to file. On success, the resulting size distribution and the data fit are stored to files with uncertainties.

Output files start with the base name of the input file. They have the current date+time appended to avoid overwriting existing results."""

CHANGESTEXT = (u"""

Changes in 0.0.11:
- distribution statistics log output and writing to stats file
- plain SAS evaluation (no fit) if no param is active
- all output files with extensions and storing in settings
- configuration file now *.cfg
- single start/stop button

Changes in 0.0.10:
- data file listing widget on top with short info
  - double-click uses sphere size est. for sphere model radius range
- start/stop buttons
  - allows to abort current calculation and restart
- column names in output files
- data file names stored with settings
- switch to enable/disable background level fit
- multiple plot figures on Windows supported

Changes in 0.0.9:
- added GUI to public McSAS repository

Changes in 0.0.8:
- new model: GaussianChain, verified against SASfit:
  http://sasfit.sf.net/manual/Gaussian_Chain#Gauss_2
- fixed volume function exponent in Kholodenko
  was v² instead of just v

Changes in 0.0.7:
- Using restructured McSAS
- building GUI for models and global settings dynamically
- new model: Kholodenkos worm-like structure, verified against SASfit

Changes in 0.0.6:
Fixed handling of negative values in PDH data files.

Changes in 0.0.5:
'Number-weighted distributions now come with correct-looking observability limits.'
 https://bitbucket.org/pkwasniew/mcsas/commits/81bbf84

""".replace('\n\n', '<hr />'))
CHANGESTEXT = re.sub(r"(Changes in [0-9]+\.[0-9]+\.[0-9]+)",
                     r"<strong>\1</strong>",
                     CHANGESTEXT)

from models.scatteringmodel import ScatteringModel
from models.sphere import Sphere
from models.kholodenko import Kholodenko
from models.gaussianchain import GaussianChain
from models.lmadensesphere import LMADenseSphere
from models.cylindersIsotropic import CylindersIsotropic

MODELS = {Sphere.name(): Sphere,
          CylindersIsotropic.name(): CylindersIsotropic,
          GaussianChain.name(): GaussianChain,
          LMADenseSphere.name(): LMADenseSphere}
FIXEDWIDTH = 120

def eventLoop():
    app = QApplication(sys.argv)
    mw = MainWindow()
    mw.show()
    return app.exec_()

class PropertyWidget(SettingsWidget):
    _calculator = None

    def selectModel(self):
        index = [i for i in range(0, self.modelBox.count())
                    if self.modelBox.itemText(i) == "Sphere"][0]
        self.modelBox.setCurrentIndex(index)

    def keys(self):
        return self._calculator.paramNames()

    def calculator(self):
        """Returns a calculator object updated with current GUI settings."""
        self._updateModelParams()
        return self._calculator

    def setSphericalSizeRange(self, minVal, maxVal):
        if self.modelBox.currentText() != "Sphere":
            return
        key = "radius"
        keymin, keymax = key+"min", key+"max"
        if self.get(keymin) is not None and self.get(keymax) is not None:
            self.set(keymin, minVal)
            self.set(keymax, maxVal)

    def __init__(self, parent):
        SettingsWidget.__init__(self, parent)
        self._calculator = Calculator()
        layout = QHBoxLayout(self)
        layout.setObjectName("layout")

        mcsasSettings = QGroupBox("McSAS settings")
        mcsasLayout = QVBoxLayout(mcsasSettings)
        mcsasLayout.setObjectName("mcsasLayout")
        # TODO: use signalmapper for update ...
        entries = []
        for p in self._calculator.params():
            container = self._makeSettingWidget(entries, p)
            mcsasLayout.addWidget(container)
        mcsasSettings.setLayout(mcsasLayout)
        layout.addWidget(mcsasSettings)

        modelSettings = QGroupBox("Model settings")
        modelLayout = QVBoxLayout(modelSettings)
        modelLayout.setObjectName("modelLayout")
        self.modelBox = QComboBox(modelSettings)
        for name in MODELS.iterkeys():
            self.modelBox.addItem(name)
        self.modelBox.setFixedWidth(FIXEDWIDTH)
        modelLayout.addWidget(self.modelBox)
        self.modelParams = QWidget()
        paramLayout = QVBoxLayout(self.modelParams)
        self.modelParams.setLayout(paramLayout)
        self.modelParams.layout().addStretch()
        modelLayout.addWidget(self.modelParams)
        modelSettings.setLayout(modelLayout)
        layout.addWidget(modelSettings)
        self.modelBox.setCurrentIndex(-1)
        self.modelBox.currentIndexChanged[str].connect(self._selectModelSlot)
        self.setLayout(layout)
        self.sigValuesChanged.connect(self._updateModelParams)

    def _selectModelSlot(self, key = None):
        model = MODELS.get(str(key), None)
        if (key is not None and model is not None and
            issubclass(model, ScatteringModel)):
            self._calculator.model = model()
        for child in self.modelParams.children():
            if not isinstance(child, QWidget):
                continue
            self.modelParams.layout().removeWidget(child)
            child.setParent(QWidget())
        entries = []
        for p in reversed(self._calculator.modelParams()):
            container = self._makeSettingWidget(entries, p,
                                                activeBtns = True)
            self.modelParams.layout().insertWidget(0, container)
        entries.append(self.modelBox)
        for i in reversed(range(1, len(entries))):
            self.modelParams.setTabOrder(entries[i], entries[i-1])

    def _updateModelParams(self):
        activeChanged = False
        for p in self._calculator.modelParams():
            # persistent due to changes to the class instead of instance
            key = p.name()
            newValue = self.get(key)
            if newValue is not None:
                p.setValue(newValue)
            minValue = self.get(key+"min")
            maxValue = self.get(key+"max")
            if minValue is not None and maxValue is not None:
                p.setValueRange((minValue, maxValue))
            newActive = self.get(key+"active")
            if isinstance(newActive, bool) and p.isActive != newActive:
                p.isActive = newActive
                activeChanged = True
        # update algo settings
        for p in self._calculator.params():
            value = self.get(p.name())
            if value is None:
                continue
            p.setValue(value)
        if activeChanged:
            self._selectModelSlot()

    @staticmethod
    def _makeLabel(name):
        lbl = QLabel(name)
        lbl.setAlignment(Qt.AlignLeft|Qt.AlignVCenter)
        return lbl

    def _makeEntry(self, name, dtype, value, minmax = None):
        ntry = self.getInputWidget(dtype)(self)
        ntry.setObjectName(name)
        if dtype is bool:
            ntry.setChecked(value)
        else:
            ntry.setAlignment(Qt.AlignRight|Qt.AlignVCenter)
            if isList(minmax) and len(minmax):
                ntry.setMinimum(min(minmax))
                ntry.setMaximum(max(minmax))
            ntry.setValue(value)
        self.connectInputWidgets(ntry)
        return ntry

    def _makeSettingWidget(self, entries, param, activeBtns = False):
        widget = QWidget(self)
        layout = QHBoxLayout(widget)
        lbl = self._makeLabel(param.displayName())
        lbl.setWordWrap(True)
        layout.addWidget(lbl)
        minmax = None
        if param.isActive and isinstance(param, ParameterNumerical):
            minmax = type(param).min(), type(param).max()
            ntryMin = self._makeEntry(
                    param.name()+"min", param.dtype, param.min(), minmax)
            ntryMin.setPrefix("min: ")
            layout.addWidget(ntryMin)
            ntryMax = self._makeEntry(
                    param.name()+"max", param.dtype, param.max(), minmax)
            ntryMax.setPrefix("max: ")
            layout.addWidget(ntryMax)
            ntryMin.setFixedWidth(FIXEDWIDTH)
            ntryMax.setFixedWidth(FIXEDWIDTH)
            entries.extend((ntryMax, ntryMin)) # reversed order, see above
        else:
            if isinstance(param, ParameterNumerical):
                minmax = param.min(), param.max()
            ntry = self._makeEntry(param.name(), param.dtype, param.value(),
                                   minmax)
            ntry.setFixedWidth(FIXEDWIDTH)
            layout.addWidget(ntry)
            entries.append(ntry)
        if activeBtns:
            activeBtn = QPushButton("active", self)
            activeBtn.setObjectName(param.name()+"active")
            activeBtn.setCheckable(True)
            activeBtn.setChecked(param.isActive)
            activeBtn.setFixedWidth(FIXEDWIDTH*.5)
            layout.addWidget(activeBtn)
            activeBtn.clicked.connect(self._updateModelParams)
            self.connectInputWidgets(activeBtn)
        widget.setLayout(layout)
        return widget

class FileList(DataList):
    sigSphericalSizeRange = Signal((float, float))

    def loadData(self, fileList = None):
        if fileList is None or type(fileList) is bool:
            fileList = getOpenFiles(self, "Load one or more data files",
                                    LastPath.get(), multiple = True)
        # populates to data list widget with items based on the return of
        # processSourceFunc(filename)
        DataList.loadData(self, sourceList = fileList, showProgress = False,
                          processSourceFunc = SASData.load)

    def itemDoubleClicked(self, item, column):
        valueRange = item.data().sphericalSizeEst()
        self.sigSphericalSizeRange.emit(min(valueRange), max(valueRange))

class MainWindow(MainWindowBase):
    onCloseSignal = Signal()
    _loadedData = None

    def __init__(self, parent = None):
        MainWindowBase.__init__(self, version, parent) # calls setupUi() and restoreSettings()

    def setupUi(self, *args):
        # called in MainWindowBase.__init__()
        self.fileWidget = FileList(self, title = "data files",
                                   withBtn = False)
        self.fileWidget.setHeader(SASData.displayDataDescr())
        self.fileWidget.setMaximumHeight(100)
        self.fileWidget.setToolTip(
                "Double click to use the estimated size for the model.")

        self.loadBtn = QPushButton("load files ...")
        self.loadBtn.pressed.connect(self.fileWidget.loadData)
        self.startStopBtn = QPushButton()
        self.startStopBtn.setCheckable(True)
        self.startStopBtn.clicked[bool].connect(self.onStartStopClick)
        btnLayout = QVBoxLayout()
        for btn in self.loadBtn, self.startStopBtn:
            btn.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Maximum)
            btnLayout.addWidget(btn)
        btnWidget = QWidget(self)
        btnWidget.setLayout(btnLayout)
        self.propWidget = PropertyWidget(self)
        self.propWidget.setSizePolicy(QSizePolicy.Preferred,
                                      QSizePolicy.Maximum)
        self.fileWidget.sigSphericalSizeRange.connect(
                        self.propWidget.setSphericalSizeRange)
        ctrlLayout = QHBoxLayout()
        ctrlLayout.addWidget(btnWidget)
        ctrlLayout.addWidget(self.propWidget)
        settingsWidget = QWidget(self)
        settingsWidget.setLayout(ctrlLayout)

        self.logWidget = LogWidget(self, appversion = version)
        self.onCloseSignal.connect(self.logWidget.onCloseSlot)
        self.logWidget.setSizePolicy(QSizePolicy.Preferred,
                                     QSizePolicy.Expanding)
        self.logWidget.append(INFOTEXT)
        if len(CHANGESTEXT):
            self.logWidget.append(CHANGESTEXT)
        self.logWidget.append("\n\r")

        self.centralLayout = QVBoxLayout()
        self.centralLayout.addWidget(self.fileWidget)
        self.centralLayout.addWidget(settingsWidget)
        self.centralLayout.addWidget(self.logWidget)

        centralWidget = QWidget(self)
        centralWidget.setLayout(self.centralLayout)
        self.setCentralWidget(centralWidget)

    def restoreSettings(self):
        MainWindowBase.restoreSettings(self)
        settings = self.appSettings()
        for name in self.propWidget.keys():
            if self.propWidget.get(name) is None:
                continue # no UI element for this setting
            val = settings.value(name)
            self.propWidget.set(name, settings.value(name))
        try:
            value = unicode(settings.value("lastpath").toString())
        except AttributeError: # QVariant
            value = unicode(settings.value("lastpath"))
        if os.path.isdir(value):
            LastPath.set(value)

    def storeSettings(self):
        MainWindowBase.storeSettings(self)
        settings = self.appSettings()
        for name in self.propWidget.keys():
            value = self.propWidget.get(name)
            if value is None:
                continue # no UI element for this setting
            settings.setValue(name, value)
        settings.setValue("lastpath", LastPath.get())
        settings.sync()
        tempSettings = QSettings("/tmp/qsettings.test", QSettings.IniFormat)
        for key in settings.allKeys():
            if key in ('geometry', 'windowState', 'lastpath'):
                continue
            tempSettings.setValue(key, settings.value(key))
        tempSettings.sync()

    def fileDialog(self):
        filenames = getOpenFiles(self, "Load one or more data files",
                                 LastPath.get(), multiple = True)
        self.loadFiles(filenames)

    def onStartup(self):
        self.propWidget.selectModel()
        self.fileWidget.loadData(self.getCommandlineArguments())
        self.onStartStopClick(False)

    def onStartStopClick(self, checked):
        if checked:
            self.startStopBtn.setText("stop")
            self.startStopBtn.setChecked(True)
            self.calc()
        # run this also for 'start' after calculation
        self.propWidget.calculator().stop()
        self.startStopBtn.setText("start")
        self.startStopBtn.setChecked(False)

    def calc(self):
        if len(self.fileWidget) <= 0:
            return
        self.logWidget.clear()
        calculator = self.propWidget.calculator()
        self.fileWidget.updateData(updateFunc = calculator,
                                   showProgress = False)

    def closeEvent(self, closeEvent):
        super(MainWindow, self).closeEvent(closeEvent)
        self.onStartStopClick(False)
        self.onCloseSignal.emit()

# vim: set ts=4 sts=4 sw=4 tw=0:
