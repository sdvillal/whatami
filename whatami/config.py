# coding=utf-8
"""An attempt to abstract configurability and experiment identifiability in a convenient way.

It works this way:

  - Objects provide their own ids based on parameters=value dictionaries.
    They do so by returning an instance of the *Configuration* class from a method called "what()"
    (and that's all)

  - Optionally, this package provides a Configurable class that can be inherited to provide automatic
    creation of Configuration objects from the class dictionary (and optionally slots). All attributes
    will be considered part of the configuration, except for those whose names start or end by '_'.

Examples
--------

>>> # Objects of this class provide a configuration
>>> class DuckedConfigurable(object):
...      def __init__(self, quantity, name, company=None, verbose=True):
...          self.quantity = quantity
...          self.name = name
...          self.company = company
...          self.verbose = verbose
...
...      def what(self):
...          return Configuration('ducked', {'quantity': self.quantity, 'name': self.name, 'company': self.company})
>>>
>>>
>>> duckedc = DuckedConfigurable(33, 'salty-lollypops', verbose=False)
>>> # The configuration id string helps consistency by sorting by key alphanumeric order
>>> duckedc.what().id()
u"ducked#company=None#name='salty-lollypops'#quantity=33"
>>> # Inheriting from Configurable makes objects gain a what() method
>>> # In this case, what() is infered automatically
>>> class Company(Configurable):
...     def __init__(self, name, city, verbose=True):
...          super(Company, self).__init__()
...          self.name = name
...          self.city = city
...          self._verbose = verbose  # not part of config
...          self.social_reason_ = '%s S.A., %s' % (name, city)  # not part of config
>>> cc = Company(name='Chupa Chups', city='Barcelona')
>>> cc.what().id()
u"Company#city='Barcelona'#name='Chupa Chups'"
>>> # Ultimately, we can nest configurables...
>>> duckedc = DuckedConfigurable(33, 'salty-lollypops', company=cc, verbose=False)
>>> print duckedc.what().id()
ducked#company="Company#city='Barcelona'#name='Chupa Chups'"#name='salty-lollypops'#quantity=33
"""

# Authors: Santi Villalba <sdvillal@gmail.com>
# Licence: BSD 3 clause

import datetime
import hashlib
import inspect
import shlex
from copy import copy
from collections import OrderedDict
from functools import partial
from socket import gethostname

from whatami.misc import callable2call, is_iterable, internet_time


# http://en.wikipedia.org/wiki/Comparison_of_file_systems#Limits
MAX_EXT4_FN_LENGTH = 255


