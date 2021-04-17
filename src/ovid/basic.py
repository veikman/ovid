# -*- coding: utf-8 -*-
"""Basic tools for metamorphoses: arbitrary substring substitutions.

This module is not suitable for anything Python's re module can do alone.
It's built for frameworks where nested shorthand expressions can produce
further shorthand expressions that require functions to resolve.

TODO: Allow escaping of the various delimiters and separators defined
herein. Matthew Barnett's regex module would/will make this easier.

------

This file is part of Ovid.

Ovid is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

Ovid is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with Ovid.  If not, see <http://www.gnu.org/licenses/>.

"""

import re
import logging
import functools


class Cacher(type):
    """Metaclass for caching classes."""

    def __new__(cls, *args, **kwargs):
        """Compose a memoization cache onto each new class."""
        new = super().__new__(cls, *args, **kwargs)
        new._cache = dict()
        return new

    @classmethod
    def cache_results(cls):
        """Prepare to memoize.

        A generic memoization decorator that ignores keyword arguments.

        Results are cached in the class of the decorated method.

        """
        def decorator(obj):

            @functools.wraps(obj)
            def memoizer(*args):
                cache = args[0]._cache
                key = (obj.__name__,) + args
                if key not in cache:
                    # print('New:', obj.__name__, 'with', args)  # Debug.
                    cache[key] = obj(*args)
                return cache[key]

            return memoizer

        return decorator


class OneWayProcessor(metaclass=Cacher):
    """A tool that replaces one substring pattern with function output.

    This class wraps some "re" module functions in homonymous methods.

    """

    log = logging.getLogger('ovid')

    def __init__(self, pattern, function, **kwargs):
        self.re = self._generate_re(pattern, **kwargs)
        self.function = function

        # For preprocessing, find out which groups in the regex are unnamed.
        named = set(self.re.groupindex.values())
        unnamed = (i for i in range(1, self.re.groups + 1) if i not in named)
        self._unnamed_group_indices = tuple(unnamed)

    @classmethod
    def _generate_re(cls, subpattern, **kwargs):
        """Trivial here. Overridden elsewhere in this module."""
        return re.compile(subpattern, **kwargs)

    @classmethod
    def variant_class(cls, name='Custom', **kwargs):
        """Generate a fresh subclass.

        This is useful for subclassing subclasses of OneWayProcessor.
        In particular, it's intended for customizing lead-in strings,
        separator strings etc., and to easily make subclasses with
        their own registries, none of which exist on OneWayProcessor.

        """
        return type(name, (cls,), kwargs)

    def sub(self, string, **kwargs):
        """Apply as with re.sub."""
        return self._process(self.re.sub, string, **kwargs)

    def subn(self, string, **kwargs):
        """Apply as with re.subn."""
        return self._process(self.re.subn, string, **kwargs)

    def _process(self, parser, string, **kwargs):
        """Apply self.re.sub or self.re.subn as parsers.

        Pass keywords arguments not supported by those parsers to
        self.function.

        """
        def repl(matchobject):
            unnamed, named = self._unique_groups(matchobject)
            kwargs.update(named)
            return self.function(*unnamed, **kwargs)

        return parser(repl, string, count=kwargs.pop('count', 0))

    def _unique_groups(self, matchobject):
        """Break down match objects for the processor function.

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

        """
        # With 0-1 arguments group() returns a string, else a tuple.
        if self._unnamed_group_indices:
            unnamed = matchobject.group(*self._unnamed_group_indices)
            if len(self._unnamed_group_indices) == 1:
                unnamed = (unnamed,)
        else:
            unnamed = ()

        # To make default values in the user's function meaningful,
        # eliminate non-matching optional named groups.
        named = {k: v for k, v in matchobject.groupdict().items()
                 if v is not None}

        return (unnamed, named)

    @classmethod
    def _double_braces(cls, string):
        """Add Python string formatting escapes.

        This method is not used in this class itself, but is used by
        both producing and inspecting inheritors.

        """
        return re.sub('{', '{{', re.sub('}', '}}', string))

    def __repr__(self):
        """Provide a default string representation for debuggers."""
        return f'<Ovid processor for {self.function.__name__}>'


class CollectiveProcessor(OneWayProcessor):
    """Adds the ability to run multiple processors recursively.

    The intended use case for this subclass is to do consistent project-
    wide text manipulation with multiple expressions, which may produce
    one another.

    """

    registry = list()

    @classmethod
    def variant_class(cls, new_registry=True, **kwargs):
        """Give the variant its own registry."""
        if new_registry:
            kwargs['registry'] = list()
        return super().variant_class(**kwargs)

    @classmethod
    def collective_sub(cls, string, **kwargs):
        """Apply all registered processors until none are applicable.

        This is a risky way to do the job, dependent on the order in
        which the various processors are registered. A depth-first
        version is available in the DelimitedShorthand subclass.

        """
        for individual_processor in cls.registry:
            s, n = individual_processor.subn(string, **kwargs)
            if n and s != string:
                # A hit happened and the string actually changed. Recurse.
                # Checking the content prevents infinite recursion where
                # some output is valid input.
                string = s
                return cls.collective_sub(string, **kwargs)
        return string


