# coding=utf-8
"""Unobtrusive object (self-)identification for python.

*whatami* strives to abstract configurability and experiment identifiability in a convenient way,
by allowing each object/computation to provide a string uniquelly and consistently self-identifying
blah...

It works this way:

  - Objects provide their own ids based on "parameter=value" dictionaries.
    They do so by returning an instance of the *What* class from a method called *"what()"*.
    What objects have in turn a method called "id()" providing reasonable strings
    to describe the object.

  - whatami also provides a *Whatable* mixin and a *whatable* decorator. They can be
    used to provide automatic creation of *What* objects from the object attributes or
    functions default parameters.

  - whatami automatically generated id strings tend to be long and therefore not human-friendly

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

from __future__ import print_function, unicode_literals
from future.builtins import str
from past.builtins import basestring as basestring23
import hashlib
import inspect
import shlex
from copy import copy
from functools import partial, update_wrapper, WRAPPER_ASSIGNMENTS
import types
from arpeggio import ParserPython, Optional, ZeroOrMore, StrMatch, RegExMatch, EOF, PTNodeVisitor

from whatami.misc import callable2call, is_iterable


# http://en.wikipedia.org/wiki/Comparison_of_file_systems#Limits
MAX_EXT4_FN_LENGTH = 255


class What(object):
    """Stores and manipulates object configuration.

    Configurations are just dictionaries {key: value} that can nest and have a name.

    This helper class allows to represent configurations as (reasonable, python-like) strings.

    Parameters
    ----------
    name : string
        The name of this configuration (e.g. "RandomForest").

    configuration_dict : dictionary
        The {key:value} property dictionary for this configuration.

    nickname : string, default None
        The nickname can be an arbitrary, short, human-friendly string used to represent this configuration.

    non_id_keys : iterable (usually of strings), default None
        A list of keys that should not be considered when generating ids.
        For example: "num_threads" or "verbose" should not change results when fitting a model.

    synonyms : dictionary, default None
        We allow to use up to one synonyms for each property name, the mapping is this dictionary.
        Use with caution, as it can make hard or impossible configuration reconstruction or identification
        if badly implemented.

    sort_by_key : bool
        Sort parameters by key (in lexicographic order if keys are strings) when building the id string.

    prefix_keys : list of keys, default None
        These keys will appear first in the configuration string.
        Their order is not affected by "sorted_by_key" flag.

    postfix_keys : list of keys, default None
        These keys will appear last in the configuration string.
        Their order is not affected by "sorted_by_key" flag.
    """

    def __init__(self,
                 name,
                 configuration_dict,
                 nickname=None,
                 # ID string building options
                 non_id_keys=None,
                 synonyms=None,
                 sort_by_key=True,
                 prefix_keys=None,
                 postfix_keys=None):
        super(What, self).__init__()
        self.name = name
        self.configdict = configuration_dict
        self._nickname = None
        self.nickname = nickname
        self._prefix_keys = prefix_keys if prefix_keys else []
        self._postfix_keys = postfix_keys if postfix_keys else []
        self._sort_by_key = sort_by_key
        # Synonyms to allow more concise representations
        self._synonyms = {}
        if synonyms is not None:
            for longname, shortname in synonyms.items():
                self.set_key_synonym(longname, shortname)
        # Keys here won't make it to the configuration string unless explicitly asked for
        if not non_id_keys:
            self._non_ids = set()
        elif is_iterable(non_id_keys):
            self._non_ids = set(non_id_keys)
        else:
            raise Exception('non_ids must be None or an iterable')

    # ---- Magics

    def __eq__(self, other):
        """Two configurations are equal if they have the same name and parameters."""
        return hasattr(other, 'name') and self.name == other.name and \
            hasattr(other, 'configdict') and self.configdict == other.configdict

    def __getattr__(self, item):
        """Allow to retrieve configuration values using dot notation over Configuration objects."""
        return self.configdict[item]

    def __getitem__(self, item):
        """Allow to retrieve configuration values using [] notation over Configuration objects."""
        return self.configdict[item]

    def __str__(self):
        """The default representation is the configuration string including non_ids keys."""
        return self.id(nonids_too=True)

    # ---- Nicknames and registered whatables (id <-> shortname -> whatable)

    # Bidirectional mapping
    _id2nickname = {}  # id -> (nickname, what)
    _nickname2id = {}  # nickname -> id

    @property
    def nickname(self):
        """Returns the nickname associated to this configuration, defaulting to the nickname in the register."""
        if self._nickname is None:
            return What._id2nickname.get(self.id(), (None,))[0]
        return self._nickname

    @nickname.setter
    def nickname(self, nickname):
        """Sets the nickname of this configuration (but do not touches )."""
        self._nickname = nickname

    def register_my_nickname(self, save_what=False):
        if self.nickname is not None:
            What.register_nickname(self.nickname, self.id(), save_what=save_what)

    def nickname_or_id(self, nonids_too=False, maxlength=0):
        """Returns the nickname if it exists, otherwise it returns the id.
        In either case nonids_too and maxlength are honored.
        """
        nn = self.nickname
        if nn is None:
            nn = self.id(nonids_too=nonids_too,
                         maxlength=maxlength)
        return self._trim_too_long(nn, maxlength=maxlength)

    @staticmethod
    def register_nickname(nickname, what, save_what=False):
        """Registers a new map nickname <-> what_id, optionally saving the object "what".

        Parameters
        ----------
        nickname: string
            The new nickname for what

        what: string or whatable

        save_what: boolean, default False

        """

        if hasattr(what, 'what') and hasattr(what.what(), 'id'):
            new_id = what.what().id()
            new_what = what if save_what else None
        elif isinstance(what, basestring23):
            new_id = what
            new_what = None
        else:
            raise TypeError('"what" must be a whatable or a string, but is a %r' % type(what))

        i2n, n2i = What._id2nickname, What._nickname2id

        # Ensure a one-to-one relationship
        if nickname in n2i and not n2i[nickname] == new_id:
            raise Exception('nickname "%s" is already associated with id "%s", delete it before updating' %
                            (nickname, n2i[nickname]))
        if new_id in i2n and not i2n[new_id][0] == nickname:
            raise Exception('id "%s" is already associated with nickname "%s", delete it before updating' %
                            (new_id, i2n[new_id][0]))

        # Add binding
        i2n[new_id] = (nickname, new_what)
        n2i[nickname] = new_id

    @staticmethod
    def remove_nickname(nickname):
        what_id = What.nickname2id(nickname)
        if what_id is not None:
            del What._nickname2id[nickname]
            del What._id2nickname[what_id]

    @staticmethod
    def remove_id(what_id):
        What.remove_nickname(What.id2nickname(what_id))

    @staticmethod
    def nickname2id(nickname):
        return What._nickname2id.get(nickname)

    @staticmethod
    def id2nickname(what_id):
        return What._id2nickname.get(what_id, (None,))[0]

    @staticmethod
    def nickname2what(nickname):
        what_id = What.nickname2id(nickname)
        if what_id is not None:
            return What.id2what(what_id)
        return None

    @staticmethod
    def id2what(what_id):
        return What._id2nickname.get(what_id, (None, None))[1]

    @staticmethod
    def reset_nicknames():
        What._id2nickname = {}
        What._nickname2id = {}

    @staticmethod
    def all_nicknames():
        return sorted(What._nickname2id.items())

    # ---- Keys (property names)

    def set_key_synonym(self, name, synonym):
        """Configures the synonym for the property name."""
        self._synonyms[name] = synonym

    def key_synonym(self, name):
        """Returns the global synonym for the property name, if it is registered, otherwise the name itself."""
        return self._synonyms.get(name, name)

    def keys(self):
        """Returns the configuration keys."""
        return self.configdict.keys()

    # ---- ID string generation

    def _as_string(self, nonids_too=False):
        """Makes a best effort to represent this configuration as a string.

        Parameters
        ----------
        nonids_too : bool, default False
          if False, non-ids keys are ignored.

        Returns
        -------
        a string representing this configuration.

        Examples
        --------
        The strings look like follows:
          "rfc(n_trees=10,verbose=True,splitter="gini,verbose=True",min_split=10)"
        where
          "rfc" is the name of the configuration
          "n_trees=10" is one of the properties
          "verbose=True" is another property that should show up only if nonids_too is True
          "splitter=xxx" is another property with a nested configuration:
               "gini" is the name of the nested configuration
               "verbose=True" is a parameter of the nested configuration
          "min_split=10" is another property
        """

        # Key-value list
        def sort_kvs_fl():
            kvs = self.configdict.items()
            if self._sort_by_key:
                kvs = sorted(kvs)
            first_set = set(self._prefix_keys)
            last_set = set(self._postfix_keys)
            if len(first_set & last_set) > 0:
                raise Exception('Some identifiers (%r) appear in both first and last, they should not' %
                                (first_set & last_set))
            kvs_dict = dict(kvs)
            return [(f, kvs_dict[f]) for f in self._prefix_keys] + \
                   [kv for kv in kvs if not kv[0] in (first_set | last_set)] + \
                   [(f, kvs_dict[f]) for f in self._postfix_keys]

        kvs = sort_kvs_fl()
        return ','.join(
            '%s=%s' % (self.key_synonym(k), self._nested_string(v))
            for k, v in kvs
            if nonids_too or k not in self._non_ids)

    def id(self, nonids_too=False, maxlength=0):
        """Returns the id string (unicode) of this configuration.

        Parameters
        ----------
        nonids_too: boolean, default False
          Non-ids keys are ignored if nonids_too is False.

        malength: int, default 0
          If the id length goes over maxlength, the parameters part get replaced by its sha256.
          If <= 0, it is ignored and the full id string will be returned.
        """

        my_id = '%s(%s)' % (self.key_synonym(self.name), self._as_string(nonids_too=nonids_too))
        return self._trim_too_long(my_id, maxlength=maxlength)

    @staticmethod
    def _trim_too_long(string, maxlength=0):
        if 0 < maxlength < len(string):
            return hashlib.sha256(string).hexdigest()
        return string

    def _nested_string(self, v):
        """Returns the nested configuration string for a variety of value types."""

        if isinstance(v, What):
            return v.id()
        if hasattr(v, 'what'):
            configuration = getattr(v, 'what')
            configuration = configuration() if callable(configuration) else configuration
            if isinstance(configuration, What):
                return configuration.id()
            raise Exception('object has a "configuration" attribute, but it is not of Configuration class')
        if inspect.isbuiltin(v):  # Special message if we try to pass something like sorted or np.array
            raise Exception('Cannot determine the argspec of a non-python function (%s). '
                            'Please wrap it in a whatable' % v.__name__)
        if isinstance(v, property):
            raise Exception('Dynamic properties are not suppported.')
        if isinstance(v, partial):
            name, keywords = callable2call(v)
            config = copy(self)
            config.name = name
            config.configdict = keywords
            return config.id()
        if isinstance(v, dict):
            my_copy = copy(self)
            my_copy.name = ''
            my_copy.configdict = v
            return '{%s}' % self._nested_string(my_copy)[1:-1]
        if isinstance(v, set):
            return '{%s}' % ','.join(map(self._nested_string, sorted(v)))
        if isinstance(v, list):
            return '[%s]' % ','.join(map(self._nested_string, v))
        if isinstance(v, tuple):
            return '(%s)' % ','.join(map(self._nested_string, v))
        if inspect.isfunction(v):
            args, _, _, defaults = inspect.getargspec(v)
            defaults = [] if not defaults else defaults
            args = [] if not args else args
            params_with_defaults = dict(zip(args[-len(defaults):], defaults))
            config = copy(self)
            config.name = v.__name__
            config.configdict = params_with_defaults
            return config.id()
        if ' at 0x' in str(v):  # An object without proper representation, try a best effort
            config = copy(self)  # Careful
            config.name = v.__class__.__name__
            config.configdict = config_dict_for_object(v)
            return config.id()
        if isinstance(v, basestring23):
            return '\'%s\'' % v
        return str(v)


def whatareyou(obj,
               name=None,
               # nickname
               nickname=None,
               # ID string building options
               non_id_keys=None,
               synonyms=None,
               sort_by_key=True,
               prefix_keys=None,
               postfix_keys=None,
               # Config-dict building options
               add_dict=True,
               add_slots=True,
               add_properties=False,
               exclude_prefix='_',
               exclude_postfix='_',
               excludes=('what',)):
    """Returns a What configuration following the specified behavior.

    The meaning of all the parameters can be found in either *What* or *config_dict_for_object*.

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
        c_name, cd = callable2call(obj)
        name = c_name if name is None else name
    except:
        cd = config_dict_for_object(obj,
                                    add_dict=add_dict,
                                    add_slots=add_slots,
                                    add_properties=add_properties,
                                    exclude_prefix=exclude_prefix,
                                    exclude_postfix=exclude_postfix,
                                    excludes=excludes)
    return What(name=obj.__class__.__name__ if name is None else name,
                configuration_dict=cd,
                nickname=nickname,
                non_id_keys=non_id_keys,
                synonyms=synonyms,
                sort_by_key=sort_by_key,
                prefix_keys=prefix_keys,
                postfix_keys=postfix_keys)


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


def config_dict_for_object(obj,
                           add_dict=True,
                           add_slots=True,
                           add_properties=False,
                           exclude_prefix='_',
                           exclude_postfix='_',
                           excludes=('what',)):
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

    add_properties: boolean, default False
        Add all the attributes defined as obj @properties

    exclude_prefix: string, default '_'
        Exclude all attributes whose name starts with this string

    exclude_postix: string, default '_'
        Exclude all attributes whose name ends with this string

    excludes: string iterable, default ('what',)
        Exclude all attributes whose name appears in this collection

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
    >>> sorted(config_dict_for_object(obj, add_dict=False, add_slots=False, add_properties=False).items())
    []
    >>> sorted(config_dict_for_object(obj, add_dict=True, add_slots=False, add_properties=False).items())
    [('prop', 3)]
    >>> sorted(config_dict_for_object(obj, add_dict=True, add_slots=True, add_properties=False).items())
    [('prop', 3), ('sprop', 4)]
    >>> sorted(config_dict_for_object(obj, add_dict=True, add_slots=False, add_properties=True).items())
    [('pprop', 5), ('prop', 3)]
    >>> sorted(config_dict_for_object(obj, add_dict=True, add_slots=True, add_properties=True).items())
    [('pprop', 5), ('prop', 3), ('sprop', 4)]
    >>> sorted(config_dict_for_object(obj, add_dict=False, add_slots=True, add_properties=False).items())
    [('sprop', 4)]
    >>> sorted(config_dict_for_object(obj, add_dict=False, add_slots=False, add_properties=True).items())
    [('pprop', 5)]
    >>> sorted(config_dict_for_object(obj, add_dict=False, add_slots=True, add_properties=True).items())
    [('pprop', 5), ('sprop', 4)]
    """
    # see also dir
    cd = {}
    if add_dict:
        cd.update(_dict(obj))
    if add_slots:
        cd.update(_slotsdict(obj))
    if add_properties:
        cd.update(_propsdict(obj))
    return {k: v for k, v in cd.items() if
            (exclude_prefix and not k.startswith(exclude_prefix)) and
            (exclude_postfix and not k.endswith(exclude_postfix)) and
            k not in set(excludes)}


def is_whatable(obj):
    """Whatable objects have a method what() that takes no parameters and return a What configuration.

    Examples
    --------
    >>> wp = whatable(partial(str, a=3))
    >>> is_whatable(wp)
    True
    >>> is_whatable(str)
    False
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
        if hasattr(what_method, 'im_self') and what_method.im_self is None:
            # Unbounded method, so this comes from a class
            if hasattr(what_method, 'whatami'):
                return True
            raise Exception('Cannot infer return type for unbound method what, '
                            'please pass a %r instance instead of the class' % obj)
        return isinstance(what_method(), What)
    except:
        return False


