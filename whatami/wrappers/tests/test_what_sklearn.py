# coding=utf-8

# Authors: Santi Villalba <sdvillal@gmail.com>
# Licence: BSD 3 clause
from __future__ import unicode_literals, absolute_import
from future.builtins import str
from sklearn.cluster import KMeans
from sklearn.ensemble import RandomForestClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import Normalizer

from whatami.wrappers.what_sklearn import whatamise_sklearn, _check_all_monkeypatched

whatamise_sklearn(check=True, log=True)


def test_monkeypatch():
    assert _check_all_monkeypatched()


def test_non_ids():
    rfc = RandomForestClassifier()
    assert 'n_jobs' not in rfc.what().id()
    assert 'n_jobs' in str(rfc.what())


def test_pipeline():
    norm = Normalizer(norm='l1')
    norm_id = norm.what().id()
    assert norm_id == "Normalizer(norm='l1')"
    kmeans = KMeans(n_clusters=12)
    kmeans_id = kmeans.what().id()
    assert kmeans_id == \
        "KMeans(init='k-means++',max_iter=300,n_clusters=12,n_init=10," \
        "precompute_distances='auto',random_state=None,tol=0.0001,verbose=0)"
    pipeline_id = Pipeline((('norm', norm), ('kmeans', kmeans))).what().id()
    assert pipeline_id == "Pipeline(steps=[('norm',%s),('kmeans',%s)])" % (norm_id, kmeans_id)
