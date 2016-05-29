# -*- coding: utf-8 -*-
'''Unit tests for the basic module.'''


import collections
import logging
import re
import unittest

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


class Basic(unittest.TestCase):
    def test_elementary(self):
        self.assertEqual(basic.OneWayProcessor('a', lambda: 'b').sub('a'), 'b')

    def test_operation_on_unnamed_group(self):
        self.assertEqual(basic.OneWayProcessor('(.)',
                                               lambda v: 2 * v).sub('a'),
                         'aa')

    def test_collective(self):
        cls = basic.AutoRegisteringProcessor
        cls.registry.clear()
        cls('a', lambda: 'A')
        cls('b', lambda: 'B')

        ret = cls.collective_sub('ab')
        self.assertEqual(ret, 'AB')

        ret = cls.collective_sub('bab')
        self.assertEqual(ret, 'BAB')

        ret = cls.collective_sub('c')
        self.assertEqual(ret, 'c')

        # Tempt infinite recursion. 'C' will match '.'.
        cls('.', lambda: 'C')

        ret = cls.collective_sub('c')
        self.assertEqual(ret, 'C')


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
        basic.CollectiveProcessor.registry.clear()
        basic.OneWayProcessor._cache.clear()
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


class Passthrough(unittest.TestCase):
    def test_single(self):
        deque = collections.deque()

        def f(string, passthrough=None):
            deque.append(string)
            deque.append(passthrough)
            return 'c'

        processor = basic.OneWayProcessor('(.*)', f)
        ret = processor.sub('a', passthrough='b')

        self.assertEqual(ret, 'c')
        self.assertEqual(deque.popleft(), 'a')
        self.assertEqual(deque.popleft(), 'b')
        self.assertFalse(deque)

        ret = processor.sub('d', passthrough=1)

        self.assertEqual(ret, 'c')
        self.assertEqual(deque.popleft(), 'd')
        self.assertEqual(deque.popleft(), 1)
        self.assertFalse(deque)

        ret = processor.sub('e')

        self.assertEqual(ret, 'c')
        self.assertEqual(deque.popleft(), 'e')
        self.assertEqual(deque.popleft(), None)
        self.assertFalse(deque)

    def test_multiple(self):
        deque = collections.deque()

        def f(_, **kwargs):
            deque.append(kwargs)
            return '_'

        processor = basic.OneWayProcessor('(.*)', f)
        ret = processor.sub('a', b0='b', b1='B')

        self.assertEqual(ret, '_')
        self.assertEqual(deque.popleft(), {'b0': 'b', 'b1': 'B'})
        self.assertFalse(deque)

        processor.sub('_', lst=['a'])

        self.assertEqual(deque.popleft(), {'lst': ['a']})
        self.assertFalse(deque)

    def test_basic_collective(self):
        deque = collections.deque()

        def f0(string, passthrough=None):
            deque.append(string)
            if passthrough is not None:
                deque.append(passthrough)
            return '¹'

        def f1(string, passthrough=None):
            f0(string, passthrough=passthrough)
            return '²'

        basic.AutoRegisteringProcessor.registry.clear()
        basic.AutoRegisteringProcessor('(a)', f0)
        basic.AutoRegisteringProcessor('(.*)', f1)

        ret = basic.AutoRegisteringProcessor.collective_sub('b')

        self.assertEqual(ret, '²')
        self.assertEqual(deque.popleft(), 'b')
        self.assertEqual(deque.popleft(), '²')
        self.assertFalse(deque)

        ret = basic.AutoRegisteringProcessor.collective_sub('a',
                                                            passthrough=True)

        self.assertEqual(ret, '²')
        self.assertEqual(deque.popleft(), 'a')
        self.assertEqual(deque.popleft(), True)
        self.assertEqual(deque.popleft(), '¹')
        self.assertEqual(deque.popleft(), True)
        self.assertEqual(deque.popleft(), '²')
        self.assertEqual(deque.popleft(), True)
        self.assertFalse(deque)

        ret = basic.AutoRegisteringProcessor.collective_sub('A',
                                                            passthrough=False)

        self.assertEqual(ret, '²')
        self.assertEqual(deque.popleft(), 'A')
        self.assertEqual(deque.popleft(), False)
        self.assertEqual(deque.popleft(), '²')
        self.assertEqual(deque.popleft(), False)
        self.assertFalse(deque)

    def test_delimited_collective(self):
        deque = collections.deque()

        class Processor(basic.DelimitedShorthand):
            pass

        def f0(passthrough=None):
            deque.append(passthrough)
            return '¹'

        Processor.registry.clear()
        Processor._cache.clear()
        Processor('a', f0)

        ret = Processor.collective_sub('{{a}}')

        self.assertEqual(ret, '¹')
        self.assertEqual(deque.popleft(), None)
        self.assertFalse(deque)

        ret = Processor.collective_sub('{{a}}', passthrough='A')

        self.assertEqual(ret, '¹')
        self.assertEqual(deque.popleft(), 'A')
        self.assertFalse(deque)
