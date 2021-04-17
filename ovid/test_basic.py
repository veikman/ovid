# -*- coding: utf-8 -*-
"""Unit tests for the basic module."""

import collections
import logging
import re

from pytest import raises
from pytest import fixture

from ovid.basic import OneWayProcessor as OWProc
from ovid.basic import CollectiveProcessor as CProc
from ovid.basic import DelimitedShorthand as Delimited
from ovid.basic import AutoRegisteringProcessor as AutoProc


#############
# NON-TESTS #
#############

@fixture
def cleared():
    """Clear caches and provide a new subclass."""
    CProc.registry.clear()
    OWProc._cache.clear()
    Delimited._cache.clear()

    class SubClass(Delimited):
        pass
    SubClass._cache.clear()

    yield SubClass


@fixture
def delimited():
    """Provide a semi-realistic set of processors.

    Return a function for their collective application, as a convenience.

    """
    Delimited.registry.clear()
    Delimited._cache.clear()
    Delimited('(b)', lambda *_: 'y')
    Delimited('(c)', lambda *_: '{{b}}')
    Delimited('(d)', lambda *_: '{{c}}{{c}}')

    yield Delimited.collective_sub


###############
# BASIC TESTS #
###############

def test_elementary():
    assert OWProc('a', lambda: 'b').sub('a') == 'b'


def test_multiline_single_blank():
    pattern = '''a

    a'''
    sample = '''Aa

    aA'''
    processor = OWProc(pattern, lambda: 'b')
    assert processor.sub(sample) == 'AbA'


def test_multiline_double_blank():
    pattern = '''a


    a'''
    sample = '''Aa


    aA'''
    processor = OWProc(pattern, lambda: 'b')
    assert processor.sub(sample) == 'AbA'


def test_operation_on_unnamed_group():
    assert OWProc('(.)', lambda v: 2 * v).sub('a') == 'aa'


def test_collective_simple():
    cls = AutoProc
    cls.registry.clear()
    cls('a', lambda: 'A')
    cls('b', lambda: 'B')

    assert cls.collective_sub('ab') == 'AB'
    assert cls.collective_sub('bab') == 'BAB'
    assert cls.collective_sub('c') == 'c'

    # Tempt infinite recursion. 'C' will match '.'.
    cls('.', lambda: 'C')

    assert cls.collective_sub('c') == 'C'


###############################
# TESTS OF DelimitedShorthand #
###############################


def test_clean_empty(delimited):
    assert delimited('') == ''


def test_clean_nonempty(delimited):
    assert delimited('a') == 'a'


def test_no_markup_tokens(delimited):
    assert delimited('b') == 'b'


def test_leftover_closer(delimited, caplog):
    caplog.set_level(logging.ERROR)
    with raises(Delimited.OpenShorthandError):
        delimited('b}}')


def test_broken_opener(delimited, caplog):
    caplog.set_level(logging.ERROR)
    with raises(Delimited.OpenShorthandError):
        delimited('{b}}')


def test_leftover_opener(delimited, caplog):
    caplog.set_level(logging.ERROR)
    with raises(Delimited.OpenShorthandError):
        delimited('{{b')


def test_unknown_shorthand_empty(delimited, caplog):
    caplog.set_level(logging.ERROR)
    with raises(Delimited.UnknownShorthandError):
        delimited('{{}}')


def test_unknown_shorthand_nonempty(delimited, caplog):
    caplog.set_level(logging.ERROR)
    with raises(Delimited.UnknownShorthandError):
        delimited('{{a}}')


def test_match_solo(delimited):
    assert delimited('{{b}}') == 'y'


def test_single_match_context(delimited):
    assert delimited('a{{b}}a') == 'aya'


def test_double_match_context(delimited):
    assert delimited('a{{b}}{{b}}a') == 'ayya'


def test_separating_context(delimited):
    assert delimited('a{{b}}a{{b}}a') == 'ayaya'


def test_recursion(delimited):
    assert delimited('a{{c}}a') == 'aya'


def test_explosion(delimited):
    assert delimited('a{{d}}a') == 'ayya'


def test_escape(delimited):
    assert delimited(r'a\{\{c\}\}a') == r'a\{\{c\}\}a'


##############################
# TESTS OF CUSTOM DELIMITERS #
##############################

def test_single_character():
    class SingleCharacter(Delimited):
        registry = list()
        lead_in = '{'
        lead_out = '}'

    # A single-character pattern with single-character delimitation.
    p = SingleCharacter('a', lambda: 'x')
    assert p.sub('abc') == 'abc'
    assert p.sub('{a}bc') == 'xbc'
    assert p.sub(r'{a}\}bc') == r'x\}bc'
    assert p.sub(r'\{{a}bc') == r'\{xbc'

    # A larger, multi-line pattern with single-character delimitation.
    p = SingleCharacter('a\na', lambda: 'x')
    assert p.sub('abc') == 'abc'
    assert p.sub('{a\na}bc') == 'xbc'
    assert p.sub('{a\na}\\}bc') == r'x\}bc'
    assert p.sub('\\{{a\na}bc') == r'\{xbc'


def test_identical():
    class Identical(Delimited):
        registry = list()
        lead_in = '%'
        lead_out = '%'

    p = Identical('a', lambda: 'x')
    assert p.sub('abc') == 'abc'
    assert p.sub('%a%bc') == 'xbc'
    assert p.sub(r'\%a\%bc') == r'\%a\%bc'
    assert p.sub(r'\%a\%bc') == r'\%a\%bc'


####################
# TESTS OF CACHING #
####################


def test_new_with_metaclassing(cleared):
    assert id(OWProc._cache) != id(Delimited._cache)
    assert OWProc._cache is not Delimited._cache


def test_new_with_subclassing(cleared):
    assert id(OWProc._cache) != id(cleared._cache)
    assert OWProc._cache is not cleared._cache


def test_shared_with_instantiation(cleared):
    a, b = cleared('a', None), cleared('b', None)

    assert id(a._cache) == id(b._cache)
    assert a._cache is b._cache


def test_use(cleared):
    def f():
        return 'r'

    assert not cleared._cache
    cleared('p', f)
    ret = cleared.collective_sub('a{{p}}')
    assert ret == 'ar'
    assert cleared._cache


################################
# TESTS OF DYNAMIC SUBCLASSING #
################################

def test_oneway():
    c = OWProc.variant_class()
    assert str(c) == "<class 'ovid.basic.Custom'>"
    assert c.__bases__ == (OWProc,)


def test_collective_dynamic():
    CProc.registry.clear()
    CProc.registry.append('dummy')
    c = CProc.variant_class()
    assert c.registry == []


def test_delimited_caching():
    def f():
        return 'x'

    c = Delimited.variant_class(name='Busybody',
                                lead_in=re.escape('|'),
                                lead_out=re.escape('|'),
                                escape='´´')
    c('g', f)
    ret = c.collective_sub('´|g|a')
    assert ret == '´xa'


#################################
# TESTS OF ARGUMENT PASSTHROUGH #
#################################

# The passing of arguments to a processor function via sub().

def test_single():
    deque = collections.deque()

    def f(string, passthrough=None):
        deque.append(string)
        deque.append(passthrough)
        return 'c'

    processor = OWProc('(.+)', f)
    ret = processor.sub('a', passthrough='b')

    assert ret == 'c'
    assert deque.popleft() == 'a'
    assert deque.popleft() == 'b'
    assert not deque

    ret = processor.sub('d', passthrough=1)

    assert ret == 'c'
    assert deque.popleft() == 'd'
    assert deque.popleft() == 1
    assert not deque

    ret = processor.sub('e')

    assert ret == 'c'
    assert deque.popleft() == 'e'
    assert deque.popleft() is None
    assert not deque


def test_multiple():
    deque = collections.deque()

    def f(_, **kwargs):
        deque.append(kwargs)
        return '_'

    processor = OWProc('(.+)', f)
    ret = processor.sub('a', b0='b', b1='B')

    assert ret == '_'
    assert deque.popleft() == {'b0': 'b', 'b1': 'B'}
    assert not deque

    processor.sub('_', lst=['a'])

    assert deque.popleft() == {'lst': ['a']}
    assert not deque


def test_basic_collective():
    deque = collections.deque()

    def f0(string, passthrough=None):
        deque.append(string)
        if passthrough is not None:
            deque.append(passthrough)
        return '¹'

    def f1(string, passthrough=None):
        f0(string, passthrough=passthrough)
        return '²'

    AutoProc.registry.clear()
    AutoProc('(a)', f0)
    AutoProc('(.+)', f1)

    ret = AutoProc.collective_sub('b')

    assert ret == '²'
    assert deque.popleft() == 'b'
    assert deque.popleft() == '²'
    assert not deque

    ret = AutoProc.collective_sub('a', passthrough=True)

    assert ret == '²'
    assert deque.popleft() == 'a'
    assert deque.popleft() is True
    assert deque.popleft() == '¹'
    assert deque.popleft() is True
    assert deque.popleft() == '²'
    assert deque.popleft() is True
    assert not deque

    ret = AutoProc.collective_sub('A', passthrough=False)

    assert ret == '²'
    assert deque.popleft() == 'A'
    assert deque.popleft() is False
    assert deque.popleft() == '²'
    assert deque.popleft() is False
    assert not deque


def test_delimited_collective():
    deque = collections.deque()

    class Processor(Delimited):
        pass

    def f0(passthrough=None):
        deque.append(passthrough)
        return '¹'

    Processor.registry.clear()
    Processor._cache.clear()
    Processor('a', f0)

    ret = Processor.collective_sub('{{a}}')

    assert ret == '¹'
    assert deque.popleft() is None
    assert not deque

    ret = Processor.collective_sub('{{a}}', passthrough='A')

    assert ret == '¹'
    assert deque.popleft() == 'A'
    assert not deque
