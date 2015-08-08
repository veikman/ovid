# -*- coding: utf-8 -*-
'''Unit tests for the mm module.'''

import unittest
import unittest.mock as mock

import ovid.mm as mm


class SubstitutionElements(unittest.TestCase):
    def _forwards(self, regex, *args, **kwargs):
        '''Examine a generated substitution function signature.'''
        m = mock.Mock()

        def f(*args, **kwargs):
            m(*args, **kwargs)
            return ''

        processor = mm.OneWayProcessor(regex, f)
        processor.sub('abc')
        m.assert_called_once_with(*args, **kwargs)

    def _backwards(self, regex, reference_output, *args, **kwargs):
        '''Examine the matchable product of reverse operation.'''
        processor = mm.TwoWayProcessor(regex, lambda: None)
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
        mm.DelimitedShorthand.registry.clear()
        mm.DelimitedShorthand('(b)', lambda *_: 'y')
        mm.DelimitedShorthand('(c)', lambda *_: '{{b}}')

    def _match(self, text_in, text_out):
        self.assertEqual(mm.DelimitedShorthand.collective_sub(text_in),
                         text_out)

    def test_clean_empty(self):
        self._match('', '')

    def test_clean_nonempty(self):
        self._match('a', 'a')

    def test_no_markup_tokens(self):
        self._match('b', 'b')

    def test_leftover_closer(self):
        with self.assertRaises(mm.DelimitedShorthand.OpenShorthandError):
            self._match('b}}', 'b}}')

    def test_leftover_opener(self):
        with self.assertRaises(mm.DelimitedShorthand.OpenShorthandError):
            self._match('{{b', '')

    def test_unknown_shorthand_empty(self):
        with self.assertRaises(mm.DelimitedShorthand.UnknownShorthandError):
            self._match('{{}}', '')

    def test_unknown_shorthand_nonempty(self):
        with self.assertRaises(mm.DelimitedShorthand.UnknownShorthandError):
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


class MasterFunction(unittest.TestCase):
    def _match(self, string, reference_output, *args):
        m = mock.Mock()

        responses = {'b': '',
                     'c': 'y',
                     'd': '{{c}}',
                     'e': '{{b|1}}'}

        def f(string):
            m(*string.split('|'))
            return responses.get(string[0], 'x')

        mm.GenericDelimitedShorthand.registry.clear()
        mm.GenericDelimitedShorthand(f)
        output = mm.GenericDelimitedShorthand.collective_sub(string)

        self.assertEqual(reference_output, output)
        self.assertListEqual([mock.call(*a) for a in args], m.call_args_list)

    def test_minimal(self):
        self._match('a{{c}}e', 'aye', ['c'])

    def test_parameter(self):
        self._match('{{b|2}}', '', ['b', '2'])

    def test_recursive(self):
        self._match('{{b}}{{d}}', 'y', ['b'], ['d'], ['c'])

    def test_reverse_recursive(self):
        self._match('{{d}}{{b}}', 'y', ['d'], ['c'], ['b'])

    def test_nesting_valid(self):
        self._match('{{d{{e}}}}', 'y', ['e'], ['b', '1'], ['d'], ['c'])

    def test_nesting_invalid(self):
        self._match('{{a{{c}}}}', 'x', ['c'], ['ay'])


class CustomDelimiters(unittest.TestCase):
    def test_single_parens(self):
        class Parentheses(mm.DelimitedShorthand):
            registry = list()
            lead_in = '%'
            lead_out = '%'

        p = Parentheses('a', lambda: 'x')
        self.assertEqual(p.sub('abc'), 'abc')
        self.assertEqual(p.sub('%a%bc'), 'xbc')
