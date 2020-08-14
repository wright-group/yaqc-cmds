#!/usr/bin/env python3

import os
import pathlib
import subprocess
import sys

import appdirs  # type: ignore
import click

from .__version__ import __version__
from ._pycmds import app, MainWindow, style


@click.group(invoke_without_command=True)
@click.version_option(__version__)
def main():
    launch()


@main.command()
def launch():
    global window
    window = MainWindow()
    style.set_style()
    window.show()
    window.showMaximized()
    app.exec_()


if __name__ == "__main__":
    main()
