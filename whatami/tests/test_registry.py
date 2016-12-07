# coding=utf-8

# Authors: Santi Villalba <sdvillal@gmail.com>
# Licence: BSD 3 clause

from __future__ import absolute_import

from whatami import call_dict
from ..what import whatable
from ..registry import WhatamiRegistry, Recorder

import pytest


@pytest.fixture()
def registry():
    return WhatamiRegistry()


WHAT2NICKS = ['rfc0']


@pytest.fixture(params=WHAT2NICKS, ids=WHAT2NICKS)
def what2nick(request):
    if request.param == 'rfc0':
        @whatable
        def rfc(x, y=3, z='xyz'):  # pragma: no cover
            return x, y, z
        whatid = "rfc(y=3,z='xyz')"
        nick = 'rfc0'
        return rfc, whatid, nick
    raise ValueError('unknown fixture "%s"' % request.param)  # pragma: no cover


def test_register(registry, what2nick):

    what, whatid, nick = what2nick

    # register and access
    with pytest.raises(ValueError):
        registry.register(what, None)
    with pytest.raises(ValueError):
        registry.register(None, nick)
    assert what == registry.register(what=what, nickname=nick)
    assert nick == registry.nick_or_id(what)
    assert whatid == registry.nick2id(nick)

    # do not allow double registration
    with pytest.raises(Exception) as excinfo:
        registry.register(what, 'YOUSHALLNOTPASS')
    assert 'id "%s" is already associated with nickname "%s", delete it before updating' % (whatid, nick) \
           in str(excinfo.value)

    with pytest.raises(Exception) as excinfo:
        registry.register('YOUSHALLNOTPASS()', nick)
    assert 'nickname "%s" is already associated with id "%s", delete it before updating' % (nick, whatid) \
           in str(excinfo.value)


def test_list(registry, what2nick):
    what, whatid, nick = what2nick
    registry.register(what=what, nickname=nick)
    assert registry.list() == [(nick, whatid)]


def test_remove(registry, what2nick):

    what, whatid, nick = what2nick

    # remove by nickname
    assert what == registry.register(what, nick)
    assert registry.list() == [(nick, whatid)]
    registry.remove(nickname=nick)
    assert registry.list() == []

    # remove by whatid
    assert what == registry.register(what, nick)
    assert registry.list() == [(nick, whatid)]
    registry.remove(what=what)
    assert registry.list() == []

    # remove by both need to match the entry
    assert what == registry.register(what, nick)
    assert registry.list() == [(nick, whatid)]
    with pytest.raises(ValueError):
        registry.remove(what=what, nickname='NO')
    assert registry.list() == [(nick, whatid)]
    with pytest.raises(ValueError):
        registry.remove(what='NO()', nickname=nick)

    # remove does not accept None parameters
    with pytest.raises(ValueError) as excinfo:
        registry.remove()
    assert 'at least one of nickname or what must be provided' == str(excinfo.value)


def test_reset(registry, what2nick):
    what, whatid, nick = what2nick
    assert what == registry.register(what, nick)
    assert registry.list() == [(nick, whatid)]
    registry.reset()
    assert registry.list() == []


def test_recorder_basic():
    rec = Recorder(name='registry', id_column_name='name', register='me')
    assert rec.name == 'registry'
    # curried add
    keep = rec.add(keep=True)
    drop = rec.add(keep=False)
    rec.add('first', afield=3)
    keep('keepme', anotherfield=4)
    drop('dropme', why='ugliness')
    assert rec.get('first') == [{'name': 'first', 'afield': 3, 'register': 'me'}]
    assert rec.get('keepme') == [{'name': 'keepme', 'keep': True, 'anotherfield': 4, 'register': 'me'}]
    assert rec.get('dropme') == [{'name': 'dropme', 'keep': False, 'why': 'ugliness', 'register': 'me'}]
    # partial add
    pkeep = rec.padd(keep=True)
    records = pkeep('keepmepartial', why='pity')
    expectation = {'keepmepartial': {'name': 'keepmepartial',
                                     'keep': True, 'why': 'pity', 'register': 'me'}}
    assert records == expectation
    assert rec.get('keepmepartial') == [expectation['keepmepartial']]
    # multiple adds on one call
    records = pkeep(['a', 'b'], why='why not', price=[3, 2])
    assert records == {
        'a': {'name': 'a', 'keep': True, 'why': 'why not', 'price': 3, 'register': 'me'},
        'b': {'name': 'b', 'keep': True, 'why': 'why not', 'price': 2, 'register': 'me'},
    }
    # disallow duplicates
    with pytest.raises(Exception) as excinfo:
        rec.add('a')
    assert '"a" is already in the registry' in str(excinfo.value)


def test_recorder_inheritance():
    class Books(Recorder):
        # noinspection PyMethodOverriding
        def add(self, ids, title, author, collection, **fields):
            return super(Books, self).add(**call_dict())
    books = Books()
    # noinspection PyArgumentList
    reverte_alatriste = books.add(author='Arturo', collection='Alatriste')
    reverte_alatriste('ala1', 'El Capitan Alatriste')
    reverte_alatriste(['ala2', 'ala3'],
                      ['Limpieza de sangre', 'El sol de Breda'],
                      sequel=True)
    ala1, ala2, ala3 = books.get('ala1', 'ala2', 'ala3')
    assert ala1 == {'author': 'Arturo',
                    'collection': 'Alatriste',
                    'id': 'ala1',
                    'title': 'El Capitan Alatriste'}
    assert ala2 == {'author': 'Arturo',
                    'collection': 'Alatriste',
                    'id': 'ala2',
                    'title': 'Limpieza de sangre',
                    'sequel': True}
    assert ala3 == {'author': 'Arturo',
                    'collection': 'Alatriste',
                    'id': 'ala3',
                    'title': 'El sol de Breda',
                    'sequel': True}


def test_recorder_inheritance_naming_contract_check():
    with pytest.raises(Exception) as excinfo:
        class BadRecorder(Recorder):
            def add(self, bad_name, **fields):
                return super(BadRecorder, self).add(bad_name, **fields)
    assert "function 'add' is missing ['ids'] positional args" in str(excinfo.value)

# TODO: get the tests in Recorder doctest here, and expand with more (corner) cases
