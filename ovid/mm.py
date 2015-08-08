# -*- coding: utf-8 -*-
'''Tools for Ovid's metamorphoses: arbitrary substring substitutions.

This module is not suitable for anything Python's re module can do alone.
It's built for frameworks where nested shorthand expressions can produce
further shorthand expressions that require functions to resolve.

Written for Python 3.4. Backwards compatibility is limited by re.fullmatch.

'''


import re
import logging


class OneWayProcessor():
    '''A tool that replaces one substring pattern with function output.

    This class wraps some familiar re functions in homonymous methods.

    '''

    def __init__(self, pattern, function):
        self.re = self._generate_re(pattern)
        self.function = function

    def _preprocess(self, matchobject):
        '''Break down match objects for the processor function.

        With this stock version, the function passed to the constructor
        of the processor class will _not_ receive a match object, nor
        the complete matching string.

        The function will receive, as its positional arguments, all
        unnamed groups of the regex pattern. As keyword arguments, it
        will receive all named groups, by their respective names.

        Named groups are not duplicated as positional arguments.
        This is unlike the behaviour of Python's re module.

        Example:

        A match on the pattern '(a)(?P<n>b)(c)' will lead to a function
        call resembling f('a', 'c', n='b') and the function, here called
        f, should therefore have a definition similar to this one:

        def f(first_unnamed, second_unnamed, n='default value for n'):
            return 'cooked string'

        '''
        n_unnamed = matchobject.re.groups
        named = set(matchobject.re.groupindex.values())
        unnamed = [i for i in range(1, n_unnamed + 1) if i not in named]
        args = ()
        if unnamed:
            # With 0-1 arguments group() returns a string, else a tuple.
            args = matchobject.group(*unnamed)
            if len(unnamed) == 1:
                args = (args,)
        return self.function(*args, **matchobject.groupdict())

    @classmethod
    def _generate_re(cls, subpattern):
        '''Trivial here. Overridden elsewhere in this module.'''
        return re.compile(subpattern)

    def sub(self, string, **kwargs):
        return re.sub(self.re, self._preprocess, string, **kwargs)

    def subn(self, string, **kwargs):
        return re.subn(self.re, self._preprocess, string, **kwargs)

    def __repr__(self):
        s = '<Ovid processor for {}>'
        return s.format(self.function.__name__)


class TwoWayProcessor(OneWayProcessor):
    '''A processor that can produce targets appropriate for itself.

    This can be used to generate specifications programmatically, for
    later treatment by the same processor in two different stages of a
    program suite.

    '''

    def __init__(self, *args):
        super().__init__(*args)
        self._prepare_production()

    def _prepare_production(self):
        self._production_template = self.re.pattern
        self._production_groups_unnamed = list()
        self._production_groups_named = dict()

        def named_group_collector(match):
            name, content = match.groups()
            self._production_groups_named[name] = re.compile(content)
            return '{{{}}}'.format(name)

        def unnamed_group_collector(match):
            content = match.group(1)
            self._production_groups_unnamed.append(re.compile(content))
            return '{}'

        def collect(metapattern, collector):
            args = (metapattern, collector, self._production_template, 1)
            self._production_template, n = re.subn(*args)
            if n:
                collect(metapattern, collector)

        # Patterns to capture patterns, with fixed-width font commentary.
        metapattern = (r'(?!\\)\('
                       #     ^  ^ leading unescaped parenthesis
                       r'\?P<(?P<name>\w+)>(?P<content>.*?[^\\])'
                       # named groups characterising a named group,
                       # whose content cannot end with a backslash
                       r'\)')
                       # ^ closing parenthesis, unescaped by ^
        collect(metapattern, named_group_collector)

        metapattern = r'(?!\\)\((?!\?)(.*?[^\\])\)'
        # unescaped parens  ^  ^             ^   ^  as delimiters again
        # not a special group       ^
        # otherwise any non-empty string ^
        collect(metapattern, unnamed_group_collector)

    def produce(self, *unnamed, **named):
        '''Present an appropriate target string.'''
        b = 'Cannot reverse {}'.format(repr(self))

        for i, stuff in enumerate(zip(unnamed,
                                      self._production_groups_unnamed)):
            content, regex = stuff
            if not re.fullmatch(regex, content):
                s = "{}: Unnamed group {}'s content '{}' does not match '{}'."
                raise ValueError(s.format(b, i, content, regex))

        for name, content in named.items():
            regex = self._production_groups_named[name]
            if not re.fullmatch(regex, content):
                s = "{}: Named group {}'s content '{}' does not match '{}'."
                raise ValueError(s.format(b, name, content, regex))

        return self._production_template.format(*unnamed, **named)


