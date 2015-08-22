# coding=utf-8
from .fixtures import *
from whatami.whatutils import whatid2columns


def test_whatid2columns(df_with_whatid):
    whatid_column = 'whatid'
    expected_value_columns = sorted(set(df_with_whatid.columns) - {whatid_column})
    # add without name change
    edf = whatid2columns(df_with_whatid, whatid_column, prefix='pre-', inplace=False)
    assert edf is not df_with_whatid
    for col in expected_value_columns:
        assert (df_with_whatid[col] == edf[col]).all()
    # add with prefix
    edf = whatid2columns(df_with_whatid, whatid_column, prefix='pre-', inplace=False)
    for col in expected_value_columns:
        assert (df_with_whatid[col] == edf['pre-' + col]).all()
    # add with postfix
    edf = whatid2columns(df_with_whatid, whatid_column, postfix='-post', inplace=False)
    for col in expected_value_columns:
        assert (df_with_whatid[col] == edf[col + '-post']).all()
    # only some columns
    edf = whatid2columns(df_with_whatid, whatid_column,
                         columns=expected_value_columns[:1],
                         prefix='pre-', postfix='-post', inplace=False)
    assert (df_with_whatid[expected_value_columns[0]] == edf['pre-' + expected_value_columns[0] + '-post']).all()
    for col in expected_value_columns[1:]:
        assert ('pre-' + col + '-post') not in edf.columns
    # add inplace
    edf = whatid2columns(df_with_whatid, whatid_column, prefix='pre-', postfix='-post', inplace=True)
    assert edf is df_with_whatid
    for col in expected_value_columns:
        assert (df_with_whatid[col] == df_with_whatid['pre-' + col + '-post']).all()
    # missing: test getting nested values via tuples as values in columns
