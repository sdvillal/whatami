# coding=utf-8
from ..what import whatable, whatareyou
from ..plugins import has_numpy, has_pandas
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
    if not has_numpy():
        return pytest.mark.skipif(test, reason='the numpy plugin requires numpy')
    return test


@pytest.fixture(params=map(numpy_skip, ['a1', 'a2', 'a3', 'a4', 'a5', 'a6', 'a7']),
                ids=['a1', 'a2', 'a3', 'a4', 'a5', 'a6', 'a7'])
def array(request):
    """Hardcodes hashes, so we can detect hashing changes in joblib."""
    from ..plugins import np
    arrays = {
        # base array
        'a1': (np.array([[1, 0, 1], [0, 1, 0], [1, 0, 1]]),
               '6f02029610d8eb28c804bb45e7f9d143', 'cdbda364c2078ca23ec48efc135a4056'),
        # hash changes with dtype
        'a2': (np.array([[1, 0, 1], [0, 1, 0], [1, 0, 1]], dtype=np.bool),
               '84cb98527346d5fcf7883a795b8967e5', '9407c2fc16a7c36b3aeb965ce9ce01ef'),
        'a3': (np.array([[1, 0, 1], [0, 1, 0], [1, 0, 1]], dtype=np.float),
               '94a704b9d7de461139fc94798cca01c5', '2e796b1399e90dac8c8204e0b4ad13dc'),
        # hash changes with shape and ndim
        'a4': (np.array([[1, 0, 1], [0, 1, 0], [1, 0, 1]]).reshape((1, 9)),
               '2d68497a547c11f6ccfb638eac05ce50', '575c139d5e96b6ce189f55f491239006'),
        'a5': (np.array([[1, 0, 1], [0, 1, 0], [1, 0, 1]], ndmin=3),
               'f8912d3c3bad0a81511f30426e9a69b7', '42b6871f9e881b5005e0eef1d96a7fd3'),
        # hash changes with stride/order/contiguity
        'a6': (np.array([[1, 0, 1], [0, 1, 0], [1, 0, 1]], order='F'),
               'ed2bf87a6f657114a742b23ce1d35d8a', '488d258f3e1cbc58d51f1ed0303be2e5'),
        'a7': (np.array([[1, 0, 1], [0, 1, 0], [1, 0, 1]]).T,
               'ed2bf87a6f657114a742b23ce1d35d8a', '488d258f3e1cbc58d51f1ed0303be2e5'),
    }
    return arrays[request.param]


def pandas_skip(test):  # pragma: no cover
    """Skips a test if the pandas plugin is not available."""
    # Check libraries are present
    if not has_pandas():
        return pytest.mark.skipif(test, reason='the pandas plugin requires pandas')
    # Check library versions
    from ..plugins import pd
    from distutils.version import LooseVersion
    minor = LooseVersion(pd.__version__).version[1]
    if minor not in (16, 17, 18):
        return pytest.mark.skipif(test, reason='these tests do not support pandas version %s' % pd.__version__)
    return test


@pytest.fixture(params=map(pandas_skip, ['df1', 'df2', 'df3', 'df4', 's1', 's2']),
                ids=['df1', 'df2', 'df3', 'df4', 's1', 's2'])
def df(request):
    """Hardcodes hashes, so we can detect hashing changes in joblib and pandas serialisation across versions."""
    from ..plugins import pd, np
    from distutils.version import LooseVersion
    adjacency = np.array([[1, 0, 1], [0, 1, 0], [1, 0, 1]])
    dfs = {}
    if LooseVersion('0.16') <= LooseVersion(pd.__version__) < LooseVersion('0.17'):  # pragma: no cover
        dfs = {
            'df1': (pd.DataFrame(data=adjacency, columns=['x', 'y', 'z']),
                    '06b4dd3696595163ee418eb398f12ad4', '86b79ea3b24cce05ec8d027e8e946f41'),
            'df2': (pd.DataFrame(data=adjacency, columns=['xx', 'yy', 'zz']),
                    '65f768a5c45764c2be969fcf067217a8', '4d00fbdb39c6b996412d27c34b2377f2'),
            'df3': (pd.DataFrame(data=adjacency.T, columns=['x', 'y', 'z']),
                    'd657fe3c5db78513015744fd91ef45a9', '238dd9d366d5c247bce4bceeb72513c2'),
            'df4': (pd.DataFrame(data=adjacency, columns=['x', 'y', 'z'], index=['r1', 'r2', 'r3']),
                    '5958e91e3f3d516cd347fadb08eb8d34', 'c5b977fc361c3e7c418841b646b41a7b'),
            's1': (pd.Series(data=adjacency.ravel()),
                   'fb803a8ea8f4defdac3c0c5c19a4d618', 'c24006ddea03888c8e0311a6a163e918'),
            's2': (pd.Series(data=adjacency.ravel(), index=list(range(len(adjacency.ravel()))))[::-1],
                   'f8282784d8ae6f26dd6555a17ecf374a', '117b9a9d74d990b22a303cb5c4e34064'),
        }
    elif LooseVersion('0.17') <= LooseVersion(pd.__version__) < LooseVersion('0.18'):  # pragma: no cover
        dfs = {
            'df1': (pd.DataFrame(data=adjacency, columns=['x', 'y', 'z']),
                    'cfbd33cb950a963f1f69c18040393c57', '213370e5881a6677a16a36ef928e7a2d'),
            'df2': (pd.DataFrame(data=adjacency, columns=['xx', 'yy', 'zz']),
                    '4deccdb1a2e05b76f66d75747bd59d87', '69b9b1d16e798228ea7ae4d1a66644b4'),
            'df3': (pd.DataFrame(data=adjacency.T, columns=['x', 'y', 'z']),
                    'acdc2d8ab2cf74b7cb9228f7c821543b', '0147d912cb628a67bd4a7755534989cd'),
            'df4': (pd.DataFrame(data=adjacency, columns=['x', 'y', 'z'], index=['r1', 'r2', 'r3']),
                    'bb369093d962c1102737f556448e0a4c', '06816343ea060281009194d31970e1d8'),
            's1': (pd.Series(data=adjacency.ravel()),
                   'f7aa3fa9cb0e83c0bc4bc8c6946db39f', '282e928e7af9a28e4a4a487d8b3aace2'),
            's2': (pd.Series(data=adjacency.ravel(), index=list(range(len(adjacency.ravel()))))[::-1],
                   '3e906bba8938fc47b10babf0abcd9c7c', '015f8cf4282495f03bdd185901fe67a0'),
        }
    elif LooseVersion('0.18') <= LooseVersion(pd.__version__) < LooseVersion('0.19'):  # pragma: no cover
        dfs = {
            'df1': (pd.DataFrame(data=adjacency, columns=['x', 'y', 'z']),
                    'b42c35390383ea16e6cbdd386a650352', '7133178ca4922a7ed8b17c8cc9b7c6c2'),
            'df2': (pd.DataFrame(data=adjacency, columns=['xx', 'yy', 'zz']),
                    'c7634ccb336070327fcb72237010a132', '20759a616b21a050c7edfabb7f8d3197'),
            'df3': (pd.DataFrame(data=adjacency.T, columns=['x', 'y', 'z']),
                    '111429cc6780467d5f1360ac080413b8', '74680aa0ba883e3df7f370708641df3b'),
            'df4': (pd.DataFrame(data=adjacency, columns=['x', 'y', 'z'], index=['r1', 'r2', 'r3']),
                    '771739ab3741e83d4058092c3e7048fa', '41c3285396a6a23eecf5170bd4d05089'),
            's1': (pd.Series(data=adjacency.ravel()),
                   '2b0e7e414f6cbf83df534c715f307b25', '4273d3625a0b2f4374aef2405e144d81'),
            's2': (pd.Series(data=adjacency.ravel(), index=list(range(len(adjacency.ravel()))))[::-1],
                   '43dbf2ae18abdf54921ea1a49e8d847b', '50052bba6794aceab461a1f2a1baa785'),
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
