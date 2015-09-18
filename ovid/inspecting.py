# -*- coding: utf-8 -*-
'''String metamorposis via tokens derived from function signatures.'''


import inspect
import re

import ovid.basic


class _FunctionLikeDelimitedShorthand(ovid.basic.DelimitedShorthand):
    '''Base class for further conveniences.'''

    separator = re.escape(r'|')
    assignment_operator = re.escape(r'=')

    _python_identifier = r'[^\d\W]\w*'


class SignatureShorthand(_FunctionLikeDelimitedShorthand):
    '''Markup that looks like a function call.

    This is based on automatic inspection of the function, which is
    not fully featured. Variable numbers of arguments, for example,
    are not handled.

    '''

    def __init__(self, function):
        argspec = inspect.getfullargspec(function)
        n_named = len(argspec.defaults if argspec.defaults else ())
        n_unnamed = len(argspec.args) - n_named

        pattern = function.__name__
        active_op = self._unescape(self.assignment_operator)
        active_sep = self._unescape(self.separator)

        # Mandatory unnamed arguments.
        # These cannot start with a valid identifier followed by the
        # assignment operator, because that'd create ambiguity.
        subpattern = r'((?!{i}{o})(?:(?!{s}).)*)'
        unnamed = subpattern.format(i=self._python_identifier,
                                    o=active_op,
                                    s=active_sep)
        for _ in argspec.args[:n_unnamed]:
            pattern += active_sep + unnamed

        # Optional named arguments.
        subpattern = r'(?:{s}{n}{o}(?P<{n}>(?:(?!{s}).)*))?'
        for name in argspec.args[n_unnamed:]:
            pattern += subpattern.format(n=name,
                                         o=active_op,
                                         s=active_sep)

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
        elements = re.split(self.separator, string)

        for e in elements:
            try:
                key, value = re.split(self.assignment_operator, e, maxsplit=1)
            except ValueError:
                # Did not split.
                args.append(e)
            else:
                kwargs[key] = value

        return (args, kwargs)
