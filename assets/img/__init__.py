from global_imports import *
from constants import *
from utils import *

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
                from random import choices as random_choice
                var = random_choice(vars,weights)[0]
                id = f'{id}_{var}'
            return self.__tiles[id]
        
        def weight(self, id: str) -> int:
            return self.__weights[id]
        
        #endregion Properties

        def _debug_export(self, folder_name: str):
            '''
            Export each tile as a .png file under ./tileset_debug_export/`folder_name`/
            '''

            if type(folder_name) != str: raise TypeError(f'`folder_name` must be of type str, not {type(folder_name).__name__}.') # validate type
            for c in '/\\:*?"<>|.': folder_name = folder_name.replace(c,'_') # remove illegal file characters
            folder_name = f'./tileset_debug_export/{folder_name}'
        
            from os import path, mkdir

            if not path.exists('./tileset_debug_export'): mkdir('./tileset_debug_export') # create base folder if non existant
            if not path.exists(folder_name): mkdir(folder_name) # create tileset folder if non existant

            with open(f'{folder_name}/weights.txt', 'w') as f:
                [f.write(f'{k}: {v}\n') for k,v in self.__weights.items()]
            for name, img in self.__tiles.items():
                for c in '/\\:*?"<>|.': name = name.replace(c,'_') # remove illegal file characters
                if not img.animated:
                    pygame.image.save(img.surface(),f'{folder_name}/{name}.png')
                else:
                    for i in img.anim_props.frame_indices:
                        if not os.path.exists(f'{folder_name}/{name}'): mkdir(f'{folder_name}/{name}') # create anim folder if non existant
                        pygame.image.save(img.surface(i),f'{folder_name}/{name}/{i}.png')

class assets: ...