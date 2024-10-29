# Livenodes

Livenodes are small units of computation for digital signal processing in python. They are connected multiple synced channels to create complex graphs for real-time applications. Each node may provide a GUI or Graph for live interaction and visualization.

LN-Studio is a GUI Application to create, run and debug these graphs based on QT5.

Any contribution is welcome! These projects take more time, than I can muster, so feel free to create issues for everything that you think might work better and feel free to create a MR for them as well!

Have fun and good coding!

Yale

## Citation

If you use Livenodes and/or LN-Studio in your research, please cite it as follows:

As of 2024 there is no dedicated paper to LiveNodes yet. I'm working on it. But for now, please cite the following paper:
```
@inproceedings{hartmann2022demo,
  title = {Interactive and Interpretable Online Human Activity Recognition},
  author = {Hartmann, Yale and Liu, Hui and Schultz, Tanja},
  booktitle = {PERCOM 2022 - 20th IEEE International Conference on Pervasive Computing and Communications Workshops and other Affiliated Events (PerCom Workshops)},
  year = {2022},
  pages = {109--111},
  doi = {10.1109/PerComWorkshops53856.2022.9767207},
  url = {https://www.csl.uni-bremen.de/cms/images/documents/publications/HartmannLiuSchultz_PERCOM2022.pdf},
}
```

# Installation


# Performance 
To disable assertion checks for types etc use
```
PYTHONOPTIMIZE=1 lns
```

# Testing

1. `pip install -r requirements_setup.txt`
2. `tox -e py311` or `tox -e py312`
