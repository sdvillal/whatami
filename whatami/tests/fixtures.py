# coding=utf-8
from whatami import whatable, whatareyou
import pytest
from whatami.plugins import has_numpy, has_joblib, has_pandas


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

    @whatable(force_flag_as_whatami=True)
    class C3(object):
        def __init__(self, c1=c1, c2=c2, irrelevant=True):
            super(C3, self).__init__()
            self.c1 = c1
            self.c2 = c2
            self.irrelevant = irrelevant

        def what(self):
            return whatareyou(self, non_id_keys=('irrelevant',))
    return C3()


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
                'fc5d5b43464052efbcd9e88dc0be4afd', '62171fe1114d5d961742dd95e6af37d7'),
        'df2': (pd.DataFrame(data=adjacency, columns=['xx', 'yy', 'zz']),
                'fe226e22261ff56d4cf019aa64942050', '139261e54b3ac2f2e39da6d497f6d0fd'),
        'df3': (pd.DataFrame(data=adjacency.T, columns=['x', 'y', 'z']),
                'f3d11416b1d5cb5da7753991941beb0d', 'fcd984c10ea9379faee471eedafee77b'),
        'df4': (pd.DataFrame(data=adjacency, columns=['x', 'y', 'z'], index=['r1', 'r2', 'r3']),
                '95fc40cb4635424c7ef1577d13183afa', 'c5234b1a362ef13c9c12b7b7444b8c85'),
        's1': (pd.Series(data=adjacency.ravel()),
               'e37122dc5f6320e9f12b413631056443', 'ee9729300f29a6917f30aa9e612ec67c'),
        's2': (pd.Series(data=adjacency.ravel(), index=list(range(len(adjacency.ravel()))))[::-1],
               'c0f4565b063599c6075ec6108cbca344', '74e14992d8587454d561b3194d11a984'),
    }
    return dfs[request.param]
