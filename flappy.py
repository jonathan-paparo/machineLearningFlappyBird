import pygame
import sys

WINDOW_WIDTH = 2000
WINDOW_HEIGHT = 1000


class Bird:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.vel_x = 0
        self.vel_y = 0

    def update(self, gravity=0.5):
        # Apply gravity for vertical movement
        self.vel_y += gravity
        self.y += self.vel_y

        # Apply horizontal velocity
        self.x += self.vel_x

    def flap(self, flap_strength=-8):
        # Give the bird an upward push
        self.vel_y = flap_strength

    def draw(self, screen):
        bird_width = 40
        bird_height = 30
        rect = (self.x, self.y, bird_width, bird_height)
        pygame.draw.rect(screen, (255, 255, 0), rect)  # Yellow rect


def main():
    pygame.init()
    screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    pygame.display.set_caption("Flappy Bird with Horizontal Movement")
    clock = pygame.time.Clock()

    # Spawn bird roughly at center
    bird = Bird(x=WINDOW_WIDTH // 2, y=WINDOW_HEIGHT // 2)

    running = True
    while running:
        # Limit to 30 FPS
        clock.tick(30)

        # Handle basic events
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    bird.flap()

        # 1) Get the current state of the keyboard:
        keys = pygame.key.get_pressed()

        # 2) If left arrow is held, set vel_x negative
        if keys[pygame.K_LEFT]:
            bird.vel_x = -5
        # 3) If right arrow is held, set vel_x positive
        elif keys[pygame.K_RIGHT]:
            bird.vel_x = 5
        else:
            # 4) If neither left nor right is held, stop horizontal movement
            bird.vel_x = 0

        # Update the bird (apply gravity, movement)
        bird.update()

        # BOUNDARIES
        bird_width = 40
        bird_height = 30

        # Prevent going off top
        if bird.y < 0:
            bird.y = 0
            bird.vel_y = 0
        # Prevent going off bottom
        if bird.y > WINDOW_HEIGHT - bird_height:
            bird.y = WINDOW_HEIGHT - bird_height
            bird.vel_y = 0

        # Reset bird if it hits left boundary
        if bird.x < 0:
            bird.x = WINDOW_WIDTH // 2
            bird.y = WINDOW_HEIGHT // 2
            bird.vel_x = 0
            bird.vel_y = 0

        # Reset bird if it hits right boundary
        if bird.x + bird_width > WINDOW_WIDTH:
            bird.x = WINDOW_WIDTH // 2
            bird.y = WINDOW_HEIGHT // 2
            bird.vel_x = 0
            bird.vel_y = 0

        # RENDERING
        screen.fill((135, 206, 235))
        bird.draw(screen)
        pygame.display.flip()

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
