# yaqc-cmds

[![PyPI](https://img.shields.io/pypi/v/yaqc-cmds)](https://pypi.org/project/yaqc-cmds)
[![Conda](https://img.shields.io/conda/vn/conda-forge/yaqc-cmds)](https://anaconda.org/conda-forge/yaqc-cmds)
[![black](https://img.shields.io/badge/code--style-black-black)](https://black.readthedocs.io/)

A qt-based graphical client for [bluesky-queueserver](https://blueskyproject.io/bluesky-queueserver/) with a focus on coherent multidimensional spectroscopy in the Wright Group. 

[!screenshot](./plot_screenshot.png)

## installation

Please note that at this time yaqc-cmds requires `pyside2` and is incompatable with `pyqt5`.
We are working to resolve this, PRs welcome!

Install the latest released version from PyPI:

```bash
$ python3 -m pip install yaqc-cmds
```

conda-forge and separately installable versions coming soon!

Use [flit](https://flit.readthedocs.io/) to install from source.

```
$ git clone https://github.com/wright-group/yaqc-cmds.git
$ cd yaqc-cmds
$ flit install -s
```

## configuration

yaqc-cmds requires access to two ports:
- bluesky re-manager
- bluesky zmq proxy

By default, yaqc-cmds uses the default ports on localhost.
This works for most applications.
If you require alternatives, configure yaqc-cmds with the following command:

```bash
$ yaqc-cmds edit-config
```

This will open a [toml](https://toml.io/) file which you must format as follows:

```
[bluesky]
re-manager = "localhost:60615"
zmq-proxy = "localhost:5568"
```

The default values are shown above.

## usage

First start bluesky re-manager and zmq-server.
You may wish to use [bluesky-in-a-box](https://github.com/wright-group/bluesky-in-a-box).
Then start yaqc-cmds.

Use the queue tab to add or change plans on the queueserver.
Note that yaqc-cmds is designed for usage with [wright-plans](https://github.com/wright-group/wright-plans).
wright-plans are specialized for coherent multidimensional spectroscopy.

Use the plot tab to watch raw data streaming from bluesky.

Note that direct hardware interaction or configuration is not supported by yaqc-cmds.
This application is only for interacting with the queueserver.
You may be interested in yaqc-qtpy.

## citation

This project is archived using [Zenodo](https://zenodo.org/record/1198910).
Please use DOI: 10.5281/zenodo.1198910 to cite yaqc-cmds.

