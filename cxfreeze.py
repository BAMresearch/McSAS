# -*- coding: utf-8 -*-
# cxfreeze.py
#
# Usage on target platform, tested on Windows with MinGW/MSYS:
# python cxfreeze.py build_exe

import re
import os.path
import sys
import subprocess
from cx_Freeze import setup, Executable
from gui.version import version

def get7ZipPath():
	"""Retrieves 7-Zip install path and binary from Windows Registry.
	This way, we do not rely on PATH containing 7-Zip.
	"""
	path = None
	import win32api, win32con
	for key in (win32con.HKEY_LOCAL_MACHINE, win32con.HKEY_CURRENT_USER):
		try:
			key = win32api.RegConnectRegistry(None, key)
			key = win32api.RegOpenKeyEx(key, r"SOFTWARE\7-Zip")
			path, dtype = win32api.RegQueryValueEx(key, "Path")
			path = os.path.abspath(os.path.join(path, "7z.exe"))
		except:
			pass
	return path

# 7z default on windows
SEVENZIP = get7ZipPath()
if not os.path.isfile(SEVENZIP):
    sys.exit("7-Zip: '{path}' not found!".format(path = SEVENZIP))

# target (temp) dir for mcsas package
TARGETDIR = "{0}-{1}".format(version.name(), version.number())

BASE = None
EXEC_SUFFIX = ""
if sys.platform in "win32":
    BASE = "Win32GUI"
    EXEC_SUFFIX = ".exe"

TARGETNAME = version.name() + EXEC_SUFFIX

INCLUDEFILES = []
if sys.platform in "win32":
    INCLUDEFILES += [
        'Microsoft.VC90.CRT',
                    ]

BUILDOPTIONS = dict(
    compressed = False,
    include_files = INCLUDEFILES,
    packages = [],
    includes = ["PySide", "PySide.QtCore", "PySide.QtGui", "PySide.QtSvg",
                "multiprocessing", "cutesnake",
                "scipy.sparse.csgraph._validation",
                "scipy.sparse.linalg.dsolve.umfpack", "scipy.integrate.vode",
                "scipy.integrate.lsoda",
                "matplotlib", "matplotlib.backends.backend_qt4agg"],
    excludes = ["Tkinter"],
#    icon = "res/img/brianpauw.ico",
    path = [os.getcwd()] + sys.path,
    build_exe = TARGETDIR,
    silent = True,
    copy_dependent_files = True,
)

setup(
    name = version.name(),
    version = version.number(),
    description = version.name(),
    long_description = ("GUI for Monte-Carlo size distribution analysis"),
#    url = "http://sourceforge.net/",
    license = "Creative Commons CC-BY-SA",
    author = u"Brian R. Pauw",
    author_email = "brian@stack.nl",
    contact = u"Brian R. Pauw",
    contact_email = "brian@stack.nl",
    maintainer = u"Ingo Breßler",
    maintainer_email = "ingo.bressler@bam.de",
    # additional metadata for hacked version of cx_Freeze
    # displayed in copyright info
    download_url = "2013, https://bitbucket.org/pkwasniew/mcsas",
    # company
    classifiers = u"NIMS\r\n"
                  u"National Institute for Materials Science, \r\n\r\n"
                  u"1-2-1 Sengen, 305-0047, "
                  u"305-0047, Tsukuba, Japan",
    options = dict(build_exe = BUILDOPTIONS),
    executables = [Executable("gui.py", base = BASE,
                              targetName=TARGETNAME)])

RETCODE = subprocess.call([SEVENZIP, "a", "-t7z", "-mx=9",
                           TARGETDIR+".7z", TARGETDIR])

# vim: set ts=4 sw=4 sts=4 tw=0:
