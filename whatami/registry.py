# coding=utf-8
"""Simple implementations of central registries for whatami ids, nicknames, synonyms and contexts."""

# Authors: Santi Villalba <sdvillal@gmail.com>
# Licence: BSD 3 clause

from __future__ import absolute_import, print_function

from copy import copy

from future.utils import string_types, with_metaclass

from functools import partial
from collections import OrderedDict, Hashable

from whatami import what2id, is_iterable, decorate_some, ensure_has_positional_args
from whatami.plugins import pd, toolz


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

    def nick2id(self, nickname):  # type: (str) -> Optional[str]
        """
        Maps a nickname to the corrensponding id-
        Returns a string or None if the pair is not in the registry.
        """
        return self._nick2id.get(nickname, None)

    def id2nick(self, whatid):  # type: (str) -> Optional[str]
        """
        Maps an id to the corrensponding nickname.
        Returns a string or None if the pair is not in the registry.
        """
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

    def __contains__(self, k):
        return isinstance(k, Hashable)


_RecorderMeta = decorate_some(add=[partial(ensure_has_positional_args, args=('ids',)),
                                   toolz.curry])


class Recorder(with_metaclass(_RecorderMeta)):
    """
    Manual data input helper and object registry.

    This is akin to a table in a relational database with primary key,
    sorted by insertion order. It allows to define how ids are extracted
    at insertion time, set default values and programmatically validate
    records and registry, and add columns. Convenience here prevails
    over performance.

    There are curried and partial versions of `add` to help defining
    default values for groups of records in a way that hopefully
    makes writing input commands convenient.

    At the moment records cannot be removed or modified.

    Parameters
    ----------
    name : string or None, default None
      The name of this recorder. Can be used to create namespaces.

    id_column_name : string, default "id"
      The name of the id string; this will be added to each record.

    id_extractor : (object)->string, default str
      A function that will extract an id string from an object, used in `add`.
      This can, for example, by `what2id`.

    record_postprocessors : list[(id, record, recorder) -> new_record] or None
      Specifies functions that will be called on each record, before it is added.
      These can modify the record, and are chained.
      The final result of the chain is added to the registry.

    column_defaults : {column: default value}
      Defines a column (aka attribute) that will appear in all records, and its default value.
      This can be also defined in the more versatile "record_postprocessors" machinery.

    Examples
    --------
    This is a simple recorder. We have added a record postprocessor that
    generates a column of encouragement. Postprocessors can be used for
    generating new columns, modifying columns and validating records and
    the whole registry.
    >>> def add_encouraging_attribute(an_id, record, _):
    ...     if 'cheer_up' in record:
    ...         raise Exception('I will decide if you are cool or not')
    ...     record['cheer up'] = '%s is cool' % an_id
    ...     return record
    >>> rec = Recorder(name='test',
    ...                id_column_name='id',
    ...                id_extractor=str,
    ...                record_postprocessors=[add_encouraging_attribute],
    ...                who='me', date='today')

    The most important duty of a Recorder object is, incredibly, to record records.
    For that we can use add. Like this:
    >>> got = rec.add('record1', age=0)
    >>> expected = {'record1': {'id': 'record1',
    ...                         'date': 'today',
    ...                         'age': 0,
    ...                         'cheer up': 'record1 is cool',
    ...                         'who': 'me'}}
    >>> got == expected
    True

    A rule always present on any recorder is that the id is unique.
    >>> rec.add('record1', age=2)
    Traceback (most recent call last):
    ...
    Exception: "record1" is already in the registry

    Convenience when writing recording statements is helped by several magic features
    of add. We can register several records with one call.
    >>> got = rec.add(['record2', 'record3'], unbox_iterables=True, age=[33, 66], type=None)
    >>> expected = {
    ...     'record2': {'age': 33,
    ...                 'date': 'today',
    ...                 'who': 'me',
    ...                 'type': None,
    ...                 'id': 'record2',
    ...                 'cheer up': 'record2 is cool'},
    ...     'record3': {'age': 66,
    ...                 'date': 'today',
    ...                 'who': 'me',
    ...                 'type': None,
    ...                 'id': 'record3',
    ...                 'cheer up': 'record3 is cool'}}
    >>> got == expected
    True

    There are several way of actually assigning iterables as values for columns.
    One is to disable iterable unboxing.
    >>> got = rec.add(['record4', 'record5'], unbox_iterables=False, age=[33, 66], type=None)
    >>> expected = {
    ...     'record4': {'age': [33, 66],
    ...                 'date': 'today',
    ...                 'who': 'me',
    ...                 'type': None,
    ...                 'id': 'record4',
    ...                 'cheer up': 'record4 is cool'},
    ...     'record5': {'age': [33, 66],
    ...                 'date': 'today',
    ...                 'who': 'me',
    ...                 'type': None,
    ...                 'id': 'record5',
    ...                 'cheer up': 'record5 is cool'}}
    >>> got == expected
    True

    The other one is to use a dictionary as the value of the column.
    >>> got = rec.add(['record6', 'record7'], unbox_iterables=True,
    ...               age={'record6': [100, 200], 'record7': 700})
    >>> expected = {
    ...     'record6': {'age': [100, 200],
    ...                 'date': 'today',
    ...                 'who': 'me',
    ...                 'id': 'record6',
    ...                 'cheer up': 'record6 is cool'},
    ...     'record7': {'age': 700,
    ...                 'date': 'today',
    ...                 'who': 'me',
    ...                 'id': 'record7',
    ...                 'cheer up': 'record7 is cool'}}
    >>> got == expected
    True

    Note that this last variant is more verbose, but allows fine-grained control
    of which value is assigned to each record for a column. It is also the only
    way to assign dictionaries to column values (sorry for the inconvenience!).
    One last thing you will appreciate in this example, not all records need
    to have the same attributes. Here 'record9' has no age attribute.
    >>> got = rec.add(['record8', 'record9'], unbox_iterables=True,
    ...               age={'record8': {'now': 100, 'tomorrow': 101}})
    >>> expected = {
    ...     'record8': {'age': {'now': 100, 'tomorrow': 101},
    ...                 'date': 'today',
    ...                 'who': 'me',
    ...                 'id': 'record8',
    ...                 'cheer up': 'record8 is cool'},
    ...     'record9': {'date': 'today',
    ...                 'who': 'me',
    ...                 'id': 'record9',
    ...                 'cheer up': 'record9 is cool'}}
    >>> got == expected
    True

    Note that if, by error, we try to enter a duplicated record, no record will
    actually be added to the registry
    >>> len(rec)
    9
    >>> rec.add(['record10', 'record10'])
    Traceback (most recent call last):
    ...
    Exception: "record10" is duplicated
    >>> len(rec)
    9

    Another constraint is that we cannot add a column named like the id column.
    >>> rec.add('record10', id='nif')
    Traceback (most recent call last):
    ...
    Exception: ID column would replace 'id'

    A nifty feature of add is that it is curried. This means that when called
    without actual `ids`, a function freezing some parameters is returned.
    >>> by_you_friday = rec.add(who='you', date='Friday')
    >>> got = by_you_friday('record10')
    >>> expected = {'record10': {'date': 'Friday',
    ...                          'who': 'you',
    ...                          'id': 'record10', 'cheer up': 'record10 is cool'}}
    >>> got == expected
    True

    Curry keeps working until `ids` is passed, so you can keep refining add variants.
    >>> by_you_friday_afternoon = by_you_friday(when='afternoon')
    >>> got = by_you_friday_afternoon('record11')
    >>> expected = {'record11': {'date': 'Friday',
    ...                          'who': 'you',
    ...                          'when': 'afternoon',
    ...                          'id': 'record11', 'cheer up': 'record11 is cool'}}
    >>> got == expected
    True

    Curry is an experimental feature but it is likely to stay with add.
    A not so powerful (but less likely to give unexpected problems) is to
    use python partials. This can be done manually using python partial,
    but Recorder also adds a thin wrapper over partial, `padd`.
    >>> by_her = rec.padd(who='she')
    >>> got = by_her('record12')
    >>> expected = {'record12': {'who': 'she',
    ...                          'date': 'today',
    ...                          'id': 'record12', 'cheer up': 'record12 is cool'}}
    >>> got == expected
    True
    >>> by_her_tomorrow = rec.padd(add=by_her, date='tomorrow')
    >>> got = by_her_tomorrow('record13')
    >>> expected = {'record13': {'who': 'she',
    ...                          'date': 'tomorrow',
    ...                          'id': 'record13', 'cheer up': 'record13 is cool'}}
    >>> got == expected
    True

    A little break from registering. What are the columns with defaults?
    >>> rec.column_defaults == {'date': 'today', 'who': 'me'}
    True

    We can at anytime add new defaults (although usually it is better to use curry)
    >>> rec.add_column_defaults(when='morning')
    >>> rec.column_defaults == {'date': 'today', 'when': 'morning', 'who': 'me'}
    True

    And we can also remove column defaults
    >>> rec.remove_column_defaults('who', 'date')
    >>> rec.column_defaults == {'when': 'morning'}
    True

    Here is the effect of playing with defaults in add.
    >>> got = rec.add('record14', comments='changed defaults')
    >>> got == {'record14': {'when': 'morning',
    ...                      'comments': 'changed defaults',
    ...                      'id': 'record14', 'cheer up': 'record14 is cool'}}
    True

    Postprocessors are a very powerful feature of recorders. They allow a
    great deal of flexibility when specifying constraints. We can ask what
    are the current recorder postprocessors

    >>> len(rec.record_postprocessors())
    1
    >>> print(what2id(rec.record_postprocessors()[0]))
    add_encouraging_attribute()

    Usually postprocessors would be added when instantiating the recorder
    and not touch anymore, as likely they encode business models. However,
    we are not here to tell you what you can and cannot do, so they can be
    manipulated at any time, even specified as a call to add. To see this,
    let's define a couple more postprocessors. Postprocessors are supposed
    to quack like (id, record) -> new_record.
    >>> # noinspection PyUnusedLocal
    ... def ensure_right_people(_, record, __):
    ...     right_people = {'me', 'you', 'her'}
    ...     if 'who' in record and record['who'] in right_people:
    ...         return record
    ...     raise Exception('"who" must be one of %r' % sorted(right_people))
    >>> def ensure_unique_encouragement(_, record, recorder):
    ...     if 'cheer up' in record and record['cheer up'] not in recorder.unique('cheer up'):
    ...         return record
    ...     raise Exception('the "cheer up" column must be unique in the registry')
    >>> new_processors = [ensure_right_people, ensure_unique_encouragement]

    The first postprocessor ensures each new record will have a "recorder" column
    and that it will be one of valid values. The second postprocessor ensures that
    new records have a "cool" column and that its value have not yet been seen
    in the registry. To make them work for our registry, we have three options.
    The first option is to use add.
    >>> with_added_rules = rec.add(record_postprocessors=new_processors)
    >>> with_added_rules('record15')
    Traceback (most recent call last):
    ...
    Exception: "who" must be one of ['her', 'me', 'you']
    >>> got = with_added_rules('record15', who='me')
    >>> expected = {'record15': {'who': 'me',
    ...                          'when': 'morning',
    ...                          'id': 'record15', 'cheer up': 'record15 is cool'}}

    By default, when specifying new postprocessors in add, they are run after
    the recorder postprocessors. We can instead override the recorder postprocessors
    so they are never run. This must be done with care.
    >>> with_overriding_rules = rec.add(record_postprocessors=new_processors,
    ...                                 override_postprocessors=True)
    >>> got = with_overriding_rules('record16', who='me')
    Traceback (most recent call last):
    ...
    Exception: the "cheer up" column must be unique in the registry

    Here overriding the postprocessors have gotten rid of the automatic generation
    of a required column, so we need to do it by hand.
    >>> got = with_overriding_rules('record16', who='me', **{'cheer up': 'I like this record'})
    >>> expected = {'record16': {'who': 'me',
    ...                          'when': 'morning',
    ...                          'id': 'record16',
    ...                          'cheer up': 'I like this record'}}

    The other two ways of modifying record postprocessors are the
    `add_record_postprocessors` and `override_record_postprocessors` methods,
    that work analogously to the related `add` parameters, but modify
    ther recorder postprocessors for good.

    We can append to the currently existing processors
    >>> rec.add_record_postprocessors(*new_processors)
    >>> len(rec.record_postprocessors())
    3
    >>> print(what2id(rec.record_postprocessors()[0]))
    add_encouraging_attribute()
    >>> print(what2id(rec.record_postprocessors()[1]))
    ensure_right_people()
    >>> print(what2id(rec.record_postprocessors()[2]))
    ensure_unique_encouragement()

    Or we can override the currently existing processors
    >>> rec.override_record_postprocessors(*new_processors)
    >>> len(rec.record_postprocessors())
    2
    >>> print(what2id(rec.record_postprocessors()[0]))
    ensure_right_people()
    >>> print(what2id(rec.record_postprocessors()[1]))
    ensure_unique_encouragement()

    Note that postprocessors only apply to new records being added. Records
    already in the registry remain unaffected by postprocessors changes.

    We can create a recorder that automatically generates sequential ids
    >>> class Counter(object):
    ...     def __init__(self):
    ...         super(Counter, self).__init__()
    ...         self.count = 0
    ...     def next(self, _):
    ...         self.count += 1
    ...         return self.count
    >>> # noinspection PyTypeChecker
    ... rec = Recorder(name='test', id_extractor=Counter().next)
    >>> rec.add(['first', 'second'])
    {1: {'id': 1}, 2: {'id': 2}}

    We can query the size of the registry using `len`
    >>> len(rec) == len(rec)
    True

    We can retrieve from the registry using [] notation or the get method
    >>> rec[1]
    [{'id': 1}]
    >>> rec.get(2)
    [{'id': 2}]
    >>> rec.get(1, 2)
    [{'id': 1}, {'id': 2}]

    The querying abilities on the Recorder class are at the moment limited,
    but we conviniently allow to get the data as a pandas dataframe using
    the `to_df` method.

    >>> df = rec.to_df()
    >>> len(df)
    2
    >>> list(df.columns)
    ['id']

    Subclassing `Recorder` can be a useful way to help data input and
    specify contracts. There is only one catch on doing so: if you override
    the `add` method, make sure that it has a positional parameter
    called "ids" (if that is not the case an exception will be raised on class)
    definition and that you call super's add. Let's create a Recorder subclass.

    >>> # noinspection PyMethodOverriding, PyUnusedLocal
    ... class CountryRecorder(Recorder):
    ...     def add(self, there_is_no_ids_here, continent, **columns):
    ...         return super(CountryRecorder, self).add(there_is_no_ids_here,
    ...                                                 continent=continent, **columns)
    Traceback (most recent call last):
    ...
    Exception: function 'add' is missing ['ids'] positional args; name positional args correctly

    That failed because there is not a parameter called "ids" in the redefinition of `add`.
    This however will work:
    >>> # noinspection PyMethodOverriding, PyUnusedLocal
    ... class CountryRecorder(Recorder):
    ...     def add(self, ids, continent, **columns):
    ...         return super(CountryRecorder, self).add(ids, continent=continent, **columns)
    >>> countries = CountryRecorder()
    >>> got = countries.add(['Lesotho', 'Malta'], continent=['Africa', 'Europe?'])
    >>> expected = {'Lesotho': {'continent': 'Africa', 'id': 'Lesotho'},
    ...             'Malta': {'continent': 'Europe?', 'id': 'Malta'}}
    >>> got == expected
    True
    """

    def __init__(self,
                 name=None,
                 id_column_name='id',
                 id_extractor=str,
                 record_postprocessors=None,
                 **column_defaults):
        self._registry = OrderedDict()  # Tempted to move to python >= 3.6...
        self.name = name
        self.id_extractor = id_extractor
        if not isinstance(id_column_name, string_types):
            raise ValueError('id_column_name must be a string')  # pragma: no cover
        self.id_column_name = id_column_name
        self._column_defaults = column_defaults
        self._record_postprocessors = [] if not record_postprocessors else record_postprocessors

    # --- Column defaults

    @property
    def column_defaults(self):
        """Returns a copy of the current column defaults in the registry."""
        return self._column_defaults.copy()

    def add_column_defaults(self, **columns_defaults):
        """Adds or updates column defaults."""
        self._column_defaults.update(columns_defaults)

    def remove_column_defaults(self, *columns):
        """Removes the default value for the specified columns."""
        for column in columns:
            if column in self._column_defaults:
                del self._column_defaults[column]

    # --- Record postprocessors

    def record_postprocessors(self):
        """Returns a copy of the default record postprocessor chain."""
        return copy(self._record_postprocessors)

    def add_record_postprocessors(self, *postprocessors):
        """Adds record postprocessors at the end of the chain."""
        self._record_postprocessors += postprocessors

    def override_record_postprocessors(self, *postprocessors):
        """Override the current record postprocessors."""
        self._record_postprocessors = postprocessors

    # --- Adding records machinery

    @staticmethod
    def _params2dict(ids, params, unbox_iterables, warn=False):
        """
        Helper function to allow specifying more than one record in one call to add.
        Returns a dictionary {name: param}.
        """
        if isinstance(params, dict):
            return params
        if isinstance(params, string_types):
            return {name: params for name in ids}
        if is_iterable(params) and unbox_iterables:
            if warn and len(ids) != len(params):  # pragma: no cover
                print('WARNING: number of names is different to the number of parameters (%d != %d)' %
                      (len(ids), len(params)))
            return _DefaultDict(None, **dict(zip(ids, params)))
        return _DefaultDict(default=params)

    def add(self, ids, unbox_iterables=True,
            record_postprocessors=None, override_postprocessors=False,
            **columns):
        """
        Adds new records.

        Note that to keep curry convenience, any overriding `add` should:
          - Have a parameter called `ids` (this is programmatically enforced).
          - Invoke `super.add`.

        Note that currently there is no way to add columns named "ids",
        "unbox_iterables", "record_postprocessors" and "override_postprocessors".
        This is a small concesion to convenience.

        Parameters
        ----------
        ids : Any
          The ids for the records to be added.
          This can be a single object (when adding a single record) or an iterable of objects.
          They will be passed to `self.id_extractor` to extract an appropriate id.
          They will be added to each record in the attribute `self.id_column_name`.

        unbox_iterables : bool, default True
          What to do with parameters that are iterables and multiple ids are provided.
          If True, parameters that are iterables will be zipped to the ids.
          If False, parameters that are iterables will be added verbatim
          The exception lies with dictionaries, that have different semantics. See examples.
          Use the variant that makes writing data input scripts more efficient.

        record_postprocessors : list[(id, record) -> new_record] or None, default None
          Custom postprocessors for the record being added.
          These will either completelly override or be run after the recorder postprocessors,
          depending on the value of `override_postprocessors`.

        override_postprocessors : bool, default False
          If True and `record_postprocessors` is not None, override the recorder record postprocessors.
          If False and `record_postprocessors` is not None, append to the recorder record postprocessors.
          Use overriding with caution, you probably want global contracts to hold always.

        columns : kwargs {column: value}
          The values for the columns (AKA fields, attributes) of the records.

        Returns
        -------
        A list with the added record.
        This is a curried function, when called with any parameter but without specifying
        ids, a function with frozen parameters and column defaults will be returned.

        Examples
        --------
        See the `Recorder` class docstring.
        """
        # Allow to add a single id
        if isinstance(ids, string_types) or not is_iterable(ids):
            ids = [ids]
        # Get whatami ids (maybe this should be left to the caller)
        if self.id_extractor is not None:
            ids = list(map(self.id_extractor, ids))
        # Expand iterables to field assignments
        config_dict = {param: self._params2dict(ids, value, unbox_iterables)
                       for param, value in columns.items()}
        # Add each id in turn...
        records = {}
        for an_id in ids:
            # Check id uniqueness
            if an_id in self._registry:
                raise Exception('"%s" is already in the registry' % an_id)
            if an_id in records:
                raise Exception('"%s" is duplicated' % an_id)
            # Create record
            record = {param: values[an_id] for param, values in config_dict.items()
                      if an_id in values}
            # Add id column to record
            if self.id_column_name in record:
                raise Exception('ID column would replace %r' % self.id_column_name)
            record[self.id_column_name] = an_id
            # Add default values
            for column, default in self._column_defaults.items():
                if column not in record:
                    record[column] = default
            # Postprocess record (validation, synthetic columns and more)
            postprocessors = list(self._record_postprocessors)
            if record_postprocessors is not None:
                if not override_postprocessors:
                    postprocessors += list(record_postprocessors)
                else:
                    postprocessors = list(record_postprocessors)
            # noinspection PyTypeChecker
            for function in postprocessors:
                record = function(an_id, record, self)
            # Add record to registry
            records[an_id] = record
        # All correct, commit
        self._registry.update(records)
        return records

    def padd(self, add=None, **kwargs):
        """Drop-in alternative to curried versions of self.add, using partials."""
        if add is None:
            add = self.add
        return partial(add, **kwargs)

    # --- Record retrieval

    def __getitem__(self, item):
        return self.get(item)

    def get(self, *ids):
        """Returns a list with the records identified by ids, skipping ids not in the registry."""
        return [self._registry.get(an_id) for an_id in ids if an_id in self._registry]

    def __len__(self):
        return len(self._registry)

    def unique(self, column):
        """Returns a set with the unique values of a column in the registry."""
        return {record[column] for record in self._registry.values() if column in record}

    # --- Other utils

    def to_df(self):
        """
        Returns a pandas dataframe with records in rows and as many columns as different attributes.
        It is sorted by insertion order.
        """
        return pd.DataFrame.from_dict(self._registry, orient='index').loc[self._registry.keys()]
