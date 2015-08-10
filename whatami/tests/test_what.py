# coding=utf-8

# Authors: Santi Villalba <sdvillal@gmail.com>
# Licence: BSD 3 clause

from __future__ import unicode_literals, absolute_import
from functools import partial
import hashlib

from future.utils import PY3
import pytest

from whatami import whatable, whatareyou, What, id2what
from whatami.plugins import has_joblib, has_numpy, has_pandas
from whatami.whatutils import what2id


# --- Fixtures

@pytest.fixture
def c1():
    """A simple whatable object."""
    @whatable
    class C1(object):
        def __init__(self, p1='blah', p2='bleh', length=1):
            super(C1, self).__init__()
            self.p1 = p1
            self.p2 = p2
            self.length = length
            self._p1p2 = p1 + p2
            self.p2p1_ = p2 + p1
    return C1()


@pytest.fixture
def c2(c1):
    """A whatable object with a nested whatable."""
    @whatable
    class C2(object):
        def __init__(self, name='roxanne', c1=c1):
            super(C2, self).__init__()
            self.name = name
            self.c1 = c1
    return C2()


@pytest.fixture
def c3(c1, c2):
    """A whatable object with nested whatables and irrelevant members."""

    class C3(object):
        def __init__(self, c1=c1, c2=c2, irrelevant=True):
            super(C3, self).__init__()
            self.c1 = c1
            self.c2 = c2
            self.irrelevant = irrelevant

        @whatable(force_flag_as_whatami=True)
        def what(self):
            return whatareyou(self, non_id_keys=('irrelevant',))
    return C3()


def test_configuration_nonids():

    # Non-ids
    c1 = What('tc',
              {'p1': 1, 'p2': 2, 'p3': 3, 'verbose': True, 'n_jobs': None},
              non_id_keys=('verbose', 'n_jobs'))
    assert c1.id() == 'tc(p1=1,p2=2,p3=3)'
    assert c1.id(nonids_too=True) == 'tc(n_jobs=None,p1=1,p2=2,p3=3,verbose=True)'

    with pytest.raises(Exception) as excinfo:
        What('tc',
             {'p1': 1, 'p2': 2, 'p3': 3, 'verbose': True, 'n_jobs': None},
             non_id_keys=str)
    assert str(excinfo.value) == 'non_ids must be None or an iterable'


def test_whatid():
    assert what2id(None) is None
    assert what2id('Myself') == 'Myself'
    assert what2id(int) == 'int()'  # correct behavior?


def test_non_id_keys(c3):
    # non-id keys
    config_c3 = c3.what()
    assert config_c3.id() == "C3(c1=C1(length=1,p1='blah',p2='bleh')," \
                             "c2=C2(c1=C1(length=1,p1='blah',p2='bleh'),name='roxanne'))"
    assert config_c3.id(nonids_too=True) == "C3(c1=C1(length=1,p1='blah',p2='bleh')," \
                                            "c2=C2(c1=C1(length=1,p1='blah',p2='bleh'),name='roxanne')," \
                                            "irrelevant=True)"
    c3id = "C3(c1=C1(length=1,p1='blah',p2='bleh'),c2=C2(c1=C1(length=1,p1='blah',p2='bleh'),name='roxanne'))"
    assert config_c3.id(nonids_too=False) == c3id
    sha2 = hashlib.sha256(c3id.encode('utf-8')).hexdigest()
    assert config_c3.id(maxlength=1) == sha2


def test_what_str_magic(c1, c2, c3):
    assert str(c1.what()) == "C1(length=1,p1='blah',p2='bleh')"
    assert str(c2.what()) == "C2(c1=C1(length=1,p1='blah',p2='bleh'),name='roxanne')"
    assert str(c3.what()) == "C3(c1=C1(length=1,p1='blah',p2='bleh')," \
                             "c2=C2(c1=C1(length=1,p1='blah',p2='bleh'),name='roxanne'),irrelevant=True)"


def test_what_repr_magic(c1):
    empty_dict_repr = 'set()' if PY3 else 'set([])'
    result = repr(c1.what()).replace("u'", "'")
    assert "What('C1', {" in result
    assert "'p2': 'bleh'" in result
    assert "'length': 1" in result
    assert "'p1': 'blah'" in result
    assert ("}, " + empty_dict_repr) in result
    # tests with c2 and c3 will fail because of pytest magic, rewrite without fixtures


