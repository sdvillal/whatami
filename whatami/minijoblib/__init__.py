"""
(Modified) joblib subset to isolate and control hashing of numpy arrays and pandas objects.

At the moment, representation for these objects is based on serialization and is not
consistent across python versions (2 differs from 3, this is on purpose on joblib and
we could change it) and pandas versions (in this case, only a non-full-serialization
based technique would make the trick to generate consistent ids for dataframes).

Joblib's hasher does take into account some special cases like dtype internalization or
memmapped arrays, which helps to maintain consistency.

When long-term consistency is needed, using numpy arrays and, specially,
pandas ojects in configurations should be discouraged and other techniques,
preferred.
"""

# Latest sync on 2016/07/03, master after joblib 0.9.4:
#   https://github.com/joblib/joblib/tree/af2e9b7f1770f964d74b735be93d2c55c5f2cdb2
