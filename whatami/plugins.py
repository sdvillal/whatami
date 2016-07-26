# coding=utf-8

# Authors: Santi Villalba <sdvillal@gmail.com>
# Licence: BSD 3 clause

from __future__ import print_function, absolute_import
from future.utils import string_types

import inspect
from collections import OrderedDict
from functools import partial

from whatami.misc import maybe_import

from .what import What, whatareyou
from .misc import callable2call, config_dict_for_object, curry2partial
from .minijoblib.hashing import hash as hasher


# --- Basic plugins

def what_plugin(v):
    """Deals with What objects.

    This should be first in the plugin chain to allow free specialisation of the what method.
    """
    if isinstance(v, What):
        return v.id()


def whatable_plugin(v):
    """Deals with whatable objects.

    This should be second in the plugin chain to allow free specialisation of the what method.
    """
    if hasattr(v, 'what'):
        what = v.what
        what = what() if callable(what) else what
        return what_plugin(what)


def builtin_plugin(v):
    """Special message if we try to pass something like sorted or np.array."""
    if inspect.isbuiltin(v):
        raise Exception('Cannot determine the argspec of a non-python function (%s). '
                        'Please wrap it in a whatable' % v.__name__)


def property_plugin(v):
    """Deals with dynamic properties, which are at the moment unsupported (so always raises)."""
    if isinstance(v, property):
        raise Exception('Dynamic properties are not suppported.')


def dict_plugin(v):
    """Returns an id for dictionaries, sorting the keys for unique id (except for OrderedDict).
    Any custom representation for a dictionary subclass must precede this plugin in the plugins chain.
    """
    if isinstance(v, dict):
        kvs = ['%s:%s' % (WhatamiPluginManager.build_string(dict_k),
                          WhatamiPluginManager.build_string(dict_v))
               for dict_k, dict_v in v.items()]
        if not isinstance(v, OrderedDict):
            kvs = sorted(kvs)
        id_string = '{%s}' % ','.join(kvs)
        if type(v) == dict:
            return id_string
        return '%s(seq=%s)' % (v.__class__.__name__, id_string)


def set_plugin(v):
    """Generates an id for python sets and frozensets, sorting the elements for id uniqueness."""
    if isinstance(v, (set, frozenset)):
        elements = sorted(map(WhatamiPluginManager.build_string, v))
        if type(v) == frozenset:
            return 'frozenset({%s})' % ','.join(elements) if elements else 'frozenset()'
        id_string = '{%s}' % ','.join(elements) if len(elements) > 0 else 'set()'
        if type(v) == set:
            return id_string
        return '%s(seq=%s)' % (v.__class__.__name__, id_string)


def list_plugin(v):
    """Generate a unique id for lists."""
    if isinstance(v, list):
        id_string = '[%s]' % ','.join(map(WhatamiPluginManager.build_string, v))
        if type(v) == list:
            return id_string
        return '%s(seq=%s)' % (v.__class__.__name__, id_string)


def tuple_plugin(v):
    """Generate a unique id for tuples."""
    if isinstance(v, tuple):
        id_string = '(%s)' % ','.join(map(WhatamiPluginManager.build_string, v))
        if type(v) == tuple:
            return id_string
        return '%s(seq=%s)' % (v.__class__.__name__, id_string)


#
# --- String plugin
#
# The challenge is to manage escaping in a robust and general way, without generating double escaping
#
# We need to unescape and escape back. In the general case this is difficult, see:
#  http://stackoverflow.com/questions/1885181/how-do-i-un-escape-a-backslash-escaped-string-in-python
#  http://stackoverflow.com/questions/4020539/process-escape-sequences-in-a-string-in-python
# The more robust, general approach seems to use regexps:
#   http://stackoverflow.com/a/24519338
# But because we only want to escape unescaped single quotes, our case seems simpler to solve...
#

def string_plugin(v):
    """
    Returns an id string for a string.

    This is a single-quoted string with single-quoted characters escaped.
    """
    if isinstance(v, string_types):
        return '\'%s\'' % v.replace("\\'", "'").replace("'", "\\'")
        # This is correct because of these relations:
        # "'" == "\'"
        # "\\'" == "\\\'"
        # "\\\\'" => == "\\\\\'"
        # ...


# --- Function plugins


