# coding=utf-8
"""Tests various functions in whatutils."""
from functools import partial
from ..whatutils import whatid2columns
from .fixtures import df_with_whatid


def test_whatid2columns(df_with_whatid):
    """Tests extracting values from whatid strings in a pandas dataframe column into their own columns.

    Uses df_with_whatid fixtures, that must provide a dataframe with:
      - A column "whatid" with the whatami ids
      - The rest of the columns must be the expectations for the extracted values, named as:
        - key: for top level keys
        - key1_key2_key3: for recursive keys
    """
    # Use pandas for testing
    from ..plugins import pd
    assert_series_equal = partial(pd.util.testing.assert_series_equal, check_names=False)
    whatid_column = 'whatid'
    expected_value_columns = sorted(set(df_with_whatid.columns) - {whatid_column})
    toplevel_values = [c for c in expected_value_columns if '_' not in c]
    recursive_values = [c.split('_') for c in expected_value_columns if '_' in c]
    # add without name change
    edf = whatid2columns(df_with_whatid, whatid_column, inplace=False)
    assert edf is not df_with_whatid
    for col in toplevel_values:
        assert_series_equal(df_with_whatid[col], edf[col])
    # recursive values
    edf = whatid2columns(df_with_whatid, whatid_column, recursive_values, prefix='pre-', inplace=False)
    assert edf is not df_with_whatid
    for col in recursive_values:
        colname = '_'.join(col)
        assert_series_equal(df_with_whatid[colname], edf['pre-' + colname])
    # add with prefix
    edf = whatid2columns(df_with_whatid, whatid_column, prefix='pre-', inplace=False)
    for col in toplevel_values:
        assert_series_equal(df_with_whatid[col], edf['pre-' + col])
    # add with postfix
    edf = whatid2columns(df_with_whatid, whatid_column, postfix='-post', inplace=False)
    for col in toplevel_values:
        assert_series_equal(df_with_whatid[col], edf[col + '-post'])
    # only some columns
    edf = whatid2columns(df_with_whatid, whatid_column,
                         columns=toplevel_values[:1],
                         prefix='pre-', postfix='-post', inplace=False)
    assert_series_equal(df_with_whatid[toplevel_values[0]], edf['pre-' + toplevel_values[0] + '-post'])
    for col in toplevel_values[1:]:
        assert ('pre-' + col + '-post') not in edf.columns
    # add inplace
    edf = whatid2columns(df_with_whatid, whatid_column, prefix='pre-', postfix='-post', inplace=True)
    assert edf is df_with_whatid
    for col in toplevel_values:
        assert_series_equal(df_with_whatid[col], df_with_whatid['pre-' + col + '-post'])
