# -*- coding: utf-8 -*-
'''Basic tools for Ovid's metamorphoses: arbitrary substring substitutions.

This module is not suitable for anything Python's re module can do alone.
It's built for frameworks where nested shorthand expressions can produce
further shorthand expressions that require functions to resolve.

TODO: Allow escaping of the various delimiters and separators defined
herein. Matthew Barnett's regex module would/will make this easier.

Written for Python 3.4. Backwards compatibility is limited by re.fullmatch.

'''


import re
import logging
import functools


class Cacher(type):
    '''Metaclass for caching classes.'''

    def __new__(cls, *args, **kwargs):
        new = super().__new__(cls, *args, **kwargs)
        new._cache = dict()
        return new

    @classmethod
    def cache_results(cls):
        '''Generic memoization decorator. Ignores keyword arguments.

        Results are cached in the class of the decorated method.

        '''
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
    '''A tool that replaces one substring pattern with function output.

    This class wraps some "re" module functions in homonymous methods.

    '''

    def __init__(self, pattern, function):
        self.re = self._generate_re(pattern)
        self.function = function

        # For preprocessing, find out which groups in the regex are unnamed.
        named = set(self.re.groupindex.values())
        unnamed = (i for i in range(1, self.re.groups + 1) if i not in named)
        self._unnamed_group_indices = tuple(unnamed)

    @classmethod
    def _generate_re(cls, subpattern):
        '''Trivial here. Overridden elsewhere in this module.'''
        return re.compile(subpattern, re.UNICODE)

    @classmethod
    def variant_class(cls, name='Custom', **kwargs):
        '''Generate a fresh subclass.

        This is useful for subclassing subclasses of this class.
        In particular, it's intended for customizing lead-in strings,
        separator strings etc., and to easily make subclasses with
        their own registries, none of which exist on OneWayProcessor.

        '''
        return type(name, (cls,), kwargs)

    def sub(self, string, **kwargs):
        return re.sub(self.re, self._process, string, **kwargs)

    def subn(self, string, **kwargs):
        return re.subn(self.re, self._process, string, **kwargs)

    def _process(self, matchobject):
        unnamed, named = self._unique_groups(matchobject)
        return self.function(*unnamed, **named)

    def _unique_groups(self, matchobject):
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

    def __repr__(self):
        s = '<Ovid processor for {}>'
        return s.format(self.function.__name__)


class TwoWayProcessor(OneWayProcessor):
    '''A processor that can produce targets appropriate for itself.

    This can be used to generate specifications programmatically, for
    later treatment by the same processor in two different stages of a
    program.

    Not very competent.

    '''

    class ProductionError(ValueError):
        pass

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._prepare_production()

    def _prepare_production(self):
        '''Prepare a number of strings needed for produce().'''

        self._production_template = None
        self._production_groups_unnamed = list()
        self._production_groups_named = dict()
        self._evert_groups()

        s = ('Created {} with consumption regex "{}", production regex "{}" '
             'for groups "{}", "{}".')
        logging.debug(s.format(self.__class__.__name__, self.re.pattern,
                               self._production_template,
                               self._production_groups_unnamed,
                               self._production_groups_named))

    def _evert_groups(self):
        '''Prepare to use content-catching regexes to produce content.

        This method sets the self._production_* variables declared
        in self._prepare_production(), for use in self.produce().

        NOTE: Nested catching groups are not supported here.

        '''

        def compile_re(string):
            try:
                return re.compile(string)
            except:
                s = 'Invalid proposed regex group "{}".'
                logging.error(s.format(string))
                s = 'Could not evert {}.'
                logging.error(s.format(self.re.pattern))
                raise

        def unnamed_group_collector(match):
            content = match.group(1)
            self._production_groups_unnamed.append(compile_re(content))
            return '{}'

        def named_group_collector(match):
            name, content = match.groups()
            self._production_groups_named[name] = compile_re(content)
            return '{{{}}}'.format(name)

        def collect(metapattern, collector):
            args = (metapattern, collector, self._production_template, 1)
            self._production_template, n = re.subn(*args)
            if n:
                collect(metapattern, collector)

        # Pave the way for the str.format() call in self.produce().
        self._production_template = self._double_braces(self.re.pattern)

        # Patterns to capture patterns, with fixed-width font commentary.
        metapattern = r'(?!\\)\((?!\?)(.*?[^\\])\)'
        # unescaped parens  ^  ^             ^   ^  as delimiters again
        # not a special group       ^
        # otherwise any non-empty string ^
        # NOTE: Nested groups are not supported.
        collect(metapattern, unnamed_group_collector)

        metapattern = (r'(?!\\)\('
                       #     ^  ^ leading unescaped parenthesis
                       r'\?P<(?P<name>\w+)>(?P<content>.*?[^\\])'
                       # named groups characterising a named group,
                       # whose content cannot end with a backslash
                       r'\)')
                       # ^ closing parenthesis, unescaped by ^
        collect(metapattern, named_group_collector)

    @classmethod
    def _double_braces(cls, string):
        '''Add string formatting escapes.'''
        return re.sub('{', '{{', re.sub('}', '}}', string))

    def produce(self, *unnamed, **named):
        '''Present an appropriate target string.'''
        try:
            unnamed = tuple(self._fill_unnamed(map(str, unnamed)))
            named = {k: v for k, v in self._fill_named(named)}
        except:
            logging.error('Cannot reverse {}.'.format(repr(self)))
            raise

        return self._production_template.format(*unnamed, **named)

    def _fill_unnamed(self, contents):
        '''Use zip to get the shorter sequence.'''
        for i, stuff in enumerate(zip(contents,
                                      self._production_groups_unnamed)):
            content, regex = stuff
            self._must_match(i, regex, content)
            yield content

    def _fill_named(self, named):
        for name, content in named.items():
            regex = self._production_groups_named[name]
            self._must_match(name, regex, content)
            yield name, content

    def _must_match(self, group, regex, content):
        if not re.fullmatch(regex, str(content)):
            s = "Group {}'s proposed content '{}' does not match '{}'."
            raise self.ProductionError(s.format(group, content, regex))


