import pygame
import sys
import random
from collections import deque

# Initialize Pygame
pygame.init()
pygame.mixer.init()
pygame.mixer.music.load("02. Start Music.MP3")
pygame.mixer.music.set_volume(0.5)
pygame.mixer.music.play(-1)
death_sound=pygame.mixer.Sound("15. Fail.MP3")

# Colors
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
YELLOW = (255, 255, 0)
BLUE = (0, 0, 255)
RED = (255, 0, 0)

# Maze settings
MAZE_WIDTH = 28
MAZE_HEIGHT = 31

# Function to calculate the size of each cell in the maze to fit the screen
def calculate_sizes(screen_width, screen_height):
    cell_width = screen_width // MAZE_WIDTH
    cell_height = screen_height // MAZE_HEIGHT
    return min(cell_width, cell_height)

def get_center(cell_size, maze_width, maze_height):
    width, height = pygame.display.get_window_size()
    offset_x = (width - (cell_size * maze_width)) // 2
    offset_y = (height - (cell_size * maze_height)) // 2
    return offset_x, offset_y

# Font for displaying the score and lives
font = pygame.font.Font(None, 50)

# Wall Class
class Wall(pygame.sprite.Sprite):
    def __init__(self, x, y, width, height):
        super().__init__()
        self.image = pygame.Surface([width, height])
        self.image.fill(BLUE)
        self.rect = self.image.get_rect()
        self.rect.x = x
        self.rect.y = y

# Pellet Class
class Pellet(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        self.image = pygame.Surface([PELLET_SIZE, PELLET_SIZE])
        self.image.fill(WHITE)
        self.rect = self.image.get_rect()
        self.rect.x = x
        self.rect.y = y

# Pac-Man Class
class PacMan(pygame.sprite.Sprite):
    def __init__(self):
        super().__init__()
        self.image = pygame.Surface([PACMAN_SIZE, PACMAN_SIZE])
        self.image.fill(YELLOW)
        self.rect = self.image.get_rect()
        self.rect.x = SCREEN_WIDTH // 2 - CELL_SIZE // 2
        self.rect.y = SCREEN_HEIGHT // 2 + CELL_SIZE // 2 + CELL_SIZE
        self.change_x = 0
        self.change_y = 0
        self.next_direction = None

    def try_change_direction(self, direction, walls):
        if direction == 'LEFT':
            dx, dy = -PACMAN_SPEED, 0
        elif direction == 'RIGHT':
            dx, dy = PACMAN_SPEED, 0
        elif direction == 'UP':
            dx, dy = 0, -PACMAN_SPEED
        elif direction == 'DOWN':
            dx, dy = 0, PACMAN_SPEED
        else:
            return
        test_rect = self.rect.copy()
        test_rect.x += dx
        test_rect.y += dy
        if not pygame.sprite.spritecollideany(Wall(test_rect.x, test_rect.y, PACMAN_SIZE, PACMAN_SIZE), walls):
            self.change_x, self.change_y = dx, dy

    def update(self, walls):
        if self.next_direction:
            self.try_change_direction(self.next_direction, walls)
        self.rect.x += self.change_x
        self.rect.y += self.change_y

        block_hit_list = pygame.sprite.spritecollide(self, walls, False)
        for block in block_hit_list:
            if self.change_x > 0:
                self.rect.right = block.rect.left
            elif self.change_x < 0:
                self.rect.left = block.rect.right
            elif self.change_y > 0:
                self.rect.bottom = block.rect.top
            elif self.change_y < 0:
                self.rect.top = block.rect.bottom

# Ghost Class
class Ghost(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        self.image = pygame.Surface([GHOST_SIZE, GHOST_SIZE])
        self.image.fill(RED)
        self.rect = self.image.get_rect()
        self.rect.center = (x, y)
        self.speed = GHOST_SPEED
        self.path = []
        self.target_pos = None
        self.repath_timer = 0

    def get_grid_pos(self, center=True):
        if center:
            return (self.rect.centerx // CELL_SIZE, self.rect.centery // CELL_SIZE)
        return (self.rect.x // CELL_SIZE, self.rect.y // CELL_SIZE)

    def bfs(self, start, goal, walls_set):
        if start == goal:
            return []

        queue = deque([start])
        came_from = {start: None}
        max_iterations = 500  # prevent infinite loops

        iterations = 0
        while queue and iterations < max_iterations:
            current = queue.popleft()
            if current == goal:
                break

            x, y = current
            for dx, dy in [(-1,0), (1,0), (0,-1), (0,1)]:
                neighbor = (x + dx, y + dy)
                if neighbor in walls_set or neighbor in came_from:
                    continue
                queue.append(neighbor)
                came_from[neighbor] = current

            iterations += 1

        # If goal unreachable or loop too long, return empty path
        if goal not in came_from:
            return []

        # Reconstruct path
        path = []
        current = goal
        while current and current in came_from:
            path.append(current)
            current = came_from[current]
        path.reverse()
        return path

    def update(self, walls, pacman):
        wall_grid = set((w.rect.x // CELL_SIZE, w.rect.y // CELL_SIZE) for w in walls)

        # Validate ghost & pacman positions in bounds
        ghost_grid = self.get_grid_pos()
        pacman_grid = (pacman.rect.centerx // CELL_SIZE, pacman.rect.centery // CELL_SIZE)

        if (ghost_grid in wall_grid or pacman_grid in wall_grid):
            return  # don't pathfind from/to wall tile

        # Recalculate path every few frames
        if self.repath_timer <= 0 or not self.path or self.target_pos is None:
            self.path = self.bfs(ghost_grid, pacman_grid, wall_grid)
            self.repath_timer = 15  # lower = more responsive

            if len(self.path) > 1:
                next_tile = self.path[1]
                self.target_pos = (next_tile[0] * CELL_SIZE + CELL_SIZE // 2,
                                   next_tile[1] * CELL_SIZE + CELL_SIZE // 2)
            else:
                self.target_pos = None
        else:
            self.repath_timer -= 1

        # Smooth movement toward target position
        if self.target_pos:
            tx, ty = self.target_pos
            dx = tx - self.rect.centerx
            dy = ty - self.rect.centery
            dist = max((dx**2 + dy**2) ** 0.5, 0.01)  # avoid divide-by-zero

            if dist < self.speed:
                self.rect.center = self.target_pos
                self.target_pos = None
            else:
                self.rect.x += int(self.speed * dx / dist)
                self.rect.y += int(self.speed * dy / dist)
# class Ghost(pygame.sprite.Sprite):
#
#     def __init__(self, x, y):
#         super().__init__()
#         self.image = pygame.Surface([GHOST_SIZE, GHOST_SIZE])
#         self.image.fill(RED)
#         self.rect = self.image.get_rect()
#         self.rect.x = x
#         self.rect.y = y
#         self.initial_move_timer = 60
#         self.direction = random.choice(['UP', 'DOWN', 'LEFT', 'RIGHT'])
#         self.decision_cooldown = 0  # frames before changing direction again
#
#     def move(self, direction):
#         if direction == 'UP':
#             self.rect.y -= GHOST_SPEED
#         elif direction == 'DOWN':
#             self.rect.y += GHOST_SPEED
#         elif direction == 'LEFT':
#             self.rect.x -= GHOST_SPEED
#         elif direction == 'RIGHT':
#             self.rect.x += GHOST_SPEED
#
#     def update(self, walls, pacman):
#         if self.initial_move_timer > 0:
#             self.rect.y -= GHOST_SPEED
#             self.initial_move_timer -= 1
#             return
#
#         if self.decision_cooldown > 0:
#             self.decision_cooldown -= 1
#
#         # Store current position before move
#         old_pos = self.rect.topleft
#         self.move(self.direction)
#
#         # Check for collision
#         if pygame.sprite.spritecollideany(self, walls):
#             self.rect.topleft = old_pos  # revert movement
#
#             if self.decision_cooldown == 0:
#                 # Try all directions in random order
#                 directions = ['UP', 'DOWN', 'LEFT', 'RIGHT']
#                 random.shuffle(directions)
#
#                 for new_dir in directions:
#                     test_rect = self.rect.copy()
#                     if new_dir == 'UP':
#                         test_rect.y -= GHOST_SPEED
#                     elif new_dir == 'DOWN':
#                         test_rect.y += GHOST_SPEED
#                     elif new_dir == 'LEFT':
#                         test_rect.x -= GHOST_SPEED
#                     elif new_dir == 'RIGHT':
#                         test_rect.x += GHOST_SPEED
#
#                     temp_sprite = pygame.sprite.Sprite()
#                     temp_sprite.rect = test_rect
#
#                     if not pygame.sprite.spritecollideany(temp_sprite, walls):
#                         self.direction = new_dir
#                         self.decision_cooldown = 1  # wait before next decision
#                         break
# Maze layout
mazes = [
    [
        "############################",
        "#............##............#",
        "#.####.#####.##.#####.####.#",
        "#o####.#####.##.#####.####o#",
        "#.####.#####.##.#####.####.#",
        "#..........................#",
        "#.####.##.########.##.####.#",
        "#.####.##.########.##.####.#",
        "#......##....##....##......#",
        "######.##### ## #####.######",
        "######.##### ## #####.######",
        "######.##          ##.######",
        "######.## ###--### ##.######",
        "######.## #      # ##.######",
        "       .  #      #   .     ",
        "######.## #      # ##.######",
        "######.## ######## ##.######",
        "######.##          ##.######",
        "######.## ######## ##.######",
        "######.## ######## ##.######",
        "#............##............#",
        "#.####.#####.##.#####.####.#",
        "#.####.#####.##.#####.####.#",
        "#o..##.......  .......##..o#",
        "###.##.##.########.##.##.###",
        "###.##.##.########.##.##.###",
        "#......##....##....##......#",
        "#.##########.##.##########.#",
        "#.##########.##.##########.#",
        "#..........................#",
        "############################"]
]

# Create maze
def create_maze(cell_size, offset_x, offset_y, maze_layout):
    walls = pygame.sprite.Group()
    pellets = pygame.sprite.Group()
    for y, row in enumerate(maze_layout):
        for x, char in enumerate(row):
            if char == "#":
                wall = Wall(x * cell_size + offset_x, y * cell_size + offset_y, cell_size - PACMAN_BUFFER * 2, cell_size - PACMAN_BUFFER * 2)
                walls.add(wall)
            elif char == ".":
                pellet = Pellet(x * cell_size + cell_size // 4 + offset_x, y * cell_size + cell_size // 4 + offset_y)
                pellets.add(pellet)
    return walls, pellets

# Main game
def main():
    global CELL_SIZE, PACMAN_SIZE, PACMAN_SPEED, GHOST_SIZE, GHOST_SPEED, PELLET_SIZE, SCREEN_WIDTH, SCREEN_HEIGHT, PACMAN_BUFFER

    screen = pygame.display.set_mode((0, 0), pygame.RESIZABLE)
    pygame.display.set_caption("Pac-Man by Azaan Raza")

    SCREEN_WIDTH, SCREEN_HEIGHT = pygame.display.get_window_size()
    CELL_SIZE = calculate_sizes(SCREEN_WIDTH, SCREEN_HEIGHT)
    PACMAN_SIZE = CELL_SIZE // 1.2
    PACMAN_SPEED = CELL_SIZE // 5
    GHOST_SIZE = CELL_SIZE // 1.2
    GHOST_SPEED = CELL_SIZE // 7
    PELLET_SIZE = CELL_SIZE // 4
    PACMAN_BUFFER = 0.5

    OFFSET_X, OFFSET_Y = get_center(CELL_SIZE, MAZE_WIDTH, MAZE_HEIGHT)

    maze_layout = random.choice(mazes)
    walls, pellets = create_maze(CELL_SIZE, OFFSET_X, OFFSET_Y, maze_layout)

    all_sprites = pygame.sprite.Group()
    all_sprites.add(walls, pellets)

    pacman = PacMan()
    ghost = Ghost(SCREEN_WIDTH // 2 - 3 * CELL_SIZE // 2, SCREEN_HEIGHT // 2 - 3 * CELL_SIZE)
    ghosts = pygame.sprite.Group(ghost)

    all_sprites.add(pacman, ghost)

    score, lives, paused = 0, 1, False
    fullscreen, running = False, True
    clock = pygame.time.Clock()

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_LEFT:
                    pacman.next_direction = 'LEFT'
                elif event.key == pygame.K_RIGHT:
                    pacman.next_direction = 'RIGHT'
                elif event.key == pygame.K_UP:
                    pacman.next_direction = 'UP'
                elif event.key == pygame.K_DOWN:
                    pacman.next_direction = 'DOWN'
                elif event.key == pygame.K_f:
                    fullscreen = not fullscreen
                    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT),
                        pygame.FULLSCREEN if fullscreen else pygame.RESIZABLE)
                elif event.key == pygame.K_m:
                    pygame.display.iconify()
                elif event.key == pygame.K_p:
                    paused = not paused

        if not paused:
            pacman.update(walls)
            for pellet in pygame.sprite.spritecollide(pacman, pellets, True):
                score += 1
            ghost.update(walls, pacman)
            if pygame.sprite.spritecollideany(pacman, ghosts):
                lives -= 1
                death_sound.play()
                pygame.mixer.music.stop()
                pygame.time.delay(int(death_sound.get_length() * 500))
                if lives > 0:
                    pacman.rect.x = SCREEN_WIDTH // 2 - CELL_SIZE // 2
                    pacman.rect.y = SCREEN_HEIGHT // 2 + CELL_SIZE // 2
                    ghost.rect.x = SCREEN_WIDTH // 2 - 3 * CELL_SIZE // 2
                    ghost.rect.y = SCREEN_HEIGHT // 2 - 3 * CELL_SIZE
                else:
                    print("Pac-Man was caught by the ghost! Game Over!")
                    running = False
            if len(pellets) == 0:
                print("Congratulations! You have eaten all the pellets!")
                running = False

        screen.fill(BLACK)
        all_sprites.draw(screen)

        screen.blit(font.render(f"Score: {score}", True, WHITE), [10, 10])
        screen.blit(font.render(f"Lives: {lives}", True, WHITE), [10, 40])
        if paused:
            pause_text = font.render("Paused", True, WHITE)
            screen.blit(pause_text,
                        [SCREEN_WIDTH // 2 - pause_text.get_width() // 2,
                                     SCREEN_HEIGHT // 2 - pause_text.get_height() // 2])

        pygame.display.flip()
        clock.tick(30)


    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()
