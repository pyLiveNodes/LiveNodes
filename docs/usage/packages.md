# Local Nodes and Packages

The LiveNode framework keeps a registry of known Nodes (and Bridges) so that serialization and deserialization can take place. Technically you may be able to run a graph without the following, but I would not recommend it.

Most Notes are *automatically added to the registry* using the pip `livenodes.nodes` entrypoint, which is declared in the `pyproject.toml` file (see for example [core node package](https://gitlab.csl.uni-bremen.de/livenodes/packages/livenodes_core_nodes/-/blob/main/pyproject.toml)). Therefore, if you install any package, e.g. run `pip install livenodes_core_nodes` the nodes are directly available and will show up in LN-Studio.

## Local Nodes

If you need to prototype Nodes or just don't want to host a package you have two options:
1. add the nodes directly to the registry on startup
2. use `pip install -e ./localnodes` for a local package install

Adding the nodes on startup of, for instance, LN-Studio can be achieved thusly (see [start.py](https://gitlab.csl.uni-bremen.de/livenodes/example-project/-/blob/main/start.py) in the example project):

```
from sample_projects.online.nodes.math_square import Math_Square

from livenodes import get_registry
reg = get_registry()
reg.nodes.register('math_square', Math_Square)

if __name__ == "__main__":
    from lns.main_qt import main
    main()
```

The underlying node registry uses [Class-Registry](https://class-registry.readthedocs.io/en/latest/). The initial lookup argument should be lower case and the bridges registry works the same way, just using `reg.bridges.register`.

Local nodes can be installed using a barbones `pyproject.toml` and a subsequent install with `pip install -e ...`. An example can be found again in the [EASE TSD Analysis](https://gitlab.csl.uni-bremen.de/ease/tsd1-data-analysis/-/blob/main/code/local_nodes/pyproject.toml)



## Packages

Here is a non-exhaustive list of currently existing packages. All of these packages are build automatically and can be installed via pip using the [gitlab package registry](https://gitlab.csl.uni-bremen.de/groups/livenodes/-/packages).

New install:`pip install livenodes_core_nodes `

Inside of a requirements.txt file:
```

livenodes~=0.9
livenodes_core_nodes~=0.9.4
livenodes_ease_tsd~=0.9.4
-e ./local_nodes/

```

- [Core Nodes](https://livenodes.pages.csl.uni-bremen.de/packages/livenodes_core_nodes/) Everyday usefull nodes mostly based on the efficient (Batch, Time, Channel) stream format.
- [BioKIT](https://livenodes.pages.csl.uni-bremen.de/packages/livenodes_biokit/) BioKIT based HMM training and evaluation nodes.
- [Matplotlib](https://livenodes.pages.csl.uni-bremen.de/packages/livenodes_matplotlib/) Everyday plotting with Matplotlib.
- [PLUX](https://livenodes.pages.csl.uni-bremen.de/packages/livenodes_plux/) Connect to PLUX devices.
- [QT](https://livenodes.pages.csl.uni-bremen.de/packages/livenodes_qt/) Everyday UI Elements.
- [Intel RealSense](https://livenodes.pages.csl.uni-bremen.de/packages/livenodes_realsense/) Connect to the Intel RealSense.
- [TS Matplotlib](https://livenodes.pages.csl.uni-bremen.de/packages/livenodes_ts_matplotlib/) Plotting with Matplotlib, but using (Time, Channel) format.
- [Simple TimeSeries](https://gitlab.csl.uni-bremen.de/livenodes/packages/livenodes_simple_timeseries) Utility package for (Time, Channel) format, rather than (Batch, Time, Channel)
- [Vispy](https://gitlab.csl.uni-bremen.de/livenodes/packages/livenodes_vispy) Plotting using Vispy. Mostly demo, as the matplotlib packages are optimized and thus similarly fast.

