# coding=utf-8

# Authors: Santi Villalba <sdvillal@gmail.com>
# Licence: BSD 3 clause

from __future__ import absolute_import

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


def test_recorder():

    rec = Recorder(name='registry', id_column_name='name')
    assert rec.name == 'registry'
    keep = rec.add(keep=True)
    drop = rec.add(keep=False)
    rec.add('first', afield=3)
    keep('keepme', anotherfield=4)
    drop('dropme', why='ugliness')
    assert rec.get('first') == {'name': 'first', 'afield': 3}
    assert rec.get('keepme') == {'name': 'keepme', 'keep': True, 'anotherfield': 4}
    assert rec.get('dropme') == {'name': 'dropme', 'keep': False, 'why': 'ugliness'}
