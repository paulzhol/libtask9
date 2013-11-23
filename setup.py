#!/usr/bin/env python

import sys
from setuptools import setup, find_packages, Extension

timers_module_sources = []
timers_module_libraries = ['pthread']

if sys.platform.startswith('linux') or \
    (sys.platform.startswith('freebsd') and (sys.platform[7] > '7')):
    timers_module_sources.append('libtask9/timers_ext/posix_rt.c')
    timers_module_libraries.append('rt')
else:
    timers_module_sources.append('libtask9/timers_ext/pthreads.c')

timers_module = Extension('_libtask9_timers',
                          sources = timers_module_sources,
                          libraries = timers_module_libraries)

setup(
    name = 'libtask9',
    version = '0.3.0',
    description = 'Python port of the Plan 9 from User Space (aka plan9port) version of libthread',
    author = 'Yuval Pavel Zholkover',
    author_email = 'paulzhol@gmail.com',
    url = 'https://github.com/paulzhol/libtask9',
    classifiers = [
        'Development Status :: 3 - Alpha',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Programming Language :: Python :: 2.7',
        'License :: OSI Approved :: MIT License',
    ],
    packages = find_packages(),
    ext_modules = [timers_module],
    install_requires = [
        'greenlet >= 0.4.0',
    ]
)
