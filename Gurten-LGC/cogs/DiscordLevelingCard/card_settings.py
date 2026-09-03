from io import BufferedIOBase, IOBase, BytesIO
from os import PathLike
from typing import Optional, Union
from PIL import Image, ImageColor
import urllib.request
import os
from .error import InvalidImageType, InvalidImageUrl


class Settings:
    """
    Represents the settings for the rank card

    Parameters
    ----------
    background: :class:`Optional[Union[PathLike, BufferedIOBase, str]]`
        The background image for the rank card.
        This can be:
        - a path to a file
        - a file-like object in `rb` mode
        - a URL (starting with http)
        - a HEX color string (e.g. '#36393f')
        - a PIL Image object (will be kept as-is)

    bar_color: :class:`Optional[str]`
        The color of the XP bar. This can be a hex code or a color name.
    text_color: :class:`Optional[str]`
        The color of the text.
    background_color: :class:`Optional[str]`
        Fallback background color if background is not provided.
    """

    __slots__ = ('background', 'bar_color', 'text_color', 'background_color')

    def __init__(
        self,
        background: Optional[Union[PathLike, BufferedIOBase, str]] = None,
        background_color: Optional[str] = "#36393f",
        bar_color: Optional[str] = 'white',
        text_color: Optional[str] = 'white'
    ) -> None:
        self.background = background
        self.bar_color = bar_color
        self.text_color = text_color
        self.background_color = background_color

        if isinstance(self.background, IOBase):
            # BytesIO or other file-like object
            if not (self.background.seekable() and self.background.readable()):
                raise InvalidImageType(
                    f"File buffer {self.background!r} must be seekable and readable"
                )
            self.background = Image.open(self.background)

        elif isinstance(self.background, str):
            if self.background.startswith("http"):
                # URL
                self.background = Settings._image(self.background)
            elif os.path.exists(self.background):
                # Local file path
                self.background = Image.open(open(self.background, "rb"))
            else:
                # Treat as a color (HEX or name)
                try:
                    rgb = ImageColor.getrgb(self.background)
                    self.background = Image.new("RGB", (1, 1), rgb)
                except Exception:
                    raise InvalidImageType(
                        f"Invalid background string: '{self.background}'. "
                        "Must be a valid file path, URL, or color."
                    )

        elif self.background is None:
            # No background provided – use background_color
            try:
                rgb = ImageColor.getrgb(self.background_color)
                self.background = Image.new("RGB", (1, 1), rgb)
            except Exception as e:
                raise InvalidImageType(
                    f"Invalid background_color: '{self.background_color}'"
                ) from e

        else:
            raise InvalidImageType(
                f"background must be a path, url, file buffer, or color, "
                f"not {type(self.background)}"
            )

    @staticmethod
    def _image(url: str):
        try:
            with urllib.request.urlopen(url) as response:
                data = response.read()
            return Image.open(BytesIO(data))
        except Exception as e:
            raise InvalidImageUrl(f"Invalid image url: {url}") from e