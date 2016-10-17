# coding=utf-8
"""Unobtrusive object (self-)identification for python.

*whatami* strives to abstract configurability and experiment identifiability in a convenient way,
by allowing each object/computation to provide a string uniquelly and consistently self-identifying
itself.

It works this way:

  - Objects provide their own ids based on "parameter=value" dictionaries.
    They do so by returning an instance of the `What` class from a method named `what()`.
    What objects have in turn a method named `id()` providing reasonable strings
    to describe the object (computation).

  - whatami also provides a `whatable` decorator. It can be
    used to provide automatic creation of `What` objects from
    introspecting the object attributes or functions default parameters.

  - whatami automatically generated id strings tend to be long and therefore not human-friendly.
    A parser and transformer are provided to easily manipulate these strings

Examples
--------

>>> # Objects of this class provide a configuration (What object)
>>> class DuckedConfigurable(object):
...      def __init__(self, quantity, name, company=None, verbose=True):
...          self.quantity = quantity
...          self.name = name
...          self.company = company
...          self.verbose = verbose
...
...      def what(self):
...          return What('ducked', {'quantity': self.quantity, 'name': self.name, 'company': self.company})
>>>
>>>
>>> duckedc = DuckedConfigurable(33, 'salty-lollypops', verbose=False)
>>> # The configuration id string sorts by key alphanumeric order, helping id consistency
>>> print(duckedc.what().id())
ducked(company=None,name='salty-lollypops',quantity=33)
>>> # Using the whatable decorator makes objects gain a what() method
>>> # In this case, what() is infered automatically
>>> @whatable
... class Company(object):
...     def __init__(self, name, city, verbose=True):
...          self.name = name
...          self.city = city
...          self._verbose = verbose  # not part of config
...          self.social_reason_ = '%s S.A., %s' % (name, city)  # not part of config
>>> cc = Company(name='Chupa Chups', city='Barcelona')
>>> print(cc.what().id())
Company(city='Barcelona',name='Chupa Chups')
>>> # Ultimately, we can nest whatables...
>>> duckedc = DuckedConfigurable(33, 'salty-lollypops', company=cc, verbose=False)
>>> print(duckedc.what().id())
ducked(company=Company(city='Barcelona',name='Chupa Chups'),name='salty-lollypops',quantity=33)
>>> # Also a function decorator is provided - use with caution
>>> @whatable
... def buy(company, price=2**32, currency='euro'):
...     return '%s is now mine for %g %s' % (company.name, price, currency)
>>> print(buy.what().id())
buy(currency='euro',price=4294967296)
"""

# Authors: Santi Villalba <sdvillal@gmail.com>
# Licence: BSD 3 clause

from __future__ import print_function, absolute_import
import hashlib
import inspect
from copy import deepcopy
from functools import partial, update_wrapper, WRAPPER_ASSIGNMENTS
import types

from future.utils import PY3

from .misc import callable2call, is_iterable, config_dict_for_object, extract_decorated_function_from_closure, trim_dict


class What(object):
    """Stores and manipulates object configuration.

    Configurations are just dictionaries {key: value} that can nest and have a name.

    This class allows to represent configurations as (reasonable, python-like) strings.

    Parameters
    ----------
    name : string
      The name of this configuration (e.g. "RandomForest").

    conf : dictionary
      The {key:value} property dictionary for this configuration.

    non_id_keys : iterable (usually of strings), default None
      A list of keys that should not be considered when generating ids.
      For example: "num_threads" or "verbose" should not change results when fitting a model.
      Keys here won't make it to the configuration string unless explicitly asked for

    out_name : string, default None
      If provided, the output name of the computation (e.g. "feature_importances")

    Attributes
    ----------
    `What` objects carry the same attributes passed to the constructor:
    name, conf, non_id_keys and out_name.
    """

    __slots__ = ('name', 'conf', 'non_id_keys', 'out_name')

    def __init__(self,
                 name,
                 conf,
                 non_id_keys=None,
                 out_name=None):
        super(What, self).__init__()
        self.name = name
        self.conf = conf
        self.out_name = out_name
        if non_id_keys is None:
            self.non_id_keys = set()
        elif is_iterable(non_id_keys):
            self.non_id_keys = set(non_id_keys)
        else:
            raise Exception('non_ids must be None or an iterable')

    def copy(self, deep=False):
        """Returns a copy of this whatable object.

        N.B. If the copy is shallow, side-effects might happen
        if changes are made to mutable values in the configuration dictionary.
        """
        return What(name=self.name,
                    conf=self.conf.copy() if not deep else deepcopy(self.conf),
                    non_id_keys=self.non_id_keys,
                    out_name=self.out_name)

    def flatten(self, non_ids_too=False, collections_too=False, recursive=True):
        """Returns two lists: keys and values.
        - keys is a list of tuples, each tuple being able to address a parameter of this what
        - values is a list with the value corresponding to each corresponding key in the keys array

        Parameters
        ----------
        non_ids_too : boolean, default False
          If True, include also non id keys

        collections_too : boolean, default False
          If True, include also keys that address members of python lists, tuples and dictionaries

        recursive : boolean, default True
          If True, recurse into nested What and collections

        Examples
        --------
        >>> what = whatareyou(lambda x=1, y=(1,2,{None: 3}): None)
        >>> keys, values = what.flatten(collections_too=True)
        >>> keys
        ['x', 'y', ('y', 0), ('y', 1), ('y', 2), ('y', 2, None)]
        >>> what[keys[0]]
        1
        >>> what[keys[-1]]
        3
        >>> values[0] == what[keys[0]]
        True
        >>> values[-1] == what[keys[-1]]
        True
        """
        def flatten(what, flattened_keys, flattened_values, partial_k):
            if isinstance(what, What):
                if non_ids_too:
                    kvs = sorted(what.conf.items())
                else:
                    kvs = sorted(item for item in what.conf.items() if item[0] not in what.non_id_keys)
            elif isinstance(what, (list, tuple)) and collections_too:
                kvs = enumerate(what)
            elif isinstance(what, dict) and collections_too:
                kvs = sorted(what.items())
            else:
                kvs = ()
            for k, v in kvs:
                flattened_keys.append(partial_k + (k,) if 0 < len(partial_k) else k)
                flattened_values.append(v)
                if recursive:
                    flatten(v, flattened_keys, flattened_values, partial_k + (k,))
            return flattened_keys, flattened_values
        return flatten(self, [], [], ())

    def keys(self, non_ids_too=False, collections_too=False, recursive=True):
        """Returns a list with the keys in the configuration."""
        return self.flatten(collections_too=collections_too, non_ids_too=non_ids_too, recursive=recursive)[0]

    def values(self, non_ids_too=False, collections_too=False, recursive=True):
        """Returns a list with the keys in the configuration."""
        return self.flatten(collections_too=collections_too, non_ids_too=non_ids_too, recursive=recursive)[1]

    # ---- Magics

    def __eq__(self, other):
        """Two configurations are equal if they have the same name, out_name and parameters."""
        return (hasattr(other, 'name') and self.name == other.name and
                hasattr(other, 'conf') and self.conf == other.conf and
                hasattr(other, 'out_name') and self.out_name == other.out_name)

    def __str__(self):
        """The default representation is the configuration string including non_ids keys."""
        return self.id(nonids_too=True)

    def __repr__(self):
        return '%s(%r, %r, %r, %r)' % (
            self.__class__.__name__,
            self.name,
            self.conf,
            self.non_id_keys,
            self.out_name)

    def __getitem__(self, item):
        """Allow to retrieve configuration values using [] notations, recursively, whatami aware."""
        try:
            return self.conf[item]
        except KeyError:
            if isinstance(item, tuple):
                w = self.conf
                for key in item:
                    try:
                        w = w[key]
                    except TypeError:
                        w = w.what()[key]
                return w
            raise

    # ---- Fluency

    def set(self, key, value, copy=False):
        """Sets a (non-recursive) key in the configuration dictionary and returns self or a copy."""
        # implement recursive keys
        what = self if not copy else self.copy()
        what.conf[key] = value
        return what

    # ---- ID string generation

    def id(self, nonids_too=False, maxlength=0):
        """Returns the id string (unicode) of this configuration.

        Parameters
        ----------
        nonids_too : boolean, default False
          Non-ids keys are ignored if nonids_too is False.

        maxlength : int, default 0
          If the id length goes over maxlength, it gets replaced by its sha1.
          If <= 0, it is ignored and the full id string will be returned.
        """
        from whatami.plugins import WhatamiPluginManager
        kvs = ','.join('%s=%s' % (k, WhatamiPluginManager.build_string(v))
                       for k, v in sorted(self.conf.items())
                       if nonids_too or k not in self.non_id_keys)
        my_id = '%s(%s)' % (self.name, kvs)
        if self.out_name is not None:
            my_id = '%s=%s' % (self.out_name, my_id)
        return self._trim_too_long(my_id, maxlength=maxlength)

    def positional_id(self, non_ids_too=False, maxlength=0):
        """Returns an id without parameter names, just values.

        Parameters
        ----------
        non_ids_too : boolena, default False
          Whether to include the non-id values too.

        maxlength : int, default 0
          If the id length goes over maxlength, it gets replaced by its sha1.
          If <= 0, it is ignored and the full id string will be returned.
        """
        from whatami.plugins import WhatamiPluginManager
        my_id = '%s(%s)' % (self.name, ','.join(map(WhatamiPluginManager.build_string,
                                                    self.values(non_ids_too=non_ids_too))))
        if self.out_name is not None:
            my_id = '%s=%s' % (self.out_name, my_id)
        return self._trim_too_long(my_id, maxlength=maxlength)

    @staticmethod
    def _trim_too_long(string, maxlength=0):
        """Returns the string or its sha1 if the string length is larger than maxlength."""
        if 0 < maxlength < len(string):
            return hashlib.sha1(string.encode('utf-8')).hexdigest()
        return string

    # --- ID to dictionary

    def to_dict(self, nonids_too=False):
        """Converts the id string of this What object into a dictionary.
        This should be suitable to store using json/yaml/... without custom converters.
        """
        from whatami import id2dict
        return id2dict(self.id(nonids_too=nonids_too, maxlength=0))


