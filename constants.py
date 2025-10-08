__all__ = [
    'display_ratio',

    'DEBUG_TIME_ROUNDING',

    'MAX_SEED',

    'RENDER_SIZE',
    'WINDOW_SCALE',
    'WINDOW_TITLE',
    'TARGET_FPS',

    'CONTROLS',
]

from global_imports import *

def display_ratio(value: int, relative_screen_size: int = 128*6) -> int: return round((value / relative_screen_size) * (RENDER_SIZE[0] * WINDOW_SCALE))

DEBUG_TIME_ROUNDING = 4

MAX_SEED = 1000000

RENDER_SIZE = (144,144) # Should be square
WINDOW_SCALE = 6
WINDOW_TITLE = 'LVL-3 Mental Health Game'
TARGET_FPS = 60

CONTROLS: dict[str,tuple[int,...]] = {
    'Back': (pygame.K_ESCAPE,),
    'Up': (pygame.K_w,pygame.K_UP,),
    'Down': (pygame.K_s,pygame.K_DOWN,),
    'Left': (pygame.K_a,pygame.K_LEFT,),
    'Right': (pygame.K_d,pygame.K_RIGHT,),
}