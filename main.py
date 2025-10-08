#region Imports
from global_imports import *

from constants import * # load constants

#region Pygame Inits
pygame.init()
clock = pygame.time.Clock()
display = pygame.display.set_mode(v2(RENDER_SIZE)*WINDOW_SCALE)
pygame.display.set_caption(WINDOW_TITLE)
#endregion Pygame Inits

#region Non-Main
from utils import *
#endregion Non-Main

#endregion Imports

#region Game Setup
debug('Starting game setup:',mode='header')

running = True
screen = Surface(RENDER_SIZE)

debug('Game setup complete after %Ts.',mode='closer')
#endregion Game Setup

#region Main Loop
debug('Starting main loop.',mode='header')
while running:
    #region Events
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        #region Controls
        elif event.type == pygame.KEYDOWN:
            if event.key in CONTROLS['Back']:
                running = False
        #endregion Controls
    #endregion Events

    #region Refresh Display + Next frame Setup
    display.blit(pygame.transform.scale(screen,v2(RENDER_SIZE)*WINDOW_SCALE),(0,0)) # scale up the render to the window size and display it
    pygame.display.flip() # refresh the display
    screen.fill((0,0,0)) # reset the screen for the next frame
    clock.tick(TARGET_FPS) # sleep until next frame
    #endregion Refresh Display + Next frame Setup
debug('Main loop ended after %Ts.',mode='closer_eof')
#endregion Main Loop