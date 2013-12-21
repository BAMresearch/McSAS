#!/usr/bin/env python                                                          
#coding: utf8    
"""
default for settings  and info used for a McSAS run
used by McSASCfg
"""

__author__ = "Brian R. Pauw"
__contact__ = "brian@stack.nl"
__license__ = "GPLv3+"
__copyright__ = "National Institute of Materials Science, Tsukuba, Japan"
__date__ = "2013-12-21"
__status__ = "alpha"
version = "0.0.1"

from cutesnake.algorithm import (Parameter, ParameterFloat, ParameterBoolean, ParameterNumerical)
import logging, json
import os, inspect

class cInfo(object):
    """
    This class contains all the information required to read, verify and write
    configuration parameters files.
    """
    parameters=None
    logging.getLogger('McSAScfg')
    logging.basicConfig(level = logging.DEBUG)
    _paramDefFile=None
    parameterNames=list()

    def __init__(self,**kwargs):
        """initialise the defaults and populate the database with values
        where appropriate
        default parameter file can be provided using kwarg:
        paramDefFile = 'path/to/file'
        McSASParameters.json should be in the same directory as this function
        """
        fname = kwargs.get("paramDefFile", None)
        if fname is None:
            if os.path.exists("McSASParameters.json"):
                fname = "McSASParameters.json"
            else:
                #try one more:
                #determine the directory in which this module resides
                #determine the directory in which McSASDefaultsCfg is located:
                #settings should be in the same directory:
                fdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
                fname = os.path.join(fdir, "McSASParameters.json")

        if not os.path.exists(fname):
            logging.error('no default parameter file found!')
            return false

        self.setParDefFile(fname)
        self.loadParams()

    def loadParams(self):
        """writes the default definitions and bounds for the configuration
        parameters to self.parameters"""
        self.parameters=lambda: None
        #something like what is used in McSAS?
        with open(self.parDefFile(),'r') as jfile:
            parDict=json.load(jfile)

        #now we cast this information into the Parameter class:
        for kw in parDict.keys():
            subDict = parDict[kw]
            name = kw
            value = subDict.pop("value", None)
            default = subDict.pop("default", None)
            if value is None and default is not None:
                value = default
            #determine parameter class:
            cls = subDict.pop("cls", None)
            if cls == "int":
                subDict.update(cls = ParameterNumerical)
            elif cls == "float":
                subDict.update(cls = ParameterFloat)
            elif cls == "bool": 
                subDict.update(cls = ParameterBoolean)
            else:
                logging.warning('parameter type {} for parameter {} not understood from {}'.format(cls, kw, self.parDefFile() ))

            temp = Parameter(name, value, **subDict)
            setattr(self.parameters,kw,temp)
            self.parameterNames.append(kw)
            logging.info('successfully ingested parameter: {}'.format(kw))
        

    def parseConfig(self):
        """
        Runs through the entire settings, raising warnings where necessary
        """
        for pn in self.parameterNames:
            pf = self.getPar(pn)
            if pf.value is None:
                continue #skip this value, has not yet been set
            # rewrite for McSAS:
            #pf.checkSize()
            #pf.clipValue()
            
    def setParDefFile(self,value):
        if os.path.exists(value):
            self._paramDefFile=value
        else:
            logging.warning('invalid path to parameter definitions file')
            return False
        return True
    
    def parDefFile(self):
        return self._paramDefFile

    def getPar(self,key):
        #returns the handle to the parameter defined by key or returns None
        #if it doesn't exist
        if key in self.parameterNames:
            return getattr(self.parameters,key)
        else:
            logging.warning(
                    'Could not find parameter {}. Define base parameter in parameter settings file first'.format(key)
                    )
            return None

    def setParVal(self,par,value):
        "shortcut method for setting the value of a parameter only"
        parhandle = self.getPar(par)
        parhandle.setValue(value)
    
    def getParVal(self,par):
        "shortcut method for getting the value of a parameter"
        parhandle = self.getPar(par)
        return parhandle.value()

    def set(self,par,kwargs):
        """
        sets one or more parameter attributes
        not sure the "set" function works in Parameter as in imp2
        TODO: update for McSAS
        """
        parhandle = self.getPar(par)
        
        for kw in kwargs:
            parhandle.set(kw, kwargs[kw])


