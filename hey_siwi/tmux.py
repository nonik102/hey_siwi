from __future__ import annotations
from dataclasses import dataclass
from types import TracebackType
from typing import IO, Any, ContextManager
import libtmux as tmux
from pydantic import BaseModel
import json


class TmuxConfig(BaseModel):
    windows: list[dict[str, Any]]

    @classmethod
    def from_json(cls, fp: IO[str]) -> TmuxConfig:
        attrs = json.load(fp)
        return cls(**attrs)


class TmuxManager(ContextManager):
    def __init__(self, config: TmuxConfig) -> None:
        self._server: tmux.Server | None = None
        self._session: tmux.Session | None = None
        self._windows: list[tmux.Window] = []
        self._config = config

    @property
    def server(self) -> tmux.Server:
        if not self._server:
            raise RuntimeError
        return self._server

    @property
    def session(self) -> tmux.Session:
        if not self._session:
            raise RuntimeError
        return self._session

    def __enter__(self) -> TmuxManager:
        # NOTE: do NOT kill the server, other people might be using it! :)
        self._server = tmux.Server()
        return super().__enter__()

    def start(self) -> None:
        self._session = self.server.new_session("hey_siwi")
        self._windows = [
            self._session.new_window(**attrs) for attrs in self._config.windows
        ]
        print(f"spawned {len(self._windows)} windows")


    def __exit__(self, exc_type: type[BaseException] | None, exc_value: BaseException | None, traceback: TracebackType | None, /) -> None:
        self.session.kill()
        return None


