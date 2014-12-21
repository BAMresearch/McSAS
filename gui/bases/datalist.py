# -*- coding: utf-8 -*-
# gui/bases/datalist.py

from __future__ import absolute_import # PEP328
import os.path
import logging
import collections
import sys

from time import time as timestamp
from gui.utils.signal import Signal
from utils.error import EmptySelection
from gui.utils.displayexception import DisplayException
from bases.dataset import DataSet, HierachicalDataSet, DisplayMixin
from utils import isList, isMap, isString
from utils.lastpath import LastPath
from gui.utils.translate import tr
from gui.qt import QtCore, QtGui
from QtCore import Qt, QMetaObject
from QtGui import (QWidget, QAction, QTreeWidget, QTreeWidgetItem,
                   QVBoxLayout, QPushButton, QAbstractItemView, QKeySequence)
from gui.bases.mixins.dropwidget import DropWidget
from gui.bases.mixins.contextmenuwidget import ContextMenuWidget
from gui.bases.mixins.titlehandler import TitleHandler

class DataItem(QTreeWidgetItem):
    """Generates a QTreeWidgetItem from arbitrary python objects.
    Storing those objects separately."""
    _store = None # storage for data objects associated with each item
    _isRemovable = None

    @classmethod
    def store(cls, key, value):
        if cls._store is None:
            cls._store = dict()
        cls._store[key] = value

    @classmethod
    def clear(cls, key):
        if cls._store is None:
            return
        del cls._store[key]

    @staticmethod
    def hash32(data):
        """Avoids OverFlowError at setData() with PySide on MacOS."""
        return hash(data) & 0x7fffffff

    @property
    def isRemovable(self):
        return bool(self._isRemovable)

    def __init__(self, data):
        super(DataItem, self).__init__()
        self.setChildIndicatorPolicy(
            QTreeWidgetItem.DontShowIndicatorWhenChildless)
        assert isinstance(data, DisplayMixin)
        self._isRemovable = data.isRemovable
        self.setData(0, Qt.UserRole, self.hash32(data))
        self.store(self.dataId(), data)
        self.update()

    def update(self):
        """Updates this item according to eventually changed data object"""
        data = self.data() # forced to be DataSet in __init__
        columnCount = len(data.displayData)
        for column in range(0, columnCount):
            columnData = data.displayData[column]
            if not isList(columnData): # columnData is supposed to be tuple
                columnData = (columnData, )
            for attrname in columnData: # set attributes of columns if avail
                if not hasattr(data, attrname):
                    continue
                value = getattr(data, attrname)
                getProperty, setProperty, value = self.getItemProperty(value)
                # set it always, regardless if needed
                setProperty(column, value)
        # adjust #table columns
        treeWidget = self.treeWidget()
        if treeWidget is not None and treeWidget.columnCount() < columnCount:
            treeWidget.setColumnCount(columnCount)
        # update children
        for item in self.takeChildren(): # remove all children
            item.remove()
            del item
        if isinstance(data, HierachicalDataSet):
            for child in data:
                self.addChild(DataItem(child))

    def getItemProperty(self, value):
        """For a value, returns this items getter/setter methods according
        to value type."""
        getProperty, setProperty = self.text, self.setText
        if isinstance(value, bool):
            getProperty, setProperty = self.checkState, self.setCheckState
            if value:
                value = Qt.Checked
            else:
                value = Qt.Unchecked
        elif value is None: # allows not set attrib., removes text from gui
            value = ""
        else:
            value = unicode(value) # convert numbers eventually
        return getProperty, setProperty, value

    def dataId(self):
        value = self.data(0, Qt.UserRole)
        try:
            return value.toPyObject()
        except:
            return value

    def data(self, *args):
        if len(args) > 1:
            return super(DataItem, self).data(*args)
        return self._store.get(self.dataId(), None)

    def listIndex(self):
        """
        Index of this items top most parent in the treewidget.
        """
        item = self
        while item.parent() is not None:
            item = item.parent()
        return self.treeWidget().indexOfTopLevelItem(item)

    def isTopLevelItem(self):
        return self.parent() is None

    def remove(self):
        """Removes the item from its treewidget or parent item."""
        if self.isTopLevelItem() and self.treeWidget():
            self.treeWidget().takeTopLevelItem(self.listIndex())
        elif self.parent():
            self.parent().removeChild(self)
        self.clear(self.dataId()) # remove data object form store

    def setClicked(self, column):
        self.clicked = column, timestamp()

    def setChanged(self, column):
        self.changed = column, timestamp()

    def wasClickedAndChanged(self):
        """Tests if this item was previously clicked and changed in the UI."""
        try:
            deltaTs = abs(self.clicked[1] - self.changed[1])
            return (self.clicked[0] == self.changed[0] and
                    deltaTs < 0.1)
        except StandardError:
            pass
        return False

    def setAlignment(self, alignment):
        if alignment is None:
            return
        if not isList(alignment):
            alignment = [alignment]
        for c in range(0, self.columnCount()):
            self.setTextAlignment(c, alignment[min(c, len(alignment)-1)])

