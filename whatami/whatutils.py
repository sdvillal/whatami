# coding=utf-8
"""Some utilities built on top of the `whatami.What`, `whatami.whatable` and `whatami.parse_whatid` machinery."""

# Authors: Santi Villalba <sdvillal@gmail.com>
# Licence: BSD 3 clause

from __future__ import print_function
from future.utils import string_types

import inspect
from itertools import chain

from operator import itemgetter
from arpeggio import NoMatch

from whatami.parsers import parse_whatid, build_oldwhatami_parser
from whatami.what import whatable, whatareyou, What, is_whatable


def what2id(obj):
    """Returns the configuration of obj as a string.

    Returns
    -------
      None if obj is None
      obj if obj is a string
      obj.what().id() if obj has a what() method returning a whatable
      obj.id() if obj has an id() method
      whatareyou(obj).id() otherwise
    """
    if obj is None:
        return None
    if isinstance(obj, string_types):
        return obj
    try:
        return obj.what().id()
    except:
        try:
            return obj.id()
        except:
            return whatareyou(obj).id()


# An alias for whatami.parse_whatid
id2what = parse_whatid


def id2dict(whatid):
    """
    Makes a dictionary out of a whatami id.

    The dictionary has two keys, 'whatami_name' and 'whatami_conf'.

    This should be suitable to store using json/yaml/... without custom converters.

    Parameters
    ----------
    whatid : string
      a whatami id string
    """
    what = id2what(whatid)
    return {'whatami_name': what.name,
            'whatami_out_name': what.out_name,
            'whatami_conf': {k: (v if not isinstance(v, What) else v.to_dict())
                             for k, v in what.conf.items()}}


def obj2what(obj,
             # ID string building options
             non_id_keys=None,
             # Config-dict building options
             add_dict=True,
             add_slots=True,
             add_properties=True,
             # Keys ignoring options
             exclude_prefix='_',
             exclude_postfix='_',
             excludes=('what',)):
    """Returns returns a best-guess for a suitable `What` for the obj:
     - `obj.what()` if obj is a `whatable`
     - otherwise invokes `whatareyou` on the object with the provided options.

    Examples
    --------
    >>> print(obj2what(whatable(id2what)).id())
    parse_whatid(parser=None,visitor=None)
    >>> print(obj2what(id2what).id())
    parse_whatid(parser=None,visitor=None)
    >>> print(obj2what(id2what, excludes=('parser',)).id())
    parse_whatid(visitor=None)
    """
    if is_whatable(obj):  # do not move this to whatareyou, or we face infinite recursion
        return obj.what()
    return whatareyou(obj,
                      non_id_keys=non_id_keys,
                      add_dict=add_dict,
                      add_slots=add_slots,
                      add_properties=add_properties,
                      # Keys ignoring options
                      exclude_prefix=exclude_prefix,
                      exclude_postfix=exclude_postfix,
                      excludes=excludes)


def whatvalues(what, keys=()):
    """Returns a tuple with the values assigned to keys in the the what.what() What object.
    Examples
    --------
    >>> whatvalues(obj2what(id2what), ('parser', 'visitor'))
    (None, None)
    >>> whatvalues(obj2what(id2what), 'parser')
    (None,)
    """
    if not isinstance(keys, tuple):
        keys = (keys,)
    return tuple(what[key] for key in keys)


def sort_whats(whats, *keys):
    """
    Sorts a list of What objects according to the value of some parameters.
    Examples
    --------
    >>> ids = ["Lagged(fex=distcorr(), lag=%d, response='acceleration', stimulus='force')" % lag
    ...        for lag in range(-2, 3)][::-1]
    >>> whats = list(map(id2what, ids))
    >>> whats_sorted, values = sort_whats(whats, 'lag')
    >>> [what['lag'] for what in whats]
    [2, 1, 0, -1, -2]
    >>> list(val for (val,) in values)
    [-2, -1, 0, 1, 2]
    >>> [what['lag'] for what in whats_sorted]
    [-2, -1, 0, 1, 2]
    """
    values = [whatvalues(what, keys) for what in whats]
    return tuple(zip(*[(whatid, value) for value, whatid in sorted(zip(values, whats), key=itemgetter(0))]))


def sort_whatids(whatids, *keys):
    """
    Sorts a list of whatami identifiers according to the value of some parameters.

    Examples
    --------
    >>> ids = ["Lagged(fex=distcorr(), lag=%d, response='acceleration', stimulus='force')" % lag
    ...        for lag in range(-2, 3)][::-1]
    >>> ids_sorted, values = sort_whatids(ids, 'lag')
    >>> [what['lag'] for what in map(id2what, ids)]
    [2, 1, 0, -1, -2]
    >>> list(val for (val,) in values)
    [-2, -1, 0, 1, 2]
    >>> [what['lag'] for what in map(id2what, ids_sorted)]
    [-2, -1, 0, 1, 2]
    """
    whats = map(id2what, whatids)  # if this is bottleneck, allow to pass what themselves
    values = [whatvalues(what, keys) for what in whats]
    return tuple(zip(*[(whatid, value) for value, whatid in sorted(zip(values, whatids), key=itemgetter(0))]))


