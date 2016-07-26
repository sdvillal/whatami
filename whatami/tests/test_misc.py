# coding=utf-8

# Authors: Santi Villalba <sdvillal@gmail.com>
# Licence: BSD 3 clause

from __future__ import absolute_import
from future.utils import PY3
from datetime import datetime
import inspect
from time import strptime, mktime

from functools import partial

from ..what import whatable
from ..misc import callable2call, is_iterable, mlexp_info_helper, maybe_import

import pytest


def test_is_iterable():
    assert is_iterable([1, 2, 3]) is True
    assert is_iterable([]) is True
    assert is_iterable((1, 2, 3)) is True
    assert is_iterable(()) is True
    assert is_iterable(range(19)) is True
    assert is_iterable('abc') is True
    assert is_iterable(None) is False
    assert is_iterable(2) is False
    assert is_iterable(2.5) is False
    assert is_iterable(str) is False


def test_callable2call_partials():
    assert callable2call(partial(map)) == ('map', {})
    assert callable2call(partial(map, function=str)) == ('map', {'function': str})
    assert callable2call(partial(partial(map, function=str), iterable1=())) == ('map', {'function': str,
                                                                                        'iterable1': ()})
    with pytest.raises(Exception) as excinfo:
        callable2call(partial(test_callable2call_partials, function=str, f2=2, f3=3))
    assert 'keywords are not parameters of the function' in str(excinfo.value)

    with pytest.raises(Exception) as excinfo:
        callable2call(partial(test_callable2call_partials, 2, 3))
    assert 'There are too many positional arguments indicated ' in str(excinfo.value)

    def myf(x, y=3):  # pragma: no cover
        return x + y

    with pytest.raises(Exception) as excinfo:
        callable2call(partial(myf, 2, x=3))
    assert 'Some arguments are indicated both by position and name ' in str(excinfo.value)


def test_callable2call_functions():
    assert callable2call(test_callable2call_functions) == ('test_callable2call_functions', {})
    assert callable2call(partial) == ('partial', {})

    def f(x, y=3):
        return x + y

    assert callable2call(f) == ('f', {'y': 3})
    assert f(3) == 6


def test_callable2call_builtins():
    assert callable2call(sorted) == ('sorted', {})


def test_callable2call_wrongargs():
    with pytest.raises(Exception) as excinfo:
        callable2call('sorted')
    expected = 'Only callables (partials, functions, builtins...) are allowed, \'sorted\' is none of them'
    assert str(excinfo.value) == expected


def test_callable2call_lambdas():
    # Anonymous functions are a bit of a corner case
    assert callable2call(lambda x: x) == ('lambda', {})
    assert callable2call(lambda x=5: x) == ('lambda', {'x': 5})


def test_mlexp_info_helper():

    @whatable
    class TestDataset(object):
        def __init__(self):
            super(TestDataset, self).__init__()

    @whatable
    class Prepro(object):
        def __init__(self, lower=0, upper=1):
            super(Prepro, self).__init__()
            self.min = lower
            self.max = upper

    @whatable
    class PreproModel(object):
        def __init__(self, prepro=None, reg='l1', C=1.):
            super(PreproModel, self).__init__()
            self.prepro = prepro
            self.reg = reg
            self.C = C

    @whatable
    class CVEval(object):
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
        itime=None)
    assert info['title'] == 'test'
    assert info['data_setup'] == 'TestDataset()'
    assert info['model_setup'] == "PreproModel(C=1.0,prepro=Prepro(max=1,min=0),reg='l2')"
    assert info['eval_setup'] == 'CVEval(num_folds=5,seed=2147483647)'
    assert info['fsource'] == inspect.getsourcelines(test_mlexp_info_helper)
    assert info['comments'] == 'comments4nothing'
    recorded_time = mktime(strptime(info['date'], '%Y-%m-%d %H:%M:%S'))
    assert (recorded_time - before) < 2


def test_lazy_imports():

    inspect2 = maybe_import('inspect')
    assert inspect2 is inspect

    inspect3 = maybe_import('inspect', None, '123wrong', 'inspect')
    assert inspect3 is inspect

    with pytest.raises(ImportError) as excinfo:
        failed_import = maybe_import('cool', 'conda', '123invalid', '456wrong')
        print(failed_import.whatever)
    assert 'Trying to access whatever from module cool, but the library fails to import.' in str(excinfo.value)
    expectation = 'import 123invalid: No module named 123invalid' if not PY3 else \
        'import 123invalid: No module named \'123invalid\''
    assert expectation in str(excinfo.value)
    assert 'Maybe install it like "conda install 123invalid"?' in str(excinfo.value)

    with pytest.raises(ImportError) as excinfo:
        failed_import = maybe_import('cool', 'sudo apt-get cool', '123invalid', '456wrong')
        print(failed_import.whatever)
    assert 'Trying to access whatever from module cool, but the library fails to import.' in str(excinfo.value)
    assert 'Maybe install it like "sudo apt-get cool"?' in str(excinfo.value)
