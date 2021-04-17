# -*- coding: utf-8 -*-
"""Add-ons to produce targets of subsequent metamorphosis.

This can be used to generate specifications programmatically, for
later treatment by the same processor in two different stages of a
program.

Written for Python 3.4. Backwards compatibility is limited by re.fullmatch.

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

from . import basic
from . import inspecting


class TwoWayProcessor(basic.OneWayProcessor):
    """The most basic two-way processor. Not very competent.

    You can subclass anything in ovid.basic with this and get its
    functionality, but it is a little limited. Nested catching groups,
    for example, are not supported. That is why the other modules in
    Ovid don't automatically integrate production capabilities.

    """

    class ProductionError(ValueError):
        """Raised to signal that requested output would be illegal."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._prepare_production()

    def _prepare_production(self):
        """Prepare a number of strings needed for produce()."""
        self._production_template = None
        self._production_groups_unnamed = list()
        self._production_groups_named = dict()
        self._evert_groups()

        s = ('Created {} with consumption regex "{}", production regex "{}" '
             'for groups "{}", "{}".')
        self.log.debug(s.format(self.__class__.__name__, self.re.pattern,
                                self._production_template,
                                self._production_groups_unnamed,
                                self._production_groups_named))

    def _evert_groups(self):
        """Prepare to use content-catching regexes to produce content.

        This method populates the self._production_* variables declared
        in self._prepare_production(), for use in self.produce().

        """
        def compile_re(string):
            try:
                return re.compile(string)
            except Exception:
                s = 'Invalid proposed regex group "{}".'
                self.log.error(s.format(string))
                s = 'Could not evert {}.'
                self.log.error(s.format(self.re.pattern))
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
        #                ^ closing parenthesis, unescaped by ^
        collect(metapattern, named_group_collector)

    def produce(self, *unnamed, **named):
        """Present an appropriate target string."""
        try:
            unnamed = tuple(self._fill_unnamed(map(str, unnamed)))
            named = {k: v for k, v in self._fill_named(named)}
        except Exception:
            self.log.error(f'Cannot reverse {self!r}.')
            raise

        return self._production_template.format(*unnamed, **named)

    def _fill_unnamed(self, contents):
        """Use zip to get the shorter sequence."""
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


class TwoWaySignatureShorthand(inspecting.SignatureShorthand, TwoWayProcessor):
    """Special treatment for SignatureShorthand."""

    def _evert_groups(self):
        """Override TwoWayProcessor.

        This override exists because initialization creates nested groups,
        which are not expected by the standard method. Here we can
        avoid dealing with them, using assumptions made simple by the
        predictability of the superclass.

        """
        for i in self._unnamed_group_indices:
            self._production_groups_unnamed.append(self._unnamed_pattern)

        for name, i in sorted(self.re.groupindex.items(), key=lambda x: x[1]):
            self._production_groups_named[name] = self._named_pattern

        placeholders = ('{}' for _ in self._production_groups_unnamed)
        unnamed = self._separate(*placeholders)
        elements = (self._double_braces(self.lead_in),
                    self._separate(self.function.__name__, unnamed,
                                   ignore_empty=True),
                    '{named}',
                    self._double_braces(self.lead_out)
                    )

        self._production_template = ''.join(elements)

    def produce(self, *unnamed, **named):
        """Override parent class to respect absent named groups."""
        named = sorted(named.items())
        for name, content in named:
            regex = self._production_groups_named[name]
            self._must_match(name, regex, content)
        named = (self.assignment_operator.join(map(str, n)) for n in named)
        named = self._separate(*tuple(named))
        if named:
            # Prepend a separator to isolate from preceding text.
            named = self._separate('', named)

        return super().produce(*unnamed, named=named)

    def _fill_named(self, named):
        """Another override of TwoWayProcessor.

        Simplified to reflect the earlier treatment of named groups
        in produce().

        """
        return named.items()

    @classmethod
    def _separate(cls, *args, ignore_empty=False):
        """Separate arguments with an unescaped class-specific separator.

        Escape curvilinear braces in the separator, for use with a round
        of str.format(), e.g. in the superclass's produce() method.

        """
        if ignore_empty:
            args = filter(bool, args)
        return cls._double_braces(cls.separator).join(args)
