"""Blender scene for v4 fox runner. Run:
Blender -b -P bl_scene.py -- --out DIR --start F --end F [--res 1920] [--samples 16]"""
import bpy, bmesh, math, os, sys, random
import numpy as np
from mathutils import Vector, Matrix, Quaternion

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import game as Gm

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
def arg(name, default):
    return type(default)(argv[argv.index(name) + 1]) if name in argv else default
OUTDIR = arg("--out", os.path.join(HERE, "frames"))
FSTART, FEND = arg("--start", 0), arg("--end", 0)
RESX = arg("--res", 1920)
SAMPLES = arg("--samples", 16)
FRAMELIST = arg("--frames", "")

A = np.load(os.path.join(HERE, "anim_%s.npy" % Gm.TAG))
REC_HZ = 90

# ------------------------------------------------------------------ reset
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.render.fps = Gm.FPS
for eng in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"):
    try:
        scene.render.engine = eng
        break
    except TypeError:
        pass
scene.render.resolution_x = RESX
scene.render.resolution_y = RESX * 16 // 9 if Gm.SHORT else RESX * 9 // 16
scene.render.resolution_percentage = 100
ee = scene.eevee
ee.taa_render_samples = SAMPLES
for k, v in (("use_shadows", True), ("shadow_ray_count", 1), ("shadow_step_count", 4), ("use_gtao", True),
             ("gtao_distance", 0.6), ("use_raytracing", False)):
    try:
        setattr(ee, k, v)
    except Exception:
        pass
scene.render.use_motion_blur = True
scene.render.motion_blur_shutter = 0.45
try:
    scene.view_settings.view_transform = "AgX"
    scene.view_settings.look = "AgX - Punchy"
    scene.view_settings.exposure = 0.15
except Exception:
    try:
        scene.view_settings.look = "Punchy"
    except Exception:
        pass
print("LOOK", scene.view_settings.view_transform, scene.view_settings.look)
scene.render.image_settings.file_format = "JPEG"
scene.render.image_settings.color_mode = "RGB"
scene.render.image_settings.quality = 95
scene.render.use_overwrite = False
scene.render.film_transparent = False

COL = {}
def coll(name):
    if name not in COL:
        c = bpy.data.collections.new(name)
        scene.collection.children.link(c)
        COL[name] = c
    return COL[name]


# ------------------------------------------------------------------ materials
MATS = {}
def mat(name, color, rough=0.6, sheen=0.0, metal=0.0, emit=None, emit_str=0.0, noise=0.0, coat=0.0):
    if name in MATS:
        return MATS[name]
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    b = nt.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*color, 1)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    if sheen:
        try:
            b.inputs["Sheen Weight"].default_value = sheen
        except KeyError:
            pass
    if coat:
        try:
            b.inputs["Coat Weight"].default_value = coat
        except KeyError:
            pass
    if emit:
        b.inputs["Emission Color"].default_value = (*emit, 1)
        b.inputs["Emission Strength"].default_value = emit_str
    if noise:  # subtle colour variation for organic look
        tex = nt.nodes.new("ShaderNodeTexNoise")
        tex.inputs["Scale"].default_value = 6.0
        mix = nt.nodes.new("ShaderNodeMix")
        mix.data_type = "RGBA"
        mix.inputs["Factor"].default_value = noise
        mix.inputs[6].default_value = (*color, 1)
        mix.inputs[7].default_value = (color[0] * 0.6, color[1] * 0.6, color[2] * 0.6, 1)
        nt.links.new(tex.outputs["Fac"], mix.inputs["Factor"])
        nt.links.new(mix.outputs[2], b.inputs["Base Color"])
        bump = nt.nodes.new("ShaderNodeBump")
        bump.inputs["Strength"].default_value = 0.15
        nt.links.new(tex.outputs["Fac"], bump.inputs["Height"])
        nt.links.new(bump.outputs["Normal"], b.inputs["Normal"])
    MATS[name] = m
    return m


# ------------------------------------------------------------------ mesh helpers
def _obj(name, mesh, mt, parent=None, col="char"):
    o = bpy.data.objects.new(name, mesh)
    coll(col).objects.link(o)
    if mt:
        if len(mesh.materials) == 0:
            mesh.materials.append(None)
        o.material_slots[0].link = "OBJECT"
        o.material_slots[0].material = mt
    if parent:
        o.parent = parent
    return o


def mesh_sphere(seg=32, ring=16, name="sph"):
    me = bpy.data.meshes.new(name)
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=seg, v_segments=ring, radius=1.0)
    bm.to_mesh(me); bm.free()
    for p in me.polygons:
        p.use_smooth = True
    return me


def mesh_cone(r2=1.0, seg=24, name="cone", base_origin=True, caps=True):
    me = bpy.data.meshes.new(name)
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=caps, segments=seg, radius1=1.0, radius2=r2, depth=1.0)
    if base_origin:
        bmesh.ops.translate(bm, verts=bm.verts, vec=(0, 0, 0.5))
    bm.to_mesh(me); bm.free()
    for p in me.polygons:
        p.use_smooth = True
    return me


def mesh_ico(sub=2, name="ico", jitter=0.0, seed=0):
    me = bpy.data.meshes.new(name)
    bm = bmesh.new()
    bmesh.ops.create_icosphere(bm, subdivisions=sub, radius=1.0)
    if jitter:
        rnd = random.Random(seed)
        for v in bm.verts:
            v.co *= 1 + (rnd.random() - 0.5) * jitter
    bm.to_mesh(me); bm.free()
    for p in me.polygons:
        p.use_smooth = True
    return me


def mesh_box(name="box"):
    me = bpy.data.meshes.new(name)
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bm.to_mesh(me); bm.free()
    return me


def mesh_torus(R=1.0, r=0.25, name="torus"):
    me = bpy.data.meshes.new(name)
    bm = bmesh.new()
    segs, sides = 32, 12
    verts = []
    for i in range(segs):
        a = 2 * math.pi * i / segs
        ring = []
        for j in range(sides):
            b = 2 * math.pi * j / sides
            ring.append(bm.verts.new(((R + r * math.cos(b)) * math.cos(a), (R + r * math.cos(b)) * math.sin(a), r * math.sin(b))))
        verts.append(ring)
    for i in range(segs):
        for j in range(sides):
            bm.faces.new((verts[i][j], verts[(i + 1) % segs][j], verts[(i + 1) % segs][(j + 1) % sides], verts[i][(j + 1) % sides]))
    bm.to_mesh(me); bm.free()
    for p in me.polygons:
        p.use_smooth = True
    return me


SPH = mesh_sphere()
SPH_LO = mesh_sphere(16, 8, "sph_lo")
CYL = mesh_cone(1.0, name="cyl")
CYL_T = mesh_cone(0.75, name="cyl_taper")
CONE = mesh_cone(0.0, name="cone0")
BOX = mesh_box()


def empty(name, parent=None, col="char"):
    o = bpy.data.objects.new(name, None)
    coll(col).objects.link(o)
    o.parent = parent
    return o


def child(name, me, mt, parent, loc=(0, 0, 0), scale=(1, 1, 1), rot=(0, 0, 0), col="char"):
    o = _obj(name, me, mt, parent, col)
    o.location = loc
    o.scale = scale
    o.rotation_euler = rot
    return o


# ------------------------------------------------------------------ fox character
FUR = mat("fur", (0.95, 0.42, 0.09), 0.55, sheen=0.6, noise=0.25)
WHITE = mat("fur_white", (0.95, 0.93, 0.88), 0.6, sheen=0.5)
DARK = mat("fur_dark", (0.10, 0.06, 0.05), 0.6, sheen=0.4)
HOOD = mat("hoodie", Gm.OUTFIT, 0.75, sheen=0.3, noise=0.15)
HOOD2 = mat("hoodie2", tuple(c * 0.75 for c in Gm.OUTFIT), 0.75, sheen=0.3)
SHORTS = mat("shorts", (0.08, 0.1, 0.3), 0.7)
SHOE = mat("shoe", (0.9, 0.08, 0.12), 0.35, coat=0.4)
SOLE = mat("sole", (0.97, 0.97, 0.97), 0.5)
BLACK = mat("black_gloss", (0.01, 0.01, 0.01), 0.15, coat=1.0)
PINK = mat("ear_inner", (0.98, 0.72, 0.68), 0.6)

C = Matrix(((1, 0, 0), (0, 0, -1), (0, 1, 0)))  # motion -> blender


def V(p):
    return Vector((p[0], -p[2], p[1]))


def Rb(r):
    m = Matrix([list(r[:, 0]), list(r[:, 1]), list(r[:, 2])]).transposed()
    return C @ m @ C.transposed()


head_root = empty("head_root")
child("skull", SPH, FUR, head_root, (0, 0, 0.0), (0.128, 0.12, 0.122))
child("cheek_l", SPH, WHITE, head_root, (-0.06, 0.07, -0.045), (0.06, 0.05, 0.045))
child("cheek_r", SPH, WHITE, head_root, (0.06, 0.07, -0.045), (0.06, 0.05, 0.045))
child("snout", SPH, WHITE, head_root, (0, 0.12, -0.035), (0.05, 0.085, 0.045))
child("nose", SPH, BLACK, head_root, (0, 0.205, -0.02), (0.024, 0.02, 0.02))
for s in (-1, 1):
    child(f"eye{s}", SPH, BLACK, head_root, (s * 0.052, 0.098, 0.035), (0.022, 0.016, 0.027))
    child(f"eyehl{s}", SPH_LO, WHITE, head_root, (s * 0.046, 0.112, 0.046), (0.006, 0.004, 0.006))
    ear = empty(f"ear{s}", head_root)
    ear.location = (s * 0.075, -0.01, 0.085)
    ear.rotation_euler = (math.radians(-8), math.radians(s * 22), 0)
    child(f"ear_out{s}", CONE, FUR, ear, (0, 0, 0), (0.06, 0.03, 0.17))
    child(f"ear_in{s}", CONE, PINK, ear, (0, 0.012, 0.01), (0.04, 0.015, 0.13))
    child(f"ear_tip{s}", CONE, DARK, ear, (0, 0, 0.115), (0.024, 0.014, 0.06))

chest_root = empty("chest_root")
child("chest", SPH, HOOD, chest_root, (0, 0, 0), (0.2, 0.125, 0.2))
child("hood", SPH, HOOD2, chest_root, (0, -0.1, 0.17), (0.13, 0.07, 0.085))
child("collar", SPH, WHITE, chest_root, (0, 0.06, 0.15), (0.07, 0.05, 0.06))
belly_root = empty("belly_root")
child("belly", SPH, HOOD, belly_root, (0, 0, 0), (0.165, 0.115, 0.15))
pelvis_root = empty("pelvis_root")
child("shorts", SPH, SHORTS, pelvis_root, (0, 0, -0.03), (0.175, 0.125, 0.12))

SEGS = {}
def seg(name, mt, taper=True):
    SEGS[name] = _obj(name, CYL_T if taper else CYL, mt)
    return SEGS[name]
BALLS = {}
def ball(name, mt, me=None):
    BALLS[name] = _obj(name, me or SPH, mt)
    return BALLS[name]

for sd in ("r", "l"):
    seg(sd + "_uarm", HOOD); seg(sd + "_farm", FUR); seg(sd + "_cuff", HOOD2, False)
    seg(sd + "_thigh", FUR); seg(sd + "_shortleg", SHORTS, False); seg(sd + "_shin", DARK)
    for b, m in (("_sh", HOOD), ("_elb", HOOD), ("_hand", DARK), ("_hip", SHORTS), ("_knee", FUR), ("_ank", DARK)):
        ball(sd + b, m)
    ball(sd + "_shoe", SHOE); ball(sd + "_sole", SOLE)
seg("neck", FUR)
for j in range(5):
    ball(f"tail{j}", WHITE if j == 4 else FUR)

for o in list(coll("char").objects):
    o.visible_shadow = True


def place_seg(o, a, b, r):
    d = b - a
    L = d.length
    if L < 1e-5:
        d, L = Vector((0, 0, 1e-4)), 1e-4
    q = Vector((0, 0, 1)).rotation_difference(d)
    o.matrix_world = Matrix.LocRotScale(a, q, Vector((r, r, L)))


def place_ball(o, c, r, rot=None, scale=None):
    s = Vector(scale) if scale else Vector((r, r, r))
    o.matrix_world = Matrix.LocRotScale(c, rot or Quaternion(), s)


def rec(t):
    x = t * REC_HZ
    k = int(math.floor(x))
    k = max(0, min(len(A) - 2, k))
    f = x - k
    return A[k] * (1 - f) + A[k + 1] * f


def update_char(t):
    R = rec(t)
    P = lambda i: V(R[i])
    rots = [Rb(np.array([R[34 + 3 * j], R[35 + 3 * j], R[36 + 3 * j]]).T) for j in range(4)]
    Rp, Rm, Rt, Rh = rots
    pel, mid, nb, head = P(32), P(33), P(30), P(31)
    head_root.matrix_world = Matrix.Translation(head) @ Rh.to_4x4()
    chest_c = (P(2) + P(7)) / 2 * 0.6 + nb * 0.4
    chest_root.matrix_world = Matrix.Translation(chest_c + Rt @ Vector((0, 0, -0.04))) @ Rt.to_4x4()
    belly_root.matrix_world = Matrix.Translation(mid + Rm @ Vector((0, 0, -0.04))) @ Rm.to_4x4()
    pelvis_root.matrix_world = Matrix.Translation(pel) @ Rp.to_4x4()
    place_seg(SEGS["neck"], nb, head, 0.05)
    for sd, ai, li in (("r", 12, 20), ("l", 16, 25)):
        sh, el, wr, hd = P(ai), P(ai + 1), P(ai + 2), P(ai + 3)
        place_seg(SEGS[sd + "_uarm"], sh, el, 0.06)
        place_seg(SEGS[sd + "_farm"], el, wr, 0.045)
        place_seg(SEGS[sd + "_cuff"], el, el + (wr - el) * 0.25, 0.05)
        place_ball(BALLS[sd + "_sh"], sh, 0.07)
        place_ball(BALLS[sd + "_elb"], el, 0.05)
        place_ball(BALLS[sd + "_hand"], hd, 0.052)
        hip, kn, an, heel, toe = P(li), P(li + 1), P(li + 2), P(li + 3), P(li + 4)
        place_seg(SEGS[sd + "_thigh"], hip, kn, 0.08)
        place_seg(SEGS[sd + "_shortleg"], hip, hip + (kn - hip) * 0.45, 0.09)
        place_seg(SEGS[sd + "_shin"], kn, an, 0.056)
        place_ball(BALLS[sd + "_hip"], hip + Vector((0, 0, 0.02)), 0.09)
        place_ball(BALLS[sd + "_knee"], kn, 0.058)
        place_ball(BALLS[sd + "_ank"], an, 0.042)
        fwd = (toe - heel)
        L = fwd.length
        fwd.normalize()
        up = Vector((0, 0, 1))
        side = fwd.cross(up)
        if side.length < 1e-4:
            side = Vector((1, 0, 0))
        side.normalize()
        up = side.cross(fwd)
        rm = Matrix((side, fwd, up)).transposed().to_quaternion()
        c = (heel + toe) / 2 + fwd * 0.02
        place_ball(BALLS[sd + "_shoe"], c + up * 0.01, 0, rm, (0.058, L / 2 + 0.04, 0.05))
        place_ball(BALLS[sd + "_sole"], c - up * 0.025, 0, rm, (0.062, L / 2 + 0.05, 0.022))
    # tail: anchor near pelvis back, 4 sim points
    tp = [pel + Rp @ Vector((0, -0.11, -0.05))] + [P(46 + j) for j in range(4)]
    radii = [0.06, 0.09, 0.115, 0.11, 0.075]
    for j in range(5):
        a = tp[j]
        b = tp[j + 1] if j < 4 else tp[4] + (tp[4] - tp[3]) * 0.6
        d = b - a
        q = Vector((0, 0, 1)).rotation_difference(d if d.length > 1e-5 else Vector((0, 0, 1)))
        place_ball(BALLS[f"tail{j}"], (a + b) / 2, 0, q, (radii[j], radii[j], d.length / 2 + radii[j] * 0.7))
    return R[50]


# ------------------------------------------------------------------ worlds (kits)
# road kinds: track / planks / ice / asphalt / dirt / glow / stone / candy
KIT = {
    0: dict(sun_el=38, ground=(0.18, 0.45, 0.08), gscale=1.2, road=(0.62, 0.13, 0.08), road_kind="track", line=(1, 1, 1), side=(0.85, 0.85, 0.82)),
    1: dict(sun_el=45, ground=(0.82, 0.6, 0.32), gscale=2.5, road=(0.55, 0.36, 0.2), road_kind="planks", line=(1, 1, 1), side=(0.95, 0.88, 0.7)),
    2: dict(sun_el=22, ground=(0.92, 0.95, 1.0), gscale=2.5, groughness=0.35, road=(0.7, 0.82, 0.95), road_kind="ice", line=(0.2, 0.5, 1.0), side=(1, 1, 1)),
    3: dict(sun_el=50, ground=(0.85, 0.5, 0.22), gscale=1.5, road=(0.25, 0.22, 0.2), road_kind="asphalt", line=(1, 0.8, 0.1), side=(0.75, 0.55, 0.35), dust=1.2),
    4: dict(sun_el=40, ground=(0.92, 0.32, 0.62), gscale=2.0, road=(1.0, 0.75, 0.88), road_kind="candy", line=(1, 0.3, 0.55), side=(1, 1, 1)),
    5: dict(sun_el=42, ground=(0.45, 0.46, 0.48), gscale=4.0, road=(0.1, 0.1, 0.11), road_kind="asphalt", line=(1, 1, 1), side=(0.7, 0.7, 0.72)),
    6: dict(sun_el=25, ground=(0.45, 0.32, 0.1), gscale=1.5, road=(0.35, 0.24, 0.15), road_kind="dirt", line=(1, 0.85, 0.5), side=(0.6, 0.45, 0.28)),
    7: dict(sun_el=30, ground=(0.42, 0.42, 0.48), gscale=0.8, road=(0.05, 0.05, 0.1), road_kind="glow", line=(0.2, 0.9, 1.0), side=(0.3, 0.3, 0.38), space=True),
    8: dict(sun_el=35, ground=(0.25, 0.55, 0.1), gscale=1.2, road=(0.5, 0.36, 0.2), road_kind="dirt", line=(1, 1, 1), side=(0.9, 0.85, 0.7)),
    9: dict(sun_el=55, ground=(0.1, 0.35, 0.06), gscale=1.0, road=(0.42, 0.45, 0.38), road_kind="stone", line=(0.95, 0.9, 0.7), side=(0.5, 0.52, 0.45)),
}
SCROLL = []  # mapping nodes to offset by distance


def scroll_mat(name, base, dark, scale, kind="noise", rough=0.7, coat=0.0, emit=None):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    b = nt.nodes["Principled BSDF"]
    b.inputs["Roughness"].default_value = rough
    if coat:
        b.inputs["Coat Weight"].default_value = coat
    tc = nt.nodes.new("ShaderNodeTexCoord")
    mp = nt.nodes.new("ShaderNodeMapping")
    nt.links.new(tc.outputs["Object"], mp.inputs["Vector"])
    if kind in ("planks", "candy", "stone"):
        if kind == "stone":
            tex = nt.nodes.new("ShaderNodeTexBrick")
            tex.inputs["Scale"].default_value = scale
            tex.inputs["Mortar Size"].default_value = 0.03
            tex.inputs["Color1"].default_value = (*base, 1)
            tex.inputs["Color2"].default_value = (*[c * 0.8 for c in base], 1)
            tex.inputs["Mortar"].default_value = (*dark, 1)
            out = tex.outputs["Fac"]
            col_out = tex.outputs["Color"]
        else:
            tex = nt.nodes.new("ShaderNodeTexWave")
            tex.wave_type = "BANDS"
            tex.bands_direction = "Y"
            tex.inputs["Scale"].default_value = scale
            tex.inputs["Distortion"].default_value = 2.0 if kind == "planks" else 0.0
            tex.inputs["Detail"].default_value = 3.0 if kind == "planks" else 0.0
            out = tex.outputs["Fac"]
            col_out = None
    else:
        tex = nt.nodes.new("ShaderNodeTexNoise")
        tex.inputs["Scale"].default_value = scale
        tex.inputs["Detail"].default_value = 8.0
        out = tex.outputs["Fac"]
        col_out = None
    nt.links.new(mp.outputs["Vector"], tex.inputs["Vector"])
    if col_out is None:
        ramp = nt.nodes.new("ShaderNodeValToRGB")
        ramp.color_ramp.elements[0].color = (*dark, 1)
        ramp.color_ramp.elements[1].color = (*base, 1)
        if kind == "planks":
            ramp.color_ramp.elements[0].position, ramp.color_ramp.elements[1].position = 0.12, 0.2
        elif kind == "candy":
            ramp.color_ramp.interpolation = "CONSTANT"
            ramp.color_ramp.elements[0].position, ramp.color_ramp.elements[1].position = 0.0, 0.5
        else:
            ramp.color_ramp.elements[0].position, ramp.color_ramp.elements[1].position = 0.35, 0.65
        nt.links.new(out, ramp.inputs["Fac"])
        col_out = ramp.outputs["Color"]
    nt.links.new(col_out, b.inputs["Base Color"])
    if emit:
        b.inputs["Emission Color"].default_value = (*emit, 1)
        b.inputs["Emission Strength"].default_value = 0.4
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.3
    nt.links.new(out, bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], b.inputs["Normal"])
    SCROLL.append(mp)
    return m


def plane(name, w, l, y0, mt, z=0.0, x=0.0, col="w"):
    me = bpy.data.meshes.new(name)
    hw = w / 2
    me.from_pydata([(-hw, 0, 0), (hw, 0, 0), (hw, l, 0), (-hw, l, 0)], [], [(0, 1, 2, 3)])
    o = _obj(name, me, mt, None, col)
    o.location = (x, y0, z)
    return o


def hill(name, x, y, sx, sy, sz, mt, col):
    o = _obj(name, mesh_ico(3, name, 0.25, hash(name) & 0xFFFF), mt, None, col)
    o.location = (x, y, -sz * 0.35)
    o.scale = (sx, sy, sz)
    return o


WORLD_COLS = {}
W_ROAD = 3 * Gm.LANE + 0.3


def build_ground(wi):
    th = KIT[wi]
    cn = "world%d" % wi
    WORLD_COLS[wi] = coll(cn)
    g = th["ground"]
    gm = scroll_mat(f"ground{wi}", g, tuple(c * 0.6 for c in g), th["gscale"], rough=th.get("groughness", 0.9))
    plane(f"ground{wi}", 900, 1100, -400, gm, -0.02, col=cn)
    r, kind = th["road"], th["road_kind"]
    if kind == "planks":
        rm = scroll_mat(f"road{wi}", r, tuple(c * 0.45 for c in r), 3.2, "planks", 0.6)
    elif kind == "candy":
        rm = scroll_mat(f"road{wi}", r, (1.0, 0.45, 0.65), 0.6, "candy", 0.35, coat=0.6)
    elif kind == "stone":
        rm = scroll_mat(f"road{wi}", r, (0.2, 0.25, 0.15), 1.5, "stone", 0.8)
    elif kind == "glow":
        rm = scroll_mat(f"road{wi}", r, (0.0, 0.0, 0.02), 6.0, rough=0.3, coat=0.8, emit=(0.05, 0.1, 0.3))
    else:
        rough = {"track": 0.75, "ice": 0.3, "asphalt": 0.85, "dirt": 0.95}[kind]
        rm = scroll_mat(f"road{wi}", r, tuple(c * (0.8 if kind != "dirt" else 0.6) for c in r), 9.0, rough=rough,
                        coat=0.5 if kind == "ice" else 0.0)
    plane(f"road{wi}", W_ROAD, 400, -40, rm, 0.0, col=cn)
    lm = mat(f"line{wi}", th["line"], 0.4, emit=th["line"] if kind == "glow" else None, emit_str=4.0 if kind == "glow" else 0.0)
    xs = (-1.5 * Gm.LANE, -0.5 * Gm.LANE, 0.5 * Gm.LANE, 1.5 * Gm.LANE)
    if kind in ("asphalt",) and wi != 3:
        xs = (-1.5 * Gm.LANE, 1.5 * Gm.LANE)
    for x in xs:
        plane(f"line{wi}_{x:.2f}", 0.06, 400, -40, lm, 0.004, x, col=cn)
    sm = mat(f"side{wi}", th["side"], 0.6)
    for s in (-1, 1):
        o = _obj(f"curb{wi}{s}", BOX, sm, None, cn)
        o.location = (s * (W_ROAD / 2 + 0.2), 160, 0.06)
        o.scale = (0.4, 400, 0.12)
    rnd = random.Random(wi)
    if wi == 0 or wi == 8:
        hm = mat(f"hillg{wi}", (0.12, 0.35, 0.1), 0.9, noise=0.3)
        for k in range(14):
            hill(f"h{wi}_{k}", (k - 7) * 45 + rnd.uniform(-10, 10), 330 + rnd.uniform(0, 80), rnd.uniform(40, 70), 30, rnd.uniform(25, 60), hm, cn)
    elif wi == 1:
        sea = mat("sea", (0.0, 0.32, 0.62), 0.12, coat=0.6)
        plane("sea", 400, 700, -40, sea, 0.03, 214, col=cn)
        plane("wet_sand", 6, 700, -40, mat("wet", (0.7, 0.55, 0.35), 0.25), 0.0, 12.5, col=cn)
        im = mat("island", (0.2, 0.45, 0.15), 0.9, noise=0.3)
        for k in range(4):
            hill(f"h1_{k}", 60 + k * 70, 330 + rnd.uniform(0, 60), rnd.uniform(25, 45), 25, rnd.uniform(10, 25), im, cn)
        dm = mat("dune", (0.9, 0.75, 0.48), 0.9, noise=0.2)
        for k in range(8):
            hill(f"h1d_{k}", -40 - k * 40, 300 + rnd.uniform(0, 80), rnd.uniform(40, 60), 30, rnd.uniform(10, 25), dm, cn)
    elif wi == 2:
        mm = mat("mount", (0.85, 0.9, 1.0), 0.5, noise=0.3)
        rk = mat("mrock", (0.35, 0.38, 0.45), 0.8, noise=0.3)
        for k in range(12):
            hill(f"h2_{k}", (k - 6) * 60 + rnd.uniform(-15, 15), 380 + rnd.uniform(0, 80), rnd.uniform(45, 70), 40, rnd.uniform(70, 140), rk if k % 3 == 0 else mm, cn)
    elif wi == 3:  # mesas
        mm = mat("mesa", (0.75, 0.35, 0.15), 0.9, noise=0.4)
        for k in range(10):
            o = _obj(f"mesa{k}", CYL, mm, None, cn)
            o.location = ((k - 5) * 70 + rnd.uniform(-20, 20), 300 + rnd.uniform(0, 120), -2)
            sc = rnd.uniform(25, 45)
            o.scale = (sc, sc * 0.7, rnd.uniform(25, 60))
    elif wi == 4:  # cotton-candy hills
        for k in range(12):
            c = [(1, 0.6, 0.85), (0.6, 0.85, 1), (1, 0.95, 0.6)][k % 3]
            hill(f"h4_{k}", (k - 6) * 55 + rnd.uniform(-10, 10), 320 + rnd.uniform(0, 80), rnd.uniform(35, 60), 30, rnd.uniform(30, 55),
                 mat(f"cc{k % 3}", c, 0.7, sheen=0.5), cn)
    elif wi == 5:  # skyline
        for k in range(30):
            c = [(0.35, 0.45, 0.6), (0.55, 0.55, 0.6), (0.4, 0.4, 0.45)][k % 3]
            o = _obj(f"sky{k}", BOX, mat(f"skyl{k % 3}", c, 0.4), None, cn)
            o.location = ((k - 15) * 22 + rnd.uniform(-5, 5), 260 + rnd.uniform(0, 100), 0)
            o.scale = (rnd.uniform(12, 20), rnd.uniform(12, 20), rnd.uniform(40, 120))
    elif wi == 6:
        hm = mat("hilla", (0.55, 0.35, 0.1), 0.9, noise=0.4)
        for k in range(14):
            hill(f"h6_{k}", (k - 7) * 45 + rnd.uniform(-10, 10), 330 + rnd.uniform(0, 80), rnd.uniform(40, 70), 30, rnd.uniform(25, 60), hm, cn)
    elif wi == 7:  # planets + craters horizon
        for k, (c, r_, x, z) in enumerate((((0.9, 0.5, 0.2), 60, -150, 120), ((0.3, 0.5, 1.0), 35, 160, 160), ((0.8, 0.3, 0.9), 20, 40, 220))):
            o = _obj(f"planet{k}", SPH, mat(f"planet{k}", c, 0.6, emit=c, emit_str=0.6), None, cn)
            o.location = (x, 600, z)
            o.scale = (r_, r_, r_)
        rm2 = mat("moonhill", (0.35, 0.35, 0.4), 0.9, noise=0.4)
        for k in range(10):
            hill(f"h7_{k}", (k - 5) * 60, 300 + rnd.uniform(0, 80), rnd.uniform(40, 70), 30, rnd.uniform(10, 30), rm2, cn)
    elif wi == 9:
        hm = mat("hillj", (0.05, 0.3, 0.08), 0.9, noise=0.4)
        for k in range(14):
            hill(f"h9_{k}", (k - 7) * 45, 300 + rnd.uniform(0, 80), rnd.uniform(40, 70), 30, rnd.uniform(40, 80), hm, cn)


# ------------------------------------------------------------------ decor prototypes
def proto_tree(col, k, rnd):
    e = empty(f"tree{k}", None, col)
    child("trunk", CYL_T, mat("bark", (0.32, 0.2, 0.1), 0.85, noise=0.4), e, (0, 0, 0), (0.22, 0.22, 3.2), col=col)
    leaf = mat("leaf%d" % (k % 3), [(0.12, 0.42, 0.06), (0.2, 0.5, 0.08), (0.08, 0.32, 0.05)][k % 3], 0.8, sheen=0.3, noise=0.4)
    for j in range(5):
        a = j * 1.3
        r = rnd.uniform(1.0, 1.5)
        child("crown", mesh_ico(2, "cr", 0.3, rnd.randrange(999)), leaf, e,
              (math.cos(a) * 0.7 * (j > 0), math.sin(a) * 0.7 * (j > 0), 3.4 + rnd.uniform(-0.3, 0.8)), (r, r, r * 0.85), col=col)
    return e


def proto_pine(col, k, rnd, snow=False):
    e = empty(f"pine{k}", None, col)
    child("trunk", CYL, mat("bark", (0.32, 0.2, 0.1), 0.85), e, (0, 0, 0), (0.18, 0.18, 1.2), col=col)
    g = mat("pine", (0.04, 0.24, 0.1), 0.8, noise=0.3)
    wm = mat("snowcap", (0.95, 0.97, 1.0), 0.4)
    for j in range(4):
        h = 1.0 + j * 1.15
        r = 1.6 - j * 0.33
        child("tier", CONE, g, e, (0, 0, h), (r, r, 1.7), col=col)
        if snow:
            child("cap", CONE, wm, e, (0, 0, h + 0.75), (r * 0.62, r * 0.62, 0.95), col=col)
    return e


def proto_bush(col, k, rnd, flowers=True):
    e = empty(f"bush{k}", None, col)
    g = mat("bushg", (0.1, 0.38, 0.07), 0.8, sheen=0.3, noise=0.4)
    for j in range(4):
        r = rnd.uniform(0.5, 0.8)
        child("b", mesh_ico(2, "bb", 0.3, rnd.randrange(999)), g, e, (rnd.uniform(-0.6, 0.6), rnd.uniform(-0.4, 0.4), r * 0.6), (r, r, r * 0.8), col=col)
    if flowers:
        fc = [(1, 0.2, 0.35), (1, 0.85, 0.1), (0.95, 0.95, 1)]
        for j in range(9):
            child("fl", SPH_LO, mat("flower%d" % (j % 3), fc[j % 3], 0.5), e,
                  (rnd.uniform(-0.8, 0.8), rnd.uniform(-0.5, 0.5), rnd.uniform(0.7, 1.15)), (0.08, 0.08, 0.08), col=col)
    return e


def proto_rock(col, k, rnd, color=(0.42, 0.42, 0.4)):
    e = empty(f"rock{k}", None, col)
    child("r", mesh_ico(2, "rk", 0.45, rnd.randrange(999)), mat("rock%s" % str(color), color, 0.85, noise=0.5), e, (0, 0, 0.3),
          (rnd.uniform(0.7, 1.2), rnd.uniform(0.6, 1.0), rnd.uniform(0.5, 0.8)), col=col)
    return e


def proto_palm(col, k, rnd):
    e = empty(f"palm{k}", None, col)
    bark = mat("palmbark", (0.45, 0.32, 0.18), 0.85, noise=0.5)
    leaf = mat("palmleaf", (0.12, 0.5, 0.1), 0.6, sheen=0.3)
    lean = rnd.uniform(-0.25, 0.25)
    pts = [Vector((lean * (j / 6) ** 2 * 6, 0, j * 0.85)) for j in range(7)]
    for j in range(6):
        o = child("pt", CYL_T, bark, e, col=col)
        d = pts[j + 1] - pts[j]
        o.location = pts[j]
        o.rotation_mode = "QUATERNION"
        o.rotation_quaternion = Vector((0, 0, 1)).rotation_difference(d)
        o.scale = (0.2 - j * 0.015, 0.2 - j * 0.015, d.length * 1.05)
    top = pts[-1]
    for j in range(8):
        a = j * math.pi / 4 + rnd.uniform(-0.2, 0.2)
        o = child("lf", SPH_LO, leaf, e, col=col)
        o.location = top + Vector((math.cos(a) * 1.1, math.sin(a) * 1.1, -0.35))
        o.rotation_euler = (math.sin(a) * -0.5, math.cos(a) * 0.5, a)
        o.scale = (1.4, 0.28, 0.06)
    child("coco", SPH_LO, mat("coco", (0.3, 0.2, 0.08), 0.6), e, top + Vector((0.15, 0, -0.2)), (0.16, 0.16, 0.16), col=col)
    return e


def proto_umbrella(col, k, rnd):
    e = empty(f"umb{k}", None, col)
    c = [(1, 0.25, 0.2), (1, 0.8, 0.1), (0.1, 0.55, 1.0), (1, 1, 1)][k % 4]
    child("pole", CYL, mat("pole", (0.95, 0.95, 0.95), 0.4), e, (0, 0, 0), (0.04, 0.04, 2.3), col=col)
    child("canopy", CONE, mat("canopy%d" % (k % 4), c, 0.6), e, (0, 0, 1.9), (1.3, 1.3, 0.55), col=col)
    child("towel", BOX, mat("towel%d" % (k % 3), [(1, 0.3, 0.5), (0.2, 0.8, 0.9), (1, 0.9, 0.3)][k % 3], 0.8), e, (0.9, 0.2, 0.01), (0.8, 1.7, 0.02), col=col)
    return e


def proto_snowman(col, k, rnd):
    e = empty(f"snowman{k}", None, col)
    w = mat("snowball", (0.95, 0.97, 1.0), 0.45)
    for r, z in ((0.55, 0.5), (0.4, 1.3), (0.3, 1.9)):
        child("s", SPH, w, e, (0, 0, z), (r, r, r), col=col)
    child("nose", CONE, mat("carrot", (1, 0.45, 0.05), 0.5), e, (0, -0.28, 1.92), (0.05, 0.05, 0.25), (math.radians(90), 0, 0), col=col)
    child("hat", CYL, mat("hat", (0.05, 0.05, 0.08), 0.5), e, (0, 0, 2.12), (0.22, 0.22, 0.3), col=col)
    child("scarf", mesh_torus(1, 0.3), mat("scarf", (0.9, 0.1, 0.15), 0.8), e, (0, 0, 1.63), (0.32, 0.32, 0.32), col=col)
    return e


def proto_ice(col, k, rnd):
    e = empty(f"ice{k}", None, col)
    m = mat("ice", (0.55, 0.8, 1.0), 0.05, coat=1.0)
    for j in range(3):
        o = child("c", CONE, m, e, (rnd.uniform(-0.4, 0.4), rnd.uniform(-0.3, 0.3), 0), (0.3, 0.3, rnd.uniform(1.0, 2.0)), col=col)
        o.rotation_euler = (rnd.uniform(-0.3, 0.3), rnd.uniform(-0.3, 0.3), 0)
    return e


def mesh_prism(name="prism"):
    me = bpy.data.meshes.new(name)
    v = [(-0.5, -0.5, 0), (0.5, -0.5, 0), (0, -0.5, 0.5), (-0.5, 0.5, 0), (0.5, 0.5, 0), (0, 0.5, 0.5)]
    f = [(0, 1, 2), (3, 5, 4), (0, 3, 4, 1), (1, 4, 5, 2), (0, 2, 5, 3)]
    me.from_pydata(v, [], f)
    return me


PRISM = mesh_prism()


def proto_tree2(col, k, rnd, leaves):
    e = empty(f"tree{k}", None, col)
    child("trunk", CYL_T, mat("bark", (0.32, 0.2, 0.1), 0.85, noise=0.4), e, (0, 0, 0), (0.22, 0.22, 3.2), col=col)
    c = leaves[k % len(leaves)]
    leaf = mat("leaf%s" % str(c), c, 0.8, sheen=0.3, noise=0.4)
    for j in range(5):
        a = j * 1.3
        r = rnd.uniform(1.0, 1.5)
        child("crown", mesh_ico(2, "cr", 0.3, rnd.randrange(999)), leaf, e,
              (math.cos(a) * 0.7 * (j > 0), math.sin(a) * 0.7 * (j > 0), 3.4 + rnd.uniform(-0.3, 0.8)), (r, r, r * 0.85), col=col)
    return e


def proto_cactus(col, k, rnd):
    e = empty(f"cactus{k}", None, col)
    g = mat("cactus", (0.15, 0.45, 0.15), 0.6, noise=0.3)
    h = rnd.uniform(2.0, 3.2)
    child("t", CYL, g, e, (0, 0, 0), (0.28, 0.28, h), col=col)
    child("tc", SPH, g, e, (0, 0, h), (0.28, 0.28, 0.28), col=col)
    for s in (-1, 1):
        z = rnd.uniform(0.9, 1.6)
        child("a", CYL, g, e, (s * 0.2, 0, z), (0.17, 0.17, 0.5), (0, s * math.pi / 2, 0), col=col)
        child("b", CYL, g, e, (s * 0.65, 0, z), (0.17, 0.17, 0.7), col=col)
        child("bc", SPH, g, e, (s * 0.65, 0, z + 0.7), (0.17, 0.17, 0.17), col=col)
    child("fl", SPH_LO, mat("cflower", (1, 0.3, 0.6), 0.5), e, (0, 0, h + 0.25), (0.12, 0.12, 0.08), col=col)
    return e


def proto_lollipop(col, k, rnd):
    e = empty(f"lolli{k}", None, col)
    child("stick", CYL, mat("stick", (0.97, 0.97, 0.95), 0.4), e, (0, 0, 0), (0.07, 0.07, 2.6), col=col)
    c = [(1, 0.2, 0.5), (0.3, 0.7, 1), (1, 0.8, 0.1), (0.6, 0.3, 1)][k % 4]
    child("candy", SPH, mat("lol%d" % (k % 4), c, 0.15, coat=1.0), e, (0, 0, 3.2), (0.85, 0.22, 0.85), (0, 0, rnd.uniform(0, 3)), col=col)
    child("ring", mesh_torus(1, 0.12), mat("lolring", (1, 1, 1), 0.2, coat=1.0), e, (0, 0, 3.2), (0.55, 0.55, 0.55), (math.pi / 2, 0, 0), col=col)
    return e


def proto_cupcake(col, k, rnd):
    e = empty(f"cup{k}", None, col)
    child("wrap", mesh_cone(1.3, 24, "wrapme"), mat("wrap%d" % (k % 3), [(0.3, 0.7, 1), (1, 0.5, 0.7), (0.6, 0.9, 0.4)][k % 3], 0.5), e,
          (0, 0, 0), (0.6, 0.6, 0.8), col=col)
    child("frost", SPH, mat("frost%d" % (k % 2), [(1, 0.85, 0.92), (0.98, 0.95, 0.85)][k % 2], 0.4, sheen=0.4), e, (0, 0, 1.0), (0.85, 0.85, 0.55), col=col)
    child("cherry", SPH, mat("cherry", (0.9, 0.05, 0.1), 0.15, coat=1.0), e, (0, 0, 1.6), (0.17, 0.17, 0.17), col=col)
    return e


def proto_gumtree(col, k, rnd):
    e = empty(f"gum{k}", None, col)
    child("trunk", CYL_T, mat("choco", (0.3, 0.15, 0.06), 0.4), e, (0, 0, 0), (0.18, 0.18, 2.0), col=col)
    for j in range(4):
        c = [(1, 0.3, 0.5), (0.4, 0.9, 0.5), (1, 0.85, 0.2), (0.5, 0.6, 1)][(k + j) % 4]
        a = j * 1.57
        child("g", SPH, mat("gum%d" % ((k + j) % 4), c, 0.1, coat=1.0), e,
              (math.cos(a) * 0.5 * (j > 0), math.sin(a) * 0.5 * (j > 0), 2.4 + 0.4 * (j == 0)), (0.7, 0.7, 0.6), col=col)
    return e


def proto_building(col, k, rnd):
    e = empty(f"bld{k}", None, col)
    fac = [(0.75, 0.45, 0.35), (0.85, 0.8, 0.7), (0.45, 0.55, 0.7), (0.9, 0.7, 0.4), (0.6, 0.65, 0.6)][k % 5]
    m = bpy.data.materials.new("bldm%d" % k)
    m.use_nodes = True
    nt = m.node_tree
    b = nt.nodes["Principled BSDF"]
    br = nt.nodes.new("ShaderNodeTexBrick")
    br.inputs["Color1"].default_value = (0.15, 0.3, 0.45, 1)
    br.inputs["Color2"].default_value = (0.25, 0.4, 0.55, 1)
    br.inputs["Mortar"].default_value = (*fac, 1)
    br.inputs["Mortar Size"].default_value = 0.25
    br.inputs["Scale"].default_value = 1.0
    tc = nt.nodes.new("ShaderNodeTexCoord")
    nt.links.new(tc.outputs["Object"], br.inputs["Vector"])
    nt.links.new(br.outputs["Color"], b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = 0.5
    h = rnd.uniform(8, 22)
    o = child("b", BOX, m, e, (0, 0, h / 2), (rnd.uniform(5, 8), rnd.uniform(5, 8), h), col=col)
    child("roof", BOX, mat("roof", (0.3, 0.3, 0.32), 0.7), e, (0, 0, h + 0.15), (o.scale[0] + 0.3, o.scale[1] + 0.3, 0.3), col=col)
    return e


def proto_lamp(col, k, rnd):
    e = empty(f"lamp{k}", None, col)
    child("pole", CYL, mat("lpole", (0.15, 0.15, 0.17), 0.4, metal=1.0), e, (0, 0, 0), (0.08, 0.08, 4.0), col=col)
    child("arm", BOX, mat("lpole", (0.15, 0.15, 0.17), 0.4, metal=1.0), e, (0.4, 0, 4.0), (0.9, 0.08, 0.08), col=col)
    child("bulb", SPH_LO, mat("bulb", (1, 0.95, 0.8), 0.3, emit=(1, 0.9, 0.6), emit_str=6.0), e, (0.8, 0, 3.9), (0.18, 0.18, 0.12), col=col)
    return e


def proto_pumpkin(col, k, rnd):
    e = empty(f"pump{k}", None, col)
    s = rnd.uniform(0.4, 0.7)
    child("p", SPH, mat("pumpkin", (0.95, 0.45, 0.05), 0.5, noise=0.2), e, (0, 0, s * 0.8), (s * 1.2, s * 1.2, s * 0.85), col=col)
    child("stem", CYL, mat("stem", (0.2, 0.35, 0.1), 0.7), e, (0, 0, s * 1.5), (0.06, 0.06, 0.25), col=col)
    return e


def proto_hay(col, k, rnd):
    e = empty(f"hay{k}", None, col)
    child("h", CYL, mat("hay", (0.9, 0.72, 0.3), 0.9, noise=0.5), e, (0, -0.6, 0.7), (0.7, 0.7, 1.2), (math.pi / 2, 0, 0), col=col)
    return e


def proto_barn(col, k, rnd):
    e = empty(f"barn{k}", None, col)
    red = mat("barnred", (0.65, 0.08, 0.06), 0.8, noise=0.3)
    child("b", BOX, red, e, (0, 0, 2.0), (6, 5, 4), col=col)
    child("r", PRISM, mat("barnroof", (0.25, 0.25, 0.28), 0.7), e, (0, 0, 4.0), (6.6, 5.4, 4.0), (0, 0, math.pi / 2), col=col)
    child("d", BOX, mat("barnwhite", (0.95, 0.95, 0.95), 0.6), e, (0, -2.52, 1.4), (2.2, 0.05, 2.8), col=col)
    return e


def proto_fence(col, k, rnd):
    e = empty(f"fence{k}", None, col)
    w = mat("fencew", (0.95, 0.93, 0.88), 0.6)
    for j in range(4):
        child("p", BOX, w, e, (0, j * 1.2 - 1.8, 0.5), (0.1, 0.1, 1.0), col=col)
    for z in (0.4, 0.8):
        child("r", BOX, w, e, (0, 0, z), (0.06, 3.8, 0.1), col=col)
    return e


def proto_sunflower(col, k, rnd):
    e = empty(f"sunf{k}", None, col)
    for j in range(3):
        x, y, h = rnd.uniform(-0.6, 0.6), rnd.uniform(-0.6, 0.6), rnd.uniform(1.4, 2.0)
        child("s", CYL, mat("sfstem", (0.2, 0.5, 0.1), 0.7), e, (x, y, 0), (0.04, 0.04, h), col=col)
        child("p", SPH, mat("sfpetal", (1, 0.8, 0.05), 0.6), e, (x, y - 0.05, h), (0.35, 0.08, 0.35), col=col)
        child("c", SPH, mat("sfcenter", (0.3, 0.15, 0.05), 0.8), e, (x, y - 0.1, h), (0.16, 0.06, 0.16), col=col)
    return e


def proto_crystal(col, k, rnd):
    e = empty(f"cry{k}", None, col)
    c = [(0.3, 0.9, 1.0), (0.8, 0.3, 1.0), (0.3, 1.0, 0.5)][k % 3]
    m = mat("cry%d" % (k % 3), c, 0.1, coat=1.0, emit=c, emit_str=2.5)
    for j in range(4):
        o = child("c", CONE, m, e, (rnd.uniform(-0.5, 0.5), rnd.uniform(-0.4, 0.4), 0), (0.25, 0.25, rnd.uniform(1.0, 2.4)), col=col)
        o.rotation_euler = (rnd.uniform(-0.35, 0.35), rnd.uniform(-0.35, 0.35), 0)
    return e


def proto_alienplant(col, k, rnd):
    e = empty(f"alien{k}", None, col)
    for j in range(3):
        x, h = rnd.uniform(-0.5, 0.5), rnd.uniform(1.2, 2.2)
        child("s", CYL_T, mat("astem", (0.25, 0.1, 0.4), 0.6), e, (x, 0, 0), (0.08, 0.08, h), col=col)
        c = [(0.2, 1, 0.6), (1, 0.4, 0.9), (1, 0.9, 0.2)][(k + j) % 3]
        child("b", SPH_LO, mat("abulb%d" % ((k + j) % 3), c, 0.3, emit=c, emit_str=3.0), e, (x, 0, h), (0.2, 0.2, 0.2), col=col)
    return e


def proto_bigleaf(col, k, rnd):
    e = empty(f"leafp{k}", None, col)
    g = mat("bigleaf", (0.08, 0.45, 0.1), 0.5, sheen=0.3)
    for j in range(7):
        a = j * 0.9
        o = child("l", SPH_LO, g, e, (math.cos(a) * 0.7, math.sin(a) * 0.7, 0.9), (1.0, 0.35, 0.05), col=col)
        o.rotation_euler = (math.sin(a) * 0.6, -math.cos(a) * 0.6, a)
    return e


def proto_ruin(col, k, rnd):
    e = empty(f"ruin{k}", None, col)
    st = mat("ruinst", (0.55, 0.55, 0.48), 0.9, noise=0.5)
    moss = mat("moss", (0.15, 0.4, 0.1), 0.9, noise=0.4)
    h = rnd.uniform(1.8, 4.0)
    child("c", CYL, st, e, (0, 0, 0), (0.45, 0.45, h), col=col)
    child("m", CYL, moss, e, (0, 0, h - 0.05), (0.47, 0.47, 0.15), col=col)
    child("base", BOX, st, e, (0, 0, 0.2), (1.2, 1.2, 0.4), col=col)
    return e


rnd = random.Random(7)
LEAVES_AUTUMN = [(0.85, 0.35, 0.05), (0.9, 0.6, 0.05), (0.7, 0.12, 0.05)]
LEAVES_GREEN = [(0.12, 0.42, 0.06), (0.2, 0.5, 0.08), (0.08, 0.32, 0.05)]
PROTO_SETS = {
    0: [lambda c, k: proto_tree2(c, k, rnd, LEAVES_GREEN), lambda c, k: proto_pine(c, k, rnd), lambda c, k: proto_bush(c, k, rnd), lambda c, k: proto_rock(c, k, rnd)],
    1: [lambda c, k: proto_palm(c, k, rnd), lambda c, k: proto_palm(c, k, rnd), lambda c, k: proto_umbrella(c, k, rnd), lambda c, k: proto_rock(c, k, rnd, (0.55, 0.5, 0.42))],
    2: [lambda c, k: proto_pine(c, k, rnd, True), lambda c, k: proto_pine(c, k, rnd, True), lambda c, k: proto_snowman(c, k, rnd), lambda c, k: proto_ice(c, k, rnd)],
    3: [lambda c, k: proto_cactus(c, k, rnd), lambda c, k: proto_cactus(c, k, rnd), lambda c, k: proto_rock(c, k, rnd, (0.7, 0.4, 0.2)), lambda c, k: proto_rock(c, k, rnd, (0.6, 0.45, 0.3))],
    4: [lambda c, k: proto_lollipop(c, k, rnd), lambda c, k: proto_cupcake(c, k, rnd), lambda c, k: proto_gumtree(c, k, rnd), lambda c, k: proto_lollipop(c, k, rnd)],
    5: [lambda c, k: proto_building(c, k, rnd), lambda c, k: proto_building(c, k, rnd), lambda c, k: proto_lamp(c, k, rnd), lambda c, k: proto_tree2(c, k, rnd, LEAVES_GREEN)],
    6: [lambda c, k: proto_tree2(c, k, rnd, LEAVES_AUTUMN), lambda c, k: proto_tree2(c, k, rnd, LEAVES_AUTUMN), lambda c, k: proto_pumpkin(c, k, rnd), lambda c, k: proto_hay(c, k, rnd)],
    7: [lambda c, k: proto_crystal(c, k, rnd), lambda c, k: proto_alienplant(c, k, rnd), lambda c, k: proto_rock(c, k, rnd, (0.45, 0.45, 0.5)), lambda c, k: proto_crystal(c, k, rnd)],
    8: [lambda c, k: proto_barn(c, k, rnd), lambda c, k: proto_hay(c, k, rnd), lambda c, k: proto_fence(c, k, rnd), lambda c, k: proto_sunflower(c, k, rnd)],
    9: [lambda c, k: proto_palm(c, k, rnd), lambda c, k: proto_bigleaf(c, k, rnd), lambda c, k: proto_ruin(c, k, rnd), lambda c, k: proto_bush(c, k, rnd)],
}
NPOOL = 60
POOL = {}
for wi in Gm.USED_WORLDS:
    build_ground(wi)
    POOL[wi] = [[mk("world%d" % wi, k) for k in range(NPOOL)] for mk in PROTO_SETS[wi]]

# ------------------------------------------------------------------ obstacles + coins
OBS = coll("obs")
STRIPE_R = mat("stripe_r", (0.9, 0.05, 0.05), 0.4)
STRIPE_W = mat("stripe_w", (0.97, 0.97, 0.97), 0.4)
METAL = mat("metal", (0.7, 0.72, 0.75), 0.3, metal=1.0)
LAMP = mat("lamp", (1, 0.8, 0.1), 0.3, emit=(1, 0.75, 0.1), emit_str=8.0)

def make_hurdle(k):
    e = empty(f"hurdle{k}", None, "obs")
    for s in (-1, 1):
        child("leg", BOX, METAL, e, (s * W_ROAD / 2, 0, 0.21), (0.06, 0.06, 0.42), col="obs")
        child("foot", BOX, METAL, e, (s * W_ROAD / 2, -0.15, 0.02), (0.06, 0.4, 0.04), col="obs")
    n = 10
    for j in range(n):
        x = -W_ROAD / 2 + (j + 0.5) * W_ROAD / n
        child("bar", BOX, STRIPE_R if j % 2 else STRIPE_W, e, (x, 0, 0.38), (W_ROAD / n, 0.05, 0.12), col="obs")
    return e


def make_bar(k):
    e = empty(f"duckbar{k}", None, "obs")
    for s in (-1, 1):
        child("post", BOX, STRIPE_W, e, (s * (W_ROAD / 2 + 0.1), 0, 1.0), (0.18, 0.18, 2.0), col="obs")
        child("lamp", SPH_LO, LAMP, e, (s * (W_ROAD / 2 + 0.1), 0, 2.08), (0.12, 0.12, 0.12), col="obs")
    n = 12
    for j in range(n):
        x = -W_ROAD / 2 + (j + 0.5) * W_ROAD / n
        child("bar", BOX, STRIPE_R if j % 2 else STRIPE_W, e, (x, 0, 1.52), (W_ROAD / n, 0.14, 0.22), col="obs")
    return e


def make_block(k, wi):
    e = empty(f"block{wi}_{k}", None, "obs")
    if wi in (0, 8) and wi == 0:  # stacked crates
        cm = mat("crate", (0.6, 0.38, 0.16), 0.8, noise=0.5)
        child("c1", BOX, cm, e, (0, 0, 0.5), (1.0, 1.0, 1.0), col="obs")
        child("c2", BOX, cm, e, (0.05, 0.05, 1.45), (0.85, 0.85, 0.9), (0, 0, 0.2), col="obs")
        for z in (0.12, 0.88):
            child("band", BOX, mat("crateband", (0.3, 0.18, 0.08), 0.8), e, (0, 0, z), (1.02, 1.02, 0.08), col="obs")
    elif wi == 1:  # giant beach ball
        cols = [(1, 0.15, 0.15), (1, 1, 1), (0.1, 0.4, 1), (1, 0.85, 0.1)]
        for j in range(4):
            o = child("seg", SPH, mat("ball%d" % j, cols[j], 0.25, coat=0.8), e, (0, 0, 0.6), (0.6, 0.6, 0.6), col="obs")
            o.scale = (0.6 + 0.004 * j, 0.6 - 0.004 * j, 0.6)
            o.rotation_euler = (0, 0, j * math.pi / 4)
    elif wi == 2:  # ice block with snow top
        child("ice", BOX, mat("iceblock", (0.6, 0.85, 1.0), 0.05, coat=1.0), e, (0, 0, 0.6), (1.0, 1.0, 1.2), col="obs")
        child("top", SPH, mat("snowball", (0.95, 0.97, 1.0), 0.45), e, (0, 0, 1.22), (0.55, 0.55, 0.15), col="obs")
    elif wi == 3:  # sandstone boulder
        child("r", mesh_ico(2, "boulder", 0.35, k), mat("sandstone", (0.75, 0.42, 0.2), 0.9, noise=0.5), e, (0, 0, 0.6), (0.75, 0.7, 0.65), col="obs")
    elif wi == 4:  # giant gift box
        c = [(1, 0.25, 0.45), (0.3, 0.6, 1), (0.5, 0.9, 0.4)][k % 3]
        child("box", BOX, mat("gift%d" % (k % 3), c, 0.35, coat=0.5), e, (0, 0, 0.55), (1.05, 1.05, 1.1), col="obs")
        rib = mat("ribbon", (1, 0.9, 0.2), 0.3, coat=0.8)
        child("r1", BOX, rib, e, (0, 0, 0.56), (0.18, 1.08, 1.12), col="obs")
        child("r2", BOX, rib, e, (0, 0, 0.56), (1.08, 0.18, 1.12), col="obs")
        child("bow", mesh_torus(1, 0.3), rib, e, (0, 0, 1.2), (0.25, 0.25, 0.25), (math.pi / 2, 0, 0), col="obs")
    elif wi == 5:  # construction barrier block
        y = mat("cyellow", (1, 0.75, 0.0), 0.5)
        k_ = mat("cblack", (0.05, 0.05, 0.05), 0.5)
        for j in range(4):
            child("s", BOX, y if j % 2 == 0 else k_, e, (0, 0, 0.15 + j * 0.3), (1.1, 0.9, 0.3), col="obs")
        child("lamp", SPH_LO, LAMP, e, (0, 0, 1.4), (0.12, 0.12, 0.12), col="obs")
    elif wi == 6:  # giant pumpkin
        child("p", SPH, mat("pumpkin", (0.95, 0.45, 0.05), 0.5, noise=0.2), e, (0, 0, 0.6), (0.75, 0.75, 0.6), col="obs")
        child("stem", CYL, mat("stem", (0.2, 0.35, 0.1), 0.7), e, (0, 0, 1.15), (0.08, 0.08, 0.3), col="obs")
    elif wi == 7:  # glowing asteroid
        child("a", mesh_ico(2, "aster", 0.45, k), mat("asteroid", (0.3, 0.28, 0.3), 0.9, noise=0.5, emit=(1, 0.3, 0.1), emit_str=0.3), e,
              (0, 0, 0.65), (0.7, 0.7, 0.65), col="obs")
    elif wi == 8:  # hay bale stack
        hm = mat("hay", (0.9, 0.72, 0.3), 0.9, noise=0.5)
        child("h1", BOX, hm, e, (0, 0, 0.35), (1.1, 0.9, 0.7), col="obs")
        child("h2", BOX, hm, e, (0, 0, 1.05), (1.0, 0.85, 0.7), (0, 0, 0.15), col="obs")
    else:  # mossy stone totem
        st = mat("ruinst", (0.55, 0.55, 0.48), 0.9, noise=0.5)
        child("t1", BOX, st, e, (0, 0, 0.4), (1.0, 0.9, 0.8), col="obs")
        child("t2", BOX, st, e, (0, 0, 1.15), (0.85, 0.8, 0.7), col="obs")
        child("m", BOX, mat("moss", (0.15, 0.4, 0.1), 0.9, noise=0.4), e, (0, 0, 1.52), (0.88, 0.83, 0.08), col="obs")
    return e


HURDLES = [make_hurdle(k) for k in range(8)]
BARS = [make_bar(k) for k in range(8)]
BLOCKS = {wi: [make_block(k, wi) for k in range(8)] for wi in Gm.USED_WORLDS}
_ord = {}
for _e in Gm.EVENTS:
    _k = _e['type'] if _e['type'] in ('jump', 'duck') else 'block'
    _e['ord'] = _ord.get(_k, 0)
    _ord[_k] = _e['ord'] + 1
COIN_M = mat("coin", (1.0, 0.72, 0.1), 0.18, metal=1.0, emit=(1, 0.6, 0.05), emit_str=0.6)
COIN_ME = mesh_cone(1.0, 32, "coin_me", base_origin=False)
COINS = []
for k in range(80):
    o = _obj(f"coin{k}", COIN_ME, COIN_M, None, "obs")
    o.scale = (0.2, 0.2, 0.04)
    COINS.append(o)


def coin_list():
    out = []
    for i, e in enumerate(Gm.EVENTS):
        lane = e["lane"] * Gm.LANE
        if e["type"] == "jump":
            for j in range(5):
                dy = (j - 2) * 0.9
                out.append((e["s"] + dy, lane, 0.6 + 0.9 * (1 - (dy / 2.2) ** 2), e["t"] + dy / 7.0))
        elif e["type"] == "duck":
            for j in range(4):
                dy = (j - 1.5) * 0.9
                out.append((e["s"] + dy, lane, 0.45, e["t"] + dy / 7.0))
        else:
            for j in range(5):
                dy = 3.0 + j * 1.2
                out.append((e["s"] + dy, e["to"] * Gm.LANE, 0.6, None))
    return out


COIN_LIST = coin_list()

# ------------------------------------------------------------------ sky, sun, camera
world = bpy.data.worlds.new("sky")
scene.world = world
world.use_nodes = True
wn = world.node_tree
bg = wn.nodes["Background"]
sky = wn.nodes.new("ShaderNodeTexSky")
sky.sky_type = "NISHITA"
sky.sun_elevation = math.radians(35)
sky.sun_rotation = math.radians(200)
sky.altitude = 200
sky.air_density = 1.0
sky.dust_density = 0.35
wn.links.new(sky.outputs["Color"], bg.inputs["Color"])
bg.inputs["Strength"].default_value = 0.6
space_bg = wn.nodes.new("ShaderNodeBackground")
stars = wn.nodes.new("ShaderNodeTexNoise")
stars.inputs["Scale"].default_value = 400.0
sramp = wn.nodes.new("ShaderNodeValToRGB")
sramp.color_ramp.elements[0].position = 0.72
sramp.color_ramp.elements[0].color = (0.004, 0.006, 0.03, 1)
sramp.color_ramp.elements[1].position = 0.78
sramp.color_ramp.elements[1].color = (3, 3, 3.5, 1)
wn.links.new(stars.outputs["Fac"], sramp.inputs["Fac"])
wn.links.new(sramp.outputs["Color"], space_bg.inputs["Color"])
wmix = wn.nodes.new("ShaderNodeMixShader")
wout = wn.nodes["World Output"]
wn.links.new(bg.outputs["Background"], wmix.inputs[1])
wn.links.new(space_bg.outputs["Background"], wmix.inputs[2])
wn.links.new(wmix.outputs["Shader"], wout.inputs["Surface"])

sun_d = bpy.data.lights.new("sun", "SUN")
sun_d.energy = 5.0
sun_d.angle = math.radians(3)
sun = bpy.data.objects.new("sun", sun_d)
scene.collection.objects.link(sun)

cam_d = bpy.data.cameras.new("cam")
cam_d.lens = 22 if Gm.SHORT else 24
cam_d.clip_end = 900
cam = bpy.data.objects.new("cam", cam_d)
scene.collection.objects.link(cam)
scene.camera = cam

# compositor glare for sparkle
scene.use_nodes = True
ct = scene.node_tree
rl = ct.nodes.get("Render Layers") or ct.nodes.new("CompositorNodeRLayers")
comp = ct.nodes.get("Composite") or ct.nodes.new("CompositorNodeComposite")
gl = ct.nodes.new("CompositorNodeGlare")
gl.glare_type = "FOG_GLOW"
try:
    gl.threshold = 1.6
    gl.size = 6
    gl.mix = -0.6
except Exception:
    pass
ct.links.new(rl.outputs["Image"], gl.inputs["Image"])
hsv = ct.nodes.new("CompositorNodeHueSat")
hsv.inputs["Saturation"].default_value = 1.35
hsv.inputs["Value"].default_value = 1.03
ct.links.new(gl.outputs["Image"], hsv.inputs["Image"])
ct.links.new(hsv.outputs["Image"], comp.inputs["Image"])


def hsh(n):
    n = (n * 2654435761) & 0xFFFFFFFF
    return ((n ^ (n >> 13)) * 1274126177) & 0xFFFFFFFF


def park(o):
    o.location = (o.location[0], 420.0, -80.0)
    o.scale = (0, 0, 0)


def update_world(t):
    si, s = Gm.seg_at(t)
    wi = s["world"]
    for k, c in WORLD_COLS.items():
        c.hide_render = k != wi
        c.hide_viewport = k != wi
    th = KIT[wi]
    wmix.inputs[0].default_value = 1.0 if th.get("space") else 0.0
    sky.dust_density = th.get("dust", 0.35)
    sun_d.energy = 4.0 if th.get("space") else 5.0
    d = Gm.dist(t)
    for mp in SCROLL:
        mp.inputs["Location"].default_value[1] = d
    sky.sun_elevation = math.radians(th["sun_el"])
    sun.rotation_euler = (math.radians(90 - th["sun_el"]), 0, math.radians(200 - 180 + 25))
    # decor: stable slot per item key -> no swaps between motion-blur sub-steps
    spacing = 6.0
    n0 = int(math.floor((d - 12) / spacing))
    pools = POOL[wi]
    active = [set() for _ in pools]
    for n in range(n0, n0 + 28):
        y = n * spacing - d
        if y < -12 or y > 150:
            continue
        for side in (-1, 1):
            m = n * 2 + (side > 0)
            h = hsh(m + 1000 * wi + 1)
            ty = h % len(pools)
            slot = m % NPOOL
            o = pools[ty][slot]
            active[ty].add(slot)
            off = 3.4 + (h >> 8) % 1000 / 1000 * 6.0
            if wi == 1 and side > 0:
                off = min(off, 7.5)
            if wi in (5, 8) and ty in (0,) :
                off += 5.0
            o.location = (side * (W_ROAD / 2 + off), y + ((h >> 4) % 100) / 100 * 3, 0)
            o.rotation_euler = (0, 0, ((h >> 12) % 628) / 100)
            sc = 0.8 + ((h >> 16) % 100) / 250
            o.scale = (sc, sc, sc)
    for w2 in POOL:
        for ty, objs in enumerate(POOL[w2]):
            for k, o in enumerate(objs):
                if w2 != wi or k not in active[ty]:
                    park(o)
    # obstacles: slot = ordinal of that obstacle type
    used = {"jump": set(), "duck": set(), "block": set()}
    for e in Gm.EVENTS:
        y = e["s"] - d
        if y < -8 or y > 160:
            continue
        if e["type"] == "jump":
            o = HURDLES[e["ord"] % 8]; used["jump"].add(e["ord"] % 8)
            o.location = (0, y, 0); o.scale = (1, 1, 1)
        elif e["type"] == "duck":
            o = BARS[e["ord"] % 8]; used["duck"].add(e["ord"] % 8)
            o.location = (0, y, 0); o.scale = (1, 1, 1)
        else:
            o = BLOCKS[wi][e["ord"] % 8]; used["block"].add(e["ord"] % 8)
            o.location = (e["from"] * Gm.LANE, y + 0.4, 0); o.scale = (1, 1, 1)
            if wi == 1:
                o.rotation_euler = (-(e["s"] - d) / 0.6, 0, 0)
    for objs, kk in ((HURDLES, "jump"), (BARS, "duck")):
        for k, o in enumerate(objs):
            if k not in used[kk]:
                park(o)
    for w2 in BLOCKS:
        for k, o in enumerate(BLOCKS[w2]):
            if w2 != wi or k not in used["block"]:
                park(o)
    # coins: slot = index in coin list; collected coins shrink in place
    char_x = Gm.lane_x(t)
    usedc = set()
    for idx, (s_, x, z, tcol) in enumerate(COIN_LIST):
        y = s_ - d
        if y < -1.0 or y > 110:
            continue
        o = COINS[idx % len(COINS)]
        usedc.add(idx % len(COINS))
        o.location = (x, y, z)
        o.rotation_euler = (math.radians(90), 0, t * 4 + s_)
        sc = 0.0 if (y < 0.35 and abs(x - char_x) < 0.6) else 1.0
        o.scale = (0.2 * sc, 0.2 * sc, 0.04 * sc)
    for k, o in enumerate(COINS):
        if k not in usedc:
            park(o)
    return wi


def update_camera(t, camx):
    # hook: start in front of the fox showing its face, orbit to chase view
    if Gm.SHORT:
        # high chase view: fox sits in the lower third, the road ahead stays visible above its head
        chase = Vector((camx * 0.55, -3.9, 2.75))
        look_chase = Vector((camx * 0.3, 7.0, 0.15))
    else:
        chase = Vector((camx * 0.4, -4.3, 2.5))
        look_chase = Vector((camx * 0.3, 8.0, 0.2))
    if t < 2.0:
        u = max(0.0, (t - 0.35) / 1.65)
        u = u * u * (3 - 2 * u)
        ang = math.pi * u  # 0 = in front, pi = behind
        r = 3.3 - 0.3 * math.sin(ang)
        pos = Vector((math.sin(ang) * r * 0.75, math.cos(ang) * r, 1.15 + 0.4 * u))
        k = max(0.0, (u - 0.65) / 0.35)
        k = k * k * (3 - 2 * k)
        look = Vector((0, 0, 0.95)).lerp(look_chase, k)
        pos = pos.lerp(chase, k)
    else:
        si, s = Gm.seg_at(t)
        lt = t - s["t0"]
        pos, look = chase, look_chase
        if s["kind"] == "outro" and lt > 1.6:
            u = min(1.0, (lt - 1.6) / 1.6)
            u = u * u * (3 - 2 * u)
            pos = chase.lerp(Vector((0, -2.6, 1.35)), u)
            look = look_chase.lerp(Vector((0, 0, 0.95)), u)
    cam.location = pos
    cam.rotation_mode = "QUATERNION"
    cam.rotation_quaternion = (look - pos).to_track_quat("-Z", "Y")


def update(t):
    camx = update_char(t)[0]
    update_world(t)
    update_camera(t, camx)


def on_frame(sc, *args):
    update((sc.frame_current + sc.frame_subframe) / Gm.FPS)


bpy.app.handlers.frame_change_pre.append(on_frame)

def brand_shot(kind, f, out):
    """Stills for channel branding: avatar (fox face, transparent bg) or banner (wide run scene)."""
    scene.render.use_motion_blur = False
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.frame_set(f)
    bpy.app.handlers.frame_change_pre.remove(on_frame)
    if kind == "avatar":
        scene.render.resolution_x = scene.render.resolution_y = 1080
        scene.render.film_transparent = True
        cam_d.lens = 55
        R_ = rec(f / Gm.FPS)
        head = V(R_[31])
        pos = head + Vector((0, -1.25, 0.12))
        look = head + Vector((0, 0, -0.06))
    else:
        scene.render.resolution_x, scene.render.resolution_y = 2560, 1440
        cam_d.lens = 26
        cam_d.shift_x = 0.13
        pos = Vector((0.0, -4.6, 2.1))
        look = Vector((0.0, 6.0, 1.0))
    cam.location = pos
    cam.rotation_mode = "QUATERNION"
    cam.rotation_quaternion = (look - pos).to_track_quat("-Z", "Y")
    scene.render.filepath = out
    bpy.ops.render.render(write_still=True)


if __name__ == "__main__":
    os.makedirs(OUTDIR, exist_ok=True)
    if os.environ.get("BRAND_SHOT"):
        kind, f = os.environ["BRAND_SHOT"].split(":")
        brand_shot(kind, int(f), os.path.join(OUTDIR, kind + ".png"))
        sys.exit()
    if FRAMELIST:
        for f in [int(x) for x in FRAMELIST.split(",")]:
            scene.frame_set(f)
            scene.render.filepath = os.path.join(OUTDIR, "f%05d.jpg" % f)
            bpy.ops.render.render(write_still=True)
    else:
        scene.frame_start, scene.frame_end = FSTART, FEND
        scene.render.filepath = os.path.join(OUTDIR, "f#####")
        bpy.ops.render.render(animation=True)
