# -*- coding: utf-8 -*-
# utils/tests.py

"""
Utils for testing something.
"""

import platform
import numpy
import sys

from ..utils.collections import Sequence, Mapping, Set, Callable

try:
    from gui.qt import QtCore
    from QtCore import QString
except:
    # defines QString as regular python string if it could not be imported
    QString = str

# object tests

def isString(obj):
    return isinstance(obj, str) or isinstance(obj, QString)

def isList(obj):
    return (not isString(obj) and
            (isinstance(obj, Sequence)
             or (isinstance(obj, numpy.ndarray)
                 and obj.ndim < 2)))

def isIterable(obj):
    try:
        iter(obj)
    except Exception:
        return False
    else:
        return True

def isNonEmptyString(obj):
    return (isString(obj) and len(obj) > 0)

def isMap(obj):
    return isinstance(obj, Mapping)

def isSet(obj):
    return isinstance(obj, Set)

def isNumber(obj):
    # current implementation does not account for all possibilities.
    # trying to use numbers.Number and isinstance does not accept things
    # like float32:
    # return (isinstance(obj, int) or isinstance(obj, float) or
    #         isinstance(obj, long) or isinstance(obj, complex))

    # float(obj) gives false positive for strings like "1"
    # which are not supposed to be numbers
    if isString(obj):
        return False
    # the faster way to do this is "Duck typing", according to SO:
    try:
        float(obj)
    except (ValueError, TypeError):
        try:
            complex(obj)
        except (ValueError, TypeError):
            return False
    return True

def isInteger(obj):
    return isinstance(obj, int)

def isCallable(obj):
    return isinstance(obj, Callable)

# environment tests

def isLinux():
    return platform.system().lower() in "linux"

def isMac():
    return platform.system().lower() in "darwin"

def isWindows():
    return platform.system().lower() in "windows"

def isFrozen():
    return hasattr(sys, "frozen")

# utilities

def testfor(condition, exception, errorMessage = ""):
    if __debug__ and not condition:
        raise exception(errorMessage)

def assertName(newName, errorType, noWhitespace = False):
    testfor(isString(newName) and len(newName) > 0,
            errorType, "A name is mandatory!")
    testfor(not noWhitespace or newName.find(" ") < 0,
            errorType, "A name must not contain white space!")

# vim: set ts=4 sts=4 sw=4 tw=0:
