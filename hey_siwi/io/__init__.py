from pathlib import Path
import click

class MonitorError(Exception):
    pass

class Monitor:

    def __init__(self, length: int, width: int) -> None:
        self.length = length
        self.width = width

        self._buffer: list[str] = []

    def set_screen(self, path: Path) -> None:
        try:
            with open(path, 'r') as fp:
                self._buffer = fp.readlines()
        except IOError as ex:
            raise MonitorError("Failed to read file") from ex


@click.group()
def show():
    pass

