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
BIRD_WIDTH = 40       # Visual width of the bird image
BIRD_HEIGHT = 30      # Visual height of the bird image
FLAP_STRENGTH = -8
GRAVITY = 0.5

# Bird's collision box ratio:
#  - Width is 25% of the bird image width
#  - Height is 2 × 25% = 50% of the bird image height
BIRD_COLLISION_RATIO = 1

# --------------------------
# Pipe
# --------------------------
PIPE_WIDTH = 180      # Pipe image width
PIPE_GAP = 150
PIPE_SPEED = 3
MIN_PIPE_HEIGHT = 50

# We'll shrink the pipe collision width to 1/3 the visual width
SHRINK_PIPE_FACTOR = 3.5  # meaning collision width = PIPE_WIDTH / 3

# Colors (for fallback / text)
COLOR_SKY = (135, 206, 235)

# --------------------------
# Game States
# --------------------------
STATE_START = 0
STATE_PLAYING = 1
STATE_GAME_OVER = 2

pygame.init()
screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
pygame.display.set_caption("Flappy Bird - Narrower Pipe Collision")
clock = pygame.time.Clock()

font = pygame.font.Font(None, 36)

# --------------------------------------------------------
#  Bird Class
# --------------------------------------------------------
class Bird:
    def __init__(self):
        # Load the bird image once
        raw_img = pygame.image.load("flappyBird.png").convert_alpha()
        # Scale it to match our full-size bird dimension (40×30)
        self.image = pygame.transform.scale(raw_img, (BIRD_WIDTH, BIRD_HEIGHT))

        # Calculate the collision box
        # Width = 25% of BIRD_WIDTH, height = (2 × 25%) of BIRD_HEIGHT
        self.collision_w = int(BIRD_WIDTH * BIRD_COLLISION_RATIO)
        self.collision_h = int(BIRD_HEIGHT *  BIRD_COLLISION_RATIO)

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
        """
        Return a smaller Rect for collisions,
        centered within the (x, y, BIRD_WIDTH, BIRD_HEIGHT).
        """
        collision_x = self.x + (BIRD_WIDTH - self.collision_w) / 2
        collision_y = self.y + (BIRD_HEIGHT - self.collision_h) / 2
        return pygame.Rect(collision_x, collision_y, self.collision_w, self.collision_h)

    def draw(self, surface):
        # Draw the full-size bird image
        surface.blit(self.image, (self.x, self.y))

        # Draw a red rectangle to visualize the collision box
        pygame.draw.rect(surface, (255, 0, 0), self.get_rect(), 2)

# --------------------------------------------------------
#  Pipe Class
# --------------------------------------------------------
class Pipe:
    """
    We load one pipe image for the bottom, then flip it for the top.
    The image is scaled to PIPE_WIDTH x 600 px visually.
    For collisions, we shrink the rect width to 1/3 (centered).
    """
    def __init__(self, x):
        self.x = x
        self.scored = False
        self.randomize_gap()

        # Load the pipe image
        raw_pipe_img = pygame.image.load("flappyPipe.png").convert_alpha()
        # Scale: new width = PIPE_WIDTH (180), keep ~600 tall
        self.pipe_bottom_img = pygame.transform.scale(raw_pipe_img, (PIPE_WIDTH, 600))
        # Flip vertically for the top pipe
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
        """
        Shrink the collision width to 1/3 the original (centered).
        """
        new_width = PIPE_WIDTH / SHRINK_PIPE_FACTOR   # e.g., 180 / 3 = 60
        offset_x = (PIPE_WIDTH - new_width) / 2       # center horizontally

        # top pipe collision
        top_rect = pygame.Rect(
            self.x + offset_x,
            0,
            new_width,
            self.gap_top
        )
        # bottom pipe collision
        bottom_rect = pygame.Rect(
            self.x + offset_x,
            self.gap_top + PIPE_GAP,
            new_width,
            WINDOW_HEIGHT - (self.gap_top + PIPE_GAP)
        )
        return top_rect, bottom_rect

    def draw(self, surface):
        # Draw top pipe so its bottom edge aligns with gap_top
        top_height = self.pipe_top_img.get_height()
        top_y = self.gap_top - top_height
        surface.blit(self.pipe_top_img, (self.x, top_y))

        # Draw bottom pipe
        bottom_y = self.gap_top + PIPE_GAP
        surface.blit(self.pipe_bottom_img, (self.x, bottom_y))

        # Draw collision boxes in red (debug)
        top_rect, bottom_rect = self.get_rects()
        pygame.draw.rect(surface, (255, 0, 0), top_rect, 2)
        pygame.draw.rect(surface, (255, 0, 0), bottom_rect, 2)

# --------------------------------------------------------
#  Simple Scrolling Background
# --------------------------------------------------------
class ScrollingBackground:
    def __init__(self):
        self.width = WINDOW_WIDTH
        self.height = WINDOW_HEIGHT
        self.scroll_speed = 2
        self.image = pygame.Surface((self.width, self.height))
        self.image.fill(COLOR_SKY)

        self.x1 = 0
        self.x2 = self.width

    def update(self):
        self.x1 -= self.scroll_speed
        self.x2 -= self.scroll_speed
        if self.x1 + self.width < 0:
            self.x1 = self.x2 + self.width
        if self.x2 + self.width < 0:
            self.x2 = self.x1 + self.width

    def draw(self, surface):
        surface.blit(self.image, (self.x1, 0))
        surface.blit(self.image, (self.x2, 0))

# --------------------------------------------------------
#  Helper function for text
# --------------------------------------------------------
def draw_text(surface, text, x, y, color=(255, 255, 255), center=False):
    img = font.render(text, True, color)
    rect = img.get_rect()
    if center:
        rect.center = (x, y)
    else:
        rect.topleft = (x, y)
    surface.blit(img, rect)

# --------------------------------------------------------
#  Main Game Variables
# --------------------------------------------------------
STATE_START = 0
STATE_PLAYING = 1
STATE_GAME_OVER = 2

game_state = STATE_START
score = 0
high_score = 0

bg = ScrollingBackground()
bird = Bird()
pipes = [
    Pipe(x=WINDOW_WIDTH // 2),
    Pipe(x=int(WINDOW_WIDTH * 0.75)),
    Pipe(x=WINDOW_WIDTH),
]

def reset_game():
    global score
    bird.reset()
    for i, p in enumerate(pipes):
        p.x = WINDOW_WIDTH + i * (WINDOW_WIDTH // len(pipes))
        p.scored = False
        p.randomize_gap()
    score = 0

# --------------------------------------------------------
#  Main Loop
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
        draw_text(screen, "FLAPPY BIRD - 1/3 Pipe Hitbox", WINDOW_WIDTH//2, WINDOW_HEIGHT//4, center=True)
        draw_text(screen, "Press S to Start, Q to Quit", WINDOW_WIDTH//2, WINDOW_HEIGHT//2, center=True)
        pygame.display.flip()

    elif game_state == STATE_PLAYING:
        # Update
        bg.update()
        bird.update()
        for pipe in pipes:
            pipe.update()
            # Score check
            if (pipe.x + PIPE_WIDTH) < bird.x and not pipe.scored:
                score += 1
                pipe.scored = True

        # Collision checks
        # Bird out of bounds?
        if bird.y < 0 or (bird.y + BIRD_HEIGHT) > WINDOW_HEIGHT:
            if score > high_score:
                high_score = score
            game_state = STATE_GAME_OVER

        # Pipe collision?
        bird_rect = bird.get_rect()
        for pipe in pipes:
            top_rect, bottom_rect = pipe.get_rects()
            if bird_rect.colliderect(top_rect) or bird_rect.colliderect(bottom_rect):
                if score > high_score:
                    high_score = score
                game_state = STATE_GAME_OVER

        # Draw
        bg.draw(screen)
        for pipe in pipes:
            pipe.draw(screen)
        bird.draw(screen)
        draw_text(screen, f"Score: {score}", 10, 10)
        draw_text(screen, f"High: {high_score}", 10, 50)
        pygame.display.flip()

    else:  # STATE_GAME_OVER
        bg.draw(screen)
        for pipe in pipes:
            pipe.draw(screen)
        bird.draw(screen)
        draw_text(screen, "GAME OVER", WINDOW_WIDTH//2, WINDOW_HEIGHT//4, center=True)
        draw_text(screen, f"Score: {score}", WINDOW_WIDTH//2, WINDOW_HEIGHT//2 - 20, center=True)
        draw_text(screen, f"High Score: {high_score}", WINDOW_WIDTH//2, WINDOW_HEIGHT//2 + 20, center=True)
        draw_text(screen, "Press S to Retry or Q to Quit", WINDOW_WIDTH//2, int(WINDOW_HEIGHT*0.75), center=True)
        pygame.display.flip()
