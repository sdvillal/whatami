# coding=utf-8
"""Simple implementations of central registries for whatami ids, nicknames, synonyms and contexts."""
from whatami import what2id


class WhatamiRegistry(object):
    """Bidirectional mapping, one-to-one, no persistence ATM (all should be in code), string to string (no thunks)."""

    def __init__(self, name='master'):
        super(WhatamiRegistry, self).__init__()
        self.name = name
        self._id2nick = {}
        self._nick2id = {}

    def register(self, what, nickname, overwrite=False):
        """Registers the nickname for the id of what."""

        whatid = what2id(what)

        i2n, n2i = self._id2nick, self._nick2id

        if not overwrite:
            # Ensure a one-to-one relationship; probably a nickname pointing to more than one id would be more useful
            if nickname in n2i and not n2i[nickname] == whatid:
                raise Exception('nickname "%s" is already associated with id "%s", delete it before updating' %
                                (nickname, n2i[nickname]))
            if whatid in i2n and not i2n[whatid] == nickname:
                raise Exception('id "%s" is already associated with nickname "%s", delete it before updating' %
                                (whatid, i2n[whatid][0]))

        # Add binding
        i2n[whatid] = nickname
        n2i[nickname] = whatid

    def list(self):
        """Returns a sorted list of tuples (nick, id)."""
        return sorted(self._nick2id.items())

    def remove(self, nickname=None, whatid=None):
        """Removes the entry corresponding to nickname or whatid.
        If both are provided, they must correspond to a single entry.
        """
        if nickname is None and whatid is None:
            return
        elif nickname is None:
            nickname = self.id2nick(whatid)
        elif whatid is None:
            whatid = self.nick2id(nickname)
        else:
            assert self.id2nick(whatid) == nickname
            assert self.nick2id(nickname) == whatid
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
        return self._nick2id.get(whatid, whatid)

    def reset(self):
        """Removes all entries in the registry."""
        self._id2nick = {}
        self._nick2id = {}
