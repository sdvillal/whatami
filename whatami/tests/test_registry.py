# coding=utf-8

# ---- Fixtures and teardown


def teardown_function(_):
    """After each run, wipe nicknames registry."""
    What.reset_nicknames()


def test_whatable_nickname(c1):

    class NicknamedConfigurable(object):
        def what(self):
            c = whatareyou(self)
            c.nickname = 'bigforest'
            return c

    # nicknamed configurations
    assert NicknamedConfigurable().what().nickname == 'bigforest'
    assert NicknamedConfigurable().what().nickname_or_id() == 'bigforest'

    # not nicknamed configurations
    assert c1.what().nickname is None
    assert c1.what().nickname_or_id() == "C1(length=1,p1='blah',p2='bleh')"


def test_regnick_with_what(c1):

    # saving the what...
    What.register_nickname('c1', c1, save_what=True)
    assert c1.what().nickname == 'c1'
    assert What.id2what(c1.what().id()) == c1
    assert What.nickname2what('c1') == c1
    assert What.id2nickname(c1.what().id()) == 'c1'
    assert What.nickname2id('c1') == c1.what().id()
    # not saving the what...
    What.remove_nickname('c1')
    What.register_nickname('c1', c1, save_what=False)
    assert What.id2what(c1.what().id()) is None
    assert What.nickname2what('c1') is None
    # and of course not there if we haven't registered...
    assert What.nickname2what('c2') is None
    assert What.id2what('c2') is None


def test_regnick_only_what():
    with pytest.raises(Exception) as excinfo:
        What.register_nickname('c1', 1)
    expected = '"what" must be a whatable or a string, but is a <type \'int\'>' if not PY3 else \
        '"what" must be a whatable or a string, but is a <class \'int\'>'
    assert str(excinfo.value) == expected


def test_regnick_remove_id(c1):
    What.register_nickname('c1', c1, save_what=True)
    # remove by id...
    What.remove_id(c1.what().id())
    # nothing in there
    assert What.nickname2id('c1') is None
    assert What.id2nickname(c1.what().id()) is None
    assert What.id2what(c1.what().id()) is None


def test_regnick_do_not_reregister(c1):
    What.register_nickname('c1', c1)
    # do not allow update...
    What.register_nickname('c1', c1, save_what=False)
    with pytest.raises(Exception) as excinfo:
        What.register_nickname('c1', 'blahblehblih')
    assert str(excinfo.value) == 'nickname "c1" is already associated with id ' \
                                 '"C1(length=1,p1=\'blah\',p2=\'bleh\')", delete it before updating'
    with pytest.raises(Exception) as excinfo:
        What.register_nickname('c2', c1.what().id())
    assert str(excinfo.value) == 'id "%s" is already associated with nickname "c1", delete it before updating' %\
                                 c1.what().id()
    # no problem if we remove it first...
    What.remove_nickname('c1')
    assert c1.what().nickname is None
    What.register_nickname('c1', c1)
    assert c1.what().nickname == 'c1'


def test_regnick_self(c1):
    # self-registration
    what = c1.what()
    what.nickname = 'c1'
    what.register_my_nickname()
    what.nickname = None
    assert what.nickname == 'c1'
    assert c1.what().nickname == 'c1'  # Recall that a call to what() always return a new "What" object

    # no problem on re-registering the same map
    what.register_my_nickname()
    assert what.nickname == 'c1'
    assert c1.what().nickname == 'c1'
    What.remove_nickname('c1')
    assert what.nickname is None
    assert c1.what().nickname is None


def test_regnick_all_nicknames():
    # listing nicknames, reset
    What.register_nickname('one', 'oneblah')
    What.register_nickname('two', 'twoblah')
    assert What.all_nicknames() == [('one', 'oneblah'), ('two', 'twoblah')]
    What.reset_nicknames()
    assert What.all_nicknames() == []
