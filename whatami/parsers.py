# coding=utf-8
"""Utilities for parsing and transforming whatami id strings."""

# Authors: Santi Villalba <sdvillal@gmail.com>
# Licence: BSD 3 clause

from __future__ import print_function, absolute_import, unicode_literals  # N.B. arpeggio wants unicode
from arpeggio import ParserPython, Optional, ZeroOrMore, StrMatch, RegExMatch, EOF, PTNodeVisitor, visit_parse_tree


def build_whatami_parser(reduce_tree=False, debug=False):
    """
    Builds an arpeggio parser that accepts any valid whatami generated id string.

    (this function also describes the grammar of the language that What.id() strings should pertain to)

    Parameters
    ----------
    reduce_tree : boolean, default False
      Check `arpeggio.ParserPython` documentation

    debug : boolean, default False
      Check `arpeggio.ParserPython` documentation (N.B. will generate dot files in the running directory)

    Returns
    -------
    The arpeggio parser. Call `parser.parse` to generate the AST.
    """

    # Syntactic noise

    def list_sep():
        return StrMatch(',')

    # Basic types

    def an_id():
        # These account for valid python 2 identifiers. Python 3 allow unicode in identifiers.
        # See:
        #   http://stackoverflow.com/questions/5474008/regular-expression-to-confirm-whether-a-string-is-a-valid-identifier-in-python
        # When/if adapting to py3, that should be handled.
        # Note also that arpeggio does not allow unicode in regexps;
        # it should be easy to implement by just allowing arbitrary re flags in RegExMatch
        return RegExMatch(r'[_A-Za-z][_a-zA-Z0-9]*')

    def a_number():
        return [RegExMatch('-?\d+((\.\d*)?((e|E)(\+|-)?\d+)?)?'),
                StrMatch('-inf'), StrMatch('inf'), StrMatch('nan')]

    def a_string():
        return StrMatch("'"), RegExMatch(r"(\\.|[^'])*"), StrMatch("'")

    def a_true():
        return StrMatch('True')

    def a_false():
        return StrMatch('False')

    def a_bool():
        return [a_true, a_false]

    def a_none():
        return StrMatch('None')

    # Collection types: lists, tuples, dictionaries

    def list_elements():
        return value, ZeroOrMore(list_sep, value)

    def a_list():
        return StrMatch('['), Optional(list_elements), StrMatch(']')

    def a_tuple():
        return StrMatch('('), Optional(list_elements), StrMatch(')')

    def dictkv():
        return value, StrMatch(':'), value

    def dict_elements():
        return dictkv, ZeroOrMore(list_sep, dictkv)

    def a_dict():
        return StrMatch('{'), Optional(dict_elements), StrMatch('}')

    def an_empty_set():
        return [StrMatch('set()'), StrMatch('frozenset()')]

    def a_non_empty_set():
        return [(StrMatch('{'), Optional(list_elements), StrMatch('}')),
                (StrMatch('frozenset({'), Optional(list_elements), StrMatch('})'))]

    def a_set():
        return [an_empty_set, a_non_empty_set]

    # Key-values

    def value():
        return [a_none, a_bool, a_number, a_string, a_tuple, a_list, a_set, a_dict, whatami_id]

    def kv():
        return an_id, StrMatch('='), value

    def kvs():
        return kv, ZeroOrMore(list_sep, kv)

    # Top level

    def whatami_id():
        return Optional(an_id, StrMatch('=')), an_id, StrMatch('('), Optional(kvs), StrMatch(')')

    def whatami_id_top():
        return whatami_id, EOF

    return ParserPython(whatami_id_top, reduce_tree=reduce_tree, debug=debug)


class WhatamiTreeVisitor(PTNodeVisitor):
    """A tree visitor for whatami id ASTs that returns a `whatami.What` object.

    Parameters
    ----------
    debug : boolean, default False
      Use debug output when visiting a tree

    Returns
    -------
    A `whatami.What` object inferred from the id string.
    """

    def __init__(self, debug=False):
        # N.B. these actions assume that syntactic noise is being ignored, therefore defaults=True
        super(WhatamiTreeVisitor, self).__init__(defaults=True, debug=debug)

    # --- Basic types

    @staticmethod
    def visit_an_id(node, _):
        return node.value

    @staticmethod
    def visit_a_number(node, _):
        try:
            return int(node.value)
        except ValueError:
            return float(node.value)

    @staticmethod
    def visit_a_string(_, children):
        return children[0]

    @staticmethod
    def visit_a_true(*_):
        return True

    @staticmethod
    def visit_a_false(*_):
        return False

    # None is the arpeggio marker for nodes to be ignored, we need this trick to defer None instantiation
    _NONE_NODE = '*-*NoNeNoDe*-*'

    @staticmethod
    def nonenode2none(x):
        return None if x is WhatamiTreeVisitor._NONE_NODE else x

    @staticmethod
    def visit_a_none(*_):
        return WhatamiTreeVisitor._NONE_NODE

    # --- Collection types: lists, tuples, dictionaries

    @staticmethod
    def visit_list_elements(_, children):
        return list(map(WhatamiTreeVisitor.nonenode2none, children))

    @staticmethod
    def visit_a_list(_, children):
        return children[0] if len(children) else []

    @staticmethod
    def visit_a_tuple(_, children):
        return tuple(children[0]) if len(children) else ()

    @staticmethod
    def visit_dictkv(_, children):
        return WhatamiTreeVisitor.nonenode2none(children[0]), WhatamiTreeVisitor.nonenode2none(children[1])

    @staticmethod
    def visit_dict_elements(_, children):
        return children

    @staticmethod
    def visit_a_dict(_, children):
        return dict(list(children[0]))

    @staticmethod
    def visit_an_empty_set(*_):
        return set()

    @staticmethod
    def visit_a_non_empty_set(_, children):
        return set(list(children[0]))

    # Key-values

    @staticmethod
    def visit_value(_, children):
        return children[0]

    @staticmethod
    def visit_kv(_, children):
        return children[0], WhatamiTreeVisitor.nonenode2none(children[1])

    @staticmethod
    def visit_kvs(_, children):
        return children

    # --- Top level

    @staticmethod
    def visit_whatami_id(_, children):
        from whatami import What
        # lengths can be 1, 2 or 3
        if 3 == len(children):
            out_name, an_id, kvs = children
        elif 2 == len(children):
            an_id, kvs = children
            out_name = None
        else:
            an_id = children[0]
            kvs = []
            out_name = None
        return What(an_id, dict(list(kvs)), out_name=out_name)

    @staticmethod
    def visit_whatami_id_top(_, children):
        return children[0]


