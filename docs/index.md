# Livenodes

Livenodes is a pure python, node-based framework for online and offline digital signal processing (of biosignals) with and without graphical user interfaces and user interaction.

You'll find a list with use cases, features and all the other good stuff below. It's awesome to have you here! Good Coding, Good Research and Good Luck in your Endeavours!

Yale Hartmann
[Website](https://www.uni-bremen.de/en/csl/institute/team/staff/yale-hartmann)

## Use cases / Examples
- Biosignal-Based Interaction Applications
    - Visualization of ML Predictions in Realtime and dependent on user input: [Youtube](https://www.youtube.com/watch?v=E8EEMYG2PpQ)
    - Live Human Activity Recognition: [Gitlab Repo](https://gitlab.csl.uni-bremen.de/livenodes/example-project)
    - Online ASR (with distributed computing, where the ASR Model can run on a different machine): [TODO create and add link]()
    - EMG and Accelermoter-based Gesture Recognition using Plux MuscleBans and BioKIT-based HMMs: [TODO Link to Felix' BA]()
    - EMG-based biosignals calculator: [TODO Link to Dennis' BA]()
    - Closed Loop Experiments
- High-performance and/or distributed digital signal processing
    - automatic dataset cleaning and live display of summary (note: if you only need the calculation, you might want to look at other frameworks)
- Optimization of ML (Preprocessing) Graphs
    - Biosignals 23/24 Example: TODO add link

## Features
- Core LiveNodes:
    - [Pure Python (Stateful) Nodes](./usage/node.md)
    - [Acyclic Graphs with synced data packages and typed data streams](./concepts/streams.md)
    - [Easy Multithreading and Multiprocessing (just set a Flag and the framework will do the rest)](./advanced/multiprocessing.md)
    - [Distributed Computing (currently in works)]()
    - Don't choose between offline and online processing, do both. Parameter optimization of a graph offline and run with online sensors.
    - [Create graphs in python, yaml, json or a visual editor](./advanced/serialization.md)
    - [Full Logging](./advanced/logger.md)
    - [TODO: Graph Macros/Recursion]()
- Visual Ecosystem: [Smart-Studio](http://livenodes.pages.csl.uni-bremen.de/smart-studio/readme.html)
    - Visualize everything (data, states, interaction)
    - Graphical Interaction
    - Create and edit graphs in a visual editor
    - Time and profile of your graphs
- Package Ecosystem:
    - [Easy Node installation via pip packages or local nodes](./usage/extensibility.md)
    - [Large set of tried and tested nodes](https://gitlab.csl.uni-bremen.de/groups/livenodes/-/packages)

## Node Packages

- [Core Nodes](https://livenodes.pages.csl.uni-bremen.de/packages/livenodes_core_nodes/) Everyday usefull nodes mostly based on the efficient (Batch, Time, Channel) stream format.
- [BioKIT](https://livenodes.pages.csl.uni-bremen.de/packages/livenodes_biokit/) BioKIT based HMM training and evaluation nodes.
- [Matplotlib](https://livenodes.pages.csl.uni-bremen.de/packages/livenodes_matplotlib/) Everyday plotting with Matplotlib.
- [PLUX](https://livenodes.pages.csl.uni-bremen.de/packages/livenodes_plux/) Connect to PLUX devices.
- [QT](https://livenodes.pages.csl.uni-bremen.de/packages/livenodes_qt/) Everyday UI Elements.
- [Intel RealSense](https://livenodes.pages.csl.uni-bremen.de/packages/livenodes_realsense/) Connect to the Intel RealSense.
- [TS Matplotlib](https://livenodes.pages.csl.uni-bremen.de/packages/livenodes_ts_matplotlib/) Plotting with Matplotlib, but using (Time, Channel) format.
- [Simple TimeSeries](https://gitlab.csl.uni-bremen.de/livenodes/packages/livenodes_simple_timeseries) Utility package for (Time, Channel) format, rather than (Batch, Time, Channel)
- [Vispy](https://gitlab.csl.uni-bremen.de/livenodes/packages/livenodes_vispy) Plotting using Vispy. Mostly demo, as the matplotlib packages are optimized and thus similarly fast.

## Where to start

I recomend to checkout the example repository, which contains great examples ranging from very simple graphs for recording and online data annotation, how to use livendes for DSP in jupyter notebooks up to very complex online unsupervised segmentation used for online training and recognition of an HAR system.

Examples Repository: https://gitlab.csl.uni-bremen.de/livenodes/example-project

## Documentation

If you want to
- create and run a graph, have a look at the [quickstart](./quickstart/index.md)
- write your own nodes, you can find more information [here](./usage/node.md)
- delve into the concepts of the core livenode system, I recommend you take a look at the [advanced concepts](./advanced/index.md).
- run or see an example, use the link from [above](##use-cases).
- look at specific features, use the link from [above](##features).

If you are seasoned with all the concepts, and need specific information, the [module reference](./modules/modules.rst) is for you.

## Similar Frameworks

There are multiple node-based and python frameworks, but as far as I know none, that combines recording, processing, visualzing and interaction for biosignals in one combined package. Further frameworks are listed [here](./advanced/similar_framworks.md).


## Platform independence

The LiveNode Package itself is pureley python based and most node packages are to, so they should run on all major platforms. I personally work on primarily Unix-based systems, so let me know if you encounter troubles anywhere.

That being said, a node require a platform-specific library or dependency. Check the dependencies of the node packages you want to  install!

Notable cases:
- Smart-Studio requires PyQTAds, which does currently have no easy installable ARM version
- BioKIT is mainly build for Ubuntu

## Citing and Mentioning

If you are using livenodes in your academic work, please cite or acknowledge this paper in your publications, as it helps me and my phd a lot:

As there is no dedicated Livenode Paper, please use this for now: https://www.csl.uni-bremen.de/cms/publications/bibtexbrowser.php?key=hartmann2022demo&bib=csl_all_publications.bib

If you use livenodes in any other work or project, please link the Livenodes git page and/or let me know / create a PR, so I can shout out your project in the use cases.


## Contributing

I'm grateful for any contribution, from typos/language to examples, tests, questions, use cases, code extenstions / suggestions, bug fixes, feature implementations, etc. For all of these please create a Pull Request (PR) and/or get in touch with me, also: you rock!

If you developed your own nodes and want to host them as a package: first of all: you are awesome, secondly, please have a look at the existing packages and either get in touch with me to host them on the csl gitlab or just host them directly via pip.

If you don't know where to start, there also should always be a list of open issues/features which I would be super grateful if you have a look and see what suits you.

Further information: [Contributing](./contributing/index.md)



# Index

```{eval-rst}
.. toctree::
    :maxdepth: 2
    :caption: Start

    usage/quickstart.md

    usage/node.md
    usage/graph.md
    usage/multiprocessing.md
    usage/packages.md


.. toctree::
    :maxdepth: 2
    :caption: Advanced

    advanced/streams.md
    advanced/synchronization.md
    advanced/execution.md

    advanced/draw.md

    advanced/serialization.md
    advanced/logging.md
    advanced/profiling.md

.. toctree::
    :caption: Modules
    :maxdepth: 2

    modules/modules.rst

.. toctree::
    :caption: Repository
    :maxdepth: 2

    contributing/index.md
    authors.rst
    changelog.rst

```


