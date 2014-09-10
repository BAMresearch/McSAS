# -*- coding: utf-8 -*-
# numbergenerator.py

from abc import ABCMeta, abstractmethod
import numpy

# it seems treating number generators as instances is more convenient than
# the current implementation (types/classes only)
# instances could be constructed with parameters, eg for randomExp or const

class NumberGenerator(object):
    """Base class for number generators.
    Generates numbers in the interval [0, 1].
    Scaling is supposed to happen elsewhere."""
    __metaclass__ = ABCMeta

    @classmethod
    @abstractmethod
    def get(cls, count = 1):
        raise NotImplementedError

class RandomUniform(NumberGenerator):
    @classmethod
    def get(cls, count = 1):
        return numpy.random.uniform(size = count)

import sys

# numpy.left|right_shift does not work for uint64 out of the box
lshift = lambda x,s: numpy.uint64(x) * numpy.uint64(2**s)
rshift = lambda x,s: numpy.uint64(x) / numpy.uint64(2**s)

class RandomXorShiftUniform(NumberGenerator):
    """Implemented according to xorshift1024* at http://xorshift.di.unimi.it

    >>> from cutesnake.algorithm.numbergenerator import RandomXorShiftUniform
    >>> RandomXorShiftUniform.getSeed()
    >>> RandomXorShiftUniform.setSeed()
    >>> RandomXorShiftUniform.next()
    >>> RandomXorShiftUniform.get()
    >>> RandomXorShiftUniform.get(3)
    """
    _dtype = numpy.uint64
    _count = 16
    s = None
    p = None

    @classmethod
    def getSeed(cls):
        """Generate seed using numpy."""
        def rand32():
            return numpy.random.random_integers(
                        numpy.iinfo(numpy.uint32).min,
                        numpy.iinfo(numpy.uint32).max)
        seedData = numpy.zeros(cls._count, dtype = cls._dtype) # init empty array
        for i in range(cls._count): # for each 64bit uint
            seedData[i] = (lshift(rand32(), 32)) + rand32()
        return seedData

    @classmethod
    def setSeed(cls, seedData = None):
        try:
            seedData = seedData.flatten()
            assert(len(seedData) == cls._count)
            assert(seedData.dtype is cls._dtype)
        except StandardError:
            seedData = None
        if seedData is None:
            # seed it ourselves
            seedData = cls.getSeed()
        cls.s = seedData
        cls.p = numpy.random.random_integers(cls._count) - 1
        print >>sys.__stderr__, "got seed:", cls.s

    @classmethod
    def next(cls):
        s0 = cls.s[ cls.p ]
        cls.p = ( cls.p + 1 ) & 15
        s1 = cls.s[ cls.p ]
        s1 ^= lshift(s1, 31) # a
        s1 ^= rshift(s1, 11) # b
        s0 ^= rshift(s0, 30) # c
        cls.s[ cls.p ] = s0 ^ s1
        print >>sys.__stderr__, "next", cls.s 
        return numpy.uint64(cls.s[ cls.p ]) * numpy.uint64(1181783497276652981) # star8/M_8

    @classmethod
    def get(cls, count = 1):
        def getFloat():
            return ( ( 1./4 ) / ( 1L << 62 ) ) * cls.next()
        old_settings = numpy.seterr(all = 'ignore')
        res = numpy.zeros(count)
        for i in range(count):
            res[i] = getFloat()
        numpy.seterr(**old_settings)
        return res

class RandomExponential(NumberGenerator):
    lower, upper = 0., 1.

    @classmethod
    def get(cls, count = 1):
        rs = 10**(numpy.random.uniform(cls.lower, cls.upper, count))
        rs = (rs - 1) / (10**(cls.upper - cls.lower))
        return rs

class RandomExponential1(RandomExponential):
    """Alias class for RandomExponential"""
    pass

class RandomExponential2(RandomExponential):
    """Picks values with inverse logarithmic probability over )0, 1(
    , as if it were spanning two decades."""
    upper = 2.

class RandomExponential3(RandomExponential):
    """Picks values with inverse logarithmic probability over )0, 1(
    , as if it were spanning three decades."""
    upper = 3.

if __name__ == "__main__":
    import doctest
    doctest.testmod()

# vim: set ts=4 sts=4 sw=4 tw=0:
