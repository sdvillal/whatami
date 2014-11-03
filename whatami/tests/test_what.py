# coding=utf-8

# Authors: Santi Villalba <sdvillal@gmail.com>
# Licence: BSD 3 clause

from datetime import datetime
from functools import partial
import hashlib

import pytest

from whatami import whatable, whatareyou, What, \
    configuration_as_string, parse_id_string, config_dict_for_object, is_whatable


# ---- Fixtures and teardown

def teardown_function(_):
    """After each run, wipe nicknames registry."""
    What.reset_nicknames()


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
def c3(c1, c2, quote_string_values=True):
    """A whatable object with nested whatables and irrelevant members."""

    class C3(object):
        def __init__(self, c1=c1, c2=c2, irrelevant=True, quote_string_values=quote_string_values):
            super(C3, self).__init__()
            self.c1 = c1
            self.c2 = c2
            self.irrelevant = irrelevant
            self._quote_string_values = quote_string_values

        @whatable(force_flag_as_whatami=True)
        def what(self):
            return whatareyou(self,
                              non_id_keys=('irrelevant',),
                              quote_string_values=self._quote_string_values)
    return C3()


# ---- Let the testing begin...


def test_parse_id_simple():
    # Proper splitting
    name, parameters = parse_id_string('rfc#n_jobs=4#n_trees=100##', infer_numbers=False)
    assert name == 'rfc'
    assert parameters.get('n_jobs', None) == '4'
    assert parameters.get('n_trees', None) == '100'
    assert len(parameters) == 2
    # Number inference
    name, parameters = parse_id_string('rfc#n_jobs=4#n_trees=100##')
    assert name == 'rfc'
    assert parameters.get('n_jobs', None) == 4
    assert parameters.get('n_trees', None) == 100
    assert len(parameters) == 2
    # No parameters
    name, parameters = parse_id_string('rfc', infer_numbers=False)
    assert name == 'rfc'
    assert len(parameters) == 0
    # No name
    with pytest.raises(Exception) as excinfo:
        parse_id_string('#param=55')
    assert excinfo.value.message == '#param=55 has no name, and it should (it starts already by #)'


def test_parse_id_nested():
    name, parameters = parse_id_string('rfc#n_jobs="multiple#here=100"', infer_numbers=False, parse_nested=False)
    assert name == 'rfc'
    assert len(parameters) == 1
    assert parameters['n_jobs'] == 'multiple#here=100'
    # Do not remove quotes...
    name, parameters = parse_id_string('rfc#n_jobs="multiple#here=100"',
                                       infer_numbers=True, remove_quotes=False, parse_nested=False)
    assert name == 'rfc'
    assert len(parameters) == 1
    assert parameters['n_jobs'] == '"multiple#here=100"'
    # Parse nested
    name, parameters = parse_id_string('rfc#n_jobs="multiple#here=100"',
                                       infer_numbers=True, remove_quotes=False, parse_nested=True)
    assert name == 'rfc'
    assert len(parameters) == 1
    nested_name, nested_parameters = parameters['n_jobs']
    assert nested_name == 'multiple'
    assert len(nested_parameters) == 1
    assert nested_parameters['here'] == 100


def test_parse_id_invalid():

    # Configurations should not be empty
    with pytest.raises(Exception) as excinfo:
        parse_id_string('')
    assert excinfo.value.message == 'Cannot parse empty configuration strings'

    # Configurations should have a name
    with pytest.raises(Exception) as excinfo:
        parse_id_string('#noname=invalid')
    assert excinfo.value.message == '#noname=invalid has no name, and it should (it starts already by #)'

    # Keys should exist
    with pytest.raises(Exception) as excinfo:
        parse_id_string('useless#=no_key_is_invalid')
    assert excinfo.value.message == 'Splitting has not worked. Missing at least one key or a value.'

    # Values should exist
    with pytest.raises(Exception) as excinfo:
        parse_id_string('useless#no_value_is_invalid=')
    assert excinfo.value.message == 'Splitting has not worked. Missing at least one key or a value.'

    # The only non-word character should be "="
    with pytest.raises(Exception) as excinfo:
        parse_id_string('useless#at@is_invalid')
    assert excinfo.value.message == 'Splitting has not worked. ' \
                                    'There is something that is not a = where there should be.'


def test_configuration_nonids_prefix_postfix():

    # Non-ids
    c1 = What('tc',
              {'p1': 1, 'p2': 2, 'p3': 3, 'verbose': True, 'n_jobs': None},
              non_id_keys=('verbose', 'n_jobs'))
    assert c1.id() == 'tc#p1=1#p2=2#p3=3'
    assert c1.id(nonids_too=True) == 'tc#n_jobs=None#p1=1#p2=2#p3=3#verbose=True'

    with pytest.raises(Exception) as excinfo:
        What('tc',
             {'p1': 1, 'p2': 2, 'p3': 3, 'verbose': True, 'n_jobs': None},
             non_id_keys=str)
    assert excinfo.value.message == 'non_ids must be None or an iterable'

    # Synonyms
    c1 = What('tc',
              {'p1': 1, 'p2': 2, 'p3': 3, 'verbose': True, 'n_jobs': None},
              non_id_keys=('verbose', 'n_jobs'),
              synonyms={'verbose': 'v'})
    assert c1.id(nonids_too=True) == 'tc#n_jobs=None#p1=1#p2=2#p3=3#v=True'

    # Prefix and postfix keys
    c1 = What('tc',
              {'p1': 1, 'p2': 2, 'p3': 3, 'verbose': True, 'n_jobs': None},
              non_id_keys=('verbose', 'n_jobs'),
              prefix_keys=('p3', 'p2'),
              postfix_keys=('p1',))
    assert c1.id(nonids_too=True) == 'tc#p3=3#p2=2#n_jobs=None#verbose=True#p1=1'

    with pytest.raises(Exception) as excinfo:
        What('tc',
             {'p1': 1, 'p2': 2, 'p3': 3, 'verbose': True, 'n_jobs': None},
             non_id_keys=('verbose', 'n_jobs'),
             prefix_keys=('p3', 'p2'),
             postfix_keys=('p1', 'p2')).id()
    assert excinfo.value.message == 'Some identifiers (set([\'p2\'])) appear in both first and last, they should not'


def test_configuration_as_string():

    assert configuration_as_string(None) is None

    assert configuration_as_string('Myself') == 'Myself'

    with pytest.raises(Exception) as excinfo:
        configuration_as_string(datetime)
    assert excinfo.value.message == 'the object must be None, a string, have a what() method or have an id() method'


def test_non_nested_configurations(c1):
    # Non-nested configurations
    config_c1 = c1.what()
    assert config_c1.name == 'C1'
    assert len(config_c1.configdict) == 3
    assert config_c1.p1 == 'blah'
    assert config_c1.p2 == 'bleh'
    assert config_c1.length == 1
    assert config_c1 == config_c1
    assert config_c1.id() == 'C1#length=1#p1=\'blah\'#p2=\'bleh\''
    assert len(set(config_c1.keys()) | {'p1', 'p2', 'length'}) == 3


def test_nested_whatables(c1, c2):
    # Nested whatables
    config_c2 = c2.what()
    assert config_c2.name == 'C2'
    assert len(config_c2.configdict) == 2
    assert config_c2['name'] == 'roxanne'
    assert config_c2.c1.what() == c1.what()
    assert config_c2.id() == 'C2#c1="C1#length=1#p1=\'blah\'#p2=\'bleh\'"#name=\'roxanne\''


def test_nested_configurations(c1, c2):
    # Nested
    c2.c1 = c1.what()
    config_c2 = c2.what()
    assert config_c2.id() == 'C2#c1="C1#length=1#p1=\'blah\'#p2=\'bleh\'"#name=\'roxanne\''


def test_non_id_keys(c3):
    # non-id keys
    config_c3 = c3.what()
    assert config_c3.id() == 'C3#c1="C1#length=1#p1=\'blah\'#p2=\'bleh\'"#' \
                             'c2="C2#c1="C1#length=1#p1=\'blah\'#p2=\'bleh\'"#name=\'roxanne\'"'
    assert config_c3.id(nonids_too=True) == 'C3#c1="C1#length=1#p1=\'blah\'#p2=\'bleh\'"#' \
                                            'c2="C2#c1="C1#length=1#p1=\'blah\'#p2=\'bleh\'"#name=\'roxanne\'"#' \
                                            'irrelevant=True'
    assert config_c3.id(nonids_too=True) == 'C3#c1="C1#length=1#p1=\'blah\'#p2=\'bleh\'"#' \
                                            'c2="C2#c1="C1#length=1#p1=\'blah\'#p2=\'bleh\'"#name=\'roxanne\'"#' \
                                            'irrelevant=True'
    sha2 = hashlib.sha256('C3#c1="C1#length=1#p1=\'blah\'#p2=\'bleh\'"#'
                          'c2="C2#c1="C1#length=1#p1=\'blah\'#p2=\'bleh\'"#name=\'roxanne\'"').hexdigest()
    assert config_c3.id(maxlength=1) == sha2
    config_c3.set_key_synonym('c1', 'C1Syn')
    assert config_c3.key_synonym('c1') == 'C1Syn'
    assert config_c3.id() == 'C3#C1Syn="C1#length=1#p1=\'blah\'#p2=\'bleh\'"#' \
                             'c2="C2#c1="C1#length=1#p1=\'blah\'#p2=\'bleh\'"#name=\'roxanne\'"'


def test_non_quoted_string_values(c3):
    # non-quoted string values must cascade recursively
    # - this makes things complex, should get rid of this feat
    assert c3.what().id(quote_string_vals=False) == 'C3#c1="C1#length=1#p1=blah#p2=bleh"#' \
                                                    'c2="C2#c1="C1#length=1#p1=blah#p2=bleh"#name=roxanne"'


def test_whatable_magics(c1):
    # configuration magics
    assert str(c1.what()) == 'C1#length=1#p1=\'blah\'#p2=\'bleh\''


def test_whatable_functions(c1):
    def identity(x):
        return x

    # Functions
    c1.p1 = identity
    assert c1.what().id() == 'C1#length=1#p1="identity#"#p2=\'bleh\''
    assert c1.p1(1) == 1


def test_whatable_partial(c1):

    def identity(x):
        return x

    # Partial functions
    c1.p1 = partial(identity, x=1)
    assert c1.what().id() == 'C1#length=1#p1="identity#x=1"#p2=\'bleh\''
    assert c1.p1() == 1


def test_whatable_builtins(c1):
    # Builtins - or whatever foreigner - do not allow introspection
    c1.p1 = sorted
    with pytest.raises(Exception) as excinfo:
        c1.what().id()
    assert excinfo.value.message == 'Cannot determine the argspec of a non-python function (sorted). ' \
                                    'Please wrap it in a whatable'


def test_whatable_anyobject(c1):

    # Objects without proper representation
    class RandomClass():
        def __init__(self):
            self.param = 'yes'
    c1.p1 = RandomClass()
    assert c1.what().id() == 'C1#length=1#p1="RandomClass#param=\'yes\'"#p2=\'bleh\''


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
    assert A().what().id() == 'A#a=3'


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
                        config_dict_for_object(self, add_properties=True))

    cp = ClassWithProps()
    assert cp.what().id() == 'ClassWithProps#prop=3'

    # Objects with dynamically added properties
    setattr(cp, 'dprop', property(lambda: 5))
    with pytest.raises(Exception) as excinfo:
        cp.what().id()
    assert excinfo.value.message == 'Dynamic properties are not suppported.'


def test_is_whatable(c1):
    assert is_whatable(c1)
    assert not is_whatable(str)


def test_whatable_slots():

    # N.B. Slots are implemented as descriptors
    @whatable
    class Slots(object):
        __slots__ = ['prop']

        def __init__(self):
            self.prop = 3

    slots = Slots()
    assert slots.what().id() == 'Slots#prop=3'


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

    assert Sub().what().id() == 'Sub#a=\'subA\'#b=\'superB\'#c=\'subC\''


def test_whatable_does_not_override_what(c1):
    c1.what = 33
    assert not is_whatable(c1)
    with pytest.raises(Exception) as excinfo:
        whatable(c1)
    assert excinfo.value.message == 'object already has an attribute what, and is not a whatami what, ' \
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
    assert s3.what().id() == "S3#d1=1#d2=4#p1=5#s1=2#s2=3#s3=6"

    s3 = whatable(s3, add_dict=True, add_slots=True, add_properties=False)
    assert s3.what().id() == "S3#d1=1#d2=4#s1=2#s2=3#s3=6"

    s3 = whatable(s3, add_dict=True, add_slots=False, add_properties=True)
    assert s3.what().id() == "S3#d1=1#d2=4#p1=5"

    s3 = whatable(s3, add_dict=True, add_slots=False, add_properties=False)
    assert s3.what().id() == "S3#d1=1#d2=4"

    s3 = whatable(s3, add_dict=False, add_slots=False, add_properties=False)
    assert s3.what().id() == "S3#"

    s3 = whatable(s3, add_dict=False, add_slots=True, add_properties=False)
    assert s3.what().id() == "S3#s1=2#s2=3#s3=6"

    s3 = whatable(s3, add_dict=False, add_slots=False, add_properties=True)
    assert s3.what().id() == "S3#p1=5"

    s3 = whatable(s3, add_dict=False, add_slots=True, add_properties=True)
    assert s3.what().id() == "S3#p1=5#s1=2#s2=3#s3=6"


def test_whatable_nickname(c1):

    class NicknamedConfigurable(object):
        def what(self):
            c = whatareyou(self)
            c.nickname = 'bigforest'
            return c

    # nicknamed configurations
    assert NicknamedConfigurable().what().nickname == 'bigforest'
    assert NicknamedConfigurable().what().nickname_or_id() == 'bigforest'

    # not nicknamed configurations
    assert c1.what().nickname is None
    assert c1.what().nickname_or_id() == 'C1#length=1#p1=\'blah\'#p2=\'bleh\''


def test_regnick_with_what(c1):

    # saving the what...
    What.register_nickname('c1', c1, save_what=True)
    assert c1.what().nickname == 'c1'
    assert What.id2what(c1.what().id()) == c1
    assert What.nickname2what('c1') == c1
    assert What.id2nickname(c1.what().id()) == 'c1'
    assert What.nickname2id('c1') == c1.what().id()
    # not saving the what...
    What.remove_nickname('c1')
    What.register_nickname('c1', c1, save_what=False)
    assert What.id2what(c1.what().id()) is None
    assert What.nickname2what('c1') is None
    # and of course not there if we haven't registered...
    assert What.nickname2what('c2') is None
    assert What.id2what('c2') is None


def test_regnick_only_what():
    with pytest.raises(Exception) as excinfo:
        What.register_nickname('c1', 1)
    assert excinfo.value.message == '"what" must be a whatable or a string, but is a <type \'int\'>'


def test_regnick_remove_id(c1):
    What.register_nickname('c1', c1, save_what=True)
    # remove by id...
    What.remove_id(c1.what().id())
    # nothing in there
    assert What.nickname2id('c1') is None
    assert What.id2nickname(c1.what().id()) is None
    assert What.id2what(c1.what().id()) is None


def test_regnick_do_not_reregister(c1):
    What.register_nickname('c1', c1)
    # do not allow update...
    What.register_nickname('c1', c1, save_what=False)
    with pytest.raises(Exception) as excinfo:
        What.register_nickname('c1', 'blahblehblih')
    assert excinfo.value.message == 'nickname "c1" is already associated with id ' \
                                    '"C1#length=1#p1=\'blah\'#p2=\'bleh\'", delete it before updating'
    with pytest.raises(Exception) as excinfo:
        What.register_nickname('c2', c1.what().id())
    assert excinfo.value.message == 'id "%s" is already associated with nickname "c1", delete it before updating' %\
                                    c1.what().id()
    # no problem if we remove it first...
    What.remove_nickname('c1')
    assert c1.what().nickname is None
    What.register_nickname('c1', c1)
    assert c1.what().nickname == 'c1'


def test_regnick_self(c1):
    # self-registration
    what = c1.what()
    what.nickname = 'c1'
    what.register_my_nickname()
    what.nickname = None
    assert what.nickname == 'c1'
    assert c1.what().nickname == 'c1'  # Recall that a call to what() always return a new "What" object

    # no problem on re-registering the same map
    what.register_my_nickname()
    assert what.nickname == 'c1'
    assert c1.what().nickname == 'c1'
    What.remove_nickname('c1')
    assert what.nickname is None
    assert c1.what().nickname is None


def test_regnick_all_nicknames():
    # listing nicknames, reset
    What.register_nickname('one', 'oneblah')
    What.register_nickname('two', 'twoblah')
    assert What.all_nicknames() == [('one', 'oneblah'), ('two', 'twoblah')]
    What.reset_nicknames()
    assert What.all_nicknames() == []


def test_whatable_duck():

    class DuckedWhatable(object):
        def what(self):
            return What(self.__class__.__name__, {'param1': 33})
    cduck = DuckedWhatable()
    assert cduck.what().id() == 'DuckedWhatable#param1=33'

    @whatable
    class NestedDuckedWhatable(object):
        def __init__(self):
            super(NestedDuckedWhatable, self).__init__()
            self.ducked = cduck
    nested_duck = NestedDuckedWhatable()
    assert nested_duck.what().id() == 'NestedDuckedWhatable#ducked="DuckedWhatable#param1=33"'


def test_whatable_decorator():
    @whatable
    def normalize(x, loc=5, scale=3):
        """returns (x+loc) / scale"""
        return (x + loc) / scale
    assert normalize.what().id() == 'normalize#loc=5#scale=3'
    assert normalize.__name__ == 'normalize'
    assert normalize.__doc__ == 'returns (x+loc) / scale'

    # very specific case: partial application over a whatable closure
    normalize6 = partial(normalize, loc=6)
    assert not hasattr(normalize6, 'what')
    assert not hasattr(normalize6, '__name__')  # partials have no name
    normalize6 = whatable(normalize6)
    assert normalize6.what().id() == 'normalize#loc=6#scale=3'
    assert normalize6(3) == 3


def test_list_parameters(c1):
    @whatable
    class WhatableWithList():
        def __init__(self):
            self.list = [c1, 'second']
    w = WhatableWithList()
    assert w.what().id() == "WhatableWithList#list=[%s, \'second\']" % c1.what().id()
    w.list = []
    assert w.what().id() == "WhatableWithList#list=[]"


def test_tuple_parameters(c1):
    @whatable
    class WhatableWithTuple():
        def __init__(self):
            self.tuple = ('first', c1)
    w = WhatableWithTuple()
    assert w.what().id() == "WhatableWithTuple#tuple=(\'first\', %s)" % c1.what().id()
    w.tuple = ()
    assert w.what().id() == "WhatableWithTuple#tuple=()"


def test_dict_parameters(c1):
    @whatable
    class WhatableWithDict():
        def __init__(self):
            self.dict = {'c1': c1, 'two': 2}
    w = WhatableWithDict()
    assert w.what().id() == "WhatableWithDict#dict={c1=\"C1#length=1#p1='blah'#p2='bleh'\"#two=2}"
    w.dict = {}
    assert w.what().id() == "WhatableWithDict#dict={}"


def test_set_parameters(c1):
    @whatable
    class WhatableWithSet():
        def __init__(self):
            self.set = {c1, 2}
    w = WhatableWithSet()
    assert w.what().id() == "WhatableWithSet#set={2, C1#length=1#p1='blah'#p2='bleh'}"
    w.set = set()
    assert w.what().id() == "WhatableWithSet#set={}"
