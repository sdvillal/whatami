whatami: unintrusive object self-identification for python
==========================================================

|Pypi Version| |Build Status| |Coverage Status|

About
-----

Whatami is an attempt to abstract configurability and experiment
identifiability in a convenient way.

It works this way:

-  Objects provide their own ids based on parameters=value dictionaries.
   They do so by returning an instance of the *Configuration* class from
   a method called *"what()"* (and that's all)

-  Optionally, this package provides a *Configurable* class that can be
   inherited to provide automatic creation of Configuration objects from
   the class dictionary (and optionally slots). All attributes will be
   considered part of the configuration, except for those whose names
   start or end by '\_'.

Example
-------

.. code:: python

    from whatami.config import Configuration, Configurable

    # Objects of this class provide a configuration
    class DuckedConfigurable(object):
        def __init__(self, quantity, name, company=None, verbose=True):
            self.quantity = quantity
            self.name = name
            self.company = company
            self.verbose = verbose

        def what(self):
            return Configuration('ducked', {'quantity': self.quantity, 'name': self.name, 'company': self.company})

    duckedc = DuckedConfigurable(33, 'salty-lollypops', verbose=False)
    # The configuration id string helps consistency by sorting by key alphanumeric order
    print duckedc.what().id()
    # u"ducked#company=None#name='salty-lollypops'#quantity=33"

    # Inheriting from Configurable makes objects gain a what() method
    # In this case, what() is infered automatically
    class Company(Configurable):
        def __init__(self, name, city, verbose=True):
            super(Company, self).__init__()
            self.name = name
            self.city = city
            self._verbose = verbose  # not part of config
            self.social_reason_ = '%s S.A., %s' % (name, city)  # not part of config
    cc = Company(name='Chupa Chups', city='Barcelona')
    cc.what().id()
    u"Company#city='Barcelona'#name='Chupa Chups'"
    # We can nest configurations...
    duckedc = DuckedConfigurable(33, 'salty-lollypops', company=cc, verbose=False)
    print duckedc.what().id()
    # ducked#company="Company#city='Barcelona'#name='Chupa Chups'"#name='salty-lollypops'#quantity=33

.. |Build Status| image:: https://travis-ci.org/sdvillal/whatami.svg?branch=master
   :target: https://travis-ci.org/sdvillal/whatami
.. |Coverage Status| image:: https://img.shields.io/coveralls/sdvillal/whatami.svg
   :target: https://coveralls.io/r/sdvillal/whatami
.. |Pypi Version| image:: https://badge.fury.io/py/whatami.svg
   :target: http://badge.fury.io/py/whatami