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

A slighly more meaningful example follows, using a different Ovid class,
through a decorator.

    >>> @ovid.inspecting.SignatureShorthand.register
    >>> def melee(to_hit, damage, defense=''):
    ...     repl = 'Melee weapon: {} to hit with {} damage.'
    ...     repl = repl.format(to_hit or '±0', damage or '±0')
    ...     if defense:
    ...         repl += ' {} to be hit in melee.'.format(defense)
    ...     return repl
    ... 
    >>> @ovid.inspecting.SignatureShorthand.register
    >>> def wood():
    ...     bark_states = ('mostly stripped', 'brown', 'gray')
    ...     repl = 'The bark is {}.'.format(random.choice(bark_states))
    ...     return repl
    ... 
    >>> sample = 'A stick. {{wood}} {{melee||+1|defense=-1}}'
    >>> ovid.inspecting.SignatureShorthand.collective_sub(sample)
    'A stick. The bark is gray. Melee weapon: ±0 to hit with +1 damage. -1 to be hit in melee.'

Here, the decorator automatically adds our two functions to a registry,
and the Ovid class constructs our regular expressions for us, with
delimiters and separators that can be customized through subclassing.
We apply both processors collectively, through a class method. Collective
application supports recursion and nesting.

### Use cases

Ovid grew out of [CBG](https://github.com/veikman/cbg). Ovid combines
with CBG to support shorthand expressions in, for example, YAML. The
expressions expand to repetitive rule text and symbols on playing cards.

Because advanced Ovid processors can "evert" and produce the expressions
they themselves would consume, Ovid also combines with CBG to generate
elegant raw text specifications for larger games.

A more complicated real-world use case is the maintenance of the author's
website. Here, Ovid refines specifications as a pre-processor to Markdown.
This makes it easy to write a blog article that references a movie review
that hasn't been written yet. When the review is eventually added to the
database, an Ovid processor finds it and adds a working hyperlink to the
article, in its published form.

### Legal

Ovid is licensed as detailed in the accompanying file COPYING.txt.

