# coding=utf-8
"""Simple implementations of central registries for whatami ids, nicknames, synonyms and contexts."""


class WhatamiRegistry(object):

    # Bidirectional mapping
    _id2nickname = {}  # id -> (nickname, what)
    _nickname2id = {}  # nickname -> id

    @staticmethod
    def nickname_or_id(whatid):
        """Returns the nickname if it exists, otherwise it returns the id.
        In either case nonids_too and maxlength are honored.
        """
        return WhatamiRegistry._nickname2id.get(whatid, whatid)

    @staticmethod
    def register_nickname(nickname, what, save_what=False, overwrite=False):
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
