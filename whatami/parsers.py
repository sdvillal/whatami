# coding=utf-8
"""Utilities for parsing and transforming whatami id strings."""

# Authors: Santi Villalba <sdvillal@gmail.com>
# Licence: BSD 3 clause

from __future__ import print_function, unicode_literals, absolute_import
from arpeggio import ParserPython, Optional, ZeroOrMore, StrMatch, RegExMatch, EOF, PTNodeVisitor, visit_parse_tree


def build_whatami_parser(reduce_tree=False, debug=False):
    """
    Builds an arpeggio parser that accepts any valid whatami generated id string.

    (this function also describes the grammar of the language that What.id() strings should pertain to)

    Known limitations:
      - does not handle escaped single quoted in strings
       (for example, it will fail to parse "rfc(name='\'banyan\'')")

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

    def kv_sep():
        return StrMatch('=')

    def dictkv_sep():
        return StrMatch(':')

    def string_quote():
        return StrMatch('\'')

    def anything_but_quotes():
        return RegExMatch('[^\']*')

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
        return RegExMatch('-?\d+((\.\d*)?((e|E)(\+|-)?\d+)?)?')

    def a_string():
        return string_quote, anything_but_quotes, string_quote

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
        return value, dictkv_sep, value

    def dict_elements():
        return dictkv, Optional(list_sep, dictkv)

    def a_dict():
        return StrMatch('{'), Optional(dict_elements), StrMatch('}')

    # Key-values

    def value():
        return [a_none, a_bool, a_number, a_string, a_tuple, a_list, a_dict, whatami_id]

    def kv():
        return an_id, kv_sep, value

    def kvs():
        return kv, ZeroOrMore(list_sep, kv)

    # Top level

    def whatami_id():
        return an_id, StrMatch('('), Optional(kvs), StrMatch(')')

    def whatami_id_top():
        return whatami_id, EOF

    return ParserPython(whatami_id_top, reduce_tree=reduce_tree, debug=debug)


class WhatamiTreeVisitor(PTNodeVisitor):
    """A tree visitor for whatami id ASTs that returns tuples (name, conf), where conf is a dictionary.

    Parameters
    ----------
    debug : boolean, default False
      Use debug output when visiting a tree
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
        return children[0]

    @staticmethod
    def visit_a_tuple(_, children):
        return tuple(children[0])

    @staticmethod
    def visit_dictkv(_, children):
        return WhatamiTreeVisitor.nonenode2none(children[0]), WhatamiTreeVisitor.nonenode2none(children[1])

    @staticmethod
    def visit_dict_elements(_, children):
        return children

    @staticmethod
    def visit_a_dict(_, children):
        return dict(children[0])

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
        an_id = children[0]
        kvs = list(children[1]) if len(children) > 1 else []
        return an_id, dict(kvs)

    @staticmethod
    def visit_whatami_id_top(_, children):
        return children[0]


def parse_whatid(id_string, parser=build_whatami_parser(), visitor=WhatamiTreeVisitor()):
    """
    Parses whatami id string into a pair (name, configuration).
    Makes a best effort to reconstruct python objects.

    Parameters
    ----------
    id_string : string
        The whatami id string to parse back.

    Returns
    -------
    A tuple (name, configuration). Name is a string and configuration is a dictionary.

    Examples
    --------
    >>> (name, config) = parse_whatid('rfc(n_jobs=multiple(here=100))')
    >>> print(name)
    rfc
    >>> print(len(config))
    1
    >>> print(config['n_jobs'][1]['here'])
    100
    """
    return visit_parse_tree(parser.parse(id_string), visitor=visitor)
