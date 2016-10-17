# coding=utf-8
"""Whatable wrappers for scikit learn tools.

Using it is fairly simple and does not require changing anything that is already using sklearn,
but beware that we are monkey-patching sklearn BaseEstimator to add the what method.

Example
-------

>>> # Monkey-patch sklearn estimators
>>> whatamise_sklearn()
>>> # Use what() to retrieve the id of a model
>>> from sklearn.ensemble import RandomForestClassifier
>>> rfc = RandomForestClassifier(n_jobs=8, n_estimators=23)
>>> print(rfc.what().id())
rfc(bootstrap=True,class_weight=None,criterion='gini',max_depth=None,max_features='auto',max_leaf_nodes=None,min_impurity_split=1e-07,min_samples_leaf=1,min_samples_split=2,min_weight_fraction_leaf=0.0,n_estimators=23,random_state=None,warm_start=False)
>>> print(rfc.what())
rfc(bootstrap=True,class_weight=None,criterion='gini',max_depth=None,max_features='auto',max_leaf_nodes=None,min_impurity_split=1e-07,min_samples_leaf=1,min_samples_split=2,min_weight_fraction_leaf=0.0,n_estimators=23,n_jobs=8,oob_score=False,random_state=None,verbose=0,warm_start=False)

Implementation Notes
--------------------

scikit-learn, in the good tradition of machine learning libraries (e.g. good old weka)
already deals graciously with configurability. Almost all interesting tools in sklearn
(classifiers, regressors, clusterers, dimensionality-reducers and other preprocessors)
are classes inheriting from BaseEstimator:
  https://github.com/scikit-learn/scikit-learn/blob/master/sklearn/base.py

This is the key contract for these subclasses:
  "All estimators should specify all the parameters that can be set at the class level
   in their __init__ as explicit keyword arguments (no *args or **kwargs)."

This allows the sklearn folks to precisely define a protocol for configuring, configuration
retrieval and cloning (along with other niceties like standard control of deprecation).

It also makes really easy to add a what() method to scikit estimators.
"""

# Authors: Santi Villalba <sdvillal@gmail.com>
# Licence: BSD 3 clause

from __future__ import absolute_import
import inspect
import warnings

from sklearn.base import BaseEstimator
from sklearn.cluster import KMeans, DBSCAN, MeanShift, SpectralClustering, Birch
from sklearn.cluster.affinity_propagation_ import AffinityPropagation
from sklearn.cluster.bicluster import SpectralCoclustering, SpectralBiclustering
from sklearn.cluster.hierarchical import AgglomerativeClustering, FeatureAgglomeration
from sklearn.cluster.k_means_ import MiniBatchKMeans
from sklearn.cross_decomposition import PLSRegression, PLSCanonical, CCA, PLSSVD
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor, ExtraTreesClassifier, ExtraTreesRegressor
from sklearn.ensemble.gradient_boosting import GradientBoostingClassifier, GradientBoostingRegressor
from sklearn.gaussian_process import GaussianProcess
from sklearn.linear_model import Ridge, Lasso, ElasticNet, Lars, OrthogonalMatchingPursuit, \
    BayesianRidge, ARDRegression, LogisticRegression, SGDClassifier, SGDRegressor, Perceptron, LassoLars, \
    LinearRegression
from sklearn.naive_bayes import GaussianNB, MultinomialNB, BernoulliNB
from sklearn.neighbors import KNeighborsClassifier, RadiusNeighborsClassifier, KNeighborsRegressor, \
    RadiusNeighborsRegressor, NearestCentroid
from sklearn.pipeline import FeatureUnion
from sklearn.preprocessing import Normalizer
from sklearn.preprocessing.data import MinMaxScaler
from sklearn.svm import SVC, NuSVC, LinearSVC, SVR, NuSVR
from sklearn.tree import DecisionTreeClassifier, DecisionTreeRegressor

from ..what import What
from ..misc import all_subclasses


# ----- Manually check which parameters are not part of the default id (WIP)

_LAST_SKLEARN_CHECKED = '1.5.1'

_SKLRegistry = {}


class _SklearnEstimatorID(object):
    """
    Stores information about sklearn short names, non_id_params, notes and possibly others.

    N.B. it is better to include a non-existing non_id_param
    (innocuous, can help to support several sklearn versions)
    than to leave out existing non_id_params.
    """

    def __init__(self,
                 skclass,
                 short_name,
                 non_id_params=(),
                 notes=None):
        self.skclass = skclass
        self.short_name = short_name if short_name is not None else skclass.__name__
        self.non_id_params = non_id_params
        self.notes = notes


def _a(skclass, nickname, non_id_params=(), notes=None):
    """Adds a class to the SKLRegistry."""
    _SKLRegistry[skclass.__name__] = _SklearnEstimatorID(skclass, nickname, non_id_params, notes)


# Ensembles
_a(RandomForestClassifier, 'rfc', ('verbose', 'n_jobs', 'oob_score'),
   'oob_score used to change the internal representation of the model (recheck)')
_a(RandomForestRegressor, 'rfr', ('verbose', 'n_jobs', 'oob_score'),
   'Same non-ids as RFC')
_a(ExtraTreesClassifier, 'etc', ('n_jobs', 'verbose', 'oob_score'))
_a(ExtraTreesRegressor, 'etr', ('n_jobs', 'verbose', 'oob_score'))
_a(GradientBoostingClassifier, 'gbc', ('verbose',))
_a(GradientBoostingRegressor, 'gbr', ('verbose',))

# GLMs
_a(Ridge, 'ridge', ('copy_X',))
_a(Lasso, 'lasso', ('copy_X',),
   'we need to take care of "precompute" when we pass the Gram matrix, should use a hash of the array')
_a(ElasticNet, 'elnet', ('copy_X',),
   'we need to take care of "precompute" when we pass the Gram matrix, should use a hash of the array')
_a(Lars, 'lars', ('verbose', 'copy_X', 'fit_path'),
   'we need to take care of "precompute" when we pass the Gram matrix, should use a hash of the array')
_a(LassoLars, 'lassolars', ('verbose', 'copy_X', 'fit_path'),
   'we need to take care of "precompute" when we pass the Gram matrix, should use a hash of the array')
_a(OrthogonalMatchingPursuit, 'omp', ('copy_X', 'copy_Xy', 'copy_Gram'),
   'we need to take care of "precompute" when we pass the Gram matrix, should use a hash of the array')
_a(BayesianRidge, 'bayridge', ('copy_X', 'verbose'))
_a(ARDRegression, 'ardr', ('copy_X', 'verbose'))
_a(LogisticRegression, 'logreg')
_a(SGDClassifier, 'sgdc', ('verbose', 'n_jobs'))
_a(SGDRegressor, 'sgdr', ('verbose',))
_a(Perceptron, 'perceptron', ('verbose', 'n_jobs'))
_a(LinearRegression, 'lr', ('copy_X',))

# SVMs
_a(SVC, 'svc', ('cache_size', 'verbose'))
_a(NuSVC, 'nusvc', ('cache_size', 'verbose'))
_a(LinearSVC, 'linsvc', ('verbose',))
_a(SVR, 'svr', ('cache_size', 'verbose'))
_a(NuSVR, 'nusvr', ('cache_size', 'verbose'))

# NaiveBayes
_a(GaussianNB, 'gnb')
_a(MultinomialNB, 'mnb')
_a(BernoulliNB, 'bnb')

# Decision Trees
_a(DecisionTreeClassifier, 'dtc')
_a(DecisionTreeRegressor, 'dtr')

# Nearest Neighbours
_a(KNeighborsClassifier, 'knc', ('warn_on_equidistant',))
_a(RadiusNeighborsClassifier, 'rnc', ('outlier_label',),
   'outlier_label is questionable, but it won\'t change the model')
_a(KNeighborsRegressor, 'knr', ('warn_on_equidistant',))
_a(RadiusNeighborsRegressor, 'rnr')
_a(NearestCentroid, 'nc')

# Partial Least Squares
_a(PLSRegression, 'plsr', ('copy',))
_a(PLSCanonical, 'plscan', ('copy',))
_a(CCA, 'cca', ('copy',))
_a(PLSSVD, 'plssvd')

# Gaussian Processes
_a(GaussianProcess, 'gp', ('storage_mode', 'verbose'))

# Clusterers
_a(KMeans, None, ('n_jobs', 'copy_x', 'verbose', 'precompute_distances'))
_a(MiniBatchKMeans, None, ('verbose',))
_a(MeanShift, None, ('n_jobs',))
_a(AffinityPropagation, None, ('copy', 'verbose',))
_a(SpectralClustering, None, ())
_a(DBSCAN, None, ())
_a(AgglomerativeClustering, None, ('memory',))
_a(Birch, None, ('compute_labels', 'copy'))
_a(FeatureAgglomeration, None, ('memory',))
_a(SpectralCoclustering, None, ('n_jobs',))
_a(SpectralBiclustering, None, ('n_jobs',))

# Preprocessing
_a(Normalizer, None, ('copy',))
_a(MinMaxScaler, None, ('copy',))

# Pipelines
_a(FeatureUnion, 'f_union', ('n_jobs',))


# Make the invese map: short_name -> long_name
_SKLShort2Long = dict((v.short_name, k) for k, v in _SKLRegistry.items())


# ----- Monkey-patching for whatability


def _what_for_sklearn(x):
    """Returns a What configuration for the scikit learn estimator x."""
    name = x.__class__.__name__
    configuration_dict = x.get_params(deep=False)   # N.B. we take care of recursing ourselves
    pinfo = _SKLRegistry.get(name, None)
    if pinfo is not None:
        return What(pinfo.short_name,
                    conf=configuration_dict,
                    non_id_keys=pinfo.non_id_params)
    return What(name, conf=configuration_dict)


def whatamise_sklearn(check=False, log=False):
    """Monkey-patches sklearn.base.BaseEstimator to make sklearn estimators whatable.

    Parameters
    ----------
    check: boolean, default True
        If True, call check_all_monkeypatched() after getting right BaseEstimator.what
    """
    if not hasattr(BaseEstimator, 'what'):
        BaseEstimator.what = _what_for_sklearn
    if check:
        _check_all_monkeypatched()
    if log:
        print('Scikit-Learn estimators now are whatable')


def _check_all_monkeypatched():
    """Double-checks that instances sklearn estimators have acquired the proper "what" method.
    Raises an assertion error if it is not the case.
    """

    # Make sure we have added what to sklearn stuff
    whatamise_sklearn(check=False)

    # Trick to force python to populate part of the BaseEstimator hierarchy
    from sklearn.ensemble.forest import RandomForestClassifier
    assert BaseEstimator.__subclasscheck__(RandomForestClassifier)
    from sklearn.cluster import KMeans
    assert BaseEstimator.__subclasscheck__(KMeans)
    from sklearn.feature_extraction import DictVectorizer
    assert BaseEstimator.__subclasscheck__(DictVectorizer)
    from sklearn.decomposition import KernelPCA
    assert BaseEstimator.__subclasscheck__(KernelPCA)

    with warnings.catch_warnings():
        warnings.simplefilter('ignore')
        for cls in all_subclasses(BaseEstimator):
            if not inspect.isabstract(cls):
                try:
                    obj = cls()
                    assert hasattr(obj, 'what'), cls.__name__
                    assert isinstance(obj.what(), What), cls.__name__
                except TypeError:
                    pass
    return True


####
#
# Notes:
#  - As usual, when rng (random_state) is a None or a custom rng, identity is not really defined.
#    Maybe we could warn to always use an int random_state when this is detected (in what_for_sklearn).
#
#  - This is too aggressive on patching, but creating a lighter version by getting a plugin to whatareyou
#    that realizes about sklearn classes and applies ignores wisely is very easy to do.
#
####