def whatareyou(obj,
               # ID string building options
               non_id_keys=None,
               # Config-dict building options
               add_dict=True,
               add_slots=True,
               add_properties=True,
               add_class=False,
               # Keys ignoring options
               exclude_prefix='_',
               exclude_postfix='_',
               excludes=('what',)):
    """Returns a What configuration following the specified behavior for inferring the configuration and ignoring keys.

    The meaning of all the parameters can be found in `What`, `config_dict_for_object`
    and `trim_dict`, to which this function delegates.

    Examples
    --------
    >>> def mola(a, n=5):
    ...     print(a + n)
    >>> print(whatareyou(mola).id())
    mola(n=5)
    >>> from functools import partial
    >>> print(whatareyou(partial(mola, n=7)))
    mola(n=7)
    """
    try:
        name, cd = callable2call(obj)
    except (ValueError, TypeError):
        if type(obj) in (list, tuple, set, dict):  # N.B. do not use isinstance here
            name = obj.__class__.__name__
            cd = {'seq': obj}
        else:
            name = obj.__class__.__name__
            cd = config_dict_for_object(obj,
                                        add_dict=add_dict,
                                        add_slots=add_slots,
                                        add_properties=add_properties,
                                        add_class=add_class)
    return What(name=name,
                conf=trim_dict(cd,
                               exclude_prefix=exclude_prefix,
                               exclude_postfix=exclude_postfix,
                               excludes=excludes),
                non_id_keys=non_id_keys)


def is_whatable(obj):
    """Whatable objects have a method what() that takes no parameters and return a What configuration.

    Examples
    --------
    # >>> wp = whatable(partial(str, a=3))
    # >>> is_whatable(wp)
    # True
    # >>> is_whatable(str)
    # False
    >>> @whatable
    ... class WO(object):
    ...     def __init__(self):
    ...         self.a = 3
    >>> # The class is whatable...
    >>> is_whatable(WO)
    True
    >>> # ...so they are the instances
    >>> is_whatable(WO())
    True
    """
    try:
        what_method = obj.what
        selfbind = '__self__' if PY3 else 'im_self'
        if getattr(what_method, selfbind, None) is None:
            # Unbounded method, so this comes from a class
            if hasattr(what_method, 'whatami'):
                return True
            raise Exception('Cannot infer return type for unbound method what, '
                            'please pass a %r instance instead of the class' % obj)
        return isinstance(what_method(), What)
    except:
        return False


