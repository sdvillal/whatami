# coding=utf-8
"""Whatable wrappers for scikit learn tools.

Using it is fairly simple and does not require changing anything that is already using sklearn,
but beware that we are monkey-patching sklearn BaseEstimator to add the what method.

Example
-------

>>> # Monkey-patch sklearn estimators
>>> whatamize_sklearn()
>>> # Use what() to retrieve the id of a model
>>> from sklearn.ensemble import RandomForestClassifier
>>> rfc = RandomForestClassifier(n_jobs=8, n_estimators=23)
>>> print(rfc.what().id())
rfc(bootstrap=True,class_weight=None,criterion='gini',max_depth=None,max_features='auto',max_leaf_nodes=None,min_impurity_decrease=0.0,min_impurity_split=None,min_samples_leaf=1,min_samples_split=2,min_weight_fraction_leaf=0.0,n_estimators=23,random_state=None,warm_start=False)
>>> print(rfc.what())
rfc(bootstrap=True,class_weight=None,criterion='gini',max_depth=None,max_features='auto',max_leaf_nodes=None,min_impurity_decrease=0.0,min_impurity_split=None,min_samples_leaf=1,min_samples_split=2,min_weight_fraction_leaf=0.0,n_estimators=23,n_jobs=8,oob_score=False,random_state=None,verbose=0,warm_start=False)


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

See also rendered docs:
  API: http://scikit-learn.org/stable/modules/classes.html
  New glossary: http://scikit-learn.org/dev/glossary.html
"""

# Authors: Santi Villalba <sdvillal@gmail.com>
# Licence: BSD 3 clause

from __future__ import print_function, absolute_import

import inspect
import warnings
import logging
from collections import OrderedDict
from distutils.version import StrictVersion

from sklearn.base import BaseEstimator

from whatami import whatamize_object, obj2what, import_submodules, fqn, maybe_import_member, init_argspec
from whatami.what import What
from whatami.misc import all_subclasses


# ----- Manually check which parameters are not part of the default id (WIP)

_SKLRegistry = OrderedDict()

_WHATAMIZED_BASES = ('sklearn.base.BaseEstimator',
                     'sklearn.gaussian_process.kernels.Kernel',
                     'sklearn.model_selection.BaseCrossValidator',
                     'sklearn.model_selection._split.BaseShuffleSplit',
                     'sklearn.model_selection._split._RepeatedSplits',)


class _ObjectParametersMeta(object):
    """
    Stores information about an object short name, non_id_params, notes and possibly others.

    N.B. it is better to include a non-existing non_id_param
    (innocuous, can help to support several sklearn versions)
    than to leave out existing non_id_params.
    """

    def __init__(self,
                 object_ref,
                 short_name,
                 non_id_params=(),
                 notes=None,
                 group=None,
                 extra=None):
        self.object = object_ref
        self.short_name = short_name if short_name is not None else object_ref.__name__
        self.non_id_params = non_id_params
        self.notes = notes
        self.group = group
        self.extra = extra


def _a(skclass, nickname=None, non_id_params=(), notes=None, override=True):
    """Adds a class to the SKLRegistry."""
    # Maybe we should key using FQNs to avoid any possible name clash
    if not override and skclass.__name__ in _SKLRegistry:  # pragma: no cover
        raise Exception('%r is already in the sklearn registry' % skclass.__name__)
    _SKLRegistry[skclass.__name__] = _ObjectParametersMeta(skclass, nickname, non_id_params, notes)


