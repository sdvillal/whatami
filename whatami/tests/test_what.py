# coding=utf-8

# Authors: Santi Villalba <sdvillal@gmail.com>
# Licence: BSD 3 clause

from __future__ import unicode_literals, absolute_import
from functools import partial
import hashlib
from future.utils import PY3

import pytest

from whatami import whatable, whatareyou, What, is_whatable
from whatami.whatutils import what2id
from whatami.misc import config_dict_for_object, trim_dict


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


def test_whatable_simple(c1):
    # Non-nested configurations
    config_c1 = c1.what()
    assert config_c1.name == 'C1'
    assert len(config_c1.conf) == 3
    assert config_c1.conf['p1'] == 'blah'
    assert config_c1.conf['p2'] == 'bleh'
    assert config_c1.conf['length'] == 1
    assert config_c1 == config_c1
    assert config_c1.id() == "C1(length=1,p1='blah',p2='bleh')"


def test_nested_whatables(c1, c2):
    # Nested whatables
    config_c2 = c2.what()
    assert config_c2.name == 'C2'
    assert len(config_c2.conf) == 2
    assert config_c2.conf['name'] == 'roxanne'
    assert config_c2.conf['c1'].what() == c1.what()
    assert config_c2.id() == "C2(c1=C1(length=1,p1='blah',p2='bleh'),name='roxanne')"
    c2.c1 = c1.what()
    config_c2 = c2.what()
    assert config_c2.id() == "C2(c1=C1(length=1,p1='blah',p2='bleh'),name='roxanne')"


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


def test_whatable_partial(c1):

    def identity(x):
        return x

    # Partial functions
    c1.p1 = partial(identity, x=1)
    assert c1.what().id() == "C1(length=1,p1=identity(x=1),p2='bleh')"
    assert c1.p1() == 1


def test_whatable_builtins(c1):
    # Builtins - or whatever foreigner - do not allow introspection
    c1.p1 = sorted
    with pytest.raises(Exception) as excinfo:
        c1.what().id()
    assert str(excinfo.value) == 'Cannot determine the argspec of a non-python function (sorted). ' \
                                 'Please wrap it in a whatable'


def test_whatable_anyobject(c1):

    # Objects without proper representation
    class RandomClass(object):
        def __init__(self):
            self.param = 'yes'
    c1.p1 = RandomClass()
    assert c1.what().id() == "C1(length=1,p1=RandomClass(param='yes'),p2='bleh')"


def test_whatable_force_flag():
    @whatable(force_flag_as_whatami=True)
    class A(object):

        def __init__(self):
            super(A, self).__init__()
            self.a = 3

        def what(self):
            return whatareyou(self)

    assert is_whatable(A)
    assert is_whatable(A())
    assert A().what().id() == 'A(a=3)'


def test_whatable_data_descriptors():

    # Objects with @properties
    class ClassWithProps(object):
        def __init__(self):
            self._prop = 3

        @property
        def prop(self):
            return self._prop

        def what(self):
            return What(self.__class__.__name__,
                        trim_dict(config_dict_for_object(self, add_properties=True)))

    cp = ClassWithProps()
    assert cp.what().id() == 'ClassWithProps(prop=3)'

    # Objects with dynamically added properties
    setattr(cp, 'dprop', property(lambda: 5))
    with pytest.raises(Exception) as excinfo:
        cp.what().id()
    assert str(excinfo.value) == 'Dynamic properties are not suppported.'


def test_is_whatable(c1):
    assert is_whatable(c1)
    assert not is_whatable(str)


def test_whatable_custom_func():

    def whatfunc(obj):  # pragma: no cover
        return What('custom', conf={'n_trees': None, 'original': obj.__name__})

    def rfc(n_trees=30):  # pragma: no cover
        return n_trees

    assert whatable(rfc).what().id() == 'rfc(n_trees=30)'
    assert whatable(rfc, whatfunc=whatfunc).what().id() == 'custom(n_trees=None,original=\'rfc\')'


@pytest.mark.xfail(reason='fix infinite recursion')
def test_whatable_custom_func_recursive():

    def whatfunc(obj):  # pragma: no cover
        return What('custom', conf={'n_trees': None, 'original': obj})

    def rfc(n_trees=30):  # pragma: no cover
        return n_trees

    assert whatable(rfc).what().id() == 'rfc(n_trees=30)'
    assert whatable(rfc, whatfunc=whatfunc).what().id() == 'custom(n_trees=None,original=rfc(n_trees=30))'


def test_whatable_slots():

    # N.B. Slots are implemented as descriptors
    @whatable
    class Slots(object):
        __slots__ = ['prop']

        def __init__(self):
            self.prop = 3

    slots = Slots()
    assert slots.what().id() == 'Slots(prop=3)'


def test_whatable_inheritance():

    # Inheritance works as spected
    @whatable
    class Super(object):
        def __init__(self):
            super(Super, self).__init__()
            self.a = 'superA'
            self.b = 'superB'

    class Sub(Super):
        def __init__(self):
            super(Sub, self).__init__()
            self.c = 'subC'
            self.a = 'subA'

    assert Sub().what().id() == "Sub(a='subA',b='superB',c='subC')"


def test_whatable_does_not_override_what(c1):
    c1.what = 33
    assert not is_whatable(c1)
    with pytest.raises(Exception) as excinfo:
        whatable(c1)
    assert str(excinfo.value) == 'object already has an attribute what, and is not a whatami what, ' \
                                 'if you know what I mean'


def test_whatable_torturing_inheritance():

    class D1(object):

        def __init__(self):
            self.d1 = 1

    class S1(D1):
        __slots__ = 's1'

        def __init__(self):
            super(S1, self).__init__()
            self.s1 = 2

    class S2(S1):
        __slots__ = 's2'

        def __init__(self):
            super(S2, self).__init__()
            self.s2 = 3

    class D2(S2):

        def __init__(self):
            super(D2, self).__init__()
            self.d2 = 4

    class P1(D2):

        def __init__(self):
            super(P1, self).__init__()

        @property
        def p1(self):
            return 5

    class S3(P1):
        __slots__ = 's3'

        def __init__(self):
            super(S3, self).__init__()
            self.s3 = 6

    s3 = S3()

    s3 = whatable(s3, add_dict=True, add_slots=True, add_properties=True)
    assert s3.what().id() == "S3(d1=1,d2=4,p1=5,s1=2,s2=3,s3=6)"

    s3 = whatable(s3, add_dict=True, add_slots=True, add_properties=False)
    assert s3.what().id() == "S3(d1=1,d2=4,s1=2,s2=3,s3=6)"

    s3 = whatable(s3, add_dict=True, add_slots=False, add_properties=True)
    assert s3.what().id() == "S3(d1=1,d2=4,p1=5)"

    s3 = whatable(s3, add_dict=True, add_slots=False, add_properties=False)
    assert s3.what().id() == "S3(d1=1,d2=4)"

    s3 = whatable(s3, add_dict=False, add_slots=False, add_properties=False)
    assert s3.what().id() == "S3()"

    s3 = whatable(s3, add_dict=False, add_slots=True, add_properties=False)
    assert s3.what().id() == "S3(s1=2,s2=3,s3=6)"

    s3 = whatable(s3, add_dict=False, add_slots=False, add_properties=True)
    assert s3.what().id() == "S3(p1=5)"

    s3 = whatable(s3, add_dict=False, add_slots=True, add_properties=True)
    assert s3.what().id() == "S3(p1=5,s1=2,s2=3,s3=6)"


def test_whatable_duck():

    class DuckedWhatable(object):
        def what(self):
            return What(self.__class__.__name__, {'param1': 33})
    cduck = DuckedWhatable()
    assert cduck.what().id() == 'DuckedWhatable(param1=33)'

    @whatable
    class NestedDuckedWhatable(object):
        def __init__(self):
            super(NestedDuckedWhatable, self).__init__()
            self.ducked = cduck
    nested_duck = NestedDuckedWhatable()
    assert nested_duck.what().id() == 'NestedDuckedWhatable(ducked=DuckedWhatable(param1=33))'


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


def test_whatable_builtin():
    with pytest.raises(TypeError) as excinfo:
        whatable(all)
    assert 'builtins cannot be whatamised' in str(excinfo.value)

    with pytest.raises(Exception) as excinfo:
        whatable(str)
    assert 'cannot whatamise' in str(excinfo.value)


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


def test_whatable_faker():

    class Faker(object):
        def what(self):
            return 'fool you: %r' % self

    @whatable
    class Fool(object):
        def __init__(self):
            self.faker = Faker()

    with pytest.raises(Exception) as excinfo:
        whatareyou(Fool()).id()
    assert 'object has a "what" attribute, but it is not of What class' in str(excinfo.value)


def test_what_copy(c1, c2, c3):
    for c in (c1, c2, c3):
        what = c.what()
        assert what == what.copy()
