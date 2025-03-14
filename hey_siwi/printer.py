from abc import ABC, abstractmethod


class ColorMixin(ABC):
    @staticmethod
    def color_8bit(code: int) -> str:
        return f"\033[{code}m"

    @property
    def noc(self) -> str:
        return self.color_8bit(0)

    @property
    @abstractmethod
    def c1(self) -> str: ...

    @property
    @abstractmethod
    def c2(self) -> str: ...

    @property
    @abstractmethod
    def c3(self) -> str: ...


class Classic(ColorMixin):
    @property
    def c1(self) -> str:
        return self.color_8bit(91)

    @property
    def c2(self) -> str:
        return self.color_8bit(92)

    @property
    def c3(self) -> str:
        return self.color_8bit(96)


class Printer(Classic):
    pass