def partial_plugin(v):
    """Deals with partials and toolz curried functions.

    Configuration are the set parameters ("compulsory") and default parameters
    ("weak", as can be changed at dispatch time).
    """
    v = curry2partial(v)
    if isinstance(v, partial):
        name, keywords = callable2call(v)
        return What(name, keywords).id()


def function_plugin(v):
    """Deals with functions, configuration are the keyword args.

    Note that configuration is "weak" and not guaranteed, as can change at dispatch time.
    """
    if inspect.isfunction(v):
        args, _, _, defaults = inspect.getargspec(v)
        defaults = [] if not defaults else defaults
        args = [] if not args else args
        params_with_defaults = dict(zip(args[-len(defaults):], defaults))
        name = v.__name__ if v.__name__ != '<lambda>' else 'lambda'
        what = What(name, params_with_defaults)
        return what.id()


# --- "Capture all" plugins

def anyobject0x_plugin(v, deep=False):
    """An object without proper representation, try a best effort.

    Parameters
    ----------
    v : object
      The object to represent as an id string

    deep : boolean, default False
      If True, an id string will be generated recursively for all members of v
      Note that this is quite unsafe and we do not check for circular recursion.
    """
    if ' at 0x' in str(v):
        if deep:
            what = What(v.__class__.__name__, config_dict_for_object(v))
        else:
            what = What(v.__class__.__name__, {})
        return what.id()


def anyobject_plugin(v):
    """Delegate to str, this should be the last plugin in the chain."""
    return str(v)

# --- Numpy and pandas

hasher = partial(hasher, hash_name='md5')


np = maybe_import('numpy', 'conda')


def has_numpy():
    """Returns True iff numpy can be imported."""
    return inspect.ismodule(np)


pd = maybe_import('pandas', 'conda')


def has_pandas():
    """Returns True iff pandas can be imported."""
    return pd is not None


def numpy_plugin(v):
    """Represents numpy arrays as "class(hash='xxx')"."""
    if np is not None and hasher is not None:
        if isinstance(v, np.ndarray):
            return "%s(hash='%s')" % (v.__class__.__name__, hasher(v))


def rng_plugin(v):
    """Represents a numpy rng as a string RandomState(state=xxx)."""
    if np is not None and hasher is not None:
        if isinstance(v, np.random.RandomState):
            return "%s(state=%s)" % (v.__class__.__name__, whatareyou(v.__getstate__()).id())


def pandas_plugin(v):
    """Represents pandas objects as any of "DataFrame(hash='xxx')" or "Series(hash='xxx')"."""
    if pd is not None and hasher is not None:
        if isinstance(v, (pd.DataFrame, pd.Series)):
            return "%s(hash='%s')" % (v.__class__.__name__, hasher(v))
    #
    # Given the variability of pandas key classes and the stability of numpy
    # ABI it should repay to create an spesialised pandas plugin that just
    # cast indices and data as arrays and use these to generate IDs that
    # are stable between pandas versions.
    #


# --- Plugin management

class WhatamiPluginManager(object):
    """
    Examples
    --------
    >>> def float_plugin(v):
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

    DEFAULT_PLUGINS = (
        # whatami plugins, should go first
        what_plugin,
        whatable_plugin,
        # basic plugins
        builtin_plugin,
        property_plugin,
        string_plugin,
        tuple_plugin,
        list_plugin,
        dict_plugin,
        set_plugin,
        # callable plugins
        partial_plugin,
        function_plugin,
        # numpy/pandas plugins
        pandas_plugin,
        numpy_plugin,
        rng_plugin,
        # capture-all plugins, should come last in the chain
        anyobject0x_plugin,
        anyobject_plugin,
    )

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
        """Removes a plugin from the list of plugins.

        Parameters
        ----------
        plugin : function
          The plugin to drop
        """
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
        plugin : function (value) -> string
          A function that checks for value type and if it applies generates a string representing it.

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

    @classmethod
    def build_string(cls, v):
        """Returns the nested configuration string for a variety of value types.

        Parameters
        ----------
        v : object
          The object to represent as a string
        """
        for plugin in cls.plugins():
            string = plugin(v)
            if string is not None:
                return string


toolz = maybe_import('toolz', 'pip', 'cytoolz', 'toolz')
