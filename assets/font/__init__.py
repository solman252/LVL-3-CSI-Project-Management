from pygame import font as __font
from constants import display_ratio as __display_ratio

__font_sizes = {}

def font(size: int, font_name: str = 'font') -> __font.Font:
    mode = 'file'
    if font_name.startswith('_sys: '):
        font_name = font_name.removeprefix('_sys: ')
        mode = 'sysfont'
    if f'{font_name}_{size}' in __font_sizes:
        return __font_sizes[f'{font_name}_{size}']
    if mode == 'file':
        try:
            out = __font.Font(f'assets/font/{font_name}.ttf', __display_ratio(size))
        except FileNotFoundError:
            out = __font.Font(f'assets/font/font.ttf', __display_ratio(size))
    else:
        try:
            out = __font.SysFont(font_name, __display_ratio(size))
        except FileNotFoundError:
            out = __font.SysFont('Arial', __display_ratio(size))
    __font_sizes[f'{font_name}_{size}'] = out
    return out