class DataList(QWidget, DropWidget, ContextMenuWidget):
    """
    Manages all loaded spectra.

    >>> from utilsgui import DialogInteraction, DisplayException
    >>> from spectralist import SpectraList
    >>> sl = DialogInteraction.instance(SpectraList)

    Test available actions
    >>> [str(action.text()) for action in sl.listWidget.actions()]
    ['load spectra', 'remove', '', 'save matrices', 'select all']
    >>> sl.listWidget.count()
    0

    Test methods on empty list
    >>> sl.updateSpectra()
    >>> sl.removeSelectedSpectra()
    >>> [sl.getMatrix(i) for i in -1,0,1]
    [None, None, None]
    >>> DialogInteraction.query(DisplayException, sl.saveMatrix,
    ...                         slot = 'accept')
    >>> sl.selectionChangedSlot()

    """
    sigSelectedIndex = Signal((int, int))
    sigSelectedData = Signal((object,))
    sigUpdatedData = Signal((object,))
    sigRemovedData = Signal(list)
    sigReceivedUrls = Signal(list)
    sigEditingFinished = Signal()
    _nestedItems = None # are nested items allowed? (plain list behaviour)

    def __init__(self, parent = None, title = None, withBtn = True,
                 nestedItems = True):
        QWidget.__init__(self, parent)
        ContextMenuWidget.__init__(self)
        self.title = TitleHandler.setup(self, title)
        self._nestedItems = nestedItems
        self._setupUi(withBtn)
        self._setupActions()
        self.setupUi()
        QMetaObject.connectSlotsByName(self)

    def _setupUi(self, withBtn):
        self.setObjectName("DataList")
        self.setAcceptDrops(True)
        self.verticalLayout = QVBoxLayout(self)
        self.verticalLayout.setObjectName("verticalLayout")
        if withBtn:
            self.loadBtn = QPushButton(self)
            self.loadBtn.setText(tr("load"))
            self.loadBtn.setObjectName("loadBtn")
            self.loadBtn.released.connect(self.loadData)
            self.verticalLayout.addWidget(self.loadBtn)
        self.listWidget = QTreeWidget(self)
        self.listWidget.setHeaderHidden(True)
        self.listWidget.setContextMenuPolicy(Qt.ActionsContextMenu)
        self.listWidget.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.listWidget.setDragEnabled(True)
        self.listWidget.setDragDropMode(QAbstractItemView.InternalMove)
        self.listWidget.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.listWidget.setObjectName("listWidget")
        self.listWidget.itemSelectionChanged.connect(self.selectionChanged)
        self.listWidget.itemClicked.connect(self._itemClicked)
        self.listWidget.itemChanged.connect(self._itemChanged)
        self.listWidget.itemDoubleClicked.connect(self.itemDoubleClicked)
        self.listWidget.itemExpanded.connect(self.fitColumnsToContents)
        self.listWidget.itemCollapsed.connect(self.fitColumnsToContents)
        self.verticalLayout.addWidget(self.listWidget)
        self.sigReceivedUrls.connect(self.loadData)
        self.clearSelection = self.listWidget.clearSelection

    def _setupActions(self):
        self.addMenuEntry(
            name = "load", text = tr("load %1"), menuStates = "*",
            toolTip = tr("Add one or more %1."),
            callbacks = self.loadData)
        self.addMenuSeparator()
        self.addMenuEntry(
            name = "remove", text = tr("remove"),
            toolTip = tr("Remove selected %1."),
            shortCut = QKeySequence.Delete, menuStates = "isRemovableSelected",
            callbacks = self.removeSelected)
        self.addMenuSeparator("hasSelection")
        self.addMenuSeparator("isNotEmpty")
        self.addMenuEntry(
            name = "selectall", text = tr("select all"),
            shortCut = QKeySequence.SelectAll, menuStates = "isNotEmpty",
            callbacks = self.listWidget.selectAll)
        self.addMenuEntry(
            name = "expandall", text = tr("expand all"),
            toolTip = tr("Show nested items of this %1. (double-click)"),
            callbacks = self.expandAll,
            menuStates = "itemsHaveChildren")
        self._updateContextMenu()

    def _updateContextMenu(self):
        self.updateMenu(self.listWidget)

    def fitColumnsToContents(self, *args):
        for c in range(0, self.listWidget.columnCount()):
            self.listWidget.resizeColumnToContents(c)

    def setupUi(self):
        """Reimplement this in child classes for custom UI configuration."""
        pass

    def leaveEvent(self, event):
        self.sigEditingFinished.emit()

    def clear(self):
        self.listWidget.clear()

    def expandAll(self):
        self.listWidget.expandAll()
        self.fitColumnsToContents()

    def __len__(self):
        return self.listWidget.topLevelItemCount()

    def isEmpty(self):
        return len(self) <= 0

    def isNotEmpty(self):
        return not self.isEmpty()

    def hasSelection(self):
        return len(self.listWidget.selectedItems()) > 0

    def isRemovableSelected(self):
        """True, if there is at least one item selected which may be removed"""
        return self.hasSelection()

    def itemsHaveChildren(self):
        return any([item.childCount() > 0 for item in self.topLevelItems()])

    def setHeader(self, labels = None):
        if not isList(labels):
            return
        self.listWidget.setHeaderLabels(labels)
        self.listWidget.setHeaderHidden(False)
        self.listWidget.setColumnCount(len(labels))

    def updateItems(self):
        for item in self.topLevelItems():
            item.update()
        self.fitColumnsToContents()

    def _itemClicked(self, item, column):
        item.setClicked(column)
        if item.wasClickedAndChanged():
            self.itemUpdate(item, column)

    def _itemChanged(self, item, column):
        item.setChanged(column)
        if item.wasClickedAndChanged():
            self.itemUpdate(item, column)

    def itemUpdate(self, item, column):
        """Reimplement to update item if changed by user in GUI"""
        pass

    def itemDoubleClicked(self, item, column):
        pass

    def currentSelection(self):
        selected = self.listWidget.selectedItems()
        index, data = -1, None
        if len(selected) > 0:
            index = selected[0].listIndex()
            data = selected[0].data()
        return index, data

    def selectionChanged(self):
        index, data = self.currentSelection()
        self.sigSelectedIndex.emit(len(self), index)
        self.sigSelectedData.emit(data)
        self._updateContextMenu()

    def removeSelected(self):
        selected = self.listWidget.selectedItems()
        index = 0
        self.sigRemovedData.emit(self.data(selected))
        for item in selected:
            if not item.isRemovable:
                continue
            index = item.listIndex()
            item.remove()
        # select the next item after the removed ones
        self.listWidget.clearSelection()
        if index >= len(self):
            index = len(self) - 1
        if index >= 0:
            self.listWidget.setCurrentIndex(
                    self.listWidget.indexFromItem(
                        self.listWidget.topLevelItem(index)))
        self.selectionChanged()

    def setCurrentIndex(self, index):
        if index < 0 or index >= len(self):
            return
        item = self.listWidget.topLevelItem(index)
        index = self.listWidget.indexFromItem(item)
        self.listWidget.setCurrentIndex(index)
        self.selectionChanged()

    def add(self, data):
