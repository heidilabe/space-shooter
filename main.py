"""
Space Shooter - Juego de nave espacial en Python con pygame.

Caracteristicas:
- Ventana 400x600, fondo estelar con estrellas parpadeantes y planetas neón.
- Nave controlada en 4 direcciones (flechas / WASD), disparo automatico.
- Enemigos triangulares que descienden en oleadas con dificultad creciente.
- Marcianos de platillo esporadicos, mas resistentes y valiosos.
- Vidas, puntuacion, pantalla de Game Over y reinicio.
- Solo se pierde una vida al chocar directamente con un enemigo.

Ejecutar con:  python main.py   (requiere: pip install pygame)
"""

import math
import random
import sys

import pygame

# ---------------------------------------------------------------------------
# Configuracion
# ---------------------------------------------------------------------------
WIDTH, HEIGHT = 700, 900
FPS = 60
TITLE = "Space Shooter"

PLAYER_VEL = 7
PLAYER_COOLDOWN = 0.16          # segundos entre disparos (mas rapido)

PLAYER_LIVES = 3
PLAYER_SCALE = (60, 60)
BULLET_SPEED = 14
BULLET_SCALE = (6, 16)

ENEMY_BASE_VEL = 1.2            # velocidad inicial de caida (lenta)
ENEMY_MAX_VEL = 4.0
ENEMY_WAVE_DELAY = 2.6          # segundos entre oleadas (mas respiro)
ENEMY_ROWS = 5                  # filas MAXIMAS por oleada (progresivo)
ENEMY_PER_ROW = 7
ENEMY_SCALE = (50, 50)
ENEMY_POINTS = 10

# Marciano (platillo): aparece de vez en cuando, aguanta varios impactos
MARTIAN_HP = 3                    # disparos necesarios para destruirlo
MARTIAN_POINTS = 75               # puntos al destruirlo
MARTIAN_CHANCE = 0.16             # ~1 de cada 5-8 enemigos generados

# Colores
BLACK = (5, 5, 12)
DARK_PURPLE = (18, 10, 40)
NEON_PURPLE = (138, 43, 226)
WHITE = (240, 240, 255)
RED = (255, 50, 50)
ORANGE = (255, 140, 50)
YELLOW = (255, 230, 120)

FONT_NAME = None  # fuente por defecto de pygame


# ---------------------------------------------------------------------------
# Utilidades de dibujo (formas con contorno neón)
# ---------------------------------------------------------------------------
def draw_polygon_outline(surface, color, glow, points, width=2):
    """Dibuja una polilinea cerrada con un halo neon y su contorno."""
    pygame.draw.polygon(surface, glow, points, width + 4)
    pygame.draw.polygon(surface, color, points, width)


# ---------------------------------------------------------------------------
# Clases
# ---------------------------------------------------------------------------
class Player:
    """Nave del jugador, situada en la parte inferior de la pantalla."""

    def __init__(self, game):
        self.game = game
        self.width, self.height = PLAYER_SCALE
        self.x = (WIDTH - self.width) // 2
        self.y = HEIGHT - self.height - 60
        self.speed = PLAYER_VEL
        self.lives = PLAYER_LIVES
        self.cooldown_timer = 0.0
        self.invulnerable = 0.0  # segundos de invulnerabilidad tras perder vida

    def update_position(self, keys):
        """Movimiento 100% manual en 4 direcciones. Se ejecuta cada frame
        desde el while running.

        Flechas / WASD desplazan la nave; sin input permanece quieta.
        Limita horizontal y verticalmente. La zona vertical va desde
        unas 40% de la pantalla hasta justo el borde inferior, para que
        la nave no invada toda la escena.
        """
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            self.x -= self.speed
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            self.x += self.speed
        if keys[pygame.K_UP] or keys[pygame.K_w]:
            self.y -= self.speed
        if keys[pygame.K_DOWN] or keys[pygame.K_s]:
            self.y += self.speed

        self.x = max(0, min(self.x, WIDTH - self.width))
        self.y = max(HEIGHT * 0.4, min(self.y, HEIGHT - self.height))

    def update(self, dt):
        """Temporizadores (no mueve la nave): invulnerabilidad y disparo
        automatico hacia adelante con cooldown fijo."""
        if self.invulnerable > 0:
            self.invulnerable -= dt

        self.cooldown_timer -= dt
        if self.cooldown_timer <= 0:
            self.shoot()
            self.cooldown_timer = PLAYER_COOLDOWN

    def shoot(self):
        bx = self.x + self.width / 2 - BULLET_SCALE[0] / 2
        self.game.bullets.append(Bullet(bx, self.y - 6))

    @property
    def rect(self):
        return pygame.Rect(self.x, self.y, self.width, self.height)

    def hit(self):
        """Devuelve True si el jugador sigue en juego tras el golpe."""
        if self.invulnerable > 0:
            return False  # ignora golpes durante la invulnerabilidad
        self.lives -= 1
        print(f"VIDA PERDIDA -> Vidas ahora: {self.lives}")
        self.invulnerable = 2.0
        return self.lives > 0

    def draw(self, surface):
        # Parpadeo mientras es invulnerable
        if self.invulnerable > 0 and int(self.invulnerable * 8) % 2 == 0:
            return

        cx, cy = self.x + self.width / 2, self.y + self.height / 2
        glow = NEON_PURPLE
        # Cuerpo (triangulo apuntando arriba) + aletas
        points = [
            (cx, self.y + 2),            # punta
            (self.x + 4, self.y + self.height - 4),
            (self.x + self.width / 2, self.y + self.height - 10),
            (self.x + self.width - 4, self.y + self.height - 4),
        ]
        draw_polygon_outline(surface, WHITE, glow, points, 2)
        # Cabina
        cockpit = [(cx, self.y + 14), (cx - 4, self.y + 22), (cx + 4, self.y + 22)]
        draw_polygon_outline(surface, (220, 220, 255), (120, 40, 200), cockpit, 1)


class Bullet:
    """Proyectil que viaja hacia arriba."""

    def __init__(self, x, y):
        self.width, self.height = BULLET_SCALE
        self.x = x
        self.y = y
        self.speed = BULLET_SPEED
        self.alive = True

    def update(self, dt):
        self.y -= self.speed
        if self.y < -self.height:
            self.alive = False

    def draw(self, surface):
        rect = pygame.Rect(self.x, self.y, self.width, self.height)
        pygame.draw.rect(surface, YELLOW, rect.inflate(6, 2))
        pygame.draw.rect(surface, WHITE, rect)

    @property
    def rect(self):
        return pygame.Rect(self.x, self.y, self.width, self.height)


class Enemy:
    """Enemigo triangular invertido que desciende desde arriba."""

    def __init__(self, x, y, vel):
        self.width, self.height = ENEMY_SCALE
        self.x = x
        self.y = y
        self.vel = vel          # velocidad de caida en px/frame
        self.wobble = random.uniform(0, math.tau)
        self.hp = 1             # disparos necesarios para morir
        self.points = ENEMY_POINTS
        self.alive = True

    def update(self, dt):
        # Pequeño balanceo horizontal para dar vida al movimiento
        self.wobble += dt * 3
        sway = math.sin(self.wobble) * 1.2
        self.x += sway
        self.y += self.vel
        if self.y > HEIGHT:
            self.alive = False

    def draw(self, surface):
        cx, cy = self.x + self.width / 2, self.y + self.height / 2
        glow = RED if self.vel < 4.5 else ORANGE
        points = [
            (self.x + 4, self.y + 4),               # esquina sup izq
            (cx, self.y + self.height - 2),         # punta abajo
            (self.x + self.width - 4, self.y + 4),  # esquina sup der
            (cx, self.y + 12),                      # muesca central
        ]
        draw_polygon_outline(surface, glow, (60, 5, 5), points, 2)
        # Ojo central
        pygame.draw.circle(surface, glow, (int(cx), int(self.y + self.height / 2)), 4)

    @property
    def rect(self):
        return pygame.Rect(self.x, self.y, self.width, self.height)


class Martian:
    """Marciano con platillo: mas resistente y valioso que el enemigo normal.

    Se dibuja como una elipse verde (platillo/cupula) con dos ojos.
    Requiere MARTIAN_HP impactos para ser destruido.
    """

    def __init__(self, x, y, vel):
        self.width, self.height = ENEMY_SCALE
        self.x = x
        self.y = y
        self.vel = vel          # velocidad de caida en px/frame
        self.wobble = random.uniform(0, math.tau)
        self.hp = MARTIAN_HP
        self.points = MARTIAN_POINTS
        self.alive = True

    def update(self, dt):
        # Balanceo mas amplio que el enemigo normal
        self.wobble += dt * 3
        sway = math.sin(self.wobble) * 2.2
        self.x += sway
        self.y += self.vel
        # Sale por el fondo sin penalizar al jugador
        if self.y > HEIGHT:
            self.alive = False

    def draw(self, surface):
        cx, cy = self.x + self.width / 2, self.y + self.height / 2
        # Cambia el brillo segun la resistencia restante (pista visual)
        glow = (120, 255, 140) if self.hp > 1 else (255, 190, 70)

        # Cuerpo / plato (elipse ancha)
        body = pygame.Rect(
            int(self.x + 2), int(self.y + 20),
            self.width - 4, self.height - 32,
        )
        body = body.inflate(14, 8)
        pygame.draw.ellipse(surface, (25, 110, 55), body)
        pygame.draw.ellipse(surface, glow, body, 2)

        # Cupula (elipse verde superior)
        dome = pygame.Rect(
            int(self.x + 10), int(self.y + 6),
            self.width - 20, self.height - 36,
        )
        dome = dome.inflate(6, 6)
        pygame.draw.ellipse(surface, (45, 160, 80), dome)
        pygame.draw.ellipse(surface, glow, dome, 2)

        # Ojos
        for side in (-1, 1):
            ex, ey = int(cx + side * 8), int(self.y + 21)
            pygame.draw.circle(surface, WHITE, (ex, ey), 6)
            pygame.draw.circle(surface, (15, 15, 15), (ex + side, ey + 1), 3)

    @property
    def rect(self):
        return pygame.Rect(self.x, self.y, self.width, self.height)


class Game:
    """Clase principal: gestiona la ventana, el bucle de juego y los estados."""

    def __init__(self):
        pygame.init()
        pygame.display.set_caption(TITLE)
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        self.clock = pygame.time.Clock()
        self.font_big = pygame.font.SysFont(FONT_NAME, 64)
        self.font_mid = pygame.font.SysFont(FONT_NAME, 34)
        self.font_small = pygame.font.SysFont(FONT_NAME, 22)

        self.game_loop()  # el bucle inicializa y reinicia el estado

    # -- Estados ------------------------------------------------
    def start_game(self):
        self.player = Player(self)
        self.bullets = []
        self.enemies = []
        self.stars = self.make_stars(80)
        self.planets = self.make_planets(3)
        self.score = 0
        self.wave = 0
        self.elapsed = 0.0
        self.wave_timer = 0.0
        self.game_over = False
        self.enemy_vel = ENEMY_BASE_VEL

    def make_stars(self, n):
        return [
            {"x": random.randint(0, WIDTH),
             "y": random.randint(0, HEIGHT),
             "r": random.choice([1, 1, 2]),
             "phase": random.uniform(0, math.tau),
             "speed": random.uniform(0.4, 1.6)}
            for _ in range(n)
        ]

    def make_planets(self, n):
        return [
            {"x": random.randint(int(WIDTH * 0.12), int(WIDTH * 0.88)),
             "y": random.randint(int(HEIGHT * 0.08), int(HEIGHT * 0.75)),
             "r": random.randint(30, 70),
             "type": random.choice(["planet", "asteroid"])}
            for _ in range(n)
        ]

    # -- Actualizacion ------------------------------------------
    def update(self, dt):
        if self.game_over:
            return

        self.elapsed += dt
        self.update_stars(dt)

        # Dificultad creciente MUY gradual: ~+0.005 px/s de caida por segundo.
        # A los 2 min la velocidad sube solo ~0.6 px/frame.
        self.enemy_vel = min(
            ENEMY_MAX_VEL,
            ENEMY_BASE_VEL + self.elapsed * 0.005
        )

        # Spawn de oleadas: el intervalo baja lentamente y con piso alto
        self.wave_timer -= dt
        if self.wave_timer <= 0:
            self.spawn_wave()
            self.wave_timer = max(1.2, ENEMY_WAVE_DELAY - self.wave * 0.05)
            self.wave += 1

        self.player.update(dt)
        for b in self.bullets:
            b.update(dt)
        for e in self.enemies:
            e.update(dt)

        # Limpieza de elementos fuera de pantalla
        self.bullets = [b for b in self.bullets if b.alive]
        self.enemies = [e for e in self.enemies if e.alive]

        self.check_collisions()

    def update_stars(self, dt):
        for s in self.stars:
            s["phase"] += dt * (2 + s["speed"])
            s["y"] += s["speed"] * 1.5
            if s["y"] > HEIGHT:
                s["y"] = -2
                s["x"] = random.randint(0, WIDTH)

    def spawn_wave(self):
        # Progresion de cantidad: al inicio pocos enemigos, crecen lento.
        # Filas:   oleadas 0-1 -> 2 | 2-3 -> 3 | 4-5 -> 4 | 6+ -> 5
        # Columnas: oleadas 0-1 -> 5 | 2-3 -> 6 | 4+ -> 7
        rows = min(ENEMY_ROWS, 2 + self.wave // 2)
        cols = min(ENEMY_PER_ROW, 5 + self.wave // 2)
        for row in range(rows):
            for col in range(cols):
                x = 10 + col * ((WIDTH - 20) / cols)
                y = -ENEMY_SCALE[1] - row * (ENEMY_SCALE[1] + 14)
                x += random.uniform(-4, 4)
                # Un marciano aparece en lugar de un enemigo normal con
                # probabilidad ~1 de cada 5-8 generados.
                if random.random() < MARTIAN_CHANCE:
                    e = Martian(x, y, self.enemy_vel + row * 0.2)
                else:
                    e = Enemy(x, y, self.enemy_vel + row * 0.2)
                self.enemies.append(e)

    def check_collisions(self):
        # Disparos vs enemigos: cada bala dania a un enemigo; la destruccion
        # solo ocurre cuando su resistencia (hp) llega a 0.
        for b in self.bullets:
            if not b.alive:
                continue
            br = b.rect
            for e in self.enemies:
                if e.alive and br.colliderect(e.rect):
                    b.alive = False
                    e.hp -= 1
                    if e.hp <= 0:
                        e.alive = False
                        self.score += e.points
                        self.play_sound("explosion")
                    else:
                        self.play_sound("hit")
                    break

        # Nave vs enemigos: UNICA condicion de perder vida. Los enemigos
        # que llegan al fondo (ya eliminados en su update) no penalizan.
        pr = self.player.rect
        for e in self.enemies:
            if e.alive and pr.colliderect(e.rect):
                e.alive = False
                print(f"COLISION -> Player rect: {pr} | Enemy rect: {e.rect} | Vidas antes: {self.player.lives}")
                self.play_sound("explosion")
                # Game Over solo tras una colision real (vidas <= 0)
                if not self.player.hit():
                    self.game_over = True
                    self.play_sound("game_over")

    # -- Sonido (opcional, genera tonos si no hay assets) --------
    def play_sound(self, name):
        try:
            if name == "shot":
                sample = self._tone(880, 0.05)
            elif name == "hit":
                sample = self._tone(440, 0.05)
            elif name == "explosion":
                sample = self._tone(110, 0.2)
            else:  # game_over
                sample = self._tone(55, 0.6)
            sample.play()
        except Exception:
            pass  # sin audio en entornos sin dispositivo de sonido

    @staticmethod
    def _tone(freq, duration):
        """Genera un sonido sintetizado sencillo como fallback."""
        from array import array
        pygame.mixer.init()
        rate = 22050
        n = int(rate * duration)
        sound = array(
            "h",
            (int(32767 * 0.5 * math.sin(2 * math.pi * freq * i / rate))
             for i in range(n)),
        )
        return pygame.mixer.Sound(buffer=sound.tobytes())

    # -- Dibujo ------------------------------------------------
    def draw(self):
        self.screen.fill(BLACK)
        self.draw_background()
        self.player.draw(self.screen)
        for b in self.bullets:
            b.draw(self.screen)
        for e in self.enemies:
            e.draw(self.screen)
        self.draw_hud()

        if self.game_over:
            self.draw_game_over()

        pygame.display.flip()

    def draw_background(self):
        # Planeta/asteroide decorativo con contorno neon
        for p in self.planets:
            r = p["r"]
            if p["type"] == "planet":
                color = (30, 20, 60)
                ring = [(int(p["x"] + r), int(p["y"]), 30, 10)]
                pygame.draw.circle(self.screen, color, (p["x"], p["y"]), r)
                pygame.draw.circle(self.screen, NEON_PURPLE, (p["x"], p["y"]), r, 2)
                pygame.draw.ellipse(self.screen, (40, 28, 80), ring[0], 2)
            else:
                color = (24, 24, 46)
                pts = []
                for i in range(8):
                    a = i * math.tau / 8
                    rr = r * random.uniform(0.7, 1.0)
                    pts.append((p["x"] + rr * math.cos(a), p["y"] + rr * math.sin(a)))
                draw_polygon_outline(self.screen, color, (70, 30, 120), pts, 2)

        # Estrellas parpadeantes
        t = self.elapsed
        for s in self.stars:
            brightness = int(80 + 160 * abs(math.sin(s["phase"])))
            pygame.draw.circle(
                self.screen, (brightness, brightness, min(255, brightness + 30)),
                (int(s["x"]), int(s["y"])), s["r"]
            )

    def draw_hud(self):
        score_txt = self.font_small.render(f"Score: {self.score}", True, WHITE)
        self.screen.blit(score_txt, (12, 12))
        lives_txt = self.font_small.render(f"Vidas: {self.player.lives}", True, RED)
        self.screen.blit(lives_txt, (12, 40))
        wave_txt = self.font_small.render(f"Oleada: {self.wave}", True, NEON_PURPLE)
        self.screen.blit(wave_txt, (WIDTH - 120, 12))

    def draw_game_over(self):
        overlay = pygame.Surface((WIDTH, HEIGHT))
        overlay.set_alpha(150)
        overlay.fill(BLACK)
        self.screen.blit(overlay, (0, 0))

        title = self.font_big.render("GAME OVER", True, RED)
        self.screen.blit(title, title.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 60)))

        score = self.font_mid.render(f"Puntuacion: {self.score}", True, WHITE)
        self.screen.blit(score, score.get_rect(center=(WIDTH // 2, HEIGHT // 2)))

        hint = self.font_small.render("Pulsa ESPACIO o R para reiniciar", True, NEON_PURPLE)
        self.screen.blit(hint, hint.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 45)))

    # -- Bucle principal ----------------------------------------
    def game_loop(self):
        self.start_game()
        running = True
        while running:
            dt = self.clock.tick(FPS) / 1000.0

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        running = False
                    elif self.game_over and event.key in (pygame.K_SPACE, pygame.K_r):
                        self.start_game()

            if not self.game_over:
                # Estado REAL del teclado, fuera del for event para que sea
                # continuo mientras la tecla este presionada.
                keys = pygame.key.get_pressed()
                self.player.update_position(keys)

            self.update(dt)
            self.draw()

        pygame.quit()
        sys.exit()


# ---------------------------------------------------------------------------
# Punto de entrada

# ---------------------------------------------------------------------------
if __name__ == "__main__":
    Game()