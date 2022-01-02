import json
import os
import pygame as pg
import random
global screen

pg.init()
pg.display.set_caption("Minesweeper")
pg.mixer.init()

stats_path = "STATS.json"

def get_stats():
    path = stats_path

    # Generate the stats dictionary if it doesn't already exist
    if not os.path.isfile(path):
        stats = {
            'Tiles Revealed': 0,
            'Flags Placed': 0,
            'Times Chorded': 0,
            'Games Lost': 0,
            'Games Won': 0,
        }
        
        # Keep count of how many of each number is seen also
        for i in range(9):
            stats[f"{i}s Revealed"] = 0
        return stats

    else:
        with open(path, 'r') as f:
            return json.load(f)


def save_stats(stats):
    path = stats_path
    with open(path, 'w') as f:
        json.dump(stats, f, indent=4)
    

class Application:
    def __init__(self, grid, sidebar):
        self.running = True
        self.clock = pg.time.Clock()
        self.fps = 60

        self.grid = grid
        self.sidebar = sidebar
        
        self.selected_tile = None
        self.chording = False

        self.has_saved_stats = False

    def event_loop(self):
        for event in pg.event.get():
            if event.type == pg.QUIT:
                self.quit()

            mouse_pos = pg.mouse.get_pos()

            if self.grid.is_mouse_over_grid(mouse_pos):
                self.handle_grid_events(event, mouse_pos)
            elif self.selected_tile is not None:
                self.grid.unchord(self.selected_tile)
                
            if self.sidebar.is_mouse_over_sidebar(mouse_pos):
                if self.sidebar.is_mouse_over_face(mouse_pos):
                    self.handle_face_events(event, mouse_pos)
                else:
                    self.sidebar.release_face()

            # When to save the stats (it should be after a click and should happen once)
            if self.grid.is_game_over and not self.has_saved_stats:
                save_stats(STATS)
                self.has_saved_stats = True

    def handle_face_events(self, event, mouse_pos):
        x, y = mouse_pos
        click = pg.mouse.get_pressed()

        if click[0]:
            self.sidebar.press_face()
        if event.type == pg.MOUSEBUTTONUP:
            if event.button == 1:
                self.sidebar.release_face()
                self.reset()

    def handle_grid_events(self, event, mouse_pos):
        x, y = mouse_pos
        
        if self.grid.is_game_over:
            return
        
        click = pg.mouse.get_pressed()

        # If holding left click button
        if click[0]:
            # So that the sound only plays once
            if not self.grid.is_holding:
                self.grid.play_sfx('click')
                
            self.grid.is_holding = True

            # Chording (holding left and right click)
            if self.selected_tile is not None:
                if click[2]:
                    self.grid.unchord(self.selected_tile)
                    self.selected_tile = self.grid.get_clicked_tile(x, y)
                    self.grid.chord(self.selected_tile)

                    # So that the sound only plays once
                    if not self.chording:
                        self.grid.play_sfx('chord')
                    self.chording = True
                else:
                    self.selected_tile.release()
                    
            self.selected_tile = self.grid.get_clicked_tile(x, y)
            self.selected_tile.hold_down()            

        else:
            self.grid.is_holding = False

            if self.selected_tile is not None:
                self.selected_tile.release()
                
            if event.type == pg.MOUSEBUTTONDOWN:
                    
                if event.button == 3:
                    self.selected_tile = self.grid.get_clicked_tile(x, y)
                    self.grid.flag(self.selected_tile)
            
        # Actions will take place upon release of the mouse button
        if event.type == pg.MOUSEBUTTONUP:
            if self.chording:
                self.grid.chord_reveal(self.selected_tile)
                self.chording = False

            # Left click
            elif event.button == 1 and self.selected_tile is not None:
                self.grid.reveal_tile(self.selected_tile)
        
    def update(self, dt):
        self.sidebar.display(dt)
        self.grid.display()

    def reset(self):
        self.grid.reset()
        self.sidebar.reset()
        self.has_saved_stats = False

    def run(self):
        dt = self.clock.tick(self.fps)
        self.update(dt)
        
        while self.running:
            dt = self.clock.tick(self.fps)
            self.event_loop()
            self.update(dt)
            pg.display.update()

        pg.quit()

    def quit(self):
        self.running = False

class SideBar:
    def __init__(self, real_width, real_height, grid, theme):
        self.width = real_width
        self.height = real_height
        self.grid = grid
        
        self.theme = theme['theme']
        self.bg_color = theme['primary_color']
        self.secondary_color = theme['secondary_color']
        
        self.tile_length = self.grid.tile_width
        self.font = pg.font.SysFont(theme['font_name'], 30)

        # Positions the sidebar on the right of the main grid
        self.sidebar_surface = pg.Surface((self.width, self.height))        
        self.top_left = self.grid.width * self.tile_length

        self.sprite_mapping = self.load_sprites()
        self.face_is_pressed = False

        self.timer = 0

    @property
    def face_state(self):
        if self.face_is_pressed:
            return 'happy_active'
        if self.grid.has_won:
            return 'cool'
        if self.grid.has_lost:
            return 'dead'
        if self.grid.is_holding:
            return 'shock'
        return 'happy'

    @property
    def mines_left(self):
        return self.grid.mines - self.grid.flags_placed

    def load_sprites(self):
        print(self.theme)
        path = os.path.join(self.theme, 'faces')
        sprite_mapping = {}
        for file in os.listdir(path):
            filename, _ = os.path.splitext(file)
            img = pg.image.load(os.path.join(path, file))
            img = pg.transform.scale(img, (self.tile_length*2, self.tile_length*2))
            sprite_mapping[filename] = img
        return sprite_mapping
    
    def display(self, dt):
        screen.blit(self.sidebar_surface, (self.top_left, 0))
        self.sidebar_surface.fill(pg.Color(self.bg_color))

        # Border dividing the grid and the sidebar
        pg.draw.line(self.sidebar_surface, pg.Color(self.secondary_color), (0, 0), (0, self.height), width=5)

        # Draw the face
        face = pg.Surface((self.tile_length*2, self.tile_length*2))
        face.blit(self.sprite_mapping[self.face_state], (0, 0))
        self.sidebar_surface.blit(face, ((self.width//2) - (self.tile_length), self.tile_length))

        # Display info
        self.display_text("Time Left:", 9)
        self.display_text(self.format_milliseconds(self.timer), 10)
        self.display_text("Mines Left:", 12)
        self.display_text(str(self.mines_left), 13)
        self.timer_tick(dt)
        
    def display_text(self, txt, tile_y_pos, absolute_y_pos=None):
        """
        This will display text at a given y position in the sidebar and will center it to look nice.
        By default, it will take in a tile_y_pos so it looks nice and aligned with the grid.
        """
        
        if absolute_y_pos is not None:
            y_pos = absolute_y_pos
        else:
            y_pos = tile_y_pos * self.tile_length
            
        width, height = self.font.size(txt)
        x_pos = (self.width//2) - (width//2)
        y_pos = y_pos - (height // 2)
        text = self.font.render(txt, False, self.secondary_color)
        self.sidebar_surface.blit(text, (x_pos, y_pos))
        
    def format_milliseconds(self, milliseconds):
        seconds, milliseconds = divmod(milliseconds, 1000)
        minutes, seconds = divmod(seconds, 60)
        return f"{minutes:02d}:{seconds:02d}:{milliseconds:03d}"
        
    def reset(self):
        self.timer = 0

    def timer_tick(self, dt):
        if not self.grid.is_game_over and not self.grid.is_first_click:
            self.timer += dt
        
    def is_mouse_over_face(self, mouse_pos):
        mouse_x, mouse_y = mouse_pos
        
        mouse_x -= self.grid.width * self.tile_length
        mouse_y -= self.tile_length
        boundary_x = [(self.width//2) - (self.tile_length), (self.width//2) + (self.tile_length)]
        return boundary_x[0] < mouse_x < boundary_x[1] and 0 < mouse_y < self.tile_length*2

    def is_mouse_over_sidebar(self, mouse_pos):
        mouse_x, mouse_y = mouse_pos
        return mouse_x > self.grid.width*self.tile_length

    def press_face(self):
        self.face_is_pressed = True

    def release_face(self):
        self.face_is_pressed = False

class Grid:
    
    def __init__(self, width, height, tile_size, mines, theme):
        """
        Width and height are the number of tiles for the width and height.
        """
        
        self.width = width
        self.height = height
        
        self.theme = theme['theme']
        self.is_checkered = theme['is_checkered']
        self.has_number_sprites = theme['has_number_sprites']
        self.font = pg.font.SysFont(theme['font_name'], 30)
        self.number_color_map = theme['number_color_map']
        
        self.tile_size = tile_size
        self.tile_width = tile_size[0]
        self.tile_height = tile_size[1]
        
        self.mines = mines
        self.grid = self.initiate_grid()
        self.sprite_mapping = self.load_sprites()
        self.flags_placed = 0

        self.is_first_click = True

        # Different states of a game
        self.is_holding = False
        self.has_won = False
        self.has_lost = False

        self.sfx_mapping = self.load_sounds()

        if self.theme == 'vine':
            self.bg_image = self.get_bg_image('vine/eyebrow.png')
        else:
            self.bg_image = None
            

    def __str__(self):
        return str(self.grid)

    def __repr__(self):
        return f"Grid({self.grid})"

    @property
    def is_game_over(self):
        return self.has_won or self.has_lost

    def play_sfx(self, sfx):
        self.sfx_mapping[sfx].play()

    def reset(self):
        self.is_holding = False
        self.has_won = False
        self.has_lost = False
        self.is_first_click = True
        self.grid = self.initiate_grid()
        self.flags_placed = 0
        
    def is_mouse_over_grid(self, mouse_pos):
        mouse_x = mouse_pos[0]
        return mouse_x < self.width*self.tile_width

    def get_clicked_tile(self, mouse_x, mouse_y):
        tile_x = mouse_x // self.tile_width
        tile_y = mouse_y // self.tile_height
        tile = self.grid[tile_y][tile_x]
        return tile

    def get_bg_image(self, path):
        img = pg.image.load(path)
        width = self.tile_width * self.width
        height = self.tile_height * self.height
        img = pg.transform.scale(img, (width, height))
        return img
        
    def load_sprites(self):
        path = os.path.join(self.theme, 'tiles')
        sprite_mapping = {}
        for file in os.listdir(path):
            filename, _ = os.path.splitext(file)
            img = pg.image.load(os.path.join(path, file))
            img = pg.transform.scale(img, self.tile_size)
            sprite_mapping[filename] = img
        return sprite_mapping

    def load_sounds(self):
        path = os.path.join(self.theme, 'sfx')
        sfx_mapping = {}
        for file in os.listdir(path):
            filename, _ = os.path.splitext(file)
            sfx = pg.mixer.Sound(os.path.join(path, file))
            sfx_mapping[filename] = sfx
        return sfx_mapping

    def initiate_grid(self):
        """Start the grid with placeholder empty tiles, since the mines get generated after first click."""
        
        return [[Tile(self.tile_size, (x, y), 0) for x in range(self.width)] for y in range(self.height)]
    
    def get_grid(self, clicked):
        """
        Mines will be represented as the string 'mine'
        Flags will be represented as the string 'flag'
        All other values will be represented as integers from 0-8
        """

        # Keep wherever people place flags before the first click
        flag_coords = self.get_flag_placement()
        
        # Randomly decide where the mines will go
        free_tiles = [(x, y) for y in range(self.height) for x in range(self.width)]

        # So that a mine never generates on the first click and on neighboring squares
        x, y = clicked
        for y_seek in range(-1, 2):
            for x_seek in range(-1, 2):
                nx, ny = x+x_seek, y+y_seek
                if nx >= 0 and nx < self.width and ny >= 0 and ny < self.height:
                    free_tiles.remove((nx, ny))
            
        random.shuffle(free_tiles)
        mine_coords = free_tiles[:self.mines]
        
        for y in range(self.height):
            for x in range(self.width):
                if (x, y) in mine_coords:
                    state = 'mine'
                else:
                    state = 0
                is_flagged = (x, y) in flag_coords
                self.grid[y][x] = Tile(self.tile_size, (x, y), state, is_flagged=is_flagged)

        self.grid = self.enumerate_tiles(self.grid)
        return self.grid

    def get_flag_placement(self):
        coords = []
        for y in range(self.height):
            for x in range(self.width):
                if self.grid[y][x].is_flagged:
                    coords.append((x, y))
        return coords
                    
    def enumerate_tiles(self, grid):
        width, height = len(grid[0]), len(grid)
        
        for y in range(height):
            for x in range(width):
                if grid[y][x].state != 'mine':
                    # Count how many mines surround the tile
                    count = 0
                    for neighbor in self.get_tile_neighbors(grid[y][x]):
                        if neighbor.state == 'mine':
                            count += 1
                    grid[y][x].state = count
        return grid
        
    def get_tile_neighbors(self, tile):
        """Helper to function to get an iterable of a tile's neigbours."""
        
        x, y = tile.index
        for y_seek in range(-1, 2):
            for x_seek in range(-1, 2):
                nx, ny = x+x_seek, y+y_seek
                
                if nx >= 0 and nx < self.width and ny >= 0 and ny < self.height:
                    neighbor = self.grid[ny][nx]
                    yield neighbor

    def check_win(self):
        """You win if the only tiles left are bombs."""

        mines = 0
        for y in range(self.height):
            for x in range(self.width):
                if not self.grid[y][x].is_revealed:
                    mines += 1
        return mines == self.mines

    def chord(self, tile):
        for neighbor in self.get_tile_neighbors(tile):
            if not neighbor.is_revealed:
                neighbor.hold_down()

    def unchord(self, tile):
        for neighbor in self.get_tile_neighbors(tile):
            if not neighbor.is_revealed:
                neighbor.release()

    def chord_reveal(self, tile):
        flags = 0
        for neighbor in self.get_tile_neighbors(tile):
            if neighbor.is_flagged:
                flags += 1

        if flags == tile.state and flags > 0:
            for neighbor in self.get_tile_neighbors(tile):
                if not neighbor.is_revealed:
                    neighbor.release()
                    self.reveal_tile(neighbor)
            STATS["Times Chorded"] += 1
            
        else:
            self.unchord(tile)
            
    def flag(self, tile):
        x, y = tile.index

        if not tile.is_revealed:
            if tile.is_flagged:
                self.flags_placed -= 1
            else:
                self.flags_placed += 1
            tile.flag()
            self.play_sfx('flag')

    def reveal_tile(self, tile):
        x, y = tile.index

        # Do not allow tiles to be revealed to take place if any of these conditions are met
        if tile.is_flagged or tile.is_revealed:
            return

        # Generate grid after the first click
        if self.is_first_click:
            self.grid = self.get_grid(clicked=tile.index)
            
            # Update clicked tile value from 0
            tile = self.grid[y][x]
            self.is_first_click = False
            self.play_sfx('large_reveal')

        tile.reveal()
        
        # Game over
        if tile.state == 'mine':
            for y in range(self.height):
                for x in range(self.width):
                    if self.grid[y][x].state == 'mine':
                        self.grid[y][x].reveal()
                        
                    # Incorrect flag
                    elif self.grid[y][x].is_flagged:
                        self.grid[y][x].state = 'not_mine'
                    
            tile.state = 'active_mine'
            self.has_lost = True
            STATS["Games Lost"] += 1
            self.play_sfx('boom')

        # Winning the game
        if self.check_win():
            self.has_won = True
            STATS["Games Won"] += 1

        # Uncover other tiles using depth first search
        if tile.state == 0:
            self.play_sfx('large_reveal')
        
            to_visit = list(self.get_tile_neighbors(tile))
            while len(to_visit) > 0:
                visiting_tile = to_visit.pop()

                if visiting_tile.state == 0 and not visiting_tile.is_revealed:
                    to_visit.extend(list(self.get_tile_neighbors(visiting_tile)))
                    
                if visiting_tile.state != 'mine':
                    visiting_tile.reveal()             

    def display(self):
        if self.bg_image is not None:
            screen.blit(self.bg_image, (0,0))
        
        for y in range(self.height):
            for x in range(self.width):
                x_pos = x * self.tile_width
                y_pos = y * self.tile_height
                tile = self.grid[y][x]
                
                if self.is_checkered:
                    # Light tile
                    if (x+y) % 2 == 0:
                        sprite = self.sprite_mapping['hidden_light']
                    # Dark tile
                    else:
                        sprite = self.sprite_mapping['hidden_dark']

                if tile.state == 'not_mine':
                    sprite = self.sprite_mapping['not_mine']
                    
                elif tile.is_flagged:
                    sprite = self.sprite_mapping['flag']

                elif tile.is_revealed:
                    if self.is_checkered and tile.state != 'mine':
                        if (x+y) % 2 == 0:
                            state = '0_light'
                        else:
                            state = '0_dark'
                        sprite = self.sprite_mapping[state]
                        screen.blit(sprite, (x_pos, y_pos))

                    state = str(tile.state)

                    if not self.is_checkered or state != '0':
                        if self.has_number_sprites:
                            sprite = self.sprite_mapping[state]

                        else:
                            # Render using generated fonts
                            if state.isnumeric():
                                color = self.number_color_map[state]
                                width, height = self.font.size(state)
                                x_pos += (self.tile_width//2) - (width//2)
                                y_pos += (self.tile_height//2) - (height//2)
                                sprite = self.font.render(state, False, color)
                            else:
                                sprite = self.sprite_mapping[state]
                        
                elif tile.is_held_down:
                    if self.is_checkered:
                        sprite = sprite.copy()
                        brighten = 10
                        sprite.fill((brighten, brighten, brighten), special_flags=pg.BLEND_RGB_ADD)
                    else:
                        sprite = self.sprite_mapping['0']
                        
                elif not self.is_checkered:
                    sprite = self.sprite_mapping['hidden']

                else:
                    # If it reaches here, that means the tile is a hidden checkered tile (which was already diplayed)
                    already_displayed = True
                    
                if self.bg_image is not None and tile.is_revealed and not tile.is_flagged:
                    sprite.set_alpha(160)

                screen.blit(sprite, (x_pos, y_pos))
                
class Tile:
    def __init__(self, size, index, state, is_revealed=False, is_flagged=False, is_held_down=False):
        width, height = size
        self.width = width
        self.height = height
        self.index = index # The position of the tile in the grid matrix
        self.state = state
        self.is_revealed = is_revealed
        self.is_flagged = is_flagged
        self.is_held_down = is_held_down
        
    def __str__(self):
        return str(self.state)

    def __repr__(self):
        return f"Tile({self.state})"

    def reveal(self):
        self.is_revealed = True
        stat_title = f"{self.state}s Revealed"

        if stat_title in STATS:
            STATS[stat_title] += 1
            STATS["Tiles Revealed"] += 1
        

    def flag(self):
        if not self.is_revealed:
            self.is_flagged = not self.is_flagged

            if self.is_flagged:
                STATS["Flags Placed"] += 1

    def hold_down(self):
        self.is_held_down = True

    def release(self):
        self.is_held_down = False


def main():
    tile_length = 30

    # These numbers are given in terms of how many tiles can fit across each length
    grid_width = 20
    grid_height = 20
    sidebar_width = 5
    sidebar_height = grid_height

    THEMES = {
        "discord": {
            'theme': 'discord',
            'primary_color': "#37393e",
            'secondary_color': pg.Color('white'),
            'is_checkered': True,
            'has_number_sprites': False,
            'font_name':  "Helvetica Neue UltraLight",

            'number_color_map': {
                '1': '#5866ef',
                '2': '#3da560',
                '3': '#ec4145',
                '4': '#4f5d7e',
                '5': '#9b84ec',
                '6': '#49ddc1',
                '7': '#f37b68',
                '8': '#f9a62b'
            }
        },

        "vine": {
            'theme': 'vine',
            'primary_color': "#37393e",
            'secondary_color': pg.Color('white'),
            'is_checkered': False,
            'has_number_sprites': True,
            'font_name':  "Helvetica Neue UltraLight",
            'number_color_map': None
        },

        "classic": {
            'theme': 'classic',
            'primary_color': "#37393e",
            'secondary_color': pg.Color('white'),
            'is_checkered': False,
            'has_number_sprites': True,
            'font_name':  "Helvetica Neue UltraLight",
            'number_color_map': None
        }
    }
            
    theme = "classic"
        
    grid = Grid(
        grid_width,
        grid_height,
        (tile_length, tile_length),
        mines=70,
        theme=THEMES[theme],
    )

    sidebar = SideBar(
        sidebar_width * tile_length,
        sidebar_height * tile_length,
        grid,
        THEMES[theme],
    )

    global screen
    screen_width = (grid.width * tile_length) + (sidebar_width * tile_length)
    screen_height = grid.height * tile_length
    screen = pg.display.set_mode((screen_width, screen_height))

    # Initiate the stats
    global STATS
    STATS = get_stats()
    
    
        
    app = Application(grid, sidebar)
    app.run()

if __name__ == '__main__':
    main()
