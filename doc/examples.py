from __future__ import print_function, division
from whatami import what, what2id, id2what
import whatami
import threading

print(type(threading))
print(what2id(threading))

from sklearn.gaussian_process.kernels import Product, DotProduct

kernel = Product(DotProduct(), DotProduct())

print(kernel.__class__.__name__)

whatid = what2id(kernel)
print(id2what(whatid))

assert whatid == id2what(whatid).id()

# Some corner cases
# Modules
# Whatami supports generating strings for python modules, but it is not advisable to go this way

# Note that classes and modules are unsafe, as they trigger imports that might go wrong
# if a russian hacker has hijacked the location in disk blah.
