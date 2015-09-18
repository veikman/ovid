# -*- coding: utf-8 -*-
'''Unit tests for the inspecting module.'''

import logging
import unittest
import unittest.mock as mock

import ovid.inspecting as inspecting
import ovid.test_basic as test_basic


_Unknown = inspecting.SignatureShorthand.UnknownShorthandError
_Open = inspecting.SignatureShorthand.OpenShorthandError


class RecursiveCollective(unittest.TestCase):
    def _match(self, string, reference_output, *argsets, unknown=False):
        responses = {'b': '',
                     'c': 'y',
                     'd': '{{c|2|kw=3}}',
                     'e': '{{b|kw=1}}'}

        # Part 1: Indiscriminate with master function.
        m = mock.Mock()
        inspecting.IndiscriminateShorthand.registry.clear()

        def f(*args, **kwargs):
            m(*args, **kwargs)
            return responses.get(args[0], 'x')

        inspecting.IndiscriminateShorthand(f)
        output = inspecting.IndiscriminateShorthand.collective_sub(string)

        self.assertListEqual([mock.call(*a, **ka) for a, ka in argsets],
                             m.call_args_list)
        self.assertEqual(reference_output, output)

        # Part 2: Signature-based.
        m = mock.Mock()
        inspecting.SignatureShorthand.registry.clear()

        def b(kw=None):
            m(kw=kw)
            return responses['b']

        def c(arg, kw=None):
            m(arg, kw=kw)
            return responses['c']

        def d():
            m()
            return responses['d']

        def e():
            m()
            return responses['e']

        inspecting.SignatureShorthand(b)
        inspecting.SignatureShorthand(c)
        inspecting.SignatureShorthand(d)
        inspecting.SignatureShorthand(e)

        if unknown:
            with self.assertRaises(_Unknown):
                output = inspecting.SignatureShorthand.collective_sub(string)
            return
        else:
            output = inspecting.SignatureShorthand.collective_sub(string)

        self.assertListEqual([mock.call(*a[1:], **ka) for a, ka in argsets],
                             m.call_args_list)
        self.assertEqual(reference_output, output)

    def test_single(self):
        self._match('a{{c|1|kw=2}}e', 'aye', (('c', '1'), {'kw': '2'}))

    def test_recursive(self):
        self._match('{{b|kw=b}}{{d}}', 'y',
                    (('b',), {'kw': 'b'}),
                    (('d',), {}),
                    (('c', '2'), {'kw': '3'}))

    def test_reverse_recursive(self):
        self._match('{{d}}{{b|kw=b}}', 'y',
                    (('d',), {}),
                    (('c', '2'), {'kw': '3'}),
                    (('b',), {'kw': 'b'}))

    def test_nesting_valid(self):
        self._match('{{d{{e}}}}', 'y',
                    (('e',), {}),
                    (('b',), {'kw': '1'}),
                    (('d',), {}),
                    (('c', '2'), {'kw': '3'}))

    @test_basic.suppress(logging.WARNING)
    def test_nesting_invalid(self):
        self._match('{{a{{c}}}}', 'x',
                    (('c',), {}),
                    (('ay',), {}),
                    unknown=True)


class SignatureShorthandConstruction(unittest.TestCase):
    def _match(self, string, output_reference):
        sh = inspecting.SignatureShorthand
        sh.registry.clear()

        def f(arg, kw0=1, kw1=None):
            return ' '.join(map(str, (arg, kw0, kw1)))

        sh(f)
        self.assertEqual(output_reference, sh.collective_sub(string))

    @test_basic.suppress(logging.WARNING)
    def test_extraneous_kwarg(self):
        with self.assertRaises(_Unknown):
            self._match('{{f|1|kw0=1|kw1=1|kw2=1}}', None)

    def test_all_present(self):
        self._match('{{f|1|kw0=1|kw1=1}}', '1 1 1')

    def test_missing_kwarg(self):
        self._match('{{f|1|kw0=1}}', '1 1 None')

    def test_other_missing_kwarg(self):
        self._match('{{f|1|kw1=1}}', '1 1 1')

    def test_no_kwargs(self):
        self._match('{{f|1}}', '1 1 None')

    def test_empty_arg(self):
        self._match('{{f|}}', ' 1 None')

    @test_basic.suppress(logging.ERROR)
    def test_arg_resembling_kwarg_negative(self):
        with self.assertRaises(_Unknown):
            self._match('{{f|arg=1}}', None)
        with self.assertRaises(_Unknown):
            self._match('{{f|kw0=1}}', None)

    @test_basic.suppress(logging.ERROR)
    def test_arg_resembling_kwarg_positive(self):
        self._match('{{f|1=1|kw0=arg=1}}', '1=1 arg=1 None')

    @test_basic.suppress(logging.ERROR)
    def test_function_only(self):
        with self.assertRaises(_Unknown):
            self._match('{{f}}', None)

    @test_basic.suppress(logging.ERROR)
    def test_missing_leadout(self):
        with self.assertRaises(_Open):
            self._match('{{f|1', None)


class Tail(unittest.TestCase):
    '''Not to be confused with test_basic.CustomDelimiters.'''

    class SingleCharacterDelimiters(inspecting.SignatureShorthand):
        registry = list()
        lead_in = '{'
        lead_out = '}'

    @classmethod
    def setUpClass(cls):
        def a(one):
            return one

        cls.a1 = cls.SingleCharacterDelimiters(a)
        cls.a2 = inspecting.SignatureShorthand(a)

    def test_negative(self):
        self.assertEqual(self.a1.collective_sub('abc'), 'abc')
        self.assertEqual(self.a2.collective_sub('abc'), 'abc')

    def test_inert(self):
        self.assertEqual(self.a1.collective_sub('{a|x}bc'), 'xbc')
        self.assertEqual(self.a2.collective_sub('{{a|x}}bc'), 'xbc')
