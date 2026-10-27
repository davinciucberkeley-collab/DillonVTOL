"""Photoreal renders of the test set-ups and the aircraft, built in Blender from the real CAD meshes.

Run with Blender 4.2 (Cycles, GPU when available):
    blender -b --factory-startup -P docs/figures/render_scenes.py -- [scene ...]
Scenes: studio, cg_weigh, tethered, thrust_stand, car_roof, proof_load (default: all).

Geometry: every part from cad/mesh/*.STL (metres, part frame), placed by its comp= record in cad/params.txt
(x, y, z and a 3 x 3 rotation, SOLIDWORKS frame: X forward, Y up, Z right) - the same data the review's 3-D viewer
uses, so the renders always match the model. Fixtures (scales, stand, stakes, sandbags, car roof) are simple modelled
props, sized from the test plan; they are illustrations, not designs.
Output: docs/figures/renders/<scene>.png and <scene>.json, the pixel position of each labelled feature, which
docs/figures/make_figures.py uses to place callouts on the render.
"""
import json, math, os, sys
import bpy
from mathutils import Matrix, Vector
from bpy_extras.object_utils import world_to_camera_view

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MESH = os.path.join(ROOT, 'cad', 'mesh')
OUT = os.path.join(ROOT, 'docs', 'figures', 'renders')
W, H = 1600, 1000
META = json.load(open(os.path.join(MESH, 'meta.json'), encoding='utf-8'))
# SOLIDWORKS Y-up to Blender Z-up: (x, y, z)_sw -> (x, -z, y)_blender
SW2B = Matrix(((1, 0, 0, 0), (0, 0, -1, 0), (0, 1, 0, 0), (0, 0, 0, 1)))


def comps():
    out = []
    for line in open(os.path.join(ROOT, 'cad', 'params.txt'), encoding='utf-8'):
        if not line.startswith('comp='): continue
        f = line.strip()[5:].split('|')
        r = [float(v) for v in f[4].split(',')]
        out.append((f[0], Vector((float(f[1]), float(f[2]), float(f[3]))), Matrix(((r[0], r[1], r[2]), (r[3], r[4], r[5]), (r[6], r[7], r[8])))))
    return out


# ---------------------------------------------------------------- scene set-up
def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'
    try:
        prefs = bpy.context.preferences.addons['cycles'].preferences
        prefs.compute_device_type = 'OPTIX'; prefs.get_devices()
        for d in prefs.devices: d.use = True
        sc.cycles.device = 'GPU'
    except Exception:
        sc.cycles.device = 'CPU'
    sc.cycles.samples = 160; sc.cycles.use_denoising = True
    sc.render.resolution_x, sc.render.resolution_y = W, H
    sc.render.film_transparent = False
    sc.view_settings.view_transform = 'AgX'; sc.view_settings.look = 'AgX - Medium High Contrast'
    world = bpy.data.worlds.new('w'); sc.world = world; world.use_nodes = True
    bg = world.node_tree.nodes['Background']; bg.inputs[0].default_value = (0.30, 0.32, 0.35, 1); bg.inputs[1].default_value = 0.35
    sc.view_settings.exposure = -0.3
    return sc


_mats = {}
def mat(name, color, rough=0.45, metal=0.0, coat=0.0, alpha=1.0):
    key = (name, tuple(round(c, 3) for c in color), rough, metal, alpha)
    if key in _mats: return _mats[key]
    m = bpy.data.materials.new(name); m.use_nodes = True
    p = m.node_tree.nodes['Principled BSDF']
    p.inputs['Base Color'].default_value = (*color, 1); p.inputs['Roughness'].default_value = rough
    p.inputs['Metallic'].default_value = metal
    if coat: p.inputs['Coat Weight'].default_value = coat
    if alpha < 1:
        p.inputs['Alpha'].default_value = alpha; m.blend_method = 'BLEND'
    _mats[key] = m
    return m


def part_material(part):
    n = part
    if n.startswith(('Wing_Panel', 'Aileron', 'H_Tail', 'Elevator', 'Fin', 'Rudder', 'Fuselage_Pod', 'Wing_Saddle')):
        return mat('foam skin', (0.72, 0.74, 0.77), 0.35, coat=0.4)
    if n == 'Canopy': return mat('canopy', (0.05, 0.08, 0.13), 0.08, coat=1.0)
    if n.startswith(('Boom_Front', 'Boom_Rear', 'Spar_Tube', 'Wing_Joiner', 'Landing_Leg', 'Pitot_Tube')):
        return mat('6061 aluminium', (0.80, 0.81, 0.83), 0.28, metal=1.0)
    if n.startswith(('Lift_Prop', 'Pusher_Prop')): return mat('carbon prop', (0.03, 0.03, 0.035), 0.3, coat=0.6)
    if n.startswith(('Lift_Motor', 'Pusher_Motor')): return mat('motor', (0.09, 0.09, 0.1), 0.35, metal=0.8)
    if n.startswith(('Motor_Mount', 'Pusher_Cup')): return mat('PA6-CF', (0.13, 0.13, 0.14), 0.6)
    if n.startswith('Battery_6S'): return mat('battery', (0.12, 0.25, 0.55), 0.5)
    if n.startswith(('Flight_Controller', 'ESC', 'Receiver', 'GPS')): return mat('circuit board', (0.05, 0.22, 0.12), 0.4)   # electronics read as boards, not as printed parts
    if n[:1] in 'FNWI' and n[1:3].isdigit(): return mat('steel', (0.62, 0.63, 0.65), 0.3, metal=1.0)
    c = META.get(n, {}).get('c', [0.55, 0.57, 0.6])
    return mat('PETG ' + n, tuple(c), 0.5)


def crisp(me, angle=35):
    """smooth shading across shallow angles only, so machined edges stay sharp (CAD meshes are faceted)"""
    try:
        me.shade_smooth(); me.set_sharp_from_angle(angle=math.radians(angle))
    except AttributeError:
        for poly in me.polygons: poly.use_smooth = True


_meshes = {}
def aircraft(keep=None, xform=Matrix.Identity(4)):
    """place every component (or those whose part name passes keep) under one root; returns the root"""
    root = bpy.data.objects.new('C0', None); bpy.context.collection.objects.link(root)
    root.matrix_world = xform @ SW2B
    for part, pos, rot in comps():
        if keep and not keep(part): continue
        if part not in _meshes:
            path = os.path.join(MESH, part + '.STL')
            if not os.path.exists(path): continue
            bpy.ops.wm.stl_import(filepath=path)
            ob = bpy.context.selected_objects[0]; me = ob.data
            bpy.data.objects.remove(ob); _meshes[part] = me
            crisp(me)
            me.materials.append(part_material(part))
        ob = bpy.data.objects.new(part, _meshes[part]); bpy.context.collection.objects.link(ob)
        m = rot.to_4x4(); m.translation = pos
        ob.parent = root; ob.matrix_parent_inverse = Matrix.Identity(4); ob.matrix_local = m
        try:
            ob.modifiers.new('bevelsmooth', 'WEIGHTED_NORMAL')
        except Exception:
            pass
    bpy.context.view_layer.update()
    return root


def sw(p):
    """a point in the aircraft (SOLIDWORKS) frame -> Blender world, before any extra placement"""
    return SW2B @ Vector(p)


def box(name, loc, size, material, bevel=0.004):
    bpy.ops.mesh.primitive_cube_add(location=loc)
    ob = bpy.context.active_object; ob.name = name; ob.scale = (size[0] / 2, size[1] / 2, size[2] / 2)
    bpy.ops.object.transform_apply(scale=True)
    if bevel:
        b = ob.modifiers.new('bev', 'BEVEL'); b.width = bevel; b.segments = 3
    ob.data.materials.append(material)
    for p in ob.data.polygons: p.use_smooth = True
    return ob


def cyl(name, a, b, r, material, verts=32):
    a, b = Vector(a), Vector(b); d = b - a
    bpy.ops.mesh.primitive_cylinder_add(vertices=verts, radius=r, depth=d.length, location=(a + b) / 2)
    ob = bpy.context.active_object; ob.name = name
    ob.rotation_mode = 'QUATERNION'; ob.rotation_quaternion = Vector((0, 0, 1)).rotation_difference(d)
    ob.data.materials.append(material)
    return ob


def floor(material, z=0.0, size=40, cyc=True):
    """studio floor; with cyc a seamless sweep up into a back wall (at +y, behind the subject) so no horizon shows"""
    if not cyc:
        bpy.ops.mesh.primitive_plane_add(size=size, location=(0, 0, z))
        ob = bpy.context.active_object; ob.data.materials.append(material); return ob
    import bmesh
    prof = [(-12.0, 0.0)] + [(3.0 + 3.0 * math.sin(a), 3.0 - 3.0 * math.cos(a)) for a in [i * math.pi / 2 / 16 for i in range(17)]] + [(6.0, 10.0)]
    me = bpy.data.meshes.new('cyc'); bm = bmesh.new()
    rows = [[bm.verts.new((x, y, z + h)) for (y, h) in prof] for x in (-12.0, 12.0)]
    for i in range(len(prof) - 1):
        bm.faces.new((rows[0][i], rows[1][i], rows[1][i + 1], rows[0][i + 1]))
    bm.to_mesh(me); bm.free()
    for poly in me.polygons: poly.use_smooth = True
    ob = bpy.data.objects.new('cyc', me); bpy.context.collection.objects.link(ob); me.materials.append(material)
    return ob


def studio_lights(target=(0, 0, 0.3), power=1.0):
    def area(name, loc, energy, size, color=(1, 1, 1)):
        L = bpy.data.lights.new(name, 'AREA'); L.energy = energy * power; L.size = size; L.color = color
        ob = bpy.data.objects.new(name, L); bpy.context.collection.objects.link(ob); ob.location = loc
        d = Vector(target) - Vector(loc); ob.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
    area('key', (3.0, -3.5, 4.0), 1100, 2.0)
    area('fill', (-4.0, -2.0, 2.5), 220, 4.0, (0.90, 0.94, 1.0))
    area('rim', (-1.0, 4.0, 3.5), 700, 2.0)
    area('top', (0, 0, 5.0), 400, 5.0)


def outdoor(sun_elev=38, sun_rot=150):
    """physical sky and a sun lamp, for the field scenes"""
    w = bpy.context.scene.world; nt = w.node_tree
    sky = nt.nodes.new('ShaderNodeTexSky'); sky.sky_type = 'NISHITA'; sky.sun_elevation = math.radians(sun_elev); sky.sun_rotation = math.radians(sun_rot)
    nt.links.new(sky.outputs['Color'], nt.nodes['Background'].inputs['Color']); nt.nodes['Background'].inputs['Strength'].default_value = 0.22
    sun = bpy.data.lights.new('sun', 'SUN'); sun.energy = 3.2; sun.angle = math.radians(1.5)
    ob = bpy.data.objects.new('sun', sun); bpy.context.collection.objects.link(ob)
    ob.rotation_euler = (math.radians(90 - sun_elev), 0, math.radians(sun_rot))


def grass_mat():
    m = bpy.data.materials.new('grass'); m.use_nodes = True; nt = m.node_tree; p = nt.nodes['Principled BSDF']
    noise = nt.nodes.new('ShaderNodeTexNoise'); noise.inputs['Scale'].default_value = 60; noise.inputs['Detail'].default_value = 8
    ramp = nt.nodes.new('ShaderNodeValToRGB'); ramp.color_ramp.elements[0].color = (0.035, 0.09, 0.025, 1); ramp.color_ramp.elements[1].color = (0.11, 0.2, 0.05, 1)
    nt.links.new(noise.outputs['Fac'], ramp.inputs['Fac']); nt.links.new(ramp.outputs['Color'], p.inputs['Base Color'])
    bump = nt.nodes.new('ShaderNodeBump'); bump.inputs['Strength'].default_value = 0.6
    nt.links.new(noise.outputs['Fac'], bump.inputs['Height']); nt.links.new(bump.outputs['Normal'], p.inputs['Normal'])
    p.inputs['Roughness'].default_value = 0.95
    return m


def camera(loc, target, lens=50):
    cam = bpy.data.cameras.new('cam'); cam.lens = lens
    ob = bpy.data.objects.new('cam', cam); bpy.context.collection.objects.link(ob); ob.location = loc
    d = Vector(target) - Vector(loc); ob.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
    bpy.context.scene.camera = ob
    return ob


def render(name, anchors):
    sc = bpy.context.scene; os.makedirs(OUT, exist_ok=True)
    sc.render.filepath = os.path.join(OUT, name + '.png'); bpy.ops.render.render(write_still=True)
    pts = {}
    for k, p in anchors.items():
        v = world_to_camera_view(sc, sc.camera, Vector(p))
        pts[k] = [round(v.x * W, 1), round((1 - v.y) * H, 1)]
    json.dump({'size': [W, H], 'anchors': pts}, open(os.path.join(OUT, name + '.json'), 'w'), indent=1)
    print('rendered', name)


def world_of(obname):
    ob = bpy.data.objects.get(obname)
    return ob.matrix_world.translation.copy() if ob else Vector((0, 0, 0))


def bbox_world(ob_names_prefix):
    pts = [o.matrix_world @ Vector(c) for o in bpy.data.objects if o.type == 'MESH' and o.name.startswith(ob_names_prefix) for c in o.bound_box]
    lo = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    hi = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    return lo, hi


def lowest_z():
    zs = [(o.matrix_world @ Vector(c)).z for o in bpy.data.objects if o.type == 'MESH' and o.parent and o.parent.name == 'C0' for c in o.bound_box]
    return min(zs)


# ---------------------------------------------------------------- scenes
def scene_studio():
    reset(); root = aircraft(); bpy.context.view_layer.update()
    root.location.z -= lowest_z(); bpy.context.view_layer.update()
    floor(mat('studio floor', (0.30, 0.32, 0.35), 0.45))
    studio_lights((0, 0, 0.3)); camera((2.05, -2.45, 1.35), (-0.08, 0, 0.22), 38)
    render('studio', {'pod': (0.35, 0, 0.3)})


def scene_cg_weigh():
    reset(); root = aircraft(); bpy.context.view_layer.update()
    lift = 0.06                                                  # scales and boards under the legs
    root.location.z -= lowest_z() - lift; bpy.context.view_layer.update()
    floor(mat('bench', (0.30, 0.32, 0.35), 0.45))
    wood = mat('board', (0.62, 0.45, 0.28), 0.6); dark = mat('scale', (0.12, 0.12, 0.13), 0.4); lcd = mat('lcd', (0.55, 0.75, 0.62), 0.2)
    anchors = {}
    for i, xs in enumerate((0.301, -0.460)):                    # front and rear gear stations (comp Landing_Leg x)
        p = sw((xs, 0, 0))
        box(f'scale{i}', (p.x, 0, 0.022), (0.22, 0.22, 0.044), dark)
        box(f'lcd{i}', (p.x + 0.06, -0.111, 0.03), (0.07, 0.004, 0.025), lcd, 0)
        box(f'board{i}', (p.x, 0, 0.052), (0.12, 1.0, 0.016), wood)
        anchors[f'scale{i+1}'] = (p.x, -0.11, 0.03)
    lo, hi = bbox_world('Wing_Panel_R')
    anchors['wing'] = ((lo.x + hi.x) / 2, (lo.y + hi.y) / 2, hi.z)
    cg = sw((-0.0796, 0, 0)); anchors['cg'] = (cg.x, 0, hi.z + 0.02)
    studio_lights((0, 0, 0.3)); camera((1.75, -2.05, 1.05), (-0.08, 0, 0.12), 36)
    render('cg_weigh', anchors)


def scene_tethered():
    reset(); root = aircraft(); bpy.context.view_layer.update()
    root.location.z -= lowest_z() - 1.0; bpy.context.view_layer.update()
    floor(grass_mat(), 0, 80, cyc=False)
    rope = mat('tether', (0.85, 0.45, 0.1), 0.6); steel = mat('stake', (0.5, 0.5, 0.52), 0.35, metal=1.0)
    anchors = {}
    for i, z in enumerate((0.4337, -0.4337)):                   # tethers from the front gear clamps
        top = (root.matrix_world @ Vector((0.301, -0.06, z)))
        stake = Vector((top.x + 0.25, top.y + (1 if top.y > 0 else -1) * 1.1, 0.02))
        mid = (top + stake) / 2; mid.z -= 0.35                    # slack
        curve = bpy.data.curves.new(f't{i}', 'CURVE'); curve.dimensions = '3D'; curve.bevel_depth = 0.004
        sp = curve.splines.new('BEZIER'); sp.bezier_points.add(2)
        for bp, p in zip(sp.bezier_points, (top, mid, stake)):
            bp.co = p; bp.handle_left_type = bp.handle_right_type = 'AUTO'
        ob = bpy.data.objects.new(f'tether{i}', curve); bpy.context.collection.objects.link(ob); curve.materials.append(rope)
        cyl(f'stake{i}', stake + Vector((0, 0, -0.1)), stake + Vector((0, 0, 0.12)), 0.008, steel, 12)
        anchors[f'stake{i+1}'] = tuple(stake); anchors[f'tether{i+1}'] = tuple(mid)
    anchors['aircraft'] = tuple(root.matrix_world @ Vector((0.3, 0.05, 0)))
    anchors['ground_below'] = tuple(root.matrix_world.translation * Vector((1, 1, 0)))
    outdoor(32, 140)
    camera((3.7, -3.3, 2.05), (0.1, 0, 0.6), 32)
    render('tethered', anchors)


def scene_thrust_stand():
    reset()
    unit = lambda n: n in ('Lift_Motor', 'Motor_Mount_Upper', 'Motor_Mount_Cap', 'Prop_Plate', 'Lift_Prop')
    root = aircraft(unit)
    # keep only the front-right unit: everything placed near the front-right station
    keep_c = sw((0.391, 0, 0.434))
    for o in list(bpy.data.objects):
        if o.type == 'MESH' and o.parent == root and (o.matrix_world.translation - keep_c).length > 0.12:
            bpy.data.objects.remove(o)
    bpy.context.view_layer.update()
    # move the unit so its boom bore centre sits on the beam end, 0.42 m above the bench
    c = keep_c.copy(); root.location = Vector((-0.25, 0, 0.42)) - c + Vector((0, 0, 0.0)); bpy.context.view_layer.update()
    alu = mat('extrusion', (0.78, 0.79, 0.81), 0.3, metal=1.0); wood = mat('plywood', (0.72, 0.56, 0.36), 0.6)
    blue = mat('load cell', (0.15, 0.32, 0.75), 0.4); pcb = mat('electronics', (0.1, 0.35, 0.18), 0.5); dark = mat('dark', (0.1, 0.1, 0.11), 0.5)
    floor(mat('bench', (0.30, 0.32, 0.35), 0.45))
    box('base', (0, 0, 0.012), (0.9, 0.3, 0.024), wood)
    box('post', (0, 0, 0.2), (0.04, 0.04, 0.38), alu)
    cyl('pivot', (0, -0.04, 0.4), (0, 0.04, 0.4), 0.008, mat('steel', (0.62, 0.63, 0.65), 0.3, metal=1.0))
    box('beam', (0, 0, 0.405), (0.56, 0.025, 0.025), alu)
    box('loadcell', (0.25, 0, 0.36), (0.13, 0.03, 0.03), blue)
    box('cellpost', (0.25, 0, 0.17), (0.04, 0.04, 0.32), alu)
    box('hx711', (0.17, 0.08, 0.03), (0.06, 0.04, 0.012), pcb)
    box('esc', (-0.12, 0.08, 0.045), (0.06, 0.03, 0.012), dark)
    studio_lights((0, 0, 0.35), 0.8); camera((0.62, -0.95, 0.66), (-0.04, 0, 0.33), 40)
    render('thrust_stand', {'motor': (-0.25, 0, 0.46), 'pivot': (0, -0.04, 0.4), 'cell': (0.25, -0.015, 0.36), 'hx711': (0.17, 0.08, 0.036), 'esc': (-0.12, 0.08, 0.05)})


def scene_car_roof():
    reset()
    unit = lambda n: n in ('Lift_Motor', 'Motor_Mount_Upper', 'Motor_Mount_Cap', 'Prop_Plate', 'Lift_Prop')
    root = aircraft(unit); keep_c = sw((0.391, 0, 0.434))
    for o in list(bpy.data.objects):
        if o.type == 'MESH' and o.parent == root and (o.matrix_world.translation - keep_c).length > 0.12:
            bpy.data.objects.remove(o)
    root.location = Vector((0, 0, 1.95)) - keep_c; bpy.context.view_layer.update()
    paint = mat('car paint', (0.06, 0.09, 0.14), 0.25, coat=1.0); glass = mat('glass', (0.05, 0.07, 0.09), 0.05, coat=1.0)
    alu = mat('rack', (0.12, 0.12, 0.13), 0.4, metal=0.6); steel = mat('steel', (0.62, 0.63, 0.65), 0.3, metal=1.0)
    floor(mat('asphalt', (0.035, 0.035, 0.04), 0.85), cyc=False)
    box('roof', (0, 0, 1.45), (2.0, 1.45, 0.06), paint, 0.05)
    box('body', (0, 0, 0.95), (4.2, 1.8, 0.9), paint, 0.12)
    box('glass', (0.9, 0, 1.25), (0.9, 1.4, 0.35), glass, 0.05)
    for y in (-0.5, 0.5): box(f'bar{y}', (0, y, 1.53), (1.9, 0.05, 0.03), alu)
    cyl('mast', (0, 0.5, 1.53), (0, 0.5, 1.9), 0.0127, steel)
    box('arm', (0, 0.25, 1.92), (0.04, 0.5, 0.02), steel)
    box('scale', (0.0, 0.5, 1.75), (0.03, 0.03, 0.12), mat('luggage scale', (0.15, 0.32, 0.75), 0.4))
    outdoor(30, 200)
    camera((0.95, -0.95, 2.02), (0.0, 0.18, 1.86), 36)
    render('car_roof', {'prop': tuple(keep_c + root.location + Vector((0, 0, 0.035))), 'scale': (0.0, 0.5, 1.75), 'mast': (0, 0.5, 1.6), 'flow': (1.4, 0, 2.0)})


def scene_proof_load():
    reset()
    wing = lambda n: n.startswith(('Wing_Panel', 'Aileron', 'Wing_Saddle', 'Wing_Joiner', 'Spar_Tube', 'Joiner_Stop', 'Root_Tongue', 'Bolt_Pillar'))
    flip = Matrix.Rotation(math.pi, 4, 'X')                      # inverted for the test
    root = aircraft(wing, flip); bpy.context.view_layer.update()
    root.location.z -= lowest_z() - 0.45; bpy.context.view_layer.update()
    lo, hi = bbox_world('Wing_Panel')
    foam = mat('padding', (0.25, 0.25, 0.27), 0.9); wood = mat('support', (0.62, 0.45, 0.28), 0.6)
    bag = mat('sandbag', (0.66, 0.58, 0.42), 0.95)
    floor(mat('floor', (0.30, 0.32, 0.35), 0.45))
    for y in (-0.1, 0.1):
        box(f'support{y}', ((lo.x + hi.x) / 2, y, 0.22), (0.35, 0.06, 0.44), wood)
        box(f'pad{y}', ((lo.x + hi.x) / 2, y, 0.447), (0.35, 0.07, 0.014), foam)
    kg = [1.64, 1.59, 1.49, 1.33, 1.08, 0.62]                    # test plan S01 schedule, per side
    sx = lo.x + 0.30 * (hi.x - lo.x) / 1.0
    anchors = {}
    for side in (-1, 1):
        for st, k in zip((0.1, 0.3, 0.5, 0.7, 0.9, 1.1), kg):
            h = 0.03 + 0.05 * k / 1.64
            box(f'bag{side}{st}', ((lo.x + hi.x) / 2 + 0.02, side * st, hi.z + h / 2), (0.16, 0.13, h), bag, 0.02)
        gx, gy = (lo.x + hi.x) / 2, side * 1.17                  # tip gauge: a ruler standing beside the tip
        box(f'gauge{side}', (gx - 0.2, gy, 0.3), (0.025, 0.012, 0.6), mat('gauge', (0.15, 0.32, 0.75), 0.4))
        anchors[f'tip{side}'] = (gx - 0.2, gy, 0.42)
    anchors['bag'] = ((lo.x + hi.x) / 2, 0.5, hi.z + 0.06); anchors['support'] = ((lo.x + hi.x) / 2 + 0.17, 0.1, 0.3)
    studio_lights((0, 0, 0.5), 0.85); camera((2.45, -2.25, 1.75), ((lo.x + hi.x) / 2, 0.05, 0.38), 32)
    render('proof_load', anchors)


SCENES = {'studio': scene_studio, 'cg_weigh': scene_cg_weigh, 'tethered': scene_tethered, 'thrust_stand': scene_thrust_stand,
          'car_roof': scene_car_roof, 'proof_load': scene_proof_load}

if __name__ == '__main__':
    args = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    for name in (args or list(SCENES)):
        _mats.clear(); _meshes.clear()
        SCENES[name]()
