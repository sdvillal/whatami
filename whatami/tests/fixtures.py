# coding=utf-8
from ..what import whatable, whatareyou
from ..plugins import has_numpy, has_joblib, has_pandas
import pytest


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
        return pytest.mark.skipif(test, reason='the numpy plugin requires both numpy and joblib')
    return test


@pytest.fixture(params=map(numpy_skip, ['a1', 'a2', 'a3', 'a4', 'a5', 'a6', 'a7']),
                ids=['a1', 'a2', 'a3', 'a4', 'a5', 'a6', 'a7'])
def array(request):
    """Hardcodes hashes, so we can detect hashing changes in joblib."""
    from ..plugins import np
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
    # Check libraries are present
    if not (has_pandas() and has_joblib()):
        return pytest.mark.skipif(test, reason='the pandas plugin requires both pandas and joblib')
    # Check library versions
    from ..plugins import pd
    from distutils.version import LooseVersion
    minor = LooseVersion(pd.__version__).version[1]
    if minor not in (16, 17):
        return pytest.mark.skipif(test, reason='these tests do not support pandas version %s' % pd.__version__)
    return test


@pytest.fixture(params=map(pandas_skip, ['df1', 'df2', 'df3', 'df4', 's1', 's2']),
                ids=['df1', 'df2', 'df3', 'df4', 's1', 's2'])
def df(request):
    """Hardcodes hashes, so we can detect hashing changes in joblib."""
    from ..plugins import pd, np
    from distutils.version import LooseVersion
    adjacency = np.array([[1, 0, 1], [0, 1, 0], [1, 0, 1]])
    dfs = {}
    if LooseVersion('0.16') <= LooseVersion(pd.__version__) < LooseVersion('0.17'):  # pragma: no cover
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
    elif LooseVersion('0.17') <= LooseVersion(pd.__version__) < LooseVersion('0.18'):  # pragma: no cover
        dfs = {
            'df1': (pd.DataFrame(data=adjacency, columns=['x', 'y', 'z']),
                    '4e3bd601694d810b122afcaa03dc8657', '4e170e720983e95acf9f3dc236aad281'),
            'df2': (pd.DataFrame(data=adjacency, columns=['xx', 'yy', 'zz']),
                    'bed8e94e953d1a69b6b10f122db9d768', 'd37e44c3ea7562be9256435ec925080a'),
            'df3': (pd.DataFrame(data=adjacency.T, columns=['x', 'y', 'z']),
                    'b5a2fa63a034eff697e95eb4f849ba38', 'f5bf82a7647a0789b1714e503cad7d7a'),
            'df4': (pd.DataFrame(data=adjacency, columns=['x', 'y', 'z'], index=['r1', 'r2', 'r3']),
                    '6a24c46e973fe74b208b13f74435b041', 'b7747e3d4bbd4477698037eb9d933282'),
            's1': (pd.Series(data=adjacency.ravel()),
                   'd5dc5e9943d1b74f604a99dd74e8d034', '6e62c2340b898886512176c20011fab6'),
            's2': (pd.Series(data=adjacency.ravel(), index=list(range(len(adjacency.ravel()))))[::-1],
                   'd8ec7deecaca6a0a42a2c9967e2beba6', '1f6fc6f831e48c59868f1e0157df79c5'),
        }
    return dfs[request.param]


@pytest.fixture(params=map(pandas_skip, ['dfw1']),
                ids=['dfw1'])
def df_with_whatid(request):
    """Fixtures to test whatid manipulations mixed with pandas dataframes.

    Provides dataframes with:
      - A column "whatid" with the whatami ids
      - The rest of the columns must be the expectations for the extracted values, named as:
        - key: for top level keys
        - key1_key2_key3: for recursive keys
    """
    from ..plugins import pd
    if request.param == 'dfw1':
        whatids = [
            "Blosc(cname='blosclz',level=5,shuffle=False)",
            "Blosc(cname='blosclz',level=6,shuffle=True)",
            "Blosc(cname='lz4hc',level=7,shuffle=True)",
            "Blosc(cname='lz4hc',level=8,shuffle=False)",
            "C2(c1=C1(length=1,p1='blah',p2='bleh'),name='roxanne')",
        ] * 4
        cnames = ['blosclz', 'blosclz', 'lz4hc', 'lz4hc', None] * 4
        levels = [5, 6, 7, 8, None] * 4
        shuffles = [False, True, True, False, None] * 4
        c1_lengths = [None, None, None, None, 1] * 4
        df = pd.DataFrame({'whatid': whatids,
                           'cname': cnames,
                           'level': levels,
                           'shuffle': shuffles,
                           'c1_length': c1_lengths})
        return df
    else:  # pragma: no cover
        raise ValueError('Unknown fixture %s' % request.param)
