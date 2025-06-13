from __future__ import annotations
from time import sleep
import sys
import subprocess
import os
from types import TracebackType
from typing import ContextManager
import click
from pathlib import Path

from hey_siwi.common import ROOT_DIRECTORY_ENVVAR
from hey_siwi.tmux import TmuxConfig, TmuxManager


class cd(ContextManager):

    def __init__(self, dir: str | Path) -> None:
        self._original_dir: Path | None = None
        self._new_dir = Path(dir)

    def __enter__(self) -> Path:
        self._original_dir = Path(os.getcwd())
        os.chdir(self._new_dir)
        return self._new_dir

    def __exit__(self, exc_type: type[BaseException] | None, exc_value: BaseException | None, traceback: TracebackType | None, /) -> None:
        assert self._original_dir is not None
        os.chdir(self._original_dir)


class MyCommand:
    # emojis!
    _BASE_ENV = {"UNICORN": "\U0001F984", "THUMBS_UP": "\U0001F44D"}

    def __str__(self) -> str:
        return self._cmd

    def __init__(self, command: str, env: dict[str, str] | None = None) -> None:
        self._env = os.environ.copy() | self._BASE_ENV | (env or {})
        self._cmd = command

    def exec(self) -> int:
        rv = subprocess.run(
            self._cmd,
            env=self._env,
            shell=True,
            stdout=sys.stdout,
            stderr=sys.stderr,
            stdin=sys.stdin,
        )
        return rv.returncode


def get_startup_commands() -> list[MyCommand]:
    return [
        MyCommand(command='printf "===> Entering paradise %s\\n" "$UNICORN"'),
    ]

def get_shutdown_commands() -> list[MyCommand]:
    return [
        MyCommand(command='printf "===> We are back! %s\\n" "$THUMBS_UP"'),
    ]


@click.option("--home-directory", envvar=ROOT_DIRECTORY_ENVVAR, required=True)
@click.option("--tmux-config", "-t")
@click.command()
def activate(home_directory: str, tmux_config: str) -> None:
    with open(tmux_config, 'r', encoding='utf-8') as fp:
        tmux_conf = TmuxConfig.from_json(fp)
    try:
        with TmuxManager(tmux_conf) as tmux:
            with cd(home_directory):
                for command in get_startup_commands():
                    command.exec()
                tmux.start()
                click.secho(f"Activated siwi in session {tmux.session.name}", fg='green')
                sleep(4)
                for command in get_shutdown_commands():
                    command.exec()
    except Exception as ex:
        raise click.ClickException(str(ex)) from ex
