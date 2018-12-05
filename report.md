---
title: The Title of My Report
author: "Author One, Author Two, Author Three"
date: Berkeley Institute for Data Science (BIDS) \newline \vspace{-.15cm}  University of California, Berkeley  \newline October 2018
draft: true
bibliography: bibliography.bib
#fontfamily: utopia
# See also http://pandoc.org/MANUAL.html#templates (search for fontfamily)
# utopia, bookman, mathpazo (Palatino), arev (Arev Sans), fouriernc, times, libertine, lmodern
documentclass: tufte-handout
fontfamily: mathpazo
mainfont: Palatino
monofont: Menlo
fontsize: 10pt
newtxmathoptions:
- cmintegrals
- cmbraces
linkcolor: RoyalBlue
urlcolor: RoyalBlue
toccolor: RoyalBlue
abstract: |
    Any LaTeX can go here; this is the summary of the document.

---

# Some section

The content of some section.  And you can use raw LaTeX too if you
need.  You can add **margin notes**.\marginnote{This is a margin note.}

You can also make footnotes, that appear in the margin[^my_footnote].

Sometimes there's something to fix, so [add a fixme note for
that]{.fixme}.  Otherwise, a [comment might do]{.comment}.

From your bibliography, you can cite papers [@scikit-image].  You can
change the citation style
by [downloading another style](https://www.zotero.org/styles?q=ieee)
and then modifying the Makefile to use that style file.

[^my_footnote]: And this is the text of my footnote.  It can have
[links to important pages](https://github.com/bids/fellows/wiki).

## And then a subsection {#with-an-anchor-if-you-need-to-refer-to-it}

In the [subsection](#with-an-anchor-if-you-need-to-refer-to-it) it is
written that...

Pandoc Markdown supports various forms of tables.  Like this one:

| Table | Header |
|-------|--------|
| 4.00  |  5.00  |

You should also take a look at the manual
for [Tufte LaTeX](https://ctan.org/pkg/tufte-latex?lang=en), because
you can use raw LaTeX with any of the instructions described within.

Finally, you can also switch the document format to any class of your
choice, but you will also have to modify the `Makefile` to remove the
Tufte style there.

# A beautiful diagram

Here is a beautiful diagram.

![](build/diagram.png){ width=30% }

Which can also be rendered as a captioned figure:

![My Beautiful Diagram](build/diagram.png){ width=30% }

# Some source code

```python
def foo(bar):
    return bar + 1
```

# Bibliography

