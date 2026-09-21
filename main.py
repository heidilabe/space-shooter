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

ENEMY_BASE_VEL = 1.0            # velocidad inicial de caida (esquivable)
ENEMY_MAX_VEL = 2.0             # tope: siguen siendo esquivables al final
ENEMY_WAVE_DELAY = 3.5          # segundos entre oleadas (mas respiro)
ENEMY_ROWS = 2                  # filas MAXIMAS por oleada (muy pocas)
ENEMY_PER_ROW = 3               # meteoritos MAX por fila (dispersos)
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

        cx = self.x + self.width / 2
        glow = NEON_PURPLE

        # Propulsor / llama trasera animada: parpadea cambiando su longitud
        flame_len = self.height * 0.16 + (int(self.game.elapsed * 8) % 2) * 5
        flame_base = self.y + self.height - 8
        flame = [
            (cx - 5, flame_base),
            (cx, flame_base + flame_len),
            (cx + 5, flame_base),
        ]
        pygame.draw.polygon(surface, ORANGE, flame)
        draw_polygon_outline(surface, YELLOW, ORANGE, flame, 1)

        # Alas laterales (triangulos a los costados)
        for side in (-1, 1):
            wing = [
                (cx + side * 8, self.y + 26),
                (cx + side * (self.width / 2 - 2), self.y + self.height - 6),
                (cx + side * 6, self.y + self.height - 6),
            ]
            draw_polygon_outline(surface, WHITE, glow, wing, 2)

        # Cuerpo principal tipo cohete (alargado, con base ancha)
        body = [
            (cx, self.y + 2),
            (cx + 9, self.y + 22),
            (cx + 9, self.y + self.height - 12),
            (cx - 9, self.y + self.height - 12),
            (cx - 9, self.y + 22),
        ]
        pygame.draw.polygon(surface, DARK_PURPLE, body)
        draw_polygon_outline(surface, WHITE, glow, body, 2)

        # Cabina / luz central celeste brillante
        cockpit = pygame.Rect(cx - 6, self.y + 16, 12, 18)
        pygame.draw.ellipse(surface, (140, 220, 255), cockpit)
        pygame.draw.ellipse(surface, (230, 250, 255), cockpit.inflate(-6, -8))
        pygame.draw.circle(surface, (220, 245, 255), (int(cx - 2), int(self.y + 22)), 3)


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
    """Meteorito: roca irregular gris con cráteres y sombreado 3D que gira."""

    def __init__(self, x, y, vel):
        self.width, self.height = ENEMY_SCALE
        self.x = x
        self.y = y
        self.vel = vel
        self.hp = 1
        self.points = ENEMY_POINTS
        self.alive = True

        # 1. FORMA ROCOSA (Más angular y variada)
        n = random.randint(10, 14)  # Más vértices para mayor detalle
        self.shape = []
        for i in range(n):
            angle = i * math.tau / n
            # Variación de radio más agresiva para que no sea redondo
            dist = random.uniform(0.6, 1.1)
            self.shape.append((math.cos(angle) * dist, math.sin(angle) * dist))

        # 2. COLORES (Gris piedra)
        gray_val = random.randint(100, 130)
        self.color_base = (gray_val, gray_val, gray_val + 5)
        self.color_dark = (gray_val - 40, gray_val - 40, gray_val - 35)
        self.color_light = (min(255, gray_val + 40), min(255, gray_val + 40), min(255, gray_val + 50))

        # 3. CRÁTERES (Generados una sola vez)
        self.craters = []
        for _ in range(random.randint(4, 7)):
            # Posición aleatoria dentro de la roca (polares)
            c_ang = random.uniform(0, math.tau)
            c_dist = random.uniform(0.1, 0.6)
            c_rad = random.uniform(2, 6)
            # Guardamos datos para dibujo
            self.craters.append({
                "rel_pos": (math.cos(c_ang) * c_dist, math.sin(c_ang) * c_dist),
                "radius": c_rad,
                "shadow_color": (gray_val - 60, gray_val - 60, gray_val - 55),
                "light_color": (min(255, gray_val + 20), min(255, gray_val + 20), min(255, gray_val + 30))
            })

        self.angle = random.uniform(0, math.tau)
        self.spin = random.choice([-1, 1]) * random.uniform(0.4, 1.2)

    def update(self, dt):
        self.angle += self.spin * dt
        self.y += self.vel
        if self.y > HEIGHT:
            self.alive = False

    def _rotate(self, px, py):
        ca, sa = math.cos(self.angle), math.sin(self.angle)
        return (px * ca - py * sa, px * sa + py * ca)

    def draw(self, surface):
        cx = self.x + self.width / 2
        cy = self.y + self.height / 2
        max_r = min(self.width, self.height) / 2 * 0.95

        # --- DIBUJO DE LA SILUETA ---
        pts = []
        for (sx, sy) in self.shape:
            rx, ry = self._rotate(sx, sy)
            pts.append((cx + rx * max_r, cy + ry * max_r))

        # Sombra proyectada (desplazada un poco a la derecha/abajo)
        shadow_pts = [(p[0] + 3, p[1] + 3) for p in pts]
        pygame.draw.polygon(surface, (15, 15, 25), shadow_pts)

        # Cuerpo base
        pygame.draw.polygon(surface, self.color_base, pts)

        # Borde de luz (Superior-Izquierda) y Sombra (Inferior-Derecha)
        # Dibujamos un contorno sutil
        pygame.draw.polygon(surface, self.color_dark, pts, 2)

        # --- DIBUJO DE CRÁTERES ---
        for c in self.craters:
            # Rotar la posición del cráter
            rx, ry = self._rotate(c["rel_pos"][0], c["rel_pos"][1])
            pos = (int(cx + rx * max_r), int(cy + ry * max_r))

            # Profundidad del cráter (Sombra)
            pygame.draw.circle(surface, c["shadow_color"], pos, int(c["radius"]))
            # Brillo en el borde inferior del cráter (Luz lateral)
            light_pos = (pos[0] + 1, pos[1] + 1)
            pygame.draw.circle(surface, c["light_color"], light_pos, int(c["radius"]), 1)

        # --- DETALLES DE TEXTURA (Puntos de luz aleatorios fijos) ---
        # Usamos la rotación para que las "motas" sigan a la roca
        for i in range(5):
            # Usar i como semilla simple
            tx, ty = self._rotate(math.cos(i) * 0.4, math.sin(i * 2) * 0.4)
            t_pos = (int(cx + tx * max_r), int(cy + ty * max_r))
            pygame.draw.circle(surface, self.color_light, t_pos, 1)

    @property
    def rect(self):
        return pygame.Rect(self.x, self.y, self.width, self.height)


