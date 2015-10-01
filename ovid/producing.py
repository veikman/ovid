# -*- coding: utf-8 -*-
'''Processors that can produce targets appropriate for themselves.

Written for Python 3.4. Backwards compatibility is limited by re.fullmatch.

'''

import logging
import re

import ovid.basic


class TwoWayProcessor(ovid.basic.OneWayProcessor):
    '''The most basic two-way processor. Not very competent.

    This can be used to generate specifications programmatically, for
    later treatment by the same processor in two different stages of a
    program.

    You can subclass anything in ovid.basic with this and get its
    functionality, but it is a little limited.

    '''

    class ProductionError(ValueError):
        '''Raised to signal that requested output would be illegal.'''
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


class TwoWaySignatureShorthand(ovid.inspecting.SignatureShorthand,
                               TwoWayProcessor):

    def _evert_groups(self):
        '''An override of TwoWayProcessor.

        This override exists because initialization creates nested groups,
        which are not expected by the standard method. Here we can
        avoid dealing with them, using simple assumptions.

        '''
        for i in self._unnamed_group_indices:
            self._production_groups_unnamed.append(self._unnamed_pattern)

        for name, i in sorted(self.re.groupindex.items(), key=lambda x: x[1]):
            self._production_groups_named[name] = self._named_pattern

        def sep(*args, ignore_empty=False):
            if ignore_empty:
                args = filter(lambda x: x, args)
            return self._double_braces(self.separator).join(args)

        elements = (self._double_braces(self.lead_in),
                    sep(self.function.__name__,
                        sep(*('{}' for _ in self._production_groups_unnamed)),
                        sep(*('{{{}}}'.format(name) for name in
                              self._production_groups_named)),
                        ignore_empty=True),
                    self._double_braces(self.lead_out)
                    )

        self._production_template = ''.join(elements)

    def produce(self, *unnamed, **named):
        '''Supply empty strings to absent named groups.'''
        for name in self._production_groups_named:
            if name not in named:
                named[name] = ''
        return super().produce(*unnamed, **named)

    def _fill_named(self, named):
        '''Another override of TwoWayProcessor.

        Here the objective is simply to prepend the assignment part to
        a named argument's content.

        '''
        for name, content in named.items():
            regex = self._production_groups_named[name]
            content = self.assignment_operator.join((name, str(content)))
            self._must_match(name, regex, content)
            yield name, content
