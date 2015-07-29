# coding=utf-8

# Authors: Santi Villalba <sdvillal@gmail.com>
# Licence: BSD 3 clause

from __future__ import unicode_literals, absolute_import
from functools import partial
from future.utils import PY3

import pytest

from whatami.misc import callable2call, is_iterable


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
        assert callable2call(partial(test_callable2call_partials, function=str, f2=2, f3=3))
    assert 'keywords are not parameters of the function' in str(excinfo.value)

    with pytest.raises(Exception) as excinfo:
        assert callable2call(partial(test_callable2call_partials, 2, 3))
    assert 'There are too many positional arguments indicated ' in str(excinfo.value)


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
    if PY3:  # pragma: no cover
        expected = 'Only callables (partials, functions, builtins...) are allowed, \'sorted\' is none of them'
    else:  # pragma: no cover
        expected = 'Only callables (partials, functions, builtins...) are allowed, u\'sorted\' is none of them'
    assert str(excinfo.value) == expected


def test_callable2call_lambdas():
    # Anonymous functions are a bit of a corner case
    assert callable2call(lambda x: x) == ('<lambda>', {})
    assert callable2call(lambda x=5: x) == ('<lambda>', {'x': 5})
