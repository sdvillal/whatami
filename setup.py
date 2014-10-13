#! /usr/bin/env python2
# coding=utf-8

# Authors: Santi Villalba <sdvillal@gmail.com>
# Licence: BSD 3 clause

try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

import whatami

setup(
    name='whatami',
    license='BSD 3 clause',
    description='Easily provide python objects with self-identification',
    # long_description=open('README.md').read(),  # Use pyandoc or move to RST
    version=whatami.__version__,
    url='https://github.com/sdvillal/whatami',
    author='Santi Villalba',
    author_email='sdvillal@gmail.com',
    packages=['whatami', 'whatami.tests'],
    package_data={'': ['*.txt', '*.cfg', '*.md']},  # use MANIFEST.in
    classifiers=[
        'Intended Audience :: Science/Research',
        'Intended Audience :: Developers',
        'License :: OSI Approved',
        'Programming Language :: Python',
        'Topic :: Software Development',
        'Topic :: Scientific/Engineering',
        'Operating System :: Unix',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
    ],
    test_require=['pytest'],
    platforms=['Any'],
)