class CollectiveProcessor(TwoWayProcessor):
    '''Adds the ability to run multiple processors recursively.

    The intended use case for this subclass is to do consistent project-
    wide text manipulation with multiple expressions, which may produce
    one another.

    '''
    registry = list()

    @classmethod
    def variant_class(cls, new_registry=True, **kwargs):
        '''Give the variant its own registry.'''
        if new_registry:
            kwargs['registry'] = list()
        return super().variant_class(**kwargs)

    @classmethod
    def collective_sub(cls, string, **kwargs):
        '''Apply all registered processors until none are applicable.

        This is a risky way to do the job, dependent on the order in
        which the various processors are registered. A depth-first
        version is available in the DelimitedShorthand subclass.

        '''
        for individual_processor in cls.registry:
            string, n = individual_processor.subn(string, **kwargs)
            if n:
                return cls.collective_sub(string, **kwargs)
        return string


class AutoRegisteringProcessor(CollectiveProcessor):
    '''Adds automatic registration of processors on creation.'''

    def __init__(self, pattern, function):
        super().__init__(pattern, function)
        self.registry.append(self)


class DelimitedShorthand(AutoRegisteringProcessor, metaclass=Cacher):
    '''A bundle of conveniences.

    The choice of appropriate delimiters for subclasses is currently
    limited by regex conventions. Parentheses, for example, are not
    automatically escaped to generate regexes for searching for literal
    parentheses. For parentheses to be useful, they should be escaped
    when supplied as arguments to variant_class().

    The choice of appropriate delimiters is also limited by the intended
    level of nesting. Using the same string as lead-in and lead-out will
    complicate nesting.

    '''

    lead_in = '{{'
    lead_out = '}}'

    escape = re.escape('\\')

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
    @Cacher.cache_results()
    def _targetfinder(cls):
        '''Generate a regex pattern useful for working with nesting.

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

        '''
        s = (r'{active_in}'
             r'((?:{inactive_in}|{inactive_out}|(?!{active_in}).)*?)'
             r'{active_out}')
        p = s.format(active_in=cls._unescape(cls.lead_in),
                     inactive_in=cls._escape(cls.lead_in),
                     active_out=cls._unescape(cls.lead_out),
                     inactive_out=cls._escape(cls.lead_out))
        return re.compile(p)

    @classmethod
    @Cacher.cache_results()
    def _escape(cls, delimiter):
        '''Produce a regex pattern for a token in its escaped form.'''
        if cls.escape and delimiter:
            return ''.join((cls.escape + d for d in delimiter))
        return delimiter

    @classmethod
    @Cacher.cache_results()
    def _unescape(cls, delimiter):
        '''Produce a regex pattern for a token in its unescaped form.'''
        if cls.escape and len(delimiter) == 1:
            return r'(?<!{}){}'.format(re.escape(cls.escape), delimiter)
        return delimiter

    @classmethod
    def collective_sub(cls, raw_string, safe=True, **kwargs):
        '''With optional precautions against sloppy markup.'''
        cooked_string = cls._collective_sub_unsafe(raw_string, **kwargs)

        if safe:
            delimiters = (cls.lead_in, cls.lead_out)
            for delimiter in delimiters:
                if re.search(cls._unescape(delimiter), cooked_string):
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

                s = 'Giving up after applying the following regexes:'
                logging.warning(s)
                for i in cls.registry:
                    logging.warning(i.re.pattern)

                s = "Unable to substitute for '{}'."
                raise cls.UnknownShorthandError(s.format(repl))

            # Incorporate the modification.
            string = string[:target.start()] + repl + string[target.end():]

            # Recurse to get the rest.
            return cls._collective_sub_unsafe(string, **kwargs)

        # Nothing else looks like valid markup.
        return string