def whatable(obj=None,
             whatfunc=None,
             force_flag_as_whatami=False,
             # ID string building options
             non_id_keys=None,
             # Config-dict building options
             add_dict=True,
             add_slots=True,
             add_properties=True,
             add_class=False,
             exclude_prefix='_',
             exclude_postfix='_',
             excludes=('what',),
             # Other
             modify_func_inplace=False):
    """Decorates an object (also classes) to add a "what()" method.

    When decorating a callable (function, partial...), a brand new, equivalent callable will be
    returned (thus leaving the original intact). In this case, "what" provides safe ids
    only for results obtained when the function is called with its default parameters.
    This is useful in limited cases, for example, if we have a partial to fix all parameters
    but the data.

    When decorating non-callable objects or classes, this function adds a method "what"
    that respects all the {add_dict, add_slots, add_properties, exclude_prefix, exclude_postfix
    and excludes} as per `config_dict_for_object` and `trim_dict`.

    All the parameters are ignored if `whatfunc` is provided. It must be a function returning
    `whatfunc` should be a function accepting one object and must return another function
    that should return the relevant `What` object when called.

    Returns
    -------
    obj with a "what" method (or a wrapper function in case obj is originally a function)

    Examples
    --------
    >>> def normalize(x, mean=3, std=2):
    ...     return (x - mean) / std
    >>> cnormalize = whatable(normalize)
    >>> print(cnormalize.what().id())
    normalize(mean=3,std=2)
    >>> print(cnormalize.__name__)
    normalize
    >>> int(cnormalize(5))
    1
    >>> hasattr(normalize, 'what')
    False
    >>> @whatable
    ... def thunk(x, name='hi'):
    ...     print(x, name)
    >>> print(thunk.what().id())
    thunk(name='hi')
    >>> from future.moves.collections import UserDict
    >>> ud = whatable(UserDict())
    >>> is_whatable(ud)
    True
    >>> print(ud.what().id())
    UserDict(data={})
    >>> @whatable(add_properties=True)
    ... class WhatableWithProps(object):
    ...     def __init__(self):
    ...         super(WhatableWithProps, self).__init__()
    ...         self.a = 3
    ...         self._b = 2
    ...         self._c = 1
    ...     @property
    ...     def d(self):
    ...         return 0
    >>> wwp = WhatableWithProps()
    >>> is_whatable(wwp)
    True
    >>> print(wwp.what().id())
    WhatableWithProps(a=3,d=0)
    >>> wwp = whatable(wwp, add_dict=False, add_properties=True)
    >>> print(wwp.what().id())
    WhatableWithProps(d=0)
    """

    # class decorator
    if obj is None:
        return partial(whatable,
                       whatfunc=whatfunc,
                       force_flag_as_whatami=force_flag_as_whatami,
                       # ID string building options
                       non_id_keys=non_id_keys,
                       # Config-dict building options
                       add_dict=add_dict,
                       add_slots=add_slots,
                       add_properties=add_properties,
                       add_class=add_class,
                       # Keys ignoring options
                       exclude_prefix=exclude_prefix,
                       exclude_postfix=exclude_postfix,
                       excludes=excludes,
                       modify_func_inplace=modify_func_inplace)

    # function decorator
    if inspect.isfunction(obj) or isinstance(obj, partial):

        if not modify_func_inplace:
            # Do not modify func inplace
            def whatablefunc(*args, **kwargs):
                return obj(*args, **kwargs)

            # Wrapper to get proper '__name__', '__doc__' and '__module__' when present
            # "wraps" won't work for partials or lambdas on python 2.x.
            # See: http://bugs.python.org/issue3445

            update_in_wrapper = [method for method in WRAPPER_ASSIGNMENTS if hasattr(obj, method)]
            if len(update_in_wrapper):
                whatablefunc = update_wrapper(wrapper=whatablefunc,
                                              wrapped=obj,
                                              assigned=update_in_wrapper)
        else:
            whatablefunc = obj

        # Adds what method
        if whatfunc is None:
            name, config_dict = callable2call(obj, closure_extractor=extract_decorated_function_from_closure)
            whatablefunc.what = partial(What, name=name, conf=config_dict, non_id_keys=excludes)
        else:
            whatablefunc.what = partial(whatfunc, whatablefunc)
        whatablefunc.what.whatami = True

        return whatablefunc

    if inspect.isbuiltin(obj):
        raise TypeError('builtins cannot be whatamised')

    # At the moment we just monkey-patch the object
    if hasattr(obj, 'what') and not is_whatable(obj):
        if force_flag_as_whatami:
            # mark this method as a whatami method
            # http://legacy.python.org/dev/peps/pep-0232/
            # http://stackoverflow.com/questions/23345005/does-pep-232-also-works-for-instance-methods
            to_annotate = obj.what.__func__ if not PY3 else obj.what
            to_annotate.whatami = True
            return obj
        else:
            raise Exception('object already has an attribute what, and is not a whatami what, if you know what I mean')

    try:
        def whatablefunc(self):
            return whatareyou(self,
                              non_id_keys=non_id_keys,
                              add_dict=add_dict,
                              add_slots=add_slots,
                              add_properties=add_properties,
                              add_class=add_class,
                              exclude_prefix=exclude_prefix,
                              exclude_postfix=exclude_postfix,
                              excludes=excludes)
        whatablefunc = whatfunc if whatfunc is not None else whatablefunc
        whatablefunc.whatami = True
        if inspect.isclass(obj):
            obj.what = whatablefunc
        else:
            obj.what = types.MethodType(whatablefunc, obj)
        return obj
    except:
        raise Exception('cannot whatamise %s' % type(obj))