#        print "ADD1", self.topLevelItems()
        # WTF? w/o it returns QTreeWidgetItem instead of DataItem below!
        DataItem(data)
        self.listWidget.addTopLevelItem(DataItem(data))
#        print "ADD2", self.topLevelItems()
        item = self.listWidget.topLevelItem(len(self)-1)
        if not self._nestedItems:
            item.setFlags(int(item.flags()) - int(Qt.ItemIsDropEnabled))
        return item

    def topLevelItems(self):
        return [self.listWidget.topLevelItem(i)
                for i in range(0, len(self))]

    def data(self, indexOrItem = None, selectedOnly = False):
        """
        Returns the list of data for a given list index or list widget item.
        If none is specified return the data of all items or the data of
        selected items only, if desired.
        """
        if type(indexOrItem) is int:
            if indexOrItem < 0 or indexOrItem >= len(self):
                raise IndexError
            items = [self.listWidget.topLevelItem(indexOrItem)]
        elif type(indexOrItem) is DataItem:
            items = [indexOrItem]
        elif (isList(indexOrItem) and
              len(indexOrItem) > 0 and
              type(indexOrItem[0]) is DataItem):
            items = indexOrItem
        else: # no indexOrItem given
            if selectedOnly:
                items = self.listWidget.selectedItems()
            else:
                items = self.topLevelItems()
        return [item.data() for item in items]

    def updateData(self, selectedOnly = False, showProgress = True,
                   updateFunc = None, prepareFunc = None, stopFunc = None,
                   **kwargs):
        """
        Calls the provided function on all data items.

        The object returned by prepareFunc() is forwarded as optional argument
        to updateFunc(dataItem, optionalArguments = None).
        """
        data = self.data(selectedOnly = selectedOnly)
        if data is None or len(data) <= 0:
            self.sigUpdatedData.emit(None)
            return
        progress = None
        if showProgress:
            from gui.utils.progressdialog import ProgressDialog
            progress = ProgressDialog(self, count = len(data))
        updateResult = []
        # check provided stop function
        if (stopFunc is not None and
            not isinstance(stopFunc, collections.Callable)):
            stopFunc = None
        # call provided functions which can raise exceptions
        errorOccured = False # raise error after processing all items
        try:
            # call prepare function
            prepareResult = None
            if prepareFunc is not None:
                prepareResult = prepareFunc(**kwargs)
            if prepareResult is None:
                prepareResult = []
            if not isList(prepareResult):
                prepareResult = [prepareResult,]
            # call update function on each data object
            for item in data:
                try:
                    updateResult.append(
                            updateFunc(item, *prepareResult, **kwargs))
                    if progress is not None and progress.update():
                        break
                    if stopFunc is not None and stopFunc():
                        break
                except StandardError, e:
                    errorOccured = True
                    logging.error(str(e).replace("\n"," ") + " ... skipping")
                    continue
            if progress is not None:
                progress.close()
        except StandardError, e:
            # progress.cancel()
            # catch and display _all_ exceptions in user friendly manner
            # DisplayException(e)
            errorOccured = True
            pass
        if errorOccured:
            self.reraiseLast()
