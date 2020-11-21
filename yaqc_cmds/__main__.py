#!/usr/bin/env python3

import os
import pathlib
import subprocess
import sys

import appdirs  # type: ignore
import click
import toml

from .__version__ import __version__

config = {}


@click.group(invoke_without_command=True)
@click.version_option(__version__)
@click.pass_context
def main(ctx):
    if ctx.invoked_subcommand is None:
        launch()


@main.command()
@click.option("-c", "--config", "config_filepath")
def launch(config_filepath):
    from ._main_window import app, MainWindow
    from .project import style

    if config_filepath:
        config_filepath = pathlib.Path(config_filepath)
    else:
        config_filepath = (
            pathlib.Path(appdirs.user_config_dir("yaqc-cmds", "yaqc-cmds")) / "config.toml"
        )

    global window, config
    config = toml.load(config_filepath)
    window = MainWindow(config)
    style.set_style()
    window.show()
    window.showMaximized()
    app.exec_()


@main.command(name="edit-config")
def edit_config():
    config_filepath = (
        pathlib.Path(appdirs.user_config_dir("yaqc-cmds", "yaqc-cmds")) / "config.toml"
    )
    config_filepath.parent.mkdir(parents=True, exist_ok=True)
    if not config_filepath.exists():
        if click.confirm(
            "No config file found, would you like to use the default (virtual) configuration?",
            default=True,
        ):
            config_template = pathlib.Path(__file__).parent / "config-template.toml"
            config_filepath.write_text(config_template.read_text())

    while True:
        if sys.platform.startswith("win32"):
            config_filepath = str(config_filepath)
            subprocess.run([os.environ.get("EDITOR", "notepad.exe"), config_filepath])
        else:
            subprocess.run([os.environ.get("EDITOR", "vi"), config_filepath])
        try:
            toml.load(config_filepath)
            break
        except Exception as e:
            print(e, file=sys.stderr)

            if not click.confirm(
                "Error parsing config toml. Would you like to re-edit?",
                default=True,
            ):
                break


if __name__ == "__main__":
    main()
