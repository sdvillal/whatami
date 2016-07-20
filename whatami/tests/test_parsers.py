# coding=utf-8

# Authors: Santi Villalba <sdvillal@gmail.com>
# Licence: BSD 3 clause

from __future__ import absolute_import
import arpeggio

from ..what import What
from ..parsers import parse_whatid

import pytest


# --- Parsing id strings

@pytest.mark.xfail(reason='known limitation, to fix or to document as permanent limitation')
def test_parse_whatid_within_string():  # pragma: no cover
    what = parse_whatid("rfc(name=''banyan'')")
    assert what.name == 'rfc'
    assert what.conf == {'name': "'banyan'"}


def test_parse_id_simple():
    # no parameters
    what = parse_whatid('rfc()')
    assert what.name == 'rfc'
    assert what.conf == {}

    # one parameter
    what = parse_whatid("rfc(n_jobs=4)")
    assert what.name == 'rfc'
    assert what.conf == {'n_jobs': 4}

    # multiple parameters
    what = parse_whatid("rfc(deep=True,gini=False,n_jobs=3.4,n_trees=100,seed='rng',splitter=None)")
    assert what.name == 'rfc'
    assert what.conf == {'n_jobs': 3.4, 'n_trees': 100, 'seed': 'rng', 'deep': True, 'splitter': None, 'gini': False}


def test_parse_id_infs_nans():
    # -inf
    what = parse_whatid("rfc(min=-inf)")
    assert what['min'] == -float('inf')
    # +inf
    what = parse_whatid("rfc(min=inf)")
    assert what['min'] == float('inf')
    # nan
    what = parse_whatid("rfc(min=nan)")
    assert what['min'] != what['min']


def test_parse_id_lists():
    # lists become lists
    what = parse_whatid("rfc(splits=[1,7,'end'],empty=[])")
    assert what.name == 'rfc'
    assert what.conf == {'splits': [1, 7, 'end'], 'empty': []}
    # also with tuples
    what = parse_whatid("rfc(splits=(1,7,'end'),empty=[])")
    assert what.name == 'rfc'
    assert what.conf == {'splits': (1, 7, 'end'), 'empty': []}


def test_parse_id_dicts():
    what = parse_whatid("rfc(splits={1:7, None:'end', 'end':None, 'lst': [7, 'b', 1], 'd': {'nest': 2}})")
    assert what.name == 'rfc'
    assert what.conf == {'splits': {1: 7, None: 'end', 'end': None, 'lst': [7, 'b', 1], 'd': {'nest': 2}}}


def test_parse_id_sets():
    # with elements
    what = parse_whatid("rfc(splits={1, None, 'end'})")
    assert what.name == 'rfc'
    assert what.conf == {'splits': {1, None, 'end'}}
    # empty
    what = parse_whatid("rfc(splits=set())")
    assert what.name == 'rfc'
    assert what.conf == {'splits': set()}


def test_parse_id_spaces():
    what = parse_whatid("rfc(splits={  1:7,  None: 'end','end':None, 'lst': [7,'b', 1], 'd':  {'nest': 2}})")
    assert what.name == 'rfc'
    assert what.conf == {'splits': {1: 7, None: 'end', 'end': None, 'lst': [7, 'b', 1], 'd': {'nest': 2}}}


def test_parse_id_nested():
    what = parse_whatid('rfc(n_jobs=multiple(here=100))')
    assert what.name == 'rfc'
    assert what.conf == {'n_jobs': What('multiple', {'here': 100})}

    # machine learning inspired nasty nestness

    norm_id = 'Normalizer(norm=\'l1\')'
    kmeans_id = "KMeans(init='k-means++',max_iter=300,n_clusters=12,n_init=10," \
                "precompute_distances=True,random_state=None,tol=0.0001,verbose=0)"
    pipeline_id = "Pipeline(steps=[('norm', %s), ('clusterer', %s)])" % (norm_id, kmeans_id)
    what = parse_whatid(pipeline_id)
    assert what.name == 'Pipeline'
    assert what.conf == {
        'steps': [('norm', What('Normalizer', {'norm': 'l1'})),
                  ('clusterer', What('KMeans', {
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


def test_parse_id_escaped():
    whatid = "A(b='C(d=\\'hey\\')')"
    what = parse_whatid(whatid)
    assert what.id() == whatid


def test_parse_id_out_name():
    what = parse_whatid('kurtosis=moments(x=std=Normal(mean=0,std=1))')
    assert what.out_name == 'kurtosis'
    assert what.name == 'moments'
    assert what.conf == {'x': What(name='Normal',
                                   conf={'mean': 0, 'std': 1},
                                   out_name='std')}


def test_arpeggio_resilience():
    with pytest.raises(TypeError):
        parse_whatid(map)
    what = parse_whatid("rfc(splits = {1, None, 'end'})")
    assert what.name == 'rfc'
    assert what.conf == {'splits': {1, None, 'end'}}
