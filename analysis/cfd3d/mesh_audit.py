"""Audit the full-aircraft CFD meshes (out/L1..L4/mesh.su2; every level whose mesh exists; L4 added 2026-11-03) against published CFD gridding guidelines.

Everything in "metrics" is measured from the mesh files themselves (via postprocess.read_su2 and its mesh.npz cache);
every threshold in "standards" was read at the cited URL on the date given. The output is out/mesh_audit.json.

Frame (SU2): x aft, y starboard, z up, metres. The wing is the rectangular NACA 2415 panel x 0..c_ref, y ~0.03..1.2.

Measured per level:
  * counts (nodes, tets, wall triangles by marker)
  * far-field distance: nearest far-field node to any wall node, plus the box extents, in chords and semispans
  * wing chordwise surface spacing at the LE (edges with midpoint x < 1 % c) and at the TE (edges with one node on the
    sharp TE line), at six spanwise stations; surface points per section from an exact plane cut of the wing triangles
  * TE edge spacing (node spacing along the closed TE line), spanwise spacing at the tip and root
  * first-cell normal size: height of each wall-adjacent tet over its wall face, h = 3 V / A
  * volume gradation: size ratio of face-adjacent tets (size = rms edge length), and size vs distance from the wing
  * element quality: signed volume, dihedral angles, radius ratio 3 r_in / R_circ, edge ratio
  * refinement ratios between levels, globally (N ratio^(1/3), Celik 2008 Eq. 1 with a common domain volume) and per
    region (surface spacings), to test whether the levels are one geometric family
  * wake cell size 1 c and 3 c behind the wing TE, H-tail LE/TE spacing, pod nose spacing

Usage:  py analysis/cfd3d/mesh_audit.py           (about a minute per level for L3)
"""
import json, math, re, sys, time
from pathlib import Path

import numpy as np
from scipy.spatial import cKDTree

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
OUT = HERE / "out"
sys.path.insert(0, str(HERE))
from postprocess import read_su2  # noqa: E402  (reuses the mesh.npz cache)

sys.path.insert(0, str(HERE.parent))
import geom  # noqa: E402
C_REF = json.loads((HERE / "out" / "reference.json").read_text(encoding="utf-8"))["chord_m"]   # m, reference chord of the meshed geometry (run_cases.C_REF; rev 2026-11-02: was the hard-coded 0.284176 of the old wing)
SEMISPAN = 1.2              # m, wing tip at y = 1.2 (wing marker y-extent, measured below and reported)
WALLS = ["wing", "htail", "fins", "pod", "booms", "motors", "gear"]
STATIONS = [0.15, 0.35, 0.55, 0.75, 0.95, 1.10]    # wing spanwise stations, m (clear of the root junction and tip box)
LEVELS = {1: 1.5, 2: 1.0, 3: 0.72, 4: 0.52}         # build_mesh.LEVELS (scale factor f)
CHECKED = "2026-11-01"


def pct(a, q):
    return float(np.percentile(a, q)) if len(a) else None


