import pygame
import sys
import random

# --- Window dimensions ---
WINDOW_WIDTH = 800
WINDOW_HEIGHT = 600

# --- Bird constants ---
BIRD_X = 100
BIRD_WIDTH = 40
BIRD_HEIGHT = 30
FLAP_STRENGTH = -8
GRAVITY = 0.5

# --- Pipe constants ---
PIPE_WIDTH = 60
PIPE_GAP = 150
PIPE_SPEED = 3
MIN_PIPE_HEIGHT = 50

# --- Colors ---
COLOR_BIRD = (255, 255, 0)   # yellow
COLOR_PIPE = (0, 255, 0)     # green
COLOR_SKY = (135, 206, 235)  # sky blue

# --- Game states ---
STATE_START = 0
STATE_PLAYING = 1
STATE_GAME_OVER = 2

pygame.init()
screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
pygame.display.set_caption("Flappy Bird - Score & High Score")
clock = pygame.time.Clock()

# --- Font for text ---
font = pygame.font.Font(None, 36)  # Default Pygame font, size 36

# ----------------------------------------------------------
# Bird class
# ----------------------------------------------------------
class Bird:
    def __init__(self):
        self.reset()

    def reset(self):
        """Put the bird back in the middle, no vertical velocity."""
        self.x = BIRD_X
        self.y = WINDOW_HEIGHT // 2
        self.vel_y = 0

    def flap(self):
        """Make the bird jump (negative velocity)."""
        self.vel_y = FLAP_STRENGTH

    def update(self):
        """Apply gravity and move the bird vertically."""
        self.vel_y += GRAVITY
        self.y += self.vel_y

    def get_rect(self):
        """Return a rect for collision checks."""
        return pygame.Rect(self.x, self.y, BIRD_WIDTH, BIRD_HEIGHT)

    def draw(self, surface):
        """Draw a simple yellow rectangle as the bird."""
        pygame.draw.rect(surface, COLOR_BIRD, self.get_rect())

# ----------------------------------------------------------
# Pipe class
# ----------------------------------------------------------
class Pipe:
    """
    A pair of top and bottom pipes. The gap is random.
    We'll track whether this pipe has been 'scored' yet
    to increment the score exactly once when the bird passes.
    """
    def __init__(self, x):
        self.x = x
        self.width = PIPE_WIDTH
        self.scored = False
        self.randomize_gap()

    def randomize_gap(self):
        """
        Choose a random start for the gap that isn't too close
        to the top or bottom.
        """
        self.gap_top = random.randint(
            MIN_PIPE_HEIGHT,
            WINDOW_HEIGHT - PIPE_GAP - MIN_PIPE_HEIGHT
        )

    def update(self):
        """
        Move the pipe to the left. If it goes off-screen,
        reset it to the far right with a new gap.
        """
        self.x -= PIPE_SPEED
        if self.x + self.width < 0:
            self.x = WINDOW_WIDTH
            self.randomize_gap()
            self.scored = False  # Bird can score again on this pipe

    def get_rects(self):
        """
        Return two rects: top pipe rect, bottom pipe rect.
        """
        top_rect = pygame.Rect(self.x, 0, self.width, self.gap_top)
        bottom_rect = pygame.Rect(
            self.x,
            self.gap_top + PIPE_GAP,
            self.width,
            WINDOW_HEIGHT - (self.gap_top + PIPE_GAP)
        )
        return top_rect, bottom_rect

    def draw(self, surface):
        top_rect, bottom_rect = self.get_rects()
        pygame.draw.rect(surface, COLOR_PIPE, top_rect)
        pygame.draw.rect(surface, COLOR_PIPE, bottom_rect)

# ----------------------------------------------------------
# Scrolling background (optional)
# ----------------------------------------------------------
class ScrollingBackground:
    """
    Scrolls left to give a sense of motion.
    We draw two copies of the background side by side.
    """
    def __init__(self):
        self.width = WINDOW_WIDTH
        self.height = WINDOW_HEIGHT
        self.scroll_speed = 2

        # Try loading an image named "background.png"
        # If missing, we'll just fill with sky blue
        try:
            self.image = pygame.image.load("background.png").convert()
            self.image = pygame.transform.scale(self.image, (self.width, self.height))
        except:
            self.image = pygame.Surface((self.width, self.height))
            self.image.fill(COLOR_SKY)

        # Positions of the two images
        self.x1 = 0
        self.x2 = self.width

    def update(self):
        self.x1 -= self.scroll_speed
        self.x2 -= self.scroll_speed

        # If off screen, reset to the right
        if self.x1 + self.width < 0:
            self.x1 = self.x2 + self.width
        if self.x2 + self.width < 0:
            self.x2 = self.x1 + self.width

    def draw(self, surface):
        surface.blit(self.image, (self.x1, 0))
        surface.blit(self.image, (self.x2, 0))

# ----------------------------------------------------------
# Helper functions
# ----------------------------------------------------------
def draw_text(surface, text, x, y, color=(255, 255, 255), center=False):
    """
    Render some text onto the screen at (x, y).
    If center=True, the text is centered at (x, y).
    """
    img = font.render(text, True, color)
    rect = img.get_rect()
    if center:
        rect.center = (x, y)
    else:
        rect.topleft = (x, y)
    surface.blit(img, rect)

# ----------------------------------------------------------
# Main loop variables
# ----------------------------------------------------------
game_state = STATE_START  # Start screen at first
score = 0
high_score = 0

bg = ScrollingBackground()
bird = Bird()

# We'll create a few pipes spaced out across the screen
pipes = [
    Pipe(x=WINDOW_WIDTH // 2),
    Pipe(x=int(WINDOW_WIDTH * 0.75)),
    Pipe(x=WINDOW_WIDTH),
]

def reset_game():
    """
    Reset everything for a new round.
    """
    global score
    bird.reset()
    for i, p in enumerate(pipes):
        # Space them out evenly on the right
        p.x = WINDOW_WIDTH + i * (WINDOW_WIDTH // len(pipes))
        p.scored = False
        p.randomize_gap()
    score = 0

# ----------------------------------------------------------
# Main game loop
# ----------------------------------------------------------
while True:
    clock.tick(30)  # 30 FPS

    # --- Event Handling ---
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()
        elif event.type == pygame.KEYDOWN:
            # Handle keys depending on game state
            if game_state == STATE_START:
                if event.key == pygame.K_s:
                    # Start the game
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
                    # Restart
                    reset_game()
                    game_state = STATE_PLAYING
                elif event.key in (pygame.K_q, pygame.K_ESCAPE):
                    pygame.quit()
                    sys.exit()

    # --- Update / Draw depending on game state ---
    if game_state == STATE_START:
        # Just draw a static background or slightly scrolling
        bg.update()
        bg.draw(screen)
        bird.draw(screen)

        draw_text(screen, "FLAPPY BIRD", WINDOW_WIDTH // 2, WINDOW_HEIGHT // 4, center=True)
        draw_text(screen, "Press S to Start or Q to Quit", WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2, center=True)
        pygame.display.flip()

    elif game_state == STATE_PLAYING:
        # 1) Update
        bg.update()
        bird.update()
        for pipe in pipes:
            pipe.update()

            # Check if bird passes this pipe => +1 to score
            # Condition: pipe's right edge < bird.x, and not pipe.scored
            if (pipe.x + pipe.width) < bird.x and not pipe.scored:
                score += 1
                pipe.scored = True

        # 2) Collision checks
        # a) Bird out of bounds (top or bottom)
        if bird.y < 0 or (bird.y + BIRD_HEIGHT) > WINDOW_HEIGHT:
            # Bird died
            if score > high_score:
                high_score = score
            game_state = STATE_GAME_OVER

        # b) Pipe collision
        bird_rect = bird.get_rect()
        for pipe in pipes:
            top_rect, bottom_rect = pipe.get_rects()
            if bird_rect.colliderect(top_rect) or bird_rect.colliderect(bottom_rect):
                # Bird died
                if score > high_score:
                    high_score = score
                game_state = STATE_GAME_OVER

        # 3) Draw
        bg.draw(screen)
        for pipe in pipes:
            pipe.draw(screen)
        bird.draw(screen)

        # 4) Draw score
        draw_text(screen, f"Score: {score}", 10, 10, color=(255,255,255))
        draw_text(screen, f"High: {high_score}", 10, 50, color=(255,255,255))
        pygame.display.flip()

    elif game_state == STATE_GAME_OVER:
        # Draw final frame (background & pipes) so we can show "Game Over" on top
        bg.draw(screen)
        for pipe in pipes:
            pipe.draw(screen)
        bird.draw(screen)

        # Score texts
        draw_text(screen, "GAME OVER", WINDOW_WIDTH//2, WINDOW_HEIGHT//4, center=True)
        draw_text(screen, f"Score: {score}", WINDOW_WIDTH//2, WINDOW_HEIGHT//2 - 20, center=True)
        draw_text(screen, f"High Score: {high_score}", WINDOW_WIDTH//2, WINDOW_HEIGHT//2 + 20, center=True)
        draw_text(screen, "Press S to Retry or Q to Quit", WINDOW_WIDTH//2, int(WINDOW_HEIGHT*0.75), center=True)
        pygame.display.flip()

    # End of main loop iteration
