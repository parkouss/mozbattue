*mozbattue*
===========

*mozbattue* is a command line tool that tries to find the root cause
of intermittents bugs for *mozilla*.

Installation
============

For now::

  pip install git+https://github.com/parkouss/mozbattue.git

Quick start
===========

1. Get the lasts known intermittents bugs from mozilla::

  mozbattue update

2. You can now list the intermittents bugs:

  mozbattue list
  # get more information about one bug:
  mozbattue info <bugid>

3. trigger 10 builds for the oldest intermittent found in the bug, 30
   revisions before:

  mozbattue trigger <bugid> -30 --times 10

