from __future__ import annotations

import os
from ast import literal_eval
from io import StringIO
from pathlib import Path
from textwrap import indent
from typing import Tuple
from urllib.parse import urlencode

from lark import Transformer, Discard, Token, lark
from ebnf import parse

from railroad import NonTerminal, Terminal, Choice, OneOrMore, ZeroOrMore, Diagram, Optional, Sequence, Group, Comment, Start, DEFAULT_STYLE

LARK_PATH = Path(os.path.dirname(lark.__file__), 'grammars', 'lark.lark')

def eval_escaping(s):
    w = ''
    i = iter(s)
    for n in i:
        w += n
        if n == '\\':
            try:
                n2 = next(i)
            except StopIteration:
                raise ValueError("Literal ended unexpectedly (bad escaping): `%r`" % s)
            if n2 == '\\':
                w += '\\\\'
            elif n2 not in 'uxnftr':
                w += '\\'
            w += n2
    w = w.replace('\\"', '"').replace("'", "\\'")

    to_eval = "u'''%s'''" % w
    try:
        s = literal_eval(to_eval)
    except SyntaxError as e:
        raise ValueError(s, e)

    return s


def _unquote_literal(t, v) -> Tuple[str, str]:
    flag_start = v.rfind('/"'[type == 'STRING']) + 1
    assert flag_start > 0
    flags = v[flag_start:]

    v = v[:flag_start]
    assert v[0] == v[-1] and v[0] in '"/', v
    x = v[1:-1]

    s = eval_escaping(x)

    if t == 'STRING':
        s = s.replace('\\\\', '\\')
    return repr(s)[1:-1], flags


class Lark2Railroad(Transformer):
    def __init__(self, css=DEFAULT_STYLE):
        super(Lark2Railroad, self).__init__()
        self._css = css

    def __default__(self, data, children, meta):
        raise ValueError((data, children))

    def _href_generator(self, node_type, value):
        return None

    def rule_params(self, children):
        if len(children) != 0:
            raise ValueError("Rule templates are currently not supported")
        raise Discard

    def token_params(self, children):
        if len(children) != 0:
            raise ValueError("Token templates are currently not supported")
        raise Discard

    def name(self, children):
        name, = children
        return {'RULE': NonTerminal, 'TOKEN': Terminal}[name.type] \
            (name.value, href=self._href_generator(name.type, name.value))

    def literal(self, children):
        value, = children
        return Terminal(value.value, href=self._href_generator(value.type, value.value))

    def literal_range(self, children):
        start, end = children
        return Terminal(f'{start}..{end}', self._href_generator('literal_range', (start, end)))

    def expansion(self, children):
        return Sequence(*children)

    def expansions(self, children):
        return Choice(0, *children)

    def maybe(self, children):
        return Optional(children[0])

    def alias(self, children):
        base, name = children
        return Group(base, name.value)

    def expr(self, children):
        if len(children) == 3:
            base, mi, ma = children
            if int(mi.value) == 0:
                if int(ma.value) == 1:
                    return Optional(base)
                return ZeroOrMore(base, Comment(f'{mi.value}..{ma.value}'))
            else:
                return OneOrMore(base, Comment(f'{mi.value}..{ma.value}'))
        base, op = children
        if op.type != 'OP':
            return OneOrMore(base, Comment(f'{op.value} times'))
        if op.value == '+':
            return OneOrMore(base)
        elif op.value == '*':
            return ZeroOrMore(base)
        elif op.value == '?':
            return Optional(base)
        else:
            raise ValueError(f"Unsupported Operator {op!r}")

    def rule(self, children):
        name, expansions = children
        return name, Diagram(Start('complex', name.value), expansions, type='complex', css=self._css)

    def token(self, children):
        name, expansions = children
        return name, Diagram(Start('simple', name.value), expansions, type='simple', css=self._css)

    def _ignore_this_node(self, children):
        raise Discard

    import_path = import_ = ignore = _ignore_this_node

    def start(self, children):
        return children


STYLE_TEMPLATE_DIRECT = """\
  <style type='text/css'>
  {style}
  </style>"""

STYLE_TEMPLATE_LINK = '<link rel="stylesheet" href="{href}">'

HTML_TEMPLATE = """\
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">

  <title>Grammar railroad diagram for {file_name!r}</title>

{style}

</head>

<body>
  {diagrams}
</body>
</html>\
"""

DIAGRAM_TEMPLATE = """
  <div id='{id}'>
{svg}
  </div>
"""


class Lark2HTML(Lark2Railroad):
    _file_name = '&lt;string&gt;'

    def __init__(self, css=DEFAULT_STYLE, css_ref=None, file_name=None, regex_link_creator=lambda regex, flags: None,
                 get_import=lambda path: None):
        super(Lark2HTML, self).__init__(css=None)
        if css_ref is not None:
            assert css is None or css is DEFAULT_STYLE, "Cannot specify both css and css_ref"
            self._global_css = STYLE_TEMPLATE_LINK.format(href=css_ref)
        else:
            self._global_css = STYLE_TEMPLATE_DIRECT.format(style=css)
        if file_name is not None:
            self._file_name = file_name
        self._regex_link_creator = regex_link_creator
        self._get_import = get_import

    def _href_generator(self, node_type, value):
        if node_type in ('RULE', 'TOKEN'):
            return f'#{value}'
        elif node_type == 'REGEXP':
            regex, flags = _unquote_literal(node_type, value)
            return self._regex_link_creator(regex, flags)
        else:
            return None

    def import_path(self, children):
        return children

    def import_(self, children):
        if len(children) == 2:
            path, alias = children
        else:
            path, = children
            alias = path[-1]
        path = [t.text if not isinstance(t, Token) else t.value for t in path]
        alias = alias.text
        info = self._get_import(path)
        if info is None:
            raise Discard
        file_name, href = info
        t, c = [('simple', Terminal), ('complex', NonTerminal)][alias.islower()]
        return alias, Diagram(Start(t, alias),
                              c(f"import {path[-1]} from {''.join(path[:-2])}[{file_name!r}]",
                                href=href),
                              type=t, css=self._css)

    def start(self, children):
        diagrams = []
        for name, d in children:
            d: Diagram
            buffer = StringIO()
            d.writeSvg(buffer.write)
            diagrams.append(DIAGRAM_TEMPLATE.format(id=name.lstrip('?!'), svg=indent(buffer.getvalue(), '    ')))
        diagrams = '<br>'.join(diagrams)
        return HTML_TEMPLATE.format(
            file_name=self._file_name,
            style=self._global_css,
            diagrams=diagrams
        )


setattr(Lark2HTML, 'import', Lark2HTML.import_)


def regex101(regex, flags):
    return "https://regex101.com/?{}".format(urlencode({'regex': regex, 'flavor': 'python', 'flags': flags}))


def pythex(regex, flags):
    return "https://pythex.org/?{}".format(urlencode({
        'regex': regex,
        'ignorecase': int('i' in flags),
        'multiline': int('m' in flags),
        'dotall': int('s' in flags),
        'verbose': int('x' in flags)}))


def basic_import_link(path):
    name = path[-3]  # ['path', '.', 'to', '.', 'grammar', '.', 'NAME']
    return '%s.lark' % name, './%s.html#%s' % (name, path[-1])

def auto_import_for(base_file: Path, s: set[Path]):
    # Note: we are not using the import semantics of lark, but only approximate them. This *should* work
    def auto_import_link(path):
        if path[0] == '.':
            children = path[1:-1:2]
            import_path = base_file.parent.joinpath(*children).with_suffix('.lark')
        else:
            assert len(path) == 3
            import_path = LARK_PATH.with_name(path[0]).with_suffix('.lark')
        s.add(import_path)
        name = path[-3]  # ['path', '.', 'to', '.', 'grammar', '.', 'NAME']
        return '%s.lark' % name, './%s.html#%s' % (name, path[-1])
    return auto_import_link

if __name__ == '__main__':
    from argparse import ArgumentParser

    argparser = ArgumentParser('python -m ebnf.railroad',
                               description='Creates .html files with railroad diagrams from the grammar file')

    argparser.add_argument('-i', '--imports', action='store_true',
                           help='Generate import links. Assumes all diagrams are in the same folder')
    argparser.add_argument('-a', '--auto-import', action='store_true',
                           help='Automatically tries to import grammars and also generate those diagrams. Implies -i')
    argparser.add_argument('-c', '--common', action='append', default=[],
                           help='Generate a diagram for a stdlib lark grammar')
    out_group = argparser.add_mutually_exclusive_group()
    out_group.add_argument('-s', '--stdout', action='store_true',
                           help='Only valid when only one grammar has been specified. Outputs to stdout')
    out_group.add_argument('-o', '--out', default='.', help='The directory in which to put the diagrams. Defaults to the current directory')
    css_group = argparser.add_mutually_exclusive_group()
    css_group.add_argument('--css', help="Specify the css to use for the diagram")
    css_group.add_argument('--css-ref',
                           help="Specify that the css should be kept as an external file. Uses the exact string provided as a link")

    regex_group = argparser.add_mutually_exclusive_group()
    regex_group.add_argument('--regex101', action='store_const', const=regex101, dest='regex', help='Create regex links to regex101.com')
    regex_group.add_argument('--pythex', action='store_const', const=pythex, dest='regex', help='Create regex links to pythex.org')

    argparser.add_argument('grammars', nargs='*', help="The .lark files for which to generate the diagrams")

    ns = argparser.parse_args()
    kwargs = {}
    if ns.css is not None:
        kwargs['css'] = open(ns.css).read()
    elif ns.css_ref is not None:  # argparse should prevent that both are not None
        kwargs['css'] = None
        kwargs['css_ref'] = ns.css_ref
    if ns.regex is not None:
        kwargs['regex_link_creator'] = ns.regex
    if ns.imports:
        kwargs['get_import'] = basic_import_link
    l2h = Lark2HTML(**kwargs)
    for g in ns.common:
        ns.grammars.append(LARK_PATH.with_name(g).with_suffix('.lark'))

    if not ns.grammars:
        argparser.print_help()
        exit()
    if ns.stdout:
        assert len(ns.grammars) == 1, "Can only output to stdout when exactly one grammar is specified"
        assert not ns.auto_import, "Can not automatically generate imports when outputting to stdout"
        g, = ns.grammars
        l2h._file_name = os.path.basename(g)
        with open(g) as f:
            grammar = f.read()
        print(l2h.transform(parse('lark', grammar)))
    else:
        to_generate = {Path(g).with_suffix('.lark') for g in ns.grammars}
        generated = set()
        while to_generate:
            g = to_generate.pop()
            l2h._file_name = g.name
            if l2h._file_name in generated:
                continue
            else:
                generated.add(l2h._file_name)
            if ns.auto_import:
                l2h._get_import = auto_import_for(g, to_generate)
            with open(g) as f:
                grammar = f.read()
            tree = parse('lark', grammar)
            base, ext = os.path.splitext(l2h._file_name)
            with open(os.path.join(ns.out, base + '.html'), 'w') as f:
                f.write(l2h.transform(tree))
