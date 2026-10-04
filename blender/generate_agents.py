"""
VÉRTICE · Agentes · modelado procedural + material PBR único + hitboxes estándar + exportación .glb

Plantilla de 5 agentes (3 mujeres, 2 hombres), todos con la MISMA estatura (1,80 m) y las MISMAS hitboxes:
  MUJERES  valquiria (Duelista,   carmesí #ff4655)  atlética, pelo corto táctico, hombrera derecha, rodilleras
           kage      (Vanguardia, cian    #00f3ff)  ligera, traje ceñido con arnés cruzado, coleta alta, visor monofocal
           nyx       (Iniciadora, menta   #2ec4b6)  capucha táctica, traje técnico medio, brazo izquierdo cibernético
  HOMBRES  aegis     (Centinela,  ámbar   #ffb703)  pesado, hombros anchos, placas balísticas, casco angular cerrado
           vortex    (Controlador, púrpura #7b2cbf) gabardina técnica hasta los muslos, máscara antigás de doble filtro

Uso (sin abrir la interfaz):
    blender --background --python generate_agents.py -- [todos|valquiria|kage|nyx|aegis|vortex] [carpeta_salida]
o con el módulo de Python:  pip install bpy  →  python generate_agents.py [todos|<agente>] [carpeta_salida]
Salida por defecto: ../assets/characters/<agente>.glb

Convenciones (Blender, Z arriba; el exportador glTF las pasa a +Y arriba, que es lo que lee Three.js):
  · Metros. Pivote (0, 0, 0) en la base de los pies. Altura total EXACTA 1,80 m (se normaliza al final).
  · El agente mira a +Y en Blender → -Z en glTF/Three.js (igual que la cámara y los bots del juego).
  · Pose de reposo táctica: fusil compacto en preparado bajo, cañón al frente.
  · Una sola malla `<AGENTE>_Body` con un solo material `M_<Agente>` (Principled BSDF) que lee una paleta
    de N×1 píxeles (color, metal/rugosidad y emisión): cada pieza apunta sus UV a su color → 1 draw call.
  · Hitboxes invisibles obligatorias (mallas sin material, el juego las oculta y usa sus medidas):
      HITBOX_HEAD  esfera de radio 0,12 centrada a 1,65 m
      HITBOX_BODY  caja 0,38 (ancho) × 0,65 (alto) × 0,38 (fondo) centrada a 1,15 m
      HITBOX_LEGS  caja 0,30 (ancho) × 0,75 (alto) × 0,30 (fondo) centrada a 0,45 m
    El fondo es igual al ancho: así la caja no depende del giro del agente (el juego usa AABB).
  · Vacío `Muzzle_Point` en la boca del fusil: de ahí salen trazadoras y fogonazo.
  · Presupuesto: 4.500-6.000 triángulos por agente (el script falla si se sale).
"""
import bpy, bmesh, math, os, sys
from mathutils import Matrix, Vector

ARGS = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else sys.argv[1:]
ALL = ['valquiria', 'kage', 'nyx', 'aegis', 'vortex']
PICK = [a for a in ARGS if a in ALL] or ALL
OUT_DIR = next((a for a in ARGS if a not in ALL and a != 'todos'), None)
OUT_DIR = os.path.abspath(OUT_DIR or os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'assets', 'characters'))

HEIGHT = 1.80
TRI_MIN, TRI_MAX = 4500, 6000
MUZZLE = (0.06, 0.84, 1.35)          # = (0.06, 1.35, -0.84) en Three.js: el mismo punto que usan los bots
HITBOX = {                            # (centro z, ancho, alto) · la cabeza es (centro z, radio)
    'HEAD': (1.65, 0.12),
    'BODY': (1.15, 0.38, 0.65),
    'LEGS': (0.45, 0.30, 0.75),
}

# ------------------------------------------------------------------------------------------------ paletas
# Celdas: 0 piel · 1 traje principal · 2 traje secundario · 3 equipo/blindaje · 4 metal · 5 acento (pintura)
#         6 pelo · 7 botas/goma · 8 fusil · 9 acento luminoso (visor, lentes, interfaz)
def hexrgb(h):
    h = h.lstrip('#'); return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))

def palette(skin, suit, suit2, gear, metal, accent, hair, gear_metal=0.15, suit_rough=0.8):
    a = hexrgb(accent)
    #        color          metal       rugosidad   emisión
    return [(hexrgb(skin),  0.00,       0.65,       (0, 0, 0)),
            (hexrgb(suit),  0.05,       suit_rough, (0, 0, 0)),
            (hexrgb(suit2), 0.05,       0.75,       (0, 0, 0)),
            (hexrgb(gear),  gear_metal, 0.55,       (0, 0, 0)),
            (hexrgb(metal), 0.85,       0.32,       (0, 0, 0)),
            (a,             0.10,       0.50,       (0, 0, 0)),
            (hexrgb(hair),  0.00,       0.70,       (0, 0, 0)),
            ((0x14, 0x15, 0x18), 0.00,  0.90,       (0, 0, 0)),
            ((0x1c, 0x1f, 0x23), 0.35,  0.55,       (0, 0, 0)),
            (a,             0.00,       0.20,       tuple(int(c * 0.85) for c in a))]

AGENTS = {
    'valquiria': dict(role='Duelista', sex='F', accent='#ff4655',
                      pal=palette('#c98e6c', '#24272d', '#3a3f47', '#4a4f57', '#8d949c', '#ff4655', '#2a1a14')),
    'kage':      dict(role='Vanguardia', sex='F', accent='#00f3ff',
                      pal=palette('#e2b896', '#151a22', '#232b36', '#2c3340', '#9aa3ad', '#00f3ff', '#101216', suit_rough=0.45)),
    'nyx':       dict(role='Iniciadora', sex='F', accent='#2ec4b6',
                      pal=palette('#8a5a40', '#2b3236', '#3c464b', '#4b565c', '#b7c0c6', '#2ec4b6', '#e8e4dc')),
    'aegis':     dict(role='Centinela', sex='M', accent='#ffb703',
                      pal=palette('#a26f52', '#2f3329', '#454b3c', '#5d6352', '#7d838a', '#ffb703', '#1a1714', gear_metal=0.35)),
    'vortex':    dict(role='Controlador', sex='M', accent='#7b2cbf',
                      pal=palette('#d2a17f', '#221d2b', '#353042', '#2a2d33', '#8f96a0', '#7b2cbf', '#17141c')),
}
SKIN, SUIT, SUIT2, GEAR, METAL, ACC, HAIR, BOOT, GUN, GLOW = range(10)


# ------------------------------------------------------------------------------------------------ geometría
class Builder:
    """Acumula vértices y caras de todas las piezas; al final crea UNA malla con UV a la celda de cada pieza."""
    def __init__(self):
        self.v, self.f, self.cell, self.smooth = [], [], [], []

    def add(self, verts, faces, cell, smooth=True, m=None):
        o = len(self.v)
        for p in verts:
            p = Vector(p)
            self.v.append(tuple(m @ p) if m is not None else tuple(p))
        for fc in faces:
            self.f.append([i + o for i in fc]); self.cell.append(cell); self.smooth.append(smooth)

    def add_bm(self, bm, cell, smooth=True, m=None):
        bm.verts.index_update()
        self.add([v.co.copy() for v in bm.verts], [[v.index for v in f.verts] for f in bm.faces], cell, smooth, m)
        bm.free()

    def mirror_x(self, fn):
        """Ejecuta fn(sx) para el lado derecho (+1) y el izquierdo (-1)."""
        fn(1); fn(-1)


def rot(rx=0, ry=0, rz=0):
    return (Matrix.Rotation(math.radians(rz), 4, 'Z') @ Matrix.Rotation(math.radians(ry), 4, 'Y')
            @ Matrix.Rotation(math.radians(rx), 4, 'X'))


def box(B, c, s, cell, r=(0, 0, 0), bevel=0.0, smooth=False):
    """Caja de tamaño s=(x, y, z) centrada en c, con giro r (grados) y bisel opcional."""
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, vec=Vector(s), verts=bm.verts)
    if bevel > 0:
        bmesh.ops.bevel(bm, geom=list(bm.edges), offset=bevel, segments=1, affect='EDGES', profile=0.5)
    B.add_bm(bm, cell, smooth, Matrix.Translation(Vector(c)) @ rot(*r))


def ellipsoid(B, c, r, cell, nu=12, nv=8, keep=None, r_=(0, 0, 0), smooth=True, inner=0.0):
    """Elipsoide (UV). keep(x, y, z) en coordenadas locales normalizadas decide qué vértices se quedan
    (para cortes: capucha, pelo, hombrera). inner > 0 añade la cara interior (normales invertidas)."""
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=nu, v_segments=nv, radius=1.0)
    if keep:
        bmesh.ops.delete(bm, geom=[v for v in bm.verts if not keep(v.co.x, v.co.y, v.co.z)], context='VERTS')
    if inner > 0:
        dup = bmesh.ops.duplicate(bm, geom=list(bm.verts) + list(bm.edges) + list(bm.faces))
        dverts = [g for g in dup['geom'] if isinstance(g, bmesh.types.BMVert)]
        dfaces = [g for g in dup['geom'] if isinstance(g, bmesh.types.BMFace)]
        for v in dverts: v.co *= (1.0 - inner)
        bmesh.ops.reverse_faces(bm, faces=dfaces)
    bmesh.ops.scale(bm, vec=Vector(r), verts=bm.verts)
    B.add_bm(bm, cell, smooth, Matrix.Translation(Vector(c)) @ rot(*r_))


def ring(center, tangent, rx, ry, seg, power=2.0, roll_up=Vector((0, 0, 1))):
    """Anillo superelíptico perpendicular a `tangent`."""
    t = Vector(tangent).normalized()
    up = roll_up if abs(t.dot(roll_up)) < 0.95 else Vector((0, 1, 0))
    a = t.cross(up).normalized(); b = a.cross(t).normalized()
    pts = []
    for i in range(seg):
        ang = 2 * math.pi * i / seg
        ca, sa = math.cos(ang), math.sin(ang)
        x = math.copysign(abs(ca) ** (2 / power), ca) * rx
        y = math.copysign(abs(sa) ** (2 / power), sa) * ry
        pts.append(Vector(center) + a * x + b * y)
    return pts


def loft(B, rings, cell, cap0=True, cap1=True, smooth=True):
    """Une anillos con el mismo nº de vértices (tubos, torsos, gabardinas)."""
    seg = len(rings[0]); verts, faces = [], []
    for r in rings: verts += r
    for k in range(len(rings) - 1):
        for i in range(seg):
            a, b = k * seg + i, k * seg + (i + 1) % seg
            faces.append([a, a + seg, b + seg, b])                # normales hacia fuera
    if cap0: faces.append(list(range(seg)))
    if cap1: faces.append([(len(rings) - 1) * seg + i for i in range(seg)][::-1])
    B.add(verts, faces, cell, smooth)