def test_what_getitem_magic(c1, c2, c3):
    assert c1.what()['length'] == 1
    assert c1.what()['p1'] == 'blah'
    assert c2.what()['c1', 'p1'] == 'blah'
    assert c3.what()['c2', 'c1', 'p1'] == 'blah'
    with pytest.raises(KeyError):
        assert c1.what()['not_there']


def test_what_eq_magic(c1, c2, c3):
    assert c1.what() == c1.what()
    assert c1.what() != c2.what()
    assert c1.what() != c3.what()
    assert c2.what() == c2.what()
    assert c2.what() != c1.what()
    assert c2.what() != c3.what()
    assert c3.what() == c3.what()
    assert c3.what() != c1.what()
    assert c3.what() != c2.what()


def test_whatable_functions(c1):
    def identity(x):
        return x

    # Functions
    c1.p1 = identity
    assert c1.what().id() == "C1(length=1,p1=identity(),p2='bleh')"
    assert c1.p1(1) == 1


def test_whatable_decorator():
    @whatable
    def normalize(x, loc=5, scale=3):
        """returns (x+loc) / scale"""
        return (x + loc) / scale
    assert normalize.what().id() == 'normalize(loc=5,scale=3)'
    assert normalize.__name__ == 'normalize'
    assert normalize.__doc__ == 'returns (x+loc) / scale'

    # very specific case: partial application over a whatable closure
    normalize6 = partial(normalize, loc=6)
    assert not hasattr(normalize6, 'what')
    assert not hasattr(normalize6, '__name__')  # partials have no name
    normalize6 = whatable(normalize6)
    assert normalize6.what().id() == 'normalize(loc=6,scale=3)'
    assert normalize6(3) == 3


def test_list_parameters(c1):
    @whatable
    class WhatableWithList(object):
        def __init__(self):
            self.list = [c1, 'second']
    w = WhatableWithList()
    assert w.what().id() == "WhatableWithList(list=[%s,'second'])" % c1.what().id()
    w.list = []
    assert w.what().id() == "WhatableWithList(list=[])"


def test_tuple_parameters(c1):
    @whatable
    class WhatableWithTuple(object):
        def __init__(self):
            self.tuple = ('first', c1)
    w = WhatableWithTuple()
    assert w.what().id() == "WhatableWithTuple(tuple=('first',%s))" % c1.what().id()
    w.tuple = ()
    assert w.what().id() == "WhatableWithTuple(tuple=())"


def test_dict_parameters(c1):
    @whatable
    class WhatableWithDict(object):
        def __init__(self):
            self.dict = {'c1': c1, 'two': 2}
    w = WhatableWithDict()
    assert w.what().id() == "WhatableWithDict(dict={'c1':C1(length=1,p1='blah',p2='bleh'),'two':2})"
    w.dict = {}
    assert w.what().id() == "WhatableWithDict(dict={})"


def test_set_parameters(c1):
    @whatable
    class WhatableWithSet(object):
        def __init__(self):
            self.set = {c1, 2}
    w = WhatableWithSet()
    assert w.what().id() == "WhatableWithSet(set={2,C1(length=1,p1='blah',p2='bleh')})"
    # whatables must have no memory of configuration
    w.set = set()
    assert w.what().id() == "WhatableWithSet(set=set())"


def test_lamda_id():

    def norm(x, y=3, normal=lambda x, ly=33: x + ly):  # pragma: no cover
        return normal(x) * x + y

    assert what2id(norm) == 'norm(normal=lambda(ly=33),y=3)'
    assert id2what(what2id(norm)) == What('norm', {'normal': What('lambda', {'ly': 33}), 'y': 3})


def test_what_copy(c1, c2, c3):
    for c in (c1, c2, c3):
        what = c.what()
        assert what == what.copy()


def numpy_skip(test):  # pragma: no cover
    """Skips a test if the numpy plugin is not available."""
    if not (has_numpy() and has_joblib()):
        return pytest.mark.skipif(test, reason='the numpy plugin requires both pandas and joblib')
    return test


@pytest.fixture(params=map(numpy_skip, ['a1', 'a2', 'a3', 'a4', 'a5', 'a6', 'a7']),
                ids=['a1', 'a2', 'a3', 'a4', 'a5', 'a6', 'a7'])