def _declare0dot15dot1():  # pragma: no cover
    from sklearn.cluster import KMeans, DBSCAN, MeanShift, SpectralClustering, Birch
    from sklearn.cluster.affinity_propagation_ import AffinityPropagation
    from sklearn.cluster.bicluster import SpectralCoclustering, SpectralBiclustering
    from sklearn.cluster.hierarchical import AgglomerativeClustering, FeatureAgglomeration
    from sklearn.cluster.k_means_ import MiniBatchKMeans
    from sklearn.cross_decomposition import PLSRegression, PLSCanonical, CCA, PLSSVD
    from sklearn.ensemble import (RandomForestClassifier, RandomForestRegressor,
                                  ExtraTreesClassifier, ExtraTreesRegressor)
    from sklearn.ensemble.gradient_boosting import GradientBoostingClassifier, GradientBoostingRegressor
    from sklearn.gaussian_process import GaussianProcess
    from sklearn.linear_model import (Ridge, Lasso, ElasticNet, Lars, OrthogonalMatchingPursuit,
                                      BayesianRidge, ARDRegression, LogisticRegression, SGDClassifier,
                                      SGDRegressor, Perceptron, LassoLars, LinearRegression)
    from sklearn.naive_bayes import GaussianNB, MultinomialNB, BernoulliNB
    from sklearn.neighbors import (KNeighborsClassifier, RadiusNeighborsClassifier, KNeighborsRegressor,
                                   RadiusNeighborsRegressor, NearestCentroid)
    from sklearn.pipeline import FeatureUnion
    from sklearn.preprocessing import Normalizer
    from sklearn.preprocessing.data import MinMaxScaler
    from sklearn.svm import SVC, NuSVC, LinearSVC, SVR, NuSVR
    from sklearn.tree import DecisionTreeClassifier, DecisionTreeRegressor

    # Ensembles
    _a(RandomForestClassifier, 'rfc', ('verbose', 'n_jobs', 'oob_score'),
       'oob_score used to change the internal representation of the model (recheck); '
       'warm start is non-id unless we use incremental learning')
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


def _declare0dot19dot1():  # pragma: no cover

    # Calibration
    from sklearn.calibration import CalibratedClassifierCV
    _a(CalibratedClassifierCV)

    # Clusterers
    from sklearn.cluster import (AffinityPropagation, AgglomerativeClustering,
                                 Birch, DBSCAN, FeatureAgglomeration,
                                 KMeans, MiniBatchKMeans, MeanShift,
                                 SpectralClustering, SpectralCoclustering, SpectralBiclustering)
    _a(AffinityPropagation, None, ('copy', 'verbose',))
    _a(AgglomerativeClustering, None, ('memory',))
    _a(Birch, None, ('copy', 'compute_labels'))
    _a(DBSCAN, None, ('n_jobs',))
    _a(FeatureAgglomeration, None, ('memory',))
    _a(KMeans, None, ('copy_x', 'n_jobs', 'precompute_distances', 'verbose'))
    _a(MiniBatchKMeans, None, ('compute_labels', 'verbose'))
    _a(MeanShift, None, ('n_jobs',))
    _a(SpectralClustering, None, ('n_jobs',))
    _a(SpectralCoclustering, None, ('n_jobs',))
    _a(SpectralBiclustering, None, ('n_jobs',))

    # Covariance estimators
    from sklearn.covariance import (EmpiricalCovariance, EllipticEnvelope, GraphLasso, GraphLassoCV,
                                    LedoitWolf, MinCovDet, OAS, ShrunkCovariance)
    _a(EmpiricalCovariance)
    _a(EllipticEnvelope, None, ('store_precision',))
    _a(GraphLasso, None, ('verbose',))
    _a(GraphLassoCV, None, ('n_jobs', 'verbose',))
    _a(LedoitWolf)
    _a(MinCovDet)
    _a(OAS)
    _a(ShrunkCovariance)

    # Cross decomposition
    from sklearn.cross_decomposition import PLSRegression, PLSCanonical, CCA, PLSSVD
    _a(PLSRegression, 'plsr', ('copy',))
    _a(PLSCanonical, 'plscan', ('copy',))
    _a(CCA, 'cca', ('copy',))
    _a(PLSSVD, 'plssvd', ('copy',))

    # Matrix decomposition
    from sklearn.decomposition import (DictionaryLearning, FactorAnalysis, FastICA, IncrementalPCA,
                                       KernelPCA, LatentDirichletAllocation, MiniBatchDictionaryLearning,
                                       MiniBatchSparsePCA, NMF, PCA, SparsePCA, SparseCoder, TruncatedSVD)
    _a(DictionaryLearning, None, ('n_jobs', 'verbose'))
    _a(FactorAnalysis, None, ('copy',))
    _a(FastICA)
    _a(IncrementalPCA, None, ('copy',))
    _a(KernelPCA, None, ('copy_X', 'n_jobs'))
    _a(LatentDirichletAllocation, None, ('n_jobs', 'verbose'))
    _a(MiniBatchDictionaryLearning, None, ('n_jobs', 'verbose'))
    _a(MiniBatchSparsePCA, None, ('callback', 'n_jobs', 'verbose'))
    _a(NMF, None, ('verbose',))
    _a(PCA, None, ('copy',))
    _a(SparsePCA, None, ('n_jobs', 'verbose'))
    _a(SparseCoder, None, ('n_jobs',))
    _a(TruncatedSVD)

    # Discriminant analysis
    from sklearn.discriminant_analysis import LinearDiscriminantAnalysis, QuadraticDiscriminantAnalysis
    _a(LinearDiscriminantAnalysis, None, ('store_covariance',))
    _a(QuadraticDiscriminantAnalysis, None, ('store_covariance',))

    # Dummy Estimators
    from sklearn.dummy import DummyClassifier, DummyRegressor
    _a(DummyClassifier)
    _a(DummyRegressor)

    # Ensembles
    from sklearn.ensemble import (AdaBoostClassifier, AdaBoostRegressor,
                                  BaggingClassifier, BaggingRegressor,
                                  ExtraTreesClassifier, ExtraTreesRegressor,
                                  GradientBoostingClassifier, GradientBoostingRegressor,
                                  IsolationForest,
                                  RandomForestClassifier, RandomForestRegressor, RandomTreesEmbedding,
                                  VotingClassifier)
    _a(AdaBoostClassifier)
    _a(AdaBoostRegressor)
    _a(BaggingClassifier, None, ('n_jobs', 'oob_score', 'verbose'))
    _a(BaggingRegressor, None,  ('n_jobs', 'oob_score', 'verbose'))
    _a(ExtraTreesClassifier, 'etc', ('n_jobs', 'oob_score', 'verbose'))
    _a(ExtraTreesRegressor, 'etr', ('n_jobs', 'oob_score', 'verbose'))
    _a(GradientBoostingClassifier, 'gbc', ('verbose',))
    _a(GradientBoostingRegressor, 'gbr', ('verbose',))
    _a(IsolationForest, None, ('n_jobs', 'verbose'))
    _a(RandomForestClassifier, 'rfc', ('verbose', 'n_jobs', 'oob_score'),
       'oob_score used to change the internal representation of the model (recheck); '
       'warm start is non-id unless we use incremental learning')
    _a(RandomForestRegressor, 'rfr', ('verbose', 'n_jobs', 'oob_score'),
       'Same non-ids as RFC')
    _a(RandomTreesEmbedding, 'rte', ('verbose', 'n_jobs'))
    _a(VotingClassifier, None, ('n_jobs',))

    # Feature extraction
    from sklearn.feature_extraction import DictVectorizer, FeatureHasher
    from sklearn.feature_extraction.image import PatchExtractor
    # noinspection PyProtectedMember
    from sklearn.feature_extraction.text import (CountVectorizer, HashingVectorizer,
                                                 TfidfTransformer, TfidfVectorizer)
    _a(DictVectorizer)
    _a(FeatureHasher)
    _a(PatchExtractor)
    _a(CountVectorizer)
    _a(HashingVectorizer)
    _a(TfidfTransformer)
    _a(TfidfVectorizer)

    # Feature selection
    from sklearn.feature_selection import (GenericUnivariateSelect, SelectPercentile, SelectKBest,
                                           SelectFpr, SelectFdr, SelectFromModel, SelectFwe,
                                           RFE, RFECV, VarianceThreshold)
    _a(GenericUnivariateSelect)
    _a(SelectPercentile)
    _a(SelectKBest)
    _a(SelectFpr)
    _a(SelectFdr)
    _a(SelectFromModel)
    _a(SelectFwe)
    _a(RFE, None, ('verbose',))
    _a(RFECV, None, ('n_jobs', 'verbose'))
    _a(VarianceThreshold)

    # Gaussian processes
    from sklearn.gaussian_process import (GaussianProcessClassifier, GaussianProcessRegressor)
    from sklearn.gaussian_process.kernels import (CompoundKernel, ConstantKernel, DotProduct,
                                                  ExpSineSquared, Exponentiation,
                                                  Matern, PairwiseKernel, Product, RBF,
                                                  RationalQuadratic, Sum, WhiteKernel)
    _a(GaussianProcessClassifier, 'gpc', ('copy_X_train', 'n_jobs'))
    _a(GaussianProcessRegressor, 'gpr', ('copy_X_train',))
    _a(CompoundKernel)
    _a(ConstantKernel)
    _a(DotProduct)
    _a(ExpSineSquared)
    _a(Exponentiation)
    _a(Matern)
    _a(PairwiseKernel)
    _a(Product)
    _a(RBF)
    _a(RationalQuadratic)
    _a(Sum)
    _a(WhiteKernel)

    # Isotonic regression
    from sklearn.isotonic import IsotonicRegression
    _a(IsotonicRegression)

    # Kernel approximation
    from sklearn.kernel_approximation import AdditiveChi2Sampler, Nystroem, RBFSampler, SkewedChi2Sampler
    _a(AdditiveChi2Sampler)
    _a(Nystroem)
    _a(RBFSampler)
    _a(SkewedChi2Sampler)

    # Kernel ridge regression
    from sklearn.kernel_ridge import KernelRidge
    _a(KernelRidge)

    # GLMs
    from sklearn.linear_model import (ARDRegression, BayesianRidge, ElasticNet, ElasticNetCV,
                                      HuberRegressor, Lars, LarsCV, Lasso, LassoCV,
                                      LassoLars, LassoLarsCV, LassoLarsIC,
                                      LinearRegression, LogisticRegression, LogisticRegressionCV,
                                      MultiTaskLasso, MultiTaskElasticNet,
                                      MultiTaskElasticNetCV, MultiTaskLassoCV,
                                      OrthogonalMatchingPursuit, OrthogonalMatchingPursuitCV,
                                      PassiveAggressiveClassifier, PassiveAggressiveRegressor,
                                      Perceptron, RANSACRegressor,
                                      Ridge, RidgeClassifier, RidgeClassifierCV, RidgeCV,
                                      SGDClassifier, SGDRegressor, TheilSenRegressor)
    _a(ARDRegression, 'ardr', ('copy_X', 'verbose'))
    _a(BayesianRidge, 'bayridge', ('copy_X', 'verbose'))
    _a(ElasticNet, 'elnet', ('copy_X',),
       'we need to take care of "precompute" when we pass the Gram matrix, should use a hash of the array')
    _a(ElasticNetCV, 'elnetcv', ('copy_X', 'n_jobs', 'verbose'),
       'we need to take care of "precompute" when we pass the Gram matrix, should use a hash of the array')
    _a(HuberRegressor)
    _a(Lars, 'lars', ('copy_X', 'fit_path', 'verbose'),
       'we need to take care of "precompute" when we pass the Gram matrix, should use a hash of the array')
    _a(LarsCV, 'larscv', ('copy_X', 'fit_path', 'n_jobs', 'verbose'),
       'we need to take care of "precompute" when we pass the Gram matrix, should use a hash of the array')
    _a(Lasso, 'lasso', ('copy_X',),
       'we need to take care of "precompute" when we pass the Gram matrix, should use a hash of the array')
    _a(LassoCV, 'lassocv', ('copy_X', 'n_jobs', 'verbose'),
       'we need to take care of "precompute" when we pass the Gram matrix, should use a hash of the array')
    _a(LassoLars, 'lassolars', ('copy_X', 'fit_path', 'verbose'),
       'we need to take care of "precompute" when we pass the Gram matrix, should use a hash of the array')
    _a(LassoLarsCV, 'lassolarscv', ('copy_X', 'fit_path', 'n_jobs', 'verbose'),
       'we need to take care of "precompute" when we pass the Gram matrix, should use a hash of the array')
    _a(LassoLarsIC, 'lassolarsic', ('copy_X', 'verbose'),
       'we need to take care of "precompute" when we pass the Gram matrix, should use a hash of the array')
    _a(LinearRegression, 'linreg', ('copy_X', 'n_jobs'))
    _a(LogisticRegression, 'logreg', ('n_jobs', 'verbose'))
    _a(LogisticRegressionCV, 'logregcv', ('n_jobs', 'verbose'))
    _a(MultiTaskLasso, None, ('copy_X',))
    _a(MultiTaskLassoCV, None, ('copy_X', 'n_jobs', 'verbose'))
    _a(MultiTaskElasticNet, None, ('copy_X',))
    _a(MultiTaskElasticNetCV, None, ('copy_X', 'n_jobs', 'verbose'))
    _a(OrthogonalMatchingPursuit, 'omp', (),
       'we need to take care of "precompute" when we pass the Gram matrix, should use a hash of the array')
    _a(OrthogonalMatchingPursuitCV, 'ompcv', ('copy', 'n_jobs', 'verbose'),
       'we need to take care of "precompute" when we pass the Gram matrix, should use a hash of the array')
    _a(PassiveAggressiveClassifier, None, ('n_jobs', 'verbose'))
    _a(PassiveAggressiveRegressor, None, ('verbose',))
    _a(Perceptron, 'perceptron', ('n_jobs', 'verbose'))
    _a(RANSACRegressor)
    _a(Ridge, 'ridge', ('copy_X',))
    _a(RidgeClassifier, None, ('copy_X',))
    _a(RidgeClassifierCV)
    _a(RidgeCV)
    _a(SGDClassifier, 'sgdc', ('n_jobs', 'verbose'))
    _a(SGDRegressor, 'sgdr', ('verbose',))
    _a(TheilSenRegressor, None, ('copy_X', 'n_jobs', 'verbose'))

    # Manifold learning
    from sklearn.manifold import Isomap, LocallyLinearEmbedding, MDS, SpectralEmbedding, TSNE
    _a(Isomap, None, ('n_jobs',))
    _a(LocallyLinearEmbedding, None, ('n_jobs', 'neighbors_algorithm'),
       'neighbors algo must go if ever using non-exact')
    _a(MDS, None, ('n_jobs', 'verbose'))
    _a(SpectralEmbedding, None, ('n_jobs',))
    _a(TSNE, None, ('verbose',))

    # GMMs
    from sklearn.mixture import BayesianGaussianMixture, GaussianMixture
    _a(BayesianGaussianMixture, None, ('verbose', 'verbose_interval'))
    _a(GaussianMixture, None, ('verbose', 'verbose_interval'))

    # Model selection
    from sklearn.model_selection import (GroupKFold, GroupShuffleSplit, KFold,
                                         LeaveOneGroupOut, LeavePGroupsOut,
                                         LeaveOneOut, LeavePOut,
                                         PredefinedSplit, RepeatedStratifiedKFold, ShuffleSplit,
                                         StratifiedKFold, StratifiedShuffleSplit, TimeSeriesSplit,
                                         GridSearchCV, RandomizedSearchCV)
    _a(GroupKFold)
    _a(GroupShuffleSplit)
    _a(KFold)
    _a(LeaveOneGroupOut)
    _a(LeavePGroupsOut)
    _a(LeaveOneOut)
    _a(LeavePOut)
    _a(PredefinedSplit)
    _a(RepeatedStratifiedKFold)
    _a(ShuffleSplit)
    _a(StratifiedKFold)
    _a(StratifiedShuffleSplit)
    _a(TimeSeriesSplit)
    _a(GridSearchCV, None, ('error_score', 'n_jobs', 'pre_dispatch', 'refit', 'return_train_score', 'verbose'))
    _a(RandomizedSearchCV, None, ('error_score', 'n_jobs', 'pre_dispatch', 'refit', 'return_train_score', 'verbose'))

    # Multiclass and multilabel classification
    from sklearn.multiclass import OneVsRestClassifier, OneVsOneClassifier, OutputCodeClassifier
    _a(OneVsRestClassifier, None, ('n_jobs',))
    _a(OneVsOneClassifier, None, ('n_jobs',))
    _a(OutputCodeClassifier, None, ('n_jobs',))

    # Multioutput regression and classification
    from sklearn.multioutput import ClassifierChain, MultiOutputClassifier, MultiOutputRegressor
    _a(ClassifierChain)
    _a(MultiOutputClassifier, None, ('n_jobs',))
    _a(MultiOutputRegressor, None, ('n_jobs',))

    # Naive Bayes
    from sklearn.naive_bayes import BernoulliNB, GaussianNB, MultinomialNB
    _a(BernoulliNB, 'bnb')
    _a(GaussianNB, 'gnb')
    _a(MultinomialNB, 'mnb')

    # Nearest Neighbors
    from sklearn.neighbors import (KernelDensity,
                                   KNeighborsClassifier, RadiusNeighborsClassifier,
                                   KNeighborsRegressor, RadiusNeighborsRegressor,
                                   LocalOutlierFactor,
                                   NearestCentroid, NearestNeighbors)
    _a(KernelDensity)
    _a(KNeighborsClassifier, 'knc', ('n_jobs',))
    _a(KNeighborsRegressor, 'knr', ('n_jobs',))
    _a(LocalOutlierFactor, 'lof', ('n_jobs',))
    _a(RadiusNeighborsClassifier, 'rnc')
    _a(RadiusNeighborsRegressor, 'rnr')
    _a(NearestCentroid, 'nc')
    _a(NearestNeighbors, None, ('n_jobs',))

    # Neural network models
    from sklearn.neural_network import BernoulliRBM, MLPClassifier, MLPRegressor
    _a(BernoulliRBM, None, ('verbose',))
    _a(MLPClassifier, None, ('verbose',))
    _a(MLPRegressor, None, ('verbose',))

    # Pipelines
    from sklearn.pipeline import FeatureUnion, Pipeline
    _a(FeatureUnion, None, ('n_jobs',))
    _a(Pipeline, None, ('memory',))

    # Preprocessing and Normalization
    from sklearn.preprocessing import (Binarizer, FunctionTransformer, Imputer,
                                       KernelCenterer, LabelBinarizer, LabelEncoder,
                                       MultiLabelBinarizer, MaxAbsScaler, MinMaxScaler,
                                       Normalizer, OneHotEncoder, PolynomialFeatures,
                                       QuantileTransformer, RobustScaler, StandardScaler)
    _a(Binarizer, None, ('copy',))
    _a(FunctionTransformer)
    _a(Imputer, None, ('copy', 'verbose'))
    _a(KernelCenterer)
    _a(LabelBinarizer)
    _a(LabelEncoder)
    _a(MultiLabelBinarizer)
    _a(MaxAbsScaler, None, ('copy',))
    _a(MinMaxScaler, None, ('copy',))
    _a(Normalizer, None, ('copy',))
    _a(OneHotEncoder)
    _a(PolynomialFeatures)
    _a(QuantileTransformer, None, ('copy',))
    _a(RobustScaler, None, ('copy',))
    _a(StandardScaler, None, ('copy',))

    # Random projections
    from sklearn.random_projection import GaussianRandomProjection, SparseRandomProjection
    _a(GaussianRandomProjection)
    _a(SparseRandomProjection)

    # Semisupervised learning
    from sklearn.semi_supervised import LabelPropagation, LabelSpreading
    _a(LabelPropagation, None, ('n_jobs',))
    _a(LabelSpreading, None, ('n_jobs',))

    # SVMs
    from sklearn.svm import LinearSVC, LinearSVR, NuSVC, NuSVR, OneClassSVM, SVC, SVR
    _a(LinearSVC, 'linsvc', ('verbose',))
    _a(LinearSVR, 'linsvr', ('verbose',))
    _a(NuSVC, 'nusvc', ('cache_size', 'verbose'))
    _a(NuSVR, 'nusvr', ('cache_size', 'verbose'))
    _a(OneClassSVM, 'ocsvm', ('cache_size', 'verbose'))
    _a(SVC, 'svc', ('cache_size', 'verbose'))
    _a(SVR, 'svr', ('cache_size', 'verbose'))

    # Decision Trees
    from sklearn.tree import (DecisionTreeClassifier, DecisionTreeRegressor,
                              ExtraTreeClassifier, ExtraTreeRegressor)
    _a(DecisionTreeClassifier, 'dtc')
    _a(DecisionTreeRegressor, 'dtr')
    _a(ExtraTreeClassifier)
    _a(ExtraTreeRegressor)


def _declare_id_nonid_attributes():
    """Checks scikit version and applies the best matching wrapping function."""

    import sklearn
    sklearn_version = StrictVersion(sklearn.__version__)

    # Versions I have, more or less, manually checked
    supported_versions = sorted((
        (StrictVersion('0.15.1'), _declare0dot15dot1),
        (StrictVersion('0.19.1'), _declare0dot19dot1),
        (StrictVersion('0.19.2'), _declare0dot19dot1),
    ))

    # Choose a version, default to the immediately older explicitly supported
    version = declarator = None
    for version, declarator in supported_versions:
        if version >= sklearn_version:
            break

    # Warn if the version is not explicitly supported
    # We might want to allow being loose / share declarations between versions
    if version != sklearn_version:  # pragma: no cover
        logging.getLogger(__package__).warn('Unsupported sklearn version %r, trying to apply %r' %
                                            (sklearn_version, version))

    # Declare IDs and non ids for several sklearn estimators
    declarator()


# Make the invese map: short_name -> long_name
_SKLShort2Long = dict((v.short_name, k) for k, v in _SKLRegistry.items())


# ----- Monkey-patching for whatability


def _what_for_sklearn(x, use_short=True):
    """Returns a What configuration for the scikit learn estimator x."""
    name = x.__class__.__name__
    pinfo = _SKLRegistry.get(name, None)
    try:
        configuration_dict = x.get_params(deep=False)   # N.B. we take care of recursing ourselves
    except AttributeError:
        return obj2what(x,
                        force_inspect=True,
                        name_override=pinfo.short_name if use_short else name,
                        non_id_keys=pinfo.non_id_params)
    if pinfo is not None:
        return What(pinfo.short_name if use_short else name,
                    conf=configuration_dict,
                    non_id_keys=pinfo.non_id_params)
    return What(name, conf=configuration_dict)


def whatamize_sklearn(check=False, log=False):
    """Monkey-patches sklearn.base.BaseEstimator to make sklearn estimators whatable.

    Parameters
    ----------
    check: boolean, default True
      If True, call check_all_monkeypatched() after getting right BaseEstimator.what

    log: bool, default False
      If True, print success message.
    """
    _declare_id_nonid_attributes()
    # Whatamise all estimators
    whatamize_object(BaseEstimator, _what_for_sklearn, fail_on_import_error=True, force=False)
    # Whatamise a selection of other classes
    for clazz in _WHATAMIZED_BASES:
        whatamize_object(clazz, _what_for_sklearn, fail_on_import_error=False, force=False)
    if check:
        _check_all_monkeypatched()
    if log:
        logging.getLogger(__package__).info('Scikit-Learn estimators now are whatable')


def _check_all_monkeypatched():
    """Double-checks that instances sklearn estimators have acquired the proper "what" method.
    Raises an assertion error if it is not the case.
    """

    # Make sure we have added what to sklearn stuff
    whatamize_sklearn(check=False)

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


def sklearn_parameters_report():

    # Store sklearn version
    import sklearn
    report = {'sklearn_version': sklearn.__version__}

    # Whatamise the library
    whatamize_sklearn()
    whatamized = {}
    for name, meta in _SKLRegistry.items():
        args, varargs, varkw, defaults, required = init_argspec(meta.object)
        whatamized[fqn(meta.object)] = args, varargs, varkw, defaults, required, name, meta

    # Import all from sklearn we can import, so we can find relevant subclasses
    import_submodules('sklearn')

    # Collect subclasess from relevant bases
    all_report = {}
    for base_fqn in _WHATAMIZED_BASES:
        member = maybe_import_member(base_fqn, fail_if_import_error=False)
        if member is not None:
            for subclass in all_subclasses(member):
                args, varargs, varkw, defaults, required = init_argspec(subclass)
                all_report[fqn(subclass)] = args, varargs, varkw, defaults, required, None

    # Do we miss someting?
    report['unwhatamized'] = sorted(set(all_report) - set(whatamized))

    # TODO: store a history of this (maybe pickle) that can help supporting more easily new sklearn versions
    # So report too:
    #   - changes in required parameters
    #   - new parameters
    #   - removed parameters
    #   - changes in parameter default values
    # Plus some automatic way to try to catch errors in my definition of non-id values
    # This is WIP until then

    return report

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