class AutoRegisteringProcessor(CollectiveProcessor):
    """Adds automatic registration of processors on creation."""

    def __init__(self, pattern, function, **kwargs):
        super().__init__(pattern, function, **kwargs)
        self.registry.append(self)


class DelimitedShorthand(AutoRegisteringProcessor, metaclass=Cacher):
    """A bundle of conveniences.

    The choice of appropriate delimiters for subclasses is currently
    limited by regex conventions. Parentheses, for example, are not
    automatically escaped to generate regexes for searching for literal
    parentheses. For parentheses to be useful, they should be escaped
    or used in raw literals when supplied as arguments to variant_class().

    The choice of appropriate delimiters is also limited by the intended
    level of nesting. Using the same string as lead-in and lead-out will
    complicate nesting.

    """

    lead_in = '{{'
    lead_out = '}}'

    # The ‘flags’ property is used by the class to generate its generic
    # targeting regex and is therefore also the default for instances.
    flags = 0

    escape = re.escape('\\')

    class OpenShorthandError(ValueError):
        """Raised when what appears to be markup is not properly delimited."""

    class UnknownShorthandError(ValueError):
        """Raised when otherwise valid markup has no registered processor."""

    @classmethod
    def _generate_re(cls, subpattern, flags=None):
        """Override parent class.

        We rely on a targetfinder regex to keep this method, and user input,
        relatively simple.

        """
        flags = cls.flags if flags is None else flags
        return re.compile(''.join((cls.lead_in, subpattern, cls.lead_out)),
                          flags=flags)

    @classmethod
    @Cacher.cache_results()
    def _targetfinder(cls):
        """Compile a regex pattern useful for working with nesting.

        This pattern has to find the smallest group of characters
        inside a pair of active (i.e. not escaped) delimiters. To
        guarantee that the group is minimal, it cannot contain a
        non-escaped lead-in. This is what causes nested groups to be
        resolved from the inside out in collective substitutions.

        The group is allowed to be empty, to catch broken markup where
        a user forgot to add content.

        The group is allowed to contain escaped delimiters, skipping
        over such sequences in their entirety to avoid misinterpreting
        single-character delimiters after passing their escape
        characters.

        """
        s = (r'{active_in}'
             r'((?:{inactive_in}|{inactive_out}|(?!{active_in}).)*?)'
             r'{active_out}')
        p = s.format(active_in=cls._unescape(cls.lead_in),
                     inactive_in=cls._escape(cls.lead_in),
                     active_out=cls._unescape(cls.lead_out),
                     inactive_out=cls._escape(cls.lead_out))
        return re.compile(p, flags=cls.flags)

    @classmethod
    @Cacher.cache_results()
    def _active_delimiters(cls):
        """Compile regex patterns useful for tracing errors."""
        return tuple(map(lambda d: re.compile(cls._unescape(d),
                                              flags=cls.flags),
                         (cls.lead_in, cls.lead_out)))

    @classmethod
    @Cacher.cache_results()
    def _escape(cls, delimiter):
        """Produce a regex pattern for a token in its escaped form."""
        if cls.escape and delimiter:
            return ''.join((cls.escape + d for d in delimiter))
        return delimiter

    @classmethod
    @Cacher.cache_results()
    def _unescape(cls, delimiter):
        """Produce a regex pattern for a token in its unescaped form."""
        if cls.escape and len(delimiter) == 1:
            return r'(?<!{}){}'.format(re.escape(cls.escape), delimiter)
        return delimiter

    @classmethod
    def collective_sub(cls, raw_string, safe=True, **kwargs):
        """With optional precautions against sloppy markup.

        Globbed keyword arguments are passed on to _collective_sub_unsafe()
        but are not actually used in this base class.

        """
        cooked_string = cls._collective_sub_unsafe(raw_string, **kwargs)

        if safe:
            delimiters = cls._active_delimiters()
            for delimiter in delimiters:
                if delimiter.search(cooked_string):
                    b = 'Open (unbalanced) shorthand expression'

                    s = '{} resulting from "{}".'
                    cls.log.error(s.format(b, raw_string))

                    s = '{} in "{}".'
                    cls.log.error(s.format(b, cooked_string))

                    s = '{}: Found {} without a corresponding {}.'
                    opposite = delimiters[1 - delimiters.index(delimiter)]
                    s = s.format(b, delimiter.pattern, opposite.pattern)
                    raise cls.OpenShorthandError(s)

        return cooked_string

    @classmethod
    def _collective_sub_unsafe(cls, string, **kwargs):
        """Depth-first search, using delimiters to control resolution order."""
        target = cls._targetfinder().search(string)
        if target:
            repl = super().collective_sub(target.group(), **kwargs)
            if repl == target.group():
                # No effect. Likely user error.
                # However, this may also be caused by processors having
                # output identical to their own input.

                s = 'Giving up after applying the following regexes:'
                cls.log.warning(s)
                for i in cls.registry:
                    cls.log.warning(i.re.pattern)

                s = "Unable to substitute for '{}'."
                raise cls.UnknownShorthandError(s.format(repl))

            # Incorporate the modification.
            string = string[:target.start()] + repl + string[target.end():]

            # Recurse to get the rest.
            return cls._collective_sub_unsafe(string, **kwargs)

        # Nothing else looks like valid markup.
        return string
