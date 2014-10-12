# coding=utf-8
"""Tests Configurable and friends."""

# Authors: Santi Villalba <sdvillal@gmail.com>
# Licence: BSD 3 clause

from datetime import datetime
from functools import partial
import hashlib
import inspect
from time import strptime, mktime

import pytest

from whatami.config import parse_id_string, Configurable, Configuration, config_dict_for_object, \
    mlexp_info_helper, _dict_or_slotsdict, configuration_as_string


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


def test_dict_or_slots():

    # No matter we have a __dict__...
    class NoSlots(object):
        def __init__(self):
            self.prop = 3
    assert _dict_or_slotsdict(NoSlots()) == {'prop': 3}

    # ...or a __slots__
    class Slots(object):
        __slots__ = ['prop']

        def __init__(self):
            self.prop = 3
    assert _dict_or_slotsdict(Slots()) == {'prop': 3}


def test_configuration_nonids_prefix_postfix():

    # Non-ids
    c1 = Configuration('tc',
                       {'p1': 1, 'p2': 2, 'p3': 3, 'verbose': True, 'n_jobs': None},
                       non_id_keys=('verbose', 'n_jobs'))
    assert c1.id() == 'tc#p1=1#p2=2#p3=3'
    assert c1.id(nonids_too=True) == 'tc#n_jobs=None#p1=1#p2=2#p3=3#verbose=True'

    with pytest.raises(Exception) as excinfo:
        Configuration('tc',
                      {'p1': 1, 'p2': 2, 'p3': 3, 'verbose': True, 'n_jobs': None},
                      non_id_keys=str)
    assert excinfo.value.message == 'non_ids must be None or an iterable'

    # Synonyms
    c1 = Configuration('tc',
                       {'p1': 1, 'p2': 2, 'p3': 3, 'verbose': True, 'n_jobs': None},
                       non_id_keys=('verbose', 'n_jobs'),
                       synonyms={'verbose': 'v'})
    assert c1.id(nonids_too=True) == 'tc#n_jobs=None#p1=1#p2=2#p3=3#v=True'

    # Prefix and postfix keys
    c1 = Configuration('tc',
                       {'p1': 1, 'p2': 2, 'p3': 3, 'verbose': True, 'n_jobs': None},
                       non_id_keys=('verbose', 'n_jobs'),
                       prefix_keys=('p3', 'p2'),
                       postfix_keys=('p1',))
    assert c1.id(nonids_too=True) == 'tc#p3=3#p2=2#n_jobs=None#verbose=True#p1=1'

    with pytest.raises(Exception) as excinfo:
        Configuration('tc',
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
    assert excinfo.value.message == 'the object must be None, a string or have an id() method'


@pytest.fixture
def c1():
    """A simple configurable object."""
    class C1(Configurable):
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
    """A configurable object with a nested configurable."""
    class C2(Configurable):
        def __init__(self, name='roxanne', c1=c1):
            super(C2, self).__init__()
            self.name = name
            self.c1 = c1
    return C2()


@pytest.fixture
def c3(c1, c2, quote_string_values=True):
    """A configurable object with nested configurables and irrelevant members."""
    class C3(Configurable):
        def __init__(self, c1=c1, c2=c2, irrelevant=True, quote_string_values=quote_string_values):
            super(C3, self).__init__()
            self.c1 = c1
            self.c2 = c2
            self.irrelevant = irrelevant
            self._quote_string_values = quote_string_values

        def what(self):
            return Configuration(
                self.__class__.__name__,
                non_id_keys=('irrelevant',),
                configuration_dict=config_dict_for_object(self),
                quote_string_values=self._quote_string_values)
    return C3()


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


def test_nested_configurables(c1, c2):
    # Nested configurables
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
    config_c3.set_synonym('c1', 'C1Syn')
    assert config_c3.synonym('c1') == 'C1Syn'
    assert config_c3.id() == 'C3#C1Syn="C1#length=1#p1=\'blah\'#p2=\'bleh\'"#' \
                             'c2="C2#c1="C1#length=1#p1=\'blah\'#p2=\'bleh\'"#name=\'roxanne\'"'


def test_non_quoted_string_values(c3):
    # non-quoted string values must cascade recursively
    # - this makes things complex, should get rid of this feat
    assert c3.what().id(quote_string_vals=False) == 'C3#c1="C1#length=1#p1=blah#p2=bleh"#' \
                                                   'c2="C2#c1="C1#length=1#p1=blah#p2=bleh"#name=roxanne"'


def test_configurable_magics(c1):
    # configuration magics
    assert str(c1.what()) == 'C1#length=1#p1=\'blah\'#p2=\'bleh\''


def test_configurable_functions(c1):
    def identity(x):
        return x

    # Functions
    c1.p1 = identity
    assert c1.what().id() == 'C1#length=1#p1="identity#"#p2=\'bleh\''


def test_configurable_partial(c1):

    def identity(x):
        return x

    # Partial functions
    c1.p1 = partial(identity, x=1)
    assert c1.what().id() == 'C1#length=1#p1="identity#x=1"#p2=\'bleh\''


def test_configurable_builtins(c1):
    # Builtins - or whatever foreigner - do not allow introspection
    c1.p1 = sorted
    with pytest.raises(Exception) as excinfo:
        c1.what().id()
    assert excinfo.value.message == 'Cannot determine the argspec of a non-python function (sorted). ' \
                                    'Please wrap it in a configurable'


def test_configurable_anyobject(c1):

    # Objects without proper representation
    class RandomClass():
        def __init__(self):
            self.param = 'yes'
    c1.p1 = RandomClass()
    assert c1.what().id() == 'C1#length=1#p1="RandomClass#param=\'yes\'"#p2=\'bleh\''


def test_configurable_data_descriptors():

    # Objects with data descriptors
    class ClassWithProps(Configurable):
        def __init__(self, add_descriptors=True):
            super(ClassWithProps, self).__init__(add_descriptors=add_descriptors)
            self._prop = 3

        @property
        def prop(self):
            return self._prop

    cp = ClassWithProps(add_descriptors=True)
    assert cp.what().id() == 'ClassWithProps#prop=3'
    cp = ClassWithProps(add_descriptors=False)
    assert cp.what().id() == 'ClassWithProps#'

    # Objects with dynamically added properties
    setattr(cp, 'dprop', property(lambda: 5))
    with pytest.raises(Exception) as excinfo:
        cp.what().id()
    assert excinfo.value.message == 'Dynamic properties are not suppported.'


def test_configurable_slots():

    # Objects with __slots__
    class Slots(Configurable):
        __slots__ = ['prop']

        def __init__(self):
            super(Slots, self).__init__(add_descriptors=True)  # N.B. Slots are implemented as descriptors.
            self.prop = 3

    slots = Slots()
    assert slots.what().id() == 'Slots#prop=3'


def test_configurable_inheritance():

    # Inheritance works as spected
    class Super(Configurable):
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


def test_configurable_nickname(c1):

    class NicknamedConfigurable(Configurable):
        def what(self):
            c = super(NicknamedConfigurable, self).what()
            c.nickname = 'bigforest'
            return c

    # nicknamed configurations
    assert NicknamedConfigurable().what().nickname == 'bigforest'
    assert NicknamedConfigurable().what().nickname_or_id() == 'bigforest'

    # not nicknamed configurations
    assert c1.what().nickname is None
    assert c1.what().nickname_or_id() == 'C1#length=1#p1=\'blah\'#p2=\'bleh\''


def test_configurable_duck():

    class DuckedConfiguration(object):
        def what(self):
            return Configuration(self.__class__.__name__, {'param1': 33})
    cduck = DuckedConfiguration()
    assert cduck.what().id() == 'DuckedConfiguration#param1=33'

    class NestedDuckedConfiguration(Configurable):
        def __init__(self):
            super(NestedDuckedConfiguration, self).__init__()
            self.ducked = cduck
    nested_duck = NestedDuckedConfiguration()
    assert nested_duck.what().id() == 'NestedDuckedConfiguration#ducked="DuckedConfiguration#param1=33"'


def test_mlexp_info_helper():

    class TestDataset(Configurable):
        def __init__(self):
            super(TestDataset, self).__init__()

    class Prepro(Configurable):
        def __init__(self, lower=0, upper=1):
            super(Prepro, self).__init__()
            self.min = lower
            self.max = upper

    class PreproModel(Configurable):
        def __init__(self, prepro=None, reg='l1', C=1.):
            super(PreproModel, self).__init__()
            self.prepro = prepro
            self.reg = reg
            self.C = C

    class CVEval(Configurable):
        def __init__(self, num_folds=10, seed=0):
            super(CVEval, self).__init__()
            self.num_folds = num_folds
            self.seed = seed

    before = int(datetime.now().strftime("%s"))
    info = mlexp_info_helper(
        title='test',
        data_setup=TestDataset().what(),
        model_setup=PreproModel(prepro=Prepro(), reg='l2').what(),
        eval_setup=CVEval(num_folds=5, seed=2147483647).what(),
        exp_function=test_mlexp_info_helper,
        comments='comments4nothing',
        itime=False)
    assert info['title'] == 'test'
    assert info['data_setup'] == 'TestDataset#'
    assert info['model_setup'] == 'PreproModel#C=1.0#prepro="Prepro#max=1#min=0"#reg=\'l2\''
    assert info['eval_setup'] == 'CVEval#num_folds=5#seed=2147483647'
    assert info['fsource'] == inspect.getsourcelines(test_mlexp_info_helper)
    assert info['comments'] == 'comments4nothing'
    recorded_time = mktime(strptime(info['date'], '%Y-%m-%d %H:%M:%S'))
    assert (recorded_time - before) < 2


if __name__ == '__main__':
    pytest.main(__file__)