# coding=utf-8
"""Tests that id strings generated using introspection are valid."""
from __future__ import unicode_literals, absolute_import
from whatami import whatable
from whatami.parsers import parse_whatid
import pytest


TEST_CASES = ['simple', 'collections', 'nested']


@pytest.fixture(params=TEST_CASES, ids=TEST_CASES)
def whatable2spectations(request):

    # Simple whatable
    if request.param == 'simple':
        @whatable
        def rfc(X, y, n_trees=10, split=2, depth=None, criterion='gini', alpha=1.34):
            return X, y, n_trees, split, depth, criterion, alpha
        expected_id = "rfc(alpha=1.34,criterion='gini',depth=None,n_trees=10,split=2)"
        expected_name = 'rfc'
        expected_conf = {'n_trees': 10,
                         'split': 2,
                         'depth': None,
                         'criterion': 'gini',
                         'alpha': 1.34}
        return rfc, expected_id, expected_name, expected_conf

    # Whatable with collections
    if request.param == 'collections':

        a_dict = {'a': 2, None: 'c'}
        a_list = ['l', None, 3.2]
        a_tuple = (33, a_list, a_dict)

        @whatable
        def rfc(X, y, t=a_tuple):
            return X, y, t
        expected_id = "rfc(t=(33,['l',None,3.2],{'a':2,None:'c'}))"
        expected_name = 'rfc'
        expected_conf = {'t': a_tuple}
        return rfc, expected_id, expected_name, expected_conf

    # Whatable with nested whatables
    if request.param == 'nested':

        a_dict = {'a': 2, None: 'c'}
        a_list = ['l', None, 3.2]
        a_tuple = (33, a_list, a_dict)

        @whatable
        def rfc(X, y, t=a_tuple):
            return X, y, t

        @whatable
        def nests(nested=rfc):
            return nested

        expected_id = "nests(nested=rfc(t=(33,['l',None,3.2],{'a':2,None:'c'})))"
        expected_name = 'nests'
        expected_conf = {'nested': ('rfc', {'t': (33, ['l', None, 3.2], {None: 'c', 'a': 2})})}
        return nests, expected_id, expected_name, expected_conf

    raise ValueError('Cannot find test case %s' % request.param)


def test_roundtrip(whatable2spectations):
    a_whatable, expected_idstring, expected_name, expected_conf = whatable2spectations
    assert expected_idstring == a_whatable.what().id()
    name, conf = parse_whatid(expected_idstring)
    assert expected_name == name
    assert expected_conf == conf
