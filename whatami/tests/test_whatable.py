# coding=utf-8
from functools import partial

import pickle

from ..what import is_whatable, What, trim_dict, config_dict_for_object
from ..whatutils import what2id
from .fixtures import *
from whatami.plugins import WhatamiPluginManager, anyobject0x_plugin, anyobject_plugin


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


def test_whatable_partial(c1):

    def identity(x):
        return x

    # Partial functions
    c1.p1 = partial(identity, x=1)
    assert c1.what().id() == "C1(length=1,p1=identity(x=1),p2='bleh')"
    assert c1.p1() == 1


def test_whatable_recursive_partials():

    def f0(x, y=3, z=12):
        return x + y + z

    # Just the function
    assert what2id(f0) == 'f0(y=3,z=12)'
    assert whatable(f0).what().id() == 'f0(y=3,z=12)'

    # A partial with a lambda
    f2 = partial(f0, x=lambda x: x**2)
    assert what2id(f2) == 'f0(x=lambda(),y=3,z=12)'
    assert whatable(f2).what().id() == 'f0(x=lambda(),y=3,z=12)'

    # A partial with a partial
    f1 = partial(f0, x=partial(f0, x=2))
    assert what2id(f1) == 'f0(x=f0(x=2,y=3,z=12),y=3,z=12)'
    assert whatable(f1).what().id() == 'f0(x=f0(x=2,y=3,z=12),y=3,z=12)'

    # A partial with a partial with a partial
    f3 = partial(f0, x=partial(f0, x=partial(f0, x=None)))
    assert what2id(f3) == 'f0(x=f0(x=f0(x=None,y=3,z=12),y=3,z=12),y=3,z=12)'
    assert whatable(f3).what().id() == 'f0(x=f0(x=f0(x=None,y=3,z=12),y=3,z=12),y=3,z=12)'


def test_whatable_builtins(c1):
    # Builtins - or whatever foreigner - do not allow introspection
    c1.p1 = sorted
    with pytest.raises(Exception) as excinfo:
        c1.what().id()
    assert str(excinfo.value) == 'Cannot determine the argspec of a non-python function (sorted). ' \
                                 'Please wrap it in a whatable'


def test_whatable_anyobject(c1):

    # Objects without proper representation - default
    class RandomClass(object):
        def __init__(self):
            self.param = 'yes'
    c1.p1 = RandomClass()
    assert c1.what().id() == "C1(length=1,p1=RandomClass(),p2='bleh')"

    # Objects without proper representation - deep introspection
    WhatamiPluginManager.drop(anyobject0x_plugin)
    WhatamiPluginManager.insert(partial(anyobject0x_plugin, deep=True), before=anyobject_plugin)
    assert c1.what().id() == "C1(length=1,p1=RandomClass(param='yes'),p2='bleh')"
    WhatamiPluginManager.reset()

    # Making the object whatable
    c1.p1 = whatable(RandomClass())
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


def test_whatable_class_members():

    @whatable(add_class=True)
    class C(object):
        x = 1
        y = 33

    class D(C):
        z = 'z'

    class E(D):
        x = 'x'

    c = C()
    assert c.what().id() == 'C(x=1,y=33)'
    c.y = 'y'
    assert c.what().id() == "C(x=1,y='y')"
    assert D().what().id() == "D(x=1,y=33,z='z')"
    assert E().what().id() == "E(x='x',y=33,z='z')"


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


def test_whatable_builtin():
    with pytest.raises(TypeError) as excinfo:
        whatable(all)
    assert 'builtins cannot be whatamised' in str(excinfo.value)

    with pytest.raises(Exception) as excinfo:
        whatable(str)
    assert 'cannot whatamise' in str(excinfo.value)


def test_whatable_faker():

    class Faker(object):
        def what(self):
            return 'Fool you; %s' % self.__class__.__name__

    @whatable
    class Fool(object):
        def __init__(self):
            self.faker = Faker()

    assert 'Fool you; Faker' not in whatareyou(Fool()).id()
    assert whatareyou(Fool()).id() == 'Fool(faker=Faker())'


# --- Test pickability (https://github.com/sdvillal/whatami/issues/8)

def pickle_roundtrip(x):
    return pickle.loads(pickle.dumps(x))


class Pickable(object):
    def __init__(self, x=3):
        super(Pickable, self).__init__()
        self.x = x


def test_whatable_class_pickling():

    # Decorating a Pickable class
    WhatablePickable = pickle_roundtrip(whatable(Pickable))
    assert WhatablePickable.__name__ == 'Pickable'
    assert WhatablePickable(5).what().id() == 'Pickable(x=5)'


def pickable(x, y, z=3):  # pragma: no cover
    return x + y + z


@pytest.mark.xfail(reason='need to find a way to do this')
def test_whatable_function_pickling():  # pragma: no cover
    whatable_pickable = whatable(pickable)
    assert whatable_pickable.what().id() == 'pickable(z=3)'
    roundtripped = pickle_roundtrip(whatable_pickable)
    assert roundtripped.what().id() == 'pickable(z=3)'


@pytest.mark.xfail(reason='allow to patch types and, if not, add at least a whatable partial construct')
def test_whatable_type():  # pragma: no cover
    whatable_partial = whatable(partial)
    m = whatable_partial(pickable, x=1)
    assert m.what().id() == 'pickable(x=1,z=3)'
    assert m(y=2) == 6
    whatable_partial = pickle_roundtrip(whatable_partial)
    m = whatable_partial(pickable, x=1)
    assert m.what().id() == 'pickable(x=1,z=3)'
    assert m(y=2) == 6


def test_whatable_inplacefunc():

    def afunc(x=3):  # pragma: no cover
        return x

    wafunc = whatable(afunc, modify_func_inplace=True)

    assert afunc is wafunc
    assert afunc.what().id() == wafunc.what().id()
    assert wafunc.what().id() == 'afunc(x=3)'

# --- Test whatareyou for basic collections


def test_whatareyou_basic_collections():
    # List
    x = [1, 2, '3']
    assert whatareyou(x).id() == "list(seq=[1,2,'3'])"
    # Tuple
    x = tuple([1, 2, '3'])
    assert whatareyou(x).id() == "tuple(seq=(1,2,'3'))"
    # Set
    x = {1, 2, '3'}
    assert whatareyou(x).id() == "set(seq={'3',1,2})"
    # Dict
    x = {1: 'one', 2: 'two', '3': 'three'}
    assert whatareyou(x).id() == "dict(seq={'3':'three',1:'one',2:'two'})"
