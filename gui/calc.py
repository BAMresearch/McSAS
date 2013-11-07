# -*- coding: utf-8 -*-
# calc.py

import sys
import logging
import time
import os.path
import ConfigParser
import numpy
import numpy as np
from cutesnake.qt import QtCore
from QtCore import QUrl
from cutesnake.dataset import DataSet, DisplayMixin
from cutesnake.utils import isList
from cutesnake.utils.lastpath import LastPath
from cutesnake.datafile import PDHFile, AsciiFile
from cutesnake.utilsgui.displayexception import DisplayException
from cutesnake.log import timestamp, addHandler
import cutesnake.log as log
from McSAS import McSAS

class SASData(DataSet, DisplayMixin):
    _sizeEst = None
    _emin = 0.01 # minimum possible error (1%)
    _uncertainty = None

    @staticmethod
    def displayDataDescr():
        return ("filename", "data points", "est. sphere size")

    @property
    def displayData(self):
        return ("title", "count", "sphericalSizeEstText")

    @property
    def count(self):
        return len(self.q())

    @property
    def sphericalSizeEstText(self):
        return "min: {0:.4f}, max: {1:.4f}".format(*self.sphericalSizeEst())

    @classmethod
    def load(cls, filename):
        if not os.path.isfile(filename):
            logging.warning("File '{0}' does not exist!".format(filename))
            return
        logging.info("Loading '{0}' ...".format(filename))

        if str(filename[-4:]).lower() == '.pdh':
            sasFile = PDHFile(filename)
        else:
            sasFile = AsciiFile(filename) # works for CSV too

        sasData = cls(sasFile.name, sasFile.data)
        return sasData

    def q(self):
        return self.origin[:, 0]

    def i(self):
        return self.origin[:, 1]

    def __init__(self, *args):
        DataSet.__init__(self, *args)
        self._sizeEst = np.array([np.pi/np.max(self.q()), np.pi/np.min(self.q())])
        self.prepareUncertainty()

    def sphericalSizeEst(self):
        return self._sizeEst

    def minUncertainty(self):
        return self._emin

    def prepareUncertainty(self):
        self._uncertainty = self.minUncertainty() * self.i()
        minUncertaintyPercent = self.minUncertainty() * 100.
        if self.origin.shape[1] < 3:
            logging.warning("No error column provided! Using {}% of intensity."
                            .format(minUncertaintyPercent))
        else:
            count = sum(self._uncertainty > self.origin[:, 2])
            if count > 0:
                logging.warning("Minimum uncertainty ({}% of intensity) set "
                                "for {} datapoints.".format(
                                minUncertaintyPercent, count))
            self._uncertainty = np.maximum(self._uncertainty, self.origin[:, 2])

    def uncertainty(self):
        return self._uncertainty

