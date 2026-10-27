"""Blender toolkit for the step-by-step figures of the build manual and test plan.

A figure is a short function in step_specs.py that receives a Scene (S) and calls:
  S.assembly(focus, context, ghost)   the C0 assembly from the CAD meshes; focus parts orange, context as built,
                                      ghost translucent, everything else hidden (patterns: 'Part', 'Part-2', 'Part*', '*')
  S.part(name, loc, rot)              one CAD part on its own (e.g. on the print bed), SOLIDWORKS frame -> world
  S.tube / S.foam / S.bow / ...       simple shop props (illustrative; sized from the build manual)
  S.mark(name, point)                 a named anchor for a callout
  S.label(anchor, text)               a callout (placed on the image by annotate_steps.py)
  S.caption(lines)                    the caption band: first line bold (what to do), then details / the check
  S.view(az, el, target=..., fit=...) camera: azimuth and elevation in degrees, framed to fit the named objects
Geometry of every aircraft part is exact (cad/mesh, placed by cad/params.txt); props are not designs.
"""
import json, math, os, re, sys
import bpy
from mathutils import Matrix, Vector
from bpy_extras.object_utils import world_to_camera_view

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import render_scenes as RS                                                   # meshes, materials, lights, floor

OUT = os.path.join(HERE, 'renders', 'steps')
W, H = 1600, 1000


def _match(name, part, pats):
    for p in pats:
        p = p.strip()
        if not p: continue
        if p == '*' or p == name or p == part: return True
        if p.endswith('*') and part.startswith(p[:-1]): return True
    return False


