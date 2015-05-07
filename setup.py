# -*- coding: utf-8 -*-

from setuptools import setup

setup(name="mozbattue",
      version='0.1',
      description='mozbattue',
      author='Julien Pagès',
      author_email='j.parkouss@gmail.com',
      packages=['mozbattue'],
      entry_points="""
          [console_scripts]
          mozbattue = mozbattue.main:main
        """,
      platforms=['Any'],
      install_requires=['bugsy', 'mozci'],
)
