# coding=utf-8
from __future__ import unicode_literals, absolute_import
try:
    from .misc import *
    from .what import *
    from .parsers import *
    from .whatutils import *
except ImportError:  # pragma: no cover
    pass

__version__ = '4.0.0-dev0'