def body_loft(B, stations, cell, seg=16, power=2.4, cap0=True, cap1=True, smooth=True):
    """Tronco: estaciones (z, semiancho, semifondo, desplazamiento y) apiladas en vertical."""
    rings = []
    for z, rx, ry, oy in stations:
        rings.append(ring((0, oy, z), (0, 0, 1), rx, ry, seg, power, roll_up=Vector((0, 1, 0))))
    loft(B, rings, cell, cap0, cap1, smooth)


def tube(B, pts, radii, cell, seg=10, cap0=True, cap1=True, smooth=True, power=2.0, ry_scale=1.0):
    """Tubo por una cadena de puntos con radio por punto (brazos, piernas, coleta, filtros)."""
    pts = [Vector(p) for p in pts]; rings = []
    for i, p in enumerate(pts):
        if i == 0: t = pts[1] - pts[0]
        elif i == len(pts) - 1: t = pts[-1] - pts[-2]
        else: t = (pts[i + 1] - pts[i]).normalized() + (pts[i] - pts[i - 1]).normalized()
        rings.append(ring(p, t, radii[i], radii[i] * ry_scale, seg, power))
    loft(B, rings, cell, cap0, cap1, smooth)


def joint(B, c, r, cell, nu=10, nv=6):
    ellipsoid(B, c, (r, r, r), cell, nu, nv)


# ------------------------------------------------------------------------------------------------ cuerpo base
def build_agent(name, spec):
    B = Builder()
    F = spec['sex'] == 'F'
    heavy = name == 'aegis'
    lean = name == 'kage'

    # ---------------- tronco (pelvis → hombros) ----------------
    if F:
        hip_w, waist_w, chest_w, sh_w = (0.165, 0.12, 0.15, 0.165) if not lean else (0.158, 0.112, 0.142, 0.156)
    else:
        hip_w, waist_w, chest_w, sh_w = (0.165, 0.155, 0.195, 0.215) if not heavy else (0.175, 0.17, 0.215, 0.235)
    torso_cell = SUIT
    body_loft(B, [
        (0.80, hip_w * 0.80, 0.090, 0.0),
        (0.86, hip_w,        0.105, 0.0),
        (0.95, hip_w * 1.01, 0.110, 0.0),
        (1.04, waist_w,      0.092, 0.005),
        (1.13, waist_w * 1.04, 0.096, 0.008),
        (1.22, chest_w * 0.98, 0.108 if not F else 0.112, 0.010),
        (1.30, chest_w,      0.112 if not F else 0.118, 0.012),
        (1.37, chest_w * 1.02, 0.106, 0.008),
        (1.43, sh_w,         0.095, 0.0),
        (1.48, sh_w * 0.72,  0.080, -0.005),
        (1.51, 0.075,        0.060, -0.005),
    ], torso_cell, seg=24, power=2.3)
    # entrepierna (une las piernas al tronco)
    ellipsoid(B, (0, 0, 0.81), (hip_w * 0.72, 0.095, 0.07), torso_cell, 14, 8)
    # cuello y cabeza
    tube(B, [(0, -0.005, 1.48), (0, 0.0, 1.57)], [0.052 if F else 0.062, 0.046 if F else 0.055], SKIN, seg=12)
    head_c = (0, 0.012, 1.655)
    head_r = (0.088 if F else 0.094, 0.104, 0.112)
    ellipsoid(B, head_c, head_r, SKIN, 24, 16)
    # nariz y orejas (rasgos mínimos que leen de lejos)
    ellipsoid(B, (0, 0.112, 1.645), (0.014, 0.022, 0.024), SKIN, 8, 6)
    B.mirror_x(lambda sx: ellipsoid(B, (sx * (head_r[0] - 0.004), 0.0, 1.652), (0.012, 0.022, 0.03), SKIN, 8, 6))
    # ojos y cejas (debajo de cascos, máscaras y visores quedan tapados)
    B.mirror_x(lambda sx: ellipsoid(B, (sx * 0.032, 0.1, 1.672), (0.014, 0.008, 0.008), BOOT, 8, 4))
    B.mirror_x(lambda sx: box(B, (sx * 0.034, 0.104, 1.694), (0.03, 0.01, 0.007), HAIR, r=(0, sx * -8, 0)))
    # cinturón táctico con hebilla del color del agente
    body_loft(B, [(0.925, hip_w * 1.035, 0.115, 0.0), (0.975, hip_w * 1.03, 0.114, 0.0)], BOOT, seg=20, power=2.3, cap0=False, cap1=False, smooth=False)
    box(B, (0, 0.118, 0.95), (0.06, 0.012, 0.04), ACC, bevel=0.004)
    B.mirror_x(lambda sx: box(B, (sx * 0.13, 0.06, 0.94), (0.05, 0.05, 0.07), GEAR, bevel=0.008, r=(0, 0, sx * 25)))   # cartucheras

    # ---------------- piernas (posición abierta, rodilla algo flexionada) ----------------
    thigh_r = 0.078 if F else 0.085
    if heavy: thigh_r = 0.092
    def leg(sx):
        hip = (sx * 0.09, 0.0, 0.86); knee = (sx * 0.115, 0.03, 0.49); ankle = (sx * 0.125, -0.005, 0.10)
        tube(B, [hip, ((hip[0] + knee[0]) / 2, 0.015, 0.68), knee], [thigh_r, thigh_r * 0.86, thigh_r * 0.66], SUIT2 if name != 'kage' else SUIT, seg=12)
        joint(B, knee, thigh_r * 0.66, SUIT2 if name != 'kage' else SUIT, 10, 6)
        tube(B, [knee, (sx * 0.12, 0.02, 0.30), ankle], [thigh_r * 0.64, thigh_r * 0.6, thigh_r * 0.45], SUIT2 if name != 'kage' else SUIT, seg=12)
        # bota: caña + pie biselado
        tube(B, [(sx * 0.125, -0.005, 0.07), (sx * 0.125, 0.0, 0.22)], [0.058, 0.055], BOOT, seg=12)
        box(B, (sx * 0.126, 0.045, 0.045), (0.105, 0.27, 0.09), BOOT, bevel=0.02)
        box(B, (sx * 0.126, 0.04, 0.006), (0.11, 0.285, 0.012), GEAR)          # suela
    B.mirror_x(leg)

    # ---------------- brazos con el fusil en preparado ----------------
    upper_r = 0.048 if F else 0.056
    if heavy: upper_r = 0.062
    arm_cell = SUIT
    def arm(side):
        # side +1 derecho (mano en la empuñadura), -1 izquierdo (mano en el guardamanos)
        sx = side
        shoulder = Vector((sx * (sh_w + 0.01), -0.005, 1.425))
        if side > 0: elbow, wrist, hand = Vector((0.22, 0.08, 1.16)), Vector((0.13, 0.23, 1.255)), Vector((0.105, 0.26, 1.265))
        else:        elbow, wrist, hand = Vector((-0.17, 0.30, 1.17)), Vector((-0.02, 0.50, 1.28)), Vector((0.02, 0.54, 1.29))
        cyber = name == 'nyx' and side < 0
        cell_u = METAL if cyber else arm_cell
        joint(B, shoulder, upper_r * 1.18, cell_u, 12, 8)
        tube(B, [shoulder, shoulder.lerp(elbow, 0.5), elbow], [upper_r, upper_r * 0.95, upper_r * 0.82], cell_u, seg=12)
        joint(B, elbow, upper_r * 0.84, METAL if cyber else arm_cell, 10, 6)
        tube(B, [elbow, elbow.lerp(wrist, 0.5), wrist], [upper_r * 0.8, upper_r * 0.78, upper_r * 0.6], cell_u if not cyber else METAL, seg=12)
        # mano (guante) orientada hacia el fusil
        d = (hand - wrist).normalized()
        yaw = math.degrees(math.atan2(-d.x, d.y))
        box(B, tuple(hand), (0.06, 0.09, 0.05), BOOT if not cyber else METAL, r=(0, 0, yaw), bevel=0.012)
        if cyber:
            # brazo cibernético: anillos luminosos, placas y la interfaz del antebrazo
            for k in (0.25, 0.55, 0.8):
                p = shoulder.lerp(elbow, k)
                tube(B, [p - (elbow - shoulder).normalized() * 0.008, p + (elbow - shoulder).normalized() * 0.008],
                     [upper_r * 1.06, upper_r * 1.06], GLOW, seg=12, smooth=False)
            for k in (0.3, 0.7):
                p = elbow.lerp(wrist, k)
                tube(B, [p - (wrist - elbow).normalized() * 0.006, p + (wrist - elbow).normalized() * 0.006],
                     [upper_r * 0.86, upper_r * 0.86], GLOW, seg=12, smooth=False)
            mid = elbow.lerp(wrist, 0.5); fd = (wrist - elbow).normalized()
            fy = math.degrees(math.atan2(-fd.x, fd.y)); fp = math.degrees(math.asin(max(-1, min(1, fd.z))))
            box(B, tuple(mid + Vector((-0.035, 0, 0.03))), (0.05, 0.11, 0.012), GLOW, r=(fp, -20, fy), bevel=0.003)   # pantalla
            box(B, tuple(mid + Vector((-0.03, 0, 0.022))), (0.062, 0.13, 0.016), GEAR, r=(fp, -20, fy), bevel=0.004)  # marco
            ellipsoid(B, tuple(shoulder + Vector((-0.01, 0, 0.03))), (upper_r * 1.5, upper_r * 1.35, upper_r * 1.0), METAL, 12, 6,
                      keep=lambda x, y, z: z > -0.2)
    B.mirror_x(arm)

    # ---------------- fusil compacto (igual en los 5: mismas medidas y misma boca) ----------------
    gx = 0.075
    box(B, (gx, 0.04, 1.305), (0.04, 0.16, 0.075), GUN, r=(-4, 0, 0), bevel=0.008)          # culata
    box(B, (gx, 0.26, 1.325), (0.05, 0.30, 0.08), GUN, bevel=0.008)                          # cajón
    box(B, (gx, 0.52, 1.335), (0.052, 0.24, 0.062), GEAR, bevel=0.01)                        # guardamanos
    box(B, (gx, 0.34, 1.235), (0.034, 0.06, 0.13), GUN, r=(14, 0, 0), bevel=0.006)          # cargador
    box(B, (gx, 0.22, 1.255), (0.032, 0.045, 0.09), GUN, r=(-18, 0, 0), bevel=0.006)        # empuñadura
    box(B, (gx, 0.27, 1.385), (0.034, 0.09, 0.04), GUN, bevel=0.006)                         # mira holográfica
    box(B, (gx, 0.316, 1.39), (0.026, 0.004, 0.026), GLOW)                                   # cristal de la mira
    tube(B, [(MUZZLE[0] + 0.0, 0.62, 1.338), (MUZZLE[0], MUZZLE[1] - 0.05, 1.338)], [0.012, 0.012], METAL, seg=10, smooth=False)
    tube(B, [(MUZZLE[0], MUZZLE[1] - 0.06, 1.338), (MUZZLE[0], MUZZLE[1], 1.338)], [0.018, 0.018], GUN, seg=10, smooth=False)
    box(B, (gx + 0.028, 0.30, 1.33), (0.006, 0.12, 0.012), ACC)                              # franja del agente en el cajón

    # ---------------- rasgos de cada agente ----------------
    globals()['dress_' + name](B, head_c, head_r, sh_w, chest_w, waist_w, hip_w, upper_r)
    return B


# ------------------------------------------------------------------------------------------------ agentes
def face_band(B, head_c, head_r, cell, z0, z1, keep_front=True):
    """Visera/gafas: casquete del elipsoide de la cabeza entre z0 y z1 en la mitad frontal."""
    def keep(x, y, z):
        zz = head_c[2] + z * head_r[2] * 1.06
        return z0 <= zz <= z1 and (y > 0.05 if keep_front else True)
    ellipsoid(B, head_c, (head_r[0] * 1.06, head_r[1] * 1.06, head_r[2] * 1.06), cell, 20, 16, keep=keep, smooth=True)


def dress_valquiria(B, hc, hr, sh_w, chest_w, waist_w, hip_w, ur):
    # pelo corto táctico: casquete por encima de las orejas, algo más largo arriba (volumen hacia delante)
    ellipsoid(B, (hc[0], hc[1] - 0.006, hc[2] + 0.012), (hr[0] * 1.1, hr[1] * 1.1, hr[2] * 1.08), HAIR, 18, 12,
              keep=lambda x, y, z: z > (-0.05 if y < 0.2 else 0.32) or (y < -0.3 and z > -0.55))
    ellipsoid(B, (0.0, 0.07, hc[2] + 0.085), (0.075, 0.06, 0.03), HAIR, 10, 6, r_=(-25, 0, 0))   # flequillo levantado
    # chaleco ligero con franja carmesí
    body_loft(B, [(1.08, chest_w * 0.98, 0.112, 0.012), (1.20, chest_w * 1.02, 0.124, 0.016), (1.33, chest_w * 1.06, 0.13, 0.016),
                  (1.40, chest_w * 1.02, 0.118, 0.01)], GEAR, seg=20, power=2.6, smooth=False)
    box(B, (0, 0.135, 1.245), (0.035, 0.012, 0.2), ACC)
    # hombrera derecha reforzada: tres láminas superpuestas y borde carmesí
    sp = (sh_w + 0.02, -0.005, 1.44)
    ellipsoid(B, sp, (0.095, 0.09, 0.07), GEAR, 14, 8, keep=lambda x, y, z: z > -0.15, r_=(0, 18, 0), smooth=False)
    ellipsoid(B, (sp[0] + 0.02, sp[1], sp[2] - 0.045), (0.085, 0.085, 0.05), METAL, 14, 6, keep=lambda x, y, z: z > -0.1, r_=(0, 30, 0), smooth=False)
    ellipsoid(B, (sp[0] + 0.035, sp[1], sp[2] - 0.08), (0.075, 0.08, 0.04), ACC, 14, 6, keep=lambda x, y, z: z > -0.1, r_=(0, 42, 0), smooth=False)
    # rodilleras reforzadas
    B.mirror_x(lambda sx: (box(B, (sx * 0.117, 0.095, 0.50), (0.1, 0.05, 0.12), GEAR, r=(8, 0, 0), bevel=0.018),
                           box(B, (sx * 0.117, 0.122, 0.505), (0.07, 0.01, 0.025), ACC, r=(8, 0, 0))))
    # coderas
    B.mirror_x(lambda sx: joint(B, (0.22 if sx > 0 else -0.17, 0.08 if sx > 0 else 0.30, 1.16 if sx > 0 else 1.17), ur * 0.95, GEAR, 10, 6))


def dress_kage(B, hc, hr, sh_w, chest_w, waist_w, hip_w, ur):
    # pelo recogido y ceñido + coleta alta (cadena de anillos que cae por la espalda)
    ellipsoid(B, (hc[0], hc[1] - 0.008, hc[2] + 0.008), (hr[0] * 1.07, hr[1] * 1.07, hr[2] * 1.05), HAIR, 18, 12,
              keep=lambda x, y, z: z > 0.05 or y < -0.35)
    tube(B, [(0, -0.07, 1.765), (0, -0.115, 1.785), (0, -0.165, 1.74), (0, -0.19, 1.64), (0, -0.18, 1.53), (0, -0.16, 1.44)],
         [0.03, 0.04, 0.042, 0.034, 0.022, 0.006], HAIR, seg=10)
    tube(B, [(0, -0.07, 1.762), (0, -0.09, 1.775)], [0.034, 0.034], ACC, seg=10, smooth=False)          # coletero
    # visor monofocal: una sola lente sobre el ojo derecho con soporte a la sien
    ellipsoid(B, (0.038, 0.098, 1.665), (0.03, 0.012, 0.024), GLOW, 12, 6)
    tube(B, [(0.038, 0.088, 1.665), (0.038, 0.1, 1.665)], [0.034, 0.034], GEAR, seg=12, smooth=False)
    box(B, (0.075, 0.05, 1.67), (0.012, 0.09, 0.016), GEAR, r=(0, 0, -25), bevel=0.003)
    tube(B, [(hr[0] + 0.0, -0.01, 1.67), (hr[0] + 0.004, 0.04, 1.672)], [0.016, 0.016], METAL, seg=10, smooth=False)
    # arnés cruzado: dos cintas en X por delante y por detrás + anilla central luminosa
    for side in (1, -1):
        for yy in (0.118, -0.098):
            box(B, (0, yy, 1.26), (0.03, 0.012, 0.42), GEAR, r=(0, side * 33, 0))
    ellipsoid(B, (0, 0.128, 1.26), (0.03, 0.012, 0.03), GLOW, 12, 6)
    # tiras del traje ceñido (líneas cian que marcan la silueta)
    B.mirror_x(lambda sx: box(B, (sx * waist_w * 0.95, 0.03, 1.1), (0.01, 0.03, 0.3), ACC, r=(0, sx * -5, 0)))
    B.mirror_x(lambda sx: box(B, (sx * 0.125, 0.07, 0.30), (0.02, 0.012, 0.32), ACC))                      # espinilleras
    # mochila plana de vanguardia
    box(B, (0, -0.13, 1.24), (0.2, 0.06, 0.26), GEAR, bevel=0.02)


def dress_nyx(B, hc, hr, sh_w, chest_w, waist_w, hip_w, ur):
    # capucha táctica: concha gruesa abierta por delante + cuello cerrado que cae a los hombros
    def hood_keep(x, y, z):
        face = y > 0.2 and -0.62 < z < 0.75 and abs(x) < 0.8
        return not face and z > -0.85
    ellipsoid(B, (hc[0], hc[1] - 0.015, hc[2] + 0.01), (hr[0] * 1.32, hr[1] * 1.3, hr[2] * 1.22), SUIT2, 20, 14, keep=hood_keep, inner=0.1)
    tube(B, [(0, -0.005, 1.46), (0, 0.0, 1.54)], [sh_w * 0.68, 0.085], SUIT2, seg=20, cap0=False, cap1=False)
    # mechón claro asomando bajo la capucha
    ellipsoid(B, (0.03, 0.085, hc[2] + 0.06), (0.055, 0.03, 0.035), HAIR, 10, 6, r_=(0, -20, 0))
    # línea de interfaz en la frente de la capucha
    box(B, (0, 0.118, hc[2] + 0.1), (0.09, 0.008, 0.008), GLOW, r=(-35, 0, 0))
    # chaqueta técnica media hasta la cadera, cremallera y panel menta
    body_loft(B, [(0.84, hip_w * 1.08, 0.122, 0.0), (0.95, hip_w * 1.08, 0.125, 0.0), (1.06, waist_w * 1.12, 0.108, 0.006),
                  (1.20, chest_w * 1.08, 0.122, 0.012), (1.33, chest_w * 1.08, 0.128, 0.014), (1.42, sh_w * 1.04, 0.108, 0.0)],
              SUIT, seg=20, power=2.3, cap0=False, cap1=False)
    box(B, (0.0, 0.13, 1.14), (0.012, 0.01, 0.56), METAL)
    box(B, (0.075, 0.133, 1.27), (0.05, 0.01, 0.07), ACC, r=(0, 0, 0))
    # sensor de reconocimiento en la cadera derecha (iniciadora)
    tube(B, [(0.19, 0.0, 0.92), (0.19, 0.0, 1.0)], [0.035, 0.035], GEAR, seg=10, smooth=False)
    ellipsoid(B, (0.19, 0.0, 1.005), (0.03, 0.03, 0.015), GLOW, 10, 6)


def dress_aegis(B, hc, hr, sh_w, chest_w, waist_w, hip_w, ur):
    # casco angular cerrado: octógono facetado que cubre toda la cabeza + visera rasgada ámbar
    rings = []
    for z, sx, sy, oy in [(1.535, 0.085, 0.1, 0.0), (1.56, 0.112, 0.128, 0.012), (1.64, 0.122, 0.138, 0.016),
                          (1.72, 0.118, 0.13, 0.008), (1.77, 0.09, 0.105, 0.0), (1.80, 0.05, 0.062, -0.006)]:
        rings.append(ring((0, oy, z), (0, 0, 1), sx, sy, 8, power=1.35, roll_up=Vector((0, 1, 0))))
    loft(B, rings, GEAR, smooth=False)
    box(B, (0, 0.146, 1.668), (0.15, 0.02, 0.022), GLOW, bevel=0.004)                     # visera
    box(B, (0, 0.152, 1.6), (0.07, 0.03, 0.06), METAL, r=(10, 0, 0), bevel=0.01)          # mentonera
    B.mirror_x(lambda sx: box(B, (sx * 0.12, 0.02, 1.66), (0.03, 0.12, 0.08), METAL, bevel=0.01))       # orejeras
    box(B, (0, -0.04, 1.81), (0.03, 0.14, 0.02), ACC, bevel=0.004)                         # cresta
    # placas balísticas torácicas (frontal y dorsal) + placas laterales y abdominales
    box(B, (0, 0.13, 1.27), (0.36, 0.06, 0.32), GEAR, bevel=0.02)
    box(B, (0, 0.165, 1.31), (0.22, 0.02, 0.16), METAL, bevel=0.01)
    box(B, (0, 0.178, 1.31), (0.14, 0.006, 0.02), ACC)
    box(B, (0, -0.12, 1.27), (0.36, 0.06, 0.32), GEAR, bevel=0.02)
    B.mirror_x(lambda sx: box(B, (sx * 0.2, 0.0, 1.2), (0.05, 0.2, 0.2), GEAR, bevel=0.015))
    for k, z in enumerate((1.07, 0.99)):
        box(B, (0, 0.122 - k * 0.004, z), (0.24 - k * 0.02, 0.05, 0.07), GEAR, bevel=0.012)
    # hombreras pesadas (hombros anchos: la silueta del centinela)
    def pad(sx):
        box(B, (sx * (sh_w + 0.05), 0.0, 1.46), (0.15, 0.2, 0.06), GEAR, r=(0, sx * 22, 0), bevel=0.02)
        box(B, (sx * (sh_w + 0.08), 0.0, 1.405), (0.12, 0.18, 0.05), METAL, r=(0, sx * 38, 0), bevel=0.015)
        box(B, (sx * (sh_w + 0.105), 0.0, 1.395), (0.012, 0.16, 0.035), ACC, r=(0, sx * 38, 0))
    B.mirror_x(pad)
    # placas de muslo y rodilleras
    B.mirror_x(lambda sx: (box(B, (sx * 0.11, 0.1, 0.68), (0.13, 0.04, 0.2), GEAR, r=(-4, 0, 0), bevel=0.015),
                           box(B, (sx * 0.117, 0.1, 0.5), (0.12, 0.06, 0.13), METAL, r=(6, 0, 0), bevel=0.02),
                           box(B, (sx * 0.125, 0.07, 0.28), (0.1, 0.04, 0.2), GEAR, bevel=0.015)))


def dress_vortex(B, hc, hr, sh_w, chest_w, waist_w, hip_w, ur):
    # pelo corto peinado hacia atrás
    ellipsoid(B, (hc[0], hc[1] - 0.012, hc[2] + 0.012), (hr[0] * 1.08, hr[1] * 1.08, hr[2] * 1.06), HAIR, 18, 12,
              keep=lambda x, y, z: z > (0.05 if y > 0.3 else -0.25))
    # máscara antigás: pieza facial, dos filtros laterales y gafas luminosas
    def mask_keep(x, y, z):
        zz = hc[2] + z * hr[2] * 1.08
        return y > 0.1 and 1.565 < zz < 1.655
    ellipsoid(B, hc, (hr[0] * 1.1, hr[1] * 1.12, hr[2] * 1.08), GEAR, 20, 14, keep=mask_keep, inner=0.06)
    box(B, (0, 0.122, 1.6), (0.05, 0.03, 0.05), METAL, r=(15, 0, 0), bevel=0.01)          # válvula
    def filt(sx):
        a = Vector((sx * 0.045, 0.1, 1.595)); b = Vector((sx * 0.1, 0.16, 1.565))
        tube(B, [a, b], [0.024, 0.032], METAL, seg=12, smooth=False)
        tube(B, [b, b + (b - a).normalized() * 0.035], [0.036, 0.036], GEAR, seg=12, smooth=False)
        tube(B, [b + (b - a).normalized() * 0.035, b + (b - a).normalized() * 0.042], [0.03, 0.03], ACC, seg=12, smooth=False)
    B.mirror_x(filt)
    B.mirror_x(lambda sx: ellipsoid(B, (sx * 0.036, 0.098, 1.676), (0.026, 0.012, 0.022), GLOW, 12, 6))
    box(B, (0, 0.06, 1.678), (0.2, 0.02, 0.018), GEAR, bevel=0.004)                         # correa de las gafas
    # gabardina técnica hasta los muslos (vuelo hacia abajo, cuello alto) con ribete púrpura
    body_loft(B, [(0.56, hip_w * 1.38, 0.17, -0.01), (0.70, hip_w * 1.26, 0.15, -0.006), (0.86, hip_w * 1.14, 0.132, 0.0),
                  (0.98, waist_w * 1.18, 0.122, 0.004), (1.12, waist_w * 1.12, 0.112, 0.006), (1.25, chest_w * 1.08, 0.124, 0.01),
                  (1.36, chest_w * 1.08, 0.124, 0.008), (1.44, sh_w * 1.06, 0.106, 0.0)],
              SUIT, seg=20, power=2.4, cap0=False, cap1=False)
    tube(B, [(0, -0.01, 1.44), (0, -0.01, 1.58)], [sh_w * 0.6, 0.085], SUIT, seg=20, cap0=False, cap1=False)    # cuello alto
    box(B, (0.0, 0.135, 1.0), (0.016, 0.014, 0.82), ACC)                                    # cierre frontal
    body_loft(B, [(0.555, hip_w * 1.39, 0.172, -0.01), (0.585, hip_w * 1.37, 0.168, -0.01)], ACC, seg=20, power=2.4,
              cap0=False, cap1=False, smooth=False)                                         # bajo de la gabardina
    box(B, (0, -0.15, 1.1), (0.012, 0.03, 0.5), SUIT2)                                      # abertura trasera
    B.mirror_x(lambda sx: box(B, (sx * 0.12, 0.13, 1.02), (0.07, 0.02, 0.07), SUIT2, bevel=0.008))   # bolsillos
    # granadas de humo en el cinturón (controlador)
    for k, x in enumerate((-0.15, -0.09)):
        tube(B, [(x, 0.1, 0.9), (x, 0.1, 0.97)], [0.022, 0.022], ACC if k == 0 else GEAR, seg=10, smooth=False)


# ------------------------------------------------------------------------------------------------ material
def make_material(name, pal):
    N = len(pal)
    def img(tag, pixels, non_color):
        im = bpy.data.images.new(f'T_{name}_{tag}', width=N, height=1, alpha=False)
        # El espacio de color va ANTES que los píxeles: cambiarlo después regenera la imagen y la deja en negro.
        if non_color: im.colorspace_settings.name = 'Non-Color'
        flat = []
        for p in pixels: flat += [p[0], p[1], p[2], 1.0]
        im.pixels = flat
        im.pack()
        return im
    base = img('BaseColor', [[c / 255 for c in col] for col, *_ in pal], False)
    mr = img('MetalRough', [[0.0, r, m] for _, m, r, _ in pal], True)       # glTF: rugosidad en G, metal en B
    em = img('Emissive', [[c / 255 for c in e] for *_, e in pal], False)
    mat = bpy.data.materials.new(f'M_{name}')
    if hasattr(mat, 'use_nodes'): mat.use_nodes = True
    nt = mat.node_tree; bsdf = nt.nodes['Principled BSDF']
    def tex(im, y):
        n = nt.nodes.new('ShaderNodeTexImage'); n.image = im; n.interpolation = 'Closest'; n.location = (-600, y); return n
    tb, tm, te = tex(base, 0), tex(mr, -300), tex(em, -600)
    sep = nt.nodes.new('ShaderNodeSeparateColor'); sep.location = (-300, -300)
    nt.links.new(tb.outputs['Color'], bsdf.inputs['Base Color'])
    nt.links.new(tm.outputs['Color'], sep.inputs['Color'])
    nt.links.new(sep.outputs['Green'], bsdf.inputs['Roughness'])
    nt.links.new(sep.outputs['Blue'], bsdf.inputs['Metallic'])
    nt.links.new(te.outputs['Color'], bsdf.inputs['Emission Color'])
    bsdf.inputs['Emission Strength'].default_value = 1.0
    return mat, N


# ------------------------------------------------------------------------------------------------ hitboxes
def hitbox_object(kind):
    me = bpy.data.meshes.new(f'HITBOX_{kind}')
    bm = bmesh.new()
    if kind == 'HEAD':
        z, r = HITBOX['HEAD']
        bmesh.ops.create_icosphere(bm, subdivisions=2, radius=r)
        bmesh.ops.translate(bm, vec=Vector((0, 0, z)), verts=bm.verts)
    else:
        z, w, h = HITBOX[kind]
        bmesh.ops.create_cube(bm, size=1.0)
        bmesh.ops.scale(bm, vec=Vector((w, w, h)), verts=bm.verts)
        bmesh.ops.translate(bm, vec=Vector((0, 0, z)), verts=bm.verts)
    bm.to_mesh(me); bm.free()
    ob = bpy.data.objects.new(f'HITBOX_{kind}', me)
    ob.hide_render = True; ob.display_type = 'WIRE'
    ob['hitbox'] = kind.lower()
    bpy.context.scene.collection.objects.link(ob)
    return ob


# ------------------------------------------------------------------------------------------------ construir + exportar
def generate(name):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.scene.unit_settings.system = 'METRIC'
    spec = AGENTS[name]
    title = name.capitalize()
    mat, N = make_material(title, spec['pal'])
    B = build_agent(name, spec)

    # altura exacta: escala uniforme respecto al pivote de los pies
    top = max(v[2] for v in B.v); bottom = min(v[2] for v in B.v)
    assert abs(bottom) < 0.002, f'{name}: los pies no tocan el suelo ({bottom:.4f})'
    assert abs(top - HEIGHT) < 0.06, f'{name}: altura de modelado fuera de margen ({top:.3f} m)'
    k = HEIGHT / top
    verts = [(x * k, y * k, z * k) for x, y, z in B.v]

    me = bpy.data.meshes.new(f'{title}_Body')
    me.from_pydata(verts, [], B.f)
    me.validate(clean_customdata=False)
    me.update()
    uv = me.uv_layers.new(name='UVMap')
    for poly, cell, sm in zip(me.polygons, B.cell, B.smooth):
        u = (cell + 0.5) / N
        for li in poly.loop_indices: uv.data[li].uv = (u, 0.5)
        poly.use_smooth = sm
    me.materials.append(mat)
    body = bpy.data.objects.new(f'{title}_Body', me)
    bpy.context.scene.collection.objects.link(body)
    body['agent'] = name; body['role'] = spec['role']; body['accent'] = spec['accent']

    muzzle = bpy.data.objects.new('Muzzle_Point', None)
    muzzle.empty_display_type = 'SPHERE'; muzzle.empty_display_size = 0.02
    bpy.context.scene.collection.objects.link(muzzle)
    muzzle.location = Vector(MUZZLE) * k

    for kind in ('HEAD', 'BODY', 'LEGS'): hitbox_object(kind)

    tris = sum(len(p.vertices) - 2 for p in me.polygons)
    zs = [v.co.z for v in me.vertices]; xs = [v.co.x for v in me.vertices]
    print(f'[AGENTE {name}] triángulos: {tris} · alto: {max(zs) - min(zs):.4f} m · ancho: {max(xs) - min(xs):.3f} m · escala {k:.4f}')
    assert TRI_MIN <= tris <= TRI_MAX, f'{name}: {tris} triángulos fuera del presupuesto {TRI_MIN}-{TRI_MAX}'
    assert abs(max(zs) - HEIGHT) < 1e-4 and abs(min(zs)) < 1e-3

    os.makedirs(OUT_DIR, exist_ok=True)
    out = os.path.join(OUT_DIR, f'{name}.glb')
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.export_scene.gltf(filepath=out, export_format='GLB', export_yup=True, use_selection=True,
                              export_apply=True, export_materials='EXPORT', export_normals=True,
                              export_texcoords=True, export_extras=True)
    print(f'[AGENTE {name}] exportado: {out}')
    return tris


if __name__ == '__main__':
    total = {n: generate(n) for n in PICK}
    print('[AGENTES] ' + ' · '.join(f'{n} {t} tris' for n, t in total.items()))
