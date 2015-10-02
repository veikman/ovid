# -*- coding: utf-8 -*-
'''String metamorposis via tokens derived from function signatures.'''


import inspect
import re

import ovid.basic


class AutoEscapingCacher(ovid.basic.Cacher):
    '''A metaclass for classes that need separators and operators.'''

    def __new__(cls, *args, **kwargs):
        new = super().__new__(cls, *args, **kwargs)
        new._separator_escaped = re.escape(new.separator)
        new._assignment_operator_escaped = re.escape(new.assignment_operator)
        return new


class _FunctionLikeDelimitedShorthand(ovid.basic.DelimitedShorthand,
                                      metaclass=AutoEscapingCacher):
    '''Base class for further conveniences.'''

    separator = '|'
    assignment_operator = '='

    _python_identifier = r'[^\d\W]\w*'

    @classmethod
    def swallow(cls, function):
        '''A decorator for use on markup functions.

        Used alone, what this does is to register the decorated
        function as markup and replace the decorated function in the
        namespace of its module with the markup created from it.

        This is useful mainly for two-way (producing) markup
        processors, which need to be individually accessible.

        '''
        return cls(function)

    @classmethod
    def register(cls, function):
        '''A decorator for use on markup functions.

        The effect of this is the same as transform(), except that
        the function is left intact in the namespace, and the markup
        ends up less accessible in the registry of the class.

        '''
        cls.swallow(function)
        return function


class SignatureShorthand(_FunctionLikeDelimitedShorthand):
    '''Markup that looks like a function call.

    This is based on automatic inspection of the function, which is
    not fully featured. Variable numbers of arguments, for example,
    are not handled.

    '''

    def __init__(self, function):
        '''A few things done here are unnecessary for this one-way version.

        They're intended for the producing subclass.

        '''
        argspec = inspect.getfullargspec(function)
        n_named = len(argspec.defaults if argspec.defaults else ())
        n_unnamed = len(argspec.args) - n_named

        pattern = function.__name__
        active_op = self._unescape(self._assignment_operator_escaped)
        active_sep = self._unescape(self._separator_escaped)

        # The actual content of an unnamed group must not look like a
        # named group and must not contain an active separator.
        s = r'(?!{i}{o})((?:(?!{s}).)*)'.format(i=self._python_identifier,
                                                o=active_op,
                                                s=active_sep)
        self._unnamed_pattern = self._double_braces(s)

        # Mandatory unnamed arguments, with separators.
        subpattern = r'{s}{c}'.format(c=self._unnamed_pattern,
                                      s=active_sep)
        for _ in argspec.args[:n_unnamed]:
            pattern += subpattern

        # A named group is simpler, though its prefix is more complicated.
        s = r'(?:(?!{s}).)*'.format(s=active_sep)
        self._named_pattern = self._double_braces(s)

        # Optional named arguments.
        subpattern = r'(?:{s}{{0}}{o}(?P<{{0}}>{c}))?'
        subpattern = subpattern.format(c=self._named_pattern,
                                       o=active_op,
                                       s=active_sep)
        for name in argspec.args[n_unnamed:]:
            pattern += subpattern.format(name)

        super().__init__(pattern, function)


class IndiscriminateShorthand(_FunctionLikeDelimitedShorthand):
    '''Hit anything in delimiters.

    Very similar to SignatureShorthand, but for use with a generic
    variadic master function: a switchboard that handles all markup.

    '''

    def __init__(self, function):
        '''Accept any content, but lazily, and cushioned by delimiters.'''
        super().__init__('(.*?)', function)

    def _process(self, matchobject):
        '''Break down the single unnamed group in the regex.'''
        unnamed, _ = self._unique_groups(matchobject)
        args, kwargs = self._tokenize(unnamed[0])
        return self.function(*args, **kwargs)

    def _tokenize(self, string):
        args, kwargs = list(), dict()
        elements = re.split(self._separator_escaped, string)

        for e in elements:
            try:
                key, value = re.split(self._assignment_operator_escaped, e,
                                      maxsplit=1)
            except ValueError:
                # Did not split.
                args.append(e)
            else:
                kwargs[key] = value

        return (args, kwargs)