class Configuration(object):
    """Configurations are just dictionaries {key: value} that can nest and have a name.

    This helper class allows to represent configurations as (reasonable) strings.

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

    quote_strings : boolean, default True
        If True string values will be single-quoted in the configuration string.
        This value can be overrided at anytime by specifying quote_string_values when calling to id()
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
                 postfix_keys=None,
                 quote_string_values=True):
        super(Configuration, self).__init__()
        self.name = name
        self.configdict = configuration_dict
        self.nickname = nickname
        self._prefix_keys = prefix_keys if prefix_keys else []
        self._postfix_keys = postfix_keys if postfix_keys else []
        self._sort_by_key = sort_by_key
        self._quote_strings = quote_string_values
        # Synonyms to allow more concise representations
        self._synonyms = {}
        if synonyms is not None:
            for longname, shortname in synonyms.iteritems():
                self.set_synonym(longname, shortname)
        # Keys here won't make it to the configuration string unless explicitly asked for
        if not non_id_keys:
            self._non_ids = set()
        elif is_iterable(non_id_keys):
            self._non_ids = set(non_id_keys)
        else:
            raise Exception('non_ids must be None or an iterable')

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

    def as_string(self, nonids_too=False, sep='#', quote_string_vals=None):
        """Makes a best effort to represent this configuration as a string.

        Parameters
        ----------
        nonids_too : bool, default False
          if False, non-ids keys are ignored.

        sep : string, default '#'
          the string to separate parameters; the default, '#', is a good value because
          it comes early in the ASCII table (before any alphanum character); the caveat
          is that it requires quotes when using on shell scripts
          (as usually # is the comment opening character)
          Choose carefully and be consistent.

        Returns
        -------
        a string representing this configuration.

        Examples
        --------
        The strings look like follows:
          "rfc#n_trees=10#verbose=True#splitter="gini#verbose=True"#min_split=10"
        where
          "rfc" is the name of the configuration
          "n_trees=10" is one of the properties
          "verbose=True" is another property that should show up only if nonids_too is True
          "splitter=xxx" is another property with a nested configuration:
               "gini" is the name of the nested configuration
               "verbose=True" is a parameter of the nested configuration
          "min_split=10" is another property
        """

        # String quoting policy defaults to this configuration's if not specified
        if quote_string_vals is None:
            quote_string_vals = self._quote_strings

        # Key-value list
        def sort_kvs_fl():
            kvs = self.configdict.iteritems()
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
        return sep.join(
            '%s=%s' % (self.synonym(k), self._nested_string(v, quote_string_vals=quote_string_vals))
            for k, v in kvs
            if nonids_too or k not in self._non_ids)

    def id(self, nonids_too=False, maxlength=0, quote_string_vals=None):
        """Returns the id unicode string of this configuration.

        Parameters
        ----------
        nonids_too: boolean, default False
          Non-ids keys are ignored if nonids_too is False.

        malength: int, default 0
          If the id length goes over maxlength, the parameters part get replaced by its sha256.
          If <= 0, it is ignored and the full id string will be returned.

        quote_string_vals: boolean, default None
          If True, string values will be quoted.
          If None, we use the Configuration set property.
        """
        if quote_string_vals is None:
            quote_string_vals = self._quote_strings

        if quote_string_vals is False:
            print 'Here'

        my_id = u'%s#%s' % (self.synonym(self.name), self.as_string(nonids_too=nonids_too,
                                                                    quote_string_vals=quote_string_vals))
        if 0 < maxlength < len(my_id):
            return hashlib.sha256(my_id).hexdigest()
        return my_id

    def nickname_or_id(self, nonids_too=False, maxlength=0, quote_string_vals=None):
        """Returns the nickname if it exists, otherwise it returns the id (respecting nonids_too and maxlength)."""
        if quote_string_vals is None:
            quote_string_vals = self._quote_strings
        return self.id(nonids_too=nonids_too, maxlength=maxlength, quote_string_vals=quote_string_vals) \
            if self.nickname is None else self.nickname

    def _nested_string(self, v, quote_string_vals):
        """Returns the nested configuration string for a variaety of value types."""
        def nest(string):
            return u'"%s"' % string

        if isinstance(v, Configuration):
            return nest(v.id(quote_string_vals=quote_string_vals))
        if hasattr(v, 'what'):
            configuration = getattr(v, 'what')
            configuration = configuration() if callable(configuration) else configuration
            if isinstance(configuration, Configuration):
                return nest(configuration.id(quote_string_vals=quote_string_vals))
            raise Exception('object has a "configuration" attribute, but it is not of Configuration class')
        if inspect.isbuiltin(v):  # Special message if we try to pass something like sorted or np.array
            raise Exception('Cannot determine the argspec of a non-python function (%s). '
                            'Please wrap it in a configurable' % v.__name__)
        if isinstance(v, property):
            raise Exception('Dynamic properties are not suppported.')
        if isinstance(v, partial):
            name, keywords = callable2call(v)
            config = copy(self)
            config.name = name
            config.configdict = keywords
            return nest(config.id(quote_string_vals=quote_string_vals))
        if inspect.isfunction(v):
            args, _, _, defaults = inspect.getargspec(v)
            defaults = [] if not defaults else defaults
            args = [] if not args else args
            params_with_defaults = dict(zip(args[-len(defaults):], defaults))
            config = copy(self)
            config.name = v.__name__
            config.configdict = params_with_defaults
            return nest(config.id(quote_string_vals=quote_string_vals))
        if ' at 0x' in unicode(v):  # An object without proper representation, try a best effort
            config = copy(self)  # Careful
            config.name = v.__class__.__name__
            config.configdict = config_dict_for_object(v)
            return nest(config.id(quote_string_vals=quote_string_vals))
        if isinstance(v, (unicode, basestring)):
            if quote_string_vals:
                return u'\'%s\'' % v
            return u'%s' % v
        return unicode(v)

    def set_synonym(self, name, synonym):
        """Configures the synonym for the property name."""
        self._synonyms[name] = synonym

    def synonym(self, name):
        """Returns the global synonym for the property name, if it is registered, otherwise the name itself."""
        return self._synonyms.get(name, name)

    def keys(self):
        """Returns the configuration keys."""
        return self.configdict.keys()


def _dict_or_slotsdict(obj):
    """Returns a dictionary with the properties for an object, handling objects with __slots__ defined.
    Example:
    >>> class NoSlots(object):
    ...     def __init__(self):
    ...         self.prop = 3
    >>> _dict_or_slotsdict(NoSlots())
    {'prop': 3}
    >>> class Slots(object):
    ...     __slots__ = ['prop']
    ...     def __init__(self):
    ...         self.prop = 3
    >>> _dict_or_slotsdict(Slots())
    {'prop': 3}
    """
    try:
        return obj.__dict__
    except:
        return {slot: getattr(obj, slot) for slot in obj.__slots__}


def _data_descriptors(obj):
    """Returns the data descriptors in an object (except __weakref__).
    See: http://docs.python.org/2/reference/datamodel.html
    Example:
    >>> class PropertyCarrier(object):
    ...     def __init__(self):
    ...         self._prop = 3
    ...     @property
    ...     def prop(self):
    ...         return self._prop
    ...     @prop.setter
    ...     def prop(self, prop):
    ...         self._prop = prop
    >>> _data_descriptors(PropertyCarrier())
    {'prop': 3}
    """
    descriptors = inspect.getmembers(obj.__class__, inspect.isdatadescriptor)
    return {dname: value.__get__(obj) for dname, value in descriptors if '__weakref__' != dname}


def config_dict_for_object(obj, add_descriptors=False):
    """Returns a copy of the object __dict__ (or equivalent) but for properties that start or end by '_'."""
    cd = _dict_or_slotsdict(obj)
    if add_descriptors:
        cd.update(_data_descriptors(obj))
    return {k: v for k, v in cd.iteritems()
            if not k.startswith('_') and not k.endswith('_')}


class Configurable(object):
    """A configurable object has a configuration.

    This class strives to be as little intrusive as possible and performs all its
    magic only on request (call to "configuration").

    By default, the object is introspected to get the configuration, so that:
       - the name is the class name of the object
       - the parameters are the instance variables that do not start or end with '_'
       - data descriptors (e.g. @property) are not part of the configuration


    See also
    --------
    config_dict_for_object, Configuration
    """

    __slots__ = ('_add_descriptors',)

    def __init__(self, add_descriptors=False):
        super(Configurable, self).__init__()
        self._add_descriptors = add_descriptors

    def what(self):
        """Returns a Configuration object."""
        return Configuration(
            self.__class__.__name__,
            configuration_dict=config_dict_for_object(self,
                                                      add_descriptors=self._add_descriptors))

#
# def configure(self, configuration):
#     """Configures a new object with the requested configuration.
#
#     Parameters
#     ----------
#     configuration : Configuration
#
#     Returns
#     -------
#     A new object with the requested configuration
#     """
#     raise NotImplementedError  # If wanted, concrete cases need to implement this.
#                                # For example, easy for sklearn estimators (just pass params to the constructor).
#


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
    >>> print name
    rfc
    >>> print len(config)
    1
    >>> print config['n_jobs']
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


def configuration_as_string(obj):
    """Returns the setup of obj as a string.
    (Here configurable means None, a string or an object providing an "id" method.)
    """
    if obj is None:
        return None
    if isinstance(obj, basestring):
        return obj
    try:
        return obj.id()
    except AttributeError:
        raise Exception('the object must be None, a string or have an id() method')  # TypeError


def mlexp_info_helper(title,
                      data_setup=None,
                      model_setup=None,
                      eval_setup=None,
                      exp_function=None,
                      comments=None,
                      itime=False):
    """Creates a dictionary describing machine learning experiments.

    Parameters:
      - title: the title for the experiment
      - data_setup: a configurable for the data used in the experiment
      - model_setup: a configurable for the model used in the experiment
      - eval_setup: a configurable for the evaluation method used in the experiment
      - exp_function: the function in which the experiment is defined;
                      its source text lines will be stored
      - comments: a string with whatever else we need to say
      - itime: if True we try to store UTC time from  an internet source

    (Here configurable means None, a string or an object providing an "id" method.)

    Return:
      An ordered dict mapping strings to strings with all or part of:
      title, data_setup, model_setup, eval_setup, fsource, date, idate (internet datetime), host, comments
    """
    info = OrderedDict((
        ('title', title),
        ('data_setup', configuration_as_string(data_setup)),
        ('model_setup', configuration_as_string(model_setup)),
        ('eval_setup', configuration_as_string(eval_setup)),
        ('fsource', inspect.getsourcelines(exp_function) if exp_function else None),
        ('date', datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')),
        ('idate', None if not itime else internet_time()),
        ('host', gethostname()),
        ('comments', comments),
    ))
    return info
