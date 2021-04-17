## Ovid: tools for text metamorphosis

This Python package is a templating engine. It will remind you of other such
engines available for Python, such as the standard library’s string.Template,
Jinja, and the Django template system.

Ovid works by pairing up regular expressions with functions. Both are
needed to create an Ovid processor. You apply the processor to a string,
and if the regular expression matches, the function receives the content
of the matching groups from that expression. The function’s output replaces
the match.

### Examples

Here is a trivial example:

```python
from ovid.basic import OneWayProcessor

def f(group):
    return 3 * group

OneWayProcessor('(b)', f).sub('abc')  # Returns 'abbbc'
```

As you can see, the regex matches `b` and identifies it as a group, which
Ovid passes to the function we have defined. The function does not
receive the match object.

A slightly more meaningful example follows, using a different Ovid class,
through a decorator.

```python
import random
from ovid.inspecting import SignatureShorthand as SS

_BARK_STATES = ('mostly stripped', 'brown', 'gray')

@SS.register
def melee(to_hit, damage, defense=''):
    repl = f'{to_hit or "±0"} to hit with {damage or "±0"} damage.'
    if defense:
        repl += f' {defense} to be hit in melee.'
    return repl

@SS.register
def wood():
    return f'The bark is {random.choice(_BARK_STATES)}.'

sample = 'A stick. {{wood}} {{melee||+1|defense=-1}}'
SS.collective_sub(sample)  # Return value:
# 'A stick. The bark is gray. ±0 to hit with +1 damage. -1 to be hit in melee.'
```

Here, the decorator adds our two functions to a registry, and the Ovid class
constructs our regular expressions for us, with delimiters and separators that
can be customized through subclassing. We apply both processors collectively,
through a class method. Collective application supports recursion, nesting, and
the passing of additional contextual information to processors.

Finally, Ovid processors can evert, outputting suitable input.

```python
from ovid.producing import TwoWaySignatureShorthand

def hyperlink(href, text=None):
   return f'<a href="{href}">{text or href}</a>'

processor = TwoWaySignatureShorthand(hyperlink)

processor.produce('https://www.fsf.org/', text='FSF')
# Return value: '{{hyperlink|https://www.fsf.org/|text=FSF}}'

processor.sub('{{hyperlink|https://www.python.org/psf/|text=PSF}}')
# Return value: '<a href="https://www.python.org/psf/">PSF</a>'
```

In this example, an object built from one function can produce a template,
and parse such a template as in the first example.

### Use cases

Ovid grew out of [CBG](https://github.com/veikman/cbg). There, Ovid enables
shorthand expressions in the manual text input that CBG uses to make
playing cards. Because Ovid processors can evert, Ovid also combines with CBG
to generate elegant raw text specifications for larger games.

A more complicated real-world use case is the maintenance of the author’s
website. Here, Ovid refines specifications as a pre-processor to Markdown.
This makes it easy to write a blog article that references a movie review that
hasn’t been written yet. When the review is eventually added to the database,
an Ovid processor finds it and adds a hyperlink to the article’s published
form.

In the same process, the Django model instance that owns each raw string is
passed through the Ovid layer to the encapsulated functions as contextual
information, which enables these functions to map internal references in
addition to replacing substrings.

### Legal

Copyright 2015–2021 Viktor Eikman

Ovid is licensed as detailed in the accompanying file LICENSE.
