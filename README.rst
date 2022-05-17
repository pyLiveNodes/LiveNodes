========
Overview
========

LiveNodes: node based live streaming sensor/data and visualization suite.

* Free software: MIT license

Installation
============

::

    pip install livenodes

You can also install the in-development version with::

    pip install git+ssh://git@gitlab.csl.uni-bremen.de/yale1/livenodes.git@main

Documentation
=============

Hosted at:
http://yale1.pages.csl.uni-bremen.de/smart-studio/

Notes on sphinx: 
- https://samnicholls.net/2016/06/15/how-to-sphinx-readthedocs/
- https://www.sphinx-doc.org/en/master/usage/extensions/napoleon.html


Development
===========

To run all the tests run::

    tox

Note, to combine the coverage data from all the tox environments run:

.. list-table::
    :widths: 10 90
    :stub-columns: 1

    - - Windows
      - ::

            set PYTEST_ADDOPTS=--cov-append
            tox

    - - Other
      - ::

            PYTEST_ADDOPTS=--cov-append tox
