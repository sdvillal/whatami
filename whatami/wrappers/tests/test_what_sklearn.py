# coding=utf-8

# Authors: Santi Villalba <sdvillal@gmail.com>
# Licence: BSD 3 clause

from __future__ import absolute_import
from future.builtins import str
from sklearn.cluster import KMeans
from sklearn.ensemble import RandomForestClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import Normalizer

from whatami.wrappers.what_sklearn import whatamize_sklearn, _check_all_monkeypatched, sklearn_parameters_report

whatamize_sklearn(check=True, log=True)


def test_monkeypatch():
    assert _check_all_monkeypatched()


def test_non_ids():
    rfc = RandomForestClassifier()
    assert 'n_jobs' not in rfc.what().id()
    assert 'n_jobs' in str(rfc.what())


# noinspection PyUnresolvedReferences
def test_pipeline():
    norm = Normalizer(norm='l1')
    norm_id = norm.what().id()
    assert norm_id == "Normalizer(norm='l1')"
    kmeans = KMeans(n_clusters=12)
    kmeans_id = kmeans.what().id()
    print(kmeans_id)
    assert kmeans_id == \
        "KMeans(algorithm='auto',init='k-means++',max_iter=300,n_clusters=12,n_init=10,random_state=None,tol=0.0001)"
    # noinspection PyTypeChecker
    pipeline_id = Pipeline((('norm', norm), ('kmeans', kmeans))).what().id()
    assert pipeline_id == "Pipeline(steps=(('norm',%s),('kmeans',%s)))" % (norm_id, kmeans_id)


def test_no_estimators():
    from sklearn.model_selection import KFold, RepeatedStratifiedKFold, StratifiedShuffleSplit
    assert (KFold(n_splits=5, shuffle=True, random_state=0).what().id() ==
            "KFold(n_splits=5,random_state=0,shuffle=True)")
    assert (StratifiedShuffleSplit(n_splits=2, test_size='default', train_size=None, random_state=0).what().id() ==
            "StratifiedShuffleSplit(n_splits=2,random_state=0,test_size='default',train_size=None)")
    assert (RepeatedStratifiedKFold(n_splits=5, n_repeats=2, random_state=0).what().id() ==
            "RepeatedStratifiedKFold(cv=<class 'sklearn.model_selection._split.StratifiedKFold'>,"
            "cvargs={'n_splits':5},n_repeats=2,random_state=0)")

    from sklearn.gaussian_process.kernels import WhiteKernel
    assert (WhiteKernel(noise_level=2, noise_level_bounds=(1e-5, 1e5)).what().id() ==
            "WhiteKernel(noise_level=2,noise_level_bounds=(1e-05,100000.0))")


def test_sklearn_parameters_report():
    result = sklearn_parameters_report()
    # well, this ought not to be like this...
    assert 'sklearn.cluster.bicluster.BaseSpectral' in result['unwhatamized']
