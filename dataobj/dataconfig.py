# -*- coding: utf-8 -*-
# dataobj/dataconfig.py

from __future__ import absolute_import # PEP328

from abc import ABCMeta, abstractproperty
import numpy
from bases.algorithm import AlgorithmBase
from utils.parameter import Parameter
from utils.mixedmethod import mixedmethod
from utils.units import NoUnit
from utils import isCallable

class CallbackRegistry(object):
    _callbacks = None # registered callbacks on certain events

    @abstractproperty
    def callbackSlots(self):
        raise NotImplementedError

    def register(self, what, func):
        # check for the correct number of arguments of func as well?
        assert isCallable(func)
        self._assertPurpose(what)
        if self._callbacks is None: # lazy init
            self._callbacks = dict()
        if what not in self._callbacks:
            self._callbacks[what] = []
        if func not in self._callbacks[what]:
            self._callbacks[what].append(func)

    def callback(self, what, *args, **kwargs):
        self._assertPurpose(what)
        if self._callbacks is None:
            return
        funcLst = []
        for func in self._callbacks.get(what, []):
            if not isCallable(func):
                continue
            func(*args, **kwargs)
            funcLst.append(func)
        # update the callback list, invalid functions removed
        self._callbacks[what] = funcLst

    def _assertPurpose(self, what):
        assert what in self.callbackSlots, (
            "'{}' not in predefined callback slots '{}'"
            .format(what, self.callbackSlots))

class DataConfig(AlgorithmBase, CallbackRegistry):
    parameters = (
        Parameter("x0Low", 0., unit = NoUnit(),
            displayName = "lower {x0} cut-off",
            valueRange = (0., numpy.inf), decimals = 1),
        Parameter("x0High", numpy.inf, unit = NoUnit(),
            displayName = "upper {x0} cut-off",
            valueRange = (0., numpy.inf), decimals = 1),
        Parameter("x1Low", 0., unit = NoUnit(),
            displayName = "lower {x1} cut-off",
            valueRange = (0., numpy.inf), decimals = 1),
        Parameter("x1High", numpy.inf, unit = NoUnit(),
            displayName = "upper {x1} cut-off",
            valueRange = (0., numpy.inf), decimals = 1),
        Parameter("fMaskZero", False, unit = NoUnit(),
            displayName = "Mask {f} values of 0", description =
            "Renders intensity values that are zero invalid for fitting"),
        Parameter("fMaskNeg", False, unit = NoUnit(),
            displayName = "Mask negative {f} values", description =
            "Renders negative intensity values invalid for fitting"),
    )

    @property
    def showParams(self):
        lst = super(DataConfig, self).showParams
        if not self.is2d: # put psi settings right behind q settings
            lst.remove("x1Low")
            lst.remove("x1High")
        return lst

    @property
    def callbackSlots(self):
        return set(("x0limits", "x1limits", "fMasks"))

    def __init__(self):
        super(DataConfig, self).__init__()
        self.x0Low.setOnValueUpdate(self.updateX0Limits)
        self.x0High.setOnValueUpdate(self.updateX0Limits)
        self.x1Low.setOnValueUpdate(self.updateX1Limits)
        self.x1High.setOnValueUpdate(self.updateX1Limits)
        self.fMaskZero.setOnValueUpdate(self.updateFMasks)
        self.fMaskNeg.setOnValueUpdate(self.updateFMasks)

    def updateX0Limits(self):
        self._onLimitUpdate(self.x0Low, self.x0High, "x0limits")

    def updateX1Limits(self):
        self._onLimitUpdate(self.x1Low, self.x1High, "x1limits")

    def _onLimitUpdate(self, pLow, pHigh, callbackName):
        if not pLow() <= pHigh():
            temp = pLow()
            pLow.setValue(pHigh())
            pHigh.setValue(temp)
        self.callback(callbackName, (pLow(), pHigh()))

    def updateFMasks(self):
        self.callback("fMasks", (self.fMaskZero(), self.fMaskNeg()))

    def setX0ValueRange(self, limits):
        """Sets available range of loaded data."""
        self.x0Low.setValueRange(limits)
        self.x0High.setValueRange(limits)

    def setX1ValueRange(self, limits):
        pass

# vim: set ts=4 sts=4 sw=4 tw=0:
