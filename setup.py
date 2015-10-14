#!/usr/bin/env python2
# coding=utf-8

# Authors: Santi Villalba <sdvillal@gmail.com>
# Licence: BSD 3 clause

try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

setup(
    name='whatami',
    license='BSD 3 clause',
    description='Easily provide python objects with self-identification',
    long_description=open('README.rst').read().replace('|Build Status| |Coverage Status| |Scrutinizer Status|', ''),
    version='4.0.3',
    url='https://github.com/sdvillal/whatami',
    author='Santi Villalba',
    author_email='sdvillal@gmail.com',
    packages=['whatami',
              'whatami.tests',
              'whatami.wrappers',
              'whatami.wrappers.tests'],
    classifiers=[
        'Intended Audience :: Science/Research',
        'Intended Audience :: Developers',
        'Topic :: Software Development',
        'Topic :: Scientific/Engineering',
        'License :: OSI Approved',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
        'Operating System :: Unix',
    ],
    install_requires=['arpeggio>=1.0', 'future'],
    tests_require=['pytest', 'pytest-cov', 'pytest-pep8'],
    extras_require={
        'sklearn': ['scikit-learn'],
        'docs': ['Sphinx'],
    },
    platforms=['Any'],
)
