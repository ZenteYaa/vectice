"""
VÉRTICE · Titán (skin Estándar) · modelado procedural + materiales PBR + exportación .glb

Uso (sin abrir la interfaz):
    blender --background --python titan_default.py -- [ruta_salida.glb]
o con el módulo de Python:  pip install bpy  →  python titan_default.py [ruta_salida.glb]

Convenciones (Blender, Z arriba; el exportador glTF las pasa a +Y arriba):
  · Unidades en metros. El cañón apunta a +Y en Blender → -Z en glTF/Three.js (hacia delante de la cámara).
  · Origen (0, 0, 0) = la empuñadura, en el punto donde la mano la sujeta.
  · Hijo vacío `Muzzle_Point` en la boca del freno: de ahí salen trazadoras y fogonazo.
  · El eje de la mira está a SCOPE_Z sobre el origen: la pose ADS del juego baja el arma justo esa altura.
  · Un solo material `M_Titan_Base` con una paleta de 4×1 píxeles (color, metal/rugosidad y emisión):
    cada pieza apunta sus UV al color que le toca → una sola malla y un solo draw call.
"""
import bpy, bmesh, math, os, sys

OUT = next((a for a in sys.argv[sys.argv.index('--') + 1:] if a.endswith('.glb')), None) if '--' in sys.argv else \
      next((a for a in sys.argv[1:] if a.endswith('.glb')), None)
OUT = OUT or os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'assets', 'weapons', 'titan_default.glb')
SCOPE_Z = 0.14            # altura del eje de la mira sobre la empuñadura
SEG = 12                  # lados de los cilindros (low poly para eSports)

# ---------------------------------------------------------------- escena limpia
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.unit_settings.system = 'METRIC'

# ---------------------------------------------------------------- paleta (atlas de 4 celdas)
#            color base         metal  rugosidad  emisión
PALETTE = [((0x1a, 0x1d, 0x20), 0.15, 0.78, (0, 0, 0)),         # 0 grafito / carbón militar mate
           ((0x2b, 0x30, 0x35), 0.80, 0.30, (0, 0, 0)),         # 1 acero satinado (cerrojo, tornillería, cañón)
           ((0x06, 0x14, 0x14), 0.10, 0.05, (0x0c, 0x6e, 0x5c)),  # 2 lente: vidrio oscuro con reflejo cian/esmeralda
           ((0x11, 0x13, 0x15), 0.00, 0.92, (0, 0, 0))]         # 3 goma (empuñadura, cantonera, carrillera)
N = len(PALETTE)

def srgb_to_lin(c):
    c /= 255.0
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

def make_image(name, pixels, non_color):
    img = bpy.data.images.new(name, width=N, height=1, alpha=False)
    flat = []
    for p in pixels: flat += [p[0], p[1], p[2], 1.0]
    img.pixels = flat
    if non_color: img.colorspace_settings.name = 'Non-Color'
    img.pack()
    return img

base_img = make_image('T_Titan_BaseColor', [[c / 255 for c in col] for col, *_ in PALETTE], False)
# glTF: metal en el canal B y rugosidad en el G de la misma imagen.
mr_img = make_image('T_Titan_MetalRough', [[0.0, r, m] for _, m, r, _ in PALETTE], True)
em_img = make_image('T_Titan_Emissive', [[c / 255 for c in e] for *_, e in PALETTE], False)

mat = bpy.data.materials.new('M_Titan_Base')
if hasattr(mat, 'use_nodes'): mat.use_nodes = True
nt = mat.node_tree
bsdf = nt.nodes['Principled BSDF']
def tex(img, x):
    n = nt.nodes.new('ShaderNodeTexImage'); n.image = img; n.interpolation = 'Closest'; n.location = (x, 0); return n
tb, tm, te = tex(base_img, -600), tex(mr_img, -600), tex(em_img, -600)
tm.location = (-600, -300); te.location = (-600, -600)
sep = nt.nodes.new('ShaderNodeSeparateColor'); sep.location = (-300, -300)
nt.links.new(tb.outputs['Color'], bsdf.inputs['Base Color'])
nt.links.new(tm.outputs['Color'], sep.inputs['Color'])
nt.links.new(sep.outputs['Green'], bsdf.inputs['Roughness'])
nt.links.new(sep.outputs['Blue'], bsdf.inputs['Metallic'])
nt.links.new(te.outputs['Color'], bsdf.inputs['Emission Color'])
bsdf.inputs['Emission Strength'].default_value = 1.0

# ---------------------------------------------------------------- piezas
parts = []

def finish(obj, cell, bevel=0.0):
    """UV de toda la pieza al centro de su celda de la paleta, material único y (opcional) bisel de 1 segmento."""
    if bevel > 0:
        m = obj.modifiers.new('bevel', 'BEVEL'); m.width = bevel; m.segments = 1; m.limit_method = 'ANGLE'
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.modifier_apply(modifier='bevel')
    me = obj.data
    if not me.uv_layers: me.uv_layers.new(name='UVMap')
    uv = me.uv_layers.active.data
    u = (cell + 0.5) / N
    for l in uv: l.uv = (u, 0.5)
    me.materials.clear(); me.materials.append(mat)
    for p in me.polygons: p.use_smooth = False
    parts.append(obj)
    return obj

def box(name, sx, sy, sz, x, y, z, cell=0, bevel=0.004, rx=0.0):
    bpy.ops.mesh.primitive_cube_add(size=1, location=(x, y, z), rotation=(math.radians(rx), 0, 0))
    o = bpy.context.object; o.name = name; o.scale = (sx, sy, sz)
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
    return finish(o, cell, bevel)

def cyl(name, r, length, x, y, z, cell=1, axis='Y', seg=SEG, r2=None):
    """Cilindro (o cono si r2) a lo largo de `axis`, centrado en (x, y, z)."""
    if r2 is None:
        bpy.ops.mesh.primitive_cylinder_add(vertices=seg, radius=r, depth=length, location=(x, y, z))
    else:
        bpy.ops.mesh.primitive_cone_add(vertices=seg, radius1=r, radius2=r2, depth=length, location=(x, y, z))
    o = bpy.context.object; o.name = name
    if axis == 'Y': o.rotation_euler = (math.radians(-90), 0, 0)
    elif axis == 'X': o.rotation_euler = (0, math.radians(90), 0)
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
    return finish(o, cell)

def prism(name, profile, width, cell=0, bevel=0.003):
    """Pieza angular: perfil en el plano YZ (lista de (y, z)) extruido `width` a lo ancho (X)."""
    bm = bmesh.new()
    h = width / 2
    left = [bm.verts.new((-h, y, z)) for y, z in profile]
    right = [bm.verts.new((h, y, z)) for y, z in profile]
    bm.faces.new(left[::-1]); bm.faces.new(right)
    n = len(profile)
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new((left[i], left[j], right[j], right[i]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); scene.collection.objects.link(o)
    return finish(o, cell, bevel)

# Cajón de mecanismos (receiver): sección central angular.
prism('Receiver', [(-0.13, 0.005), (0.24, 0.005), (0.24, 0.07), (0.20, 0.095), (-0.09, 0.095), (-0.13, 0.07)], 0.058)
box('Ejection_Port', 0.062, 0.10, 0.026, 0.0, 0.05, 0.068, cell=1, bevel=0.0)          # ventana de expulsión (acero)
cyl('Bolt_Body', 0.016, 0.20, 0.0, -0.01, 0.06, cell=1)                               # cerrojo
cyl('Bolt_Handle', 0.006, 0.07, 0.055, -0.04, 0.05, cell=1, axis='X', seg=8)           # manija del cerrojo
cyl('Bolt_Knob', 0.013, 0.022, 0.095, -0.04, 0.05, cell=1, axis='X', seg=10)
# Riel Picatinny superior.
box('Rail', 0.026, 0.40, 0.012, 0.0, 0.06, 0.101, cell=1, bevel=0.0)
for i in range(9):
    box(f'Rail_Slot_{i}', 0.030, 0.012, 0.006, 0.0, -0.12 + i * 0.045, 0.108, cell=0, bevel=0.0)

# Guardamanos y bípode plegado debajo.
prism('Handguard', [(0.24, 0.012), (0.50, 0.018), (0.50, 0.078), (0.24, 0.084)], 0.054)
for i in range(4):
    box(f'Handguard_Vent_{i}', 0.056, 0.035, 0.012, 0.0, 0.28 + i * 0.055, 0.05, cell=3, bevel=0.0)
box('Bipod_Mount', 0.04, 0.03, 0.02, 0.0, 0.46, 0.0, cell=1, bevel=0.0)
for s in (-1, 1):
    box(f'Bipod_Leg_{s}', 0.012, 0.20, 0.012, s * 0.016, 0.36, -0.008, cell=1, bevel=0.0)
    box(f'Bipod_Foot_{s}', 0.02, 0.025, 0.016, s * 0.016, 0.255, -0.008, cell=3, bevel=0.0)

# Cañón pesado estriado + freno de boca.
cyl('Barrel', 0.0145, 0.26, 0.0, 0.63, 0.05, cell=1, seg=12)
for i in range(3):                                                                    # estrías (anillos)
    cyl(f'Barrel_Flute_{i}', 0.0165, 0.012, 0.0, 0.54 + i * 0.06, 0.05, cell=0, seg=12)
box('Muzzle_Brake', 0.042, 0.075, 0.034, 0.0, 0.79, 0.05, cell=0, bevel=0.004)
for i in range(3):
    box(f'Brake_Port_{i}', 0.046, 0.011, 0.020, 0.0, 0.768 + i * 0.022, 0.05, cell=1, bevel=0.0)
cyl('Brake_Bore', 0.007, 0.002, 0.0, 0.828, 0.05, cell=1, seg=8)

# Empuñadura táctica (pistol grip) con el origen en la mano, y guardamonte.
prism('Pistol_Grip', [(-0.03, 0.01), (0.03, 0.01), (0.005, -0.11), (-0.05, -0.115), (-0.045, -0.06)], 0.034, cell=3)
prism('Trigger_Guard', [(0.03, 0.0), (0.11, 0.0), (0.11, -0.012), (0.045, -0.045), (0.03, -0.045)], 0.012, cell=0, bevel=0.0)
box('Trigger', 0.006, 0.008, 0.026, 0.0, 0.06, -0.012, cell=1, bevel=0.0, rx=-15)

# Cargador recto desmontable.
box('Magazine', 0.036, 0.075, 0.105, 0.0, 0.15, -0.045, cell=0, bevel=0.003)
box('Magazine_Plate', 0.04, 0.08, 0.012, 0.0, 0.15, -0.1, cell=1, bevel=0.0)

# Culata ergonómica ajustable con carrillera elevada.
prism('Stock', [(-0.13, 0.07), (-0.13, -0.005), (-0.20, -0.03), (-0.40, -0.075), (-0.40, 0.085), (-0.24, 0.085)], 0.044)
box('Cheek_Rest', 0.046, 0.16, 0.03, 0.0, -0.31, 0.10, cell=3, bevel=0.004)
box('Butt_Pad', 0.05, 0.022, 0.17, 0.0, -0.411, 0.005, cell=3, bevel=0.004)
cyl('Stock_Adjust', 0.008, 0.06, 0.0, -0.20, 0.10, cell=1, axis='Z', seg=8)

# Mira telescópica: tubo, campanas, torretas y lentes.
cyl('Scope_Tube', 0.017, 0.26, 0.0, 0.09, SCOPE_Z, cell=0, seg=14)
cyl('Scope_Objective', 0.027, 0.08, 0.0, 0.25, SCOPE_Z, cell=0, seg=14, r2=0.018)
cyl('Scope_Ocular', 0.022, 0.06, 0.0, -0.07, SCOPE_Z, cell=0, seg=14, r2=0.017)
cyl('Turret_Top', 0.011, 0.024, 0.0, 0.10, SCOPE_Z + 0.026, cell=1, axis='Z', seg=10)
cyl('Turret_Side', 0.011, 0.024, 0.026, 0.10, SCOPE_Z, cell=1, axis='X', seg=10)
for y in (0.01, 0.17):                                                                # anillas sobre el riel
    box(f'Scope_Ring_{y}', 0.03, 0.02, SCOPE_Z - 0.105, 0.0, y, (SCOPE_Z + 0.105) / 2, cell=1, bevel=0.0)
cyl('Lens_Front', 0.024, 0.004, 0.0, 0.292, SCOPE_Z, cell=2, seg=14)
cyl('Lens_Rear', 0.019, 0.004, 0.0, -0.102, SCOPE_Z, cell=2, seg=14)

# ---------------------------------------------------------------- unir en una malla, origen en la empuñadura
bpy.ops.object.select_all(action='DESELECT')
for o in parts: o.select_set(True)
bpy.context.view_layer.objects.active = parts[0]
bpy.ops.object.join()
titan = bpy.context.object
titan.name = 'Titan_Default'
titan.data.name = 'Titan_Default_Mesh'
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
scene.cursor.location = (0, 0, 0)
bpy.ops.object.origin_set(type='ORIGIN_CURSOR')
bm = bmesh.new(); bm.from_mesh(titan.data)
bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
bm.to_mesh(titan.data); bm.free()

muzzle = bpy.data.objects.new('Muzzle_Point', None)
muzzle.empty_display_type = 'SPHERE'; muzzle.empty_display_size = 0.02
scene.collection.objects.link(muzzle)
muzzle.parent = titan
muzzle.location = (0.0, 0.83, 0.05)

tris = sum(len(p.vertices) - 2 for p in titan.data.polygons)
ys = [v.co.y for v in titan.data.vertices]
print(f'[TITAN] triángulos: {tris} · longitud: {max(ys) - min(ys):.3f} m · eje de mira: {SCOPE_Z} m')
assert tris <= 4500, f'presupuesto superado: {tris} triángulos'

# ---------------------------------------------------------------- exportar
os.makedirs(os.path.dirname(os.path.abspath(OUT)), exist_ok=True)
bpy.ops.object.select_all(action='SELECT')
bpy.ops.export_scene.gltf(filepath=os.path.abspath(OUT), export_format='GLB', export_yup=True,
                          use_selection=True, export_apply=True, export_materials='EXPORT',
                          export_normals=True, export_texcoords=True, export_extras=False)
print('[TITAN] exportado:', os.path.abspath(OUT))
