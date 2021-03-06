## Ovid: tools for text metamorphosis

This Python package is a templating engine. It will remind you of other such
engines available for Python, such as the standard library's string.Template,
and the Django template system.

Ovid works by pairing up regular expressions with functions. Both are
needed to create an Ovid processor. You apply the processor to a string,
and if the regular expression matches, the function receives the content
of the matching groups from that expression. The function's output replaces
the match.

### Examples

Here is a trivial example from an interactive Python interpreter:

    >>> def f(group):
    ...     return 3 * group
    ...
    >>> ovid.basic.OneWayProcessor('(b)', f).sub('abc')
    'abbbc'

As you can see, the regex matches "b" and identifies it as a group, which
Ovid passes to the function we have defined. The function does not
receive the match object, just the contents. The only point to using Ovid
for something this basic is that our function can be relatively simple,
compared to functions that need to treat complete match objects.

A slightly more meaningful example follows, using a different Ovid class,
through a decorator.

    >>> _BARK_STATES = ('mostly stripped', 'brown', 'gray')
    >>>
    >>> @ovid.inspecting.SignatureShorthand.register
    >>> def melee(to_hit, damage, defense=''):
    ...     repl = f'{to_hit or "±0"} to hit with {damage or "±0"} damage.'
    ...     if defense:
    ...         repl += f' {defense} to be hit in melee.'
    ...     return repl
    ...
    >>> @ovid.inspecting.SignatureShorthand.register
    >>> def wood():
    ...     return f'The bark is {random.choice(_BARK_STATES)}.'
    ...
    >>> sample = 'A stick. {{wood}} {{melee||+1|defense=-1}}'
    >>> ovid.inspecting.SignatureShorthand.collective_sub(sample)
    'A stick. The bark is gray. ±0 to hit with +1 damage. -1 to be hit in melee.'

Here, the decorator automatically adds our two functions to a registry,
and the Ovid class constructs our regular expressions for us, with
delimiters and separators that can be customized through subclassing.
We apply both processors collectively, through a class method. Collective
application supports recursion, nesting, and the passing of additional
contextual information to processors.

### Use cases

Ovid grew out of [CBG](https://github.com/veikman/cbg). There, Ovid enables
shorthand expressions in the manual text input that CBG uses to make
playing cards. Because advanced Ovid processors can "evert" and produce
the expressions they themselves would consume, Ovid also combines with CBG
to generate elegant raw text specifications for larger games.

A more complicated real-world use case is the maintenance of the author's
website. Here, Ovid refines specifications as a pre-processor to Markdown.
This makes it easy to write a blog article that references a movie review
that hasn't been written yet. When the review is eventually added to the
database, an Ovid processor finds it and adds a working hyperlink to the
article's published form.

In the same process, the Django model instance that owns each raw string
is passed through the Ovid layer to the encapsulated functions as
contextual information, which enables these functions to map internal
references in addition to replacing substrings.

### Legal

Copyright 2015–2020 Viktor Eikman

Ovid is licensed as detailed in the accompanying file COPYING.txt.