def array(request):
    """Hardcodes hashes, so we can detect hashing changes in joblib."""
    from whatami.plugins import np
    arrays = {
        # base array
        'a1': (np.array([[1, 0, 1], [0, 1, 0], [1, 0, 1]]),
               'a6bb4681650ec50fce0123412a78753e', 'cbded866f66a0fa6767b4e286c3552df'),
        # hash changes with dtype
        'a2': (np.array([[1, 0, 1], [0, 1, 0], [1, 0, 1]], dtype=np.bool),
               '82fe62950379505b6581df73d5a5bf2d', '5118dfbd9491eab8ce757c49b6fd06df'),
        'a3': (np.array([[1, 0, 1], [0, 1, 0], [1, 0, 1]], dtype=np.float),
               '1b5b918e0bae98539bb7aa886c791548', '7149c69cf4a5f85bd49e92496d5d2cb8'),
        # hash changes with shape and ndim
        'a4': (np.array([[1, 0, 1], [0, 1, 0], [1, 0, 1]]).reshape((1, 9)),
               'bc2afdb8b2d4ac89b5718105c554921b', '37c27fea094cf3eddf4b11e602955c2a'),
        'a5': (np.array([[1, 0, 1], [0, 1, 0], [1, 0, 1]], ndmin=3),
               '657a4d5a3a3e2190e21d1a06772b90fc', '33d23b13c6a0d41d9b6273ff4962f6c9'),
        # hash changes with stride/order/contiguity
        'a6': (np.array([[1, 0, 1], [0, 1, 0], [1, 0, 1]], order='F'),
               'fddb29315104f69723750835086584bf', '6465c08894edcc3d0d122b2fd0acb68f'),
        'a7': (np.array([[1, 0, 1], [0, 1, 0], [1, 0, 1]]).T,
               'fddb29315104f69723750835086584bf', '6465c08894edcc3d0d122b2fd0acb68f'),
    }
    return arrays[request.param]


def test_numpy_plugin(array):

    array, array_hash2, array_hash3 = array
    array_hash = array_hash2 if not PY3 else array_hash3

    # joblib hash has changed?
    from whatami.plugins import hasher
    assert array_hash == hasher(array)

    @whatable
    def lpp(adjacency=array):  # pragma: no cover
        return adjacency

    assert lpp.what().id() == "lpp(adjacency=ndarray(hash='%s'))" % array_hash


def pandas_skip(test):  # pragma: no cover
    """Skips a test if the pandas plugin is not available."""
    if not (has_pandas() and has_joblib()):
        return pytest.mark.skipif(test, reason='the pandas plugin requires both pandas and joblib')
    return test


@pytest.fixture(params=map(pandas_skip, ['df1', 'df2', 'df3', 'df4', 's1', 's2']),
                ids=['df1', 'df2', 'df3', 'df4', 's1', 's2'])
def df(request):
    """Hardcodes hashes, so we can detect hashing changes in joblib."""
    from whatami.plugins import pd, np
    adjacency = np.array([[1, 0, 1], [0, 1, 0], [1, 0, 1]])
    dfs = {
        'df1': (pd.DataFrame(data=adjacency, columns=['x', 'y', 'z']),
                'd6ac6db11e51f8991b8ad741bdee6edb', '62171fe1114d5d961742dd95e6af37d7'),
        'df2': (pd.DataFrame(data=adjacency, columns=['xx', 'yy', 'zz']),
                'ef6fc324c5d710f14ef15be4733223df', '139261e54b3ac2f2e39da6d497f6d0fd'),
        'df3': (pd.DataFrame(data=adjacency.T, columns=['x', 'y', 'z']),
                '0ea43fc0b4e99c9e3477d0c82ade7260', 'fcd984c10ea9379faee471eedafee77b'),
        'df4': (pd.DataFrame(data=adjacency, columns=['x', 'y', 'z'], index=['r1', 'r2', 'r3']),
                'bb144c7abab7e2323c8882f0b6f129b7', 'c5234b1a362ef13c9c12b7b7444b8c85'),
        's1': (pd.Series(data=adjacency.ravel()),
               'e37122dc5f6320e9f12b413631056443', 'ee9729300f29a6917f30aa9e612ec67c'),
        's2': (pd.Series(data=adjacency.ravel(), index=list(range(len(adjacency.ravel()))))[::-1],
               'c0f4565b063599c6075ec6108cbca344', '74e14992d8587454d561b3194d11a984'),
    }
    return dfs[request.param]


def test_pandas_plugin(df):

    df, df_hash2, df_hash3 = df
    df_hash = df_hash2 if not PY3 else df_hash3
    name = df.__class__.__name__

    # check for changes in joblib hashing
    from whatami.plugins import hasher
    assert df_hash == hasher(df)

    # check for proper string generation
    @whatable
    def lpp(adjacency=df):  # pragma: no cover
        return adjacency

    assert lpp.what().id() == "lpp(adjacency=%s(hash='%s'))" % (name, df_hash)
