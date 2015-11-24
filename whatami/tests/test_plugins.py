# coding=utf-8
"""Test id string generation plugins on isolation."""
from collections import namedtuple, OrderedDict

from future.utils import PY2

from whatami.plugins import (string_plugin, rng_plugin, has_joblib, has_numpy,
                             tuple_plugin, list_plugin, set_plugin, dict_plugin)
import pytest


def test_string_plugin():
    assert string_plugin("cuckoo's nest") == "'cuckoo\\'s nest'"
    assert string_plugin('') == "''"
    assert string_plugin(2) is None


def test_dict_plugin():

    # dict
    assert dict_plugin({}) == '{}'
    assert (dict_plugin({'int': 1, 'str': '1', 'func': test_dict_plugin}) ==
            "{'func':test_dict_plugin(),'int':1,'str':'1'}")

    # OrderedDict
    assert dict_plugin(OrderedDict()) == 'OrderedDict(seq={})'
    assert (dict_plugin(OrderedDict([('int', 1), ('str', '1'), ('func', test_dict_plugin)])) ==
            "OrderedDict(seq={'int':1,'str':'1','func':test_dict_plugin()})")


def test_set_plugin():

    # set
    assert set_plugin(set()) == 'set()'
    assert set_plugin({1, '1', test_set_plugin}) == "{'1',1,test_set_plugin()}"

    # frozenset
    assert set_plugin(frozenset()) == 'frozenset()'
    assert (set_plugin(frozenset([1, '1', test_set_plugin])) ==
            "frozenset({'1',1,test_set_plugin()})")

    # custom set
    class MySet(set):
        pass
    assert set_plugin(MySet()) == 'MySet(seq=set())'
    assert set_plugin(MySet([1, '1', test_set_plugin])) == "MySet(seq={'1',1,test_set_plugin()})"


def test_list_plugin():

    # Basic lists
    assert list_plugin([1, '1', test_list_plugin]) == "[1,'1',test_list_plugin()]"

    # Derived lists
    class MyList(list):
        pass
    assert list_plugin(MyList([1, '1', test_list_plugin])) == "MyList(seq=[1,'1',test_list_plugin()])"
    # maybe we should add a plugin specialised in named tuples, to include the names...


def test_tuple_plugin():

    # Basic tuples
    x = (1, '1', test_tuple_plugin)
    assert tuple_plugin(x) == "(1,'1',test_tuple_plugin())"

    # Subclasses
    x = namedtuple('namedt', ('x', 'y', 'z'))(1, '1', test_tuple_plugin)
    assert tuple_plugin(x) == "namedt(seq=(1,'1',test_tuple_plugin()))"
    # maybe we should add a plugin specialised in named tuples, to include the names...


@pytest.mark.skipif(not (has_numpy() and has_joblib()),
                    reason='the numpy RandomState plugin requires both numpy and joblib')
def test_rng_plugin():
    # noinspection PyPackageRequirements
    import numpy as np
    # The state will depend on the seed...
    rng = np.random.RandomState(0)
    expected_hash = '5b6099022c0aef7e918077c51e887a8a' if PY2 else '17debf0d63a4ef211ea37a05af1f66f7'
    expected = "RandomState(state=tuple(seq=('MT19937',ndarray(hash='%s'),624,0,0.0)))" % expected_hash
    assert rng_plugin(rng) == expected
    # ...and on where are we on the pseudo-random sampling chain
    rng.uniform(size=1)
    expected_hash = '831b5fa156c3cd5941c1a8090c13aa4a' if PY2 else 'd700a30c6dc897d7ac58a508e48cc095'
    expected = "RandomState(state=tuple(seq=('MT19937',ndarray(hash='%s'),2,0,0.0)))" % expected_hash
    assert rng_plugin(rng) == expected
