# -*- coding: utf-8 -*-
# dataobj/sasconfig.py

import logging
from abc import ABCMeta
import numpy as np
from scipy import stats
from future.utils import with_metaclass

from ..bases.algorithm import AlgorithmBase
from ..utils.parameter import Parameter
from ..utils.units import (ScatteringIntensity, ScatteringVector, Angle,
                         NoUnit)
from ..utils import clip
from . import DataConfig

class SmearingConfig(with_metaclass(ABCMeta, AlgorithmBase)):
    """Abstract base class, can't be instantiated."""
    _qOffset = None # integration point positions, depends on beam profile
    _weights = None # integration weight per position, depends on beam profile
    shortName = "SAS smearing configuration"
    parameters = (
        Parameter("doSmear", False, unit = NoUnit(),
            displayName = "Apply smearing correction",
            ),
        Parameter("nSteps", 25, unit = NoUnit(),
            displayName = "number of smearing points around each q",
            valueRange = (0, 1000)),
        # 2-d collimated systems require a different smearing than
        # slit-collimated data
        Parameter("twoDColl", False, unit = NoUnit(),
            displayName = "Slit-smeared data (unchecked), or 2D-averaged "
                          "data (checked)",
            ),
#        Parameter("collType", u"Slit", unit = NoUnit(),
#            displayName = "Type of collimation leading to smearing",
#            valueRange = [u"Slit", u"Pinhole", u"Rectangular", u"None"])
    )

    def updateQUnit(self, newUnit):
        assert isinstance(newUnit, ScatteringVector)

    def updateQLimits(self, qLimit):
        pass

    def updatePUnit(self, newUnit):
        assert isinstance(newUnit, Angle)

    def updatePLimits(self, pLimit):
        pass

    def updateSmearingLimits(self, q):
        pass

    @property
    def qOffset(self):
        return self._qOffset

    @property
    def weights(self):
        return self._weights

    @property
    def prepared(self):
        return self._qOffset, self._weights

    def __str__(self):
        s = [str(id(self)) + " " + super(SmearingConfig, self).__str__()]
        s.append("  qOffset: {}".format(self.qOffset))
        s.append("  weights: {}".format(self.weights))
        return "\n".join(s)

    def hdfWrite(self, hdf):
        super(SmearingConfig, self).hdfWrite(hdf)
        hdf.writeMembers(self, 'qOffset', 'weights')

