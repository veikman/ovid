# -*- coding: utf-8 -*-
"""Packaging metadata."""

from setuptools import setup

from ovid import __version__

setup(
    name='ovid',
    version=__version__,
    description='Text metamorphosis toolbox',
    requires=[],
    author='Viktor Eikman',
    author_email='viktor.eikman@gmail.com',
    url='https://github.com/veikman/ovid',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3',
        'Topic :: Database',
        'Topic :: Games/Entertainment :: Board Games',
        'Topic :: Games/Entertainment :: Multi-User Dungeons (MUD)',
        'Topic :: Games/Entertainment :: Role-Playing',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Topic :: Text Processing :: Filters',
        'Topic :: Text Processing :: Markup',
        ],
    packages=['ovid'],
    )
