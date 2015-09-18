# -*- coding: utf-8 -*-
'''Unit tests for the basic module.'''

import logging
import re
import unittest
import unittest.mock as mock

import ovid.basic as basic


def suppress(logging_level):
    '''Temporarily silence logging up to the named level.

    This function returns a function-altering function.

    '''
    def decorator(method):
        def replacement(instance, *args, **kwargs):
            logging.disable(logging_level)
            method(instance, *args, **kwargs)
            logging.disable(logging.NOTSET)
        return replacement
    return decorator


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
        processor = basic.TwoWayProcessor(regex, lambda: None)
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


class Automatic(unittest.TestCase):
    @staticmethod
    def setUpClass():
        basic.DelimitedShorthand.registry.clear()
        basic.DelimitedShorthand('(b)', lambda *_: 'y')
        basic.DelimitedShorthand('(c)', lambda *_: '{{b}}')
        basic.DelimitedShorthand('(d)', lambda *_: '{{c}}{{c}}')

    def _match(self, text_in, text_out):
        self.assertEqual(basic.DelimitedShorthand.collective_sub(text_in),
                         text_out)

    def test_clean_empty(self):
        self._match('', '')

    def test_clean_nonempty(self):
        self._match('a', 'a')

    def test_no_markup_tokens(self):
        self._match('b', 'b')

    @suppress(logging.ERROR)
    def test_leftover_closer(self):
        with self.assertRaises(basic.DelimitedShorthand.OpenShorthandError):
            self._match('b}}', None)

    @suppress(logging.ERROR)
    def test_broken_opener(self):
        with self.assertRaises(basic.DelimitedShorthand.OpenShorthandError):
            self._match('{b}}', None)

    @suppress(logging.ERROR)
    def test_leftover_opener(self):
        with self.assertRaises(basic.DelimitedShorthand.OpenShorthandError):
            self._match('{{b', '')

    @suppress(logging.ERROR)
    def test_unknown_shorthand_empty(self):
        with self.assertRaises(basic.DelimitedShorthand.UnknownShorthandError):
            self._match('{{}}', '')

    @suppress(logging.ERROR)
    def test_unknown_shorthand_nonempty(self):
        with self.assertRaises(basic.DelimitedShorthand.UnknownShorthandError):
            self._match('{{a}}', '')

    def test_match_solo(self):
        self._match('{{b}}', 'y')

    def test_single_match_context(self):
        self._match('a{{b}}a', 'aya')

    def test_double_match_context(self):
        self._match('a{{b}}{{b}}a', 'ayya')

    def test_separating_context(self):
        self._match('a{{b}}a{{b}}a', 'ayaya')

    def test_recursion(self):
        self._match('a{{c}}a', 'aya')

    def test_explosion(self):
        self._match('a{{d}}a', 'ayya')

    def test_escape(self):
        self._match(r'a\{\{c\}\}a', r'a\{\{c\}\}a')


class CustomDelimiters(unittest.TestCase):
    class SingleCharacter(basic.DelimitedShorthand):
        registry = list()
        lead_in = '{'
        lead_out = '}'

    class Identical(basic.DelimitedShorthand):
        registry = list()
        lead_in = '%'
        lead_out = '%'

    def test_single_character(self):
        p = CustomDelimiters.SingleCharacter('a', lambda: 'x')
        self.assertEqual(p.sub('abc'), 'abc')
        self.assertEqual(p.sub('{a}bc'), 'xbc')
        self.assertEqual(p.sub(r'{a}\}bc'), r'x\}bc')
        self.assertEqual(p.sub(r'\{{a}bc'), r'\{xbc')

    def test_identical(self):
        p = CustomDelimiters.Identical('a', lambda: 'x')
        self.assertEqual(p.sub('abc'), 'abc')
        self.assertEqual(p.sub('%a%bc'), 'xbc')
        self.assertEqual(p.sub(r'\%a\%bc'), r'\%a\%bc')
        self.assertEqual(p.sub('\%a\%bc'), '\%a\%bc')


class Caching(unittest.TestCase):
    class SubClass(basic.DelimitedShorthand):
        pass

    def setUp(self):
        basic.OneWayProcessor._cache.clear()
        basic.DelimitedShorthand._cache.clear()
        self.SubClass._cache.clear()

    def test_new_with_metaclassing(self):
        self.assertNotEqual(id(basic.OneWayProcessor._cache),
                            id(basic.DelimitedShorthand._cache))
        self.assertIsNot(basic.OneWayProcessor._cache,
                         basic.DelimitedShorthand._cache)

    def test_new_with_subclassing(self):
        self.assertNotEqual(id(basic.OneWayProcessor._cache),
                            id(self.SubClass._cache))
        self.assertIsNot(basic.OneWayProcessor._cache,
                         self.SubClass._cache)

    def test_shared_with_instantiation(self):
        a, b = self.SubClass('a', None), self.SubClass('b', None)

        self.assertEqual(id(a._cache), id(b._cache))
        self.assertIs(a._cache, b._cache)

    def test_use(self):
        def f():
            return 'r'

        self.assertFalse(self.SubClass._cache)
        self.SubClass('p', f)
        ret = self.SubClass.collective_sub('a{{p}}')
        self.assertEqual(ret, 'ar')
        self.assertTrue(self.SubClass._cache)


class DynamicSubclassing(unittest.TestCase):
    def test_oneway(self):
        c = basic.OneWayProcessor.variant_class()
        self.assertEqual(str(c), "<class 'ovid.basic.Custom'>")
        self.assertEqual(c.__bases__, (basic.OneWayProcessor,))

    def test_collective(self):
        basic.CollectiveProcessor.registry.clear()
        basic.CollectiveProcessor.registry.append('dummy')
        c = basic.CollectiveProcessor.variant_class()
        self.assertListEqual(c.registry, [])

    def test_delimited_caching(self):
        def f():
            return 'x'

        c = basic.DelimitedShorthand.variant_class(name='Busybody',
                                                   lead_in=re.escape('|'),
                                                   lead_out=re.escape('|'),
                                                   escape='´´')
        c('g', f)
        ret = c.collective_sub('´|g|a')
        self.assertEqual(ret, '´xa')
