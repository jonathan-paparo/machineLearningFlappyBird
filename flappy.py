import pygame
import sys
import random

# --------------------------
# Window dimensions
# --------------------------
WINDOW_WIDTH = 800
WINDOW_HEIGHT = 600

# --------------------------
# Bird
# --------------------------
BIRD_X = 100
BIRD_WIDTH = 40  # Visual width of the bird image
BIRD_HEIGHT = 30  # Visual height of the bird image
FLAP_STRENGTH = -8
GRAVITY = 0.5

# Use a full collision box for the bird
BIRD_COLLISION_RATIO = 1

# --------------------------
# Pipe
# --------------------------
PIPE_WIDTH = 180  # Pipe image width
PIPE_GAP = 150
PIPE_SPEED = 3
MIN_PIPE_HEIGHT = 50

# We'll shrink the pipe collision width by a factor
SHRINK_PIPE_FACTOR = 4.5    # e.g., 180 / 3.5 ~ 51 px wide for collisions

# --------------------------
# Colors
# --------------------------
COLOR_SKY = (135, 206, 235)

# --------------------------
# Game States
# --------------------------
STATE_START = 0
STATE_PLAYING = 1
STATE_GAME_OVER = 2

pygame.init()
screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
pygame.display.set_caption("Flappy Bird - Improved Start & Clouds")
clock = pygame.time.Clock()

font = pygame.font.Font(None, 36)


# --------------------------------------------------------
# 1) Utility: draw_text
# --------------------------------------------------------
def draw_text(surface, text, x, y, color=(255, 255, 255), center=False):
    """
    Draws text onto the surface at (x, y).
    If center=True, (x, y) is the center of the text.
    """
    img = font.render(text, True, color)
    rect = img.get_rect()
    if center:
        rect.center = (x, y)
    else:
        rect.topleft = (x, y)
    surface.blit(img, rect)


# --------------------------------------------------------
# 2) Create Slides with Non-Overlapping Clouds
# --------------------------------------------------------
def create_slides(num_slides=10):
    """
    Each slide is 800x600, filled with the same sky color (COLOR_SKY).
    Clouds are placed in the top one-third, ensuring no overlap.
    """
    slides = []

    # Load the cloud image once
    cloud_raw = pygame.image.load("cloud.png").convert_alpha()
    # Scale the cloud to 1/3 of its original size
    cloud_w = cloud_raw.get_width() // 3
    cloud_h = cloud_raw.get_height() // 3
    cloud_scaled = pygame.transform.scale(cloud_raw, (cloud_w, cloud_h))

    for _ in range(num_slides):
        # Create a slide with sky color
        surf = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT))
        surf.fill(COLOR_SKY)

        # Place 2-4 non-overlapping clouds
        cloud_count = random.randint(2, 4)
        cloud_positions = []  # Keep track of cloud positions to avoid overlaps

        for _ in range(cloud_count):
            max_attempts = 100  # Avoid infinite loops in rare cases
            for _ in range(max_attempts):
                cx = random.randint(0, WINDOW_WIDTH - cloud_w)
                cy = random.randint(0, (WINDOW_HEIGHT // 3) - cloud_h)

                # Check for overlap
                overlap = False
                for existing in cloud_positions:
                    ex, ey = existing
                    if abs(cx - ex) < cloud_w and abs(cy - ey) < cloud_h:
                        overlap = True
                        break

                if not overlap:
                    cloud_positions.append((cx, cy))
                    surf.blit(cloud_scaled, (cx, cy))
                    break

        slides.append(surf)
    return slides


SLIDES = create_slides(num_slides=10)


# --------------------------------------------------------
# 3) RandomSlidesBackground
# --------------------------------------------------------
class RandomSlidesBackground:
    """
    Scrolls two side-by-side slides left at a fixed speed.
    When one slides off-screen, it reappears on the right
    with another random slide from SLIDES.
    """

    def __init__(self, slides, scroll_speed=2):
        self.width = WINDOW_WIDTH
        self.height = WINDOW_HEIGHT
        self.scroll_speed = scroll_speed

        self.slides = slides if slides else []
        if not self.slides:
            # fallback if empty
            fallback = pygame.Surface((self.width, self.height))
            fallback.fill(COLOR_SKY)
            self.slides = [fallback]

        self.x1 = 0
        self.x2 = self.width

        self.slide1 = random.choice(self.slides)
        self.slide2 = random.choice(self.slides)

    def update(self):
        # Scroll each "panel" to the left
        self.x1 -= self.scroll_speed
        self.x2 -= self.scroll_speed

        # If first panel is off-screen, move it to the right of second
        if self.x1 + self.width < 0:
            self.x1 = self.x2 + self.width
            self.slide1 = random.choice(self.slides)

        # If second panel is off-screen, move it to the right of first
        if self.x2 + self.width < 0:
            self.x2 = self.x1 + self.width
            self.slide2 = random.choice(self.slides)

    def draw(self, surface):
        surface.blit(self.slide1, (self.x1, 0))
        surface.blit(self.slide2, (self.x2, 0))


# --------------------------------------------------------
# 4) Bird Class
# --------------------------------------------------------
class Bird:
    def __init__(self):
        # Load the bird image (assume it's already transparent background)
        raw_img = pygame.image.load("flappyBird.png").convert_alpha()
        # Scale
        self.image = pygame.transform.scale(raw_img, (BIRD_WIDTH, BIRD_HEIGHT))

        # Collision box = full image size
        self.collision_w = int(BIRD_WIDTH * BIRD_COLLISION_RATIO)
        self.collision_h = int(BIRD_HEIGHT * BIRD_COLLISION_RATIO)

        self.reset()

    def reset(self):
        self.x = BIRD_X
        self.y = WINDOW_HEIGHT // 2
        self.vel_y = 0

    def flap(self):
        self.vel_y = FLAP_STRENGTH

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
# 5) Pipe Class
# --------------------------------------------------------
class Pipe:
    """
    Pipe image scaled to (PIPE_WIDTH x 600).
    Collision box narrower by factor=3.5, centered horizontally.
    """

    def __init__(self, x):
        self.x = x
        self.scored = False
        self.randomize_gap()

        # Load pipe
        raw_pipe = pygame.image.load("flappyPipe.png").convert_alpha()
        self.pipe_bottom_img = pygame.transform.scale(raw_pipe, (PIPE_WIDTH, 600))
        self.pipe_top_img = pygame.transform.flip(self.pipe_bottom_img, False, True)

    def randomize_gap(self):
        self.gap_top = random.randint(
            MIN_PIPE_HEIGHT,
            WINDOW_HEIGHT - PIPE_GAP - MIN_PIPE_HEIGHT
        )

    def update(self):
        self.x -= PIPE_SPEED
        if self.x + PIPE_WIDTH < 0:
            self.x = WINDOW_WIDTH
            self.randomize_gap()
            self.scored = False

    def get_rects(self):
        new_width = PIPE_WIDTH / SHRINK_PIPE_FACTOR
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
        # Top pipe
        top_h = self.pipe_top_img.get_height()
        top_y = self.gap_top - top_h
        surface.blit(self.pipe_top_img, (self.x, top_y))

        # Bottom pipe
        bottom_y = self.gap_top + PIPE_GAP
        surface.blit(self.pipe_bottom_img, (self.x, bottom_y))

        # Red collision boxes
        top_rect, bottom_rect = self.get_rects()
        pygame.draw.rect(surface, (255, 0, 0), top_rect, 2)
        pygame.draw.rect(surface, (255, 0, 0), bottom_rect, 2)


# --------------------------------------------------------
# 6) Main Game Variables
# --------------------------------------------------------
game_state = STATE_START
score = 0
high_score = 0

bg = RandomSlidesBackground(create_slides(num_slides=10), scroll_speed=2)
bird = Bird()
pipes = [
    Pipe(x=WINDOW_WIDTH // 2),
    Pipe(x=int(WINDOW_WIDTH * 0.75)),
    Pipe(x=WINDOW_WIDTH),
]


def reset_game():
    global score
    bird.reset()
    for i, pipe in enumerate(pipes):
        pipe.x = WINDOW_WIDTH + i * (WINDOW_WIDTH // len(pipes))
        pipe.randomize_gap()  # Randomize pipe gaps at the start
        pipe.scored = False
    score = 0


# --------------------------------------------------------
# 7) Main Loop
# --------------------------------------------------------
while True:
    clock.tick(30)

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()
        elif event.type == pygame.KEYDOWN:
            if game_state == STATE_START:
                if event.key == pygame.K_s:
                    reset_game()
                    game_state = STATE_PLAYING
                elif event.key in (pygame.K_q, pygame.K_ESCAPE):
                    pygame.quit()
                    sys.exit()
            elif game_state == STATE_PLAYING:
                if event.key == pygame.K_SPACE:
                    bird.flap()
            elif game_state == STATE_GAME_OVER:
                if event.key == pygame.K_s:
                    reset_game()
                    game_state = STATE_PLAYING
                elif event.key in (pygame.K_q, pygame.K_ESCAPE):
                    pygame.quit()
                    sys.exit()

    if game_state == STATE_START:
        bg.update()
        bg.draw(screen)
        bird.draw(screen)
        draw_text(screen, "FLAPPY BIRD with Clouds", WINDOW_WIDTH // 2, WINDOW_HEIGHT // 4, center=True)
        draw_text(screen, "Press S to Start | Q to Quit", WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2, center=True)
        pygame.display.flip()

    elif game_state == STATE_PLAYING:
        bg.update()
        bird.update()
        for pipe in pipes:
            pipe.update()
            if (pipe.x + PIPE_WIDTH) < bird.x and not pipe.scored:
                score += 1
                pipe.scored = True

        if bird.y < 0 or (bird.y + BIRD_HEIGHT) > WINDOW_HEIGHT:
            if score > high_score:
                high_score = score
            game_state = STATE_GAME_OVER

        bird_rect = bird.get_rect()
        for pipe in pipes:
            top_rect, bottom_rect = pipe.get_rects()
            if bird_rect.colliderect(top_rect) or bird_rect.colliderect(bottom_rect):
                if score > high_score:
                    high_score = score
                game_state = STATE_GAME_OVER

        bg.draw(screen)
        for pipe in pipes:
            pipe.draw(screen)
        bird.draw(screen)
        draw_text(screen, f"Score: {score}", 10, 10)
        draw_text(screen, f"High: {high_score}", 10, 50)
        pygame.display.flip()

    else:
        bg.draw(screen)
        for pipe in pipes:
            pipe.draw(screen)
        bird.draw(screen)
        draw_text(screen, "GAME OVER", WINDOW_WIDTH // 2, WINDOW_HEIGHT // 4, center=True)
        draw_text(screen, f"Score: {score}", WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 - 20, center=True)
        draw_text(screen, f"High Score: {high_score}", WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 + 20, center=True)
        draw_text(screen, "Press S to Retry | Q to Quit", WINDOW_WIDTH // 2, int(WINDOW_HEIGHT * 0.75), center=True)
        pygame.display.flip()
