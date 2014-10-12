#! /usr/bin/env python2
# coding=utf-8

# Authors: Santi Villalba <sdvillal@gmail.com>
# Licence: BSD 3 clause

from setuptools import setup


setup(
    name='whatami',
    license='BSD 3 clause',
    description='Easily provide python objects with self-identification',
    version='0.1-dev',
    url='https://github.com/sdvillal/whatami',
    author='Santi Villalba',
    author_email='sdvillal@gmail.com',
    classifiers=[
        'Intended Audience :: Science/Research',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD 3 clause'
        'Programming Language :: Python',
        'Topic :: Software Development',
        'Topic :: Scientific/Engineering',
        'Operating System :: Unix',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
    ],
    test_require=['pytest']
)
