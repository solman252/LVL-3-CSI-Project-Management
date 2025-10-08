from global_imports import *
from constants import *
from utils import *

from random import choices as random_choice
from os import path as os_path, mkdir

class core:
    AcceptableImage = Union[Surface,'core.BaseImage',str]

    def slice_sheet(sheet: AcceptableImage, size: Coordinate, required_indices: Optional[Sequence[int]] = None) -> tuple[Surface, ...]:
        '''
        Slice an image into tiles of size `size`.
        Output is a tuple of pygame Surfaces taken from the original image, ordered starting at top left, going right then down.

        If `required_indices` is provided, the output will only include the subsurfaces at indices stated in `required_indices`.\\
        If not provided, it will return all subsurfaces.
        '''

        #region Validate args
        #region sheet
        if isinstance(sheet,core.BaseImage): sheet = sheet.surface() # BaseImage -> get surface
        if isinstance(sheet,str): sheet = pygame.image.load(f'assets/img/{sheet.removesuffix('.png')}.png').convert_alpha() # str -> load image
        if not isinstance(sheet,Surface): raise TypeError(f'`sheet` must be of type pygame.Surface, BaseImage (or children), or str, not {type(sheet).__name__}.') # TypeError
        #endregion sheet

        #region size
        if not is_coordinate(size): raise TypeError(f'`size` ({repr(size)}) must be a valid Coordinate object.') # TypeError
        if not is_coordinate(size,True): raise ValueError(f'`size` x ({size[0]}) and y ({size[1]}) must be integers.') # only int coords
        if not (0 < size[0] <= sheet.get_width() and 0 < size[1] <= sheet.get_height()): raise ValueError(f'`size` must be > (0,0) and < {sheet.get_size()}.') # size non existant or bigger than sheet
        #endregion size

        #endregion Validate args

        cols, rows = sheet.get_width() // int(size[0]), sheet.get_height() // int(size[1])
        sub_defs = [(x, y) for y in range(rows) for x in range(cols)] # get coords for each subsurface

        if required_indices is not None and (not isinstance(required_indices, Sequence) or isinstance(required_indices, bytes) or any(not (isinstance(i, int) and 0 <= i < cols*rows) for i in required_indices)): raise TypeError(f'`required_indices` must be a sequence of integers in range 0-{cols*rows-1}.') # validate required_indices

        required_indices = tuple(required_indices) if required_indices is not None else tuple(range(len(sub_defs))) # generate required_indices if not provided

        unique_surfaces = {}
        for i in set(required_indices): # get subsurface if not gotten already
            unique_surfaces[i] = sheet.subsurface(pygame.Rect(sub_defs[i][0] * size[0], sub_defs[i][1] * size[1], size[0], size[1]))

        return tuple(unique_surfaces[i] for i in required_indices) # return subsurfaces in order

    class AnimationProperties:
        '''
        Stores information about animation, such as framerate, frame size, and which frames go where.
        '''
        def __init__(self, framerate: float|int, size: Coordinate, frame_sheet_indices: Optional[Sequence[int]] = None):
            self.__locked = False
            self.framerate = framerate
            self.size = size
            self.frame_sheet_indices = frame_sheet_indices
        
        #region Properties
        #region Framerate property
        @property
        def framerate(self) -> float: return self.__framerate
        @framerate.setter
        def framerate(self, framerate: float|int):
            #region Validate args
            if self.__locked: raise AttributeError('Cannot edit a locked AnimationProperty.')
            if not isinstance(framerate,(int,float)): raise TypeError(f'`framerate` must be of type float or int, not {type(framerate).__name__}.')
            if framerate <= 0: raise ValueError(f'`framerate` ({framerate}) must be > 0.')
            #endregion Validate args

            self.__framerate = float(framerate)
        #endregion Framerate property
        
        #region Size property
        @property
        def size(self) -> Coordinate: return self.__size
        @size.setter
        def size(self, size: Coordinate):
            #region Validate args
            if self.__locked: raise AttributeError('Cannot edit a locked AnimationProperty.')
            if not is_coordinate(size): raise TypeError(f'`size` ({repr(size)}) must be a valid Coordinate object.')
            if not is_coordinate(size,True): raise ValueError(f'`size` x ({size[0]}) and y ({size[1]}) must be integers.')
            if size[0] < 0 or size[1] < 0: raise ValueError(f'`size` x ({size[0]}) and y ({size[1]}) must be > 0.')
            #endregion Validate args

            self.__size = v2(size)
        #endregion Size property

        #region Frame sheet indices property
        @property
        def frame_sheet_indices(self) -> tuple[int, ...] | None: return self.__frame_indices
        @frame_sheet_indices.setter
        def frame_sheet_indices(self, frame_sheet_indices: Sequence[int] | None):
            if self.__locked: raise AttributeError('Cannot edit a locked AnimationProperty.')

            if frame_sheet_indices == None: # clear sheet indices
                self.__frame_indices = None
                return
            
            if not isinstance(frame_sheet_indices, Sequence) or isinstance(frame_sheet_indices, bytes) or any(not (isinstance(x, int) and x >= 0) for x in frame_sheet_indices): raise TypeError(f'`frame_sheet_indices` must be a sequence of integers above 0.') # validate arg

            self.__frame_indices = tuple(frame_sheet_indices)
        #endregion Frame sheet indices property

        @property
        def frame_indices(self) -> tuple[int, ...] | None: return tuple(range(len(self.__frame_indices)))

        #endregion Properties
        
        def lock(self):
            self.__locked = True
        
        def copy(self, copy_locked_state: bool = False) -> 'core.AnimationProperties':
            if not isinstance(copy_locked_state,bool): raise TypeError(f'`copy_locked_state` must be of type bool, not {type(copy_locked_state).__name__}') # validate arg

            out = core.AnimationProperties(self.__framerate,self.__size,self.__frame_indices)
            if copy_locked_state and self.__locked: out.lock()
            return out

    class BaseImage:
        '''
        Base class for images.
        Automatically handles animations.
        '''
        def __init__(self, surf: 'core.AcceptableImage', anim_props: Optional['core.AnimationProperties'] = None):
            #region Validate args
            if not (anim_props is None or isinstance(anim_props,core.AnimationProperties)): raise TypeError(f'`anim_props` must be of type AnimationProperties, not {type(anim_props).__name__}.')

            #region surf
            if isinstance(surf,core.BaseImage): surf = surf.surface()
            if not isinstance(surf,(Surface,str)): raise TypeError(f'`surf` must be of type pygame.Surface, BaseImage (or children), or str, not {type(surf).__name__}.')
            if isinstance(surf,str): surf = pygame.image.load(f'assets/img/{surf.removesuffix('.png')}.png').convert_alpha()
            #endregion surf

            #endregion Validate args

            if anim_props is None: # normal image
                self.__anim_props = None
                self.__animated = False
                self.__surf = surf.copy()
                return
            
            # animated image
            
            self.__animated = True
            self.__anim_props: core.AnimationProperties = anim_props.copy()

            self.__frames: tuple[Surface, ...] = core.slice_sheet(surf,anim_props.size,anim_props.frame_sheet_indices)

            if self.__anim_props.frame_sheet_indices == None: self.__anim_props.frame_sheet_indices = tuple(range(len(self.__frames)))
            self.__anim_props.lock()

        #region Properties
        @property
        def animated(self) -> bool: return self.__animated

        #region Animation properties property
        @property
        def anim_props(self) -> Union['core.AnimationProperties',None]: return self.__anim_props
        anim_properties = anim_props
        animation_props = anim_props
        animation_properties = anim_props
        #endregion Animation properties property

        def surface(self, frame: Optional[int] = None) -> Surface:
            if not self.animated:
                return self.__surf
            
            if not isinstance(frame,int): raise TypeError(f'`frame` must be of type int, not {type(frame).__name__}.') # validate arg
            return self.__frames[frame % len(self.__anim_props.frame_indices)]
        surf = surface

        #endregion Properties

    class TileSetDefinition:
        '''
        Stores data for tileset definitions, such as standard tile indices, tile variations, and animated tile properties.
        '''
        def __init__(self, defs: dict[str,int|tuple[int,...]|dict[int|tuple[int,...],int]], rules: Optional[Callable] = None):
            if not isinstance(defs,dict): raise TypeError(f'`defs` must be of type dict, not {type(defs).__name__}.')

            #region Prepare storage
            self.standard: dict[str,int] = {}
            self.animated: dict[str,tuple[int,...]] = {}
            self.animated_framerates: dict[str,int] = {}
            self.variation_weights: dict[str,int] = {}
            self.variation_ids: dict[str,int] = {}
            self.tile_ids: list[str] = []
            #endregion Prepare storage
            
            # store data
            def add(tile_id: str, data: int|tuple[int,...]|dict[int|tuple[int,...],int], in_var: bool = False): # made a function for recursiveness when using variations
                if type(data) == int: self.standard[tile_id] = data

                elif type(data) == dict: # variation
                    if in_var: raise TypeError(f'Cannot add a variation to a variation.')
                    self.variation_ids[tile_id] = len(data)
                    variations = data
                    _tile_id = tile_id
                    variation_index = -1
                    for data, weight in variations.items():
                        variation_index += 1
                        tile_id = f'{_tile_id}_{variation_index}'
                        add(tile_id,data,True)
                        self.variation_weights[tile_id] = weight

                elif (isinstance(data, Sequence) and not isinstance(data, bytes)) and len(data) == 2 and type(data[0]) == int and ((isinstance(data[1], Sequence) and not isinstance(data[1], bytes)) and all(isinstance(x, int) and x >= 0 for x in data[1])): # animated
                    self.animated[tile_id] = data[1]
                    self.animated_framerates[tile_id] = data[0]
                
                else: raise TypeError(f'Values in `defs` must be of type int, tuple[int (> 0),tuple[int (>= 0), ...]], or dict, not {type(data).__name__}.') # incorrect tile def

            for tile_id, data in defs.items(): # create defs
                if type(tile_id) != str: raise TypeError(f'Keys in `defs` must be of type str, not {type(tile_id).__name__}.')
                self.tile_ids.append(tile_id)
                add(tile_id,data)

            #region rules
            __fallback_rules_val = tuple(defs.keys())[-1]
            def __fallback_rules(*args, **kwargs) -> str: return __fallback_rules_val
            if rules is not None and callable(rules): self.rules = rules
            else: self.rules = __fallback_rules
            #endregion rules

    class TileSet(BaseImage):
        '''
        TODO: DOCSTRING
        '''
        def __init__(self, sheet: 'core.AcceptableImage', tile_size: Coordinate, defs: Union['core.TileSetDefinition',dict[str,int|tuple[int,...]|dict[int|tuple[int,...],int]]]):
            #region Validate args
            if isinstance(defs,dict): defs = core.TileSetDefinition(defs)
            if not isinstance(defs,core.TileSetDefinition): raise TypeError(f'`defs` must be of type TileSetDefinition or dict, not {type(defs).__name__}.')
            if isinstance(sheet,str): sheet = f'tilesets/{sheet}'
            #endregion Validate args

            super().__init__(sheet)

            required_indices = list(defs.standard.values())
            [required_indices.extend(anim_indices) for anim_indices in defs.animated.values()]

            all_tiles = core.slice_sheet(sheet,tile_size)
            fps = defs.animated_framerates
            
            #region Prepare / fetch storage
            self.__tiles: dict[str,core.BaseImage] = {}
            self.__weights: dict[str,int] = defs.variation_weights
            self.__variated_tile_ids = defs.variation_ids
            self.__tile_ids = defs.tile_ids
            #endregion Prepare / fetch storage

            for tile_id, tile_index in defs.standard.items(): # create standard tile objects
                if tile_id not in self.__weights: self.__weights[tile_id] = 1 # if no weight provided, give base (1)
                self.__tiles[tile_id] = core.BaseImage(all_tiles[tile_index])
            
            for tile_id, tile_indices in defs.animated.items(): # create animated tile objects
                if tile_id not in self.__weights: self.__weights[tile_id] = 1 # if no weight provided, give base (1)
                self.__tiles[tile_id] = core.BaseImage(sheet,core.AnimationProperties(fps[tile_id],tile_size,tile_indices))
            
            self.rules = defs.rules

        #region Properties
        @property
        def tile_ids(self) -> tuple[str]: return self.__tile_ids
        
        def tile(self, id: str) -> 'core.BaseImage':
            if id in self.__variated_tile_ids: # variated tile, so pick random variation
                vars = range(0,self.__variated_tile_ids[id])
                weights = [self.__weights[f'{id}_{i}'] for i in vars]
                var = random_choice(vars,weights)[0]
                id = f'{id}_{var}'
            return self.__tiles[id]
        
        def weight(self, id: str) -> int:
            return self.__weights[id]
        
        #endregion Properties

        def _debug_export(self, folder_name: str):
            '''
            Export each tile as a .png file under ./debug/tileset_export/`folder_name`/
            '''

            #region Validate arg
            if type(folder_name) != str: raise TypeError(f'`folder_name` must be of type str, not {type(folder_name).__name__}.') # validate type
            for c in '/\\:*?"<>|.': folder_name = folder_name.replace(c,'_') # remove illegal file characters
            folder_name = f'./debug/tileset_export/{folder_name}'
            #endregion Validate arg

            if not os_path.exists('./debug'): mkdir('./debug') # create base folder if non existant
            if not os_path.exists('./debug/tileset_export'): mkdir('./debug/tileset_export') # create tileset_export folder if non existant
            if not os_path.exists(folder_name): mkdir(folder_name) # create tileset folder if non existant

            with open(f'{folder_name}/weights.txt', 'w') as f:
                [f.write(f'{k}: {v}\n') for k,v in self.__weights.items()]
            for name, img in self.__tiles.items():
                for c in '/\\:*?"<>|.': name = name.replace(c,'_') # remove illegal file characters
                if not img.animated:
                    pygame.image.save(img.surface(),f'{folder_name}/{name}.png')
                else:
                    for i in img.anim_props.frame_indices:
                        if not os_path.exists(f'{folder_name}/{name}'): mkdir(f'{folder_name}/{name}') # create anim folder if non existant
                        pygame.image.save(img.surface(i),f'{folder_name}/{name}/{i}.png')

class assets:
    class menu:
        ICON = core.BaseImage('menu/icon')

    class tilesets:
        class definitions:
            def __STANDARD_rules(tl: bool, t: bool, tr: bool, l: bool, r: bool, bl: bool, b: bool, br: bool):
                if not l and not t and r and br and b: return 'cotl'
                if not r and not t and l and bl and b: return 'cotr'
                if not l and not b and r and tr and t: return 'cobl'
                if not r and not b and l and tl and t: return 'cobr'

                if not br and b and bl and l and tl and t and tr and r: return 'citl'
                if not bl and b and br and r and tr and t and tl and l: return 'citr'
                if not tr and t and tl and l and bl and b and br and r: return 'cibl'
                if not tl and t and tr and r and br and b and bl and l: return 'cibr'

                if l and not t and r and br and b and bl: return 'et'
                if l and not b and r and tr and t and tl: return 'eb'
                if b and not l and t and tr and r and br: return 'el'
                if b and not r and t and tl and l and bl: return 'er'

                if not l and not t and not r and b: return 'st'
                if not l and not b and not r and t: return 'sb'
                if not b and not l and not t and r: return 'sl'
                if not b and not r and not t and l: return 'sr'

                if l and not tl and t and not tr and r and br and b and bl: return 'set'
                if l and not bl and b and not br and r and tr and t and tl: return 'seb'
                if b and not bl and l and not tl and t and tr and r and br: return 'sel'
                if b and not br and r and not tr and t and tl and l and bl: return 'ser'

                if l and tl and t and not tr and r and not b: return 'ttl'
                if r and tr and t and not tl and l and not b: return 'ttr'
                if l and bl and b and not br and r and not t: return 'tbl'
                if r and br and b and not bl and l and not t: return 'tbr'

                if not l and t and not r and b: return 'dv'
                if not t and r and not b and l: return 'dh'

                if not tl and t and tr and r and not br and b and bl and l: return 'qcl'
                if not tr and t and tl and l and not bl and b and br and r: return 'qcr'

                if tl and t and tr and l and r and bl and b and br: return 'fill'
            __STANDARD = {
                'cotl': 0, 'cotr': 1, 'citl': 2, 'citr': 3,
                'cobl': 4, 'cobr': 5, 'cibl': 6, 'cibr': 7,
                'et':   8, 'eb':   9, 'el':  10, 'er':  11,
                'st':  12, 'sb':  13, 'sl':  14, 'sr':  15,
                'set': 16, 'seb': 17, 'sel': 18, 'ser': 19,
                'ttl': 20, 'ttr': 21, 'tbl': 22, 'tbr': 23,
                'dv':  24, 'dh':  25, 'qcl': 26, 'qcr': 27,
                'fill': {
                    28: 4, 29: 4, 30: 16,
                    32: 4, 33: 4, 34: 16,
                    36: 4, 37: 4, 38: 16,
                }
            }
            STANDARD = core.TileSetDefinition(__STANDARD,__STANDARD_rules)

            def __ALT_rules(tl: bool, t: bool, tr: bool, l: bool, r: bool, bl: bool, b: bool, br: bool):
                if not l and not t and r and b: return 'cotl'
                if not r and not t and l and b: return 'cotr'
                if not l and not b and r and t: return 'cobl'
                if not r and not b and l and t: return 'cobr'

                if not br and b and bl and l and tl and t and tr and r: return 'citl'
                if not bl and b and br and r and tr and t and tl and l: return 'citr'
                if not tr and t and tl and l and bl and b and br and r: return 'cibl'
                if not tl and t and tr and r and br and b and bl and l: return 'cibr'

                if l and not t and r and br and b and bl: return 'et'
                if l and not b and r and tr and t and tl: return 'eb'
                if b and not l and t and tr and r and br: return 'el'
                if b and not r and t and tl and l and bl: return 'er'

                if not tl and t and tr and r and not br and b and bl and l: return 'qcl'
                if not tr and t and tl and l and not bl and b and br and r: return 'qcr'

                if tl and t and tr and l and r and bl and b and br: return 'fill'
            __ALT = {
                'cotl': 0, 'cotr': 1, 'citl': 2, 'citr': 3,  'et': 4,  'er':  5,  'qcl': 6,
                'cobl': 7, 'cobr': 8, 'cibl': 9, 'cibr': 10, 'eb': 11, 'el':  12, 'qcr': 13,
                'fill': {
                    14: 1, 15: 1,
                    16: 1, 17: 1,
                    18: 1, 19: 1,
                    20: 12,
                }
            }
            ALT = core.TileSetDefinition(__ALT,__ALT_rules)

            __SAND = __STANDARD.copy()
            __SAND['fill'] = {
                28: 8, 29: 8, 30: 8, 31: 8,
                32: 1, 33: 1, 34: 1,
            }
            SAND = core.TileSetDefinition(__SAND,__STANDARD_rules)

            __SAND_ALT = __ALT.copy()
            __SAND_ALT['fill'] = {
                14: 8, 15: 8,
                16: 8, 17: 8,
                18: 1, 19: 1, 20: 1,
            }
            SAND_ALT = core.TileSetDefinition(__SAND_ALT,__ALT_rules)

            __WATER = __STANDARD.copy()
            for k in __WATER.keys(): __WATER[k] = 0
            WATER = core.TileSetDefinition(__WATER,__STANDARD_rules)

        FOREST = core.TileSet('forest',(16,16),definitions.STANDARD)
        GRASS = core.TileSet('grass',(16,16),definitions.STANDARD)
        SAND = core.TileSet('sand',(16,16),definitions.SAND)
        WATER = core.TileSet('water',(16,16),definitions.WATER)

        FOREST_ALT = core.TileSet('forest_alt',(16,16),definitions.ALT)
        GRASS_ALT = core.TileSet('grass_alt',(16,16),definitions.ALT)
        SAND_ALT = core.TileSet('sand_alt',(16,16),definitions.SAND_ALT)

        PLAYER = core.TileSet('player',(16,16),{
            'sd': 0, 'su': 1, 'sl': 2, 'sr': 3,
            'wd': (30,(4,8)), 'wu': (30,(5,9)), 'wl': (30,(6,10)), 'wr': (30,(7,11)),
        })