class Scene:
    def __init__(self, fid, kind='studio'):
        self.id, self.labels, self.lines, self.anchors, self.objs = fid, [], [], {}, {}
        RS._mats.clear(); RS._meshes.clear()
        RS.reset()
        sc = bpy.context.scene; sc.cycles.samples = 128
        self.kind = kind
        self._style(sc)
        if kind == 'studio':
            RS.floor(RS.mat('studio floor', (0.30, 0.32, 0.35), 0.45))
        elif kind == 'bench':
            # one large bench top instead of a studio sweep, so no edge, horizon or coplanar floor shows in close-ups
            RS.floor(RS.mat('workbench', (0.36, 0.25, 0.15), 0.55), 0, 60, cyc=False)
            # a low camera sees past the bench to the world: give it a warm haze instead of a dark band
            bg = sc.world.node_tree.nodes['Background']; bg.inputs[0].default_value = (0.42, 0.36, 0.30, 1); bg.inputs[1].default_value = 1.0
        elif kind == 'field':
            RS.floor(RS.grass_mat(), 0, 120, cyc=False)

    def _style(self, sc):
        """technical-illustration look: saturated colour (Standard view) and Freestyle outlines on silhouettes,
        borders and creases, so every part reads clearly even when it is pale or see-through"""
        sc.view_settings.view_transform = 'AgX'; sc.view_settings.look = 'AgX - Punchy'; sc.view_settings.exposure = -0.35
        sc.render.use_freestyle = True; sc.render.line_thickness_mode = 'ABSOLUTE'; sc.render.line_thickness = 1.0
        vl = sc.view_layers[0]; vl.use_freestyle = True; fs = vl.freestyle_settings; fs.crease_angle = math.radians(138)
        ls = fs.linesets[0] if len(fs.linesets) else fs.linesets.new('lines')
        ls.select_by_visibility = True; ls.visibility = 'VISIBLE'; ls.select_by_edge_types = True
        ls.select_silhouette = True; ls.select_border = True; ls.select_crease = True; ls.select_external_contour = True
        st = ls.linestyle or bpy.data.linestyles.new('outline'); ls.linestyle = st
        st.color = (0.10, 0.11, 0.13); st.thickness = 1.25; st.alpha = 0.9

    # ------------------------------------------------------------ materials
    ACCENT = None
    def accent(self):
        return RS.mat('step accent', (0.80, 0.30, 0.03), 0.4, coat=0.15)

    def ghost_mat(self, base):
        return RS.mat('ghost ' + base, (0.62, 0.70, 0.80), 0.3, alpha=0.2)

    # ------------------------------------------------------------ aircraft parts
    def assembly(self, focus=(), context=(), ghost=(), xform=None, lift=None):
        """the C0 assembly; returns the root. lift: put the lowest point at this height (m)"""
        xform = xform or Matrix.Identity(4)
        root = bpy.data.objects.new('C0', None); bpy.context.collection.objects.link(root); root.matrix_world = xform @ RS.SW2B
        count = {}
        for part, pos, rot in RS.comps():
            count[part] = count.get(part, 0) + 1; name = f'{part}-{count[part]}'
            if _match(name, part, focus): m = self.accent()
            elif _match(name, part, context): m = None
            elif _match(name, part, ghost): m = self.ghost_mat(part)
            else: continue
            me = self._mesh(part)
            if me is None: continue
            ob = bpy.data.objects.new(name, me); bpy.context.collection.objects.link(ob)
            if m is not None:
                ob.material_slots[0].link = 'OBJECT'; ob.material_slots[0].material = m
            mm = rot.to_4x4(); mm.translation = pos
            ob.parent = root; ob.matrix_parent_inverse = Matrix.Identity(4); ob.matrix_local = mm
            self.objs[name] = ob
        bpy.context.view_layer.update()
        if lift is not None:
            root.location.z += lift - self._lowest(root); bpy.context.view_layer.update()
        return root

    def _mesh(self, part):
        if part not in RS._meshes:
            path = os.path.join(RS.MESH, part + '.STL')
            if not os.path.exists(path): return None
            bpy.ops.wm.stl_import(filepath=path)
            ob = bpy.context.selected_objects[0]; me = ob.data; bpy.data.objects.remove(ob)
            RS.crisp(me)
            me.materials.append(RS.part_material(part)); RS._meshes[part] = me
        return RS._meshes[part]

    def _lowest(self, root):
        zs = [(o.matrix_world @ Vector(c)).z for o in bpy.data.objects if o.type == 'MESH' and o.parent == root for c in o.bound_box]
        return min(zs) if zs else 0.0

    def part(self, part, loc=(0, 0, 0), rot=(0, 0, 0), name=None, accent=False, sit=True):
        """one CAD part on its own: rot in degrees about world X, Y, Z (applied to the Blender-frame part);
        sit: rest its lowest point on z = loc.z"""
        me = self._mesh(part); name = name or part
        ob = bpy.data.objects.new(name, me); bpy.context.collection.objects.link(ob)
        if accent:
            ob.material_slots[0].link = 'OBJECT'; ob.material_slots[0].material = self.accent()
        R = (Matrix.Rotation(math.radians(rot[2]), 4, 'Z') @ Matrix.Rotation(math.radians(rot[1]), 4, 'Y') @ Matrix.Rotation(math.radians(rot[0]), 4, 'X'))
        ob.matrix_world = Matrix.Translation(Vector(loc)) @ R @ RS.SW2B
        bpy.context.view_layer.update()
        if sit:
            z = min((ob.matrix_world @ Vector(c)).z for c in ob.bound_box); ob.location.z += loc[2] - z
        bpy.context.view_layer.update(); self.objs[name] = ob
        return ob

    def at(self, name, where='top'):
        """a point on an object's world bounding box: top, centre, front (-y side), bottom, end+x, end-x"""
        bpy.context.view_layer.update()
        ob = self.objs.get(name) or bpy.data.objects.get(name)
        pts = [ob.matrix_world @ Vector(c) for c in ob.bound_box]
        lo = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
        hi = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
        c = (lo + hi) / 2
        return {'top': Vector((c.x, c.y, hi.z)), 'centre': c, 'front': Vector((c.x, lo.y, c.z)), 'bottom': Vector((c.x, c.y, lo.z)),
                'end+x': Vector((hi.x, c.y, c.z)), 'end-x': Vector((lo.x, c.y, c.z))}[where]

    def bbox(self, names, pad=0.05):
        bpy.context.view_layer.update(); pts = []
        for n in names:
            if n in self.anchors:                                       # a named point counts as a small box around it
                c = Vector(self.anchors[n]); pts += [c - Vector((pad, pad, pad)), c + Vector((pad, pad, pad))]; continue
            ob = self.objs.get(n) or bpy.data.objects.get(n)
            if ob is None: continue
            if ob.type == 'EMPTY':
                for ch in ob.children: pts += [ch.matrix_world @ Vector(c) for c in ch.bound_box]
            elif ob.type in ('MESH', 'CURVE'):
                pts += [ob.matrix_world @ Vector(c) for c in ob.bound_box]
        lo = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
        hi = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
        return lo, hi

    def keep_near(self, pattern, near, r):
        """drop the objects matching pattern that lie farther than r (m) from object near (e.g. loose inserts)"""
        c = self.at(near, 'centre')
        for n in self.match(pattern):
            if (self.at(n, 'centre') - c).length > r:
                bpy.data.objects.remove(self.objs.pop(n))

    def match(self, *pats):
        return [n for n in self.objs if any(_match(n, n.rsplit('-', 1)[0], [p]) for p in pats)]

    # ------------------------------------------------------------ props
    def box(self, name, loc, size, material, bevel=0.003):
        ob = RS.box(name, loc, size, material, bevel); self.objs[name] = ob; return ob

    def cyl(self, name, a, b, r, material, verts=32):
        ob = RS.cyl(name, a, b, r, material, verts); self.objs[name] = ob; return ob

    def tube(self, name, a, b, od=0.0254, material=None):
        return self.cyl(name, a, b, od / 2, material or RS.mat('6061 aluminium', (0.80, 0.81, 0.83), 0.28, metal=1.0), 40)

    def foam(self, name, loc, size, color='pink'):
        c = {'pink': (0.88, 0.36, 0.47), 'blue': (0.45, 0.62, 0.86), 'white': (0.9, 0.9, 0.9)}[color]
        return self.box(name, loc, size, RS.mat('XPS ' + color, c, 0.85), 0.002)

    def plate(self, name, loc, size, color=(0.55, 0.42, 0.28), rough=0.6):
        return self.box(name, loc, size, RS.mat('plate ' + name, color, rough), 0.002)

    def airfoil_plate(self, name, loc, chord, t=0.006, code='2415', rot_z=0):
        """a hot-wire template: the NACA section as a hardboard plate standing on its edge"""
        import bmesh
        m, p, tt = int(code[0]) / 100, int(code[1]) / 10, int(code[2:]) / 100
        pts = []
        for i in range(41):
            x = 0.5 * (1 - math.cos(math.pi * i / 40)); yt = 5 * tt * (0.2969 * math.sqrt(x) - 0.126 * x - 0.3516 * x * x + 0.2843 * x ** 3 - 0.1036 * x ** 4)
            yc = (m / p ** 2 * (2 * p * x - x * x)) if (p and x < p) else ((m / (1 - p) ** 2) * ((1 - 2 * p) + 2 * p * x - x * x) if p else 0)
            pts.append((x, yc + yt))
        pts += [(x, 2 * (yc0 if False else 0) - 0) for x, _ in []]
        lower = []
        for i in range(40, -1, -1):
            x = 0.5 * (1 - math.cos(math.pi * i / 40)); yt = 5 * tt * (0.2969 * math.sqrt(x) - 0.126 * x - 0.3516 * x * x + 0.2843 * x ** 3 - 0.1036 * x ** 4)
            yc = (m / p ** 2 * (2 * p * x - x * x)) if (p and x < p) else ((m / (1 - p) ** 2) * ((1 - 2 * p) + 2 * p * x - x * x) if p else 0)
            lower.append((x, yc - yt))
        prof = pts + lower[1:-1]
        me = bpy.data.meshes.new(name); bm = bmesh.new()
        f = [bm.verts.new((-x * chord, 0, y * chord)) for x, y in prof]; face = bm.faces.new(f)
        r = bmesh.ops.extrude_face_region(bm, geom=[face]); vs = [g for g in r['geom'] if isinstance(g, bmesh.types.BMVert)]
        bmesh.ops.translate(bm, verts=vs, vec=(0, t, 0)); bm.to_mesh(me); bm.free()
        ob = bpy.data.objects.new(name, me); bpy.context.collection.objects.link(ob)
        me.materials.append(RS.mat('hardboard', (0.45, 0.33, 0.22), 0.65))
        ob.location = loc; ob.rotation_euler = (0, 0, math.radians(rot_z)); self.objs[name] = ob
        return ob

    def bow(self, name, a, b, height=0.35):
        """hot-wire bow: wire from a to b, with the frame above it"""
        a, b = Vector(a), Vector(b); up = Vector((0, 0, height)); wood = RS.mat('bow frame', (0.55, 0.4, 0.25), 0.6)
        self.cyl(name + ' arm1', a, a + up, 0.012, wood); self.cyl(name + ' arm2', b, b + up, 0.012, wood)
        self.cyl(name + ' top', a + up, b + up, 0.014, wood)
        self.cyl(name, a, b, 0.0022, RS.mat('nichrome', (0.95, 0.35, 0.1), 0.3, metal=0.6), 8)
        return self.objs[name]

    def calipers(self, name, loc, rot_z=0):
        st = RS.mat('caliper steel', (0.72, 0.73, 0.75), 0.25, metal=1.0)
        g = [self.box(name, (loc[0], loc[1], loc[2] + 0.004), (0.2, 0.016, 0.004), st),
             self.box(name + ' jaw1', (loc[0] - 0.09, loc[1] - 0.02, loc[2] + 0.004), (0.01, 0.04, 0.004), st),
             self.box(name + ' jaw2', (loc[0] - 0.04, loc[1] - 0.02, loc[2] + 0.004), (0.01, 0.04, 0.004), st),
             self.box(name + ' display', (loc[0] - 0.02, loc[1] + 0.012, loc[2] + 0.008), (0.05, 0.022, 0.008), RS.mat('caliper body', (0.1, 0.1, 0.1), 0.4))]
        for o in g: o.rotation_euler.z = math.radians(rot_z)
        return g[0]

    def kitchen_scale(self, name, loc, size=(0.2, 0.2, 0.03)):
        self.box(name, (loc[0], loc[1], loc[2] + size[2] / 2), size, RS.mat('scale', (0.12, 0.12, 0.13), 0.4))
        self.box(name + ' lcd', (loc[0], loc[1] - size[1] / 2 + 0.002, loc[2] + size[2] * 0.6), (0.07, 0.004, 0.018), RS.mat('lcd', (0.55, 0.75, 0.62), 0.2), 0)
        return self.objs[name]

    def vise(self, name, loc, jaw=0.1):
        iron = RS.mat('vise', (0.2, 0.33, 0.45), 0.45, metal=0.4)
        self.box(name, (loc[0], loc[1], loc[2] + 0.04), (0.18, 0.12, 0.08), iron)
        self.box(name + ' jaw', (loc[0], loc[1] - 0.03, loc[2] + 0.1), (jaw, 0.02, 0.05), iron)
        self.box(name + ' jaw2', (loc[0], loc[1] + 0.03, loc[2] + 0.1), (jaw, 0.02, 0.05), iron)
        return self.objs[name]

    def weight(self, name, top, mass_kg=1.0, w=0.1):
        """a hanging water jug on a cord from point top; w: jug width (narrow where it hangs close to a support)"""
        top = Vector(top); h = (0.04 + 0.12 * min(mass_kg, 5) / 5) * (0.1 / w) ** 0.5
        self.cyl(name + ' cord', top, top - Vector((0, 0, 0.18)), 0.0015, RS.mat('cord', (0.85, 0.45, 0.1), 0.6), 8)
        return self.box(name, tuple(top - Vector((0, 0, 0.18 + h / 2))), (w, w, h), RS.mat('jug', (0.75, 0.85, 0.95), 0.15, alpha=0.92), 0.01)

    def dial_gauge(self, name, loc):
        self.cyl(name + ' post', loc, (loc[0], loc[1], loc[2] + 0.2), 0.008, RS.mat('steel', (0.62, 0.63, 0.65), 0.3, metal=1.0))
        return self.cyl(name, (loc[0], loc[1] - 0.01, loc[2] + 0.22), (loc[0], loc[1] + 0.01, loc[2] + 0.22), 0.03, RS.mat('gauge face', (0.95, 0.95, 0.92), 0.3))

    def tool_bar(self, name, a, b, r, color, metal=0.0):
        return self.cyl(name, a, b, r, RS.mat(name, color, 0.4, metal=metal))

    def torque_driver(self, name, tip, direction=(0, 0, 1)):
        tip = Vector(tip); d = Vector(direction).normalized()
        self.cyl(name + ' bit', tip, tip + d * 0.06, 0.0025, RS.mat('steel', (0.62, 0.63, 0.65), 0.3, metal=1.0), 12)
        return self.cyl(name, tip + d * 0.06, tip + d * 0.19, 0.016, RS.mat('driver handle', (0.75, 0.15, 0.12), 0.4))

    def soldering_iron(self, name, tip, direction=(0.6, 0, 0.8)):
        tip = Vector(tip); d = Vector(direction).normalized()
        self.cyl(name + ' tip', tip, tip + d * 0.05, 0.002, RS.mat('iron tip', (0.5, 0.5, 0.5), 0.3, metal=1.0), 12)
        return self.cyl(name, tip + d * 0.05, tip + d * 0.2, 0.011, RS.mat('iron grip', (0.15, 0.15, 0.17), 0.5))

    def heat_gun(self, name, nozzle, direction=(0, 0, -1)):
        n = Vector(nozzle); d = Vector(direction).normalized()
        self.cyl(name + ' nozzle', n, n - d * 0.06, 0.012, RS.mat('steel', (0.62, 0.63, 0.65), 0.3, metal=1.0))
        body = self.cyl(name, n - d * 0.06, n - d * 0.2, 0.03, RS.mat('heat gun', (0.85, 0.55, 0.1), 0.4))
        self.cyl(name + ' grip', n - d * 0.15, n - d * 0.15 + Vector((0, 0, -0.1)), 0.016, RS.mat('grip', (0.1, 0.1, 0.1), 0.5))
        return body

    def printer(self, name, centre, bed=0.25):
        c = Vector(centre); dark = RS.mat('printer frame', (0.12, 0.12, 0.13), 0.4); bedm = RS.mat('PEI bed', (0.62, 0.52, 0.3), 0.35)
        self.box(name + ' base', (c.x, c.y, c.z + 0.03), (bed + 0.12, bed + 0.12, 0.06), dark)
        self.box(name, (c.x, c.y, c.z + 0.065), (bed, bed, 0.006), bedm, 0.002)
        for dx in (-1, 1):
            self.box(name + f' post{dx}', (c.x + dx * (bed / 2 + 0.04), c.y + bed / 2 + 0.02, c.z + 0.22), (0.03, 0.03, 0.38), dark)
        self.box(name + ' gantry', (c.x, c.y + bed / 2 + 0.02, c.z + 0.36), (bed + 0.12, 0.04, 0.03), dark)
        return self.objs[name]

    def phone(self, name, loc, rot=(70, 0, 0)):
        # built at the origin, then tilted and moved, so the tilt turns it about its own centre
        ob = self.box(name, (0, 0, 0), (0.075, 0.009, 0.155), RS.mat('phone', (0.06, 0.06, 0.07), 0.2, coat=1.0), 0.003)   # bevel under half the 9 mm thickness or the mesh collapses
        ob.rotation_euler = tuple(math.radians(r) for r in rot); ob.location = Vector(loc) + ob.location
        bpy.context.view_layer.update(); return ob

    def laptop(self, name, loc):
        self.box(name, (loc[0], loc[1], loc[2] + 0.01), (0.34, 0.24, 0.02), RS.mat('laptop', (0.6, 0.62, 0.65), 0.3, metal=0.6))
        scr = self.box(name + ' screen', (loc[0], loc[1] + 0.12, loc[2] + 0.12), (0.34, 0.012, 0.22), RS.mat('laptop screen', (0.12, 0.2, 0.32), 0.15))
        scr.rotation_euler.x = math.radians(-12); return self.objs[name]

    def ir_thermometer(self, name, loc, aim=(1, 0, 0)):
        d = Vector(aim).normalized(); l = Vector(loc)
        body = self.cyl(name, l, l + d * 0.12, 0.018, RS.mat('ir gun', (0.95, 0.75, 0.1), 0.4))
        self.cyl(name + ' grip', l + d * 0.03, l + d * 0.03 + Vector((0, 0, -0.09)), 0.013, RS.mat('grip', (0.1, 0.1, 0.1), 0.5))
        return body

    def psu(self, name, loc, label_color=(0.15, 0.15, 0.17)):
        self.box(name, (loc[0], loc[1], loc[2] + 0.07), (0.22, 0.25, 0.14), RS.mat('bench supply', label_color, 0.4))
        self.box(name + ' panel', (loc[0], loc[1] - 0.126, loc[2] + 0.08), (0.18, 0.004, 0.09), RS.mat('psu panel', (0.25, 0.4, 0.55), 0.3), 0)
        return self.objs[name]

    def battery(self, name, loc, rot_z=0):
        ob = self.box(name, (loc[0], loc[1], loc[2] + 0.024), (0.155, 0.05, 0.048), RS.mat('lipo', (0.12, 0.25, 0.55), 0.5), 0.004)
        ob.rotation_euler.z = math.radians(rot_z); return ob

    def esc(self, name, loc, rot_z=0):
        ob = self.box(name, loc, (0.06, 0.028, 0.012), RS.mat('esc shrink', (0.1, 0.1, 0.11), 0.45), 0.003)
        ob.rotation_euler.z = math.radians(rot_z); return ob

    def wire(self, name, pts, color=(0.8, 0.1, 0.08), r=0.0018):
        curve = bpy.data.curves.new(name, 'CURVE'); curve.dimensions = '3D'; curve.bevel_depth = r
        sp = curve.splines.new('BEZIER'); sp.bezier_points.add(len(pts) - 1)
        for bp, p in zip(sp.bezier_points, pts):
            bp.co = p; bp.handle_left_type = bp.handle_right_type = 'AUTO'
        ob = bpy.data.objects.new(name, curve); bpy.context.collection.objects.link(ob); curve.materials.append(RS.mat('wire ' + str(color), color, 0.45))
        self.objs[name] = ob; return ob

    def tape_roll(self, name, loc, color=(0.85, 0.85, 0.82)):
        return self.cyl(name, loc, (loc[0], loc[1], loc[2] + 0.05), 0.05, RS.mat('tape', color, 0.35))

    def stripe(self, name, centre, size, color=(0.05, 0.05, 0.05)):
        """a drawn mark (marker line, tape mark): a very thin coloured box"""
        return self.box(name, centre, size, RS.mat('mark ' + str(color), color, 0.6), 0)

    # ------------------------------------------------------------ annotation and camera
    def mark(self, name, point):
        self.anchors[name] = tuple(point)

    def label(self, anchor, text, side=None):
        bpy.context.view_layer.update()
        p = anchor if not isinstance(anchor, str) else (self.anchors[anchor] if anchor in self.anchors else tuple(self.at(anchor, 'top')))
        self.labels.append({'p': list(p), 'text': text, 'side': side})

    def caption(self, *lines):
        self.lines = list(lines)

    def view(self, az=35, el=28, fit=None, lens=45, margin=1.18, target=None):
        if fit:
            lo, hi = self.bbox(fit)
        else:
            lo, hi = self.bbox([n for n in self.objs if n != 'bench mat'])
        c = Vector(target) if target else (lo + hi) / 2; r = max((hi - lo).length / 2, 0.02)
        fov = 2 * math.atan(18 / lens)                                  # 36 mm sensor width
        dist = r * margin / math.sin(fov / 2) * (W / H) ** -0.15
        d = Vector((math.cos(math.radians(el)) * math.cos(math.radians(az)), -math.cos(math.radians(el)) * math.sin(math.radians(az)) * -1, math.sin(math.radians(el))))
        d = Vector((math.cos(math.radians(el)) * math.sin(math.radians(az)), -math.cos(math.radians(el)) * math.cos(math.radians(az)), math.sin(math.radians(el))))
        cam = RS.camera(tuple(c + d * dist), tuple(c), lens)
        # refine the distance on the projected box corners, so tall subjects fit the frame height as wide ones fit its width:
        # the farthest corner sits 0.5 / margin of the frame from the centre
        sc = bpy.context.scene; want = 0.5 / margin
        corners = [Vector((x, y, z)) for x in (lo.x, hi.x) for y in (lo.y, hi.y) for z in (lo.z, hi.z)]
        for _ in range(6):
            bpy.context.view_layer.update(); ps = [world_to_camera_view(sc, cam, q) for q in corners]
            if min(q.z for q in ps) <= 0: dist *= 1.5
            else:
                ext = max(max(abs(q.x - 0.5), abs(q.y - 0.5)) for q in ps)
                if abs(ext / want - 1) < 0.02: break
                dist *= ext / want
            cam.location = c + d * dist
        if self.kind == 'field': RS.outdoor(34, 140)
        else: RS.studio_lights(tuple(c), max(0.5, min(1.4, 1.0 * (r / 0.5) ** 0.5)))
        return cam

    def render(self):
        sc = bpy.context.scene; os.makedirs(OUT, exist_ok=True)
        sc.render.filepath = os.path.join(OUT, self.id + '.png'); bpy.ops.render.render(write_still=True)
        out = []
        for L in self.labels:
            v = world_to_camera_view(sc, sc.camera, Vector(L['p']))
            out.append({'x': round(v.x * W, 1), 'y': round((1 - v.y) * H, 1), 'text': L['text'], 'side': L['side']})
        json.dump({'size': [W, H], 'labels': out, 'lines': self.lines}, open(os.path.join(OUT, self.id + '.json'), 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
        print('rendered', self.id)
