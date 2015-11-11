# coding=utf-8
"""A jumble of seemingly useful stuff."""

# Authors: Santi Villalba <sdvillal@gmail.com>
# Licence: BSD 3 clause

from __future__ import unicode_literals, absolute_import
from functools import partial
from itertools import chain
import datetime
import inspect
from collections import OrderedDict
from socket import gethostname


# http://en.wikipedia.org/wiki/Comparison_of_file_systems#Limits
MAX_EXT4_FN_LENGTH = 255


# --- Introspection tools

def curry2partial(obj):
    """Transforms toolz/cytoolz curry sugar into standard partials."""
    try:
        return partial(obj.func, *obj.args, **obj.keywords)
    except (AttributeError, TypeError):
        return obj


def callable2call(c, closure_extractor=lambda c: c):
    """
    Extracts the (actual) function name and set parameters from a callable.

    Manages partials and makes a best effort to manage anonymous functions and non-introspectable objects.


    Parameters
    ----------
    c : callable
        The function, partial, builtin or, in general, any callable.

    closure_extractor : function c -> function, default c -> c
        A function that will be executed whenever c is a closure.
        It should return a function to be analyzed by inspect.
        This can be useful to specify custom behavior with, e.g., decorated functions

    Returns
    -------
    a pair (function_name, parameter_dict), where the parameter_dict is a
    (possibly empty) dictionary {parameter_name: default_value} with the parameter
    values that are known by either default values or the partial application of the function.

    *N.B. these parameters are fixed iff they are set by a partial application, otherwise,
    for default parameters, it is up to the caller not to redefine them.*

    Examples
    --------
    >>> callable2call(partial)
    ('partial', {})

    >>> callable2call(partial(map))
    ('map', {})

    >>> name, params = callable2call(partial(map, function=str))
    >>> name
    'map'
    >>> 'str' in str(params['function'])
    True

    >>> name, params = callable2call(partial(partial(map, function=str), iterable1=()))
    >>> name
    'map'
    >>> 'str' in str(params['function'])
    True
    >>> () == params['iterable1']
    True

    >>> name, params = callable2call(lambda x: x)
    >>> print(name)
    lambda
    >>> params
    {}

    >>> name, params = callable2call(lambda x=5: x)
    >>> print(name)
    lambda
    >>> params
    {'x': 5}
    """
    def callable2call_recursive(c, positional=None, keywords=None):
        c = curry2partial(c)
        if keywords is None:
            keywords = {}
        if positional is None:
            positional = []
        if inspect.isfunction(c):
            if is_closure(c):  # allow custom behavior with closures
                c = closure_extractor(c)
            args, _, _, defaults = inspect.getargspec(c)
            defaults = [] if not defaults else defaults
            args = [] if not args else args
            args_set = set(args)
            # Check that everything is fine...
            keywords = dict(chain(zip(args[-len(defaults):], defaults), keywords.items()))  # N.B. order matters
            pos2keyword = dict(zip(args[:len(positional)], positional))  # N.B. order matters
            keywords_set = set(keywords.keys())
            if len(keywords_set - args_set) > 0:
                raise ValueError('Some partial %r keywords are not parameters of the function %s' %
                                 (keywords_set - args_set, c.__name__))
            if len(set(pos2keyword.keys()) & set(keywords.keys())) > 0:
                raise ValueError('Some arguments are indicated both by position and name (%r)' %
                                 sorted(set(pos2keyword.keys()) & set(keywords.keys())))
            if len(args_set) - len(keywords_set) < len(positional):
                raise ValueError('There are too many positional arguments indicated '
                                 'for the number of unbound positional parameters left.')
            return c.__name__.replace('<', '').replace('>', ''), \
                dict(list(keywords.items()) + list(pos2keyword.items()))
        if isinstance(c, partial):
            pkeywords = c.keywords if c.keywords is not None else {}
            return callable2call_recursive(
                c.func,
                positional=positional + list(c.args),                  # N.B. order matters
                keywords=dict(chain(pkeywords.items(), keywords.items())))   # N.B. order matters
        if hasattr(c, '__call__'):
            # No way to get the argspec from anything arriving here (builtins and the like...)
            return c.__name__, keywords
        raise ValueError('Only callables (partials, functions, builtins...) are allowed, %r is none of them' % c)
    return callable2call_recursive(c)


def all_subclasses(cls):
    """Returns a list with all the subclasses of cls in the current python session.

    Examples
    --------
    Some C inheritance...
    >>> bool in all_subclasses(int)
    True
    >>> int in all_subclasses(bool)
    False

    This is recursive...
    >>> class my_str(str):
    ...     pass
    >>> my_str in all_subclasses(str)
    True
    """
    return cls.__subclasses__() + [g for s in cls.__subclasses__() for g in all_subclasses(s)]


def _dict(obj):
    """Returns a copy of obj.__dict___ (or {} if obj has not __dict__).

    Examples
    --------
    >>> from future.moves.collections import UserDict
    >>> _dict(UserDict())
    {'data': {}}
    >>> class NoSlots(object):
    ...     def __init__(self):
    ...         self.prop = 3
    >>> ns = NoSlots()
    >>> _dict(ns)
    {'prop': 3}
    >>> _dict(ns) is not ns.__dict__
    True
    >>> class Slots(object):
    ...     __slots__ = ['prop']
    ...     def __init__(self):
    ...         self.prop = 3
    >>> _dict(Slots())
    {}
    """
    try:
        return obj.__dict__.copy()
    except:
        return {}


def _slotsdict(obj):
    """Returns a dictionary with all attributes in obj.__slots___ (or {} if obj has not __slots__).

    Examples
    --------
    >>> from future.moves.collections import UserDict
    >>> _slotsdict(UserDict())
    {}
    >>> class Slots(object):
    ...     __slots__ = 'prop'
    ...     def __init__(self):
    ...         self.prop = 3
    ...     @property
    ...     def prop2(self):
    ...         return 5
    >>> _slotsdict(Slots())
    {'prop': 3}
    """
    descriptors = inspect.getmembers(obj.__class__, inspect.isdatadescriptor)
    return {dname: value.__get__(obj) for dname, value in descriptors if
            '__weakref__' != dname if inspect.ismemberdescriptor(value)}


def _propsdict(obj):
    """Returns the @properties in an object.
    Example:
    >>> class PropertyCarrier(object):
    ...     __slots__ = 'prop2'
    ...     def __init__(self):
    ...         self.prop2 = 3
    ...     @property
    ...     def prop(self):
    ...         return self.prop2
    ...     @prop.setter
    ...     def prop(self, prop):
    ...         self.prop2 = prop
    >>> _propsdict(PropertyCarrier())
    {'prop': 3}
    """
    descriptors = inspect.getmembers(obj.__class__, inspect.isdatadescriptor)
    # All data descriptors except slots and __weakref__
    # See: http://docs.python.org/2/reference/datamodel.html
    return {dname: value.__get__(obj) for dname, value in descriptors if
            '__weakref__' != dname and not inspect.ismemberdescriptor(value)}


def _classdict(obj):
    """Returns a copy of the class dictionary, or {} if it does not exist.
    Example:
    >>> class C(object):
    ...     x = 3
    ...     __slots__ = 'y'
    >>> class D(C):
    ...     x = 'x'
    ...     z = 'z'
    >>> c = _classdict(C())
    >>> print(c['x'])
    3
    >>> d = _classdict(D())
    >>> print(d['x'])
    x
    >>> print(d['z'])
    z
    >>> d = D()
    >>> d.z = 42
    >>> d = _classdict(D())
    >>> print(d['z'])
    z
    """
    # N.B. this will include all methods down to object
    # we could avoid it ala
    #   http://stackoverflow.com/questions/4241171/inspect-python-class-attributes
    # but I feel that can be brittle
    # for example, one can wonder why removing only member from object and not also
    # from other superclasses like object...
    return dict(inspect.getmembers(obj.__class__))


def trim_dict(cd, exclude_prefix='_', exclude_postfix='_', excludes=('what',)):
    """Removes keys from a dictionary if they are (pre/post)fixed or fully match forbidden strings.

    Parameters
    ----------
    cd: dictionary
        The dictionary to trim

    exclude_prefix: string, default '_'
        Exclude all attributes whose name starts with this string

    exclude_postix: string, default '_'
        Exclude all attributes whose name ends with this string

    excludes: string iterable, default ('what',)
        Exclude all attributes whose name appears in this collection

    Returns
    -------
    A copy of cd with only the allowed keys.
    """
    return {k: v for k, v in cd.items() if
            (exclude_prefix and not k.startswith(exclude_prefix)) and
            (exclude_postfix and not k.endswith(exclude_postfix)) and
            k not in set(excludes)}


def config_dict_for_object(obj,
                           add_dict=True,
                           add_slots=True,
                           add_properties=True,
                           add_class=False):
    """Returns a dictionary with obj attributes defined in __dict__, __slots__ or as @properties.
    Does not fail in case any of these are not defined.

    Parameters
    ----------
    obj: anything
        The object to introspect

    add_dict: boolean, default True
        Add all the attributes defined in obj.__dict__

    add_slots: boolean, default True
        Add all the attributes defined in obj.__slots__

    add_properties: boolean, default True
        Add all the attributes defined as obj @properties

    add_class: boolean, default False
        Add all the attributes defined in the class

    Returns
    -------
    A dictionary {atribute: value}

    Examples
    --------
    >>> class NoSlots(object):
    ...     def __init__(self):
    ...         self.prop = 3
    ...         self._hidden = 5
    ...         self.hidden_ = 5
    >>> class Slots(NoSlots):
    ...     __slots__ = 'sprop'
    ...     def __init__(self):
    ...         super(Slots, self).__init__()
    ...         self.sprop = 4
    >>> class Props(Slots):
    ...     def __init__(self):
    ...         super(Props, self).__init__()
    ...     @property
    ...     def pprop(self):
    ...         return 5
    >>> obj = Props()
    >>> sorted(trim_dict(config_dict_for_object(obj, add_dict=False, add_slots=False, add_properties=False)).items())
    []
    >>> sorted(trim_dict(config_dict_for_object(obj, add_dict=True, add_slots=False, add_properties=False)).items())
    [('prop', 3)]
    >>> sorted(trim_dict(config_dict_for_object(obj, add_dict=True, add_slots=True, add_properties=False)).items())
    [('prop', 3), ('sprop', 4)]
    >>> sorted(trim_dict(config_dict_for_object(obj, add_dict=True, add_slots=False, add_properties=True)).items())
    [('pprop', 5), ('prop', 3)]
    >>> sorted(trim_dict(config_dict_for_object(obj, add_dict=True, add_slots=True, add_properties=True)).items())
    [('pprop', 5), ('prop', 3), ('sprop', 4)]
    >>> sorted(trim_dict(config_dict_for_object(obj, add_dict=False, add_slots=True, add_properties=False)).items())
    [('sprop', 4)]
    >>> sorted(trim_dict(config_dict_for_object(obj, add_dict=False, add_slots=False, add_properties=True)).items())
    [('pprop', 5)]
    >>> sorted(trim_dict(config_dict_for_object(obj, add_dict=False, add_slots=True, add_properties=True)).items())
    [('pprop', 5), ('sprop', 4)]
    """
    # see also dir
    cd = {}
    if add_class:
        cd.update(_classdict(obj))
    if add_dict:
        cd.update(_dict(obj))
    if add_slots:
        cd.update(_slotsdict(obj))
    if add_properties:
        cd.update(_propsdict(obj))
    return cd


def is_closure(c):
    """Checks whether an object is a python closure."""
    return inspect.isfunction(c) and c.__closure__ is not None


def extract_decorated_function_from_closure(c):
    """
    Extracts a function from closure c iff the closure only have one cell mapping to a function
    and also has a method 'what'.
    (this ad-hoc behavior could help to play well with the whatable decorator)
    """
    closure = c.__closure__
    if closure is not None and len(closure) == 1 and hasattr(c, 'what'):
        func = closure[0].cell_contents
        if inspect.isfunction(func):
            return extract_decorated_function_from_closure(func)
    return c


def is_iterable(v):
    """Checks whether an object is iterable or not."""
    try:
        iter(v)
    except:
        return False
    return True


# --- Tools to make aggregation of information from functions and whatables easier

def mlexp_info_helper(title,
                      data_setup=None,
                      model_setup=None,
                      eval_setup=None,
                      exp_function=None,
                      comments=None,
                      itime=None):
    """Creates a dictionary describing machine learning experiments.

    Parameters:
      - title: the title for the experiment
      - data_setup: a "what" for the data used in the experiment
      - model_setup: a "what" for the model used in the experiment
      - eval_setup: a "what" for the evaluation method used in the experiment
      - exp_function: the function in which the experiment is defined;
                      its source text lines will be stored
      - comments: a string with whatever else we need to say
      - itime: a callable that will provide the date from a reliable internet source
               (e.g. an NTP server or http://tycho.usno.navy.mil/cgi-bin/timer.pl)

    (Here "what" means None, a string, an object providing a "what method" or an object providing an "id" method.)

    Return:
      An ordered dict mapping strings to strings with all or part of:
      title, data_setup, model_setup, eval_setup, fsource, date, idate (internet datetime), host, comments
    """
    from .whatutils import what2id
    info = OrderedDict((
        ('title', title),
        ('data_setup', what2id(data_setup)),
        ('model_setup', what2id(model_setup)),
        ('eval_setup', what2id(eval_setup)),
        ('fsource', inspect.getsourcelines(exp_function) if exp_function else None),
        ('date', datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')),
        ('idate', None if itime is None else itime()),
        ('host', gethostname()),
        ('comments', comments),
    ))
    return info
