from os import environ
environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'

import pygame
from pygame import Vector2 as v2, Color, Surface

from typing import Union, Tuple, Sequence, Callable


from typing_extensions import Protocol as __Protocol # would put in the region, but it wont work for some reason if i do
#region pygame _commons.pyi
Coordinate = Union[Tuple[float|int, float|int], Sequence[float|int], pygame.Vector2]

RGBAOutput = Tuple[int, int, int, int]
ColorValue = Union[Color, int, str, Tuple[int, int, int], RGBAOutput, Sequence[int]]

#region Rect
_CanBeRect = Union[
    pygame.Rect,
    Tuple[Union[float, int], Union[float, int], Union[float, int], Union[float, int]],
    Tuple[Coordinate, Coordinate],
    Sequence[Union[float, int]],
    Sequence[Coordinate],
]
class _HasRectAttribute(__Protocol): rect: Union['RectValue', Callable[[], 'RectValue']]
RectValue = Union[_CanBeRect, _HasRectAttribute]
#endregion Rect

#endregion pygame _commons.pyi