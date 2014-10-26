whatami: unintrusive object self-identification for python
==========================================================

|Pypi Version| |Build Status| |Coverage Status|

About
-----

Whatami is an attempt to abstract configurability and experiment
identifiability in a convenient way. It does so by leveraging object
introspection and defining a simple, flexible and consistent API
that python objects can adhere to.


It works this way:

-  Objects provide their own ids based on parameters=value dictionaries.
   They do so by returning an instance of the *Configuration* class from
   a method called *"what()"* (and that's all).

-  Optionally, this package provides a *Whatable* mixin that can be inherited
   to provide automatic creation of *What* objects from the class dictionary
   (or *WhatableD* to do so from slots or propertes). All attributes will be
   considered part of the configuration, except for those whose names start or
   end by '\_'.


Example
-------

.. code:: python

    # Objects of this class provide a configuration (What object)
    class DuckedConfigurable(object):
        def __init__(self, quantity, name, company=None, verbose=True):
           self.quantity = quantity
           self.name = name
           self.company = company
           self.verbose = verbose

        def what(self):
            return What('ducked', {'quantity': self.quantity, 'name': self.name, 'company': self.company})

    duckedc = DuckedConfigurable(33, 'salty-lollypops', verbose=False)

    # The configuration id string sorts by key alphanumeric order, helping id consistency
    print duckedc.what().id()
    # ducked#company=None#name='salty-lollypops'#quantity=33

    # Inheriting from Whatable makes objects gain a what() method;
    # in this case, what() is infered automatically
    class Company(Whatable):
        def __init__(self, name, city, verbose=True):
            super(Company, self).__init__()
            self.name = name
            self.city = city
            self._verbose = verbose  # not part of config
            self.social_reason_ = '%s S.A., %s' % (name, city)  # not part of config
    cc = Company(name='Chupa Chups', city='Barcelona')
    print cc.what().id()
    # Company#city='Barcelona'#name='Chupa Chups'

    # Ultimately, we can nest whatables...
    duckedc = DuckedConfigurable(33, 'salty-lollypops', company=cc, verbose=False)
    print duckedc.what().id()
    # ducked#company="Company#city='Barcelona'#name='Chupa Chups'"#name='salty-lollypops'#quantity=33

    # Also a function decorator is provided - use with caution
    @whatable
    def buy(company, price=2**32, currency='euro'):
        return '%s is now mine for %g %s' % (company.name, price, currency)
    print buy.what().id()
    # buy#currency='euro'#price=4294967296


.. |Build Status| image:: https://travis-ci.org/sdvillal/whatami.svg?branch=master
   :target: https://travis-ci.org/sdvillal/whatami
.. |Coverage Status| image:: https://img.shields.io/coveralls/sdvillal/whatami.svg
   :target: https://coveralls.io/r/sdvillal/whatami
.. |Pypi Version| image:: https://badge.fury.io/py/whatami.svg
   :target: http://badge.fury.io/py/whatami
