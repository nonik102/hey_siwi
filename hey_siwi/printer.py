from abc import ABC, abstractmethod

import emoji


class _Emoji:
    man_artist = emoji.emojize(":man_singer:")
    woman_artist = emoji.emojize(":woman_singer:")
    microphone = emoji.emojize(":microphone:")
    book = emoji.emojize(":closed_book:")
    timer = emoji.emojize(":hourglass_not_done:")
    j_j = emoji.emojize(":loudly_crying_face:")
    mag_glass = emoji.emojize(":magnifying_glass_tilted_right:")


class ColorMixin(ABC):
    def __init__(self) -> None:
        self.e = _Emoji()

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
