#!/usr/bin/env python2

"""
Creates icons for OSX .ICNS and Windows .ICO based on an existing set of
icons in multiple resolutions.
Tested on OSX and Ubuntu for icon creation.
This script does not work on Windows because of missing helper programs.

### ICNS

Prepares an iconset according to https://stackoverflow.com/a/20703594
Run it in directory 'resources/icon' to create an iconset directory
for use with iconutil on OSX::

    iconutil -c icns mcsas.iconset

creates mcsas.icns

### Windows

For ICO it uses http://pngquant.org to get icons with reduced color palette
might give unexpected results because of the perception based model ...

"""

import os
import sys
import glob
import shutil
import subprocess
from collections import OrderedDict

def getSourceFiles(path, resolutions):
    files = OrderedDict()
    for r in resolutions:
        fn = glob.glob(os.path.join(path, "*_{0:04d}.png".format(r)))
        assert len(fn)
        fn = fn[0]
        assert os.path.isfile(fn)
        files[r] = fn
    return files

def createTempDir(path, name):
    # create a new directory for the iconset
    targetDir = os.path.join(path, name)
    assert not os.path.isdir(targetDir), (
        "Temporary directory exists! '{}'".format(targetDir))
    os.mkdir(targetDir)
    return targetDir

def findCommand(name):
    cmd = subprocess.check_output(["which", name]).splitlines()[0]
    assert len(cmd) and os.path.isfile(cmd)
    return cmd

def prepareIco(iconName):

    def resolutions():
        return 16, 32, 48, 256

    # find all required files
    path = os.getcwd()
    files = getSourceFiles(path, resolutions())
    pngquant = findCommand("pngquant")
    targetDir = createTempDir(path, iconName.lower() + ".ico.dir")
    for r in resolutions():
        src = files[r]
        basename = os.path.splitext(os.path.basename(src))[0]
        dst = os.path.join(targetDir, basename + ".png")
        # use src file for 32bit
        files[r] = [src]
        if 256 == r: continue
        # create 8bit copies
        shutil.copyfile(src, dst)
        subprocess.call([pngquant, "--ext", "-8.png", "--speed", "1", "8", dst])
        files[r] += glob.glob(os.path.splitext(dst)[0] + "-8.png")
        if 48 == r: continue
        # create 4bit copies
        subprocess.call([pngquant, "--ext", "-4.png", "--speed", "1", "4", dst])
        files[r] += glob.glob(os.path.splitext(dst)[0] + "-4.png")
    return files

def createIco(iconName):
    files = prepareIco(iconName)
    srcFiles = sum(files.values(), [])
    icotool = findCommand("icotool")
    subprocess.call([icotool, "-c", "-o", iconName + ".ico"] + srcFiles)

def prepareIconset(iconName):

    def resolutions():
        return 16, 32, 128, 256, 512

    # find all required resolutions
    res = dict.fromkeys(resolutions())
    for r in res.keys():
        res[r] = (r, r*2)
    # find all required files
    path = os.getcwd()
    files = getSourceFiles(path, sum(res.values(), ()))
    targetDir = createTempDir(path, iconName.lower() + ".iconset")
    # copy source images to their appropriate places&names
    for r, srcRes in res.iteritems():
        basename = "icon_{0}x{0}".format(r)
        assert len(srcRes) == 2
        srcFn = files[srcRes[0]]
        dstFn = os.path.join(targetDir, basename + ".png")
        shutil.copyfile(srcFn, dstFn)
        srcFn = files[srcRes[1]]
        dstFn = os.path.join(targetDir, basename + "@2x.png")
        shutil.copyfile(srcFn, dstFn)

    return targetDir

def createIcns(iconName):
    iconutil = findCommand("iconutil")
    srcDir = prepareIconset(iconName)
    subprocess.call([iconutil, "-c", "icns", srcDir])

if __name__ == "__main__":

    assert len(sys.argv) > 1, (
        "Please provide a icon file name to be created!")
    iconFn = sys.argv[1]
    iconName, iconExt = os.path.splitext(iconFn)
    assert len(iconName) and len(iconExt), (
        "Please provide a proper icon file name including an extension!")
    if "icns" in iconExt:
        createIcns(iconName)
    elif "ico" in iconExt:
        createIco(iconName)

# vim: set ts=4 sts=4 sw=4 tw=0:
