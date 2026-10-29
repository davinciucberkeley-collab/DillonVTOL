"""Post-process the full-aircraft SU2 runs into checks and viewer data. Everything here is read from the solver's own
files: the mesh SU2 ran on (out/L{n}/mesh.su2) and its restart (cases/<case>/restart_flow.csv, one row per mesh node
in mesh order). Nothing is interpolated between cases.

Per case:
  * surface pressure: Cp = p / q on every wall triangle (p is gauge pressure, free stream 0: INC_PRESSURE_INIT default)
  * independent force integration: F = -sum(p n A) over the wall triangles, with n oriented into the fluid using the
    tetrahedron each wall triangle belongs to; compared with SU2's own CL / CD / CMy (a bookkeeping and conservation check)
  * the volume field linearly interpolated (barycentric, inside the real tetrahedra) onto a regular grid around the
    starboard half: streamlines (RK4), wake planes (Cp, axial vorticity, crossflow), symmetry-plane slice
  * Trefftz-plane induced drag: CDi = (1/(q S)) * 2 * integral of 1/2 rho (v^2 + w^2) over a crossflow plane behind the
    aircraft (half plane doubled); an estimate independent of the surface integration (limits: numerical dissipation of
    the wake on tetrahedra, plane truncation, the pressure term of the far-field formula is neglected)
  * mesh views: wall triangles, the symmetry-plane triangles, and the exact cut of every tetrahedron crossing a
    crossflow plane (with each cut element's quality), so the viewer shows the computational mesh itself

Usage:  py analysis/cfd3d/postprocess.py L2_a4.0 [L2_a0.0 ...]      -> out/post/<case>.json (+ .npz grids)
        py analysis/cfd3d/postprocess.py pack                       -> out/viz/cfd3d_viz.json (what review/build.mjs embeds)
"""
import base64, gzip, json, math, sys, time
from pathlib import Path

import numpy as np
from scipy.spatial import cKDTree

HERE = Path(__file__).resolve().parent
OUT = HERE / "out"
sys.path.insert(0, str(HERE))
import run_cases as rc  # noqa: E402

Q = 0.5 * rc.RHO * rc.V ** 2
WALLS = rc.MARKERS


# ------------------------------------------------------------------------------------------------ readers
def read_su2(path):
    """tets (N,4) int32, points (M,3), markers {tag: tris (K,3)}"""
    cache = path.with_suffix(".npz")
    if cache.exists() and cache.stat().st_mtime > path.stat().st_mtime:
        z = np.load(cache, allow_pickle=True)
        return z["tets"], z["pts"], z["markers"].item()
    lines = path.read_text().splitlines()
    i = 0
    assert lines[0].startswith("NDIME= 3")
    ne = int(lines[1].split("=")[1]); i = 2
    tets = np.array([ln.split()[1:5] for ln in lines[i:i + ne]], dtype=np.int32); i += ne
    while not lines[i].startswith("NPOIN"):
        i += 1
    npn = int(lines[i].split("=")[1].split()[0]); i += 1
    pts = np.array([ln.split()[:3] for ln in lines[i:i + npn]], dtype=np.float64); i += npn
    markers = {}
    while i < len(lines):
        if lines[i].startswith("MARKER_TAG"):
            tag = lines[i].split("=")[1].strip(); n = int(lines[i + 1].split("=")[1])
            markers[tag] = np.array([ln.split()[1:4] for ln in lines[i + 2:i + 2 + n]], dtype=np.int32); i += 2 + n
        else:
            i += 1
    np.savez(cache, tets=tets, pts=pts, markers=np.array(markers, dtype=object))
    return tets, pts, markers


def read_restart(path):
    with open(path) as f:
        head = [h.strip().strip('"') for h in f.readline().split(",")]
    a = np.loadtxt(path, delimiter=",", skiprows=1)
    a = a[np.argsort(a[:, head.index("PointID")])]
    col = {h: a[:, k] for k, h in enumerate(head)}
    return col


# ------------------------------------------------------------------------------------------------ geometry helpers
def tri_normals(pts, tris):
    a, b, c = pts[tris[:, 0]], pts[tris[:, 1]], pts[tris[:, 2]]
    return 0.5 * np.cross(b - a, c - a)          # area-weighted


def orient_into_fluid(pts, tets, tris):
    """sign so that each wall triangle's normal points into the fluid: find the tet owning the face, compare with
    the direction to its fourth node"""
    faces = np.concatenate([tets[:, [0, 1, 2]], tets[:, [0, 1, 3]], tets[:, [0, 2, 3]], tets[:, [1, 2, 3]]])
    opp = np.concatenate([tets[:, 3], tets[:, 2], tets[:, 1], tets[:, 0]])
    fs = np.sort(faces, axis=1)
    key = (fs[:, 0].astype(np.int64) * (1 << 21) + fs[:, 1]) * (1 << 21) + fs[:, 2]
    order = np.argsort(key)
    ks = key[order]
    ts = np.sort(tris, axis=1)
    tk = (ts[:, 0].astype(np.int64) * (1 << 21) + ts[:, 1]) * (1 << 21) + ts[:, 2]
    pos = np.searchsorted(ks, tk)
    assert np.all(ks[np.minimum(pos, len(ks) - 1)] == tk), "wall triangle without an owning tetrahedron"
    o = opp[order[pos]]
    n = tri_normals(pts, tris)
    cen = pts[tris].mean(axis=1)
    s = np.sign(np.einsum("ij,ij->i", n, pts[o] - cen))
    return n * s[:, None]


def tet_quality(p):
    """normalised radius ratio-like shape measure: 6*sqrt(2)*V / l_rms^3 (1 = regular tetrahedron, 0 = flat)"""
    a, b, c, d = p[:, 0], p[:, 1], p[:, 2], p[:, 3]
    v = np.abs(np.einsum("ij,ij->i", b - a, np.cross(c - a, d - a))) / 6
    e = [b - a, c - a, d - a, c - b, d - b, d - c]
    lrms = np.sqrt(sum((x * x).sum(1) for x in e) / 6)
    return 6 * math.sqrt(2) * v / lrms ** 3


class TetLocator:
    """point location in the solver's tetrahedra: nearest node -> its incident tets (CSR) -> barycentric test;
    a second pass tries the tets of the 8 nearest nodes. Unlocated points are inside the aircraft (masked)."""

    def __init__(self, tets, pts):
        self.tets, self.pts = tets, pts
        n = len(pts)
        flat = tets.ravel(); owner = np.repeat(np.arange(len(tets)), 4)
        order = np.argsort(flat, kind="stable")
        self.ptr = np.zeros(n + 1, np.int64); np.add.at(self.ptr, flat + 1, 1); self.ptr = np.cumsum(self.ptr)
        self.adj = owner[order]
        self.tree = cKDTree(pts)
        P = pts[tets]
        T = np.stack([P[:, 1] - P[:, 0], P[:, 2] - P[:, 0], P[:, 3] - P[:, 0]], axis=2)
        self.Tinv = np.linalg.inv(T)
        self.p0 = P[:, 0]

    def _try(self, q, cand_nodes, tet_out, w_out, todo):
        for node_col in range(cand_nodes.shape[1]):
            idx = np.where(todo)[0]
            if len(idx) == 0:
                return
            nodes = cand_nodes[idx, node_col]
            deg = self.ptr[nodes + 1] - self.ptr[nodes]
            for k in range(int(deg.max())):
                sel = np.where((deg > k) & todo[idx])[0]
                if len(sel) == 0:
                    break
                ii = idx[sel]
                t = self.adj[self.ptr[nodes[sel]] + k]
                lam = np.einsum("nij,nj->ni", self.Tinv[t], q[ii] - self.p0[t])
                w = np.column_stack([1 - lam.sum(1), lam])
                ok = (w > -1e-9).all(1)
                tet_out[ii[ok]] = t[ok]; w_out[ii[ok]] = w[ok]; todo[ii[ok]] = False

    def locate(self, q):
        tet = np.full(len(q), -1, np.int64); w = np.zeros((len(q), 4)); todo = np.ones(len(q), bool)
        _, nn = self.tree.query(q, k=1)
        self._try(q, nn[:, None], tet, w, todo)
        if todo.any():
            ii = np.where(todo)[0]
            _, nn8 = self.tree.query(q[ii], k=8)
            sub_t = np.full(len(ii), -1, np.int64); sub_w = np.zeros((len(ii), 4)); sub_todo = np.ones(len(ii), bool)
            self._try(q[ii], nn8, sub_t, sub_w, sub_todo)
            tet[ii] = sub_t; w[ii] = sub_w; todo[ii] = sub_todo
        return tet, w

    def sample(self, q, fields):
        tet, w = self.locate(q)
        ok = tet >= 0
        out = {}
        for k, f in fields.items():
            v = np.full(len(q), np.nan)
            v[ok] = (f[self.tets[tet[ok]]] * w[ok]).sum(1)
            out[k] = v
        return out, ok


# ------------------------------------------------------------------------------------------------ per case
def post_case(name):
    t0 = time.time()
    lv, alpha = rc.CASES[name]
    d = rc.case_dir(name)
    tets, pts, markers = read_su2(OUT / f"L{lv}" / "mesh.su2")
    sol = read_restart(d / "restart_flow.csv")
    p = sol["Pressure"]; u, v, w = sol["Velocity_x"], sol["Velocity_y"], sol["Velocity_z"]
    assert len(p) == len(pts), "restart rows != mesh nodes"
    res = {"case": name, "level": lv, "alpha_deg": alpha, "generated": time.strftime("%Y-%m-%d %H:%M"),
           "script": "analysis/cfd3d/postprocess.py"}

    # ---- independent surface force integration ----
    ar = math.radians(alpha)
    drag_dir = np.array([math.cos(ar), 0, math.sin(ar)]); lift_dir = np.array([-math.sin(ar), 0, math.cos(ar)])
    ref = np.array([-rc.X_CG, 0, 0])
    comp, F_tot, M_tot = {}, np.zeros(3), np.zeros(3)
    for tag in WALLS:
        tris = markers[tag]
        n = orient_into_fluid(pts, tets, tris)
        pf = p[tris].mean(1)
        F = (pf[:, None] * n)          # force on the body = -p * n_out(body) = +p * n_into_fluid... see note below
        # n points into the fluid, i.e. outward from the body, so the pressure force on the body is -p n
        F = -F
        r = pts[tris].mean(1) - ref
        Ft, Mt = F.sum(0), np.cross(r, F).sum(0)
        F_tot += Ft; M_tot += Mt
        comp[tag] = {"CL": float(Ft @ lift_dir / (Q * rc.S_REF / 2)), "CD": float(Ft @ drag_dir / (Q * rc.S_REF / 2)),
                     "CMy": float(Mt[1] / (Q * rc.S_REF / 2 * rc.C_REF)), "area_m2": float(np.linalg.norm(n, axis=1).sum())}
    res["integrated"] = {"CL": float(F_tot @ lift_dir / (Q * rc.S_REF / 2)), "CD": float(F_tot @ drag_dir / (Q * rc.S_REF / 2)),
                         "CMy": float(M_tot[1] / (Q * rc.S_REF / 2 * rc.C_REF)), "components": comp}

    # ---- symmetry-plane mass-flux check: the symmetry marker must carry no normal velocity ----
    sym_nodes = np.unique(markers["symmetry"])
    res["symmetry_max_abs_vy_over_V"] = float(np.abs(v[sym_nodes]).max() / rc.V)
    # far-field: free stream recovered at the far boundary
    far_nodes = np.unique(markers["farfield"])
    sp = np.sqrt(u ** 2 + v ** 2 + w ** 2)
    res["farfield_speed_ratio"] = {"min": float(sp[far_nodes].min() / rc.V), "max": float(sp[far_nodes].max() / rc.V)}
    res["field_extrema"] = {"speed_max_mps": float(sp.max()), "speed_max_over_V": float(sp.max() / rc.V),
                            "Cp_min": float(p.min() / Q), "Cp_max": float(p.max() / Q),
                            "Cp_min_xyz_su2": pts[int(np.argmin(p))].round(4).tolist()}

    # ---- physical bound on surface pressure: incompressible Cp cannot exceed 1 (stagnation); count violations by part ----
    over = {}
    for tag in WALLS:
        nodes = np.unique(markers[tag]); c = p[nodes] / Q; bad = c > 1.0
        if bad.any():
            k = nodes[np.argmax(c)]
            over[tag] = {"nodes_cp_gt_1": int(bad.sum()), "of_nodes": int(len(nodes)), "cp_max": float(c.max()), "at_su2_m": pts[k].round(4).tolist()}
    res["cp_above_stagnation"] = over

    # ---- grids in the starboard half (SU2 frame) ----
    loc = TetLocator(tets, pts)
    fields = {"u": u, "v": v, "w": w, "p": p}
    h = 0.012
    gx = np.arange(-0.55, 2.60 + 1e-9, h); gy = np.arange(0.0, 1.55 + 1e-9, h); gz = np.arange(-0.40, 0.40 + 1e-9, h)
    G = np.stack(np.meshgrid(gx, gy, gz, indexing="ij"), -1).reshape(-1, 3)
    vals, ok = loc.sample(G, fields)
    shape = (len(gx), len(gy), len(gz))
    U = np.stack([np.nan_to_num(vals[k]).reshape(shape) for k in ("u", "v", "w")], -1)
    Pg = np.nan_to_num(vals["p"]).reshape(shape)
    inside = (~ok).reshape(shape)
    np.savez_compressed(OUT / "post" / f"{name}_grid.npz", gx=gx, gy=gy, gz=gz, U=U.astype(np.float32), P=Pg.astype(np.float32), inside=inside)
    # axial vorticity omega_x = dw/dy - dv/dz
    om_x = np.gradient(U[..., 2], h, axis=1) - np.gradient(U[..., 1], h, axis=2)
    om_x[inside] = 0

    # ---- streamlines (RK4 on the grid, trilinear) ----
    from scipy.interpolate import RegularGridInterpolator
    Ui = RegularGridInterpolator((gx, gy, gz), U, bounds_error=False, fill_value=np.nan)
    Pi = RegularGridInterpolator((gx, gy, gz), Pg, bounds_error=False, fill_value=np.nan)
    # rakes chosen to show the physics, not to fill space: just above and below the wing chord plane ahead of the LE
    # (upwash, acceleration over the upper surface, downwash), a ring at the starboard tip trailing edge (roll-up into
    # the tip vortex), and lines past the pod, booms, motors and tail
    seeds = []
    for y in np.linspace(0.10, 1.12, 11):
        for z in (-0.035, 0.045):
            seeds.append((-0.35, y, z))
    for th in np.linspace(0, 2 * math.pi, 14, endpoint=False):
        seeds.append((0.29, 1.185 + 0.025 * math.cos(th), 0.004 + 0.025 * math.sin(th)))
    for y, z in ((0.02, -0.08), (0.02, 0.06), (0.02, 0.0), (0.433, -0.035), (0.433, 0.055), (0.40, -0.10), (0.30, -0.06), (0.22, 0.02)):
        seeds.append((-0.55, y, z))
    X = np.array(seeds, float); lines = [[x] for x in X]; alive = np.ones(len(X), bool)
    ds = 0.008
    def vel(q):
        vv = Ui(q); n = np.linalg.norm(vv, axis=1, keepdims=True)
        return vv / np.where(n > 1e-6, n, np.nan)
    for _ in range(420):
        idx = np.where(alive)[0]
        if not len(idx):
            break
        q = X[idx]
        k1 = vel(q); k2 = vel(q + 0.5 * ds * k1); k3 = vel(q + 0.5 * ds * k2); k4 = vel(q + ds * k3)
        qn = q + ds / 6 * (k1 + 2 * k2 + 2 * k3 + k4)
        bad = ~np.isfinite(qn).all(1)
        # stop at the grid edge, inside the body (zero velocity), or on NaN
        Uq = Ui(np.nan_to_num(qn)); spd = np.linalg.norm(Uq, axis=1)
        bad |= ~np.isfinite(spd) | (spd < 0.05 * rc.V)
        X[idx[~bad]] = qn[~bad]
        for j, i in enumerate(idx):
            if not bad[j]:
                lines[i].append(qn[j].copy())
        alive[idx[bad]] = False
    stream = []
    for L in lines:
        L = np.array(L)
        if len(L) < 8:
            continue
        L = L[::2]
        s = np.linalg.norm(Ui(L), axis=1) / rc.V
        cp = Pi(L) / Q
        stream.append({"xyz": L.round(4).ravel().tolist(), "s": np.nan_to_num(s).round(3).tolist(), "cp": np.nan_to_num(cp).round(3).tolist()})

    # ---- wake / crossflow planes and the symmetry plane ----
    planes = []
    for xs in (0.30, 0.95, 1.6, 2.4):
        i = int(round((xs - gx[0]) / h))
        planes.append({"x": float(gx[i]), "ny": len(gy), "nz": len(gz), "y0": float(gy[0]), "z0": float(gz[0]), "h": h,
                       "cp": (Pg[i] / Q).round(3).ravel().tolist(), "omx": (om_x[i] * rc.C_REF / rc.V).round(3).ravel().tolist(),
                       "v": (U[i, :, :, 1] / rc.V).round(3).ravel().tolist(), "w": (U[i, :, :, 2] / rc.V).round(3).ravel().tolist(),
                       "inside": inside[i].ravel().astype(int).tolist()})
    sym = {"nx": len(gx), "nz": len(gz), "x0": float(gx[0]), "z0": float(gz[0]), "h": h,
           "cp": (Pg[:, 0, :] / Q).round(3).ravel().tolist(), "s": (np.linalg.norm(U[:, 0, :, :], axis=-1) / rc.V).round(3).ravel().tolist(),
           "inside": inside[:, 0, :].ravel().astype(int).tolist()}

    # ---- tip-vortex core track: min axial-vorticity location near the tip at each wake station ----
    track = []
    for i in range(0, len(gx), 4):
        if gx[i] < 0.30:
            continue
        jy = (gy > 0.9) & (gy < 1.4); jz = np.abs(gz) < 0.2
        sl = om_x[i][np.ix_(jy, jz)]
        k = np.unravel_index(np.argmax(sl), sl.shape)
        peak = float(sl[k] * rc.C_REF / rc.V)
        if peak < 0.5:      # core dissipated on this mesh: stop rather than chase noise
            break
        track.append([float(gx[i]), float(gy[jy][k[0]]), float(gz[jz][k[1]]), peak])
    res["tip_vortex_track"] = track

    # ---- Trefftz-plane induced drag on crossflow planes behind the wing (0.3 m behind the TE, then 1.0 and 1.7 m) ----
    tref = []
    for xt in (0.60, 1.30, 2.00):
        ty = np.arange(0.0, 4.0 + 1e-9, 0.02); tz = np.arange(-2.0, 2.0 + 1e-9, 0.02)
        T = np.stack(np.meshgrid([xt], ty, tz, indexing="ij"), -1).reshape(-1, 3)
        tv, tok = loc.sample(T, {"v": v, "w": w, "u": u})
        # perturbation velocity relative to the free stream, resolved normal to the free-stream direction:
        # v' (spanwise) and w'' = -u' sin(alpha) + w' cos(alpha); points inside the body or unlocated are dropped
        u_p = tv["u"] - rc.V * math.cos(ar); w_p = tv["w"] - rc.V * math.sin(ar)
        vv = np.where(tok, tv["v"], 0.0); ww = np.where(tok, -u_p * math.sin(ar) + w_p * math.cos(ar), 0.0)
        dA = 0.02 * 0.02 * np.where((T[:, 1] == 0) | (np.abs(T[:, 2]) == 2.0), 0.5, 1.0)
        Di_half = float((0.5 * rc.RHO * (vv ** 2 + ww ** 2) * dA).sum())
        tref.append({"x_su2_m": xt, "CDi": 2 * Di_half / (Q * rc.S_REF), "located_fraction": float(tok.mean())})
    res["trefftz"] = {"CDi": tref[0]["CDi"], "x_su2_m": tref[0]["x_su2_m"], "planes": tref, "plane_y_m": [0, 4], "plane_z_m": [-2, 2], "spacing_m": 0.02,
                      "note": "far-field kinetic-energy estimate on planes normal to x; the first plane (0.3 m behind the wing TE, ahead of the tail) is reported. The decay further aft is numerical dissipation of the trailing vortices on tetrahedra; the u' term of the far-field formula is neglected"}

    # ---- mesh views: wall + symmetry triangles; exact tet cut by the crossflow plane x = xc ----
    xc = 0.14   # wing mid-chord (SU2 x = -X_cad)
    P4 = pts[tets]
    s = P4[:, :, 0] - xc
    cross = (s.min(1) < 0) & (s.max(1) > 0)
    cen = P4.mean(1)
    win = cross & (cen[:, 1] < 1.45) & (np.abs(cen[:, 2]) < 0.35)
    cut_t = np.where(win)[0]
    polys, qual = [], tet_quality(P4[cut_t])
    edges = [(0, 1), (0, 2), (0, 3), (1, 2), (1, 3), (2, 3)]
    for j, t in enumerate(cut_t):
        q4, s4 = P4[t], s[t]
        poly = []
        for a, b in edges:
            if (s4[a] < 0) != (s4[b] < 0):
                f = s4[a] / (s4[a] - s4[b]); poly.append(q4[a] + f * (q4[b] - q4[a]))
        if len(poly) == 4:   # order the quad around its centroid
            c = np.mean(poly, 0); ang = [math.atan2(pp[2] - c[2], pp[1] - c[1]) for pp in poly]
            poly = [poly[k] for k in np.argsort(ang)]
        polys.append(np.array(poly)[:, 1:].round(5).ravel().tolist())
    res["mesh_cut"] = {"x_su2_m": xc, "n_cut_tets": int(len(cut_t)), "quality_min": float(qual.min()), "quality_p05": float(np.percentile(qual, 5))}

    res["timing_s"] = round(time.time() - t0, 1)
    (OUT / "post").mkdir(exist_ok=True)
    (OUT / "post" / f"{name}.json").write_text(json.dumps(res, indent=1))
    viz = {"stream": stream, "planes": planes, "sym": sym, "cut": {"x": xc, "polys": polys, "q": qual.round(3).tolist()},
           "cp_nodes": (p / Q).astype(np.float32), "speed_nodes": (sp / rc.V).astype(np.float32)}
    np.savez_compressed(OUT / "post" / f"{name}_viz.npz", cp=viz["cp_nodes"], s=viz["speed_nodes"])
    (OUT / "post" / f"{name}_viz.json").write_text(json.dumps({k: viz[k] for k in ("stream", "planes", "sym", "cut")}))
    print(json.dumps({k: res[k] for k in ("integrated", "symmetry_max_abs_vy_over_V", "farfield_speed_ratio", "field_extrema", "trefftz", "mesh_cut", "timing_s")}, indent=1))


# ------------------------------------------------------------------------------------------------ viewer pack
def b64gz(a):
    """numpy array -> base64 of the gzipped raw bytes (the page inflates it with DecompressionStream)"""
    return base64.b64encode(gzip.compress(np.ascontiguousarray(a).tobytes(), 9)).decode()


def pack(level=2):
    """out/viz/cfd3d_viz.json: the wall mesh of one level (SU2 frame, quantised), per-case Cp and speed on it,
    streamlines, wake planes, symmetry slice, the tet cut, residual histories, mesh statistics and the results"""
    tets, pts, markers = read_su2(OUT / f"L{level}" / "mesh.su2")
    groups, tri_all = [], []
    for tag in WALLS:
        groups.append({"name": tag, "i0": int(sum(len(t) for t in tri_all)), "n": int(len(markers[tag]))}); tri_all.append(markers[tag])
    tris = np.concatenate(tri_all)
    used = np.unique(tris)
    remap = np.full(len(pts), -1, np.int64); remap[used] = np.arange(len(used))
    P = pts[used]; lo, hi = P.min(0), P.max(0)
    qP = np.round((P - lo) / (hi - lo) * 65535).astype(np.uint16)
    # symmetry-plane triangles near the aircraft (the volume mesh's footprint on y = 0)
    st = markers["symmetry"]; sc = pts[st].mean(1)
    st = st[(sc[:, 0] > -1.2) & (sc[:, 0] < 3.0) & (np.abs(sc[:, 2]) < 0.9)]
    su = np.unique(st); smap = {int(v): i for i, v in enumerate(su)}
    viz = {"generated": time.strftime("%Y-%m-%d %H:%M"), "script": "analysis/cfd3d/postprocess.py pack", "level": level,
           "frame": "SU2 (x aft, y starboard, z up); the page maps to the CAD frame X=-x, Y=z, Z=y and mirrors to port",
           "surf": {"lo": lo.tolist(), "hi": hi.tolist(), "pos": b64gz(qP), "idx": b64gz(remap[tris].astype(np.uint32)), "nv": int(len(used)), "groups": groups},
           "symmesh": {"pos": b64gz(pts[su].astype(np.float32)), "idx": b64gz(np.vectorize(smap.get)(st).astype(np.uint32)), "n": int(len(st))},
           "levels": {}, "cases": {}, "results": json.loads((OUT / "cfd3d_results.json").read_text()) if (OUT / "cfd3d_results.json").exists() else None}
    for lv in (1, 2, 3):
        f = OUT / f"L{lv}" / "mesh_stats.json"
        if f.exists():
            viz["levels"][lv] = json.loads(f.read_text())
    # wing-tip patch of every level's wall mesh, for the side-by-side resolution comparison
    for lv in (1, 2, 3):
        f = OUT / f"L{lv}" / "mesh.su2"
        if not f.exists():
            continue
        _, pl, ml = read_su2(f)
        t = ml["wing"]; c = pl[t].mean(1)
        t = t[(c[:, 1] > 0.95) & (c[:, 2] > 0)]           # upper surface, outer 0.25 m
        u = np.unique(t); m = np.full(len(pl), -1); m[u] = np.arange(len(u))
        viz["levels"][lv]["tip_patch"] = {"pos": b64gz(pl[u].astype(np.float32)), "idx": b64gz(m[t].astype(np.uint32)), "n": int(len(t))}
    for name, (lv, a) in rc.CASES.items():
        if lv != level or not (OUT / "post" / f"{name}_viz.json").exists():
            continue
        z = np.load(OUT / "post" / f"{name}_viz.npz")
        v = json.loads((OUT / "post" / f"{name}_viz.json").read_text())
        cp = np.clip(np.round(z["cp"][used] * 40), -127, 127).astype(np.int8)
        sp = np.clip(np.round(z["s"][used] * 100), 0, 255).astype(np.uint8)
        head, rows = rc.read_history(rc.case_dir(name)); col = {h: i for i, h in enumerate(head)}
        rows = np.array(rows)
        leg1 = rc.case_dir(name) / "history_leg1.csv"
        if leg1.exists():   # warm restart of the same case: first leg up to its last restart write, then the second leg after it
            h1, r1 = rc.read_history_file(leg1); r1 = np.array(r1); it = h1.index("Inner_Iter")
            cut = int(r1[-1, it]) // 500 * 500
            rows[:, col["Inner_Iter"]] += cut
            rows = np.vstack([r1[r1[:, it] < cut], rows])
        step = max(1, len(rows) // 400)
        hist = {k: rows[::step, col[c]].round(6).tolist() for k, c in (("it", "Inner_Iter"), ("rp", "rms[P]"), ("ru", "rms[U]"), ("cl", "CL"), ("cd", "CD"), ("cm", "CMy")) if c in col}
        st = v["stream"]
        stream = {"n": b64gz(np.array([len(L["s"]) for L in st], np.uint16)),
                  "xyz": b64gz(np.round(np.concatenate([L["xyz"] for L in st]) * 1000).astype(np.int16)),          # mm
                  "s": b64gz(np.clip(np.round(np.concatenate([L["s"] for L in st]) * 100), 0, 255).astype(np.uint8))}
        q8 = lambda arr, k: b64gz(np.clip(np.round(np.array(arr) * k), -127, 127).astype(np.int8))
        planes = [{"x": pl["x"], "ny": pl["ny"], "nz": pl["nz"], "y0": pl["y0"], "z0": pl["z0"], "h": pl["h"],
                   "cp": q8(pl["cp"], 100), "omx": q8(pl["omx"], 20), "inside": b64gz(np.array(pl["inside"], np.uint8))} for pl in v["planes"]]
        sy = v["sym"]
        sym = {k: sy[k] for k in ("nx", "nz", "x0", "z0", "h")}
        sym.update({"cp": q8(sy["cp"], 40), "s": b64gz(np.clip(np.round(np.array(sy["s"]) * 100), 0, 255).astype(np.uint8)), "inside": b64gz(np.array(sy["inside"], np.uint8))})
        viz["cases"][name] = {"alpha": a, "cp": b64gz(cp), "s": b64gz(sp), "stream": stream, "planes": planes, "sym": sym, "hist": hist,
                              "post": json.loads((OUT / "post" / f"{name}.json").read_text())}
        if a == 4.0:
            cut = v["cut"]
            viz["cut"] = {"x": cut["x"], "n": b64gz(np.array([len(q) // 2 for q in cut["polys"]], np.uint8)),
                          "yz": b64gz(np.concatenate([np.array(q, np.float32) for q in cut["polys"]])),
                          "q": b64gz(np.clip(np.round(np.array(cut["q"]) * 255), 0, 255).astype(np.uint8)), "count": len(cut["polys"])}
    geo = json.loads((OUT / "oml_fidelity.json").read_text())
    notes = {"Wing": "STEP includes the saddle side tabs (removed)", "Pod": "OCC bounding box of the revolved spline is loose (pod radius 80 mm)", "Canopy": "OCC bounding box of the revolved spline is loose",
             "Lift_Motor": "4 mm shaft stub removed", "Pusher_Motor": "4 mm shaft stub removed", "Boom_Clamp_F": "top extended 4 mm into the wing (bonded joint)",
             "Boom_Clamp_R": "top extended 4 mm into the wing (bonded joint)", "Tail_Clamp": "top extended 3 mm into the stabiliser", "Fin_Shoe": "extended 2 mm into the stabiliser",
             "Gear_Fairing": "top extended 1.2 mm to the gear clamp (taped joint)", "H_Tail": "elevator gap sealed", "Fin": "rudder gap sealed"}
    viz["geometry"] = {"defeaturing": geo["defeaturing"], "fidelity": [dict(r, note=notes.get(r["part"], "")) for r in geo["fidelity"]]}
    cf = HERE.parent / "validation" / "claims_cfd.json"
    viz["checks"] = json.loads(cf.read_text())["claims"] if cf.exists() else None
    viz["post"] = {n: c["post"] for n, c in viz["cases"].items()}
    for n in rc.CASES:   # post-processed cases on other mesh levels, for the results table
        f = OUT / "post" / f"{n}.json"
        if n not in viz["post"] and f.exists():
            viz["post"][n] = json.loads(f.read_text())
    (OUT / "viz").mkdir(exist_ok=True)
    s = json.dumps(viz, separators=(",", ":"))
    (OUT / "viz" / "cfd3d_viz.json").write_text(s)
    print("packed", len(s) // 1024, "KB,", len(viz["cases"]), "cases")


if __name__ == "__main__":
    (OUT / "post").mkdir(exist_ok=True)
    if sys.argv[1:] == ["pack"]:
        pack()
    else:
        for n in sys.argv[1:]:
            post_case(n)