#        self.selectionChanged()
        self.sigUpdatedData.emit(self.currentSelection()[1])
        return updateResult

    def loadData(self, sourceList = None, processSourceFunc = None,
                 showProgress = True, alignment = None, **kwargs):
        """
        Loads a list of data source items.

        processSourceFunc is expected to be a function which gets individual
        elements of sourceList as argument. It returns an arbitrary data item
        which is then added to this data list widget.

        Reimplement it in child classes and it will be called on load button
        and add action signal.

        This method handles exceptions and progress indication.

        Test loading a single spectra
        >>> import utils
        >>> from tests import TestData
        >>> from utilsgui import DialogInteraction, UiSettings, fileDialogType
        >>> from chemsettings import ChemSettings
        >>> from datafiltersgui import DataFiltersGui
        >>> from spectralist import SpectraList
        >>> cs = DialogInteraction.instance(ChemSettings)
        >>> dfg = DialogInteraction.instance(DataFiltersGui)
        >>> sl = DialogInteraction.instance(SpectraList, settings = cs)
        >>> utils.LastPath.path = TestData.spectra(0)
        >>> DialogInteraction.query(fileDialogType(), sl.loadData,
        ...                         slot = 'accept')
        >>> sl.updateSpectra()
        >>> utils.LastPath.path = utils.getTempFileName()
        >>> matrixfiles = DialogInteraction.query(fileDialogType(), sl.saveMatrix,
        ...                                       slot = 'accept')
        >>> len(matrixfiles)
        1
        >>> matrixfiles

        Verify written matrix data with existent matrix export
        >>> TestData.verifyMatrix(TestData.spectra(0),
        ...                       matrixfiles[0])
        True
        """
        assert processSourceFunc is not None
        assert isList(sourceList)
        progress = None
        if showProgress:
            from gui.utils.progressdialog import ProgressDialog
            progress = ProgressDialog(self, count = len(sourceList))
        self.listWidget.clearSelection()
        errorOccured = False
        lastItem = None
        for sourceItem in sourceList:
            data = None
            try:
                data = processSourceFunc(sourceItem, **kwargs)
            except StandardError, e:
                # progress.cancel()
                # DisplayException(e)
                # on error, skip the current file
                errorOccured = True
                logging.error(str(e).replace("\n"," ") + " ... skipping")
                continue
            if data is not None:
                lastItem = self.add(data)
                lastItem.setAlignment(alignment)
            if progress is not None and progress.update():
                break
        if progress is not None:
            progress.close()
        self.fitColumnsToContents()
        # notify interested widgets about changes
        if lastItem is not None:
            self.listWidget.setCurrentItem(lastItem)
        if errorOccured:
            self.reraiseLast()

    def reraiseLast(self):
        """Reraise the last error if any and display an error message dialog.
        """
        try:
            if sys.exc_info()[0] is not None:
                raise
        except StandardError, e:
            DisplayException(e)

if __name__ == "__main__":
    import doctest
    doctest.testmod()

# vim: set ts=4 sw=4 sts=4 tw=0: