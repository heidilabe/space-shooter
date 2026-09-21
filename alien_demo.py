"""
Demo jugable del marciano pixel art.

Muestra al personaje en un escenario sencillo con gravedad y suelo,
usando las mismas proporciones y paleta en todas sus animaciones.

Controles:
    <-  ->   caminar
    SHIFT    correr (con <-  o ->)
    ESPACIO  saltar
    X        atacar
    H        recibir damo (hurt)
    ESC      salir
"""

import pygame

import alien

# ---------------------------------------------------------------------------
# Configuracion
# ---------------------------------------------------------------------------
WIDTH, HEIGHT = 640, 360
FPS = 60
TITLE = "Alien Pixel Art - Demo"

PIXEL = 3  # tamano de cada pixel del sprite en pantalla (bordes pixelados)

GRAVITY = 1800.0
JUMP_VEL = -640.0
WALK_SPEED = 170.0
RUN_SPEED = 320.0

GROUND_Y = HEIGHT - 64

SKY_TOP = (24, 92, 120)
SKY_BOTTOM = (12, 34, 66)
GROUND_COLOR = (62, 106, 74)
GRASS_COLOR = (96, 168, 96)
GRASS_LINE = (200, 240, 190)


class Player:
    """Encapsula al personaje y su logica de movimiento simple."""

    def __init__(self):
        self.anims = alien.build_animations()
        # Pre-renderiza todas las superficies (una vez) para 60 FPS.
        self.frames = {
            name: [(alien.render_grid(f["grid"], PIXEL), f["dur"])
                   for f in frames]
            for name, frames in self.anims.items()
        }
        self.w = alien.GRID_W * PIXEL
        self.h = alien.GRID_H * PIXEL

        self.x = (WIDTH - self.w) // 2
        self.y = GROUND_Y - self.h
        self.vx = 0.0
        self.vy = 0.0
        self.on_ground = True

        self.state = "idle"
        self.time = 0.0          # tiempo en el estado actual
        self.hurt_timer = 0.0
        self.face = 1            # 1 derecha / -1 izquierda

    # -- control -------------------------------------------------------
    def update(self, dt, keys):
        running = keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT]
        left = keys[pygame.K_LEFT] or keys[pygame.K_a]
        right = keys[pygame.K_RIGHT] or keys[pygame.K_d]

        if self.hurt_timer > 0:
            self.hurt_timer -= dt

        # Movimiento horizontal
        if right:
            self.vx = RUN_SPEED if running else WALK_SPEED
            self.face = 1
        elif left:
            self.vx = -RUN_SPEED if running else -WALK_SPEED
            self.face = -1
        else:
            self.vx = 0.0

        self.x += self.vx * dt
        self.x = max(0, min(self.x, WIDTH - self.w))

        # Gravedad / salto
        self.vy += GRAVITY * dt
        self.y += self.vy * dt
        self.on_ground = self.y >= GROUND_Y - self.h
        if self.on_ground:
            self.y = GROUND_Y - self.h
            self.vy = 0.0

        # Eleccion de animacion
        if self.on_ground:
            if running and self.vx != 0:
                self._set_state("run")
            elif self.vx != 0:
                self._set_state("walk")
            elif self.hurt_timer > 0:
                self._set_state("hurt")
            else:
                self._set_state("idle")
        else:
            self._set_state("jump")

        self.time += dt

    def jump(self):
        if self.on_ground:
            self.vy = JUMP_VEL
            self.on_ground = False

    def attack(self):
        if not self._in_animation("attack"):
            self._set_state("attack")

    def hurt(self):
        self.hurt_timer = 0.5
        if not self._in_animation("hurt"):
            self._set_state("hurt")

    def _in_animation(self, name):
        return self.state == name and not self._finished()

    def _set_state(self, name):
        if self.state != name:
            self.state = name
            self.time = 0.0

    def _finished(self):
        frames = self.frames[self.state]
        duration = sum(d for _, d in frames)
        return self.time > duration

    # -- dibujo --------------------------------------------------------
    def draw(self, surface):
        frames = self.frames[self.state]
        total = sum(d for _, d in frames)
        elapsed = self.time % total
        accumulator = 0.0
        for surf, dur in frames:
            accumulator += dur
            if elapsed < accumulator:
                img = surf
                break
        else:
            img = frames[-1][0]

        # Voltear segun la direccion del movimiento
        img = pygame.transform.flip(img, self.face < 0, False)
        surface.blit(img, (round(self.x), round(self.y)))

    # -- HUD -----------------------------------------------------------
    @staticmethod
    def draw_help(surface, font):
        hint = (
            "Flechas: caminar   SHIFT: correr   ESPACIO: saltar   "
            "X: atacar   H: damo   ESC: salir"
        )
        color = (225, 245, 235)
        surface.blit(font.render(hint, True, color), (16, 8))


def draw_background(surface):
    """Degradado sencillo de cielo y suelo con hierba."""
    for y in range(HEIGHT):
        t = y / HEIGHT
        r = SKY_TOP[0] + (SKY_BOTTOM[0] - SKY_TOP[0]) * t
        g = SKY_TOP[1] + (SKY_BOTTOM[1] - SKY_TOP[1]) * t
        b = SKY_TOP[2] + (SKY_BOTTOM[2] - SKY_TOP[2]) * t
        pygame.draw.line(surface, (int(r), int(g), int(b)), (0, y), (WIDTH, y))

    surface.fill(GROUND_COLOR, (0, GROUND_Y, WIDTH, HEIGHT - GROUND_Y))
    surface.fill(GRASS_COLOR, (0, GROUND_Y, WIDTH, 10))
    for x in range(0, WIDTH, 24):
        surface.fill(GRASS_LINE, (x, GROUND_Y + 9, 12, 2))


def main():
    pygame.init()
    pygame.display.set_caption(TITLE)
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    clock = pygame.time.Clock()
    font = pygame.font.SysFont(None, 22)

    player = Player()
    running = True

    while running:
        dt = clock.tick(FPS) / 1000.0

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_SPACE:
                    player.jump()
                elif event.key == pygame.K_x:
                    player.attack()
                elif event.key == pygame.K_h:
                    player.hurt()

        keys = pygame.key.get_pressed()
        player.update(dt, keys)

        draw_background(screen)
        player.draw(screen)
        Player.draw_help(screen, font)

        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    main()