# ---------------------------------------------------------------------------------
# FLAPPY.PY with NEAT Evolution integrated
# ---------------------------------------------------------------------------------
# NOTE: This single file contains the original Flappy Bird game logic
#       plus a NEAT-based AI approach that evolves birds to play the game.
#       You can run:
#           python flappy.py
#       to play manually (the normal game),
#       or:
#           python flappy.py ai
#       to watch the NEAT AI train and evolve birds over generations.
# ---------------------------------------------------------------------------------

# [1) Imports and Basic Setup]
import pygame     # <-- for rendering, input, etc.
import sys        # <-- for sys.exit()
import random     # <-- for randomizing pipes and slides
import math       # <-- optional, for advanced calculations
import os         # <-- for file paths (used in NEAT config loading)
import neat       # <-- NEAT-Python library
import time       # <-- to measure how long each generation or game loop runs

# [2) Window Dimensions and Constants]
WINDOW_WIDTH = 800         # <-- width of the game window
WINDOW_HEIGHT = 600        # <-- height of the game window

BIRD_X = 100               # <-- initial x-position of the bird
BIRD_WIDTH = 40            # <-- width of the bird image
BIRD_HEIGHT = 30           # <-- height of the bird image
FLAP_STRENGTH = -8         # <-- upward velocity for flap
GRAVITY = 0.5              # <-- gravitational acceleration
BIRD_COLLISION_RATIO = 1   # <-- collision box scale factor

PIPE_WIDTH = 180           # <-- width of each pipe image
PIPE_GAP = 150             # <-- static vertical gap size
MIN_PIPE_HEIGHT = 50       # <-- minimum top/bottom section height
PIPE_SPEED_BASE = 3        # <-- base speed of pipe movement

MIN_PIPE_SPACING = 200     # <-- minimum horizontal distance between consecutive pipes
MAX_PIPE_SPACING = 400     # <-- maximum horizontal distance between consecutive pipes

HITBOX_SHRINK_FACTOR = 0.2 # <-- shrinks pipe collision boxes horizontally
BG_SCROLL_SPEED_BASE = 2   # <-- base speed for the scrolling background

COLOR_SKY = (135, 206, 235)  # <-- color for sky background
WHITE    = (255, 255, 255)   # <-- color white for text
RED      = (200, 0, 0)       # <-- darker red for inactive button
RED_HOVER= (255, 0, 0)       # <-- brighter red for hover effect

STATE_START = 0
STATE_PLAYING = 1
STATE_GAME_OVER = 2

pygame.init()   # <-- initialize pygame
screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))  # <-- set screen mode
pygame.display.set_caption("Flappy Bird - NEAT Evolution or Manual Play")  # <-- set title
clock = pygame.time.Clock()  # <-- game clock
font = pygame.font.Font(None, 36)  # <-- default font for text rendering

# [3) Utility: draw_text]
def draw_text(surface, text, x, y, color=WHITE, center=False):
    # <-- Renders the given 'text' onto 'surface' at (x, y).
    img = font.render(text, True, color)
    rect = img.get_rect()
    if center:
        rect.center = (x, y)
    else:
        rect.topleft = (x, y)
    surface.blit(img, rect)

# [4) Utility: draw_button]
def draw_button(text, x, y, w, h, inactive_color, active_color, action=None):
    # <-- Draws a rectangular button with changing color on hover. On click, calls 'action'.
    mouse = pygame.mouse.get_pos()
    click = pygame.mouse.get_pressed()

    # Check hover
    if x + w > mouse[0] > x and y + h > mouse[1] > y:
        pygame.draw.rect(screen, active_color, (x, y, w, h))
        if click[0] == 1 and action:
            action()
    else:
        pygame.draw.rect(screen, inactive_color, (x, y, w, h))

    # Draw text
    text_surf = font.render(text, True, WHITE)
    text_rect = text_surf.get_rect(center=(x + w // 2, y + h // 2))
    screen.blit(text_surf, text_rect)

# [5) Create Slides with Non-Overlapping Clouds]
def create_slides(num_slides=20):
    # <-- Creates 'num_slides' background surfaces with scattered clouds.
    slides = []
    cloud_raw = pygame.image.load("cloud.png").convert_alpha()
    cloud_w = cloud_raw.get_width() // 3
    cloud_h = cloud_raw.get_height() // 3
    cloud_scaled = pygame.transform.scale(cloud_raw, (cloud_w, cloud_h))

    for _ in range(num_slides):
        surf = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT))
        surf.fill(COLOR_SKY)

        cloud_count = random.randint(2, 4)
        cloud_positions = []
        for _c in range(cloud_count):
            max_attempts = 100
            for _attempt in range(max_attempts):
                cx = random.randint(0, WINDOW_WIDTH - cloud_w)
                cy = random.randint(0, (WINDOW_HEIGHT // 3) - cloud_h)
                overlap = False
                for (ex, ey) in cloud_positions:
                    if abs(cx - ex) < cloud_w and abs(cy - ey) < cloud_h:
                        overlap = True
                        break
                if not overlap:
                    cloud_positions.append((cx, cy))
                    surf.blit(cloud_scaled, (cx, cy))
                    break
        slides.append(surf)
    return slides

SLIDES = create_slides()

# [6) RandomSlidesBackground Class]
class RandomSlidesBackground:
    # <-- Scrolls two side-by-side slides to the left at a given speed.
    def __init__(self, slides, scroll_speed=BG_SCROLL_SPEED_BASE):
        self.width = WINDOW_WIDTH
        self.height = WINDOW_HEIGHT
        self.scroll_speed = scroll_speed

        self.slides = slides or []
        if not self.slides:
            fallback = pygame.Surface((self.width, self.height))
            fallback.fill(COLOR_SKY)
            self.slides = [fallback]

        self.x1 = 0
        self.x2 = self.width
        self.slide1 = random.choice(self.slides)
        self.slide2 = random.choice(self.slides)

    def update(self, dynamic_speed=None):
        # <-- Move background slides left by 'dynamic_speed' or default 'scroll_speed'.
        s = dynamic_speed if dynamic_speed is not None else self.scroll_speed
        self.x1 -= s
        self.x2 -= s

        # Wrap-around logic
        if self.x1 + self.width < 0:
            self.x1 = self.x2 + self.width
            self.slide1 = random.choice(self.slides)
        if self.x2 + self.width < 0:
            self.x2 = self.x1 + self.width
            self.slide2 = random.choice(self.slides)

    def draw(self, surface):
        # <-- Blit the two slides at their current positions.
        surface.blit(self.slide1, (self.x1, 0))
        surface.blit(self.slide2, (self.x2, 0))

# [7) Bird Class]
class Bird:
    # <-- The main player or AI agent. Flies with flap, experiences gravity.
    def __init__(self):
        raw_img = pygame.image.load("flappyBird.png").convert_alpha()
        self.image = pygame.transform.scale(raw_img, (BIRD_WIDTH, BIRD_HEIGHT))

        self.collision_w = int(BIRD_WIDTH * BIRD_COLLISION_RATIO)
        self.collision_h = int(BIRD_HEIGHT * BIRD_COLLISION_RATIO)

        self.x = BIRD_X
        self.y = WINDOW_HEIGHT // 2
        self.vel_y = 0

    def reset(self):
        # <-- Resets the bird to default position and velocity.
        self.x = BIRD_X
        self.y = WINDOW_HEIGHT // 2
        self.vel_y = 0

    def flap(self):
        # <-- Applies a negative velocity to move up (flap).
        self.vel_y = FLAP_STRENGTH
        flap_sound.play()

    def update(self):
        # <-- Updates the bird's vertical velocity and position due to gravity.
        self.vel_y += GRAVITY
        self.y += self.vel_y

    def get_rect(self):
        # <-- Returns the collision rectangle (slightly reduced if ratio < 1).
        cx = self.x + (BIRD_WIDTH - self.collision_w) / 2
        cy = self.y + (BIRD_HEIGHT - self.collision_h) / 2
        return pygame.Rect(cx, cy, self.collision_w, self.collision_h)

    def draw(self, surface):
        # <-- Draws the bird and its collision box for debugging.
        surface.blit(self.image, (self.x, self.y))
        pygame.draw.rect(surface, (255, 0, 0), self.get_rect(), 2)

# [8) Pipe Class (STATIC GAP + Horizontal Spacing)]
class Pipe:
    # <-- Pipes appear at random vertical positions, move left, and get recycled.
    def __init__(self, x):
        self.x = x
        self.scored = False
        self.randomize_position()

        raw_pipe = pygame.image.load("flappyPipe.png").convert_alpha()
        self.pipe_bottom_img = pygame.transform.scale(raw_pipe, (PIPE_WIDTH, 600))
        self.pipe_top_img = pygame.transform.flip(self.pipe_bottom_img, False, True)

    def randomize_position(self):
        # <-- Decide the top position of the gap randomly within safe bounds.
        self.gap_top = random.randint(
            MIN_PIPE_HEIGHT,
            WINDOW_HEIGHT - PIPE_GAP - MIN_PIPE_HEIGHT
        )

    def update(self, pipe_speed, all_pipes):
        # <-- Move pipe left at given pipe_speed. If off-screen, reset to right side.
        self.x -= pipe_speed
        if self.x + PIPE_WIDTH < 0:
            self.reset_position(all_pipes)

    def reset_position(self, all_pipes):
        # <-- Find the rightmost pipe, then place this one further right by random spacing.
        rightmost_x = max(p.x for p in all_pipes if p is not self)
        dist = random.randint(MIN_PIPE_SPACING, MAX_PIPE_SPACING)
        self.x = rightmost_x + dist
        self.scored = False
        self.randomize_position()

    def get_rects(self):
        # <-- Return collision rects for the top and bottom pipes.
        new_width = PIPE_WIDTH * HITBOX_SHRINK_FACTOR
        offset_x = (PIPE_WIDTH - new_width) / 2

        top_rect = pygame.Rect(self.x + offset_x, 0, new_width, self.gap_top)
        bottom_rect = pygame.Rect(
            self.x + offset_x,
            self.gap_top + PIPE_GAP,
            new_width,
            WINDOW_HEIGHT - (self.gap_top + PIPE_GAP)
        )
        return top_rect, bottom_rect

    def draw(self, surface):
        # <-- Draw the pipe images and their collision boxes.
        top_h = self.pipe_top_img.get_height()
        top_y = self.gap_top - top_h
        surface.blit(self.pipe_top_img, (self.x, top_y))

        bottom_y = self.gap_top + PIPE_GAP
        surface.blit(self.pipe_bottom_img, (self.x, bottom_y))

        top_rect, bottom_rect = self.get_rects()
        pygame.draw.rect(surface, (0, 255, 0), top_rect, 2)
        pygame.draw.rect(surface, (0, 255, 0), bottom_rect, 2)

# [9) Sound Effects]
flap_sound = pygame.mixer.Sound("flap.wav")
collision_sound = pygame.mixer.Sound("collision.wav")
pass_sound = pygame.mixer.Sound("pass.wav")

# [10) Shared Game Variables (Manual Play)]
game_state = STATE_START
score = 0
high_score = 0

bg = RandomSlidesBackground(SLIDES)
NUM_PIPES = 5
pipes = []
for i in range(NUM_PIPES):
    init_x = WINDOW_WIDTH + i * MIN_PIPE_SPACING
    pipes.append(Pipe(x=init_x))
bird = Bird()

# [11) Helper Functions (Manual Play)]
def reset_game():
    global score
    score = 0
    bird.reset()
    rightmost_x = WINDOW_WIDTH
    for i, pipe in enumerate(pipes):
        dist = random.randint(MIN_PIPE_SPACING, MAX_PIPE_SPACING)
        pipe.x = rightmost_x + dist
        pipe.scored = False
        pipe.randomize_position()
        rightmost_x = pipe.x

def quit_game():
    pygame.quit()
    sys.exit()

def start_game():
    global game_state
    reset_game()
    game_state = STATE_PLAYING

def get_dynamic_speeds(current_score):
    # <-- Scale speeds with score. +1 speed for every 5 points.
    increment = current_score // 5
    bg_speed = BG_SCROLL_SPEED_BASE + increment
    pipe_speed = PIPE_SPEED_BASE + increment
    return bg_speed, pipe_speed

# ---------------------------------------------------------------------------------
# [12) NEAT-Based AI Training Integration]
# ---------------------------------------------------------------------------------
def eval_genomes(genomes, config):
    # <-- NEAT's required signature: (list_of_genomes, config_object)

    # [12.1) Setup the game environment for multiple AI birds]
    nets = []   # <-- stores each genome's neural network
    ge = []     # <-- stores each genome (to assign fitness)
    ai_birds = []  # <-- stores the Bird objects controlled by AI

    # [12.2) Create pipes and background specifically for this generation]
    local_bg = RandomSlidesBackground(SLIDES)
    local_pipes = []
    for i in range(NUM_PIPES):
        init_x = WINDOW_WIDTH + i * MIN_PIPE_SPACING
        local_pipes.append(Pipe(x=init_x))

    # [12.3) For each genome, we create a net and a Bird instance]
    for genome_id, genome in genomes:
        genome.fitness = 0
        net = neat.nn.FeedForwardNetwork.create(genome, config)
        nets.append(net)
        ai_bird = Bird()  # brand new bird
        ai_birds.append(ai_bird)
        ge.append(genome)

    # [12.4) Score tracking for NEAT run]
    frame_count = 0
    local_score = 0

    # [12.5) Game loop for the AI birds, runs until all birds die or we set a limit]
    run = True
    while run and len(ai_birds) > 0:
        clock.tick(30)   # <-- limit to 30fps so you can visualize the training
        frame_count += 1

        # Handle events (like quit)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

        # [12.6) Update background (speeds scale with local_score for difficulty)]
        current_bg_speed, current_pipe_speed = get_dynamic_speeds(local_score)
        local_bg.update(dynamic_speed=current_bg_speed)

        # [12.7) For each pipe, update position]
        for pipe in local_pipes:
            pipe.update(pipe_speed=current_pipe_speed, all_pipes=local_pipes)

        # [12.8) Next pipe calculations for AI input]
        for i, ai_bird in enumerate(ai_birds):
            # Identify the pipe that is just ahead of the bird
            nearest_pipe = None
            nearest_pipe_dist = float('inf')
            for p in local_pipes:
                dist_x = p.x - ai_bird.x
                if dist_x + PIPE_WIDTH > -50 and dist_x < nearest_pipe_dist:
                    nearest_pipe_dist = dist_x
                    nearest_pipe = p

            # [12.9) Get input features for the net (bird y, bird vel, pipe distance, pipe gap, etc.)]
            if nearest_pipe is not None:
                top_center = nearest_pipe.gap_top
                bottom_center = nearest_pipe.gap_top + PIPE_GAP

                output = nets[i].activate((
                    ai_bird.y,
                    ai_bird.vel_y,
                    nearest_pipe_dist,
                    top_center,
                    bottom_center
                ))
                # [12.10) Decide flap if output[0] > 0.5]
                if output[0] > 0.5:
                    ai_bird.flap()

        # [12.11) Update all AI birds in the environment]
        for i, ai_bird in enumerate(ai_birds):
            ai_bird.update()

        # [12.12) Check collisions & out-of-bounds]
        indices_to_remove = []
        for i, ai_bird in enumerate(ai_birds):
            # Out of bounds?
            if ai_bird.y < 0 or (ai_bird.y + BIRD_HEIGHT) >= WINDOW_HEIGHT:
                ge[i].fitness -= 1
                indices_to_remove.append(i)
                continue

            # Collisions with pipes
            bird_rect = ai_bird.get_rect()
            for pipe in local_pipes:
                top_rect, bottom_rect = pipe.get_rects()
                if bird_rect.colliderect(top_rect) or bird_rect.colliderect(bottom_rect):
                    ge[i].fitness -= 1
                    indices_to_remove.append(i)
                    break

        # [12.13) Check if any pipe is passed, reward fitness]
        for pipe in local_pipes:
            if (pipe.x + PIPE_WIDTH) < (BIRD_X + BIRD_WIDTH) and not pipe.scored:
                pipe.scored = True
                local_score += 1
                for j in range(len(ai_birds)):
                    ge[j].fitness += 5

        # [12.14) Remove dead birds in reverse order so we don't break indexing]
        for idx in reversed(indices_to_remove):
            ai_birds.pop(idx)
            nets.pop(idx)
            ge.pop(idx)

        # [12.15) (Optional) Hard limit to prevent infinite loops if you want]
        if frame_count > 10000:
            break

        # [12.16) Visualize the training run]
        screen.fill(COLOR_SKY)
        local_bg.draw(screen)
        for pipe in local_pipes:
            pipe.draw(screen)
        for ai_bird in ai_birds:
            ai_bird.draw(screen)

        draw_text(screen, f"Generation Score: {local_score}", 10, 10)
        draw_text(screen, f"Alive: {len(ai_birds)}", 10, 50)
        pygame.display.flip()

    # [12.17) End of generation. Fitness was updated above; NEAT moves on.]

def run_neat(config_file):
    # <-- Loads the config, creates a population, and runs the evolution with eval_genomes.
    config = neat.config.Config(
        neat.DefaultGenome,
        neat.DefaultReproduction,
        neat.DefaultSpeciesSet,
        neat.DefaultStagnation,
        config_file
    )

    population = neat.Population(config)

    # Add reporters for neat output
    population.add_reporter(neat.StdOutReporter(True))
    stats = neat.StatisticsReporter()
    population.add_reporter(stats)

    # Run up to 50 generations or until a fitness threshold is reached
    winner = population.run(eval_genomes, 50)

    print("Best genome found:", winner)

# ---------------------------------------------------------------------------------
# [14) Main Game Loop (Manual Play) or NEAT Evolution]
# ---------------------------------------------------------------------------------
def main_human_mode():
    global game_state, score, high_score

    while True:
        clock.tick(30)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                quit_game()
            if event.type == pygame.KEYDOWN and game_state == STATE_PLAYING:
                if event.key == pygame.K_SPACE:
                    bird.flap()

        if game_state == STATE_START:
            bg.update()
            bg.draw(screen)
            bird.draw(screen)

            draw_text(screen,
                      "Flappy Bird: Press Start or AI with 'python flappy.py ai'",
                      WINDOW_WIDTH // 2,
                      WINDOW_HEIGHT // 4,
                      center=True)
            draw_text(screen,
                      "Press SPACE in-game to Flap!",
                      WINDOW_WIDTH // 2,
                      WINDOW_HEIGHT // 4 + 60,
                      center=True)

            button_width = 150
            button_height = 50
            start_x = (WINDOW_WIDTH // 2) - (button_width + 20)
            start_y = int(WINDOW_HEIGHT * 0.6)
            quit_x = (WINDOW_WIDTH // 2) + 20
            quit_y = int(WINDOW_HEIGHT * 0.6)

            draw_button("Start", start_x, start_y, button_width, button_height, RED, RED_HOVER, action=start_game)
            draw_button("Quit", quit_x, quit_y, button_width, button_height, RED, RED_HOVER, action=quit_game)

            pygame.display.flip()

        elif game_state == STATE_PLAYING:
            current_bg_speed, current_pipe_speed = get_dynamic_speeds(score)
            bg.update(dynamic_speed=current_bg_speed)
            bird.update()

            for pipe in pipes:
                pipe.update(pipe_speed=current_pipe_speed, all_pipes=pipes)
                if (pipe.x + PIPE_WIDTH) < (bird.x + BIRD_WIDTH) and not pipe.scored:
                    score += 1
                    pipe.scored = True
                    pass_sound.play()

            # Check collisions or out-of-bounds
            if bird.y < 0 or (bird.y + BIRD_HEIGHT) > WINDOW_HEIGHT:
                if score > high_score:
                    high_score = score
                collision_sound.play()
                game_state = STATE_GAME_OVER

            bird_rect = bird.get_rect()
            for pipe in pipes:
                top_rect, bottom_rect = pipe.get_rects()
                if bird_rect.colliderect(top_rect) or bird_rect.colliderect(bottom_rect):
                    if score > high_score:
                        high_score = score
                    collision_sound.play()
                    game_state = STATE_GAME_OVER

            bg.draw(screen)
            for pipe in pipes:
                pipe.draw(screen)
            bird.draw(screen)

            draw_text(screen, f"Score: {score}", 10, 10)
            draw_text(screen, f"High: {high_score}", 10, 50)

            pygame.display.flip()

        else:
            # GAME_OVER
            bg.draw(screen)
            for pipe in pipes:
                pipe.draw(screen)
            bird.draw(screen)

            draw_text(screen, "GAME OVER", WINDOW_WIDTH // 2, WINDOW_HEIGHT // 4, center=True)
            draw_text(screen, f"Score: {score}", WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 - 20, center=True)
            draw_text(screen, f"High Score: {high_score}", WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 + 20, center=True)

            button_width = 150
            button_height = 50
            start_x = (WINDOW_WIDTH // 2) - (button_width + 20)
            start_y = int(WINDOW_HEIGHT * 0.75)
            quit_x = (WINDOW_WIDTH // 2) + 20
            quit_y = int(WINDOW_HEIGHT * 0.75)

            draw_button("Start", start_x, start_y, button_width, button_height, RED, RED_HOVER, action=start_game)
            draw_button("Quit", quit_x, quit_y, button_width, button_height, RED, RED_HOVER, action=quit_game)

            pygame.display.flip()

# ---------------------------------------------------------------------------------
# [15) Entry Point]
# ---------------------------------------------------------------------------------
if __name__ == "__main__":
    # If "ai" is passed as an argument, we run the NEAT training
    # Otherwise, we run the normal "manual play" mode
    if len(sys.argv) > 1 and sys.argv[1].lower() == "ai":
        local_dir = os.path.dirname(__file__)
        config_path = os.path.join(local_dir, "config-feedforward.txt")
        run_neat(config_path)
    else:
        main_human_mode()
