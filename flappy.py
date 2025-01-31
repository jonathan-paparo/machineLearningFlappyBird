"""
FLAPPY.PY
--------------------------------------------------------------------------------
1) Manual Flappy Bird game for testing.
2) NEAT AI with 8 inputs (two-pipe lookahead + distance to ceiling/floor).
3) SingleFileCheckpointer that overwrites "my-checkpoint-latest" each generation.
4) BIGGER PUNISHMENT for hitting walls vs. hitting a pipe:
   - Hitting top/bottom => -10 fitness
   - Hitting a pipe => -3 fitness
--------------------------------------------------------------------------------
Usage:
  python flappy.py               -> manual play
  python flappy.py ai            -> run NEAT for 50 gens, overwriting "my-checkpoint-latest"
  python flappy.py resume my-checkpoint-latest
     -> resume from that same file for additional generations
"""

import pygame
import sys
import random
import os
import neat
from neat.checkpoint import Checkpointer
import math

# ----------------------------------------------------------------------------
# 1) GAME CONSTANTS
# ----------------------------------------------------------------------------
WINDOW_WIDTH  = 800
WINDOW_HEIGHT = 600

BIRD_X        = 100
BIRD_WIDTH    = 40
BIRD_HEIGHT   = 30
FLAP_STRENGTH = -8
GRAVITY       = 0.5

PIPE_WIDTH         = 180
PIPE_GAP           = 150
MIN_PIPE_HEIGHT    = 50
PIPE_SPEED_BASE    = 3
MIN_PIPE_SPACING   = 200
MAX_PIPE_SPACING   = 400
HITBOX_SHRINK_FACTOR = 0.2

BG_SCROLL_SPEED_BASE = 2

COLOR_SKY = (135, 206, 235)
WHITE     = (255, 255, 255)
RED       = (200, 0, 0)
RED_HOVER = (255, 0, 0)

STATE_START   = 0
STATE_PLAYING = 1
STATE_GAME_OVER = 2

pygame.init()
screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
pygame.display.set_caption("Flappy Bird - Big penalty for walls, SingleFileCheckpointer")
clock = pygame.time.Clock()
font = pygame.font.Font(None, 36)

# ----------------------------------------------------------------------------
# 2) SOUND EFFECTS
# ----------------------------------------------------------------------------
flap_sound      = pygame.mixer.Sound("flap.wav")
collision_sound = pygame.mixer.Sound("collision.wav")
pass_sound      = pygame.mixer.Sound("pass.wav")

# ----------------------------------------------------------------------------
# 3) UTILS
# ----------------------------------------------------------------------------
def draw_text(surface, text, x, y, color=WHITE, center=False):
    img = font.render(text, True, color)
    rect = img.get_rect()
    if center:
        rect.center = (x, y)
    else:
        rect.topleft = (x, y)
    surface.blit(img, rect)

