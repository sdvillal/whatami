# coding=utf-8

# Authors: Santi Villalba <sdvillal@gmail.com>
# Licence: BSD 3 clause

from __future__ import absolute_import
import hashlib

from future.utils import PY3

from ..what import What
from ..whatutils import id2what, what2id
from .fixtures import *


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
    assert what2id(int) == 'int()'  # FIXME correct behavior?
    assert what2id(What(name='me', conf={'x': 1}, out_name='you')) == 'you=me(x=1)'


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
    sha1 = hashlib.sha1(c3id.encode('utf-8')).hexdigest()
    assert config_c3.id(maxlength=1) == sha1


def test_what_str_magic(c1, c2, c3):
    assert str(c1.what()) == "C1(length=1,p1='blah',p2='bleh')"
    assert str(c2.what()) == "C2(c1=C1(length=1,p1='blah',p2='bleh'),name='roxanne')"
    assert str(c3.what()) == "C3(c1=C1(length=1,p1='blah',p2='bleh')," \
                             "c2=C2(c1=C1(length=1,p1='blah',p2='bleh'),name='roxanne'),irrelevant=True)"


def test_what_repr_magic(c1):
    empty_dict_repr = 'set()' if PY3 else 'set([])'
    result = repr(c1.what()).replace("'", "'")
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


def test_list_parameters(c1):
    @whatable
    class WhatableWithList(object):
        def __init__(self):
            self.list = [c1, 'second']
    w = WhatableWithList()
    assert w.what().id() == "WhatableWithList(list=[%s,'second'])" % c1.what().id()
    w.list = []
    assert w.what().id() == "WhatableWithList(list=[])"


def test_string_escape():
    # single quotes inside strings need to be escaped...
    what = What(name='A', conf={'b': "C(d='hey')"})
    assert what.id() == "A(b='C(d=\\'hey\\')')"
    # ...but already escaped quotes should not...
    what = What(name='A', conf={'b': "C(d=\\'hey\\')"})
    assert what.id() == "A(b='C(d=\\'hey\\')')"
    # ...while other escaped chars should be kept...
    what = What(name='A', conf={'b': "C(d=\\'\\they\\')"})
    assert what.id() == "A(b='C(d=\\'\\they\\')')"
    # ...and many consecutive escaped "\" should be handled graciously...
    what = What(name='A', conf={'b': "C(d=\\\'\\they\\')"})
    assert what.id() == "A(b='C(d=\\'\\they\\')')"


def test_what_keys():
    what = What('tom', conf={'a': 3, 'b': 'z', 'c': 3.14}, non_id_keys=['b'])
    assert what.keys() == ['a', 'c']
    assert what.keys(non_ids_too=True) == ['a', 'b', 'c']


def test_what_values():
    what = What('tom', conf={'a': 3, 'b': 'z', 'c': 3.14}, non_id_keys=['b'])
    assert what.values() == [3, 3.14]
    assert what.values(non_ids_too=True) == [3, 'z', 3.14]


def test_what_positional_ids():
    what = What('tom', conf={'a': 3, 'b': 'z', 'c': 3.14}, non_id_keys=['b'], out_name='jerry')
    assert what.positional_id() == 'jerry=tom(3,3.14)'
    assert what.positional_id(non_ids_too=True) == "jerry=tom(3,'z',3.14)"
    what = What('tom', conf={'a': 3, 'b': 'z', 'c': 3.14}, non_id_keys=['b'])
    assert what.positional_id() == 'tom(3,3.14)'
    assert what.positional_id(non_ids_too=True) == "tom(3,'z',3.14)"


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


def test_pandas_plugin(df):

    df, df_hash2, df_hash3 = df
    df_hash = df_hash2 if not PY3 else df_hash3
    name = df.__class__.__name__

    # check for changes in joblib hashing and pandas pickling across versions
    from whatami.plugins import hasher
    assert df_hash == hasher(df)

    # check for proper string generation
    @whatable
    def lpp(adjacency=df):  # pragma: no cover
        return adjacency

    assert lpp.what().id() == "lpp(adjacency=%s(hash='%s'))" % (name, df_hash)


def test_to_dict(c1, c2, c3):
    assert c1.what().to_dict() == {'whatami_conf': {'length': 1, 'p1': 'blah', 'p2': 'bleh'},
                                   'whatami_name': 'C1',
                                   'whatami_out_name': None}
    assert c2.what().to_dict() == {'whatami_conf': {'c1': {'whatami_conf': {'length': 1, 'p1': 'blah', 'p2': 'bleh'},
                                                           'whatami_name': 'C1',
                                                           'whatami_out_name': None},
                                                    'name': 'roxanne'},
                                   'whatami_name': 'C2',
                                   'whatami_out_name': None}

    expected = {'whatami_name': 'C3',
                'whatami_out_name': None,
                'whatami_conf': {'c2': {'whatami_name': 'C2',
                                        'whatami_out_name': None,
                                        'whatami_conf': {'c1': {'whatami_name': 'C1',
                                                                'whatami_out_name': None,
                                                                'whatami_conf': {'p2': 'bleh',
                                                                                 'length': 1,
                                                                                 'p1': 'blah'}},
                                                         'name': 'roxanne'}},
                                 'c1': {'whatami_name': 'C1',
                                        'whatami_out_name': None,
                                        'whatami_conf': {'p2': 'bleh', 'length': 1, 'p1': 'blah'}}}}
    assert c3.what().to_dict() == expected
