# -*- coding: utf-8 -*-
# models/scatteringmodel.py

from abc import ABCMeta, abstractmethod
import numpy
from cutesnake.utils import isList, mixedmethod
from cutesnake.algorithm import AlgorithmBase
from utils.propertynames import PropertyNames

class ScatteringModel(AlgorithmBase, PropertyNames):
    __metaclass__ = ABCMeta
    compensationExponent = 0.5 # default

    def updateParamBounds(self, bounds):
        if not isList(bounds):
            bounds = [bounds,]
        if not isinstance(bounds, list):
            bounds = list(bounds)
        return bounds

    # it doesn't belong to the model?
    # should be instrumentation geometry ...
    def smear(self, arg):
        return arg

    @abstractmethod
    def vol(self, paramValues, compensationExponent = None):
        """Calculates the volume of this model, taking compensationExponent
        into account from input or preset parameters."""
        if self.paramCount() == 0 and paramValues is None:
            return True
        # by definition, no vector input, would require complex model code
        return len(paramValues) == self.paramCount()

    @abstractmethod
    def ff(self, dataset, paramValues = None):
        """Calculates the Rayleigh function of this model."""
        if self.paramCount() == 0 or paramValues is None:
            return True
        # by definition, no vector input, would require complex model code
        return len(paramValues) == self.paramCount()

    def generateParameters(self, count = 1):
        """Generates a set of parameters for this model using the predefined
        Parameter.generator. Allows for different random number distributions.
        """
        lst = numpy.zeros((count, self.paramCount()))
        for idx, param in enumerate(self.params()):
            # generate numbers in different range for each parameter
            #only for active parameters, otherwise it may try to generate
            #random values for a boolean-type parameter.
            if param.isActive():
                lst[:, idx] = param.generate(count = count)
        # output count-by-nParameters array
        return lst

    @mixedmethod
    def activeParams(setforcls):
        """returns all "active" parameters of this algorithm"""
        aPars = [par for par in setforcls.params() if par.isActive()]
        return tuple(aPars)

    @mixedmethod
    def activeParamCount(setforcls):
        return len(setforcls.activeParams())

# vim: set ts=4 sts=4 sw=4 tw=0:
