# -*- coding: utf-8 -*-
# mcsas/plotting.py
"""
Defines the format of the final report on success of an MC fit. 
"""

import logging
import inspect
import os.path
import numpy as np # For arrays
import matplotlib

from ..utils import isList, isString, isMac, isNumber
from ..utils.units import Unit, NoUnit
from mcsas import log
from ..main import makeAbsolutePath
from ..dataobj import SASData

# set up matplotlib.pyplot, do this *before* importing pyplot
try:
    # actually, we're using the TkAgg backend via matplotlibrc (Windows/Linux)
    # otherwise it crashes because of multiple GUI threads ... (only one allowed)
    import PySide # verify/test that we have pyside
    if isMac():
        matplotlib.rcParams['backend'] = 'Qt4Agg'
        matplotlib.rcParams['backend.qt4'] = 'PySide'
    else:
        matplotlib.rcParams['backend'] = 'TkAgg'
except ImportError:
    pass # no pyside

if not isMac():
    matplotlib.rcParams['backend'] = 'TkAgg'

import matplotlib.font_manager as fm
from matplotlib import gridspec
from matplotlib.pyplot import (figure, xticks, yticks, errorbar, bar,
        text, plot, grid, legend, title, xlim, ylim, sca, gca, axis,
        close, colorbar, imshow, subplot, axes, show, savefig,
        get_current_fig_manager)

PM = u"\u00B1"

def getTextSize(fig, fontProps):
    """Returns the width and height of a character for the given font setup.
    This can be different on each platform.
    """
    testText = "TEST"
    r = fig.canvas.get_renderer()
    t = text(0.5, 0.5, testText, fontproperties = fontProps)
    bb = t.get_window_extent(renderer=r)
    w, h = bb.width, bb.height
    t.remove()
    return w / len(testText), h

class CoordinateFormat(object):
    """A Function object which sets up the particular formatting with axis
    name and associated unit at initialization time and formats plot
    coordinates given as (x,y) pair."""
    _xunit, _yunit = None, None
    _fmt = u"{name} = {value}{unit}"
    _valueFmt = u"1.4g"

    def __init__(self, xname, xunit, yname, yunit):
        xu = u""
        if isinstance(xunit, Unit) and not isinstance(xunit, NoUnit):
            xu = xunit.displayMagnitudeName
        yu = u""
        if isinstance(yunit, Unit) and not isinstance(yunit, NoUnit):
            yu = yunit.displayMagnitudeName
        self._fmt = ", ".join((
            self._fmt.format(name = xname, unit = xu,
                             value = u"{x:" + self._valueFmt + "}"),
            self._fmt.format(name = yname, unit = yu,
                             value = u"{y:" + self._valueFmt + "}")))

    def __call__(self, x, y):
        return self._fmt.format(x = x, y = y)

class PlotResults(object):
    """
    This function plots the output of the Monte-Carlo procedure in two
    windows, with the left window the measured signal versus the fitted
    measVal (on double-log scale), and the righthand window the size
    distribution.
    """

    _errorBarOpts = {
            "fmt" : 'k.',
            "ecolor" : 'k',
            "elinewidth" : 2,
            "capsize" : 4,
            "ms" : 5,
            "lw" : 2,
            "solid_capstyle" : 'round',
            "solid_joinstyle" : 'miter'
    }
    # for some reason 'small' didn't work reliably and consistently with
    # py2&py3, sometimes info boxes show up with different text sizes
    # although the matplotlib version is the same for both (1.3.1)
    _infoTextFontSize = 10 # 'small'
    _infoText = {
            "size" : _infoTextFontSize,
            "horizontalalignment" : 'center',
            "multialignment" : 'center',
            "verticalalignment" : 'center'
    }
    _result = None
    _dataset = None
    _axisMargin = None
    _figureTitle = None
    _BG = None
    _SC = None
    _plotfont = None
    _textfont = None
    _monofont = None
   
    def __init__(self, allRes, dataset, axisMargin = 0.3,
                 outputFilename = None, modelData = None, autoClose = False,
                 logToFile = False, queue = None):

        # set up multiprocessing compatible logging
        # redirect to file if requested, a workaround for the moment
        if logToFile and outputFilename is not None:
            fn = outputFilename.filename("plotlog")
            fileHandler = logging.FileHandler(fn, encoding = "utf8")
            log.replaceHandler(fileHandler)

        if not isList(allRes) or not len(allRes):
            logging.info("There are no results to plot, breaking up.")
            return

        # set parameters
        self._result = allRes[0]
        self._dataset = dataset
        self._axisMargin = 0.0 # does not have any effect, it seems
        try:
            self._figureTitle = outputFilename.basename
        except AttributeError:
            self._figureTitle = ""
        self._modelData = modelData
        if self._modelData is None:
            self._modelData = dict()
        self._BG = self._result.get('background', (0., 0.))
        self._SC = self._result.get('scaling', (0., 0.))

        # set plot font
        fontFamilyArial = ["Arial", "Bitstream Vera Sans", "sans-serif"]
        self._plotfont = fm.FontProperties(family = fontFamilyArial)
        # DejaVu shows UTF8 superscript minus properly
        fontPath = makeAbsolutePath("resources/dejavuserif.ttf")
        self._textfont = fm.FontProperties(fname = fontPath)
        fontPath = makeAbsolutePath("resources/dejavumono.ttf")
        self._monofont = fm.FontProperties(fname = fontPath)
        self._infoText['fontproperties'] = self._monofont

        yscale = 'linear'
        if isinstance(dataset, SASData):
            yscale = 'log'
        # set general axes settings:
        self._AxDict = dict(
                facecolor = (.97, .97, .97),
                xscale = "log", yscale = yscale)

        # number of histograms:
        self._nHists = len(self._modelData.get('histograms', ()))
        self._nR = 1
        # number of ranges: 
        if False and self._nHists > 0: # disabled for testing
            self._ranges = ( self._modelData.get('histograms')[0].ranges )
            self._nR = len( self._ranges )

        # initialise figure:
        self._fig, self._ah = self.figInit(self._nHists, 
                self._figureTitle, self._nR)

        # show all ranges:
        for rangei in range(self._nR):
            
            #plot measVal fit:
            if dataset.is2d:
                # dysfunctional
                pass
                # psi = data[:, 3]
                # measVal2d = allRes['measVal2d']
                # qAxis = ax[self._nHists + nR]
                # self.plot2D(self._q, psi, self._measVal, measVal2d, qAxis)

            else:
                # 1D data
                qAxis = self._ah[rangei * 2 * (self._nHists + 1) 
                    + self._nHists + 1]
                fitX0 = self._result['fitX0']
                fitMeasVal = self._result['fitMeasValMean'][0,:]
                if isinstance(dataset, SASData):
                    fitX0 = np.sort(self._result['fitX0'])
                    fitMeasVal = self._result['fitMeasValMean'][0, 
                            np.argsort(self._result['fitX0'])]
                self.plot1D(dataset,
                        fitX0, fitMeasVal, qAxis)

            ## Information on the settings can be shown here:
            InfoAxis = self._ah[rangei * 2 * (self._nHists + 1)]
            # make active:
            self.plotInfo(InfoAxis)
            sca(InfoAxis)

            # plot histograms
            # https://stackoverflow.com/a/952952
            for hi, parHist in enumerate(self._modelData.get('histograms', ())):
                plotPar = parHist.param
                # prep axes:
                hAxis = self._ah[hi + (self._nHists + 1) + 1]

                # plot partial contribution in qAxis
                # not yet available, need to find partial intensities:
                # print sort(dict(inspect.getmembers(parHist)).keys())
                # fitMeasVal, fitSTD = parStat.measVal
                # self.plotPartial(fitX0, fitMeasVal, fitSTD, qAxis)

                self.plotHist(plotPar, parHist, hAxis, rangei)

                # put the rangeInfo in the plot above
                InfoAxis = self._ah[hi + 1]
                self.plotStats(parHist, rangei, self._fig, InfoAxis)

        # check current figure size, might change due to screen size (?)
        targetWidth, targetHeight = (self._figWidth * self._fig.get_dpi(),
                                     self._figHeight * self._fig.get_dpi())
        # set desired figure size (again)
        self._fig.set_figwidth(self._figWidth)
        self._fig.set_figheight(self._figHeight)
        # save figure
        try:
            self._fig.savefig(outputFilename.filenameVerbose(
                                None, "plot PDF", extension = '.pdf'),
                              dpi = 300)
        except AttributeError: pass
        # trigger plot window popup
        manager = get_current_fig_manager()
        manager.canvas.draw()
        manager.show() # resizes large windows to screen width by default
        # resize slightly to update figure to window size,
        # Windows&MacOS need this, just do it on Linux as well
        # somehow, left&right ylabel moves out of the window on windows (FIXME)
        manager.resize(int(targetWidth*1.005), int(targetHeight*1.005))

        if queue is not None:
            queue.put(True) # queue not empty means: plotting done here
        # show() seems to be nescessary otherwise the plot window is
        # unresponsive/hangs on Ubuntu or the whole program crashes on windows
        # 'python stopped working'
        show() # this is synchronous on Linux, waits here until the window is closed
        if autoClose:
            close(self._fig)

    @classmethod
    def plotGrid(self, ax):
        ax.grid(lw = 2, color = 'black', alpha = .5, dashes = [1, 6],
                dash_capstyle = 'round', zorder = -1)
            
    def formatRangeInfo(self, parHist, RI, weighti = 0):
        """Preformats the rangeInfo results ready for printing"""
        oString = u'Range {l:0.03e} to {u:0.03e}, {w}-weighted'.format(
                    l = parHist.lower, u = parHist.upper,
                    w = parHist.yweight)
        pStat = parHist.moments
        pStatFields = pStat.fields
        pStatFieldNames = pStat.fieldNames()
        for si in np.arange(0,10,2):
            pStatFieldName = pStatFieldNames[si]
            pStatField = pStatFields[si]
            pStatFieldSTD = pStatFields[si + 1]
            oString += u'\n {0}:  {1:0.03e} {pm} {2:0.03e}'.format(
                    pStatFieldName,
                    pStatField,
                    pStatFieldSTD, pm = PM)

        return oString

    def formatAlgoInfo(self):
        """Preformats the algorithm information ready for printing
        the colons are surrounded by string-marks, to force laTeX rendering"""
        oString = u' Fitting of data$:$ {} '.format(self._figureTitle)
        oString += u'\n {}'.format(self._dataset.x0.limsString)
        oString += u'\n Active parameters$:$ {}, ranges: {} '.format(
            self._modelData.get('activeParamCount', 0), self._nR)
        oString += u'\n Background level: {0:3.3g} {pm} {1:3.3g}'.format(
                self._BG[0], self._BG[1], pm = PM)
        oString += u'\n ( Scaling factor: {0:3.3g} {pm} {1:3.3g} )'.format(
                self._SC[0], self._SC[1], pm = PM)
        times = self._result['times']
        if isList(times) and len(times):
            timesDDoF = 0
            if len(times) > 1: # prevent division by zero in numpy.std()
                timesDDoF = 1
            oString += (u"\n Timing: {0:d} repetitions "
                         "of {1:3.3g} {pm} {2:3.3g} seconds").format(
                    np.size(times), times.mean(), times.std(ddof = timesDDoF),
                    pm = PM)
        return oString

    def setAxis(self, ah):
        # self.setAxis font and ticks
        ah.set_yticklabels(ah.get_yticks(), fontproperties = self._plotfont,
                size = 'large')
        ah.set_xticklabels(ah.get_xticks(), fontproperties = self._plotfont,
                size = 'large')
        ah.set_xlabel(ah.get_xlabel(), fontproperties = self._textfont,
                size = 'x-large')
        ah.set_ylabel(ah.get_ylabel(), fontproperties = self._textfont,
                size = 'x-large')
        ah.spines['bottom'].set_lw(2)
        ah.spines['top'].set_lw(2)
        ah.spines['left'].set_lw(2)
        ah.spines['right'].set_lw(2)
        ah.tick_params(axis = 'both', colors = 'black', width = 2,
                which = 'major', direction = 'in', length = 6)
        ah.tick_params(axis = 'x', colors = 'black', width = 2,
                which = 'minor', direction = 'in', length = 3)
        ah.tick_params(axis = 'y', colors = 'black', width = 2,
                which = 'minor', direction = 'in', length = 3)
        locs, labels = xticks()
        xticks(locs, ["%g" % x for x in locs])
        locs, labels = yticks()
        yticks(locs, ["%g" % x for x in locs])
        return ah

    def figInit(self, nHists, figureTitle, nR = 1):
        """initialize figure and initialise axes using GridSpec.
        Each rangeinfo (nR) contains two rows and nHists + 1 columns.
        the top row axes are for placing text objects: settings and stats.
        The bottom row axes are for plotting the fits and the histograms
        TODO: add settings to window title? (next to figure_xy)"""
        ahl = list() #list of axes handles from top left to bottom right.
        cellWidth, cellHeight = 7, 7
        numCols, numRows = nHists + 1, nR
        self._figWidth = cellWidth * numCols
        self._figHeight = cellHeight * numRows
        fig = figure(figsize = (self._figWidth, self._figHeight),
                     dpi = 80, facecolor = 'w', edgecolor = 'k')
        if isString(figureTitle):
            get_current_fig_manager().set_window_title(figureTitle)

        charWidth, charHeight = getTextSize(fig, self._textfont)
        charWidth, charHeight = (charWidth / (cellWidth * fig.dpi),
                                 charHeight / (cellHeight * fig.dpi))
        self._charHeight = charHeight
        self._charWidth = charWidth
        gs = gridspec.GridSpec(2 * numRows, numCols,
                height_ratios = np.tile([1,6], numRows))
        # update margins
        self._subPlotPars = dict(
                left  =    charWidth*11./numCols, bottom =    charHeight*4.,
                right = 1.-charWidth* 7./numCols, top    = 1.-charHeight*1.5,
                wspace =   charWidth*20.,         hspace =    charHeight*12.)
        gs.update(**self._subPlotPars)

        textAxDict = {
                'frame_on' : False,
                'yticks' : [],
                'xticks' : [],
                'ylim' : [0., 1.],
                'xlim' : [0., 1.],
                }
        for ai in range(numCols * numRows * 2 ):
            # initialise axes
            ah = subplot(gs[ai])
            # disable mouse coordinates while avoiding Tkinter error
            # about None not being callable
            ah.format_coord = lambda x, y: ""
            if ai%(numCols * 2) < numCols:
                ah.update(textAxDict) # text box settings:
            ahl.append(ah)
        return fig, ahl

    ## 2D plotting needs to be refactored after re-implementation
    # def plot2D(self, q, psi, measVal, measVal2d, qAxis):
    #     """plots 2D data and fit"""
    #     # 2D data
    #     # we need to recalculate the result in two dimensions
    #     intShow = measVal.copy()
    #     # quadrant 1 and 4 are simulated data, 2 and 3 are measured data
    #     intShow[(psi >   0) * (psi <=  90)] = measVal2d[
    #             (psi >   0) * (psi <=  90)]
    #     intShow[(psi > 180) * (psi <= 270)] = measVal2d[
    #             (psi > 180) * (psi <= 270)]
    #     xmidi = int(round(np.size(q, 1)/2))
    #     ymidi = int(round(np.size(q, 0)/2))
    #     QX = np.array([-q[ymidi, 0], q[ymidi, -1]])
    #     QY = np.array([-q[0, xmidi], q[-1, xmidi]])
    #     extent = (QX[0], QX[1], QY[0], QY[1])
    # 
    #     # indexing probably wrong:
    #     qAxis.update( axisbg = (.95, .95, .95),
    #                            xlim = QX, ylim = QY, xlabel = 'q_x, 1/m',
    #                            ylabel = 'q_y, 1/m')
    #     imshow(np.log10(intShow), extent = extent, origin = 'lower')
    #     qAxis = self.setAxis(qAxis)
    #     colorbar()
    #     title('Measured vs. Fitted measVal',
    #           fontproperties = self._textfont, size = 'large')
    #     # reapply limits, necessary for some reason:
    #     xlim(QX)
    #     ylim(QY)

    def plotPartial(self, fitX0, fitMeasVal, fitSTD, qAxis, label = 'MC partial measVal'):
        """plots 1D data and fit"""
        #make active:
        sca(qAxis)
        plot(fitX0, fitMeasVal, 'b-', lw = 1, label = label)

    def plot1D(self, dataset, fitX0, fitMeasVal, qAxis):
        """plots 1D data and fit"""
        # settings for Q-axes (override previous settings where appropriate):
        xOrigin = dataset.x0.unit.toDisplay(dataset.x0.binnedData)
        yOrigin = dataset.f.unit.toDisplay(dataset.f.binnedData)
        uOrigin = dataset.f.unit.toDisplay(dataset.f.binnedDataU)
        if not len(xOrigin):
            logging.error("No data to plot!")
            return

        xLim = (xOrigin.min() * (1 - self._axisMargin), 
                xOrigin.max() * (1 + self._axisMargin))
        yLim = (-.5, .5)
        if any(yOrigin != 0.):
            yLim = (yOrigin[yOrigin != 0].min() * (1 - self._axisMargin),
                    yOrigin.max() * (1 + self._axisMargin))
        qAxDict = self._AxDict.copy()
        qAxDict.update({
                'xlim' : xLim, 'ylim' : yLim,
                'xlabel' : u'{name} ({mag})'.format(name = dataset.x0.name,
                mag = dataset.x0.unit.displayMagnitudeName),
                'ylabel' : u'{name} ({mag})'.format(name = dataset.f.name,
                mag = dataset.f.unit.displayMagnitudeName)
                })

        # make active:
        sca(qAxis)
        qAxis.update(qAxDict)
        qAxis = self.setAxis(qAxis)
        # plot original data
        qAxis.errorbar(xOrigin, yOrigin, uOrigin, zorder = 2,
                       label = u"Measured {name}"
                               .format(name = dataset.f.name),
                       **self._errorBarOpts)
        self.plotGrid(qAxis)
        # plot fit data
        qAxis.plot(dataset.x0.unit.toDisplay(fitX0),
                   dataset.f.unit.toDisplay(fitMeasVal),
                   'r-', lw = 3, zorder = 4,
                   label = u"MC Fit {name}"
                            .format(name = dataset.f.name))
        try: # try to plot the background level
            qAxis.plot(dataset.x0.unit.toDisplay(fitX0),
                       np.ones_like(fitX0) * dataset.f.unit.toDisplay(self._BG[0]),
                       'g-', linewidth = 3, zorder = 3,
                       label = "MC Background level:\n"
                               "        ({0:03.3g})".format(self._BG[0]))
        except Exception as e:
            logging.error("could not plot background")
