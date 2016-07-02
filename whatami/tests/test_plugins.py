# coding=utf-8
"""Test id string generation plugins on isolation."""
from collections import namedtuple, OrderedDict

from future.utils import PY2

from whatami.plugins import (string_plugin, rng_plugin, has_numpy,
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


@pytest.mark.skipif(not has_numpy(),
                    reason='the numpy RandomState plugin requires numpy')
def test_rng_plugin():
    # noinspection PyPackageRequirements
    import numpy as np
    # The state will depend on the seed...
    rng = np.random.RandomState(0)
    expected_hash = 'c86ba9d751868840814285c8d894cf6e' if PY2 else '31a41b7cfda3c6075752046a36d43230'
    expected = "RandomState(state=tuple(seq=('MT19937',ndarray(hash='%s'),624,0,0.0)))" % expected_hash
    assert expected == rng_plugin(rng)
    # ...and on where are we on the pseudo-random sampling chain
    rng.uniform(size=1)
    expected_hash = 'e1f5b00dbefe7c9ea168ded4bbcd2ba8' if PY2 else '662c48a1ec3131127823ec872403fc3c'
    expected = "RandomState(state=tuple(seq=('MT19937',ndarray(hash='%s'),2,0,0.0)))" % expected_hash
    assert expected == rng_plugin(rng)
