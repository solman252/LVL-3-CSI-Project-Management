__all__ = [
    'debug',
    'iter_ranges',
    'is_coordinate',
    'is_color',
    'classonly',
    'np_utils',
]

from global_imports import *

#region Debug printing
__debug_current_depth: int = 0
__debug_prev_end: str = ''
__debug_timers: dict[str,float] = {}

from constants import DEBUG_TIME_ROUNDING as __DEBUG_TIME_ROUNDING
from time import time as __time
from itertools import product as __product

def debug(*values: object, sep: str|None = ' ', end: str|None = '\n', mode: str|None = 'content') -> None|float:
    if 'enable_debug' in environ:
        if 'debug_depth_prefix' not in environ: environ['debug_depth_prefix'] = '    '
        global __debug_current_depth, __debug_prev_end
        match(mode):
            case 'header':
                print(end=__debug_prev_end.replace('\n','\n'+__debug_current_depth*environ['debug_depth_prefix']))
                print(*values, sep=sep, end='', flush=True)
                __debug_prev_end = end or '\n'
                __debug_timers[__debug_current_depth] = __time()
                __debug_current_depth += 1
            case 'closer':
                __debug_current_depth -= 1
                sec_time = __time() - __debug_timers[__debug_current_depth]
                __debug_timers.pop(__debug_current_depth)
                print(end=__debug_prev_end.replace('\n','\n'+__debug_current_depth*environ['debug_depth_prefix']))
                print(''.join([str(v) for v in values]).replace('%T',str(round(sec_time,__DEBUG_TIME_ROUNDING+1))), sep=sep, end='', flush=True)
                __debug_prev_end = end or '\n'
                return sec_time
            case 'closer_eof':
                __debug_current_depth -= 1
                sec_time = __time() - __debug_timers[__debug_current_depth]
                __debug_timers.pop(__debug_current_depth)
                print(end=__debug_prev_end.replace('\n','\n'+__debug_current_depth*environ['debug_depth_prefix']))
                print(''.join([str(v) for v in values]).replace('%T',str(round(sec_time,__DEBUG_TIME_ROUNDING+1))), sep=sep, end='\n\033[0m', flush=True)
                __debug_prev_end = ''
                return sec_time
            case 'content':
                print(end=__debug_prev_end.replace('\n','\n'+__debug_current_depth*environ['debug_depth_prefix']))
                print(*values, sep=sep, end='', flush=True)
                __debug_prev_end = end or '\n'
            case None:
                print(*values, sep=sep, end='', flush=True)
                __debug_prev_end = end or '\n'
            case _:
                raise ValueError(mode)
#endregion printing

def iter_ranges(*dims: Union[int,tuple[int,int]]):
    '''
    Generator for shortening nested for loops.

    e.g.:
        for x, y, z in iter_ranges(2, 4, 6):
    is equivalent to:
        for z in range(6):
            for y in range(4):
                for x in range(2):
    '''
    ranges = [range(dim) if isinstance(dim,int) else range(*dim) for dim in dims]
    for all in __product(*reversed(ranges)):
        yield tuple(reversed(all))

def is_coordinate(obj, int_only: bool = False) -> bool:
    '''
    Checks if `obj` is a valid 2D pygame Coordinate.

    If `int_only` is True, it will only return True if `obj` is a valid pygame Coordinate, AND if the x and y components are both integers.
    '''
    if isinstance(obj, v2):
        x, y = obj.x, obj.y
    elif isinstance(obj, Sequence) and len(obj) == 2 and not isinstance(obj, bytes) and all(isinstance(x, (int, float)) for x in obj): # sequence of 2 numbers
        x, y = obj
    else: # invlaid type or components
        return False

    if int_only:
        return all(isinstance(v, int) or (isinstance(v, float) and v.is_integer()) for v in (x, y))
    return True

def is_color(obj) -> bool:
    '''
    Checks if `obj` is a valid pygame ColorValue.
    '''
    return (
        isinstance(obj, Color)
        or (isinstance(obj, Sequence) and len(obj) in (3,4) and not isinstance(obj, bytes) and all(isinstance(x, int) for x in obj)) # sequence of 3 or 4 ints
    )

class classonly:
    '''
    Allow access to classes and methods only through the parent class, not through instances of the parent class.

    e.g.:
        class foo:
            @classonly
            class boo: ...

        foo.boo --> No error
        foo().boo --> Attribute error
    '''
    def __init__(self, obj):
        self.obj = obj
        self.attribute_name = None

    def __set_name__(self, owner, name):
        self.attribute_name = name
        self.owner = owner

    def __get__(self, instance, owner = None):
        if instance is not None: # if accessed via instance not class
            cls = type(instance)

            # get suggestions for error
            from difflib import get_close_matches
            valid_attrs = [attr for attr in cls.__dict__ if not isinstance(cls.__dict__[attr], classonly)] # only suggest non-hidden attributes in attribute error
            suggestions = get_close_matches(self.attribute_name, valid_attrs)

            raise AttributeError(f'\'{cls.__name__}\' object has no attribute \'{self.attribute_name}\'{f'. Did you mean: \'{suggestions[0]}\'?' if suggestions else ''}') # mimic default python AttributeError

        return self.obj # Return this for no first argument in classonly methods
        # return self.obj.__get__(owner, owner) # Return this for first argument in classonly methods to be cls
    
import numpy as _np
class np_utils:
    '''
    A collection of various utility functions for numpy.
    '''

    @classonly
    class to_surf:
        @classonly
        def grayscale(arr: _np.ndarray) -> pygame.Surface:
            '''
            Creates a grayscale surface out of a 2D numpy float array.
            '''

            if not isinstance(arr, _np.ndarray): raise TypeError(f'`arr` must be of type numpy.ndarray, not {type(arr).__name__}.') # TypeError
            if len(arr.shape) != 2: raise ValueError('`arr` must be a 2-dimentional.') # not 2D

            arr = np_utils.normalize(arr) # normalize
            arr = _np.uint8(arr * 255) # scale to 0-255
            arr = _np.stack((arr, arr, arr), axis=-1) # create rgb channels from base
            return pygame.surfarray.make_surface(arr) # create surface
        
        @classonly
        def indexed(arr: _np.ndarray, colours: Sequence[ColorValue]) -> pygame.Surface:
            '''
            Creates a coloured surface out of a 2D numpy int array, using the data as indexes in `colours`.
            '''

            if not isinstance(arr, _np.ndarray): raise TypeError(f'`arr` must be of type numpy.ndarray, not {type(arr).__name__}.') # TypeError
            if len(arr.shape) != 2: raise ValueError('`arr` must be a 2-dimentional.') # not 2D
            for colour in colours:
                try: Color(colour)
                except: raise ValueError(f'{repr(colour)} is not a valid ColorValue.') # invalid colorvalue

            if arr.min() < 0: raise ValueError('Array contains one or more indices < 0.') # < 0
            if arr.max() >= len(colours): raise ValueError(f'Array contains one or more indices > {len(colours)-1}.') # out range of colours

            out = pygame.Surface(arr.shape, pygame.SRCALPHA) # create surface
            colour_array = _np.array([pygame.Color(c)[:4] for c in colours], dtype=_np.uint8) # create np array for fast indexing

            arr = _np.take(colour_array, arr, axis=0) # convert to array of colors

            rgb_view = pygame.surfarray.pixels3d(out) # get pixel rgb objects
            rgb_view[:] = arr[..., :3] # copy rgb over

            if out.get_flags() & pygame.SRCALPHA: # copy alpha if exists
                alpha_view = pygame.surfarray.pixels_alpha(out) # get pixel alpha objects
                alpha_view[:] = arr[..., 3] # copy alpha over

            del rgb_view, alpha_view  # unlock surface

            return out
    
    @classonly
    class from_surf:
        @classonly
        def grayscale(surf: Surface) -> _np.ndarray:
            '''
            Creates a 2D numpy float array out of a grayscale surface.
            '''
            if not isinstance(surf, Surface): raise TypeError(f'`surf` must be of type pygame.Surface, not {type(surf).__name__}.') # TypeError

            arr = pygame.surfarray.array3d(surf) # get rgb data

            return arr[..., 0].astype(_np.float32) / 255.0  # take red only since rgb are same value

        @classonly
        def indexed(surf: pygame.Surface, colours: Sequence[ColorValue]) -> _np.ndarray:
            '''
            Creates 2D numpy int array out of a coloured surface, using the pixel colours as indexes in `colours`.
            TODO: Add index error for bad colour
            '''

            if not isinstance(surf, Surface): raise TypeError(f'`surf` must be of type pygame.Surface, not {type(surf).__name__}.') # TypeError

            colour_array = _np.array([pygame.Color(c)[:4] for c in colours], dtype=_np.uint8) # create np array for fast indexing

            rgb_view = pygame.surfarray.array3d(surf) # get pixel rgb objects

            arr_pixels = _np.zeros((rgb_view.shape[0], rgb_view.shape[1], 4), dtype=_np.uint8) # prepare output
            arr_pixels[..., :3] = rgb_view # copy rgb over

            del rgb_view # unlock surface

            if surf.get_flags() & pygame.SRCALPHA: # if image has alpha
                alpha_view = pygame.surfarray.array_alpha(surf) # get pixel alpha objects
                arr_pixels[..., 3] = alpha_view # copy alpha over
                del alpha_view # unlock surface
            else:
                arr_pixels[..., 3] = 255 # copy alpha over (use 255)

            colour_to_index = {tuple(c): i for i, c in enumerate(colour_array)} # create a dict for quick lookup

            # flatten to speed up mapping
            flat_pixels = arr_pixels.reshape(-1, 4)
            flat_indices = _np.array([colour_to_index[tuple(px)] for px in flat_pixels], dtype=_np.int32)

            return flat_indices.reshape(arr_pixels.shape[:2]) # reshape to orig shape

    @classonly
    def normalize(arr: _np.ndarray, m: float|int = 0, M: float|int = 1) -> _np.ndarray:
        '''
        Returns a copy of `arr` that has been normalized between `m` and `M`.
        '''

        if not isinstance(arr, _np.ndarray): raise TypeError(f'`arr` must be of type numpy.ndarray, not {type(arr).__name__}.') # TypeError

        old_min = _np.min(arr)
        old_max = _np.max(arr)
        if old_min == old_max: return _np.full_like(arr, m) # if all values the same, faster to generate new array with new min
        return (arr - old_min) / (old_max - old_min) * (M - m) + m # return normalized copy
    
    @classonly
    def indicize(arr: _np.ndarray) -> _np.ndarray:
        '''
        Returns a copy of `arr` that converts items to their index in a sorted, unique version of `arr`.
        '''
        if not isinstance(arr, _np.ndarray): raise TypeError(f'`arr` must be of type numpy.ndarray, not {type(arr).__name__}.') # TypeError
        return _np.searchsorted(_np.unique(arr), arr) # unique makes a sorted array of arr's values, searchsorted converts the array to indices of unique
    
    @classonly
    def quantize(arr: _np.ndarray, levels: int) -> float:
        '''
        Quantizes `arr` to `levels` levels.
        '''

        if not isinstance(arr, _np.ndarray): raise TypeError(f'`arr` must be of type numpy.ndarray, not {type(arr).__name__}.') # TypeError

        if not isinstance(levels,int): raise TypeError(f'`levels` must be of type int, not {type(levels).__name__}.') # TypeError
        if levels <= 0: raise ValueError(f'`levels` must be > 0.') # > 0

        def _quantize(v: float, n: int) -> float:
            return _np.clip(_np.floor(v * n) / (n - 1), 0, 1)
        
        return _np.vectorize(_quantize)(arr, levels)