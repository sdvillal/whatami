# coding=utf-8
"""Tools to make easier to aggregate information from functions and whatables."""

# Authors: Santi Villalba <sdvillal@gmail.com>
# Licence: BSD 3 clause

from __future__ import unicode_literals, absolute_import
import datetime
import inspect
from collections import OrderedDict
from socket import gethostname
from whatami import what_string

from whatami.misc import internet_time


def mlexp_info_helper(title,
                      data_setup=None,
                      model_setup=None,
                      eval_setup=None,
                      exp_function=None,
                      comments=None,
                      itime=False):
    """Creates a dictionary describing machine learning experiments.

    Parameters:
      - title: the title for the experiment
      - data_setup: a "what" for the data used in the experiment
      - model_setup: a "what" for the model used in the experiment
      - eval_setup: a "what" for the evaluation method used in the experiment
      - exp_function: the function in which the experiment is defined;
                      its source text lines will be stored
      - comments: a string with whatever else we need to say
      - itime: if True we try to store UTC time from  an internet source

    (Here "what" means None, a string, an object providing a "what method" or an object providing an "id" method.)

    Return:
      An ordered dict mapping strings to strings with all or part of:
      title, data_setup, model_setup, eval_setup, fsource, date, idate (internet datetime), host, comments
    """
    info = OrderedDict((
        ('title', title),
        ('data_setup', what_string(data_setup)),
        ('model_setup', what_string(model_setup)),
        ('eval_setup', what_string(eval_setup)),
        ('fsource', inspect.getsourcelines(exp_function) if exp_function else None),
        ('date', datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')),
        ('idate', None if not itime else internet_time()),
        ('host', gethostname()),
        ('comments', comments),
    ))
    return info
