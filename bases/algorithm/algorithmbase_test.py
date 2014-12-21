# -*- coding: utf-8 -*-
# bases/algorithm/algorithmbase_test.py

from algorithmbase import AlgorithmBase, AlgorithmNameError, AlgorithmParameterError
from nose.tools import raises, assert_raises
from numpy import array as np_array
from numpy import uint32, float64, dtype
from parameter import factory as Parameter

TestPar = Parameter("testPar", 5.0, valueRange = (4.0, 13.0))

@raises(AlgorithmNameError)
def testName():
    """name is mandatory"""
    class TestAlgo(AlgorithmBase):
        pass
    t = TestAlgo()

def testParam():
    """Algorithm without parameters allowed"""
    class TestAlgo(AlgorithmBase):
        pass
    atype = TestAlgo.factory("testalgo")
    t = atype()

def testParam1():
    class TestAlgo(AlgorithmBase):
        pass
    atype = TestAlgo.factory("testalgo", TestPar)
    t = atype()

@raises(AlgorithmParameterError)
def testParam4():
    """Provided parameters have to be a subclass of ParameterBase"""
    class TestAlgo(AlgorithmBase):
        pass
    atype = TestAlgo.factory("testalgo", "dummy")
    t = atype()

@raises(AlgorithmParameterError)
def testParam5():
    """Attribute with a parameters name already set"""
    class AnotherAlgo(AlgorithmBase):
        testPar = None
    atype = AnotherAlgo.factory("testalgo", TestPar)

def testTypeVsInstance():
    class TestAlgo(AlgorithmBase):
        pass
    atype = TestAlgo.factory("testalgo", TestPar)
    ainst = atype()
    # same name
    assert atype.name() == ainst.name()
    # same (default) value
    assert atype.testPar.value() == ainst.testPar.value()
    # class vs instance
    assert type(atype.testPar) is type
    assert type(ainst.testPar) is TestPar
    assert id(atype.testPar) != id(ainst.testPar)
    # type of instance should remain in class too
    assert id(atype.testPar) == id(type(ainst).testPar)

def testCopy():
    class TestAlgo(AlgorithmBase):
        pass
    a1 = TestAlgo.factory("testalgo", TestPar)()
    a2 = a1.copy()
    assert a1 == a2
    a1.testPar.setValue(a1.testPar.value() + 1)
    assert a1.testPar != a2.testPar
    assert a1 != a2

# vim: set ts=4 sts=4 sw=4 tw=0: