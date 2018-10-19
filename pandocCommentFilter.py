#!/usr/bin/env python

"""
From https://github.com/bwhelm/Pandoc-Comment-Filter
"""

"""
Pandoc filter to extend pandoc's markdown to incorporate comment features and
other things I find useful. With `draft: true` in the YAML header, comments and
margin notes are displayed in red, and text that is highlighted or flagged with
`fixme` is marked up in the output. With `draft: false` in the YAML header,
comments and margin notes are not displayed at all, and highlightings and
`fixme` mark ups are suppressed (though the text is displayed). Also provided
are markup conventions for cross-references, index entries, and TikZ figures.

Copyright (C) 2017 Bennett Helm

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.
    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.
    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.


# Syntax Extensions

## Block-Level Items:

`<!comment>`:  begin comment block
`</!comment>`: end comment block
`<center>`:    begin centering
`</center>`:   end centering
`<!box>`:      begin frame box
`</!box>`:     end frame box
`<!speaker>`:  begin speaker notes (for revealjs)
`</!speaker>`: end speaker notes


## Inline Items: Two Styles

1. Tag-style:
    - `<comment>`:    begin commenting
    - `</comment>`:   end commenting
    - `<highlight>`:  begin highlighting (note that this requires that
                      `soul.sty` be loaded in LaTeX)
    - `</highlight>`: end highlighting
    - `<fixme>`:      begin FixMe margin note (and highlighting)
    - `</fixme>`:     end FixMe margin note (and highlighting)
    - `<margin>`:     begin margin note
    - `</margin>`:    end margin note
    - `<smcaps>`:     begin small caps style
    - `</smcaps>`:    end small caps style

2. Span-style:

    - `[...]{.comment}`:    make `...` be a comment
    - `[...]{.highlight}`:  make `...` be highlighted (note that this requires
                            that `soul.sty` be loaded in LaTeX)
    - `[...]{.fixme}`:      make `...` be a FixMe margin note (with
                            highlighting)
    - `[...]{.margin}`:     make `...` be a margin note
    - `[...]{.smcaps}`:     make `...` be in small caps


## Other Items:

1. Tag-style (pre pandoc2):
    - `< `:                 (at begining of line) do not indent paragraph
                            (after quotation block or lists, e.g.)
    - `<l LABEL>`:          create a label
    - `<r LABEL>`:          create a reference
    - `<rp LABEL>`:         create a page reference
    - `<i text-for-index>`: create LaTeX index mark (`\\index{text-for-index}`)

2. Span-style (pandoc2 and later):
    - `< `:                   (at begining of line) do not indent paragraph
                              (after quotation block or lists, e.g.)
    - `[LABEL]{.l}`:          create a label
    - `[LABEL]{.r}`:          create a reference
    - `[LABEL]{.rp}`:         create a page reference
    - `[text-for-index]{.i}`: create LaTeX index (`\\index{text-for-index}`)


## Images: Allow for tikZ figures in code blocks. They should have the
   following format:

~~~ {#tikz caption='My *great* caption' id='fig:id'
     tikzlibrary='items,to,go,in,\\usetikzlibrary{}'}

[LaTeX code]

~~~

Note that the caption can be formatted text in markdown.

"""


from pandocfilters import json, sys, walk, elt, stringify,\
    RawInline, Para, Plain, Image, Str
from os import path, mkdir, chdir, getcwd
from shutil import copyfile, rmtree
from sys import getfilesystemencoding, stderr
from subprocess import call, Popen, PIPE
from hashlib import sha1

IMAGE_PATH = path.expanduser('~/tmp/pandoc/Figures')
DEFAULT_FONT = 'fbb'
INLINE_TAG_STACK = []
BLOCK_COMMENT = False
INLINE_COMMENT = False
INLINE_MARGIN = False
INLINE_HIGHLIGHT = False
INLINE_FONT_COLOR_STACK = ['black']
USED_BOX = False
DRAFT = False

COLORS = {
    '<!comment>': 'cyan',
    '<comment>': 'cyan',
    '<highlight>': 'yellow',
    '<margin>': 'black',
    '<fixme>': 'red'
}

# HTML style for margin notes
MARGIN_STYLE = 'max-width:20%; border: 1px solid black;' + \
               'padding: 1ex; margin: 1ex; float:right; font-size: small;'

LATEX_TEXT = {
    '<!comment>': '\\color{{{}}}{{}}'.format(COLORS['<!comment>']),
    '</!comment>': '\\color{black}{}',
    '<!box>': '\\medskip\\begin{mdframed}',
    '</!box>': '\\end{mdframed}\\medskip{}',
    '<comment>': '\\textcolor{{{}}}{{'.format(COLORS['<comment>']),
    '</comment>': '}',
    '<highlight>': '\\hl{',
    '</highlight>': '}',
    '<margin>':
    '\\marginpar{{\\begin{{flushleft}}\\scriptsize{{\\textcolor{{{}}}{{'
                 .format(COLORS['<margin>']),
    '</margin>': '}}\\end{flushleft}}',
    '<fixme>': '\\marginpar{{\\scriptsize{{\\textcolor{{{}}}'
               .format(COLORS['<fixme>']) +
               '{{Fix this!}}}}}}\\textcolor{{{}}}{{'
               .format(COLORS['<fixme>']),
    '</fixme>': '}',
    '<center>': '\\begin{center}',
    '</center>': '\\end{center}',
    # Note: treat <!speaker> just like <!comment>
    '<!speaker>': '\\textcolor{{{}}}{{'.format(COLORS['<!comment>']),
    '</!speaker>': '}',
    '<smcaps>': '\\textsc{',
    '</smcaps>': '}'
}
HTML_TEXT = {
    '<!comment>': '<div style="color: {};">'.format(COLORS['<!comment>']),
    '</!comment>': '</div>',
    '<comment>': '<span style="color: {};">'.format(COLORS['<comment>']),
    '</comment>': '</span>',
    '<highlight>': '<mark>',
    '</highlight>': '</mark>',
    '<margin>': '<span style="color: {}; {}">'
                .format(COLORS['<margin>'], MARGIN_STYLE),
    '</margin>': '</span>',
    '<fixme>': '<span style="color: {}; {}">Fix this!</span>'
                .format(COLORS['<fixme>'], MARGIN_STYLE)
               + '<span style="color: {};">'.format(COLORS['<fixme>']),
    '</fixme>': '</span>',
    '<center>': '<div style="text-align:center";>',
    '</center>': '</div>',
    '<!box>': '<div style="border:1px solid black; padding:1.5ex;">',
    '</!box>': '</div>',
    # Note: treat <!speaker> just like <!comment>
    '<!speaker>': '<div style="color: {};">'.format(COLORS['<!comment>']),
    '</!speaker>': '</div>',
    '<smcaps>': '<span style="font-variant: small-caps;">',
    '</smcaps>': '</span>'
}
REVEALJS_TEXT = {
    '<!comment>': '<div style="color: {};">'.format(COLORS['<!comment>']),
    '</!comment>': '</div>',
    '<comment>': '<span style="color: {};">'.format(COLORS['<comment>']),
    '</comment>': '</span>',
    '<highlight>': '<mark>',
    '</highlight>': '</mark>',
    '<margin>': '<span style="color: {}; {};">'
                .format(COLORS['<margin>'], MARGIN_STYLE),
    '</margin>': '</span>',
    '<fixme>': '<span style="color: {}; {}">Fix this!</span>'
                .format(COLORS['<fixme>'], MARGIN_STYLE)
               + '<span style="color: {};">'.format(COLORS['<fixme>']),
    '</fixme>': '</span>',
    '<center>': '<div style="text-align:center";>',
    '</center>': '</div>',
    '<!box>': '<div style="border:1px solid black; padding:1.5ex;">',
    '</!box>': '</div>',
    '<!speaker>': '<aside class="notes">',
    '</!speaker>': '</aside>',
    '<smcaps>': '<span style="font-variant: small-caps;">',
    '</smcaps>': '</span>'
}
DOCX_TEXT = {
    '<!comment>': '',
    '</!comment>': '',
    '<comment>': '<w:rPr><w:color w:val="FF0000"/></w:rPr><w:t>',
    '</comment>': '</w:t>',
    '<highlight>': '<w:rPr><w:highlight w:val="yellow"/></w:rPr><w:t>',
    '</highlight>': '</w:t>',
    '<margin>': '',
    '</margin>': '',
    '<fixme>': '<w:rPr><w:color w:val="0000FF"/></w:rPr><w:t>',
    '</fixme>': '</w:t>',
    '<center>': '',
    '</center>': '',
    '<!box>': '',
    '</!box>': '',
    '<!speaker>': '',
    '</!speaker>': '',
    '<smcaps>': '',
    '</smcaps>': ''
}


def debug(text):
    stderr.write("*****\n" + str(text) + "\n*****\n")


def my_sha1(x):
    return sha1(x.encode(getfilesystemencoding())).hexdigest()


def tikz2image(tikz, filetype, outfile):
    from tempfile import mkdtemp
    tmpdir = mkdtemp()
    olddir = getcwd()
    chdir(tmpdir)
    f = open('tikz.tex', 'w')
    f.write(tikz)
    f.close()
    call(['pdflatex', 'tikz.tex'], stdout=stderr)
    chdir(olddir)
    if filetype == '.pdf':
        copyfile(path.join(tmpdir, 'tikz.pdf'), outfile + filetype)
    else:
        call(['convert', '-density', '300', path.join(tmpdir, 'tikz.pdf'),
              '-quality', '100', outfile + filetype])
    rmtree(tmpdir)


def toFormat(string, fromThis, toThis):
    # Process string through pandoc to get formatted JSON string.
    p1 = Popen(['echo'] + string.split(), stdout=PIPE)
    p2 = Popen(['pandoc', '-f', fromThis, '-t', toThis], stdin=p1.stdout,
               stdout=PIPE)
    p1.stdout.close()
    return p2.communicate()[0].decode('utf-8').strip('\n')


def latex(text):
    return RawInline('latex', text)


def html(text):
    return RawInline('html', text)


def docx(text):
    return RawInline('openxml', text)


def handle_comments(key, value, docFormat, meta):
    global INLINE_TAG_STACK, BLOCK_COMMENT, INLINE_COMMENT, INLINE_MARGIN,\
        INLINE_HIGHLIGHT, INLINE_FONT_COLOR_STACK, USED_BOX, DRAFT

    # If translating to markdown, leave everything alone.
    if docFormat == 'markdown':
        return

    # Check to see if we're starting or closing a Block element
    if key == 'RawBlock' or (key == 'Para' and len(value) == 1 and
                             value[0]['t'] == 'Str'):
        if key == 'RawBlock':
            elementFormat, tag = value
            if elementFormat != 'html':
                return
            tag = tag.lower()
        else:
            tag = value[0]['c']

        if not DRAFT:
            if BLOCK_COMMENT:  # Need to suppress output
                if tag == '</!comment>':
                    BLOCK_COMMENT = False
                return []

        # Not currently suppressing output ...

        if tag in ['<!comment>', '<!box>', '<center>', '<!speaker>']:
            if tag == '<!comment>':
                BLOCK_COMMENT = True
                if not DRAFT:
                    return []
                INLINE_FONT_COLOR_STACK.append(COLORS[tag])
            elif tag == '<!box>':
                USED_BOX = True
            if docFormat in ['latex', 'beamer']:
                return Para([latex(LATEX_TEXT[tag])])
            elif docFormat in ['html', 'html5']:
                return Plain([html(HTML_TEXT[tag])])
            elif docFormat == 'revealjs':
                return Plain([html(REVEALJS_TEXT[tag])])
            else:
                return
        elif tag in ['</!comment>', '</!box>', '</center>', '</!speaker>']:
            if INLINE_TAG_STACK:
                debug('Need to close all inline elements before closing '
                      + 'block elements!\n\n{}\n\nbefore\n\n{}\n\n'
                      .format(str(INLINE_TAG_STACK), tag))
                exit(1)
            if tag == '</!comment>':
                BLOCK_COMMENT = False
                if not DRAFT:
                    return []
                INLINE_FONT_COLOR_STACK.pop()
            if docFormat in ['latex', 'beamer']:
                return Para([latex(LATEX_TEXT[tag])])
            elif docFormat in ['html', 'html5']:
                return Plain([html(HTML_TEXT[tag])])
            elif docFormat == 'revealjs':
                return Plain([html(REVEALJS_TEXT[tag])])
            else:
                return
        # else:
        #     return  # TODO Is this the right thing to do?

    if not DRAFT and BLOCK_COMMENT:
        return []  # Need to suppress output

    elif key == 'Span':
        [itemID, classes, keyValues], content = value
        if "comment" in classes:
            if DRAFT:
                if docFormat in ['latex', 'beamer']:
                    newContent = walk(content, handle_comments, docFormat,
                                      meta)
                    return [latex(LATEX_TEXT["<comment>"])] + newContent +\
                           [latex(LATEX_TEXT["</comment>"])]
                elif docFormat in ['html', 'html5']:
                    newContent = walk(content, handle_comments, docFormat,
                                      meta)
                    return [html(HTML_TEXT["<comment>"])] + newContent +\
                           [html(HTML_TEXT["</comment>"])]
                elif docFormat == 'revealjs':
                    newContent = walk(content, handle_comments, docFormat,
                                      meta)
                    return [html(REVEALJS_TEXT["<comment>"])] + newContent +\
                           [html(REVEALJS_TEXT["</comment>"])]
                elif docFormat == 'docx':
                    newContent = walk(content, handle_comments, docFormat,
                                      meta)
                    return [docx(DOCX_TEXT["<comment>"])] + newContent +\
                           [docx(DOCX_TEXT["</comment>"])]
                else:
                    return content
            else:
                return []
        elif "margin" in classes:
            if DRAFT:
                if docFormat in ['latex', 'beamer']:
                    newContent = walk(content, handle_comments, docFormat,
                                      meta)
                    return [latex(LATEX_TEXT["<margin>"])] + newContent +\
                           [latex(LATEX_TEXT["</margin>"])]
                elif docFormat in ['html', 'html5']:
                    newContent = walk(content, handle_comments, docFormat,
                                      meta)
                    return [html(HTML_TEXT["<margin>"])] + newContent +\
                           [html(HTML_TEXT["</margin>"])]
                elif docFormat == 'revealjs':
                    newContent = walk(content, handle_comments, docFormat,
                                      meta)
                    return [html(REVEALJS_TEXT["<margin>"])] + newContent +\
                           [html(REVEALJS_TEXT["</margin>"])]
                else:
                    # return content
                    return []
            else:
                return []
        elif "fixme" in classes:
            if DRAFT:
                if docFormat in ['latex', 'beamer']:
                    newContent = walk(content, handle_comments, docFormat,
                                      meta)
                    return [latex(LATEX_TEXT["<fixme>"])] + newContent +\
                           [latex(LATEX_TEXT["</fixme>"])]
                elif docFormat in ['html', 'html5']:
                    newContent = walk(content, handle_comments, docFormat,
                                      meta)
                    return [html(HTML_TEXT["<fixme>"])] + newContent +\
                           [html(HTML_TEXT["</fixme>"])]
                elif docFormat == 'revealjs':
                    newContent = walk(content, handle_comments, docFormat,
                                      meta)
                    return [html(REVEALJS_TEXT["<fixme>"])] + newContent +\
                           [html(REVEALJS_TEXT["</fixme>"])]
                elif docFormat == 'docx':
                    newContent = walk(content, handle_comments, docFormat,
                                      meta)
                    return [docx(DOCX_TEXT["<fixme>"])] + newContent +\
                           [docx(DOCX_TEXT["</fixme>"])]
                else:
                    return content
            else:
                return content
        elif "highlight" in classes:
            if DRAFT:
                if docFormat in ['latex', 'beamer']:
                    # Note: Because of limitations of highlighting in LaTeX,
                    # can't nest any comments inside here: will get LaTeX
                    # error.
                    newContent = walk(content, handle_comments, docFormat,
                                      meta)
                    return [latex(LATEX_TEXT["<highlight>"])] + newContent +\
                           [latex(LATEX_TEXT["</highlight>"])]
                elif docFormat in ['html', 'html5']:
                    newContent = walk(content, handle_comments, docFormat,
                                      meta)
                    return [html(HTML_TEXT["<highlight>"])] + newContent +\
                           [html(HTML_TEXT["</highlight>"])]
                elif docFormat == 'revealjs':
                    newContent = walk(content, handle_comments, docFormat,
                                      meta)
                    return [html(REVEALJS_TEXT["<highlight>"])] + newContent +\
                           [html(REVEALJS_TEXT["</highlight>"])]
                elif docFormat == 'docx':
                    newContent = walk(content, handle_comments, docFormat,
                                      meta)
                    return [docx(DOCX_TEXT["<highlight>"])] + newContent +\
                           [docx(DOCX_TEXT["</highlight>"])]
                else:
                    return content
            else:
                return content
        elif "smcaps" in classes:
            # Always show this---don't worry about draft status!
            if docFormat in ['latex', 'beamer']:
                newContent = walk(content, handle_comments, docFormat, meta)
                return [latex(LATEX_TEXT["<smcaps>"])] + newContent +\
                       [latex(LATEX_TEXT["</smcaps>"])]
            elif docFormat in ['html', 'html5']:
                newContent = walk(content, handle_comments, docFormat, meta)
                return [html(HTML_TEXT["<smcaps>"])] + newContent +\
                       [html(HTML_TEXT["</smcaps>"])]
            elif docFormat == 'revealjs':
                newContent = walk(content, handle_comments, docFormat, meta)
                return [html(REVEALJS_TEXT["<smcaps>"])] + newContent +\
                       [html(REVEALJS_TEXT["</smcaps>"])]
            elif docFormat == 'docx':
                return docx(DOCX_TEXT[tag])
            else:
                # FIXME: I should run this through a filter that capitalizes
                # all strings in `content`.
                return content

        # Alternate way of marking index entries that's required by pandoc2.
        elif "i" in classes:  # Index
            if docFormat == 'latex':  # (This is senseless in beamer.)
                return latex(u'\\index{{{}}}'.format(stringify(content)))
            else:
                return []

        elif "l" in classes:  # Label
            if docFormat in ['latex', 'beamer']:
                return latex(u'\\label{{{}}}'.format(stringify(content)))
                # return latex('\\label{{{}}}'.format(tag[3:-1]))
            elif docFormat in ['html', 'html5']:
                return html(u'<a name="{}"></a>'.format(stringify(content)))
                # return html('<a name="{}"></a>'.format(tag[3:-1]))
            else:
                return []

        elif "r" in classes:  # Reference
            if docFormat in ['latex', 'beamer']:
                return latex(u'\\cref{{{}}}'.format(stringify(content)))
                # return latex('\\cref{{{}}}'.format(tag[3:-1]))
            elif docFormat in ['html', 'html5']:
                return html(u'<a href="#{}">here</a>'
                            .format(stringify(content)))
                # return html('<a href="#{}">here</a>'.format(tag[3:-1]))
            else:
                return []

        elif "rp" in classes:  # Page reference
            if docFormat in ['latex', 'beamer']:
                return latex(u'\\cpageref{{{}}}'.format(stringify(content)))
                # return latex('\\cpageref{{{}}}'.format(tag[4:-1]))
            elif docFormat in ['html', 'html5']:
                return html(u'<a href="#{}">here</a>'
                            .format(stringify(content)))
                # return html('<a href="#{}">here</a>'.format(tag[4:-1]))
            else:
                return []

    # Then check to see if we're changing INLINE_TAG_STACK...
    elif key == 'RawInline':
        elementFormat, tag = value
        if elementFormat != 'html':
            return

        # Check to see if need to suppress output. We do this only for
        # `<comment>` and `<margin>` tags; with `<fixme>` and `<highlight>`
        # tags, we merely suppress the tag.
        if not DRAFT:
            if tag == '<comment>':
                INLINE_COMMENT = True
                return []
            elif tag == '<margin>':
                INLINE_MARGIN = True
                return []
            elif INLINE_COMMENT:  # Need to suppress output
                if tag == '</comment>':
                    INLINE_COMMENT = False
                return []
            elif INLINE_MARGIN:  # Need to suppress output
                if tag == '</margin>':
                    INLINE_MARGIN = False
                return []
            elif tag in ['<fixme>', '<highlight>', '</fixme>',
                         '</highlight>']:
                return []  # Suppress the tag (but not the subsequent text)

        # Not currently suppressing output....

        if tag in ['<comment>', '<fixme>', '<margin>', '<highlight>',
                   '</comment>', '</fixme>', '</margin>', '</highlight>']:
            # LaTeX gets treated differently than HTML
            if docFormat in ['latex', 'beamer', 'docx']:
                preText = ''
                postText = ''
                # Cannot change COLORS within highlighting in LaTeX (but
                # don't do anything when closing the highlight tag!)
                if INLINE_HIGHLIGHT and tag != '</highlight>':
                    if docFormat in ['latex', 'beamer']:
                        preText = LATEX_TEXT['</highlight>']
                        postText = LATEX_TEXT['<highlight>']
                    elif docFormat == 'docx':
                        preText = DOCX_TEXT['</highlight>']
                        postText = DOCX_TEXT['<highlight>']
                if tag in ['<comment>', '<fixme>', '<margin>',
                           '<highlight>']:  # If any opening tag
                    if tag == '<comment>':
                        INLINE_COMMENT = True
                        INLINE_FONT_COLOR_STACK.append(COLORS[tag])
                    elif tag == '<fixme>':
                        INLINE_FONT_COLOR_STACK.append(COLORS[tag])
                    elif tag == '<margin>':
                        INLINE_MARGIN = True
                        INLINE_FONT_COLOR_STACK.append(COLORS[tag])
                    elif tag == '<highlight>':
                        INLINE_HIGHLIGHT = True
                        INLINE_FONT_COLOR_STACK.append(
                            INLINE_FONT_COLOR_STACK[-1])
                    INLINE_TAG_STACK.append(tag)
                    if docFormat in ['latex', 'beamer']:
                        return latex(preText + LATEX_TEXT[tag] + postText)
                    elif docFormat == 'docx':
                        return docx(preText + DOCX_TEXT[tag] + postText)
                elif tag in ['</comment>', '</fixme>', '</margin>',
                             '</highlight>']:
                    if tag == '</comment>':
                        INLINE_COMMENT = False
                    elif tag == '</fixme>':
                        pass
                    elif tag == '</margin>':
                        INLINE_MARGIN = False
                    elif tag == '</highlight>':
                        INLINE_HIGHLIGHT = False
                    INLINE_FONT_COLOR_STACK.pop()
                    previousColor = INLINE_FONT_COLOR_STACK[-1]
                    currentInlineStatus = INLINE_TAG_STACK.pop()
                    if currentInlineStatus[1:] == tag[2:]:
                        # matching opening tag
                        if docFormat in ['latex', 'beamer']:
                            return latex('{}{}\\color{{{}}}{{}}{}'.format(
                                    preText, LATEX_TEXT[tag], previousColor,
                                    postText))
                        elif docFormat == 'docx':
                            return docx(preText + DOCX_TEXT[tag] + postText)
                    else:
                        debug('Closing tag ({}) does not match opening tag '
                              + '({}).\n\n'.format(tag, currentInlineStatus))
                        exit(1)
            else:  # Some docFormat other than LaTeX/beamer
                if tag in ['<comment>', '<fixme>', '<margin>',
                           '<highlight>']:
                    if tag == '<highlight>':
                        INLINE_HIGHLIGHT = True
                    INLINE_TAG_STACK.append(tag)
                else:
                    if tag == '</highlight>':
                        INLINE_HIGHLIGHT = False
                    INLINE_TAG_STACK.pop()
                if docFormat in ['html', 'html5']:
                    return html(HTML_TEXT[tag])
                elif docFormat == 'revealjs':
                    return html(REVEALJS_TEXT[tag])
                else:
                    return []

        elif tag in ['<smcaps>', '</smcaps>']:
            if tag == '<smcaps>':
                INLINE_TAG_STACK.append(tag)
            else:
                INLINE_TAG_STACK.pop()
            if docFormat in ['latex', 'beamer']:
                return latex(LATEX_TEXT[tag])
            elif docFormat in ['html', 'html5']:
                return html(HTML_TEXT[tag])
            elif docFormat == 'revealjs':
                return html(REVEALJS_TEXT[tag])
            elif docFormat == 'docx':
                return docx(DOCX_TEXT[tag])
            else:
                return []

        elif tag.startswith('<i ') and tag.endswith('>'):  # Index
            if docFormat == 'latex':  # (This is senseless in beamer.)
                return latex('\\index{{{}}}'.format(tag[3:-1]))
            else:
                return []

        elif tag.startswith('<l ') and tag.endswith('>'):
            # My definition of a label
            if docFormat in ['latex', 'beamer']:
                return latex('\\label{{{}}}'.format(tag[3:-1]))
            elif docFormat in ['html', 'html5']:
                return html('<a name="{}"></a>'.format(tag[3:-1]))

        elif tag.startswith('<r ') and tag.endswith('>'):
            # My definition of a reference
            if docFormat in ['latex', 'beamer']:
                return latex('\\cref{{{}}}'.format(tag[3:-1]))
            elif docFormat in ['html', 'html5']:
                return html('<a href="#{}">here</a>'.format(tag[3:-1]))

        elif tag.startswith('<rp ') and tag.endswith('>'):
            # My definition of a page reference
            if docFormat in ['latex', 'beamer']:
                return latex('\\cpageref{{{}}}'.format(tag[4:-1]))
            elif docFormat in ['html', 'html5']:
                return html('<a href="#{}">here</a>'.format(tag[4:-1]))

    elif not DRAFT and (INLINE_COMMENT or INLINE_MARGIN):
        # Suppress all output
        return []

    # Check some cases at beginnings of paragraphs
    elif key == 'Para':
        try:
            # If translating to LaTeX, beginning a paragraph with '< '
            # will cause '\noindent{}' to be output first.
            if value[0]['t'] == 'Str' and value[0]['c'] == '<' \
                    and value[1]['t'] == 'Space':
                if docFormat in ['latex', 'beamer']:
                    return Para([latex('\\noindent{}')] + value[2:])
                elif docFormat in ['html', 'html5']:
                    return Para([html('<div class="noindent">')] +
                                value[2:] + [html('</div>')])
                else:
                    return Para(value[2:])

            else:
                return  # Normal paragraph, not affected by this filter

        except:
            return  # May happen if the paragraph is empty.

    # Check for tikz CodeBlock. If it exists, try typesetting figure
    elif key == 'CodeBlock':
        (id, classes, attributes), code = value
        if 'tikz' in classes or '\\begin{tikzpicture}' in code:
            if 'fontfamily' in meta:
                font = meta['fontfamily']['c'][0]['c']
            else:
                font = DEFAULT_FONT
            outfile = path.join(IMAGE_PATH, my_sha1(code + font))
            filetype = '.pdf' if docFormat in ['latex', 'beamer'] else '.png'
            sourceFile = outfile + filetype
            caption = ''
            library = ''
            for a, b in attributes:
                if a == 'caption':
                    caption = b
                elif a == 'tikzlibrary':
                    library = b
            if not path.isfile(sourceFile):
                try:
                    mkdir(IMAGE_PATH)
                    debug('Created directory {}\n\n'.format(IMAGE_PATH))
                except OSError:
                    pass
                codeHeader = '\\documentclass{{standalone}}\n' + \
                             '\\usepackage{{{}}}\n' + \
                             '\\usepackage{{tikz}}\n'.format(font)
                if library:
                    codeHeader += '\\usetikzlibrary{{{}}}\n'.format(library)
                codeHeader += '\\begin{document}\n'
                codeFooter = '\n\\end{document}\n'
                tikz2image(codeHeader + code + codeFooter, filetype,
                           outfile)
                debug('Created image {}\n\n'.format(sourceFile))
            if caption:
                # Need to run this through pandoc to get JSON
                # representation so that captions can be docFormatted text.
                jsonString = toFormat(caption, 'markdown', 'json')
                if "blocks" in jsonString:
                    formattedCaption = eval(jsonString)["blocks"][0]['c']
                else:  # old API
                    formattedCaption = eval(jsonString)[1][0]['c']
            else:
                formattedCaption = [Str('')]
            return Para([Image((id, classes, attributes), formattedCaption,
                        [sourceFile, caption])])
        else:  # CodeBlock, but not tikZ
            return

    else:  # Not text this filter modifies....
        return


def main():
    # This grabs the output of `pandoc` as json file, retrieves `metadata` to
    # check for draft status, and runs the document through `handle_comments`.
    # Then adds any needed entries to `metadata` and passes the output back out
    # to `pandoc`. This code is modeled after
    # <https://github.com/aaren/pandoc-reference-filter>.
    global DRAFT
    document = json.loads(sys.stdin.read())
    if len(sys.argv) > 1:
        format = sys.argv[1]
    else:
        format = ''

    if 'meta' in document:           # new API
        metadata = document['meta']
    elif document[0]:                # old API
        metadata = document[0]['unMeta']

    if 'draft' in metadata:
        DRAFT = metadata['draft']['c']
    else:
        DRAFT = False

    newDocument = document
    newDocument = walk(newDocument, handle_comments, format, metadata)

    # Need to ensure the LaTeX/beamer template knows if `mdframed` package is
    # required (when `<!box>` has been used).
    if (format == 'latex' or format == 'beamer') and USED_BOX:
        MetaList = elt('MetaList', 1)
        MetaInlines = elt('MetaInlines', 1)
        rawinlines = [MetaInlines([RawInline('tex',
                                             '\\RequirePackage{mdframed}')])]
        if 'header-includes' in metadata:
            headerIncludes = metadata['header-includes']
            if headerIncludes['t'] == 'MetaList':
                rawinlines += headerIncludes['c']
            else:  # headerIncludes['t'] == 'MetaInlines'
                rawinlines += [headerIncludes]
        metadata['header-includes'] = MetaList(rawinlines)
        newDocument['meta'] = metadata

    json.dump(newDocument, sys.stdout)


if __name__ == '__main__':
    main()