class CollectiveProcessor(OneWayProcessor):
    '''Adds the ability to run multiple processors recursively.

    The intended use case for this subclass is to do consistent project-
    wide text manipulation with multiple expressions, which may produce
    one another.

    '''
    registry = list()

    @classmethod
    def collective_sub(cls, string, **kwargs):
        '''Apply all registered processors until none are applicable.

        This is a risky way to do the job, highly dependent on the order
        in which the various processors are registered. A depth-first
        version is available in a subclass.

        '''
        for individual_processor in cls.registry:
            string, n = individual_processor.subn(string, **kwargs)
            if n:
                return cls.collective_sub(string, **kwargs)
        return string


class AutoRegisteringProcessor(CollectiveProcessor):
    '''Adds automatic registration of processors on creation.'''

    def __init__(self, *args):
        super().__init__(*args)
        self.registry.append(self)


class DelimitedShorthand(AutoRegisteringProcessor):
    '''A bundle of conveniences.

    The choice of appropriate delimiters for subclasses is currently
    limited by regex conventions. Parentheses, for example, are not
    automatically escaped.

    '''

    lead_in = '{{'
    lead_out = '}}'

    noesc = r'(?<!\\)'  # Negative lookbehind assertion for a backslash.

    class OpenShorthandError(ValueError):
        '''Raised when what appears to be markup is not properly delimited.'''
        pass

    class UnknownShorthandError(ValueError):
        '''Raised when otherwise valid markup has no registered processor.'''
        pass

    @classmethod
    def _generate_re(cls, subpattern):
        '''A significant override.

        We rely on a targetfinder regex to keep this method, and user input,
        relatively simple.

        '''
        return re.compile(''.join((cls.lead_in, subpattern, cls.lead_out)))

    @classmethod
    def _targetfinder(cls):
        '''Generate and cache a pattern useful for working with nesting.

        This pattern has to find the smallest group of any
        characters inside a pair of non-escaped delimiters and containing
        no non-escaped delimiters. The group is allowed to be empty,
        to catch broken markup.

        '''
        try:
            return cls._cached_targetfinder
        except AttributeError:
            i, o = (cls.noesc + cls.lead_in, cls.noesc + cls.lead_out)
            s = r'{i}((?:(?!(?:{e}{i}|{o})).)*?){o}'
            p = s.format(i=i, o=o, e=cls.noesc)
            cls._cached_targetfinder = re.compile(p)
            return cls._cached_targetfinder

    @classmethod
    def collective_sub(cls, raw_string, safe=True, **kwargs):
        '''With optional precautions against sloppy markup.'''
        cooked_string = cls._collective_sub_unsafe(raw_string, **kwargs)

        if safe:
            delimiters = (cls.lead_in, cls.lead_out)
            for delimiter in delimiters:
                if re.search(cls.noesc + delimiter, cooked_string):
                    b = 'Open (unbalanced) shorthand expression'

                    s = '{} resulting from "{}".'
                    logging.error(s.format(b, raw_string))

                    s = '{} in "{}".'
                    logging.error(s.format(b, cooked_string))

                    s = '{}: Found {} without a corresponding {}.'
                    opposite = delimiters[1 - delimiters.index(delimiter)]
                    s = s.format(b, delimiter, opposite)
                    raise cls.OpenShorthandError(s)

        return cooked_string

    @classmethod
    def _collective_sub_unsafe(cls, string, **kwargs):
        '''Depth-first search, using delimiters to control resolution order.'''
        target = re.search(cls._targetfinder(), string, **kwargs)
        if target:
            repl = super().collective_sub(target.group(), **kwargs)
            if repl == target.group():
                # No effect. Likely user error.
                # However, this may also be caused by processors having
                # output identical to their own input.
                s = "Unable to substitute for '{}'."
                raise cls.UnknownShorthandError(s.format(repl))

            # Incorporate the modification.
            string = string[:target.start()] + repl + string[target.end():]

            # Recurse to get the rest.
            return cls._collective_sub_unsafe(string, **kwargs)

        # Nothing else looks like valid markup.
        return string


class GenericDelimitedShorthand(DelimitedShorthand):
    '''A further simplification for use with a generic master function.'''

    def __init__(self, function):
        '''Accept any content, but lazily, and cushioned by delimiters.'''
        super().__init__('(.*?)', function)