class Martian:
    """Marciano: mas resistente y valioso que el enemigo normal.

    Se dibuja con cabeza en forma de gota invertida, cuerpo pequeño,
    brazos delgados con manos y piernas cortas con pies, todo en tonos
    verdes con sombreado. Requiere MARTIAN_HP impactos para ser destruido.
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
        cx = int(self.x + self.width / 2)
        top = int(self.y + 1)
        # Cambia el brillo segun la resistencia restante (pista visual)
        glow = (120, 255, 140) if self.hp > 1 else (255, 190, 70)

        # Paleta verde con sombreado (oscuro abajo, luz arriba-izquierda)
        green = (70, 175, 95)
        green_dark = (35, 110, 55)
        green_light = (135, 235, 155)
        black_eye = (14, 18, 22)

        # --- CABEZA OVALADA GRANDE (aprox. 50% de la altura total del personaje)
        hx, hy, R = cx, top + 20, 14
        pts = []
        for i in range(7):  # arco superior redondeado
            a = math.pi * i / 6
            pts.append((hx + R * math.cos(a), hy - R * math.sin(a)))
        pts += [
            (hx + 7, hy + 9),
            (hx, hy + 14),   # barbilla redondeada
            (hx - 7, hy + 9),
        ]
        # Sombra proyectada y relleno
        pygame.draw.polygon(surface, green_dark, [(p[0] + 2, p[1] + 2) for p in pts])
        pygame.draw.polygon(surface, green, pts)
        pygame.draw.polygon(surface, glow, pts, 1)
        # Brillo lateral (sombreado del volumen)
        pygame.draw.ellipse(
            surface, green_light,
            pygame.Rect(int(hx - R + 2), int(hy - R + 2), 9, 6),
        )

        # --- OJOS NEGROS GRANDES Y OVALADOS, con reflejo blanco cada uno
        for side in (-1, 1):
            ex = int(hx + side * 8.5 - (4.5 if side < 0 else 0))
            eye = pygame.Rect(ex, int(hy - 6), 9, 13)
            pygame.draw.ellipse(surface, black_eye, eye)
            pygame.draw.circle(surface, WHITE,
                               (ex + 3, int(hy - 3)), 2)

        # --- BOCA pequeña y discreta (sin nariz)
        pygame.draw.line(surface, green_dark,
                         (int(hx - 3), int(hy + 10)),
                         (int(hx + 3), int(hy + 10)), 2)

        # --- CUERPO pequeño y delgado debajo de la barbilla
        by = hy + 16
        body = pygame.Rect(int(cx - 6), int(by), 12, 8)
        pygame.draw.ellipse(surface, green_dark, body.move(1, 1))
        pygame.draw.ellipse(surface, green, body)
        pygame.draw.ellipse(surface, glow, body, 1)

        # --- BRAZOS delgados con manos (a los costados)
        for side in (-1, 1):
            shoulder = (cx + side * 7, by + 1)
            hand = (cx + side * 14, by - 1)
            pygame.draw.line(surface, green_dark,
                             (shoulder[0] + side, shoulder[1] + 1),
                             (hand[0] + side, hand[1] + 1), 2)
            pygame.draw.line(surface, green, shoulder, hand, 2)
            pygame.draw.circle(surface, green_light, hand, 2)
            pygame.draw.circle(surface, glow, hand, 2, 1)

        # --- PIERNAS delgadas con pies pequeños
        for side in (-1, 1):
            hip = (cx + side * 4, by + 6)
            pygame.draw.line(surface, green_dark,
                             (hip[0] + side, hip[1] + 1),
                             (hip[0] + side, hip[1] + 6), 2)
            pygame.draw.line(surface, green, hip, (hip[0], hip[1] + 6), 2)
            foot = pygame.Rect(int(hip[0] - (3 if side < 0 else 0)),
                               int(hip[1] + 4), 7, 4)
            pygame.draw.ellipse(surface, green_dark, foot.move(1, 1))
            pygame.draw.ellipse(surface, green, foot)

    @property
    def rect(self):
        return pygame.Rect(self.x, self.y, self.width, self.height)


class Explosion:
    """Estallido de particulas que se expanden y desvanecen.

    Se crea en el punto del enemigo destruido; cada particula vuela en
    una direccion aleatoria perdiendo velocidad, y el efecto completo
    dura unos ~18 frames antes de ser eliminado.
    """

    LIFETIME = 0.3  # segundos (aprox. 18 frames a 60 FPS)

    # Paletas: enemigo normal (rojo/naranja) vs marciano (verde/blanco)
    PALETTES = {
        False: [(255, 150, 50), (255, 230, 120), (255, 60, 60), (255, 190, 120)],
        True: [(140, 255, 170), (240, 255, 255), (90, 220, 120), (255, 255, 255)],
    }

    def __init__(self, x, y, martian=False):
        self.age = 0.0
        n = 18 if martian else 14
        palette = self.PALETTES[martian]
        self.particles = []
        for _ in range(n):
            angle = random.uniform(0, math.tau)
            speed = random.uniform(1.2, 4.5)
            self.particles.append({
                "x": float(x),
                "y": float(y),
                "vx": math.cos(angle) * speed,
                "vy": math.sin(angle) * speed,
                "r": random.uniform(1.5, 4.0),
                "color": random.choice(palette),
            })

    @property
    def alive(self):
        return self.age < self.LIFETIME

    def update(self, dt):
        self.age += dt
        for p in self.particles:
            p["x"] += p["vx"]
            p["y"] += p["vy"]
            # Frenado con aire para que el estallido se "abra" y pare
            p["vx"] *= 0.96
            p["vy"] *= 0.96

    def draw(self, surface):
        # Alfa de fundido proporcional a la vida restante
        t = 1.0 - self.age / self.LIFETIME
        for p in self.particles:
            r = max(1, int(p["r"] * (0.5 + 0.5 * t)))
            alpha = int(255 * t)
            x, y = int(p["x"]), int(p["y"])
            s = pygame.Surface((r * 2 + 2, r * 2 + 2), pygame.SRCALPHA)
            pygame.draw.circle(s, (*p["color"], alpha), (r + 1, r + 1), r)
            surface.blit(s, (x - r - 1, y - r - 1))


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
        self.explosions = []
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

        # Dificultad creciente POR OLEADA: +0.05 px/frame de caida por oleada.
        # Tarda muchas oleadas en alcanzar el tope; la partida se mantiene
        # jugable durante bastante tiempo.
        self.enemy_vel = min(
            ENEMY_MAX_VEL,
            ENEMY_BASE_VEL + self.wave * 0.05
        )

        # Spawn de oleadas: el intervalo baja lentamente y con piso alto
        self.wave_timer -= dt
        if self.wave_timer <= 0:
            self.spawn_wave()
            self.wave_timer = max(1.6, ENEMY_WAVE_DELAY - self.wave * 0.04)
            self.wave += 1

        self.player.update(dt)
        for b in self.bullets:
            b.update(dt)
        for e in self.enemies:
            e.update(dt)
        for ex in self.explosions:
            ex.update(dt)

        # Limpieza de elementos fuera de pantalla
        self.bullets = [b for b in self.bullets if b.alive]
        self.enemies = [e for e in self.enemies if e.alive]
        self.explosions = [ex for ex in self.explosions if ex.alive]

        self.check_collisions()

    def update_stars(self, dt):
        for s in self.stars:
            s["phase"] += dt * (2 + s["speed"])
            s["y"] += s["speed"] * 1.5
            if s["y"] > HEIGHT:
                s["y"] = -2
                s["x"] = random.randint(0, WIDTH)

    def spawn_wave(self):
        # Progresion muy lenta: pocos enemigos al inicio, crece poco a poco.
        # Por oleada: 0-2 -> 1 | 3-5 -> 2 filas x 2 | 6+ -> max 2x3 (ENEMY_ROWS/ROW)
        count = min(ENEMY_PER_ROW, 1 + self.wave // 3)
        rows = min(ENEMY_ROWS, 1 + self.wave // 3)
        for row in range(rows):
            row_x = []
            for _ in range(count):
                # Disperso en el eje X: huecos amplios y sin superposiciones.
                for _ in range(80):  # reintentos hasta separarlo bien
                    x = random.randint(15, WIDTH - 15 - ENEMY_SCALE[0])
                    if all(abs(x - px) >= 110 for px in row_x):
                        break
                else:
                    x = random.randrange(15, WIDTH - 15 - ENEMY_SCALE[0], 110)
                row_x.append(x)
                y = -ENEMY_SCALE[1] - row * (ENEMY_SCALE[1] + 70)
                # Un marciano aparece en lugar de un meteorito con
                # probabilidad ~1 de cada 5-8 generados.
                vel = self.enemy_vel + row * 0.05
                if random.random() < MARTIAN_CHANCE:
                    e = Martian(x, y, vel)
                else:
                    e = Enemy(x, y, vel)
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
                        self.explosions.append(
                            Explosion(e.x + e.width / 2, e.y + e.height / 2,
                                      isinstance(e, Martian)))
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
                self.explosions.append(
                    Explosion(e.x + e.width / 2, e.y + e.height / 2,
                              isinstance(e, Martian)))
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
        for ex in self.explosions:
            ex.draw(self.screen)
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
    
    