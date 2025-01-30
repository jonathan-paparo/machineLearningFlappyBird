import pygame     # <-- import pygame for rendering, input, etc.
import sys        # <-- import sys to allow for sys.exit()
import random     # <-- import random for randomizing pipe positions or clouds

# --------------------------
# Window dimensions
# --------------------------
WINDOW_WIDTH = 800         # <-- width of the game window
WINDOW_HEIGHT = 600        # <-- height of the game window

# --------------------------
# Bird
# --------------------------
BIRD_X = 100               # <-- initial X position of the bird
BIRD_WIDTH = 40            # <-- visual width of the bird image
BIRD_HEIGHT = 30           # <-- visual height of the bird image
FLAP_STRENGTH = -8         # <-- upward velocity for flap
GRAVITY = 0.5              # <-- gravitational acceleration
BIRD_COLLISION_RATIO = 1   # <-- collision box scale (full size)

# --------------------------
# Pipe (STATIC GAP SIZE)
# --------------------------
PIPE_WIDTH = 180           # <-- visual width of the pipe
PIPE_GAP = 150             # <-- fixed vertical gap size between top and bottom
MIN_PIPE_HEIGHT = 50       # <-- minimum top/bottom section height
PIPE_SPEED_BASE = 3        # <-- base speed of pipe movement

# --------------------------------------------------------
# Horizontal Spacing Between Pipes
# --------------------------------------------------------
# We introduce a MIN & MAX spacing to ensure there's always
# a "possible" distance between pipes—no extreme clustering or huge gaps.
MIN_PIPE_SPACING = 200     # <-- minimum distance from the rightmost pipe
MAX_PIPE_SPACING = 400     # <-- maximum distance from the rightmost pipe

# --------------------------------------------------------
# Shrink Factor for Pipe Hitboxes
# --------------------------------------------------------
# This shrinks the collision box horizontally, so the actual
# collision width is PIPE_WIDTH * HITBOX_SHRINK_FACTOR.
HITBOX_SHRINK_FACTOR = 0.2

# --------------------------------------------------------
# Scroll speeds
# --------------------------------------------------------
BG_SCROLL_SPEED_BASE = 2   # <-- base speed for the scrolling background

# --------------------------
# Colors
# --------------------------
COLOR_SKY = (135, 206, 235)  # <-- color for sky background
WHITE    = (255, 255, 255)   # <-- color white for text
RED      = (200, 0, 0)       # <-- darker red for inactive button
RED_HOVER= (255, 0, 0)       # <-- brighter red for hover effect

# --------------------------
# Game States
# --------------------------
STATE_START = 0
STATE_PLAYING = 1
STATE_GAME_OVER = 2

pygame.init()
screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
pygame.display.set_caption("Flappy Bird - Variable Pipe Spacing in a Range")
clock = pygame.time.Clock()

font = pygame.font.Font(None, 36)  # <-- font for text (size 36)

# --------------------------------------------------------
# 1) Utility: draw_text
# --------------------------------------------------------
def draw_text(surface, text, x, y, color=WHITE, center=False):
    """
    Draws text onto 'surface' at (x, y).
    If center=True, (x, y) is the center of the text rect.
    """
    img = font.render(text, True, color)
    rect = img.get_rect()
    if center:
        rect.center = (x, y)
    else:
        rect.topleft = (x, y)
    surface.blit(img, rect)

# --------------------------------------------------------
# 2) Utility: draw_button
# --------------------------------------------------------
def draw_button(text, x, y, w, h, inactive_color, active_color, action=None):
    """
    Draws a rectangular button with text. Changes color on mouse hover.
    If clicked, calls 'action' if provided.
    """
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

# --------------------------------------------------------
# 3) Create Slides with Non-Overlapping Clouds
# --------------------------------------------------------
def create_slides(num_slides=20):
    """
    Each slide is WINDOW_WIDTH x WINDOW_HEIGHT, filled with COLOR_SKY.
    Clouds placed in top one-third, ensuring no overlap.
    Using 20 slides for more variety.
    """
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

# --------------------------------------------------------
# 4) RandomSlidesBackground
# --------------------------------------------------------
class RandomSlidesBackground:
    """
    Scrolls two side-by-side slides left at a fixed or dynamic speed.
    """
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
        surface.blit(self.slide1, (self.x1, 0))
        surface.blit(self.slide2, (self.x2, 0))

# --------------------------------------------------------
# 5) Bird Class
# --------------------------------------------------------
class Bird:
    """
    Bird can flap with SPACE, applying upward velocity.
    Gravity pulls it down otherwise.
    """
    def __init__(self):
        raw_img = pygame.image.load("flappyBird.png").convert_alpha()
        self.image = pygame.transform.scale(raw_img, (BIRD_WIDTH, BIRD_HEIGHT))

        self.collision_w = int(BIRD_WIDTH * BIRD_COLLISION_RATIO)
        self.collision_h = int(BIRD_HEIGHT * BIRD_COLLISION_RATIO)

        self.x = BIRD_X
        self.y = WINDOW_HEIGHT // 2
        self.vel_y = 0

    def reset(self):
        self.x = BIRD_X
        self.y = WINDOW_HEIGHT // 2
        self.vel_y = 0

    def flap(self):
        self.vel_y = FLAP_STRENGTH
        flap_sound.play()

    def update(self):
        self.vel_y += GRAVITY
        self.y += self.vel_y

    def get_rect(self):
        cx = self.x + (BIRD_WIDTH - self.collision_w) / 2
        cy = self.y + (BIRD_HEIGHT - self.collision_h) / 2
        return pygame.Rect(cx, cy, self.collision_w, self.collision_h)

    def draw(self, surface):
        surface.blit(self.image, (self.x, self.y))
        # Red collision box
        pygame.draw.rect(surface, (255, 0, 0), self.get_rect(), 2)

# --------------------------------------------------------
# 6) Pipe Class (STATIC GAP + Range-based Horizontal Spacing)
# --------------------------------------------------------
class Pipe:
    """
    Pipe with a fixed vertical gap = PIPE_GAP.
    Horizontal collision width shrunk by HITBOX_SHRINK_FACTOR.

    For horizontal spacing, each pipe:
      - Checks the rightmost pipe among all pipes
      - Moves itself in a random range [MIN_PIPE_SPACING, MAX_PIPE_SPACING] beyond that
    """
    def __init__(self, x):
        self.x = x
        self.scored = False
        self.randomize_position()

        raw_pipe = pygame.image.load("flappyPipe.png").convert_alpha()
        self.pipe_bottom_img = pygame.transform.scale(raw_pipe, (PIPE_WIDTH, 600))
        self.pipe_top_img = pygame.transform.flip(self.pipe_bottom_img, False, True)

    def randomize_position(self):
        self.gap_top = random.randint(
            MIN_PIPE_HEIGHT,
            WINDOW_HEIGHT - PIPE_GAP - MIN_PIPE_HEIGHT
        )

    def update(self, pipe_speed, all_pipes):
        self.x -= pipe_speed
        if self.x + PIPE_WIDTH < 0:
            self.reset_position(all_pipes)

    def reset_position(self, all_pipes):
        # Find rightmost x among all pipes (excluding self)
        rightmost_x = max(p.x for p in all_pipes if p is not self)
        # Move ourselves in a random distance [MIN_PIPE_SPACING, MAX_PIPE_SPACING]
        # so there's always a pipe in that range away from the rightmost one
        dist = random.randint(MIN_PIPE_SPACING, MAX_PIPE_SPACING)
        self.x = rightmost_x + dist

        self.scored = False
        self.randomize_position()

    def get_rects(self):
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
        # top pipe
        top_h = self.pipe_top_img.get_height()
        top_y = self.gap_top - top_h
        surface.blit(self.pipe_top_img, (self.x, top_y))

        # bottom pipe
        bottom_y = self.gap_top + PIPE_GAP
        surface.blit(self.pipe_bottom_img, (self.x, bottom_y))

        # Green collision boxes
        top_rect, bottom_rect = self.get_rects()
        pygame.draw.rect(surface, (0, 255, 0), top_rect, 2)
        pygame.draw.rect(surface, (0, 255, 0), bottom_rect, 2)

# --------------------------------------------------------
# 7) Sound Effects
# --------------------------------------------------------
flap_sound = pygame.mixer.Sound("flap.wav")
collision_sound = pygame.mixer.Sound("collision.wav")
pass_sound = pygame.mixer.Sound("pass.wav")

# --------------------------------------------------------
# 8) Main Game Variables
# --------------------------------------------------------
game_state = STATE_START
score = 0
high_score = 0

bg = RandomSlidesBackground(SLIDES)

NUM_PIPES = 5                 # number of pipes to exist simultaneously
pipes = []
# Create them spaced out to the right initially
for i in range(NUM_PIPES):
    init_x = WINDOW_WIDTH + i * MIN_PIPE_SPACING
    pipes.append(Pipe(x=init_x))

bird = Bird()

# --------------------------------------------------------
# 9) Helper functions
# --------------------------------------------------------
def reset_game():
    """
    Reset the bird and pipes for a new game.
    """
    global score
    score = 0
    bird.reset()

    # We'll place each pipe in ascending order, so you eventually see them
    rightmost_x = WINDOW_WIDTH
    for i, pipe in enumerate(pipes):
        # space each pipe out in [MIN_PIPE_SPACING, MAX_PIPE_SPACING] from the rightmost
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
    """
    We scale speeds with the player's score. +1 speed for every 5 points.
    """
    increment = current_score // 5
    bg_speed = BG_SCROLL_SPEED_BASE + increment
    pipe_speed = PIPE_SPEED_BASE + increment
    return bg_speed, pipe_speed


# --------------------------------------------------------
# 10) Main Loop
# --------------------------------------------------------
while True:
    clock.tick(30)

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            quit_game()

        # Bird can flap if in PLAYING state
        if event.type == pygame.KEYDOWN and game_state == STATE_PLAYING:
            if event.key == pygame.K_SPACE:
                bird.flap()

    if game_state == STATE_START:
        bg.update()
        bg.draw(screen)
        bird.draw(screen)

        draw_text(
            screen,
            "Flappy Bird - Range-based Pipe Spacing",
            WINDOW_WIDTH // 2,
            WINDOW_HEIGHT // 4,
            center=True
        )
        draw_text(screen, f"Pipes: {NUM_PIPES}, Hitbox Factor: {HITBOX_SHRINK_FACTOR}",
                  WINDOW_WIDTH // 2, WINDOW_HEIGHT // 4 + 40, center=True)
        draw_text(screen, f"Spacing: [{MIN_PIPE_SPACING}, {MAX_PIPE_SPACING}]",
                  WINDOW_WIDTH // 2, WINDOW_HEIGHT // 4 + 80, center=True)
        draw_text(screen, "Press SPACE in-game to Flap!",
                  WINDOW_WIDTH // 2, WINDOW_HEIGHT // 4 + 120, center=True)

        # Buttons
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
        # Speeds scale with score
        current_bg_speed, current_pipe_speed = get_dynamic_speeds(score)

        bg.update(dynamic_speed=current_bg_speed)
        bird.update()

        for pipe in pipes:
            pipe.update(pipe_speed=current_pipe_speed, all_pipes=pipes)

            # Score if bird's back edge passes the pipe's right edge
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

        # Buttons
        button_width = 150
        button_height = 50
        start_x = (WINDOW_WIDTH // 2) - (button_width + 20)
        start_y = int(WINDOW_HEIGHT * 0.75)
        quit_x = (WINDOW_WIDTH // 2) + 20
        quit_y = int(WINDOW_HEIGHT * 0.75)

        draw_button("Start", start_x, start_y, button_width, button_height, RED, RED_HOVER, action=start_game)
        draw_button("Quit", quit_x, quit_y, button_width, button_height, RED, RED_HOVER, action=quit_game)

        pygame.display.flip()
