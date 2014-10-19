# coding=utf-8
"""A jumble of seemingly useful stuff."""

# Authors: Santi Villalba <sdvillal@gmail.com>
# Licence: BSD 3 clause

import datetime
import inspect
from functools import partial


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
    values that are fixed by either default values or the partial application of the function.

    Examples
    --------
    >>> callable2call(partial)
    ('partial', {})

    >>> callable2call(partial(map))
    ('map', {})

    >>> callable2call(partial(map, function=str))
    ('map', {'function': <type 'str'>})

    >>> callable2call(partial(partial(map, function=str), iterable1=()))
    ('map', {'function': <type 'str'>, 'iterable1': ()})

    >>> callable2call(lambda x: x)
    ('<lambda>', {})

    >>> callable2call(lambda x=5: x)
    ('<lambda>', {'x': 5})
    """
    def callable2call_recursive(c, positional=None, keywords=None):
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
            keywords = dict(zip(args[-len(defaults):], defaults) + keywords.items())  # N.B. order matters
            keywords_set = set(keywords.keys())
            if len(keywords_set - args_set) > 0:
                raise Exception('Some partial %r keywords are not parameters of the function %s' %
                                (keywords_set - args_set, c.__name__))
            if len(args_set) - len(keywords_set) < len(positional):
                raise Exception('There are too many positional arguments indicated '
                                'for the number of unbound positional parameters left.')
            return c.__name__, keywords
        if isinstance(c, partial):
            pkeywords = c.keywords if c.keywords is not None else {}
            return callable2call_recursive(
                c.func,
                positional=positional + list(c.args),                  # N.B. order matters
                keywords=dict(pkeywords.items() + keywords.items()))   # N.B. order matters
        if hasattr(c, '__call__'):
            # No way to get the argspec from anything arriving here (builtins and the like...)
            return c.__name__, keywords
        raise Exception('Only callables (partials, functions, builtins...) are allowed, %r is none of them' % c)
    return callable2call_recursive(c)


def is_iterable(v):
    """Checks whether an object is iterable or not."""
    try:
        iter(v)
    except:
        return False
    return True


def is_closure(c):
    """Checks whether an object is a python closure."""
    return inspect.isfunction(c) and c.__closure__ is not None


def internet_time(ntpservers=('europe.pool.ntp.org', 'ntp-0.imp.univie.ac.at')):
    """Makes a best effort to retrieve current UTC time from reliable internet sources.
    Returns a string like "Thu, 13 Mar 2014 11:35:41 UTC"
    """
    # Maybe also parse from, e.g., the webpage of the time service of the U.S. army
    try:
        import ntplib
        for server in ntpservers:
            response = ntplib.NTPClient().request(server, version=3)
            dt = datetime.datetime.utcfromtimestamp(response.tx_time)
            return dt.strftime('%a, %d %b %Y %H:%M:%S UTC')
    except ImportError:
        return None