class TrapezoidSmearing(SmearingConfig):
    parameters = (
        Parameter("umbra", 0., unit = NoUnit(), # unit set outside
            displayName = "top width of <br />trapezoidal beam profile",
            description = "full top width of the trapezoidal beam profile "
                          "(horizontal for slit-collimated systems, "
                          "circularly averaged for 2D pinhole and "
                          "rectangular slit)",
            valueRange = (0., np.inf), decimals = 9),
        Parameter("penumbra", 0., unit = NoUnit(), # unit set outside
            displayName = "bottom width of <br />trapezoidal beam profile",
            description = "full bottom width of the trapezoidal beam profile "
                          "horizontal for slit-collimated systems, circularly "
                          "averaged for 2D pinhole and rectangular slit)",
            valueRange = (0., np.inf), decimals = 9),
    )

    def inputValid(self):
        # returns True if the input values are valid
        return (self.umbra() > 0.) and (self.penumbra() > self.umbra())

    @property
    def showParams(self):
        lst = ["umbra", "penumbra"]
        return [name
                for name in super(TrapezoidSmearing, self).showParams
                    if name not in lst] + lst

    def halfTrapzPDF(self, x, c, d):
        # this trapezoidal PDF is only defined from X >= 0, and is assumed
        # to be mirrored around that point.
        # Note that the integral of this PDF from X>0 will be 0.5.
        # source: van Dorp and Kotz, Metrika 2003, eq (1)
        # using a = -d, b = -c
        logging.debug("halfTrapzPDF called")
        assert(d > 0.)
        x = abs(x)
        pdf = x * 0.
        pdf[x < c] = 1.
        if d > c:
            pdf[(c <= x) & (x < d)] = (1./(d - c)) * (d - x[(c <= x) & (x < d)])
        norm = 1./(d + c)
        pdf *= norm
        return pdf, norm

    def setIntPoints(self, q):
        """ sets smearing profile integration points for trapezoidal slit. 
        Top (umbra) of trapezoid has full width xt, bottom of trapezoid 
        (penumbra) has full width.
        Since the smearing function is assumed to be symmetrical, the 
        integration parameters are calculated in the interval [0, xb/2]
        """
        n, xt, xb = self.nSteps(), self.umbra(), self.penumbra()
        logging.debug("setIntPoints called with n = {}".format(n))

        # following qOffset is used for Pinhole and Rectangular
        qOffset = np.logspace(np.log10(q.min() / 5.),
                np.log10(xb / 2.), num = np.ceil(n / 2.))
        qOffset = np.concatenate((-qOffset[::-1], [0,], qOffset))
        if not self.twoDColl():
            # overwrite prepared integration steps qOffset:
            qOffset = np.logspace(np.log10(q.min() / 5.),
                    np.log10(xb / 2.), num = n)
            # tack on a zero at the beginning
            qOffset = np.concatenate(([0,], qOffset))

        y, dummy = self.halfTrapzPDF(qOffset, xt, xb)

        # volume fraction still off by a factor of two (I think). Can be
        # fixed by multiplying y with 0.5, but need to find it first in eqns.
                # volume fraction still off by a factor of two (I think). Can be
                # fixed by multiplying y with 0.5, but need to find it first in eqns.
        self._qOffset, self._weights = qOffset, y

    def updateQUnit(self, newUnit):
        super(TrapezoidSmearing, self).updateQUnit(newUnit)
        self.umbra.setUnit(newUnit)
        self.penumbra.setUnit(newUnit)

    def updateQLimits(self, qLimit):
        qLow, qHigh = qLimit
        self.umbra.setValueRange((0., 2. * qHigh))
        self.penumbra.setValueRange((0., 2. * qHigh))

    def updatePUnit(self, newUnit):
        super(TrapezoidSmearing, self).updatePUnit(newUnit)
        # TODO

    def updatePLimits(self, pLimit):
        pLow, pHigh = pLimit
        # TODO

    def updateSmearingLimits(self, q):
        super(TrapezoidSmearing, self).updateSmearingLimits(q)
        low, high = np.absolute(np.diff(q)).min(), q.max()
        self.umbra.setValueRange((low, 2. * high))
        self.penumbra.setValueRange((low, 2. * high))

    def __init__(self):
        super(TrapezoidSmearing, self).__init__()
        self.umbra.setOnValueUpdate(self.onUmbraUpdate)

    def onUmbraUpdate(self):
        """Value in umbra will not exceed available q."""
        # value in penumbra must not be smaller than umbra
        self.penumbra.setValueRange((self.umbra(), self.penumbra.max()))

TrapezoidSmearing.factory()

class GaussianSmearing(SmearingConfig):
    parameters = (
        Parameter("variance", 0., unit = NoUnit(), # unit set outside
            displayName = u"Variance (σ²) of <br /> Gaussian beam profile",
            #displayName = u"Variance (&sigma;<sup>2</sup>)",
            description = "Full width at half maximum of the Gaussian beam"
                          "profile (horizontal for slit-collimated systems, "
                          "circularly averaged for 2D pinhole and rectangular "
                          "slit)",
            valueRange = (0., np.inf), decimals = 9),
    )

    def inputValid(self):
        # returns True if the input values are valid
        return (self.variance() > 0.)

    @property
    def showParams(self):
        lst = ["variance"]
        return [name
                for name in super(GaussianSmearing, self).showParams
                    if name not in lst] + lst

    def setIntPoints(self, q):
        """Sets smearing profile integration points for trapezoidal slit.
        Top (umbra) of trapezoid has full width xt, bottom of trapezoid
        (penumbra) has full width.
        Since the smearing function is assumed to be symmetrical, the
        integration parameters are calculated in the interval [0, xb/2]
        """
        n, GVar = self.nSteps(), self.variance()
        logging.debug("setIntPoints called with n = {}".format(n))

        # following qOffset is used for Pinhole and Rectangular
        qOffset = np.logspace(np.log10(q.min() / 3.),
                np.log10(2.5 * GVar), num = np.ceil(n / 2.))
        qOffset = np.concatenate((-qOffset[::-1], [0,], qOffset))
        if not self.twoDColl():
            # overwrite prepared integration steps qOffset:
            qOffset = np.logspace(np.log10(q.min() / 3.),
                    np.log10(2.5 * GVar), num = n)
            # tack on a zero at the beginning
            qOffset = np.concatenate(([0,], qOffset))

        y = stats.norm.pdf(qOffset, scale = GVar)

        logging.debug("qOffset: {}, y: {}".format(qOffset, y))
        self._qOffset, self._weights = qOffset, y

    def updateQUnit(self, newUnit):
        super(GaussianSmearing, self).updateQUnit(newUnit)
        self.variance.setUnit(newUnit)

    def updateQLimits(self, qLimit):
        qLow, qHigh = qLimit
        self.variance.setValueRange((0., 2. * qHigh))

    def updatePUnit(self, newUnit):
        super(GaussianSmearing, self).updatePUnit(newUnit)
        # TODO

    def updatePLimits(self, pLimit):
        pLow, pHigh = pLimit
        # TODO

    def updateSmearingLimits(self, q):
        super(GaussianSmearing, self).updateSmearingLimits(q)
        # it seems, diff(q) can be negative
        low, high = np.absolute(np.diff(q)).min(), q.max()
        self.variance.setValueRange((low, 2. * high))

    def __init__(self):
        super(GaussianSmearing, self).__init__()