class Calculator(object):
    _algo = None # McSAS algorithm instance
    # static settings, move this to global app settings later
    indent = "    "
    nolog = False

    @staticmethod
    def paramNames():
        """Names of parameters which will be configurable by the user in a UI.
        """
        return ("convergenceCriterion", "histogramBins", "numReps",
                "numContribs", "findBackground")

    def __init__(self):
        self._algo = McSAS.factory()()

    def params(self):
        """Returns a sub set of parameters defined in paramNames()"""
        # access the property to be able to change it permanently
        return [getattr(self._algo, pname) for pname in self.paramNames()]

    @property
    def model(self):
        return self._algo.model

    @model.setter
    def model(self, newModel):
        self._algo.model = newModel

    def modelParams(self):
        # access the property to change it permanently
        return [getattr(self.model, p.name()) for p in self.model.params()]

    def stop(self):
        self._algo.stop = True

    def __call__(self, dataset):
        # start log file writing
        self._title = dataset.title
        fn = self._getResultFilename("log", "this log")
        logFile = logging.FileHandler(fn, encoding = "utf8")
        oldHandler = log.log.handlers[0]
        log.addHandler(logFile)

        bounds = dataset.sphericalSizeEst()
        logging.info("The following parameters are used for 'Analyze_1D':")
        logging.info("bounds: [{0:.4f}; {1:.4f}]"
                     .format(bounds[0], bounds[1]))
        mcargs = dict(Emin = dataset.minUncertainty(), 
                      contribParamBounds = bounds,
                      doPlot = False)
        self._writeSettings(mcargs, dataset)
        if self.nolog:
            log.removeHandler(oldHandler)
        self._algo.figureTitle = os.path.basename(self.basefn)
        self._algo.calc(Q = dataset.q(), I = dataset.i(),
                        IError = dataset.uncertainty(), **mcargs)
        if self.nolog:
            log.addHandler(oldHandler)

        if isList(self._algo.result) and len(self._algo.result):
            res = self._algo.result[0]
            if res is not None:
                self._writeDistrib(res)
                self._writeFit(res)
                self._algo.plot()
        else:
            logging.info("No results available!")

        log.removeHandler(logFile)

    def _writeFit(self, mcResult):
        self._writeResultHelper(mcResult, "fit", "fit data",
            ('fitQ', 'fitIntensityMean', 'fitIntensityStd')
        )

    def _writeDistrib(self, mcResult):
        self._writeResultHelper(mcResult, "dist", "distributions",
            ('histogramXMean', 'histogramXWidth', 'volumeHistogramYMean',
             'volumeHistogramYStd', 'volumeHistogramMinimumRequired',
             'numberHistogramYMean', 'numberHistogramYStd',
             'numberHistogramMinimumRequired')
        )

    def _writeSettings(self, mcargs, dataset):
        fn = self._getResultFilename("settings", "algorithm settings")
        config = ConfigParser.RawConfigParser()
        sectionName = "I/O Settings"
        config.add_section(sectionName)
        # do we really want to store absolute path names?
        # -> with SASfit, users often transfer output files across systems
        #    and what to do when loading/interpreting a abs. path
        #    on another machine?
        config.set(sectionName, 'dataPath', LastPath.get())

        # the filename w/o extension, see SASData.load()
        config.set(sectionName, 'fileName', dataset.title)
        # the filename with timestamp of results
        config.set(sectionName, 'outputBaseName', os.path.basename(self.basefn))

        sectionName = "MCSAS Settings"
        config.add_section(sectionName)
        for key, value in mcargs.iteritems():
            config.set(sectionName, key, value)
        for p in self.params():
            config.set(sectionName, p.name(), p.value())
        config.set(sectionName, "model", self.model.name())
        sectionName = "Model Settings"
        config.add_section(sectionName)
        for p in self.modelParams():
            config.set(sectionName, p.name(), p.value())
            config.set(sectionName, p.name()+"_min", p.min())
            config.set(sectionName, p.name()+"_max", p.max())
        with open(fn, 'w') as configfile:
            config.write(configfile)

    def _getResultFilename(self, fileKey, descr):
        fn = self._getFilename(fileKey)
        logging.info("Writing {0} to:".format(descr))
        logging.info("{0}'{1}'".format(self.indent,
                                       QUrl.fromLocalFile(fn).toEncoded()))
        return fn

    def _writeResultHelper(self, mcResult, fileKey, descr, columnNames):
        fn = self._getResultFilename(fileKey, descr)
        logging.info("Containing the following columns:")
        for cn in columnNames:
            logging.info("{0}[ {1} ]".format(self.indent, cn))
        #write header:
        AsciiFile.writeHeaderLine(fn,columnNames)
        #(additional header lines can be appended if necessary)
        data = np.vstack([mcResult[cn] for cn in columnNames]).T
        #append to the header, do not overwrite:
        AsciiFile.appendFile(fn, data)

    def _getFilename(self, kind):
        """Creates a file name from data base name, its directory and the
        current timestamp. It's created once so that all output files have
        the same base name and timestamp."""
        if not hasattr(self, "basefn") or self.basefn is None:
            self.basefn = "{0}_{1}".format(
                    os.path.join(LastPath.get(), self._title), log.timestamp())
        return "{0}_{1}.txt".format(self.basefn, kind)

# vim: set ts=4 sts=4 sw=4 tw=0:
