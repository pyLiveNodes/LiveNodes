#!/usr/bin/env python
# -*- encoding: utf-8 -*-

import io
import re
from glob import glob
from os.path import basename
from os.path import dirname
from os.path import join
from os.path import splitext

from setuptools import find_packages
from setuptools import setup

import itertools


def read(*names, **kwargs):
    with io.open(join(dirname(__file__), *names), encoding=kwargs.get('encoding', 'utf8')) as fh:
        return fh.read()

extras_require = {
        'dev': [
            'pytest>=7.0.1'
        ]
    }
extras_require['all'] = list(itertools.chain.from_iterable(extras_require.values()))

setup(
    name='livenodes',
    version='0.7.0',
    license='MIT',
    description='LiveNodes: node based live streaming sensor/data and visualization suite.',
    long_description='{}\n{}'.format(
        re.compile('^.. start-badges.*^.. end-badges', re.M | re.S).sub('', read('README.md')),
        re.sub(':[a-z]+:`~?(.*?)`', r'``\1``', read('CHANGELOG.rst')),
    ),
    author='Yale Hartmann',
    author_email='yale.hartmann@uni-bremen.de',
    url='https://gitlab.csl.uni-bremen.de/yale1/livenodes',
    packages=find_packages('src'),
    package_dir={'': 'src'},
    py_modules=[splitext(basename(path))[0] for path in glob('src/*.py')],
    include_package_data=True,
    zip_safe=False,
    classifiers=[
        # complete classifier list: http://pypi.python.org/pypi?%3Aaction=list_classifiers
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: Unix',
        'Operating System :: POSIX',
        'Operating System :: Microsoft :: Windows',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3 :: Only',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: Implementation :: CPython',
        'Programming Language :: Python :: Implementation :: PyPy',
        # uncomment if you test on these interpreters:
        # 'Programming Language :: Python :: Implementation :: IronPython',
        # 'Programming Language :: Python :: Implementation :: Jython',
        # 'Programming Language :: Python :: Implementation :: Stackless',
        'Topic :: Utilities',
    ],
    project_urls={
        'Documentation': 'https://yale1.pages.csl.uni-bremen.de/livenodes/',
        'Changelog': 'https://yale1.pages.csl.uni-bremen.de/livenodes/latest/changelog.html',
        'Issue Tracker': 'https://gitlab.csl.uni-bremen.de/yale1/livenodes/issues',
    },
    keywords=[
        # eg: 'keyword1', 'keyword2', 'keyword3',
    ],
    python_requires='>=3.6',
    install_requires=[
        "numpy>=1.22.1",
        "matplotlib>=3.5.1",
        "graphviz>=0.19.1",
        "seaborn>=0.11.2",
        "joblib>=1.1.0",
        "scikit-learn>=1.0.2",
        "scipy>=1.7.3",
        "phx-class-registry",
        "python-dotenv",
        # eg: 'aspectlib>=1.1.1', 'six>=1.7',
    ],
    extras_require=extras_require,
    entry_points={
        'console_scripts': [
            'livenodes = main_qt:main',
        ]
    },
)