#            logging.exception(e)
            pass

        titleAlignment = 'center'
        titleHandler = qAxis.set_title(u"Measured vs. Fitted {name}"
                                       .format(name = dataset.f.name),
                                       fontproperties = self._textfont,
                                       size = 'large', loc = titleAlignment)

        # set up the legend
        legendHandle, legendLabel = qAxis.get_legend_handles_labels()

        qAxis.legend(legendHandle, legendLabel,
                     loc = 1, fancybox = True, prop = self._textfont)
        # reapply limits, necessary for some reason:
        qAxis.set_xlim(xLim)
        # make the background line visible
        qAxis.set_ylim(yLim)
        if self._AxDict['yscale'] == 'linear':
            delta = np.diff(yLim) * .02 # 2% of y-axis range
            qAxis.set_ylim(min(yLim)-delta, max(yLim)+delta)
        qAxis.format_coord = CoordinateFormat(
                dataset.x0.name, dataset.x0.unit,
                dataset.f.name, dataset.f.unit)

    def plotInfo(self, InfoAxis):
        """plots the range statistics in the small info axes above plots"""
        # make active:
        sca(InfoAxis)
        # show volume-weighted info:
        ovString = self.formatAlgoInfo()
        delta = 0.001 # minor offset
        tvObj = text(0. - delta, 0. + delta, ovString, **self._infoText)
        self._fig.show()
        axis('tight')

    def plotStats(self, parHist, rangei, fig, InfoAxis):
        """plots the range statistics in the small info axes above plots"""
        # make active:
        sca(InfoAxis)
        # show volume-weighted info:
        delta = 0.001 # minor offset
        ovString = self.formatRangeInfo(parHist, rangei, weighti = 0)
        tvObj = text(0. - delta, 0. + delta, ovString, bbox = 
                {'facecolor' : 'white', 'alpha': 0.95}, **self._infoText)
        fig.show()
        axis('tight')

    def plotHist(self, plotPar, parHist, hAxis, rangei):
        """histogram plot"""
        # make active:
        sca(hAxis)

        histXLowerEdge = plotPar.toDisplay(parHist.xLowerEdge)
        histXMean =      plotPar.toDisplay(parHist.xMean)
        histXWidth =     plotPar.toDisplay(parHist.xWidth)
        # either volume or number, whichever is chosen
        HistYMean = parHist.bins.mean
        HistMinReq = parHist.observability
        HistYStd = parHist.bins.std
        HistCDF = parHist.cdf.mean # plot cumulative distribution function

        # get information for labels:
        plotTitle = plotPar.displayName()
        xLabel = u'{} ({})'.format(plotPar.name(), plotPar.suffix())

        # expand the x axis to leave a little more space left and right of the plot
        if parHist.xscale == 'log':
            xLim = (histXLowerEdge.min() * (1 - self._axisMargin), 
                    histXLowerEdge.max() * (1 + self._axisMargin))
            xScale = 'log'
        else:
            xDiff = histXLowerEdge.max() - histXLowerEdge.min()
            xLim = (histXLowerEdge.min() - 0.25 * self._axisMargin * xDiff, 
                    histXLowerEdge.max() + 0.25 * self._axisMargin * xDiff) 
            xScale = 'linear'

        # vertical limits also should be adjusted a little
        yLim = (0, HistYMean.max() * (1 + self._axisMargin) )
        # histogram axes settings:
        hAxDict = self._AxDict.copy()
        # change axis settings:
        hAxDict.update({
            'xlim' : xLim,
            'ylim' : yLim,
            'xlabel' : xLabel,
            'xscale' : xScale,
            'yscale' : 'linear',
            'ylabel' : '[Rel.] Fraction' })
        if   "int" in parHist.yweight:
            hAxDict['ylabel'] = u'[Rel.] Intensity Fraction'
        elif "vol" in parHist.yweight:
            hAxDict['ylabel'] = u'[Rel.] Volume Fraction'
        elif "num" in parHist.yweight:
            hAxDict['ylabel'] = u'[Rel.] Number Fraction'
        elif "surf" in parHist.yweight:
            hAxDict['ylabel'] = u'[Rel.] Surface Fraction'
        # update axes settings:
        hAxis.update(hAxDict)
        # change axis settings not addressible through dictionary:
        hAxis = self.setAxis(hAxis)
        #plot grid
        self.plotGrid(hAxis)

        # duplicate axes for the CDF plot:
        suppAx = hAxis.twinx()
        suppAx.set_ylim(0, 1.2)
        suppAx.set_ylabel('Cumulative distribution function')
        suppAx = self.setAxis(suppAx)

        # fill axes
        # plot active histogram:
        validi = ( (histXLowerEdge >= plotPar.toDisplay(parHist.lower)) * 
                   (histXLowerEdge <= plotPar.toDisplay(parHist.upper)) )
        validi[-1] = 0
        if not (validi.sum()==0):
            hAxis.bar(histXLowerEdge[validi], HistYMean[validi[0:-1]], 
                    width = histXWidth[validi[0:-1]], color = 'orange',
                    edgecolor = 'black', linewidth = 1, zorder = 2,
                    align = "edge", # align bar by left edge
                    label = 'MC size histogram')
        suppAx.plot(histXMean, HistCDF, '-', color = 'grey', linewidth = 2,
                    zorder = 5, label = 'Cumulative distrib.')
        # plot observability limit
        if isinstance(self._dataset, SASData):
            hAxis.plot(histXMean, HistMinReq, 'ro',
                       ms = 5, markeredgecolor = 'r',
                       label = 'Minimum visibility limit', zorder = 3)
        # plot active uncertainties
        hAxis.errorbar(histXMean[validi[0:-1]], HistYMean[validi[0:-1]], 
            HistYStd[validi[0:-1]],
                zorder = 4, **self._errorBarOpts)
        legendHandle0, legendLabel0 = hAxis.get_legend_handles_labels()
        legendHandle1, legendLabel1 = suppAx.get_legend_handles_labels()
        legendHandle0 += legendHandle1
        legendLabel0 += legendLabel1
        hAxis.legend(legendHandle0, legendLabel0, loc = 1, fancybox = True,
                     prop = self._textfont)
        title(plotTitle, fontproperties = self._textfont,
              size = 'large')
        xlim(xLim)
        suppAx.format_coord = CoordinateFormat(plotPar.name(), plotPar.unit(),
                                               "y", None)

