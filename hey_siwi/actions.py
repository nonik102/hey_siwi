from abc import ABC


class ActionConfig:
    pass


class Action(ABC):
    def execute(self, config: ActionConfig | None = None) -> None: ...