def draw_button(text, x, y, w, h, inactive_color, active_color, action=None):
    mouse = pygame.mouse.get_pos()
    click = pygame.mouse.get_pressed()
    if x + w > mouse[0] > x and y + h > mouse[1] > y:
        pygame.draw.rect(screen, active_color, (x, y, w, h))
        if click[0] == 1 and action:
            action()
    else:
        pygame.draw.rect(screen, inactive_color, (x, y, w, h))

    txt_surf = font.render(text, True, WHITE)
    txt_rect = txt_surf.get_rect(center=(x + w//2, y + h//2))
    screen.blit(txt_surf, txt_rect)

def create_slides(num_slides=20):
    slides = []
    cloud_raw = pygame.image.load("cloud.png").convert_alpha()
    cloud_w = cloud_raw.get_width() // 3
    cloud_h = cloud_raw.get_height() // 3
    cloud_scaled = pygame.transform.scale(cloud_raw, (cloud_w, cloud_h))

    for _ in range(num_slides):
        surf = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT))
        surf.fill(COLOR_SKY)
        cloud_count = random.randint(2, 4)
        used_positions = []
        for _c in range(cloud_count):
            for _attempt in range(100):
                cx = random.randint(0, WINDOW_WIDTH - cloud_w)
                cy = random.randint(0, (WINDOW_HEIGHT//3) - cloud_h)
                overlap = any(abs(cx - ex)<cloud_w and abs(cy - ey)<cloud_h for ex,ey in used_positions)
                if not overlap:
                    used_positions.append((cx, cy))
                    surf.blit(cloud_scaled, (cx, cy))
                    break
        slides.append(surf)
    return slides

SLIDES = create_slides()

# ----------------------------------------------------------------------------
# 4) RANDOM BACKGROUND
# ----------------------------------------------------------------------------
class RandomSlidesBackground:
    def __init__(self, slides, scroll_speed=BG_SCROLL_SPEED_BASE):
        self.width  = WINDOW_WIDTH
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
        if self.x1 + self.width < 0:
            self.x1 = self.x2 + self.width
            self.slide1 = random.choice(self.slides)
        if self.x2 + self.width < 0:
            self.x2 = self.x1 + self.width
            self.slide2 = random.choice(self.slides)

    def draw(self, surface):
        surface.blit(self.slide1, (self.x1, 0))
        surface.blit(self.slide2, (self.x2, 0))

# ----------------------------------------------------------------------------
# 5) BIRD
# ----------------------------------------------------------------------------
class Bird:
    def __init__(self):
        raw_img = pygame.image.load("flappyBird.png").convert_alpha()
        self.image = pygame.transform.scale(raw_img, (BIRD_WIDTH, BIRD_HEIGHT))
        self.x = BIRD_X
        self.y = WINDOW_HEIGHT//2
        self.vel_y = 0

    def reset(self):
        self.x = BIRD_X
        self.y = WINDOW_HEIGHT//2
        self.vel_y = 0

    def flap(self):
        self.vel_y = FLAP_STRENGTH
        flap_sound.play()

    def update(self):
        self.vel_y += GRAVITY
        self.y += self.vel_y

    def get_rect(self):
        return pygame.Rect(self.x, self.y, BIRD_WIDTH, BIRD_HEIGHT)

    def draw(self, surface):
        surface.blit(self.image, (self.x, self.y))
        pygame.draw.rect(surface, (255,0,0), self.get_rect(), 2)

# ----------------------------------------------------------------------------
# 6) PIPE
# ----------------------------------------------------------------------------
class Pipe:
    def __init__(self, x):
        self.x = x
        self.scored = False
        self.randomize_position()
        raw_pipe = pygame.image.load("flappyPipe.png").convert_alpha()
        self.pipe_bottom_img = pygame.transform.scale(raw_pipe, (PIPE_WIDTH, 600))
        self.pipe_top_img    = pygame.transform.flip(self.pipe_bottom_img, False, True)

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
        rightmost_x = max(p.x for p in all_pipes if p is not self)
        dist = random.randint(MIN_PIPE_SPACING, MAX_PIPE_SPACING)
        self.x = rightmost_x + dist
        self.scored = False
        self.randomize_position()

    def get_rects(self):
        new_width = PIPE_WIDTH * HITBOX_SHRINK_FACTOR
        off_x     = (PIPE_WIDTH - new_width)/2
        top_rect = pygame.Rect(self.x + off_x, 0, new_width, self.gap_top)
        bottom_rect = pygame.Rect(
            self.x + off_x,
            self.gap_top + PIPE_GAP,
            new_width,
            WINDOW_HEIGHT - (self.gap_top + PIPE_GAP)
        )
        return top_rect, bottom_rect

    def draw(self, surface):
        top_h = self.pipe_top_img.get_height()
        top_y = self.gap_top - top_h
        surface.blit(self.pipe_top_img, (self.x, top_y))
        bottom_y = self.gap_top + PIPE_GAP
        surface.blit(self.pipe_bottom_img, (self.x, bottom_y))

        tr, br = self.get_rects()
        pygame.draw.rect(surface, (0,255,0), tr, 2)
        pygame.draw.rect(surface, (0,255,0), br, 2)

# ----------------------------------------------------------------------------
# 7) MANUAL PLAY VARIABLES
# ----------------------------------------------------------------------------
game_state = STATE_START
score      = 0
high_score = 0

bg = RandomSlidesBackground(SLIDES)
NUM_PIPES = 5
pipes = []
for i in range(NUM_PIPES):
    init_x = WINDOW_WIDTH + i*MIN_PIPE_SPACING
    pipes.append(Pipe(init_x))

bird = Bird()

def reset_game():
    global score
    score = 0
    bird.reset()
    rightmost_x = WINDOW_WIDTH
    for p in pipes:
        dist = random.randint(MIN_PIPE_SPACING, MAX_PIPE_SPACING)
        p.x = rightmost_x + dist
        p.scored = False
        p.randomize_position()
        rightmost_x = p.x

def quit_game():
    pygame.quit()
    sys.exit()

def start_game():
    global game_state
    reset_game()
    game_state = STATE_PLAYING

def get_dynamic_speeds(current_score):
    increment = current_score // 5
    bg_speed   = BG_SCROLL_SPEED_BASE + increment
    pipe_speed = PIPE_SPEED_BASE       + increment
    return bg_speed, pipe_speed

# ----------------------------------------------------------------------------
# 8) MAIN HUMAN MODE
# ----------------------------------------------------------------------------
def main_human_mode():
    global game_state, score, high_score
    while True:
        clock.tick(30)
        for event in pygame.event.get():
            if event.type==pygame.QUIT:
                quit_game()
            elif event.type==pygame.KEYDOWN and game_state==STATE_PLAYING:
                if event.key==pygame.K_SPACE:
                    bird.flap()

        if game_state==STATE_START:
            bg.update()
            bg.draw(screen)
            bird.draw(screen)
            draw_text(screen,
                      "Flappy Bird - Big penalty for hitting walls!",
                      WINDOW_WIDTH//2,
                      WINDOW_HEIGHT//4,
                      center=True)
            draw_text(screen,
                      "Press SPACE in-game to flap!",
                      WINDOW_WIDTH//2,
                      WINDOW_HEIGHT//4+60,
                      center=True)

            bw = 150
            bh = 50
            sx = (WINDOW_WIDTH//2)-(bw+20)
            sy = int(WINDOW_HEIGHT*0.6)
            qx = (WINDOW_WIDTH//2)+20
            qy = int(WINDOW_HEIGHT*0.6)

            draw_button("Start", sx, sy, bw, bh, RED, RED_HOVER, action=start_game)
            draw_button("Quit",  qx, qy, bw, bh, RED, RED_HOVER, action=quit_game)

            pygame.display.flip()

        elif game_state==STATE_PLAYING:
            bg_s, pipe_s = get_dynamic_speeds(score)
            bg.update(dynamic_speed=bg_s)
            bird.update()

            for p in pipes:
                p.update(pipe_speed=pipe_s, all_pipes=pipes)
                # scoring
                if (p.x + PIPE_WIDTH)<(bird.x + BIRD_WIDTH) and not p.scored:
                    score+=1
                    p.scored=True
                    pass_sound.play()

            # collisions or out-of-bounds
            if bird.y<0 or (bird.y+BIRD_HEIGHT)>=WINDOW_HEIGHT:
                # BIG penalty for hitting walls
                if score>high_score:
                    high_score=score
                collision_sound.play()
                game_state=STATE_GAME_OVER

            br = bird.get_rect()
            for p in pipes:
                tr, br2 = p.get_rects()
                if br.colliderect(tr) or br.colliderect(br2):
                    if score>high_score:
                        high_score=score
                    collision_sound.play()
                    game_state=STATE_GAME_OVER

            bg.draw(screen)
            for p in pipes:
                p.draw(screen)
            bird.draw(screen)
            draw_text(screen, f"Score: {score}", 10,10)
            draw_text(screen, f"High: {high_score}", 10,50)
            pygame.display.flip()

        else:
            # GAME_OVER
            bg.draw(screen)
            for p in pipes:
                p.draw(screen)
            bird.draw(screen)
            draw_text(screen, "GAME OVER", WINDOW_WIDTH//2, WINDOW_HEIGHT//4, center=True)
            draw_text(screen, f"Score: {score}", WINDOW_WIDTH//2, WINDOW_HEIGHT//2-20, center=True)
            draw_text(screen, f"High Score: {high_score}", WINDOW_WIDTH//2, WINDOW_HEIGHT//2+20, center=True)

            bw = 150
            bh = 50
            sx = (WINDOW_WIDTH//2)-(bw+20)
            sy = int(WINDOW_HEIGHT*0.75)
            qx = (WINDOW_WIDTH//2)+20
            qy = int(WINDOW_HEIGHT*0.75)

            draw_button("Start", sx, sy, bw, bh, RED, RED_HOVER, action=start_game)
            draw_button("Quit",  qx, qy, bw, bh, RED, RED_HOVER, action=quit_game)

            pygame.display.flip()

# ----------------------------------------------------------------------------
# 9) NEAT EVAL (8 inputs + bigger penalty for walls)
# ----------------------------------------------------------------------------
def eval_genomes(genomes, config):
    """
    NEAT calls this per generation.
    Each bird sees 8 inputs (two-pipe lookahead + dist to ceiling/floor).
    We impose bigger penalty for hitting walls: -10
    Pipe collisions: -3
    """
    local_bg = RandomSlidesBackground(SLIDES)
    local_pipes = []
    for i in range(NUM_PIPES):
        init_x = WINDOW_WIDTH + i*MIN_PIPE_SPACING
        local_pipes.append(Pipe(init_x))

    nets = []
    ge   = []
    ai_birds = []

    for genome_id, genome in genomes:
        genome.fitness = 0
        net = neat.nn.FeedForwardNetwork.create(genome, config)
        nets.append(net)
        new_bird = Bird()
        ai_birds.append(new_bird)
        ge.append(genome)

    frame_count = 0
    local_score = 0
    run = True

    while run and len(ai_birds)>0:
        clock.tick(30)
        frame_count += 1

        for event in pygame.event.get():
            if event.type==pygame.QUIT:
                pygame.quit()
                sys.exit()

        # speeds scale with local_score
        bg_speed, pipe_speed = get_dynamic_speeds(local_score)
        local_bg.update(dynamic_speed=bg_speed)

        # move local pipes
        for p in local_pipes:
            p.update(pipe_speed=pipe_speed, all_pipes=local_pipes)

        # gather inputs & check collisions
        indices_to_remove = []
        for i,bird_ai in enumerate(ai_birds):
            # find up to 2 pipes ahead
            pipes_ahead = []
            for p_obj in local_pipes:
                dist_x = p_obj.x - bird_ai.x
                if dist_x> -PIPE_WIDTH:
                    pipes_ahead.append((dist_x, p_obj))
            pipes_ahead.sort(key=lambda x: x[0])

            if len(pipes_ahead)>0:
                dist1 = pipes_ahead[0][0]
                pipe1 = pipes_ahead[0][1]
                top1  = pipe1.gap_top
                bot1  = pipe1.gap_top + PIPE_GAP
            else:
                dist1=0; top1=0; bot1=0

            if len(pipes_ahead)>1:
                dist2 = pipes_ahead[1][0]
                pipe2 = pipes_ahead[1][1]
                top2  = pipe2.gap_top
                bot2  = pipe2.gap_top + PIPE_GAP
            else:
                dist2=0; top2=0; bot2=0

            dist_ceiling = bird_ai.y
            dist_floor   = WINDOW_HEIGHT - (bird_ai.y + BIRD_HEIGHT)

            # 8 inputs
            inputs = (
                dist_ceiling,  # 1
                dist_floor,    # 2
                dist1,         # 3
                top1,          # 4
                bot1,          # 5
                dist2,         # 6
                top2,          # 7
                bot2           # 8
            )
            output = nets[i].activate(inputs)
            if output[0]>0.5:
                bird_ai.flap()

        # update birds
        for i,bird_ai in enumerate(ai_birds):
            bird_ai.update()

        # collisions
        for i,bird_ai in enumerate(ai_birds):
            # top/bottom wall => big penalty
            if bird_ai.y<0 or (bird_ai.y+BIRD_HEIGHT)>=WINDOW_HEIGHT:
                ge[i].fitness -= 10  # big penalty
                indices_to_remove.append(i)
                continue

            # pipe collision => smaller penalty
            br = bird_ai.get_rect()
            for p_obj in local_pipes:
                tr, br2 = p_obj.get_rects()
                if br.colliderect(tr) or br.colliderect(br2):
                    ge[i].fitness -= 3  # smaller penalty
                    indices_to_remove.append(i)
                    break

        # scoring
        for p_obj in local_pipes:
            if (p_obj.x + PIPE_WIDTH)<(BIRD_X + BIRD_WIDTH) and not p_obj.scored:
                p_obj.scored=True
                local_score+=1
                # reward living birds
                for j in range(len(ai_birds)):
                    ge[j].fitness += 5

        # remove dead
        for idx in reversed(indices_to_remove):
            ai_birds.pop(idx)
            nets.pop(idx)
            ge.pop(idx)

        if frame_count>20000:
            break

        # draw
        screen.fill(COLOR_SKY)
        local_bg.draw(screen)
        for p_obj in local_pipes:
            p_obj.draw(screen)
        for b_obj in ai_birds:
            b_obj.draw(screen)
        draw_text(screen, f"Gen Score: {local_score}", 10,10)
        draw_text(screen, f"Alive: {len(ai_birds)}",   10,50)
        pygame.display.flip()

# ----------------------------------------------------------------------------
# 10) SINGLE-FILE CHECKPOINTER w/ create_checkpoint
# ----------------------------------------------------------------------------
class SingleFileCheckpointer(Checkpointer):
    """
    Overwrites 'my-checkpoint-latest' each generation.
    We define create_checkpoint to avoid missing method errors.
    """
    def __init__(self, filename="my-checkpoint-latest"):
        super().__init__(generation_interval=1, time_interval_seconds=None)
        self.filename = filename

    def create_checkpoint(self, config, population, species_set, generation):
        import random
        return (
            generation,
            config,
            population,
            species_set,
            random.getstate()
        )

    def save_checkpoint(self, config, population, species_set, generation):
        data = self.create_checkpoint(config, population, species_set, generation)
        import gzip, pickle
        with gzip.open(self.filename, "wb", compresslevel=5) as f:
            pickle.dump(data, f, protocol=pickle.HIGHEST_PROTOCOL)
        print(f"[SingleFileCheckpointer] Overwrote checkpoint: {self.filename}")

# ----------------------------------------------------------------------------
# 11) run_neat
# ----------------------------------------------------------------------------
def run_neat(config_file, checkpoint_file=None):
    """
    Load config, resume or fresh, single-file checkpoint each generation,
    up to 50 generations with eval_genomes.
    """
    config = neat.config.Config(
        neat.DefaultGenome,
        neat.DefaultReproduction,
        neat.DefaultSpeciesSet,
        neat.DefaultStagnation,
        config_file
    )

    if checkpoint_file:
        print(f"Resuming from {checkpoint_file}")
        population = neat.Checkpointer.restore_checkpoint(checkpoint_file)
    else:
        population = neat.Population(config)

    population.add_reporter(neat.StdOutReporter(True))
    stats = neat.StatisticsReporter()
    population.add_reporter(stats)

    single_cp = SingleFileCheckpointer("my-checkpoint-latest")
    population.add_reporter(single_cp)

    winner = population.run(eval_genomes, 50)
    print("Done training after 50 generations.")
    print("Best genome found:", winner)

# ----------------------------------------------------------------------------
# 12) main
# ----------------------------------------------------------------------------
def main():
    if len(sys.argv)>1:
        mode = sys.argv[1].lower()
        if mode=="ai":
            config_path = os.path.join(os.path.dirname(__file__), "config-feedforward.txt")
            run_neat(config_path)
        elif mode=="resume":
            if len(sys.argv)<3:
                print("Usage: python flappy.py resume <checkpoint_file>")
                sys.exit(1)
            cp_file = sys.argv[2]
            config_path = os.path.join(os.path.dirname(__file__), "config-feedforward.txt")
            run_neat(config_path, checkpoint_file=cp_file)
        else:
            print("Unknown arg. Use 'ai' or 'resume <filename>'")
    else:
        # no args -> manual
        main_human_mode()

if __name__=="__main__":
    main()