GaussianSmearing.factory()

class SASConfig(DataConfig):
    # TODO: fix UI elsewhere for unit selection along to each input and forward
    #       that to the DataVector
    _smearing = None
    shortName = "SAS data configuration"

    @property
    def showParams(self):
        lst = super(SASConfig, self).showParams
        lst.remove("fMaskZero")
        lst.remove("fMaskNeg")
        return lst

    def onUpdatedX0(self, x0):
        """Sets available range of loaded data."""
        super(SASConfig, self).onUpdatedX0(x0)
        if self.smearing is None:
            return
        self.smearing.updateQLimits((self.x0Low(), self.x0High()))
        self.smearing.updateSmearingLimits(x0)

    def onUpdatedX1(self, x1):
        super(SASConfig, self).onUpdatedX1(x1)
        # TODO

    def updateX0Unit(self, newUnit):
        super(SASConfig, self).updateX0Unit(newUnit)
        if self.smearing is None:
            return
        self.smearing.updateQUnit(newUnit)

    def updateX1Unit(self, newUnit):
        super(SASConfig, self).updateX1Unit(newUnit)
        if self.smearing is None:
            return
        self.smearing.updatePUnit(newUnit)

    @property
    def smearing(self):
        return self._smearing

    @smearing.setter
    def smearing(self, newSmearing):
        assert isinstance(newSmearing, SmearingConfig)
        self._smearing = newSmearing

    def prepareSmearing(self, q):

        assert( isinstance(q, np.ndarray))
        assert( q.ndim == 1)
        logging.debug("PrepareSmearing called!")

        if self.smearing is None:
            logging.warning("not smearing: self.smearing is None")
            return q
        if not self.smearing.inputValid():
            logging.warning("not smearing: Smearing parameters not valid")
            return q
        if not self.smearing.doSmear():
            logging.warning("not smearing: Smearing disabled")
            return q
        self.smearing.setIntPoints(q)
        qOffset, weights = self.smearing.prepared
        #print >>sys.__stderr__, "prepareSmearing"
        #print >>sys.__stderr__, unicode(self)
        # calculate the intensities at sqrt(q**2 + qOffset **2)
        if not self.smearing.twoDColl(): # slit collimation
            logging.debug("prepareSmearing called for slit collimation")
            logging.debug("q.shape: {}, qOffset.shape: {}".format(q.shape, qOffset.shape))
            return np.sqrt(np.add.outer(q **2, qOffset **2))
        else:
            logging.debug("prepareSmearing called for pinhole collimation")
            # Non-slit-smeared instruments, using azimuthally averaged
            # 2D-pattern (assumed!) with equally averaged beam profile.
            logging.debug("q.shape: {}, qOffset.shape: {}".format(q.shape, qOffset.shape))
            logging.debug("qOffset.min: {}, qOffset.max: {}"
                    .format(qOffset.min(), qOffset.max()))
            return np.add.outer(q, qOffset)

    def __init__(self, *args, **kwargs):
        super(SASConfig, self).__init__()
        smearing = kwargs.pop("smearing", None)
        if smearing is None:
            smearing = TrapezoidSmearing()
            # smearing = GaussianSmearing()
        if not isinstance(self.smearing, SmearingConfig):
            # is already set when unpickling
            self.smearing = smearing
        if self.smearing is not None:
            self.register("x0limits", self.smearing.updateQLimits)
            self.register("x1limits", self.smearing.updatePLimits)

    def __eq__(self, other):
        if not isinstance(other, type(self)):
            return False
        equal = ((self.smearing == other.smearing) and
                super(SASConfig, self).__eq__(other))
        return equal

    def __str__(self):
        return "\n".join((
            super(SASConfig, self).__str__(),
            str(self.smearing)
        ))

    def hdfWrite(self, hdf):
        super(SASConfig, self).hdfWrite(hdf)
        hdf.writeMember(self, 'smearing')

SASConfig.factory() # check class variables

# vim: set ts=4 sts=4 sw=4 tw=0:
