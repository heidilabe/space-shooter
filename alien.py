"""
Marciano amigable en pixel art.

Personaje extraterrestre pequeno para un juego 2D, inspirado en un
marciano clasico de videojuego. Cada animacion se construye encadenando
la misma CABEZA con bloques de CUERPO diferentes, de modo que las
proporciones, la paleta y el estilo se mantienen identicos en todas las
animaciones (idle, walk, run, jump, attack, hurt).

Los sprites se definen como rejillas de caracteres. Cada caracter es un
pixel de un color de la paleta:
    . transparente
    O verde muy oscuro  (silueta / contorno)
    D verde oscuro      (sombras)
    M verde medio       (color principal)
    L verde claro       (zonas iluminadas)
    X verde brillante   (destellos de luz)
    B negro             (ojos)
    W blanco            (reflejos de los ojos)

Renderer principal:
    render_grid(rows, pixel) -> pygame.Surface
"""

import math

import pygame

# ---------------------------------------------------------------------------
# Paleta
# ---------------------------------------------------------------------------
COLNOR_OUTLINE = (18, 90, 44)
COLNOR_DARK    = (46, 140, 78)
COLNOR_MID     = (84, 186, 106)
COLNOR_LIGHT   = (142, 232, 160)
COLNOR_GLEAM   = (196, 252, 192)
COLNOR_EYE     = (14, 18, 22)
COLNOR_WHITE   = (248, 252, 248)

PALETTE = {
    ".": None,
    "O": COLNOR_OUTLINE,
    "D": COLNOR_DARK,
    "M": COLNOR_MID,
    "L": COLNOR_LIGHT,
    "X": COLNOR_GLEAM,
    "B": COLNOR_EYE,
    "W": COLNOR_WHITE,
}

GRID_W = 17  # pixels de ancho por frame
GRID_H = 32  # pixels de alto por frame


# ---------------------------------------------------------------------------
# Cabeza (identica para todas las animaciones)
# ---------------------------------------------------------------------------
HEAD = [
    "..........L......",  # mechon superior (curvado hacia atras)
    ".........LL......",
    ".......LLL.......",
    "......OLLXLLO....",
    ".....OLLLXLLLO...",
    "....OXLLLLLLLO...",
    "...OMXLLLLLLMO...",
    "..OXMLLLLLLMDO...",
    "..OXMLLLLLLMDO...",
    "..ODBBMMMMMBBO...",  # inicio de los ojos enormes
    "..ODBWBBMBBWBO...",  # reflejo blanco del ojo
    "..ODBBBBMBBBBO...",
    "..ODBBWBMBWBBO...",  # reflejo secundario
    "..ODBBBBMBBBBO...",
    "..ODMBBBMBBMBO...",
    "..ODMMBBMMBBDO...",  # fin de los ojos
    ".....OMMOOMMMO...",  # boca pequena y discreta
    "......OMMMMDO....",
    ".......OMDO......",  # cuello muy delgado
    ".......OMDO......",
]

# Cabeza de la animacion HURT: ojos cerrados apretados y boca abierta
HURT_HEAD = [
    "..........L......",
    ".........LL......",
    ".......LLL.......",
    "......OLLXLLO....",
    ".....OLLLXLLLO...",
    "....OXLLLLLLLO...",
    "...OMXLLLLLLMO...",
    "..OXMLLLLLLMDO...",
    "..OXMLLLLLLMDO...",
    "..ODMMMMMMMMDO...",
    "..ODDBBMMBBDDO...",  # ojos cerrados
    "..ODDBBMMBBDDO...",
    "..ODDMMMMMMDDO...",
    "..ODDMMMMMMDDO...",
    "..ODDMMMMMMDDO...",
    "..ODMMMMMMMMDO...",
    ".....OMMBBBMMO...",  # boca abierta
    "......OMMMMDO....",
    ".......OMDO......",
    ".......OMDO......",
]


# ---------------------------------------------------------------------------
# Cuerpos (12 filas cada uno). La cabeza y el cuello siempre se reutilizan.
# ---------------------------------------------------------------------------
BODY_IDLE = [
    "....OMMLLLMDO....",   # hombros (postura encorvada)
    "..DMODMLLLMDOMD..",
    "..DMODDMMMDDOMD..",
    "..DM.ODDMDDO.MD..",
    "..DM.ODDDDDO.MD..",   # caderas
    "..DM.DM...MD.MD..",   # brazos largos y delgados
    "..DM.DM...MD.MD..",
    "..DM.DM...MD.MD..",
    "..DM.DM...MD.MD..",
    "..DM.DM...MD.MD..",
    "..DMMMD...DMMMD..",   # pies pequenos
    "..LLLMD...DMLLL..",
]

BODY_WALK = [
    "....OMMLLLMDO....",
    "..DMODMLLLMDOMD..",
    "..DMODDMMMDDOMD..",
    "..DM.ODDMDDO.MD..",
    "..DM.ODDDDDO.MD..",
    "..DMDM.....MDMD..",   # zancada: piernas separadas
    "..DMDM.....MDMD..",
    "..DMDM.....MDMD..",
    "..DMDM.....MDMD..",
    "..DMDM.....MDMD..",
    "..DMMMD...DMMMD..",
    "..LLLMD...DMLLL..",
]

# Run: brazos elevados; una pierna extendida y la otra recogida (una zancada).
BODY_RUN = [
    "....OMMLLLMDO....",
    "..DMODMLLLMDOMD..",
    "..DMODDMMMDDOMD..",
    "..DM.ODDMDDO.MD..",
    "..DM.ODDDDDO.MD..",
    ".....DM...MD.....",   # pierna izquierda recogida
    ".....DM...MD.....",
    "....MMD...MD.....",   # pie izquierdo elevado
    "....MMD...MD.....",
    "..........MD.....",   # pierna derecha extendida
    "..........DMM....",
    "..........DML....",
]

# Jump: piernas recogidas bajo el cuerpo, brazos elevados.
BODY_JUMP = [
    "....OMMLLLMDO....",
    "..DMODMLLLMDOMD..",
    "..DMODDMMMDDOMD..",
    "..DM.ODDMDDO.MD..",
    "..DM.ODDDDDO.MD..",
    ".....DM...MD.....",
    ".....DM...MD.....",
    ".....DM...MD.....",
    ".....DM...MD.....",
    "....MMD...DMM....",
    "....LMD...DML....",
    ".................",
]

# Attack: brazos extendidos en horizontal (golpe), piernas en guardia.
BODY_ATTACK = [
    "LMM.OMMLLLMDO.MML",
    "..DMODMLLLMDOMD..",
    "..DMODDMMMDDOMD..",
    "..DM.ODDMDDO.MD..",
    "..DM.ODDDDDO.MD..",
    "..DMDM.....MDMD..",
    "..DMDM.....MDMD..",
    "..DMDM.....MDMD..",
    "..DMDM.....MDMD..",
    "..DMDM.....MDMD..",
    "..DMMMD...DMMMD..",
    "..LLLMD...DMLLL..",
]

# Hurt: cuerpo agachado y encogido.
BODY_HURT = [
    "....OMMLLLMDO....",
    "....ODMLLLMDO....",
    "....ODDMMMDDO....",
    ".....ODDMDDO.....",
    ".....ODDDDDO.....",
    ".....DM...MD.....",
    ".....DM...MD.....",
    ".....DM...MD.....",
    ".....DM...MD.....",
    "....MMD...DMM....",
    "....LMD...DML....",
    ".................",
]

# Brazos elevados durante RUN y JUMP: pican en las filas 18-19 de la cabeza.
ARMS_UP = {
    18: "..DM...OMDO..MD..",
    19: "..DM...OMDO..MD..",
}

# Jump ademas levanta los brazos pegados a los lados de la cabeza.
JUMP_HEAD_OVERRIDES = {
    16: "..DM.OMMOOMMMOMD.",
    17: "..DM..OMMMMDOMD..",
}


# ---------------------------------------------------------------------------
# Rejilla a superficie
# ---------------------------------------------------------------------------
def render_grid(rows, pixel=3):
    """Convierte una rejilla de caracteres en una Surface de pygame.

    El escalado usa rectangulos enteros por pixel, por lo que los bordes
    quedan perfectamente pixelados (sin suavizado).
    """
    width = len(rows[0])
    height = len(rows)
    surf = pygame.Surface((width * pixel, height * pixel), pygame.SRCALPHA)
    for y, row in enumerate(rows):
        for x, ch in enumerate(row):
            color = PALETTE.get(ch)
            if color is not None:
                rect = (x * pixel, y * pixel, pixel, pixel)
                surf.fill(color, rect)
    return surf


def flip_grid(rows):
    """Espeja una rejilla horizontalmente (para alternar zancadas)."""
    return [row[::-1] for row in rows]


def build_frame(head, body, head_overrides=None):
    """Cabeza + cuerpo con override opcional de filas de la cabeza."""
    rows = list(head)
    for i, r in (head_overrides or {}).items():
        rows[i] = r
    rows.extend(body)
    assert all(len(r) == GRID_W for r in rows), "rejilla con ancho invalido"
    assert len(rows) == GRID_H, "rejilla con alto invalido"
    return rows


# ---------------------------------------------------------------------------
# Secuencias de animacion
# ---------------------------------------------------------------------------
# Cada animacion es una lista de frame-dicts con 'grid' y duracion (s) por frame.
def _frame(grid, dur):
    return {"grid": grid, "dur": dur}


def build_animations():
    """Devuelve {nombre: [frames]} listos para usar como personaje jugable."""
    idle_together = build_frame(HEAD, BODY_IDLE)
    idle_bob = build_frame(HEAD, BODY_IDLE)

    walk_step = build_frame(HEAD, BODY_WALK)          # piernas separadas
    walk_close = build_frame(HEAD, BODY_IDLE)         # piernas juntas

    run_a = build_frame(HEAD, BODY_RUN, ARMS_UP)
    run_b = flip_grid(run_a)

    jump = build_frame(HEAD, BODY_JUMP, JUMP_HEAD_OVERRIDES | ARMS_UP)

    attack = build_frame(HEAD, BODY_ATTACK)
    hurt = build_frame(HURT_HEAD, BODY_HURT)

    return {
        "idle": [_frame(idle_together, 0.45), _frame(idle_bob, 0.45)],
        "walk": [
            _frame(walk_step, 0.15),
            _frame(walk_close, 0.15),
        ],
        "run": [_frame(run_a, 0.09), _frame(run_b, 0.09)],
        "jump": [_frame(jump, 0.6)],
        "attack": [_frame(attack, 0.12), _frame(idle_together, 0.18)],
        "hurt": [_frame(hurt, 0.15), _frame(idle_together, 0.25)],
    }


# ---------------------------------------------------------------------------
# Spritesheet PNG (opcional)
# ---------------------------------------------------------------------------
def build_spritesheet(pixel=3, gap=4):
    """Une todas las animaciones en una sola imagen de spritesheet."""
    anims = build_animations()
    cols = max(len(frames) for frames in anims.values())
    frame_w = GRID_W * pixel
    frame_h = GRID_H * pixel

    sheet = pygame.Surface(
        (cols * frame_w + (cols + 1) * gap, len(anims) * frame_h + (len(anims) + 1) * gap),
        pygame.SRCALPHA,
    )
    for r, (name, frames) in enumerate(anims.items()):
        for c, fr in enumerate(frames):
            surf = render_grid(fr["grid"], pixel)
            sheet.blit(surf, (gap + c * (frame_w + gap), gap + r * (frame_h + gap)))
    return sheet


def save_spritesheet(path, pixel=3, gap=4):
    sheet = build_spritesheet(pixel, gap)
    pygame.image.save(sheet, path)
    return path


if __name__ == "__main__":
    # Autocomprobacion: imprime un mapa ASCII del sprite (checkerboard).
    import sys

    print("frames:", list(build_animations().keys()))
    if len(sys.argv) > 1:
        name = sys.argv[1]
        anims = build_animations()
        frame = anims[name][0]["grid"] if name in anims else anims["idle"][0]["grid"]
        print(f"--- {name} / idle ---")
        print("\n".join(frame).lstrip("."))
    else:
        save_spritesheet("alien_spritesheet.png", 3, 4)
        print("spritesheet guardado en alien_spritesheet.png")