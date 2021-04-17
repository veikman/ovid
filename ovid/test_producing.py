# -*- coding: utf-8 -*-
"""Unit tests for the producing module."""


import unittest.mock as mock

from ovid.basic import OneWayProcessor
from ovid.producing import TwoWayProcessor
from ovid.producing import TwoWaySignatureShorthand


#######################
# TESTS OF PRODUCTION #
#######################


def _twoway(regex, reference_output, *args, **kwargs):
    def _forwards(regex, *args, **kwargs):
        """Examine a generated substitution function signature."""
        m = mock.Mock()

        def f(*args, **kwargs):
            m(*args, **kwargs)
            return ''

        processor = OneWayProcessor(regex, f)
        processor.sub('abc')
        m.assert_called_once_with(*args, **kwargs)

    def _backwards(regex, reference_output, *args, **kwargs):
        """Examine the matchable product of reverse operation."""
        processor = TwoWayProcessor(regex, lambda: None)
        assert reference_output == processor.produce(*args, **kwargs)

    _forwards(regex, *args, **kwargs)
    _backwards(regex, reference_output, *args, **kwargs)


def test_empty():
    _twoway('$', '$')


def test_no_groups():
    _twoway('a', 'a')


def test_unnamed_group_multicharacter():
    _twoway('(ab)', 'ab', 'ab')


def test_unnamed_groups():
    _twoway('(a)(b)', 'ab', *'ab')


def test_named_group():
    _twoway('(?P<n0>a)', 'a', n0='a')


def test_named_groups():
    _twoway('(?P<n0>a)b(?P<n1>c)', 'abc', n0='a', n1='c')


def test_mix():
    _twoway('(?P<n0>a)(b)(?P<n1>c)', 'abc', 'b', n0='a', n1='c')


#####################################
# TESTS OF TwoWaySignatureShorthand #
#####################################


def test_production_noargs():
    def h():
        return '手'

    p = TwoWaySignatureShorthand(h)
    assert p.produce() == '{{h}}'
    assert p.sub(p.produce()) == '手'


def test_production_unnamed():
    def a(v):
        raise NotImplementedError

    p = TwoWaySignatureShorthand(a)
    assert p.produce(1) == '{{a|1}}'


def test_production_named():
    def a(v=None):
        raise NotImplementedError

    p = TwoWaySignatureShorthand(a)
    assert p.produce(v=1) == '{{a|v=1}}'


def test_production_combined():
    def a(v0, v1=None):
        raise NotImplementedError

    p = TwoWaySignatureShorthand(a)
    assert p.produce(1, v1=2) == '{{a|1|v1=2}}'
    assert p.produce(1) == '{{a|1}}'