def whatable(obj=None,
             force_flag_as_whatami=False,
             # nickname
             nickname=None,
             # ID string building options
             non_id_keys=None,
             synonyms=None,
             sort_by_key=True,
             prefix_keys=None,
             postfix_keys=None,
             # Config-dict building options
             add_dict=True,
             add_slots=True,
             add_properties=False,
             exclude_prefix='_',
             exclude_postfix='_',
             excludes=('what',)):
    """Decorates an object (also classes) to add a "what()" method.

    When decorating a callable (function, partial...), a brand new, equivalent callable will be
    retourned (thus leaving the original intact). In this case, "what" provides safe ids
    only for results obtained when the function is called with its default parameters.
    This is useful in limited cases, for example, if we have a partial to fix all parameters
    but the data.

    When decorating non-callable objects or classes, this function adds a method "what"
    that respects all the {add_dict, add_slots, add_properties, exclude_prefix, exclude_postfix
    and excludes} as per "config_dict_for_object".

    Returns
    -------
    obj with a "what" method.

    Examples
    --------
    >>> def normalize(x, mean=3, std=2):
    ...     return (x - mean) / std
    >>> cnormalize = whatable(normalize)
    >>> print(cnormalize.what().id())
    normalize(mean=3,std=2)
    >>> print(cnormalize.__name__)
    normalize
    >>> cnormalize(5)
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
                       force_flag_as_whatami=force_flag_as_whatami,
                       # nickname
                       nickname=nickname,
                       # ID string building options
                       non_id_keys=non_id_keys,
                       synonyms=synonyms,
                       sort_by_key=sort_by_key,
                       prefix_keys=prefix_keys,
                       postfix_keys=postfix_keys,
                       # Config-dict building options
                       add_dict=add_dict,
                       add_slots=add_slots,
                       add_properties=add_properties,
                       exclude_prefix=exclude_prefix,
                       exclude_postfix=exclude_postfix,
                       excludes=excludes)

    # function decorator
    if inspect.isfunction(obj) or isinstance(obj, partial):

        # Do not modify func inplace
        def whatablefunc(*args, **kwargs):
            return obj(*args, **kwargs)

        #
        # Wrapper to get proper '__name__', '__doc__' and '__module__' when present
        # "wraps" won't work for partials or lambdas on python 2.x.
        # See: http://bugs.python.org/issue3445
        #
        update_in_wrapper = [method for method in WRAPPER_ASSIGNMENTS if hasattr(obj, method)]
        if len(update_in_wrapper):
            whatablefunc = update_wrapper(wrapper=whatablefunc,
                                          wrapped=obj,
                                          assigned=update_in_wrapper)

        # Adds what method
        name, config_dict = callable2call(obj, closure_extractor=extract_decorated_function_from_closure)
        whatablefunc.what = lambda: What(name, config_dict)
        whatablefunc.what.whatami = True

        return whatablefunc

    if inspect.isbuiltin(obj):
        raise TypeError('builtins cannot be whatamised')

    # At the moment we just monkey-patch the object
    if hasattr(obj, 'what') and not is_whatable(obj):
        if force_flag_as_whatami:
            # http://legacy.python.org/dev/peps/pep-0232/
            # http://stackoverflow.com/questions/23345005/does-pep-232-also-works-for-instance-methods
            obj.what.__func__.whatami = True  # mark this method as a whatami method
            return obj
        else:
            raise Exception('object already has an attribute what, and is not a whatami what, if you know what I mean')

    try:
        def whatablefunc(self):
            return whatareyou(self,
                              nickname=nickname,
                              non_id_keys=non_id_keys,
                              synonyms=synonyms,
                              sort_by_key=sort_by_key,
                              prefix_keys=prefix_keys,
                              postfix_keys=postfix_keys,
                              add_dict=add_dict,
                              add_slots=add_slots,
                              add_properties=add_properties,
                              exclude_prefix=exclude_prefix,
                              exclude_postfix=exclude_postfix,
                              excludes=excludes)
        whatablefunc.whatami = True
        #
        # Nastily monkey patching extension types (e.g. cython cdef class)
        #   http://stackoverflow.com/questions/6738987/extension-method-for-python-built-in-types
        #   http://stackoverflow.com/questions/17267587/in-python-how-to-mock-a-c-extension-class
        # forbiddenfruit is small and cute and the comments on the issues quite interesting
        # but it is GPL, do we really want to use it?
        #
        if inspect.isclass(obj):
            try:
                obj.what = whatablefunc
            except:
                from forbiddenfruit import curse
                curse(obj, 'what', whatablefunc)
                print('WARNING, patched builtin/extension type %s' % type(obj))
        else:
            obj.what = types.MethodType(whatablefunc, obj)
            # This will anyway fail for extension types (can we make forbiddenfruit work with instances?)

        return obj
    except:
        raise Exception('cannot whatamise %s' % type(obj))


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


# DELETEME
def parse_id_string(id_string, sep='#', parse_nested=True, infer_numbers=True, remove_quotes=True):
    """
    Parses configuration string into a pair (name, configuration).

    Parameters
    ----------
    id_string : string
        The id string to parse back. Something like "name#k1=v1#k2="name#k22=v22"#k3=v3".

    sep : string, default '#'
        The string that separates 'key=value' pairs (see 'sep' in Configuration)

    parse_nested : bool, default True
        If true, a value that is a nested configuration string (enclosed in single or double quotes)
        is parsed into a pair (name, configuration) by calling recursivelly this function.

    infer_numbers : bool, default True
        If True, parse floats and ints to be numbers; if False, strings are returned instead.

    remove_quotes : bool, default True
        If True (and parse_nested is False), quotes are removed from values; otherwise quotes are kept.

    Returns
    -------
    A tuple (name, configuration). Name is a string and configuration is a dictionary.

    Examples
    --------
    >>> (name, config) = parse_id_string('rfc#n_jobs="multiple#here=100"')
    >>> print(name)
    rfc
    >>> print(len(config))
    1
    >>> print(config['n_jobs'])
    ('multiple', {'here': 100})
    """
    # Auxiliary functions
    def is_quoted(string):
        return string[0] == '"' and string[-1] == '"' or string[0] == '\'' and string[-1] == '\''

    def val_postproc(string):
        if parse_nested and is_quoted(string):
            return parse_id_string(string[1:-1],
                                   parse_nested=parse_nested,
                                   infer_numbers=infer_numbers,
                                   remove_quotes=remove_quotes)
        if remove_quotes:
            if is_quoted(string):
                string = string[1:-1]
        # a number?
        if infer_numbers:
            try:
                return int(string)
            except:
                try:
                    return float(string)
                except:
                    pass
        # quoted string?
        if string.startswith('\'') and string.endswith('\''):
            return string[1:-1]
        return string

    # Sanity checks
    if id_string.startswith(sep):
        raise Exception('%s has no name, and it should (it starts already by #)' % id_string)

    if not id_string:
        raise Exception('Cannot parse empty configuration strings')

    # Parse
    splitter = shlex.shlex(instream=id_string)  # shlex works with our simple syntax
    splitter.wordchars += '.'                   # so numbers are not splitted...
    splitter.whitespace = sep
    splitter.whitespace_split = False
    parameters = list(splitter)
    name = parameters[0]
    if not len(parameters[1::3]) == len(parameters[3::3]):
        raise Exception('Splitting has not worked. Missing at least one key or a value.')
    if not all(val == '=' for val in parameters[2::3]):
        raise Exception('Splitting has not worked. There is something that is not a = where there should be.')
    return name, dict(zip(parameters[1::3], (map(val_postproc, parameters[3::3]))))


def _build_whatami_parser(reduce_tree=False, debug=False):

    # Syntactic noise

    def list_sep():
        return StrMatch(',')

    def kv_sep():
        return StrMatch('=')

    def string_quote():
        return StrMatch('\'')

    def anything_but_quotes():
        return RegExMatch('[^\']*')  # FIXME: how is scaping hadled here?

    # Basic types

    def an_id():
        # These account for valid python 2 identifiers. Python 3 allow unicode in identifiers.
        # See:
        #   http://stackoverflow.com/questions/5474008/regular-expression-to-confirm-whether-a-string-is-a-valid-identifier-in-python
        # When/if adapting to py3, that should be handled.
        # Note also that arpeggio does not allow unicode in regexps;
        # it should be easy to implement by just allowing arbitrary re flags in RegExMatch
        return RegExMatch(r'[_A-Za-z][_a-zA-Z0-9]*')

    def a_number():
        return RegExMatch('-?\d+((\.\d*)?((e|E)(\+|-)?\d+)?)?')

    def a_string():
        return string_quote, anything_but_quotes, string_quote

    def a_true():
        return StrMatch('True')

    def a_false():
        return StrMatch('False')

    def a_bool():
        return [a_true, a_false]

    def a_none():
        return StrMatch('None')

    # Collection types: lists, tuples, dictionaries

    def list_elements():
        return value, ZeroOrMore(list_sep, value)

    def a_list():
        return StrMatch('['), Optional(list_elements), StrMatch(']')

    def a_tuple():
        return StrMatch('('), Optional(list_elements), StrMatch(')')

    def dictkv():
        return an_id, kv_sep, value

    def dict_elements():
        return dictkv, Optional(list_sep, dictkv)

    def a_dict():
        return StrMatch('{'), ZeroOrMore(dict_elements), StrMatch('}')

    # Key-values

    def value():
        return [whatami_id, a_number, a_string, a_none, a_bool, a_tuple, a_list, a_dict]

    def kv():
        return an_id, kv_sep, value

    def kvs():
        return kv, ZeroOrMore(list_sep, kv)

    # Top level

    def whatami_id():
        return an_id, StrMatch('('), Optional(kvs), StrMatch(')')

    def whatami_id_top():
        return whatami_id, EOF

    return ParserPython(whatami_id_top, reduce_tree=reduce_tree, debug=debug)


class WhatamiParser(object):

    def __init__(self, debug=False):
        super(WhatamiParser, self).__init__()
        self._parser = _build_whatami_parser(debug=debug)

    def parse(self, id_string):
        """Parses a whatami id string and returns the AST."""
        return self._parser.parse(id_string)


class WhatamiTreeVisitor(PTNodeVisitor):

    def __init__(self, defaults=True, debug=False):
        super(WhatamiTreeVisitor, self).__init__(defaults, debug)

    def visit_number(self, node, children):
        try:
            return int(node.value)
        except:
            return float(node.value)


def configuration_as_string(obj):
    """Returns the configuration of obj as a string.

    Returns
    -------
      None if obj is None
      obj is obj is a string
      obj.what().id() if obj has a what() method returning a whatable
      obj.id() if obj has an id() method
    """
    if obj is None:
        return None
    if isinstance(obj, basestring23):
        return obj
    try:
        return obj.what().id()
    except:
        try:
            return obj.id()
        except:
            raise TypeError('the object must be None, a string, have a what() method or have an id() method')


if __name__ == '__main__':

    parser = WhatamiParser(debug=False)

    print(parser.parse('rfc(n_jobs=4, n_trees=100, seed=\'rng\', deep=True)'))

    print(parser.parse('rfc(n_jobs=4, n_trees=100)'))

    print(parser.parse('rfc(n_jobs=multiple())'))

    print(parser.parse('rfc(n_jobs=multiple(here=100))'))

    print(parser.parse('C2(c1=C1(length=1,p1=\'blah\',p2=\'bleh\'), name=\'roxanne\')'))

    print(parser.parse('C2(c1=C1(length=1, p1=\'blah\', p2=\'bleh\'), name=\'roxanne\')'))

    print(parser.parse('rfc(n_jobs=4, n_trees=100, seed=2, name=\'mola\')'))

    print(parser.parse("KMeans(init='k-means++', max_iter=300, n_clusters=12, n_init=10,"
                       "precompute_distances=True, random_state=None, tol=0.0001, verbose=0)"))

    print(parser.parse('test(mola=[1, 2,         3, True, False])'))

    norm_id = 'Normalizer(norm=\'l1\')'
    kmeans_id = "KMeans(init='k-means++',max_iter=300,n_clusters=12,n_init=10," \
                "precompute_distances=True,random_state=None,tol=0.0001,verbose=0)"
    pipeline_id = "Pipeline(steps=[('norm', %s), ('kmeans', %s)])" % (norm_id, kmeans_id)
    print(parser.parse(pipeline_id))

#
# TODO: simple nested_string for numpy arrays, pandas dataframes and the like
#       we could go for hashes for big ones and other custom reprs depending on their nature
#       since we do not want to depend on these libes, we need to branch code for when they are
#       not present, or just add a pligin mechanism
#
