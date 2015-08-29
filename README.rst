whatami: unobtrusive object self-identification for python
==========================================================

|Pypi Version| |Build Status| |Coverage Status| |Scrutinizer Status|

About
-----

Whatami is an attempt to abstract configurability and experiment
identifiability in a convenient way. It does so by leveraging object
introspection and defining a simple, flexible and consistent API
that python objects can adhere to, even if they were not originally
designed to do it.


It works this way:

-  Objects provide their own ids based on parameters=value dictionaries.
   They do so by returning an instance of the *What* class from
   a method called *"what()"*.

-  Optionally, this package provides a *whatable* decorator to provide automatic
   creation of *What* objects from objects dictionaries, slots and properties.
   All attributes will be considered part of the configuration, except for those
   whose names start or end by '\_'.


The id strings
--------------

They aim to look like they would be generated if *__repr__* in python was always implemented
taking into account recursion and exposing only result-changing parameters. They pretty much
look like python function calls with nested parameters expanded to look like python calls
themselves.


Features
--------

* **Represent your computations as standardized ID strings.**

* **Pluggable architecture.**

* **ID strings can be parsed and manipulated.**

* **"whatamise" your library**. Included support for:

  * `scikit-learn`_
  * `pyopy`_

* **Convenience functions for data tidying.**


Example
-------

Whatami is simple but powerful. This example just shows its surface and
better docs are coming, but in the meantime, just check the docstrings
and unit tests.

.. code:: python

    # Objects of this class provide a configuration (`What` object)
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
    # ducked(company=None,name='salty-lollypops',quantity=33)

    # Using the whatable decorator makes objects gain a what() method;
    # in this case, what() is infered automatically
    @whatable
    class Company(object):
        def __init__(self, name, city, verbose=True):
            super(Company, self).__init__()
            self.name = name
            self.city = city
            self._verbose = verbose  # not part of config
            self.social_reason_ = '%s S.A., %s' % (name, city)  # not part of config
    cc = Company(name='Chupa Chups', city='Barcelona')
    print(cc.what().id())
    # Company(city='Barcelona',name='Chupa Chups')

    # Ultimately, we can nest whatables...
    duckedc = DuckedConfigurable(33, 'salty-lollypops', company=cc, verbose=False)
    print duckedc.what().id()
    # ducked(company=Company(city='Barcelona',name='Chupa Chups'),name='salty-lollypops',quantity=33)

    # We can also decorate functions and partials - use with caution
    @whatable
    def buy(company, price=2**32, currency='euro'):
        return '%s is now mine for %g %s' % (company.name, price, currency)
    print buy.what().id()
    # buy(currency='euro',price=4294967296)


Versioning
----------

Since release 4.0.0 whatami uses `semantic versioning`_, where a major version bump
happens also if the default id strings can be generated differently, even if no API
actually changes.


.. |Build Status| image:: https://travis-ci.org/sdvillal/whatami.svg?branch=master
   :target: https://travis-ci.org/sdvillal/whatami
.. |Coverage Status| image:: http://codecov.io/github/sdvillal/whatami/coverage.svg?branch=master
   :target: http://codecov.io/github/sdvillal/whatami?branch=master
.. |Pypi Version| image:: https://badge.fury.io/py/whatami.svg
   :target: http://badge.fury.io/py/whatami
.. _semantic versioning: http://semver.org/
.. _scikit-learn: http://scikit-learn.org
.. _pyopy: https://github.com/sdvillal/pyopy
.. |Scrutinizer Status| image:: https://scrutinizer-ci.com/g/sdvillal/whatami/badges/quality-score.png?b=master
   :target: https://scrutinizer-ci.com/g/sdvillal/whatami/?branch=master