def call2what(depth=1, non_id_keys=None):
    """
    Returns a What instance with information about the locals of the caller at depth.

    With the current implementation this could not work on interpreters other than cpython.

    Parameters
    ----------
    depth : int, default 1
      The depth of the desired caller in the stack; 1 is the immediate caller of call2what

    non_id_keys : string iterable, default None
      What variables of the locals to consider as non-id when creating the What object.

    Examples
    --------
    >>> def f(x, y=3, z=5):
    ...     j = 33
    ...     print('With all locals', call2what().id())
    ...     print('Only keywords', call2what(non_id_keys=['x', 'j']).id())
    ...     return j, x + y + z
    >>> _ = f(2, z=12)
    With all locals f(j=33,x=2,y=3,z=12)
    Only keywords f(y=3,z=12)
    """
    # this would probably break on interpreters other than CPython
    frame, _, _, name, _, _ = inspect.stack()[depth]
    # we could probably be (too) clever here and get only the function parameter values
    # also we could add a parameter to automatically grab only keywords... for next iteration
    conf_dict = frame.f_locals
    return What(name, conf=conf_dict, non_id_keys=non_id_keys)


def _get_or_none(what, key):
    try:
        return what[key]
    except KeyError:
        return None


def _key2colname(key):
    return '_'.join(map(str, key)) if isinstance(key, (tuple, list)) else key


def match_whatids(whatids, template_whatid, ignored_keys=(),
                  non_ids_too=False, collections_too=False, recursive=True):
    """
    Select the whatids that match the template but for some keys.

    Matching whatids will have exactly the same keys as the template
    and exactly the same values but for the keys indicated in `free_keys`.

    Parameters
    ----------
    whatids : iterator of strings
      The strings we will match to the template.

    template_whatid : string
      The whatami id string we will match

    ignored_keys : iterator of strings and tuples of strings
      The keys that do not need to match for a string to be selected.

    non_ids_too : boolean, default False
      If True, include also non id keys

    collections_too : boolean, default False
      If True, include also keys that address members of python lists, tuples and dictionaries

    recursive : boolean, default True
      If True, recurse into nested What and collections

    Returns
    -------
    A list of matching whatids.

    Examples
    --------
    >>> template = "A(x='x',y=B(x='yx'))"
    >>> whatids = (template,
    ...            "NotA(x='x',y=B(x='yx'))",
    ...            "A(x='notx',y=B(x='yx'))",
    ...            "A(x='x',y=B(x='notbx'))",
    ...            "A(x='notx',y=B(x='notbx'))",
    ...            "A(x='x',y=NotB(x='yx'))",
    ...           )
    >>> match_whatids(whatids, template, ignored_keys=())
    ["A(x='x',y=B(x='yx'))"]
    >>> match_whatids(whatids, template, ignored_keys=('x',))
    ["A(x='x',y=B(x='yx'))", "A(x='notx',y=B(x='yx'))"]
    >>> match_whatids(whatids, template, ignored_keys=(('y', 'x'),))
    ["A(x='x',y=B(x='yx'))", "A(x='x',y=B(x='notbx'))"]
    >>> match_whatids(whatids, template, ignored_keys=('y',))
    ["A(x='x',y=B(x='yx'))", "A(x='x',y=B(x='notbx'))", "A(x='x',y=NotB(x='yx'))"]
    """

    # Slow but somehow clear implementation ahead, based on What.flatten
    # Alternatives: nasty recursion, make flatten take a visitor that can abort...

    template_what = id2what(template_whatid)
    template_name = template_what.name
    template_keys, template_values = template_what.flatten(non_ids_too=non_ids_too,
                                                           collections_too=collections_too,
                                                           recursive=recursive)

    def ignore_key(key, ignored_keys=set(ignored_keys)):
        if key in ignored_keys:
            return True
        if isinstance(key, tuple):
            partial_key = key[:-1] if len(key) > 1 else key[0]
            return ignore_key(partial_key)
        return False

    def not_ignored_values(keys, values):
        return [(value.name, value.out_name) if isinstance(value, What) else value
                for key, value in zip(keys, values) if not ignore_key(key)]

    def partial_match(what,
                      template_values=not_ignored_values(template_keys, template_values)):
        if what.name != template_name:
            return False
        keys, values = what.flatten(non_ids_too=non_ids_too,
                                    collections_too=collections_too,
                                    recursive=recursive)
        return (template_keys == keys and
                not_ignored_values(keys, values) == template_values)

    return [whatid for whatid in whatids if partial_match(id2what(whatid))]


def whatid2columns(df, whatid_col, columns=None, prefix='', postfix='', inplace=True):
    """
    Extract values from whatami id strings into new columns in a pandas dataframe.

    Parameters
    ----------
    df : pandas DataFrame
      Should contain a column "whatid_col"

    whatid_col : string
      The name of the column where the whatami id strings are stored.

    columns : list of strings or list of tuples of strings, default None
      The coordinates of the parameters to extract from the whatami ids (usually a string)
      If None, all the top-level parameters of the id string will be extracted.

    prefix : string
      The name of the new columns will be prefixed with this string (if None, no prefix)

    postfix : string
      The name of the new columns will be followed by this string (if None, no postfix)

    inplace : boolean, default True
      If False, make a copy of the dataframe and add the columns there; otherwise add the new columns to df.

    Returns
    -------
    df itself or a copy if inplace is False.
    """
    # parsing is slow, cache the Whats
    whats = {whatid: id2what(whatid) for whatid in df[whatid_col].unique()}

    if columns is None:
        columns = sorted(set(chain.from_iterable(what.keys() for what in whats.values())), key=_key2colname)

    prefix = '' if prefix is None else prefix
    postfix = '' if postfix is None else postfix

    if not inplace:
        df = df.copy()

    for column in columns:
        column_name = _key2colname(column)
        if isinstance(column, list):
            column = tuple(column)
        df[prefix + column_name + postfix] = df[whatid_col].apply(
            lambda whatid: _get_or_none(whats[whatid], column))

    return df


def whatadd(what, key, values):
    """Returns a list of ids setting key to the specified values.

    Parameters
    ----------
    what : What object
      It won't be modified
    key : string
      The key to set the values on
    values : list of objects
      The values to set key to in the configuration dictonary of what

    Returns
    -------
    A list of ids generated from what by setting key to the different values.

    Examples
    --------
    >>> what = What('permen', conf={'order': 2})
    >>> print('\\n'.join(whatadd(what, 'out', ['A', 'B'])))
    permen(order=2,out='A')
    permen(order=2,out='B')
    >>> print(what.id())
    permen(order=2)
    >>> print('\\n'.join(whatadd(what, 'order', ['A', 'B'])))
    Traceback (most recent call last):
    ...
    ValueError: "order" already exists as a key in the id
    """
    what = what.copy()
    if key in what.conf:
        raise ValueError('"%s" already exists as a key in the id' % key)
    return [what.set(key, value).id() for value in values]

# --- Maintenance

OLD_WHATID_PARSER = None


def oldid2what(oldwhatid):
    """Parses an old-style whatami id into a What object.

    Examples
    --------
    >>> old_id = "out=acc_to_target#GoingTowards#im=True#positions=('x', 'y')#targets=(-0.1, -0.1)"
    >>> what = oldid2what(old_id)
    >>> print(what.id())
    GoingTowards(im=True,out='acc_to_target',positions=('x','y'),targets=(-0.1,-0.1))
    >>> old_id = "GoingTowards#im=True#positions=('x', 'y')#targets=('trg_x', 'trg_y')"
    >>> what = oldid2what(old_id)
    >>> print(what.id())
    GoingTowards(im=True,positions=('x','y'),targets=('trg_x','trg_y'))
    >>> old_id = "out=acc#GoingTowards#im=True#positions=('x', 'y')#targets=('trg_x', 'trg_y')#out='vel'"
    >>> what = oldid2what(old_id)
    Traceback (most recent call last):
    ...
    ValueError: whatid defines out ambiguously ("acc" and "vel")
    """
    global OLD_WHATID_PARSER
    if OLD_WHATID_PARSER is None:
        OLD_WHATID_PARSER = build_oldwhatami_parser()
    out = None
    if oldwhatid.startswith('out='):
        out, _, oldwhatid = oldwhatid.partition('#')
        out = out[4:]

    what = id2what(oldwhatid, parser=OLD_WHATID_PARSER)

    if out is not None:
        if 'out' in what.conf:
            raise ValueError('whatid defines out ambiguously ("%s" and "%s")' % (out, what['out']))
        what.conf['out'] = out

    return what


def id2whatami4(oldwhatid):
    """
    >>> print(id2whatami4("out=vel_to_target#GoingTowards#im=True#positions=('x', 'y')#targets=('trg_x', 'trg_y')"))
    GoingTowards(im=True,out='vel_to_target',positions=('x','y'),targets=('trg_x','trg_y'))
    >>> print(id2whatami4("velocity"))
    velocity
    """
    try:
        return oldid2what(oldwhatid).id()
    except NoMatch:
        return oldwhatid
