# -*- coding: utf-8 -*-
import os
from setuptools import setup

THIS_DIR = os.path.dirname(os.path.realpath(__file__))


def read(*path):
    return open(os.path.join(THIS_DIR, *path)).read()


setup(
    name="mozbattue",
    version='0.1',
    description=('tool which help finding the root cause of intermittents '
                 'bugs for mozilla'),
    long_description=read("README.rst"),
    author='Julien Pagès',
    author_email='j.parkouss@gmail.com',
    license='MPL 1.1/GPL 2.0/LGPL 2.1',
    packages=['mozbattue'],
    entry_points="""
        [console_scripts]
        mozbattue = mozbattue.main:main
    """,
    platforms=['Any'],
    install_requires=['bugsy', 'mozci'],
    tests_require=['mock'],
    test_suite='tests',
)