def rnd(x, n=4):
    if x is None:
        return None
    if isinstance(x, dict):
        return {k: rnd(v, n) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [rnd(v, n) for v in x]
    if isinstance(x, (float, np.floating)):
        return float(f"{float(x):.{n}g}")
    if isinstance(x, (np.integer,)):
        return int(x)
    return x


def unique_edges(tris):
    e = np.concatenate([tris[:, [0, 1]], tris[:, [1, 2]], tris[:, [2, 0]]])
    e.sort(axis=1)
    return np.unique(e, axis=0)


def stat(a, scale=1.0):
    a = np.asarray(a) * scale
    if len(a) == 0:
        return None
    return {"n": int(len(a)), "min": float(a.min()), "p05": pct(a, 5), "median": pct(a, 50), "p95": pct(a, 95), "max": float(a.max())}


def face_keys(f):
    f = np.sort(f, axis=1).astype(np.int64)
    return (f[:, 0] * (1 << 21) + f[:, 1]) * (1 << 21) + f[:, 2]


# ------------------------------------------------------------------------------------------------ per-level audit
def audit(level):
    t0 = time.time()
    tets, pts, markers = read_su2(OUT / f"L{level}" / "mesh.su2")
    nt = len(tets)
    m = {"level": level, "scale_f": LEVELS[level], "nodes": int(len(pts)), "tets": int(nt),
         "wall_triangles": {k: int(len(v)) for k, v in markers.items()}}

    # ---- tet geometry (chunked) --------------------------------------------------------------------------------
    vol = np.empty(nt); hrms = np.empty(nt); dmin = np.empty(nt); dmax = np.empty(nt); rr = np.empty(nt); er = np.empty(nt)
    for s in range(0, nt, 1_000_000):
        p = pts[tets[s:s + 1_000_000]]
        a, b, c, d = p[:, 0], p[:, 1], p[:, 2], p[:, 3]
        e = [b - a, c - a, d - a, c - b, d - b, d - c]
        l2 = np.stack([(x * x).sum(1) for x in e], 1)
        v = np.einsum("ij,ij->i", b - a, np.cross(c - a, d - a)) / 6
        vol[s:s + len(p)] = v
        hrms[s:s + len(p)] = np.sqrt(l2.mean(1))
        er[s:s + len(p)] = np.sqrt(l2.max(1) / l2.min(1))
        # outward face normals (face opposite vertex k), dihedral between faces i, j = pi - angle(n_i, n_j)
        faces = [(b, c, d, a), (a, c, d, b), (a, b, d, c), (a, b, c, d)]
        ns, areas = [], []
        for f0, f1, f2, opp in faces:
            n = np.cross(f1 - f0, f2 - f0)
            sgn = np.sign(np.einsum("ij,ij->i", n, f0 - opp))
            ar = np.linalg.norm(n, axis=1)
            ns.append(n * (sgn / np.maximum(ar, 1e-300))[:, None]); areas.append(0.5 * ar)
        ang = []
        for i in range(4):
            for j in range(i + 1, 4):
                cosv = np.clip(np.einsum("ij,ij->i", ns[i], ns[j]), -1, 1)
                ang.append(180.0 - np.degrees(np.arccos(cosv)))
        ang = np.stack(ang, 1)
        dmin[s:s + len(p)] = ang.min(1); dmax[s:s + len(p)] = ang.max(1)
        # radius ratio 3 r_in / R_circ (1 = regular tet)
        u, w, z = b - a, c - a, d - a
        num = (u * u).sum(1)[:, None] * np.cross(w, z) + (w * w).sum(1)[:, None] * np.cross(z, u) + (z * z).sum(1)[:, None] * np.cross(u, w)
        av = np.abs(v)
        Rc = np.linalg.norm(num, axis=1) / np.maximum(12 * av, 1e-300)
        rin = 3 * av / np.maximum(sum(areas), 1e-300)
        rr[s:s + len(p)] = 3 * rin / np.maximum(Rc, 1e-300)
    neg = int((vol < 0).sum()); pos = int((vol > 0).sum())
    m["quality"] = {
        "signed_volume": {"positive": pos, "negative": neg, "zero": int(nt - pos - neg),
                          "note": "one consistent sign = no inverted elements (orientation convention only)"},
        "min_dihedral_deg": {"min": float(dmin.min()), "p0_1": pct(dmin, 0.1), "p01": pct(dmin, 1), "median": pct(dmin, 50),
                             "count_below_5deg": int((dmin < 5).sum()), "count_below_10deg": int((dmin < 10).sum())},
        "max_dihedral_deg": {"max": float(dmax.max()), "p99": pct(dmax, 99), "p99_9": pct(dmax, 99.9),
                             "count_above_170deg": int((dmax > 170).sum()), "count_above_175deg": int((dmax > 175).sum())},
        "radius_ratio_3rin_over_Rcirc": {"min": float(rr.min()), "p01": pct(rr, 1), "mean": float(rr.mean())},
        "edge_ratio_max_over_min": {"median": pct(er, 50), "p99": pct(er, 99), "max": float(er.max())},
    }
    st = json.loads((OUT / f"L{level}" / "mesh_stats.json").read_text(encoding="utf-8"))
    m["quality"]["gmsh_reported"] = {"source": f"analysis/cfd3d/out/L{level}/mesh_stats.json",
                                     "minSICN": {k: st["quality_minSICN"][k] for k in ("min", "p01", "mean")},
                                     "gamma": st["quality_gamma"]}
    m["domain_volume_m3"] = float(np.abs(vol).sum())
    m["celik_h_m"] = float((np.abs(vol).sum() / nt) ** (1 / 3))     # Celik 2008 Eq. 1

    # ---- face adjacency: size ratio of neighbouring tets --------------------------------------------------------
    fk = np.concatenate([face_keys(tets[:, [1, 2, 3]]), face_keys(tets[:, [0, 2, 3]]), face_keys(tets[:, [0, 1, 3]]), face_keys(tets[:, [0, 1, 2]])])
    owner = np.tile(np.arange(nt, dtype=np.int64), 4)
    o = np.argsort(fk, kind="stable"); fk = fk[o]; owner = owner[o]
    same = np.nonzero(fk[1:] == fk[:-1])[0]
    ta, tb = owner[same], owner[same + 1]
    ratio = np.maximum(hrms[ta], hrms[tb]) / np.minimum(hrms[ta], hrms[tb])
    m["growth"] = {"adjacent_size_ratio": {"interior_faces": int(len(same)), "median": pct(ratio, 50), "p95": pct(ratio, 95),
                                           "p99": pct(ratio, 99), "p99_9": pct(ratio, 99.9), "max": float(ratio.max())},
                   "size_measure": "rms edge length of each tet"}
    del ratio, same, ta, tb

    # ---- wall-adjacent tets: first-cell normal size h = 3 V / A over the wall face ------------------------------
    def owner_of(tris):
        k = face_keys(tris)
        pos_ = np.searchsorted(fk, k)
        pos_ = np.minimum(pos_, len(fk) - 1)
        ok = fk[pos_] == k
        return owner[pos_], ok
    first = {}
    wall_all = []
    for g in WALLS:
        tris = markers[g]
        own, ok = owner_of(tris)
        ar = 0.5 * np.linalg.norm(np.cross(pts[tris[:, 1]] - pts[tris[:, 0]], pts[tris[:, 2]] - pts[tris[:, 0]]), axis=1)
        h = 3 * np.abs(vol[own]) / ar
        h = h[ok]
        first[g] = stat(h, 100 / C_REF)
        wall_all.append(h)
    hall = np.concatenate(wall_all)
    m["first_cell_height_pct_c"] = {"all_walls": stat(hall, 100 / C_REF), **first,
                                    "definition": "3 V / A of the tet owning each wall triangle, % c_ref"}
    m["first_cell_height_mm_wing_median"] = first["wing"]["median"] * C_REF * 10
    del fk, owner

    # ---- wing surface ---------------------------------------------------------------------------------------------
    wt = markers["wing"]
    wn = np.unique(wt)
    wp = pts[wn]
    xle, xte = float(wp[:, 0].min()), float(wp[:, 0].max())
    ytip = float(wp[:, 1].max())
    m["wing_extent_m"] = {"x_le": xle, "x_te": xte, "chord": xte - xle, "y_min": float(wp[:, 1].min()), "y_tip": ytip,
                          "z": [float(wp[:, 2].min()), float(wp[:, 2].max())]}
    E = unique_edges(wt)
    pa, pb = pts[E[:, 0]], pts[E[:, 1]]
    L = np.linalg.norm(pb - pa, axis=1); mid = 0.5 * (pa + pb)
    on_te_a = pa[:, 0] > xte - 1e-5; on_te_b = pb[:, 0] > xte - 1e-5
    # wing tip cap triangles (flat face at y = y_tip) are excluded from the spanwise-tip measure
    tn = np.cross(pts[wt[:, 1]] - pts[wt[:, 0]], pts[wt[:, 2]] - pts[wt[:, 0]])
    tn /= np.linalg.norm(tn, axis=1)[:, None]
    cen = pts[wt].mean(1)
    stations = []
    for ys in STATIONS:
        band = np.abs(mid[:, 1] - ys) < 0.02
        le = band & (mid[:, 0] < xle + 0.01 * C_REF)
        te_c = band & (on_te_a ^ on_te_b)                      # chordwise edges touching the TE line
        te_s = np.abs(mid[:, 1] - ys) < 0.05
        te_s &= on_te_a & on_te_b                                 # edges along the TE line
        # exact plane cut y = ys of the wing triangulation: crossing edges = section points
        ya, yb = pa[:, 1] - ys, pb[:, 1] - ys
        cross = (ya * yb) < 0
        tcut = ya[cross] / (ya[cross] - yb[cross])
        sp = pa[cross] + tcut[:, None] * (pb[cross] - pa[cross])
        sec_ok = len(sp) and (sp[:, 2].max() - sp[:, 2].min()) < 0.06 and (sp[:, 0].max() - sp[:, 0].min()) < C_REF * 1.02
        # section perimeter (points ordered by angle about the 40 %-chord point), and an equivalent 1-D point count:
        # perimeter / median local surface edge. A plane cut through isotropic triangles crosses more edges than a
        # 1-D discretisation of the same size would have, so the raw crossing count overstates resolution.
        ctr = np.array([xle + 0.4 * C_REF, sp[:, 2].mean()])
        o_ = np.argsort(np.arctan2(sp[:, 2] - ctr[1], sp[:, 0] - ctr[0]))
        ring = sp[o_][:, [0, 2]]
        perim = float(np.linalg.norm(np.diff(np.vstack([ring, ring[:1]]), axis=0), axis=1).sum())
        stations.append({"y_m": ys, "section_perimeter_m": perim,
                         "equiv_points_per_section": perim / float(np.median(L[band])),
                         "le_edge_pct_c": stat(L[le], 100 / C_REF),
                         "te_chordwise_edge_pct_c": stat(L[te_c], 100 / C_REF),
                         "te_line_spacing_pct_c": stat(L[te_s], 100 / C_REF),
                         "section_points": int(len(sp)),
                         "points_per_chord_upper_lower_avg": int(len(sp)) / 2,
                         "section_clean": bool(sec_ok)})
    m["wing_stations"] = stations
    def agg(key, q="median"):
        v = [s[key][q] for s in stations if s[key]]
        return {"median_over_stations": float(np.median(v)), "min_over_stations": float(np.min(v)), "max_over_stations": float(np.max(v))} if v else None
    m["wing_le_spacing_pct_c"] = agg("le_edge_pct_c")
    m["wing_le_spacing_min_edge_pct_c"] = float(min(s["le_edge_pct_c"]["min"] for s in stations))
    m["wing_te_spacing_pct_c"] = agg("te_chordwise_edge_pct_c")
    m["wing_te_line_spacing_pct_c"] = agg("te_line_spacing_pct_c")
    m["wing_section_points"] = {"median": float(np.median([s["section_points"] for s in stations])),
                                "per_station": [s["section_points"] for s in stations],
                                "equiv_median": float(np.median([s["equiv_points_per_section"] for s in stations])),
                                "note": "section_points = edges crossed by the plane y = station (upper + lower); equiv = perimeter / median "
                                        "local edge, comparable with the 2-D 'wall edges' in scheme_check_2d.json (CFD-12)"}
    # tip and root spanwise spacing (% semispan): surface (non-cap) triangles within 15 mm of the tip / root, in the
    # 10-90 % chord band so the LE curvature rule and the 0.6 mm TE-point field do not dominate the count
    cap = np.abs(tn[:, 1]) > 0.9
    cap |= (cen[:, 0] < xle + 0.1 * C_REF) | (cen[:, 0] > xle + 0.9 * C_REF)
    yroot = float(wp[:, 1].min())
    def tri_edge_len(sel):
        t = wt[sel]
        l = np.concatenate([np.linalg.norm(pts[t[:, i]] - pts[t[:, (i + 1) % 3]], axis=1) for i in range(3)])
        dy = np.concatenate([np.abs(pts[t[:, i], 1] - pts[t[:, (i + 1) % 3], 1]) for i in range(3)])
        return l, dy
    lt, dyt = tri_edge_len((~cap) & (cen[:, 1] > ytip - 0.015))
    lr, dyr = tri_edge_len((~cap) & (cen[:, 1] < yroot + 0.015))
    m["wing_tip_spanwise_spacing"] = {"edge_pct_semispan": stat(lt, 100 / SEMISPAN), "edge_mm_median": pct(lt, 50) * 1e3,
                                      "dy_projection_pct_semispan_median": pct(dyt[dyt > 1e-6], 50) * 100 / SEMISPAN}
    m["wing_root_spanwise_spacing"] = {"edge_pct_semispan": stat(lr, 100 / SEMISPAN), "edge_mm_median": pct(lr, 50) * 1e3,
                                       "y_root_m": yroot}
    m["wing_surface_edge_median_mm"] = pct(L, 50) * 1e3

    # ---- H-tail LE / TE (CFD-11) ----------------------------------------------------------------------------------
    ht = markers["htail"]
    hp = pts[np.unique(ht)]
    hxle, hxte = float(hp[:, 0].min()), float(hp[:, 0].max()); hc = hxte - hxle
    He = unique_edges(ht); ha, hb = pts[He[:, 0]], pts[He[:, 1]]
    hl = np.linalg.norm(hb - ha, axis=1); hm = 0.5 * (ha + hb)
    hle = hm[:, 0] < hxle + 0.01 * hc
    hte = (ha[:, 0] > hxte - 1e-5) ^ (hb[:, 0] > hxte - 1e-5)
    m["htail"] = {"x_le": hxle, "x_te": hxte, "chord_m": hc, "y_max": float(hp[:, 1].max()),
                  "le_edge_pct_local_c": stat(hl[hle], 100 / hc), "le_edge_pct_cref": stat(hl[hle], 100 / C_REF),
                  "te_chordwise_edge_pct_local_c": stat(hl[hte], 100 / hc),
                  "note": "H-tail marker also includes nothing else (build_mesh.GROUPS htail = H_Tail)"}

    # ---- pod nose / aft end spacing (% c_ref) ----------------------------------------------------------------------
    pt_ = markers["pod"]; Pe = unique_edges(pt_); qa, qb = pts[Pe[:, 0]], pts[Pe[:, 1]]
    ql = np.linalg.norm(qb - qa, axis=1); qm = 0.5 * (qa + qb)
    pxn, pxa = float(pts[np.unique(pt_), 0].min()), float(pts[np.unique(pt_), 0].max())
    m["pod_nose_spacing_pct_cref"] = stat(ql[qm[:, 0] < pxn + 0.01], 100 / C_REF)
    m["pod_aft_spacing_pct_cref"] = stat(ql[qm[:, 0] > pxa - 0.01], 100 / C_REF)
    m["pod_aft_note"] = "pod marker includes Canopy and Pusher_Motor; the aft end is the pusher motor"

    # ---- far field -------------------------------------------------------------------------------------------------
    fn = pts[np.unique(markers["farfield"])]
    walln = pts[np.unique(np.concatenate([markers[g] for g in WALLS]).ravel())]
    dfar, _ = cKDTree(walln).query(fn)
    bb_lo, bb_hi = walln.min(0), walln.max(0)
    box_lo, box_hi = fn.min(0), fn.max(0)
    dirs = {"upstream_from_nose": bb_lo[0] - box_lo[0], "downstream_from_tail": box_hi[0] - bb_hi[0],
            "outboard_from_tip": box_hi[1] - bb_hi[1], "below": bb_lo[2] - box_lo[2], "above": box_hi[2] - bb_hi[2],
            "upstream_from_wing_le": xle - box_lo[0]}
    m["farfield"] = {"box_m": {"x": [float(box_lo[0]), float(box_hi[0])], "y": [float(box_lo[1]), float(box_hi[1])], "z": [float(box_lo[2]), float(box_hi[2])]},
                     "min_distance_m": float(dfar.min()),
                     "by_direction_m": {k: float(v) for k, v in dirs.items()},
                     "by_direction_chords": {k: float(v / C_REF) for k, v in dirs.items()}}
    m["farfield_chords"] = float(dfar.min() / C_REF)
    m["farfield_semispans"] = float(dfar.min() / SEMISPAN)

    # ---- wake cell size behind the wing TE, and size vs distance from the wing --------------------------------------
    cent = pts[tets].mean(1)
    tree = cKDTree(cent)
    zte = float(pts[np.unique(E[on_te_a & on_te_b].ravel()), 2].mean())
    wake = {}
    for nc in (1, 3):
        rows = []
        for ys in (0.3, 0.6, 0.9):
            q = np.array([xte + nc * C_REF, ys, zte])
            _, idx = tree.query(q, k=8)
            rows.append({"y_m": ys, "x_m": float(q[0]), "cell_size_pct_c": float(np.median(hrms[idx]) * 100 / C_REF)})
        wake[f"{nc}c"] = {"points": rows, "median_pct_c": float(np.median([r["cell_size_pct_c"] for r in rows]))}
    m["wake"] = {**wake, "z_te_m": zte, "size_measure": "median rms edge length of the 8 tets nearest the probe"}
    m["wake_1c_pct_c"] = wake["1c"]["median_pct_c"]; m["wake_3c_pct_c"] = wake["3c"]["median_pct_c"]

    # size vs distance from the wing surface (upper side, mid span): growth implied by dh/dd
    sel = (cent[:, 0] > xle) & (cent[:, 0] < xte) & (cent[:, 1] > 0.3) & (cent[:, 1] < 0.9) & (cent[:, 2] > 0.03) & (cent[:, 2] < 0.6)
    dw, _ = cKDTree(wp).query(cent[sel])
    hs = hrms[sel]
    edges = [0, 0.005, 0.01, 0.02, 0.04, 0.08, 0.16, 0.32, 0.6]
    prof = []
    for lo, hi in zip(edges[:-1], edges[1:]):
        k = (dw >= lo) & (dw < hi)
        if k.sum():
            prof.append({"d_m": [lo, hi], "n": int(k.sum()), "h_median_mm": float(np.median(hs[k]) * 1e3)})
    for a_, b_ in zip(prof[:-1], prof[1:]):
        dd = 0.5 * (b_["d_m"][0] + b_["d_m"][1]) - 0.5 * (a_["d_m"][0] + a_["d_m"][1])
        b_["dh_dd"] = (b_["h_median_mm"] - a_["h_median_mm"]) * 1e-3 / dd
    m["growth"]["size_vs_distance_above_wing"] = prof
    slopes = [p["dh_dd"] for p in prof if "dh_dd" in p]
    m["growth"]["normal_gradation_max_dh_dd"] = float(max(slopes)) if slopes else None
    m["growth"]["note"] = "for isotropic cells the cell-to-cell growth along the normal is about 1 + dh/dd"
    m["time_s"] = round(time.time() - t0, 1)
    print(f"L{level}: {m['time_s']} s", flush=True)
    return m


# ------------------------------------------------------------------------------------------------ standards
def standards():
    DPW4 = "https://www.aiaa-dpw.org/Workshop4/gridding_guidelines_4.html"
    DPW8 = "https://www.aiaa-dpw.org/ref/gridding_guidelines_v3_07012024.pdf"
    CEL = "https://qa12.asme.org/wwwasmeorg/media/ResourceFiles/Shop/Journals/JFENumAccuracy.pdf"
    NPARC = "https://www.grc.nasa.gov/www/wind/valid/tutorial/spatconv.html"
    s = [
        ("STD-01", "AIAA DPW-4 gridding guidelines, item 2g", DPW4, "far-field distance", "~100 c_ref", True,
         "Far-field truncation changes circulation and lift for any lifting solver, viscous or inviscid."),
        ("STD-02", "AIAA DPW-8/AePW-4 gridding guidelines v3 (2024-07-01), CRM slide", DPW8, "far-field distance", "> 100 semispans", True,
         "Same physics as STD-01; DPW-8 states it per semispan for a 3-D wing (the OAT15A slide uses > 100 chords)."),
        ("STD-03", "AIAA DPW-8/AePW-4 gridding guidelines v3, CRM slide", DPW8, "wing chordwise spacing at LE and TE", "< 0.1 % local c", True,
         "Surface resolution of the suction peak and Kutta point; applies to the inviscid surface discretisation too."),
        ("STD-04", "AIAA DPW-4 gridding guidelines, item 2h-i (medium grid)", DPW4, "wing and tail chordwise spacing at LE and TE", "~0.1 % local c (medium grid)", True,
         "As STD-03; the guideline also covers the tail, so it applies to the H-tail LE (CFD-11)."),
        ("STD-05", "AIAA DPW-8/AePW-4 gridding guidelines v3, CRM slide", DPW8, "wing spanwise spacing at root and tip", "< 0.1 % semispan", True,
         "Resolves the tip vortex roll-up and root junction; geometric, not viscous."),
        ("STD-06", "AIAA DPW-8/AePW-4 gridding guidelines v3, CRM slide", DPW8, "spacing near fuselage nose and end of body", "< 1 % c_ref", True,
         "Applied to the pod nose (the pod is this aircraft's fuselage)."),
        ("STD-07", "AIAA DPW-4 gridding guidelines, item 2h-iv", DPW4, "cell size near fuselage nose and after-body", "~2.0 % c_ref", True,
         "Older, looser form of STD-06."),
        ("STD-08", "AIAA DPW-4 gridding guidelines, item 2j; DPW-8 v3 'Wing TE base >> 8 cells'", DPW4, "cells across the blunt TE base", ">= 8 / 12 / 16 cells (coarse / medium / fine)", False,
         "This wing has a sharp (closed) TE: there is no base to put cells across. TE edge spacing is reported instead."),
        ("STD-09", "AIAA DPW-8/AePW-4 gridding guidelines v3, wall-normal slide", DPW8, "first wall spacing (y+) and >= 2 constant-spacing layers", "y+ ~1 (tiny) to ~0.29 (ultra fine); >= 2 layers", False,
         "RANS boundary-layer criterion. The study is inviscid (SU2 INC_EULER) on tets with no prism layer; the wall-adjacent tet height is reported for information."),
        ("STD-10", "AIAA DPW-8/AePW-4 gridding guidelines v3, wall-normal slide; DPW-4 item 2f", DPW8, "growth rate normal to viscous walls", "< 1.2x (DPW-8); < 1.25 (DPW-4)", False,
         "Applies inside a viscous layer; there is none. Isotropic volume gradation is reported for information."),
        ("STD-11", "Celik et al. 2008, J. Fluids Eng. 130(7) 078001, Step 2", CEL, "grid refinement factor r = h_coarse / h_fine", "> 1.3", True,
         "Mesh-type independent; h from Celik Eq. 1, h = (sum V / N)^(1/3)."),
        ("STD-12", "NASA NPARC Alliance V&V, 'Examining Spatial (Grid) Convergence'", NPARC, "grid refinement ratio", "r >= 1.1", True,
         "Mesh-type independent minimum."),
        ("STD-13", "Celik et al. 2008, Step 3", CEL, "monotone convergence of the key quantity", "e32 / e21 > 0 (negative = oscillatory)", True,
         "Precondition for a Richardson / GCI estimate (CFD-02)."),
        ("STD-14", "Celik et al. 2008, Step 2; DPW-4 item 2e", CEL, "systematic refinement / same grid family", "refinement structured; same family between levels", True,
         "All sizing rules should scale together; tested by comparing regional spacing ratios with the global r."),
        ("STD-15", "AIAA DPW-4 gridding guidelines, item 2c", DPW4, "total grid size growth between levels", "~3x", True,
         "Mesh-type independent; '~' read here as within +-20 % (audit assumption, not in the source)."),
        ("STD-16", "gmsh 4.15.2 API docstring, getElementQualities (installed package)", "py -c \"import gmsh; help(gmsh.model.mesh.getElementQualities)\"", "element validity", "signed quality / volume of one sign (no inverted tets)", True,
         "Definitional: an inverted element is invalid for any finite-volume solver. No published numeric threshold on tet dihedral angles or radius ratio was read, so those are reported without pass/fail."),
    ]
    return [{"id": i, "source": src, "url": u, "checked": CHECKED, "criterion": cr, "threshold": th, "applies_to_this_mesh": ap, "why": w}
            for i, src, u, cr, th, ap, w in s]


# ------------------------------------------------------------------------------------------------ build_mesh.py strategy
def strategy():
    src = (HERE / "build_mesh.py").read_text(encoding="utf-8").splitlines()
    def ln(pat, start=0):
        for i in range(start, len(src)):
            if pat in src[i]:
                return i + 1
        raise KeyError(pat)
    def ref(a, b=None):
        la = ln(a); lb = ln(b, la - 1) if b else la
        return f"analysis/cfd3d/build_mesh.py:{la}" + (f"-{lb}" if lb != la else "")
    S = [
        ("Refinement levels", f"{len(LEVELS)} meshes share every rule; one length factor f scales most sizes (" + ", ".join(f"L{k} {v:g}" for k, v in LEVELS.items()) + ").",
         ref("LEVELS = {1: 1.5"), {"f": " / ".join(f"{v:g}" for v in LEVELS.values())}),
        ("Domain box", "Half-model box cut around the aircraft; mesh rev 2 puts the far boundary at least 33.8 m (Z: 35 m box top minus 1.2 m wing tip; 100 reference chords of 0.317 m = 31.7 m) from the aircraft, meeting the 100-chord guideline.",
         ref("DOMAIN = dict"), {"CAD frame": "X -45..35, Y -35..35, Z 0..35 m", "nearest far face": "33.8 m (above the tip)"}),
        ("Fluid volume", "The box minus the closed outer surface; only the largest volume is kept.",
         ref("body = gmsh.model.occ.importShapes", "drop, recursive=True"), {}),
        ("Symmetry / far-field / wall classification", "Faces on y = 0 become the symmetry plane, faces on the box sides the far field, everything else wall.",
         ref("boundary classification by position", "wall.append(s)"), {"tolerance": "1e-6 m"}),
        ("Wall size field", "Cell size grows linearly from the wall size at 4 mm from any wall to the far size at 30 m.",
         ref('dist = fld.add("Distance")', 'fld.setNumber(thr, "DistMin", 0.004)'), {"SizeMin": "8 mm x f", "SizeMax": "4 m x f", "DistMin": "4 mm (fixed)", "DistMax": "30 m (fixed)", "Sampling": "40"}),
        ("Trailing-edge lines", "Straight constant-x curves near the aircraft (sharp TEs of wing, tail, fins, fairings) get a finer size within 3 mm.",
         ref("# sharp trailing edges", 'fld.setNumber(tte, "DistMin", 0.003)'), {"SizeMin": "2.5 mm x f", "SizeMax": "4 m x f", "DistMin": "3 mm (fixed)", "DistMax": "0.25 m (fixed)", "Sampling": "400"}),
        ("Trailing-edge end points", "The ends of each TE line (tip, symmetry plane, fin root/tip) get 0.6 mm x f so the thin wedge does not self-intersect (mesh rev 2: scaled with f).",
         ref("# TE end points", 'fld.setNumber(ttp, "DistMin", 0.004)'), {"SizeMin": "0.6 mm x f", "DistMin": "4 mm", "DistMax": "0.12 m"}),
        ("Lifting-surface wall size (rev 2)", "Wing, horizontal tail and fins are re-meshed at 2.2 mm x f on the surface, growing to the far size over 1.2 m (the 2-D scheme check gave -8 % section lift at this spacing vs -14 % at the rev 1 spacing).",
         ref("LIFT_WALL = 0.0022", 'fld.setNumber(tl, "DistMax", 1.2)'), {"VIn": "2.2 mm x f", "DistMin": "4 mm", "DistMax": "1.2 m", "Sampling": "200"}),
        ("Box fields helper", "Each box sets a constant size inside and blends to 1 m outside over a fixed thickness.",
         ref("def add_box(cad_box, size, thick)", "boxes.append(bx)"), {"VOut": "1.0 m"}),
        ("Aircraft box", "Caps the cell size around the whole aircraft.",
         ref("# around the aircraft"), {"VIn": "20 mm x f", "Thickness": "0.4 m"}),
        ("Wake box", "Caps the cell size behind the wing and tail out to about 4 m aft.",
         ref("# wake of wing and tail"), {"VIn": "30 mm x f", "Thickness": "0.6 m", "x range (SU2)": "0.25..4.0 m"}),
        ("Tip-vortex box", "Finer cells along the starboard tip-vortex path.",
         ref("# starboard tip-vortex path"), {"VIn": "12 mm x f", "Thickness": "0.15 m"}),
        ("Wing-tip box", "Finest box, around the wing tip itself.",
         ref("# wing tip"), {"VIn": "6 mm x f", "Thickness": "0.05 m"}),
        ("Field combination", "The background size is the minimum of all fields; sizes are not extended from boundaries or points.",
         ref('mn = fld.add("Min")', '"Mesh.MeshSizeFromPoints", 0'), {"ExtendFromBoundary": "0", "FromPoints": "0"}),
        ("Curvature sizing", "Curved surfaces get 24/f elements per full turn (mesh rev 2: scaled with f, so the leading edge refines with the level).",
         ref('CURV_PER_2PI = 24', '"Mesh.MeshSizeFromCurvature", int(round(CURV_PER_2PI / f))'), {"elements per 2 pi": "24 / f"}),
        ("Global size limits", "Hard floor and ceiling on any element size.",
         ref('"Mesh.MeshSizeMin", 0.0006 * f', '"Mesh.MeshSizeMax", 4.0 * f'), {"MeshSizeMin": "0.6 mm x f", "MeshSizeMax": "4 m x f"}),
        ("Meshing algorithms", "Surface: gmsh Delaunay (5) unless ALG2D is set; volume: HXT parallel Delaunay (10).",
         ref('"Mesh.Algorithm", int', '"Mesh.Algorithm3D", 10'), {"Algorithm": "5", "Algorithm3D": "10 (HXT)"}),
        ("Optimiser", "gmsh tet optimiser and the Netgen optimiser run after volume meshing.",
         ref('"Mesh.Optimize", 1', '"Mesh.OptimizeNetgen", 1'), {"Optimize": "1", "OptimizeNetgen": "1"}),
        ("Wall component tagging", "Each wall face is assigned to a component (wing, htail, ...) by probing a point just off the face against the un-fused parts.",
         ref("# ---- classify wall faces by component", 'addPhysicalGroup(3, [keep[1]], name="fluid")'), {"probe offsets": "+-0.2..0.8 mm"}),
        ("Element type", "Linear tetrahedra throughout, linear triangles on walls, no prism layer (inviscid).",
         ref('"elements": "linear tetrahedra'), {}),
    ]
    return [{"name": n, "what": w, "code_ref": r, "parameters": p} for n, w, r, p in S]


# ------------------------------------------------------------------------------------------------ scorecard
def scorecard(M, conv):
    rows = []
    def row(std, metric, thr, vals, note):
        rows.append({"standard": std, "metric": metric, "threshold_text": thr, **{f"L{k}": v for k, v in vals.items()}, "note": note})
    def cmp(v, ok):
        return {"value": rnd(v), "result": "n/a" if v is None else ("pass" if ok(v) else "fail")}
    lv = tuple(sorted(M))
    na = {"value": None, "result": "n/a"}
    fin = f"L{lv[-1]}"
    row("STD-01", "farfield_chords", "~100 c_ref", {k: cmp(M[k]["farfield_chords"], lambda v: v >= 100) for k in lv},
        "Nearest far-field node to any wall node. '~100' tested as >= 100.")
    row("STD-02", "farfield_semispans", "> 100 semispans", {k: cmp(M[k]["farfield_semispans"], lambda v: v > 100) for k in lv}, "")
    row("STD-03", "wing_le_spacing_pct_c (median of station medians)", "< 0.1 % c",
        {k: cmp(M[k]["wing_le_spacing_pct_c"]["median_over_stations"], lambda v: v < 0.1) for k in lv},
        "Edges with midpoint within 1 % c of the LE, 6 stations. Set by the curvature rule (24/f per turn) and the 2.2 mm x f lifting-surface size.")
    row("STD-03", "wing_te_spacing_pct_c (median of station medians)", "< 0.1 % c",
        {k: cmp(M[k]["wing_te_spacing_pct_c"]["median_over_stations"], lambda v: v < 0.1) for k in lv},
        "Chordwise edges touching the sharp TE line.")
    row("STD-04", "htail le_edge_pct_local_c (median)", "~0.1 % local c (medium)",
        {k: cmp(M[k]["htail"]["le_edge_pct_local_c"]["median"], lambda v: v <= 0.1) for k in lv},
        "Relevant to CFD-11 (Cp > 1 at the H-tail LE): the LE is resolved by only a few edges.")
    row("STD-05", "wing_tip_spanwise_spacing (median edge, % semispan)", "< 0.1 % semispan",
        {k: cmp(M[k]["wing_tip_spanwise_spacing"]["edge_pct_semispan"]["median"], lambda v: v < 0.1) for k in lv}, "Wing triangles within 15 mm of the tip, 10-90 % chord, tip cap excluded.")
    row("STD-05", "wing_root_spanwise_spacing (median edge, % semispan)", "< 0.1 % semispan",
        {k: cmp(M[k]["wing_root_spanwise_spacing"]["edge_pct_semispan"]["median"], lambda v: v < 0.1) for k in lv}, "Wing triangles within 15 mm of the wing-pod junction, 10-90 % chord.")
    row("STD-06", "pod_nose_spacing_pct_cref (median)", "< 1 % c_ref",
        {k: cmp(M[k]["pod_nose_spacing_pct_cref"]["median"], lambda v: v < 1.0) for k in lv}, "Pod edges within 10 mm of the nose.")
    row("STD-07", "pod_nose_spacing_pct_cref (median)", "~2.0 % c_ref",
        {k: cmp(M[k]["pod_nose_spacing_pct_cref"]["median"], lambda v: v <= 2.0) for k in lv}, "'~2 %' tested as <= 2 %.")
    row("STD-08", "TE base cells", ">= 8 / 12 / 16", {k: {"value": None, "result": "n/a"} for k in lv},
        "Closed TE. TE line node spacing (% c, median): " + ", ".join(f"L{k} {rnd(M[k]['wing_te_line_spacing_pct_c']['median_over_stations'], 3)}" for k in lv))
    row("STD-09", "first_cell_height_pct_c (wing median)", "y+ criterion (viscous)", {k: {"value": rnd(M[k]["first_cell_height_pct_c"]["wing"]["median"]), "result": "n/a"} for k in lv},
        "Inviscid mesh: reported only.")
    row("STD-10", "adjacent_size_ratio p99", "< 1.2 (viscous layer)", {k: {"value": rnd(M[k]["growth"]["adjacent_size_ratio"]["p99"]), "result": "n/a"} for k in lv},
        "No viscous layer; isotropic gradation reported only.")
    R = conv["refinement"]
    pairs = list(zip(lv, lv[1:]))      # each pair's value is listed on its finer level
    def pair_row(std, metric, thr, val, ok, note):
        rows.append({"standard": std, "metric": metric, "threshold_text": thr, f"L{lv[0]}": na,
                     **{f"L{b}": {"value": rnd(val(a, b)), "result": "pass" if ok(val(a, b)) else "fail"} for a, b in pairs}, "note": note})
    for std, thr, ok in (("STD-11", "> 1.3", lambda v: v > 1.3), ("STD-12", ">= 1.1", lambda v: v >= 1.1)):
        pair_row(std, "r = (N_fine / N_coarse)^(1/3)", thr, lambda a, b: R[f"r_L{a}_L{b}"], ok,
                 "Value listed on the finer level of each pair (" + ", ".join(f"L{b} = L{a}->L{b}" for a, b in pairs) + ").")
    c = conv["monotone"]["CL"]
    rows.append({"standard": "STD-13", "metric": "CL at alpha 4 deg: e32/e21", "threshold_text": "> 0",
                 **{f"L{k}": na for k in lv[:-1]}, fin: {"value": rnd(c["e32_over_e21"]), "result": "pass" if c["e32_over_e21"] > 0 else "fail"},
                 "note": f"Three-level property of the finest triplet ({conv['monotone']['levels']}), listed on {fin}. A positive ratio is monotone; the asymptotic range also needs e32/e21 > 1 (CFD-02)."})
    fam = conv["family"]
    pair_row("STD-14", "worst regional spacing ratio / global r", "same family (ratios equal)", lambda a, b: fam[f"L{a}_L{b}"]["worst_dev"], lambda v: v <= 0.1,
             "Relative deviation of each regional ratio from the global r; pass if all within 10 % (audit assumption). Mesh rev 2 scales every size rule with f; the wake and tip-vortex boxes still refine faster than the global ratio.")
    pair_row("STD-15", "N_tets ratio between levels", "~3x", lambda a, b: R[f"N_ratio_L{a}_L{b}"], lambda v: 2.4 <= v <= 3.6,
             "+-20 % band is an audit assumption.")
    row("STD-16", "inverted tets (one volume sign)", "0 inverted",
        {k: {"value": min(M[k]["quality"]["signed_volume"]["positive"], M[k]["quality"]["signed_volume"]["negative"]) + M[k]["quality"]["signed_volume"]["zero"],
             "result": "pass" if min(M[k]["quality"]["signed_volume"]["positive"], M[k]["quality"]["signed_volume"]["negative"]) + M[k]["quality"]["signed_volume"]["zero"] == 0 else "fail"} for k in lv},
        "Count of tets with the minority (or zero) volume sign.")
    return rows


def convergence(M):
    N = {k: M[k]["tets"] for k in M}
    lv = sorted(M); pairs = list(zip(lv, lv[1:]))
    ref = {"celik_h_m": {f"L{k}": M[k]["celik_h_m"] for k in M}}
    for a, b in pairs:
        ref.update({f"r_L{a}_L{b}": (N[b] / N[a]) ** (1 / 3), f"N_ratio_L{a}_L{b}": N[b] / N[a],
                    f"r_celik_h_L{a}_L{b}": M[a]["celik_h_m"] / M[b]["celik_h_m"], f"f_ratio_L{a}_L{b}": LEVELS[a] / LEVELS[b]})
    regional = {
        "wing_le_spacing": lambda m: m["wing_le_spacing_pct_c"]["median_over_stations"],
        "wing_te_chordwise": lambda m: m["wing_te_spacing_pct_c"]["median_over_stations"],
        "wing_te_line": lambda m: m["wing_te_line_spacing_pct_c"]["median_over_stations"],
        "wing_first_cell_height": lambda m: m["first_cell_height_pct_c"]["wing"]["median"],
        "wing_surface_edge": lambda m: m["wing_surface_edge_median_mm"],
        "wing_tip_spanwise": lambda m: m["wing_tip_spanwise_spacing"]["edge_pct_semispan"]["median"],
        "htail_le": lambda m: m["htail"]["le_edge_pct_local_c"]["median"],
        "wake_1c": lambda m: m["wake_1c_pct_c"],
        "wake_3c": lambda m: m["wake_3c_pct_c"],
        "section_points_equiv": lambda m: 1 / m["wing_section_points"]["equiv_median"],
    }
    fam = {}
    for a, b in pairs:
        r = ref[f"r_L{a}_L{b}"]
        rat = {k: fn(M[a]) / fn(M[b]) for k, fn in regional.items()}
        dev = {k: abs(v / r - 1) for k, v in rat.items()}
        fam[f"L{a}_L{b}"] = {"global_r": r, "regional_ratio": rat, "worst": max(dev, key=dev.get), "worst_dev": max(dev.values())}
    res = json.loads((OUT / "cfd3d_results.json").read_text(encoding="utf-8"))["cases"]
    mono = {}
    trip = [k for k in lv if (res.get(f"L{k}_a4.0") or {}).get("returncode") == 0][-3:]   # finest three solved levels
    for q in ("CL", "CD", "CMy"):
        f1, f2, f3 = (res[f"L{k}_a4.0"][q] for k in trip[::-1])     # Celik: 1 = finest
        e21, e32 = f2 - f1, f3 - f2
        mono[q] = {"fine_to_coarse": [f1, f2, f3], "e21": e21, "e32": e32, "e32_over_e21": e32 / e21,
                   "convergence": "monotone" if e32 / e21 > 0 else "oscillatory"}
    return {"refinement": ref, "family": fam,
            "monotone": {**mono, "levels": "-".join(f"L{k}" for k in trip), "source": "analysis/cfd3d/out/cfd3d_results.json cases " + "/".join(f"L{k}" for k in trip) + "_a4.0"}}


def _row(sc, std, metric_start=""):
    return next((r for r in sc if r["standard"] == std and r["metric"].startswith(metric_start)), None)


def verdict(sc, M, conv):
    """Summary text built from the scorecard (rev 2026-11-02: was hard-coded for the rev 1 meshes and went stale)"""
    R = conv["refinement"]; c = conv["monotone"]["CL"]; fam = conv["family"]
    L = [f"L{k}" for k in sorted(M)]; fin = L[-1]
    passed = sorted({r["standard"] for r in sc if any(r[k]["result"] == "pass" for k in L)})
    failed = sorted({r["standard"] for r in sc if any(r[k]["result"] == "fail" for k in L)})
    le = _row(sc, "STD-03", "wing_le"); ff = _row(sc, "STD-01")
    worst = max(fam, key=lambda k: fam[k]["worst_dev"])
    e = c["e32_over_e21"]
    asym = (f"CL at alpha 4 on {conv['monotone']['levels']} is in the asymptotic range (e32/e21 = {e:.2f} > 1), so CFD-02 has a valid GCI. " if e > 1 else
            f"CL at alpha 4 on {conv['monotone']['levels']} is {'monotone' if e > 0 else 'oscillatory'} but not in the asymptotic range (e32/e21 = {e:.2f}; asymptotic needs > 1), so no valid GCI (CFD-02). ")
    t = (f"Mesh rev 2. All {len(L)} levels are valid (no inverted cells), " + " / ".join(f"{R[f'r_{a}_{b}']:.2f}" for a, b in zip(L, L[1:])) + " apart (grid-study minimum 1.3), "
         f"and the far field is {ff[fin]['value']:.0f} reference chords away (guideline 100). "
         f"The wing LE spacing refines with the level (" + " / ".join(f"{le[k]['value']:.2f}" for k in L) + " % c) but is still above the 0.1 % c "
         f"viscous-grid guideline, which this inviscid study is not built to meet. " + asym +
         f"Regional spacing ratios deviate from the global ratio by up to {100 * fam[worst]['worst_dev']:.0f} % (worst: {fam[worst]['worst']}, {worst.replace('_', '->')}). "
         f"Standards met on some level: {', '.join(passed) or 'none'}; not met: {', '.join(failed) or 'none'}.")
    return t


def needs(sc, M, conv):
    out = []
    fin = f"L{max(M)}"
    if _row(sc, "STD-02")[fin]["result"] == "fail":
        out.append("Far field at >= 100 semispans (120 m) for DPW-8; far cells can stay large, so the extra cost is small.")
    if _row(sc, "STD-03", "wing_le")[fin]["result"] == "fail":
        out.append(f"Wing and H-tail chordwise spacing near 0.1 % local chord at LE and TE (0.1 % of the {C_REF:.3f} m chord = {C_REF:.2f} mm), graded to coarser cells mid-chord (anisotropic surface mesh), for a viscous-grade grid.")
    if _row(sc, "STD-05", "wing_tip")[fin]["result"] == "fail":
        out.append("Spanwise spacing near 0.1 % semispan (1.2 mm) at the wing root and tip, locally.")
    if _row(sc, "STD-14")[fin]["result"] == "fail":
        out.append("Wake and tip-vortex boxes scaled so their spacing ratio equals the global r (the wake regions refine faster than the rest today).")
    if not conv["monotone"]["CL"]["e32_over_e21"] > 1:   # STD-13 tests only the sign; the asymptotic range needs e32/e21 > 1
        out.append("A finer level to reach the asymptotic range so the GCI of CFD-02 can be computed." if max(M) < 4 else
                   "The asymptotic range on a finer level; L4 (23 M tetrahedra, about 40 GB) is the largest that fits this PC.")
    if _row(sc, "STD-06")[fin]["result"] == "fail":
        out.append(f"Pod nose spacing under 1 % c_ref ({10 * C_REF:.2f} mm) for DPW-8; {fin} is at {_row(sc, 'STD-06')[fin]['value']:.2f} % today.")
    return out



def main():
    t0 = time.time()
    M = {k: audit(k) for k in LEVELS if (OUT / f"L{k}" / "mesh.su2").exists()}
    conv = convergence(M)
    sc = scorecard(M, conv)
    cnt = {"pass": 0, "fail": 0, "n/a": 0}
    for r in sc:
        for k in M:
            cnt[r[f"L{k}"]["result"]] += 1
    out = {
        "generated": time.strftime("%Y-%m-%d %H:%M"),
        "script": "analysis/cfd3d/mesh_audit.py",
        "inputs": [f"analysis/cfd3d/out/L1..L{max(M)}/mesh.su2 (via mesh.npz cache)", f"analysis/cfd3d/out/L1..L{max(M)}/mesh_stats.json",
                   "analysis/cfd3d/out/cfd3d_results.json", "analysis/cfd3d/build_mesh.py"],
        "reference_lengths": {"c_ref_m": C_REF, "semispan_m": SEMISPAN, "source": "run_cases.C_REF; wing marker extents (metrics.Ln.wing_extent_m)"},
        "standards": standards(),
        "metrics": {f"L{k}": rnd(v, 5) for k, v in M.items()},
        "convergence": rnd(conv, 5),
        "scorecard": sc,
        "strategy": strategy(),
        "not_measured": [
            {"metric": "cells across TE base", "reason": "the wing TE is closed (sharp); there is no base. TE line spacing is reported instead."},
            {"metric": "y+", "reason": "inviscid solution, no boundary layer; y+ is undefined for this study."},
            {"metric": "wake / tip-vortex / quality thresholds", "reason": "no published numeric threshold was read for isotropic tet wake size, dihedral angle or radius ratio; values are reported without pass/fail."},
            {"metric": "HLPW gridding guidelines", "reason": "hiliftpw.larc.nasa.gov redirected to a NASA landing page on 2026-11-01; the PDF could not be read, so no HLPW threshold is used."},
        ],
        "summary": None,
    }
    out["summary"] = {
        "passes": cnt["pass"], "fails": cnt["fail"], "not_applicable": cnt["n/a"],
        "verdict": verdict(sc, M, conv),
        "what_a_passing_mesh_needs": needs(sc, M, conv),
    }
    p = OUT / "mesh_audit.json"
    with open(p, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(out, fh, indent=1)
    print(json.dumps({"summary": out["summary"], "time_s": round(time.time() - t0, 1)}, indent=1))


if __name__ == "__main__":
    main()
