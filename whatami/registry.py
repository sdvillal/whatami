# coding=utf-8
"""Simple implementations of central registries for whatami ids, nicknames, synonyms and contexts."""

# Authors: Santi Villalba <sdvillal@gmail.com>
# Licence: BSD 3 clause

from __future__ import absolute_import, print_function
from future.utils import string_types, with_metaclass

from functools import partial
from collections import OrderedDict

from .whatutils import what2id
from .misc import is_iterable, call_dict, decorate_some
from .plugins import has_pandas, pd, toolz


class WhatamiRegistry(object):
    """Bidirectional mapping, one-to-one, no persistence ATM (all should be in code), string to string (no thunks)."""

    def __init__(self, name='master'):
        super(WhatamiRegistry, self).__init__()
        self.name = name
        self._id2nick = {}
        self._nick2id = {}

    def register(self, what, nickname):
        """Registers the nickname for the id of what; returns `what` in the interest of fluent interfaces."""

        if what is None:
            raise ValueError('what cannot be None')
        if nickname is None:
            raise ValueError('nickname cannot be None')

        whatid = what2id(what)

        i2n, n2i = self._id2nick, self._nick2id

        # Ensure a one-to-one relationship; probably a nickname pointing to more than one id would be more useful
        if nickname in n2i and not n2i[nickname] == whatid:
            raise Exception('nickname "%s" is already associated with id "%s", delete it before updating' %
                            (nickname, n2i[nickname]))
        if whatid in i2n and not i2n[whatid] == nickname:
            raise Exception('id "%s" is already associated with nickname "%s", delete it before updating' %
                            (whatid, i2n[whatid]))

        # Add binding
        i2n[whatid] = nickname
        n2i[nickname] = whatid

        # Fluent
        return what

    def list(self):
        """Returns a sorted list of tuples (nick, id)."""
        return sorted(self._nick2id.items())

    def remove(self, nickname=None, what=None):
        """Removes the entry corresponding to nickname or what.
        If both are provided, they must correspond to a single entry.
        """
        whatid = None if what is None else what2id(what)
        if nickname is None and whatid is None:
            raise ValueError('at least one of nickname or what must be provided')
        elif nickname is None:
            nickname = self.id2nick(whatid)
        elif what is None:
            whatid = self.nick2id(nickname)
        else:
            old_whatid = self.nick2id(nickname)
            old_nick = self.id2nick(nickname)
            if old_whatid != whatid or old_nick != nickname:
                raise ValueError('both whatid "%s"=="%s" and nickname "%s"=="%s" identities must hold' %
                                 (whatid, old_whatid, nickname, old_nick))
        del self._nick2id[nickname]
        del self._id2nick[whatid]

    def nick2id(self, nickname):
        """Maps a nickname to the corrensponding id, returning None if the pair is not in the registry."""
        return self._nick2id.get(nickname, None)

    def id2nick(self, whatid):
        """Maps an id to the corrensponding nickname, returning None if the pair is not in the registry."""
        return self._id2nick.get(whatid, None)

    def nick_or_id(self, what):
        """Returns the nickname if it exists, otherwise it returns the id."""
        whatid = what2id(what)
        return self._id2nick.get(whatid, whatid)

    def reset(self):
        """Removes all entries in the registry."""
        self._id2nick = {}
        self._nick2id = {}


# --- Registration helpers

class _DefaultDict(dict):
    """Like collections.defaultdict, but does not add missing keys to the dictionary."""
    def __init__(self, default, **kwargs):
        super(_DefaultDict, self).__init__(**kwargs)
        self.default = default

    def __getitem__(self, key):
        try:
            return super(_DefaultDict, self).__getitem__(key)
        except KeyError:
            return self.default


class Recorder(with_metaclass(decorate_some(add=toolz.curry))):
    """Manual data input helper."""

    def __init__(self,
                 name=None,
                 idextractor=lambda x: str(x),
                 id_column_name=None):
        self._registry = OrderedDict()
        self.name = name
        self.idextractor = idextractor
        self.columns = {}
        self.id_column_name = id_column_name

    def add_column(self, column, default=None):
        self.columns[column] = default

    def add(self, ids, **fields):
        # Allow to add a single id
        ids = [ids] if isinstance(ids, string_types) else ids
        # Get whatami ids (maybe this should be left to the caller)
        if self.idextractor is not None:
            ids = list(map(self.idextractor, ids))
        # Expand iterables to field assignments
        config_dict = {param: self._params2dict(ids, value) for param, value in fields.items()}
        # Add each id in turn...
        for an_id in ids:
            # Check id uniqueness
            if an_id in self._registry:
                raise Exception('"%s" is already in the registry' % an_id)
            # Create record
            record = {param: values[an_id] for param, values in config_dict.items()}
            # Add id column to record
            if self.id_column_name is not None:
                if self.id_column_name in record:
                    raise Exception('ID column would replace %r' % self.id_column_name)
                record[self.id_column_name] = an_id
            # Add record to registry
            self._registry[an_id] = record

    def padd(self, add=None, **kwargs):
        """Drop-in alternative to curried versions of self.add, using partials."""
        if add is None:
            add = self.add
        return partial(add, **kwargs)

    def get(self, an_id):
        return self._registry.get(an_id, None)

    def to_df(self):
        return pd.DataFrame.from_dict(self._registry, orient='index').loc[self._registry.keys()]

    @staticmethod
    def _params2dict(names, params, warn=False):
        if isinstance(params, dict):
            return params
        if isinstance(params, string_types):
            return {name: params for name in names}
        if is_iterable(params):
            if warn and len(names) != len(params):
                print('WARNING: number of names is different to the number of parameters (%d != %d)' %
                      (len(names), len(params)))
            return _DefaultDict(None, **dict(zip(names, params)))
        return _DefaultDict(default=params)