class PlotSeriesStats(object):
    """Simple 1D plotting of series statistics."""
    _figure = None
    _axes = None

    def __init__(self):
        self._figure = figure(figsize = (7, 7), dpi = 80,
                              facecolor = 'w', edgecolor = 'k')
        self._axes = subplot()

    def plot(self, stats):
        xvec = stats["seriesKey"]
        if not all((isNumber(x) for x in xvec)):
            xvecNew = range(len(xvec))
            self._axes.set_xticks(xvecNew)
            self._axes.set_xticklabels(xvec, rotation = 15)
            xvec = xvecNew
        paramUnit = stats["unit"]
        lbl = u"{param} [{lo:3g}, {hi:3g}]({pu}) {w}".format(
                param = stats["param"][0], w = stats["weighting"][0],
                lo = paramUnit.toDisplay(stats["lower"][0]),
                hi = paramUnit.toDisplay(stats["upper"][0]),
                pu = paramUnit.displayMagnitudeName)
        self._axes.errorbar(xvec, paramUnit.toDisplay(stats["mean"]),
                                  paramUnit.toDisplay(stats["meanStd"]),
                            label = lbl)
        self._axes.set_xlabel(stats["seriesKeyName"])
        self._axes.set_ylabel("mean ({})".format(paramUnit.displayMagnitudeName))
        self._axes.set_title(stats["title"])

    def show(self):
        self._axes.legend(loc = 1, fancybox = True)
        PlotResults.plotGrid(self._axes)
        self._figure.canvas.set_window_title(
                "series: " + self._axes.get_title())
        self._figure.canvas.draw()
        self._figure.show()
        show()

# vim: set ts=4 sts=4 sw=4 tw=0:
