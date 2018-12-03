#!/usr/bin/env python3

import os
import sys

try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

with open('requirements.txt') as fh:
    required = fh.read().splitlines()

setup(
    name='multiNER',
    version='0.1',
    description='Multiple NE-engines combined',
    author='Willem Jan Faber',
    url='https://github.com/KBNLresearch/multiNER/',
    package_dir={'multiNER': '.'},
    packages=['multiNER', 'multiNER'],
    install_requires=required,
    license='GPL-3.0',
)
