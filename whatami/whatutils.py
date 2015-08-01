# coding=utf-8
"""Some utilities built on top of the `whatami.What`, `whatami.whatable` and `whatami.parse_whatid` machinery."""

# Authors: Santi Villalba <sdvillal@gmail.com>
# Licence: BSD 3 clause

from operator import itemgetter

from past.builtins import basestring as basestring23

from whatami import parse_whatid, whatareyou, What
from whatami import whatable
from whatami.what import is_whatable


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
    if isinstance(obj, basestring23):
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


def flatten_what(what):
    """Returns two lists: keys and values.

    keys is a list of tuples, each tuple being able to address a parameter of what
    values is a list with the value corresponding to each corresponding key in the keys array

    Examples
    --------
    >>> what = whatareyou(lambda x=1, y=(1,2,{None: 3}): None)
    >>> keys, values = flatten_what(what)
    >>> keys
    [('x',), ('y',), ('y', 0), ('y', 1), ('y', 2), ('y', 2, None)]
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
            kvs = sorted(what.conf.items())
        elif isinstance(what, (list, tuple)):
            kvs = enumerate(what)
        elif isinstance(what, dict):
            kvs = sorted(what.items())
        else:
            kvs = ()
        for k, v in kvs:
            k = partial_k + (k,)
            flattened_keys.append(k)
            flattened_values.append(v)
            flatten(v, flattened_keys, flattened_values, k)
        return flattened_keys, flattened_values
    # pity that python recursion is terribly inefficient, we could convert this to tailrec
    return flatten(what, [], [], ())


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