DEFAULT_WHATAMI_PARSER = build_whatami_parser()
DEFAULT_WHATAMI_VISITOR = WhatamiTreeVisitor()


def parse_whatid(id_string, parser=None, visitor=None):
    """
    Parses whatami id string into a pair (name, configuration).
    Makes a best effort to reconstruct python objects.

    Parameters
    ----------
    id_string : string
      The whatami id string to parse back.

    parser : An arpeggio parser or None
      The parser. Use None to use the default parser.

    visitor : An arpeggio visitor or None.
      Semantic actions over the AST.
      If None, the default visitor (that returns a What object) is used.

    Returns
    -------
    A two-tuple (what, out_name)
    what is a `whatami.What` object, containing name and conf
    out_name is a string or None

    Examples
    --------
    >>> what = parse_whatid('rfc(n_jobs=multiple(here=100))')
    >>> print(what.name)
    rfc
    >>> print(len(what.conf))
    1
    >>> print(what.conf['n_jobs'].conf['here'])
    100
    """
    global DEFAULT_WHATAMI_PARSER
    if parser is None:
        parser = DEFAULT_WHATAMI_PARSER
    if visitor is None:
        visitor = DEFAULT_WHATAMI_VISITOR
    try:
        return visit_parse_tree(parser.parse(id_string), visitor=visitor)
    except TypeError:
        # Remove this once arpeggio is released with this fix:
        # https://github.com/igordejanovic/Arpeggio/pull/21
        DEFAULT_WHATAMI_PARSER = build_whatami_parser()
        raise

# --- Maintenance for old whatami id strings


def build_oldwhatami_parser(reduce_tree=False, debug=False):

    # Unfortunately this is an almost verbatim copy & paste of "build_whatami_parser"
    # It is hard to avoid code duplication here:
    #  - Put rules in a class: Arpeggio does not like it (maybe accepting an object with certain API could be helpful)
    #  - Put rules in module scope: functions for old-style and new-style rules should be named alike so that
    #    visitors can be reused; it turns out that it is not possible to configure if we want new/old rules
    #  - I have not explored other options (use peg syntax, use higher order functions that return rules...)

    # Syntactic noise

    def list_sep():
        return StrMatch(',')

    # Basic types

    def an_id():
        # These account for valid python 2 identifiers. Python 3 allow unicode in identifiers.
        # See:
        #   http://stackoverflow.com/questions/5474008/regular-expression-to-confirm-whether-a-string-is-a-valid-identifier-in-python
        # When/if adapting to py3, that should be handled.
        # Note also that arpeggio does not allow unicode in regexps;
        # it should be easy to implement by just allowing arbitrary re flags in RegExMatch
        return RegExMatch(r'[_A-Za-z][_a-zA-Z0-9]*')

    def a_number():
        return [RegExMatch('-?\d+((\.\d*)?((e|E)(\+|-)?\d+)?)?'),
                StrMatch('-inf'), StrMatch('inf'), StrMatch('nan')]

    def a_string():
        return StrMatch("'"), RegExMatch(r"(\\.|[^'])*"), StrMatch("'")

    def a_true():
        return StrMatch('True')

    def a_false():
        return StrMatch('False')

    def a_bool():
        return [a_true, a_false]

    def a_none():
        return StrMatch('None')

    # Collection types: lists, tuples, dictionaries

    def list_elements():
        return value, ZeroOrMore(list_sep, value)

    def a_list():
        return StrMatch('['), Optional(list_elements), StrMatch(']')

    def a_tuple():
        return StrMatch('('), Optional(list_elements), StrMatch(')')

    def dictkv():
        return value, StrMatch(':'), value

    def dict_elements():
        return dictkv, ZeroOrMore(list_sep, dictkv)

    def a_dict():
        return StrMatch('{'), Optional(dict_elements), StrMatch('}')

    def an_empty_set():
        return StrMatch('set()')

    def a_non_empty_set():
        return StrMatch('{'), Optional(list_elements), StrMatch('}')

    def a_set():
        return [an_empty_set, a_non_empty_set]

    # Key-values

    def value():
        return [a_none, a_bool, a_number, a_string, a_tuple, a_list, a_set, a_dict, whatami_id]

    def kv():
        return an_id, StrMatch('='), value

    def kvs():  # Difference from copied-pasted
        return kv, ZeroOrMore('#', kv)

    # Top level

    def whatami_id():  # Difference 1
        return [(an_id, StrMatch('#'), Optional(kvs)),
                (StrMatch('"'), an_id, StrMatch('#'), Optional(kvs), StrMatch('"'))]

    def whatami_id_top():
        return whatami_id, EOF

    return ParserPython(whatami_id_top, reduce_tree=reduce_tree, debug=debug)
