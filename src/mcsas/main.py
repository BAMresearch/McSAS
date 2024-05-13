# -*- coding: utf-8 -*-
# __main__.py

import sys
import os
import os.path

try:
    from builtins import range
except ImportError as e:
    print("Error:", e)
    print("Failed to use Python 3 imports!")
    print("When using Python 2, package 'future' might be missing.")
    print("Install it by 'sudo pip2 install future'.")
    sys.exit()

def getScriptPath():
    """Returns the full path to the current script file which calls this
    function."""
    thisFile = sys.executable # works for frozen app
    try: # __file__ not defined if frozen
        thisFile = os.path.join(os.getcwd(), __file__)
    except NameError: pass
    thisFile = os.path.abspath(thisFile)
    path, fn = os.path.split(thisFile)
    if os.path.isfile(path):
        path = os.path.dirname(path)
    return path, fn

# get script/executable location, add to module search path
SCRIPT_PATH, SCRIPT_FILENAME = getScriptPath()
#if not hasattr(sys, "frozen") and SCRIPT_PATH not in sys.path:
#    sys.path.append(SCRIPT_PATH)
    # FIXME? sphinx assumes the upper directory as root,
    # prefixes every module path with *mcsas*
    # -> do it the same way? Would simplify some things ...

import argparse
import logging
import multiprocessing

from .log import replaceStdOutErr
from .utils import isMac, isLinux

if (isLinux() and hasattr(sys, "frozen")
    and "LD_LIBRARY_PATH" not in os.environ):
    os.environ["LD_LIBRARY_PATH"] = SCRIPT_PATH

def makeAbsolutePath(relpath):
    return os.path.abspath(os.path.join(SCRIPT_PATH, relpath))

def main(argv = None):
    parser = argparse.ArgumentParser(description = "Monte Carlo SAS analysis")
    parser.add_argument("-t", "--text", action = "store_true",
                        help = "Run in text mode without graphical "
                               "user interface")
    parser.add_argument("-l", "--nolog", action = "store_true",
                        help = "Disable progress output during fit, "
                               "it's written to file in any case.")
    parser.add_argument("-s", "--start", action = "store_true",
                        help = "Start the calculation immediately.")
    parser.add_argument('fnames', nargs = '*', metavar = 'FILENAME',
                        action = "store",
                        help = "One or more data files to analyse")
    # TODO: add info about output files to be created ...
    if isMac():
        # on OSX remove automatically provided PID,
        # otherwise argparse exits and the bundle start fails silently
        for i in range(len(sys.argv)):
            if sys.argv[i].startswith("-psn"): # PID provided by osx
                del sys.argv[i]
    try:
        args = parser.parse_args()
    except SystemExit as e:
        # useful debugging code, ensure destination is writable!
#        logfn = ("/tmp/{name}_unsupported_args.log"
#                 .format(name = SCRIPT_FILENAME))
#        with open(logfn, "w") as fd:
#            fd.write("argv: " + str(sys.argv) + "\n")
        raise
    # forwarding logging setting, quick fix 
    import mcsas.gui.calc # importing here makes avoids import loops elsewhere
    mcsas.gui.calc.Calculator.nolog = args.nolog

    # initiate logging (to console stderr for now)
#    replaceStdOutErr() # replace all text output with our sinks

    if not args.text:
        from mcsas.gui.mainwindow import eventLoop
        # run graphical user interface, passing argument parser result
        return eventLoop(args)
    else:
        # TODO: fix command line run
        try:
            from mcsas.gui import calc
            calc(args.fnames)
        except Exception as e:
            # show detailed error traceback if there was one
            import traceback
            logging.error(traceback.format_exc())

# vim: set ts=4 sts=4 sw=4 tw=0:
