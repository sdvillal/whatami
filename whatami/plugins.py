# coding=utf-8

# Authors: Santi Villalba <sdvillal@gmail.com>
# Licence: BSD 3 clause

from __future__ import print_function, unicode_literals, absolute_import
import inspect
from functools import partial

from future.utils import string_types

from .what import What, whatareyou
from .misc import callable2call, config_dict_for_object, curry2partial


# --- Basic plugins

def what_plugin(_, v):
    """Deals with What objects."""
    if isinstance(v, What):
        return v.id()


def whatable_plugin(_, v):
    """Deals with whatable objects."""
    if hasattr(v, 'what'):
        what = v.what
        what = what() if callable(what) else what
        return what_plugin(None, what)


def builtin_plugin(_, v):
    """Special message if we try to pass something like sorted or np.array"""
    if inspect.isbuiltin(v):
        raise Exception('Cannot determine the argspec of a non-python function (%s). '
                        'Please wrap it in a whatable' % v.__name__)


def property_plugin(_, v):
    """Deals with dynamic properties."""
    if isinstance(v, property):
        raise Exception('Dynamic properties are not suppported.')


def dict_plugin(what, v):
    if isinstance(v, dict):
        kvs = sorted('%s:%s' % (what.build_string(k), what.build_string(v)) for k, v in v.items())
        return '{%s}' % ','.join(kvs)


def set_plugin(what, v):
    if isinstance(v, set):
        elements = sorted(map(what.build_string, v))
        return '{%s}' % ','.join(elements) if len(elements) > 0 else 'set()'


def list_plugin(what, v):
    if isinstance(v, list):
        return '[%s]' % ','.join(map(what.build_string, v))


def tuple_plugin(what, v):
    if isinstance(v, tuple):
        return '(%s)' % ','.join(map(what.build_string, v))


def string_plugin(_, v):
    if isinstance(v, string_types):
        return '\'%s\'' % v.decode('string_escape').replace("'", "\\'")


# --- Function plugins


def partial_plugin(what, v):
    """Deals with partials and toolz curried functions.
    Configuration are the set parameters ("compulsory") and default parameters ("weak").
    """
    v = curry2partial(v)
    if isinstance(v, partial):
        name, keywords = callable2call(v)
        return What(name, keywords, what.non_id_keys).id()


def function_plugin(what, v):
    """Deals with functions, configuration are the keyword args."""
    if inspect.isfunction(v):
        args, _, _, defaults = inspect.getargspec(v)
        defaults = [] if not defaults else defaults
        args = [] if not args else args
        params_with_defaults = dict(zip(args[-len(defaults):], defaults))
        name = v.__name__ if v.__name__ != '<lambda>' else 'lambda'
        what = What(name, params_with_defaults, what.non_id_keys)
        return what.id()


# --- "Capture all" plugins

def anyobject0x_plugin(what, v, deep=False):
    """An object without proper representation, try a best effort."""
    if ' at 0x' in str(v):
        if deep:
            what = What(v.__class__.__name__, config_dict_for_object(v), what.non_id_keys)
        else:
            what = What(v.__class__.__name__, {})
        return what.id()


def anyobject_plugin(_, v):
    """Delegate to str, this should be the last plugin in the chain."""
    return str(v)

# --- Numpy and pandas

try:  # pragma: no cover
    from joblib.hashing import hash as hasher
    hasher = partial(hasher, hash_name='md5')
except ImportError:  # pragma: no cover
    hasher = None


def has_joblib():
    """Returns True iff joblib can be imported."""
    return hasher is not None


try:  # pragma: no cover
    import numpy as np
except ImportError:  # pragma: no cover
    np = None


def has_numpy():
    """Returns True iff numpy can be imported."""
    return np is not None


try:  # pragma: no cover
    import pandas as pd
except ImportError:  # pragma: no cover
    pd = None


def has_pandas():
    """Returns True iff pandas can be imported."""
    return pd is not None


def numpy_plugin(_, v):
    """Represents numpy arrays as strings "ndarray(hash='xxx')"."""
    if np is not None and hasher is not None:
        if isinstance(v, np.ndarray):
            return "ndarray(hash='%s')" % hasher(v)
    return None


def pandas_plugin(_, v):
    """Represents pandas objects as any of "DataFrame(hash='xxx')" or "Series(hash='xxx')"."""
    if pd is not None and hasher is not None:
        if isinstance(v, pd.DataFrame):
            return "DataFrame(hash='%s')" % hasher(v)
        elif isinstance(v, pd.Series):
            return "Series(hash='%s')" % hasher(v)
    return None


# --- Plugin management

class WhatamiPluginManager(object):
    """
    Examples
    --------
    >>> def float_plugin(_, v):
    ...     if isinstance(v, float):
    ...         return "'float=%g'" % v
    ...     return None
    >>> function_plugin in WhatamiPluginManager.plugins()
    True
    >>> float_plugin in WhatamiPluginManager.plugins()
    False
    >>> WhatamiPluginManager.insert(float_plugin)
    >>> float_plugin in WhatamiPluginManager.plugins()
    True
    >>> float_plugin == WhatamiPluginManager.plugins()[-3]
    True
    >>> WhatamiPluginManager.drop(float_plugin)
    >>> float_plugin in WhatamiPluginManager.plugins()
    False
    >>> WhatamiPluginManager.insert(float_plugin, before=None)
    >>> float_plugin == WhatamiPluginManager.plugins()[-1]
    True
    >>> WhatamiPluginManager.reset()
    >>> WhatamiPluginManager.insert(float_plugin)
    >>> WhatamiPluginManager.reset()
    >>> float_plugin in WhatamiPluginManager.plugins()
    False
    >>> WhatamiPluginManager.drop(float_plugin)
    Traceback (most recent call last):
    ...
    ValueError: cannot drop plugin float_plugin, not in plugins list
    >>> WhatamiPluginManager.insert(string_plugin)
    Traceback (most recent call last):
    ...
    ValueError: cannot insert plugin string_plugin, already in plugins list
    >>> WhatamiPluginManager.insert(float_plugin, before=string_plugin)
    >>> float_plugin in WhatamiPluginManager.plugins()
    True
    >>> WhatamiPluginManager.drop(float_plugin)
    >>> WhatamiPluginManager.insert(float_plugin, before=float_plugin)
    Traceback (most recent call last):
    ...
    ValueError: plugin to insert before (float_plugin) not in plugins list
    >>> WhatamiPluginManager.insert(float_plugin)
    >>> print(whatareyou(lambda x=0.7: x))
    lambda(x='float=0.7')
    >>> WhatamiPluginManager.reset()
    """

    DEFAULT_PLUGINS = (what_plugin,
                       whatable_plugin,
                       builtin_plugin,
                       property_plugin,
                       string_plugin,
                       tuple_plugin,
                       list_plugin,
                       dict_plugin,
                       set_plugin,
                       partial_plugin,
                       function_plugin,
                       pandas_plugin,
                       numpy_plugin,
                       anyobject0x_plugin,
                       anyobject_plugin)

    PLUGINS = DEFAULT_PLUGINS

    @classmethod
    def plugins(cls):
        """Returns a tuple with the currently considered plugins."""
        return cls.PLUGINS

    @classmethod
    def reset(cls):
        """Makes the plugin list the default list."""
        cls.PLUGINS = cls.DEFAULT_PLUGINS

    @classmethod
    def drop(cls, plugin):
        """Removes a plugin from the list of plugins."""
        plugins = list(cls.PLUGINS)
        try:
            plugins.remove(plugin)
            cls.PLUGINS = tuple(plugins)
        except ValueError:
            raise ValueError('cannot drop plugin %s, not in plugins list' % plugin.__name__)

    @classmethod
    def insert(cls, plugin, before=anyobject0x_plugin):
        """Inserts a new plugin in the list of plugins used to generate strings for values in What configurations.

        Parameters
        ----------
        plugin : function (what, value) -> string
          A function that checks for value type and if it applies generates a string representing it,
          optionally using the information on What instance what.

        before : function, default anyobject0x_plugin
          A plugin already registered in the list. Note that the last two plugins capture most objects,
          so usually plugins need to be inserted at least before them.
          If None, the plugin is inserted at the end of the list.

        Raises
        ------
        ValueError if plugin is already in the list of registered plugins of if before is not in the list.
        """
        if plugin in cls.PLUGINS:
            raise ValueError('cannot insert plugin %s, already in plugins list' % plugin.__name__)
        plugins = list(cls.PLUGINS)
        if before is None:
            plugins.append(plugin)
        else:
            try:
                index = plugins.index(before)
                plugins.insert(index, plugin)
            except ValueError:
                raise ValueError('plugin to insert before (%s) not in plugins list' % before.__name__)
        cls.PLUGINS = tuple(plugins)
