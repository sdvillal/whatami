# coding=utf-8

# Authors: Santi Villalba <sdvillal@gmail.com>
# Licence: BSD 3 clause

from __future__ import unicode_literals, absolute_import
import arpeggio

import pytest

from whatami import parse_whatid


# --- Parsing id strings

@pytest.mark.xfail(reason='known limitation, to fix or to document as permanent limitation')
def test_parse_whatid_within_string():  # pragma: no cover
    name, conf = parse_whatid("rfc(name=''banyan'')")
    assert name == 'rfc'
    assert conf == {'name': "'banyan'"}


def test_parse_id_simple():
    # no parameters
    name, conf = parse_whatid('rfc()')
    assert name == 'rfc'
    assert conf == {}

    # one parameter
    name, conf = parse_whatid("rfc(n_jobs=4)")
    assert name == 'rfc'
    assert conf == {'n_jobs': 4}

    # multiple parameters
    name, conf = parse_whatid("rfc(deep=True,gini=False,n_jobs=3.4,n_trees=100,seed='rng',splitter=None)")
    assert name == 'rfc'
    assert conf == {'n_jobs': 3.4, 'n_trees': 100, 'seed': 'rng', 'deep': True, 'splitter': None, 'gini': False}


def test_parse_id_lists():
    # lists become lists
    name, conf = parse_whatid("rfc(splits=[1,7,'end'])")
    assert name == 'rfc'
    assert conf == {'splits': [1, 7, 'end']}
    # also with tuples
    name, conf = parse_whatid("rfc(splits=(1,7,'end'))")
    assert name == 'rfc'
    assert conf == {'splits': (1, 7, 'end')}


def test_parse_id_dicts():
    name, conf = parse_whatid("rfc(splits={1:7, None:'end', 'end':None, 'lst': [7, 'b', 1], 'd': {'nest': 2}})")
    assert name == 'rfc'
    assert conf == {'splits': {1: 7, None: 'end', 'end': None, 'lst': [7, 'b', 1], 'd': {'nest': 2}}}


def test_parse_id_spaces():
    name, conf = parse_whatid("rfc(splits={  1:7,  None: 'end','end':None, 'lst': [7,'b', 1], 'd':  {'nest': 2}})")
    assert name == 'rfc'
    assert conf == {'splits': {1: 7, None: 'end', 'end': None, 'lst': [7, 'b', 1], 'd': {'nest': 2}}}


def test_parse_id_nested():
    name, conf = parse_whatid('rfc(n_jobs=multiple(here=100))')
    assert name == 'rfc'
    assert conf == {'n_jobs': ('multiple', {'here': 100})}

    # machine learning inspired nasty nestness

    norm_id = 'Normalizer(norm=\'l1\')'
    kmeans_id = "KMeans(init='k-means++',max_iter=300,n_clusters=12,n_init=10," \
                "precompute_distances=True,random_state=None,tol=0.0001,verbose=0)"
    pipeline_id = "Pipeline(steps=[('norm', %s), ('clusterer', %s)])" % (norm_id, kmeans_id)
    name, conf = parse_whatid(pipeline_id)
    assert name == 'Pipeline'
    assert conf == {
        'steps': [('norm', ('Normalizer', {'norm': 'l1'})),
                  ('clusterer', ('KMeans', {
                      'init': 'k-means++',
                      'max_iter': 300,
                      'n_clusters': 12,
                      'n_init': 10,
                      'precompute_distances': True,
                      'random_state': None,
                      'tol': 0.0001,
                      'verbose': 0
                  }))]}


def test_parse_id_wrong():

    # Configurations must not be empty
    with pytest.raises(arpeggio.NoMatch):
        parse_whatid('')

    # Configurations must have a name
    with pytest.raises(arpeggio.NoMatch):
        parse_whatid('()')

    # Configurations must have a configuration
    with pytest.raises(arpeggio.NoMatch):
        parse_whatid('wrong')

    # Values must have a key
    with pytest.raises(arpeggio.NoMatch):
        parse_whatid('rfc(5)')

    # Keys must have a value
    with pytest.raises(arpeggio.NoMatch):
        parse_whatid('rfc(x=, y=12)')

    # Configurations must have matching parenthesis
    with pytest.raises(arpeggio.NoMatch):
        parse_whatid('rfc(5')
    with pytest.raises(arpeggio.NoMatch):
        parse_whatid('rfc5)')
