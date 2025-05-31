from pathlib import Path
import click

class MonitorError(Exception):
    pass

class Monitor:

    def __init__(self, length: int, width: int) -> None:
        self.length = length
        self.width = width

        self._buffer: list[str] = []

    def __str__(self) -> str:
        return "\n".join(self._buffer)

    def set_screen(self, path: Path) -> None:
        # NOTE: we could speed this up by doing validation in the read-in
        try:
            with open(path, 'r') as fp:
                self._buffer = [
                    line.strip('\n') for line in fp.readlines()
                ]
        except IOError as ex:
            raise MonitorError("Failed to read file") from ex

        # validation
        if max(len(l) for l in self._buffer) > self.width:
            raise MonitorError("Line is too long")
        if len(self._buffer) > self.length:
            raise MonitorError("File is too long")

    def print_screen(self) -> None:
        print(self)

@click.group()
def show():
    ...

@show.command()
def img():
    test_path = Path('/home/nonik/development/hey_siwi/test')
    monitor = Monitor(10, 10)
    monitor.set_screen(test_path)
    monitor.print_screen()

    return 0



