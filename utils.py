__all__ = [
    'debug',
    'iter_ranges',
    'is_coordinate',
    'classonly',
]

from global_imports import *

#region Debug printing
__debug_current_depth: int = 0
__debug_prev_end: str = ''
__debug_timers = {}

from constants import DEBUG_TIME_ROUNDING as __DEBUG_TIME_ROUNDING
from time import time as __time

def debug(*values: object, sep: str|None = ' ', end: str|None = '\n', mode: str|None = 'content') -> None:
    if 'enable_debug' in environ:
        if 'debug_prefix' not in environ: environ['debug_prefix'] = '    '
        global __debug_current_depth, __debug_prev_end
        match(mode):
            case 'header':
                print(end=__debug_prev_end.replace('\n','\n'+__debug_current_depth*environ['debug_prefix']))
                print(*values, sep=sep, end='', flush=True)
                __debug_prev_end = end or '\n'
                __debug_timers[__debug_current_depth] = __time()
                __debug_current_depth += 1
            case 'closer':
                __debug_current_depth -= 1
                sec_time = __time() - __debug_timers[__debug_current_depth]
                __debug_timers.pop(__debug_current_depth)
                print(end=__debug_prev_end.replace('\n','\n'+__debug_current_depth*environ['debug_prefix']))
                print(''.join([str(v) for v in values]).replace('%T',str(round(sec_time,__DEBUG_TIME_ROUNDING+1))), sep=sep, end='', flush=True)
                __debug_prev_end = end or '\n'
            case 'closer_eof':
                __debug_current_depth -= 1
                sec_time = __time() - __debug_timers[__debug_current_depth]
                __debug_timers.pop(__debug_current_depth)
                print(end=__debug_prev_end.replace('\n','\n'+__debug_current_depth*environ['debug_prefix']))
                print(''.join([str(v) for v in values]).replace('%T',str(round(sec_time,__DEBUG_TIME_ROUNDING+1))), sep=sep, end='\n\033[0m', flush=True)
                __debug_prev_end = ''
            case 'content':
                print(end=__debug_prev_end.replace('\n','\n'+__debug_current_depth*environ['debug_prefix']))
                print(*values, sep=sep, end='', flush=True)
                __debug_prev_end = end or '\n'
            case None:
                print(*values, sep=sep, end='', flush=True)
                __debug_prev_end = end or '\n'
            case _:
                raise ValueError(mode)
#endregion printing

def iter_ranges(*dims: Sequence[int]):
    '''
    Generator for shortening nested for loops.

    e.g.:
        for x, y, z in iter_ranges(2, 4, 6):
    is equivalent to:
        for z in range(6):
            for y in range(4):
                for x in range(2):
    '''
    ranges = [range(dim) for dim in dims]
    from itertools import product
    for all in product(*reversed(ranges)):
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