# coding=utf-8

# Authors: Santi Villalba <sdvillal@gmail.com>
# Licence: BSD 3 clause

from datetime import datetime
import inspect
from time import strptime, mktime

import pytest

from whatami import mlexp_info_helper, whatable


def test_mlexp_info_helper():

    @whatable
    class TestDataset(object):
        def __init__(self):
            super(TestDataset, self).__init__()

    @whatable
    class Prepro(object):
        def __init__(self, lower=0, upper=1):
            super(Prepro, self).__init__()
            self.min = lower
            self.max = upper

    @whatable
    class PreproModel(object):
        def __init__(self, prepro=None, reg='l1', C=1.):
            super(PreproModel, self).__init__()
            self.prepro = prepro
            self.reg = reg
            self.C = C

    @whatable
    class CVEval(object):
        def __init__(self, num_folds=10, seed=0):
            super(CVEval, self).__init__()
            self.num_folds = num_folds
            self.seed = seed

    before = int(datetime.now().strftime("%s"))
    info = mlexp_info_helper(
        title='test',
        data_setup=TestDataset().what(),
        model_setup=PreproModel(prepro=Prepro(), reg='l2').what(),
        eval_setup=CVEval(num_folds=5, seed=2147483647).what(),
        exp_function=test_mlexp_info_helper,
        comments='comments4nothing',
        itime=False)
    assert info['title'] == 'test'
    assert info['data_setup'] == 'TestDataset#'
    assert info['model_setup'] == 'PreproModel#C=1.0#prepro="Prepro#max=1#min=0"#reg=\'l2\''
    assert info['eval_setup'] == 'CVEval#num_folds=5#seed=2147483647'
    assert info['fsource'] == inspect.getsourcelines(test_mlexp_info_helper)
    assert info['comments'] == 'comments4nothing'
    recorded_time = mktime(strptime(info['date'], '%Y-%m-%d %H:%M:%S'))
    assert (recorded_time - before) < 2
