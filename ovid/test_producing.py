# -*- coding: utf-8 -*-
'''Unit tests for the producing module.'''


import unittest
import unittest.mock as mock

from . import basic
from . import producing


class SubstitutionElements(unittest.TestCase):
    def _forwards(self, regex, *args, **kwargs):
        '''Examine a generated substitution function signature.'''
        m = mock.Mock()

        def f(*args, **kwargs):
            m(*args, **kwargs)
            return ''

        processor = basic.OneWayProcessor(regex, f)
        processor.sub('abc')
        m.assert_called_once_with(*args, **kwargs)

    def _backwards(self, regex, reference_output, *args, **kwargs):
        '''Examine the matchable product of reverse operation.'''
        processor = producing.TwoWayProcessor(regex, lambda: None)
        self.assertEqual(reference_output, processor.produce(*args, **kwargs))

    def _twoway(self, regex, reference_output, *args, **kwargs):
        self._forwards(regex, *args, **kwargs)
        self._backwards(regex, reference_output, *args, **kwargs)

    def test_empty(self):
        self._twoway('$', '$')

    def test_no_groups(self):
        self._twoway('a', 'a')

    def test_unnamed_group_multicharacter(self):
        self._twoway('(ab)', 'ab', 'ab')

    def test_unnamed_groups(self):
        self._twoway('(a)(b)', 'ab', *'ab')

    def test_named_group(self):
        self._twoway('(?P<n0>a)', 'a', n0='a')

    def test_named_groups(self):
        self._twoway('(?P<n0>a)b(?P<n1>c)', 'abc', n0='a', n1='c')

    def test_mix(self):
        self._twoway('(?P<n0>a)(b)(?P<n1>c)', 'abc', 'b', n0='a', n1='c')


class SignatureShorthandProduction(unittest.TestCase):
    def test_production_noargs(self):
        def h():
            return '手'

        p = producing.TwoWaySignatureShorthand(h)
        self.assertEqual(p.produce(), '{{h}}')
        self.assertEqual(p.sub(p.produce()), '手')

    def test_production_unnamed(self):
        def a(v):
            raise NotImplementedError

        p = producing.TwoWaySignatureShorthand(a)
        self.assertEqual(p.produce(1), '{{a|1}}')

    def test_production_named(self):
        def a(v=None):
            raise NotImplementedError

        p = producing.TwoWaySignatureShorthand(a)
        self.assertEqual(p.produce(v=1), '{{a|v=1}}')

    def test_production_combined(self):
        def a(v0, v1=None):
            raise NotImplementedError

        p = producing.TwoWaySignatureShorthand(a)
        self.assertEqual(p.produce(1, v1=2), '{{a|1|v1=2}}')
        self.assertEqual(p.produce(1), '{{a|1}}')
