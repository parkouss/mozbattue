*mozbattue*
===========

**mozbattue** is a command line tool which help finding the root cause
of intermittents bugs for *mozilla*.

The word *battue* is a french word use to define a kind of hunt where
people encircle the animal until they kill him.

This is an analogy - *mozbattue* helps in eradicating a bug by triggering
builds on different revisions, starting from the oldest known intermittent.

Installation
============

For now::

  pip install git+https://github.com/parkouss/mozbattue.git

Quick start
===========

1. Retrieve intermittent bug data locally.
  To get the latest known intermittents bugs from Bugzilla::

    mozbattue update

2. Investigate the current bugs and choose one that you want to investigate.
  You can list the intermittents bugs with the command::

    mozbattue list

  To get detailed information about a bug::

    mozbattue info <bugid>

  Full list of intermmitent occurences::

    mozbattue info -f <bugid>

3. Trigger builds a certain number of times at different revisions to
try to find the root cause.

  To run the same build as the oldest intermittent 20 times::

    mozbattue trigger <bugid> 0 --times 20

  To run the same build on the 30th revision before the oldest intermittent::

    mozbattue trigger <bugid> -30 --times 20


Customisation
=============

You can generate the default configuration with the command::

  mozbattue generate-conf

This will write a *mozbattue.ini* file in the current folder that you can
use to change some default values.
