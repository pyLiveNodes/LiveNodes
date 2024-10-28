# Livenodes

Livenodes are small units of computation for digital signal processing in python. They are connected multiple synced channels to create complex graphs for real-time applications. Each node may provide a GUI or Graph for live interaction and visualization.

//LN-Studio is a GUI Application to create, run and debug these graphs based on QT5.

Any contribution is welcome! These projects take more time, than I can muster, so feel free to create issues for everything that you think might work better and feel free to create a MR for them as well!

Have fun and good coding!

Yale


To disable assertion checks for types etc use
```
PYTHONOPTIMIZE=1 lns
```

# Installation

`pip install livenodes --extra-index-url https://package_puller:8qYs4hBAsmAHJ5AdS_y9@gitlab.csl.uni-bremen.de/api/v4/groups/368/-/packages/pypi/simple`

# Testing

1. `pip install -r requirements_setup.txt`
2. `tox -e py311` or `tox -e py312`