# -*- coding: utf-8 -*-
"""Unit tests for the inspecting module."""


import logging
import re
import unittest.mock as mock

from pytest import fixture
from pytest import raises

from ovid.inspecting import SignatureShorthand as Signature
from ovid.inspecting import IndiscriminateShorthand as Indiscriminate


#############
# NON-TESTS #
#############


_Unknown = Signature.UnknownShorthandError
_Open = Signature.OpenShorthandError


######################
# TESTS OF RECURSION #
######################


def _recurse(string, reference_output, *argsets, unknown=False):
    """Perform a series of checks."""
    responses = {'b': '',
                 'c': 'y',
                 'd': '{{c|2|kw=3}}',
                 'e': '{{b|kw=1}}'}

    # Part 1: Indiscriminate with master function.
    m = mock.Mock()
    Indiscriminate.registry.clear()

    def f(*args, **kwargs):
        m(*args, **kwargs)
        return responses.get(args[0], 'x')

    Indiscriminate(f)
    output = Indiscriminate.collective_sub(string)

    assert [mock.call(*a, **ka) for a, ka in argsets] == m.call_args_list
    assert reference_output == output

    # Part 2: Signature-based.
    m = mock.Mock()
    Signature.registry.clear()

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

    Signature(b)
    Signature(c)
    Signature(d)
    Signature(e)

    if unknown:
        with raises(_Unknown):
            output = Signature.collective_sub(string)
        return
    else:
        output = Signature.collective_sub(string)

    assert [mock.call(*a[1:], **ka) for a, ka in argsets] == m.call_args_list
    assert reference_output == output


def test_single():
    _recurse('a{{c|1|kw=2}}e', 'aye', (('c', '1'), {'kw': '2'}))


def test_recursive():
    _recurse('{{b|kw=b}}{{d}}', 'y',
             (('b',), {'kw': 'b'}),
             (('d',), {}),
             (('c', '2'), {'kw': '3'}))


def test_reverse_recursive():
    _recurse('{{d}}{{b|kw=b}}', 'y',
             (('d',), {}),
             (('c', '2'), {'kw': '3'}),
             (('b',), {'kw': 'b'}))


def test_nesting_valid():
    _recurse('{{d{{e}}}}', 'y',
             (('e',), {}),
             (('b',), {'kw': '1'}),
             (('d',), {}),
             (('c', '2'), {'kw': '3'}))


def test_nesting_multiline():
    _recurse('{{d{{e}}}}', 'y',
             (('e',), {}),
             (('b',), {'kw': '1'}),
             (('d',), {}),
             (('c', '2'), {'kw': '3'}))


def test_nesting_invalid(caplog):
    caplog.set_level(logging.WARNING)
    _recurse('{{a{{c}}}}', 'x',
             (('c',), {}),
             (('ay',), {}),
             unknown=True)


############################################
# TESTS OF SignatureShorthand CONSTRUCTION #
############################################

def _signed(string, output_reference):
    """Perform a check using a simple processor."""
    sh = Signature
    sh.registry.clear()

    def f(arg, kw0=1, kw1=None):
        return ' '.join(map(str, (arg, kw0, kw1)))

    sh(f)
    assert output_reference == sh.collective_sub(string)


def test_extraneous_kwarg(caplog):
    caplog.set_level(logging.WARNING)
    with raises(_Unknown):
        _signed('{{f|1|kw0=1|kw1=1|kw2=1}}', None)


def test_all_present():
    _signed('{{f|1|kw0=1|kw1=1}}', '1 1 1')


def test_missing_kwarg():
    _signed('{{f|1|kw0=1}}', '1 1 None')


def test_other_missing_kwarg():
    _signed('{{f|1|kw1=1}}', '1 1 1')


def test_no_kwargs():
    _signed('{{f|1}}', '1 1 None')


def test_empty_arg():
    _signed('{{f|}}', ' 1 None')


def test_arg_resembling_kwarg_negative(caplog):
    caplog.set_level(logging.ERROR)
    with raises(_Unknown):
        _signed('{{f|arg=1}}', None)
    with raises(_Unknown):
        _signed('{{f|kw0=1}}', None)


def test_arg_resembling_kwarg_positive(caplog):
    caplog.set_level(logging.ERROR)
    _signed('{{f|1=1|kw0=arg=1}}', '1=1 arg=1 None')


def test_function_only(caplog):
    caplog.set_level(logging.ERROR)
    with raises(_Unknown):
        _signed('{{f}}', None)


def test_missing_leadout(caplog):
    caplog.set_level(logging.ERROR)
    with raises(_Open):
        _signed('{{f|1', None)


###########################
# TESTS OF TAILING MATTER #
###########################

@fixture
def _tail():
    class SingleCharacterDelimiters(Signature):
        registry = list()
        lead_in = '{'
        lead_out = '}'

    class Multiline(Signature):
        registry = list()
        flags = re.DOTALL

    def a(one):
        return one

    yield [SingleCharacterDelimiters(a), Signature(a), Multiline(a)]


def test_negative(_tail):
    a1, a2, a3 = _tail
    assert a1.collective_sub('abc') == 'abc'
    assert a2.collective_sub('abc') == 'abc'
    assert a3.collective_sub('abc') == 'abc'


def test_inert(_tail):
    a1, a2, a3 = _tail
    assert a1.collective_sub('{a|x}bc') == 'xbc'
    assert a2.collective_sub('{{a|x}}bc') == 'xbc'
    assert a3.collective_sub('{{a|x}}bc') == 'xbc'


def test_multiline(_tail, caplog):
    a1, a2, a3 = _tail
    caplog.set_level(logging.ERROR)
    with raises(Signature.OpenShorthandError):
        assert a1.collective_sub('{a|x\ny}bc') == 'x\nybc'
    with raises(Signature.OpenShorthandError):
        assert a2.collective_sub('{{a|x\ny}}bc') == 'x\nybc'
    assert a3.collective_sub('{{a|x\ny}}bc') == 'x\nybc'


#######################################
# TESTS OF REGISTRATION VIA DECORATOR #
#######################################

def test_decoration():
    Indiscriminate.registry.clear()

    @Indiscriminate.register
    def f(name):
        return 'e' + name

    ret = Indiscriminate.collective_sub('t{{x}}t')
    assert ret == 'text'
