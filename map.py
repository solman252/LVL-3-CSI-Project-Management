from global_imports import *

from constants import *

import assets
from utils import *

import numpy as np
import scipy.ndimage as scnp

from perlin_noise import PerlinNoise
import random

from os import path as os_path, mkdir

def gen_perlin(size: Coordinate, *layers: Union[int, tuple[int, int]]) -> np.ndarray:
    #region Validate size
    if not is_coordinate(size): raise TypeError(f'`size` ({repr(size)}) must be a valid Coordinate object.') # TypeError
    if not is_coordinate(size,True): raise ValueError(f'`size` x ({size[0]}) and y ({size[1]}) must be integers.') # only int coords
    if not (0 < size[0] and 0 < size[1]): raise ValueError(f'`size` must be > (0,0).') # size non existant

    if len(layers) == 0: raise ValueError(f'`layers` must have atleast one item.') # no layers
    #endregion Validate size

    #region Generate layers of perlin noise
    noises: list[PerlinNoise] = []
    for layer in layers:
        if type(layer) == int:
            octaves = layer
            seed = random.randint(0,MAX_SEED)
        elif is_coordinate(layer,True):
            octaves = layer[0]
            seed = layer[1]
        else:
            raise TypeError(layer) # invalid layer
        
        noises.append(PerlinNoise(octaves,seed))
    #endregion Generate layers of perlin noise
    
    #region Create data
    out = np.full(size,0,float)
    for x,y in iter_ranges(*size): # merge layers, halving influence every layer
        fac = 1.0
        data = 0.0
        for noise in noises:
            data += fac * noise([x/size[0],y/size[1]],(1,1)) # apply noise from this layer
            fac /= 2 # half next layer's influence
        out[x][y] = data
    #endregion Create data
    
    return np_utils.normalize(out) # normalize result

def gen_island_vignette(noise_map: np.ndarray) -> np.ndarray:
    size = noise_map.shape
    w, h = size

    # Shape and vignette parameters
    side = (74 / 128) * min(size)
    corner_radius = 0.1 * side
    amplitude = 0.125 * min(size)
    falloff = amplitude
    half_size = np.array(size) * (74 / 256)

    arr = np.zeros(size, dtype=float)

    def rounded_square_sdf(dx: float, dy: float) -> float:
        p = np.array([dx, dy])
        q = np.abs(p) - half_size
        outside = np.maximum(q, 0.0)
        inside = np.minimum(max(q[0], q[1]), 0.0)
        return np.linalg.norm(outside) + inside - corner_radius

    cx, cy = w // 2, h // 2

    for x, y in iter_ranges(w, h):
        dx, dy = x - cx, y - cy

        # Base rounded-square distance
        dist = rounded_square_sdf(dx, dy)

        # Sample inverted noise for bump modulation
        nval = 1 - np.rot90(noise_map,2)[x % w, y % h]
        bump_dist = dist - amplitude * (nval - 0.5)

        # White center, black edges with smooth fade
        t = bump_dist / falloff
        brightness = np.clip(1 - t, 0, 1)

        arr[y, x] = brightness

    return arr

class Terrain:
    '''
    Generates / stores terrain data such as seed, biomes, and tiles.
    '''
    def __init__(self, size: Coordinate, seed: Optional[float|int|str] = None, detail_layers: int = 2, base_octaves: int = 3, octave_multiplier: int = 4):
        #region Validate args
        #region Validate size
        if not is_coordinate(size): raise TypeError(f'`size` ({repr(size)}) must be a valid Coordinate object.') # TypeError
        if not is_coordinate(size,True): raise ValueError(f'`size` x ({size[0]}) and y ({size[1]}) must be integers.') # only int coords
        if not (0 < size[0] and 0 < size[1]): raise ValueError(f'`size` must be > (0,0).') # size non existant
        debug(f'Size: {size[0]}x{size[1]}')
        #endregion Validate size

        #region Validate seed
        if type(seed) == str and seed.isdecimal(): seed = int(seed) # convert strings of int to int

        if type(seed) == str: # convert string seeds to ints
            str_seed = seed
            seed: int = 0
            for c in str_seed:
                seed += ord(c)
            debug(f'Seed: {str_seed} ({seed})')
        elif seed == None or seed == 0 or seed == '': # empty seed
            seed = random.randint(0,MAX_SEED)
            debug(f'Random seed: {seed}')
        else: # float or int seed
            seed = int(seed)
            debug(f'Seed: {seed}')
        #endregion Validate seed

        #region Validate detail_layers
        if not isinstance(detail_layers,int): raise TypeError(f'`detail_layers` must be of type int, not {type(detail_layers).__name__}.') # TypeError
        if detail_layers <= 0: raise ValueError(f'`detail_layers` must be > 0.') # > 0
        #endregion Validate detail_layers

        #region Validate base_octaves
        if not isinstance(base_octaves,int): raise TypeError(f'`base_octaves` must be of type int, not {type(base_octaves).__name__}.') # TypeError
        if base_octaves <= 0: raise ValueError(f'`base_octaves` must be > 0.') # > 0
        #endregion Validate base_octaves

        #region Validate octave_multiplier
        if not isinstance(octave_multiplier,int): raise TypeError(f'`octave_multiplier` must be of type int, not {type(octave_multiplier).__name__}.') # TypeError
        if octave_multiplier <= 1: raise ValueError(f'`octave_multiplier` must be > 1.') # > 1
        #endregion Validate octave_multiplier

        #endregion Validate args

        self.size: tuple[int,int] = tuple(size)
        self.seed: int = seed

        #region Biome definitions
        self.biomes = (
            (assets.img.tilesets.WATER,      0, '#9BD4C3'),
            (assets.img.tilesets.SAND_ALT,   1, '#E8CFA6'),
            (assets.img.tilesets.GRASS_ALT,  2, '#C0D470'),
            (assets.img.tilesets.FOREST_ALT, 3, '#8DB15D'),
        )
        self.quant_biomes = (
            0,
            1,1,
            2,2,2,2,
            3,3,3,0,0,
        )
        #endregion Biome definitions

        #region Generate Datas
        #region Raw perlin
        #region Prepare layers argument
        layers: list[tuple[int,int]] = []
        octaves = base_octaves
        for i in range(detail_layers): # create `detail` noise layers
            layers.append((octaves,self.seed+i))
            octaves *= octave_multiplier # increase detail for every layer
        #endregion Prepare layers argument

        debug('Generating base noise...',end = '  ',mode='header')
        self.raw_perlin = gen_perlin(self.size,*layers)
        debug('Done after %Ts.',mode='closer')
        #endregion Raw perlin

        #region Biomes
        debug('Generating biome data...',mode='header')

        #region Island Vignette
        debug('Generating island vignette...',end = '  ',mode='header')
        self.island_vignette = gen_island_vignette(self.raw_perlin)
        self.vig_perlin = self.raw_perlin * self.island_vignette
        debug('Done after %Ts.',mode='closer')
        #endregion Island Vignette

        #region Quantize
        debug('Quantizing vignetted noise...',end = '  ',mode='header')
        self.quantized_perlin = np_utils.quantize(self.vig_perlin,len(self.quant_biomes))
        debug('Done after %Ts.',mode='closer')
        #endregion Quantize

        #region Assign biome ids
        if 'debug_enable_custom_map' not in environ:
            debug('Assigning base biome IDs...',end = '  ',mode='header')
            self.biome_data = np_utils.indicize(self.quantized_perlin) # convert to ranks
            self.biome_data = np.array(self.quant_biomes)[self.biome_data] # convert to biome ids from self.quant_biomes
            debug('Done after %Ts.',mode='closer')
        else:
            debug('Loading base biome IDs from ./debug/terrain_export/biome_data_unchanged.png...',end = '  ',mode='header')
            self.biome_data = np_utils.from_surf.indexed(pygame.image.load('./debug/terrain_export/biome_data_unchanged.png'),[b[2] for b in self.biomes])
        #endregion Assign biome ids

        if 'debug_enable_custom_map' in environ:
            self.biome_data = np_utils.from_surf.indexed(pygame.image.load('./debug/terrain_export/biome_data_unchanged.png'),[b[2] for b in self.biomes])

        self.biome_data_unchanged = self.biome_data.copy()

        #region Adjust biome ids
        # TODO: clean
        if 'debug_enable_custom_map' not in environ:
            debug('Adjusting biome IDs...',mode='header')

            self.old_biome_data = None
            i = 0
            while not np.array_equal(self.old_biome_data,self.biome_data):
                self.old_biome_data = self.biome_data.copy()
                i+= 1
                if i == 2: debug('Repeating as nessesary...',end = '  ',mode='header')
                #region Remove Small Pockets
                if i == 1: debug('Removing tiny biomes...',end = '  ',mode='header')

                for biome_id in np.unique(self.biome_data):
                    labeled, num_features = scnp.label(self.biome_data == biome_id)
                    for region_id in range(1, num_features + 1):
                        region_mask = labeled == region_id
                        if np.sum(region_mask) < (14/128)*(sum(self.size)/2):
                            # Replace small region with the most common *neighboring biome*
                            # Find border pixels of the region
                            border = np.logical_and(
                                np.logical_not(region_mask),
                                np.logical_or.reduce([
                                    np.roll(region_mask, 1, 0),
                                    np.roll(region_mask, -1, 0),
                                    np.roll(region_mask, 1, 1),
                                    np.roll(region_mask, -1, 1)
                                ])
                            )
                            if np.any(border):
                                neighbor_values = self.biome_data[border]
                                self.biome_data[region_mask] = np.bincount(neighbor_values).argmax()
                            
                if i == 1: debug('Done after %Ts.',mode='closer')
                #endregion Remove Small Pockets

                #region Remove Pokey Bits
                if i == 1: debug('Removing pokey bits...',end = '  ',mode='header')

                shifts = [(-1,0),(1,0),(0,-1),(0,1)]
                for x,y in iter_ranges(*self.size):
                    biome = self.biome_data[x][y]
                    same_neighbors = 0
                    neighbor_values = []
                    for dy, dx in shifts:
                        ny, nx = y + dy, x + dx
                        if 0 <= ny < self.size[1] and 0 <= nx < self.size[0]:
                            neighbor_values.append(self.biome_data[nx][ny])
                            if self.biome_data[nx][ny] == biome:
                                same_neighbors += 1
                    # If isolated or nearly isolated, replace
                    if same_neighbors <= 1:
                        if neighbor_values:
                            replacement = np.bincount(neighbor_values).argmax()
                            self.biome_data[x][y] = replacement
                            
                if i == 1: debug('Done after %Ts.',mode='closer')
                #endregion Remove Pokey Bits

                #region Remove Thin Bits
                if i == 1: debug('Removing thin bits...',end = '  ',mode='header')

                shifts = [(-1,0),(1,0),(0,-1),(0,1)]  # up, down, left, right
                opposites = [(0,1),(1,0)]  # indices of neighbor pairs: vertical, horizontal
                changes = []

                for x, y in iter_ranges(*self.size):
                    biome = self.biome_data[x][y]

                    neighbors = [
                        self.biome_data[x-1][y] if x-1 >= 0 else -1,  # left
                        self.biome_data[x+1][y] if x+1 < self.size[0] else -1,  # right
                        self.biome_data[x][y-1] if y-1 >= 0 else -1,  # up
                        self.biome_data[x][y+1] if y+1 < self.size[1] else -1   # down
                    ]
                    # same-id flags
                    same = [1 if n == biome else 0 for n in neighbors]

                    # Check opposite pairs
                    vertical = same[2] and same[3]   # up & down
                    horizontal = same[0] and same[1] # left & right

                    # If neither vertical nor horizontal line, remove it
                    if (vertical or horizontal):
                        # Replace with most common neighbor
                        valid_neighbors = [n for n in neighbors if n >= 0]
                        if valid_neighbors:
                            replacement = np.bincount(valid_neighbors).argmax()
                            changes.append((x,y,replacement))
                for (x,y,replacement) in changes:
                    self.biome_data[x][y] = replacement
                            
                if i == 1: debug('Done after %Ts.',mode='closer')
                #endregion Remove Thin Bits
            if i >= 2: debug('Done after %Ts.',mode='closer')

            debug('Biome ID adjustment complete after %Ts.',mode='closer')
        #endregion Adjust biome ids

        debug('Biome data generated after %Ts.',mode='closer')
        #endregion Biomes

        #region Calculate tiles
        debug('Calculating tiles...',end = '  ',mode='header')
        self.tile_data = np.full(self.size,0,int)
        self.tile_data_under = np.full(self.size,0,int)

        for x,y in iter_ranges(*self.size):
            biome_id: int = self.biome_data[x][y]
            tileset, z, _ = self.biomes[biome_id]

            neighbors = []
            connections = [True]*8
            i = -1
            for dx,dy in iter_ranges((-1,2),(-1,2)):
                if dx == 0 and dy == 0: continue
                i += 1
                if not (0 <= x+dx < self.size[0] and 0 <= y+dy < self.size[1]):
                    n_id = 0
                else:
                    n_id = self.biome_data[x+dx][y+dy]
                n_z = self.biomes[n_id][1]
                neighbors.append(n_id)
                if n_id != biome_id and n_z <= z: connections[i] = False

            tile: str = tileset.rules(*connections)

            if tile is None or tile == '':
                self.tile_data_under[x][y] = -1
                self.tile_data[x][y] = -1
                continue
            
            under: int = -1 if tile == 'fill' else [n_id for n_id in neighbors if not n_id == biome_id][0]
            if under is None: under = -1
            
            # try:
            self.tile_data_under[x][y] = under
            # except:
            #     debug(y,under)
            self.tile_data[x][y] = tileset.tile_ids.index(tile)

        debug('Done after %Ts.',mode='closer')
        #endregion Calculate tiles

        #endregion Generate Datas

    def _debug_export(self):
        '''
        Export each data array as a .png file under ./debug/tileset_export/
        '''

        if 'enable_debug' in environ:
            if not os_path.exists('./debug'): mkdir('./debug') # create base folder if non existant
            if not os_path.exists('./debug/terrain_export'): mkdir('./debug/terrain_export') # create terrain_export folder if non existant

            biome_colours = [b[2] for b in self.biomes]

            pygame.image.save(np_utils.to_surf.grayscale(self.raw_perlin),'./debug/terrain_export/0_raw_perlin.png')
            pygame.image.save(np_utils.to_surf.grayscale(self.island_vignette),'./debug/terrain_export/1_island_vignette.png')
            pygame.image.save(np_utils.to_surf.grayscale(self.vig_perlin),'./debug/terrain_export/2_vig_perlin.png')
            pygame.image.save(np_utils.to_surf.grayscale(self.quantized_perlin),'./debug/terrain_export/3_quantized_perlin.png')
            pygame.image.save(np_utils.to_surf.indexed(self.biome_data_unchanged,biome_colours),'./debug/terrain_export/4_biome_data_unchanged.png')
            pygame.image.save(np_utils.to_surf.indexed(self.biome_data,biome_colours),'./debug/terrain_export/5_biome_data.png')

            bg = Surface((self.size[0]*16,self.size[1]*16),pygame.SRCALPHA)
            for x,y in iter_ranges(*self.size):
                tile_id: int = self.tile_data[x][y]

                if tile_id == -1: continue

                biome_id: int = self.biome_data[x][y]
                tileset, *_ = self.biomes[biome_id]
                tile_id = tileset.tile_ids[tile_id]
                under: int = self.tile_data_under[x][y]

                if under != -1:
                    u_tileset = self.biomes[under][0]
                    bg.blit(u_tileset.tile('fill').surf(),(x*16,y*16))
                
                bg.blit(tileset.tile(tile_id).surf(),(x*16,y*16))

            pygame.image.save(bg,'./debug/terrain_export/6_bg.png')


# class Map: