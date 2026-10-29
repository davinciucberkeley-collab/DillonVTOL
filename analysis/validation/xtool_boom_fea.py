"""Cross-tool check of the SOLIDWORKS boom FEA (cad/Sim.cs Boom(), cad/sim/results.txt) with an independent toolchain:
gmsh 4.15 (OpenCASCADE geometry, 2nd-order tetrahedra) + a 10-node tetrahedron (C3D10-type) linear-elastic solver
written here in numpy/scipy. Nothing is shared with SOLIDWORKS except the inputs: same geometry rules, load and material.

Model (as cad/Sim.cs Boom()): 6061 tube OD boomOD, ID boomID, length feaBoomL along +x, fixed root face x = 0; tip
block = vertical cylinder radius rBlk = sqrt(m_tip / (rho pi (OD/2 + 0.05))) at x = L - rBlk, from the tube axis up
to OD/2 + 0.05 m (block mass = lift-unit mass), merged with the tube; load feaTipForce normal to the block top face.
Solved as a half model (symmetry plane z = 0, u_z = 0, half the load). Outputs: tip deflection, von Mises at the root (singular corner, so also reported away from it), bending stress at
x = 0.10 m against M c / I, and the change between two mesh sizes.

Usage:  py analysis/validation/xtool_boom_fea.py      -> analysis/validation/xtool_boom_fea.json
"""
import json, math, sys, time
from pathlib import Path

import gmsh
import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as sla

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "analysis"))
import geom  # noqa: E402

P = geom.PARAMS
E, NU = 69.0e9, 0.33            # 6061-T6: E 68.9 GPa, nu 0.33 (MatWeb "Aluminum 6061-T6; 6061-T651", https://www.matweb.com, checked 2026-10-29); the repo's E_DESIGN is 69 GPa
L, OD, ID = P["feaBoomL"], P["boomOD"], P["boomID"]
RHO = P.get("matRho", 2700.0)
MTIP, F = P["feaTipMass"], P["feaTipForce"]
HBLK = 0.05
RBLK = math.sqrt(MTIP / (RHO * math.pi * (OD / 2 + HBLK)))


def build(h):
    gmsh.model.add(f"boom_{h}")
    o = gmsh.model.occ
    # extrusions of disks rather than OCC cylinders: the swept circles keep their seam lines through the boolean, which
    # gmsh needs to mesh the periodic faces
    ann = o.cut([(2, o.addDisk(0, 0, 0, OD / 2, OD / 2))], [(2, o.addDisk(0, 0, 0, ID / 2, ID / 2))])[0]
    o.rotate(ann, 0, 0, 0, 0, 1, 0, math.pi / 2)                               # disk normal z -> x
    tube = [e for e in o.extrude(ann, L, 0, 0) if e[0] == 3]
    d = o.addDisk(L - RBLK, 0, 0, RBLK, RBLK); o.rotate([(2, d)], L - RBLK, 0, 0, 1, 0, 0, -math.pi / 2)   # normal z -> y
    blk = [e for e in o.extrude([(2, d)], 0, OD / 2 + HBLK, 0) if e[0] == 3]
    body = o.fuse(tube, blk)[0]
    # split by the plane z = 0 into two conformal halves: no periodic (seamless) cylinder faces are left for the mesher
    rect = o.addRectangle(-0.1, -0.1, 0, L + 0.2, 0.3)
    o.fragment(body, [(2, rect)])
    o.synchronize()
    # keep the z >= 0 half: the geometry and load are symmetric about z = 0, so u_z = 0 there (half the unknowns)
    for d_, t_ in gmsh.model.getEntities(3):
        if o.getCenterOfMass(d_, t_)[2] < 0:            # OCC boxes of curved faces are loose; the centroid is not
            o.remove([(d_, t_)], recursive=True)
    o.synchronize()
    for _, s_ in gmsh.model.getEntities(2):
        up, _ = gmsh.model.getAdjacencies(2, s_)
        if len(up) == 0:
            o.remove([(2, s_)], recursive=True)
    o.synchronize()
    body = gmsh.model.getEntities(3)
    root, top, sym = [], [], []
    for _, s in gmsh.model.getEntities(2):
        if len(gmsh.model.getAdjacencies(2, s)[0]) != 1:
            continue
        b = gmsh.model.getBoundingBox(2, s)
        if abs(b[2]) < 1e-4 and abs(b[5]) < 1e-4:          # planar face on z = 0 (OCC box tolerance ~1e-5)
            sym.append(s)
        if abs(b[0]) < 1e-6 and abs(b[3]) < 1e-6:
            root.append(s)
        if abs(b[1] - (OD / 2 + HBLK)) < 1e-6 and abs(b[4] - (OD / 2 + HBLK)) < 1e-6:
            top.append(s)
    gmsh.model.addPhysicalGroup(2, root, name="root"); gmsh.model.addPhysicalGroup(2, top, name="top"); gmsh.model.addPhysicalGroup(2, sym, name="sym")
    gmsh.model.addPhysicalGroup(3, [t for _, t in body], name="solid")
    gmsh.option.setNumber("Mesh.MeshSizeMax", h); gmsh.option.setNumber("Mesh.MeshSizeMin", h / 4)
    gmsh.option.setNumber("Mesh.ElementOrder", 2); gmsh.option.setNumber("Mesh.SecondOrderLinear", 0)
    gmsh.option.setNumber("Mesh.HighOrderOptimize", 1)
    gmsh.model.mesh.generate(3)
    return root, top, sym


def solve(h):
    t0 = time.time()
    root, top, sym = build(h)
    tags, xyz, _ = gmsh.model.mesh.getNodes()
    X = xyz.reshape(-1, 3); idx = {int(t): i for i, t in enumerate(tags)}
    et, etags, enodes = gmsh.model.mesh.getElements(3)
    k = list(et).index(11)                                   # 10-node tetrahedron
    conn = np.vectorize(idx.get)(enodes[k].reshape(-1, 10))
    # reference-element shape-function gradients at 4-point Gauss (gmsh's own basis: no node-ordering assumption)
    qp, qw = gmsh.model.mesh.getIntegrationPoints(11, "Gauss2")
    _, dN, _ = gmsh.model.mesh.getBasisFunctions(11, qp, "GradLagrange")
    nq = len(qw); dN = np.array(dN).reshape(nq, 10, 3)
    C = E / ((1 + NU) * (1 - 2 * NU)) * np.array([[1 - NU, NU, NU, 0, 0, 0], [NU, 1 - NU, NU, 0, 0, 0], [NU, NU, 1 - NU, 0, 0, 0],
                                                  [0, 0, 0, (1 - 2 * NU) / 2, 0, 0], [0, 0, 0, 0, (1 - 2 * NU) / 2, 0], [0, 0, 0, 0, 0, (1 - 2 * NU) / 2]])
    ne = len(conn); rows, cols, vals = [], [], []
    dofs = (3 * conn[:, :, None] + np.arange(3)).reshape(ne, 30)
    Bs, dets = [], []
    for c0 in range(0, ne, 20000):
        cc = conn[c0:c0 + 20000]; Xe = X[cc]                                # (m,10,3)
        Ke = np.zeros((len(cc), 30, 30)); Bq = []
        for q in range(nq):
            J = np.einsum("mai,aj->mij", Xe, dN[q])                         # dx_i/dxi_j
            det = np.linalg.det(J); Jinv = np.linalg.inv(J)
            G = np.einsum("aj,mji->mai", dN[q], Jinv)                       # dN_a/dx_i
            B = np.zeros((len(cc), 6, 30))
            B[:, 0, 0::3] = G[:, :, 0]; B[:, 1, 1::3] = G[:, :, 1]; B[:, 2, 2::3] = G[:, :, 2]
            B[:, 3, 0::3] = G[:, :, 1]; B[:, 3, 1::3] = G[:, :, 0]
            B[:, 4, 1::3] = G[:, :, 2]; B[:, 4, 2::3] = G[:, :, 1]
            B[:, 5, 0::3] = G[:, :, 2]; B[:, 5, 2::3] = G[:, :, 0]
            Ke += np.einsum("mki,kl,mlj->mij", B, C, B) * (det * qw[q])[:, None, None]
            Bq.append(B); dets.append(det)
        Bs.append(np.stack(Bq, 1))
        d = dofs[c0:c0 + 20000]
        rows.append(np.repeat(d, 30, axis=1).ravel()); cols.append(np.tile(d, (1, 30)).ravel()); vals.append(Ke.ravel())
    n = 3 * len(X)
    K = sp.csr_matrix((np.concatenate(vals), (np.concatenate(rows), np.concatenate(cols))), shape=(n, n))
    # load: total F in -y spread over the block top face as consistent nodal forces of a uniform traction
    f = np.zeros(n); area = 0.0
    tt, tn, _ = [], [], []
    for s in top:
        ty, tg, tn_ = gmsh.model.mesh.getElements(2, s)
        j = list(ty).index(9)                                                # 6-node triangle
        tri = np.vectorize(idx.get)(tn_[j].reshape(-1, 6))
        a = 0.5 * np.linalg.norm(np.cross(X[tri[:, 1]] - X[tri[:, 0]], X[tri[:, 2]] - X[tri[:, 0]]), axis=1)
        area += a.sum()
        for m in range(3, 6):                                                # quadratic triangle: corner loads 0, mid-side A/3
            np.add.at(f, 3 * tri[:, m] + 1, -a / 3)
    f *= (F / 2) / area                                                      # half model carries half the load
    fixed = set()
    for s in root:
        nt, _, _ = gmsh.model.mesh.getNodes(2, s, includeBoundary=True)
        fixed.update(idx[int(t)] for t in nt)
    fixed = np.array(sorted(fixed)); fd = np.concatenate([3 * fixed, 3 * fixed + 1, 3 * fixed + 2])
    symn = set()
    for s_ in sym:
        nt, _, _ = gmsh.model.mesh.getNodes(2, s_, includeBoundary=True)
        symn.update(idx[int(t)] for t in nt)
    fd = np.unique(np.concatenate([fd, 3 * np.array(sorted(symn)) + 2]))   # symmetry: u_z = 0
    free = np.setdiff1d(np.arange(n), fd)
    u = np.zeros(n)
    # symmetric fill-reducing ordering: the default COLAMD fills in to >12 GB on this mesh
    u[free] = sla.spsolve(K[free][:, free].tocsc(), f[free], permc_spec="MMD_AT_PLUS_A")
    U = u.reshape(-1, 3)
    # stresses at Gauss points, von Mises
    Bq = np.concatenate(Bs); ue = u[dofs]
    sig = np.einsum("kl,mqlj,mj->mqk", C, Bq, ue)
    s = sig
    vm = np.sqrt(0.5 * ((s[..., 0] - s[..., 1]) ** 2 + (s[..., 1] - s[..., 2]) ** 2 + (s[..., 2] - s[..., 0]) ** 2) + 3 * (s[..., 3] ** 2 + s[..., 4] ** 2 + s[..., 5] ** 2))
    xg = np.einsum("qa,mai->mqi", np.array(gmsh.model.mesh.getBasisFunctions(11, qp, "Lagrange")[1]).reshape(nq, 10), X[conn])
    I = math.pi / 64 * (OD ** 4 - ID ** 4)
    def sxx_at(x0, band=0.004):   # max |sigma_xx| over Gauss points in a thin band around x0 (outer fibres)
        m = np.abs(xg[..., 0] - x0) < band
        return float(np.abs(s[..., 0][m]).max())
    # beam: load at the block centre x = L - RBLK
    a_load = L - RBLK
    # deflection of the tube's bottom fibre along the span, against the cantilever with the load at a = L - RBLK
    bot = np.where(np.abs(X[:, 1] + OD / 2) < 2e-4)[0]
    prof = []
    for xs in (0.1, 0.2, 0.3, 0.4, a_load):
        k = bot[np.argmin(np.abs(X[bot, 0] - xs))]
        x_ = X[k, 0]; beam = F * x_ ** 2 * (3 * a_load - x_) / (6 * E * I)
        prof.append({"x_m": round(float(x_), 4), "fe_mm": float(-U[k, 1] * 1000), "beam_mm": float(beam * 1000)})
    imin = int(np.argmin(U[:, 1]))
    out = {"deflection_profile": prof, "max_defl_at_m": X[imin].round(4).tolist(), "h_m": h, "nodes": int(len(X)), "elements": int(ne), "dof": int(n),
           "tip_deflection_mm": float(-U[:, 1].min() * 1000), "max_disp_mm": float(np.linalg.norm(U, axis=1).max() * 1000),
           "vm_max_MPa": float(vm.max() / 1e6), "vm_max_x>10mm_MPa": float(vm[xg[..., 0] > 0.010].max() / 1e6),
           "sxx_x100_MPa": sxx_at(0.10) / 1e6, "beam_sxx_x100_MPa": F * (a_load - 0.10) * (OD / 2) / I / 1e6,
           "load_check_N_half_model": float(-f[1::3].sum()), "time_s": round(time.time() - t0, 1)}
    return out


def write_claim(res):
    """claims_xtool.json: the cross-tool result as a validation-matrix claim"""
    c = res["comparison"]; t = c["tip_deflection_mm"]; sx = c["sxx_x100_MPa"]; v = c["vm_max_MPa"]
    ok = abs(t["delta_vs_solidworks_pct"]) < 5 and abs(sx["delta_pct"]) < 5
    claim = {"id": "XT-01", "component": "booms", "discipline": "structures",
             "claim": "The SOLIDWORKS boom study (cad/Sim.cs Boom) is reproduced by an independent mesher and solver.",
             "value": t["solidworks"], "units": "mm tip deflection (SOLIDWORKS)",
             "equations": ["K u = f, 10-node tetrahedra, 4-point Gauss, isotropic linear elasticity", "beam check: sigma = M c / I, delta(x) = P x^2 (3a - x) / (6 E I)"],
             "assumptions": ["same geometry rules, material (E 69 GPa, nu 0.33), load and fixed root as the SOLIDWORKS study", "half model with u_z = 0 on the symmetry plane"],
             "inputs": res["inputs"], "tool": res["toolchain"],
             "evidence": [{"file": "analysis/validation/xtool_boom_fea.json", "what": "two meshes, deflection profile, stresses"}, {"file": "cad/sim/results.txt", "what": "SOLIDWORKS values"}],
             "ran_evidence": f"solved here: {', '.join(str(r['dof']) + ' DOF in ' + str(r['time_s']) + ' s' for r in res['runs'])}",
             "reproduced": {"done": True, "how": "py analysis/validation/xtool_boom_fea.py", "matches": ok},
             "independent_check": {"method": "gmsh + own C3D10 solver (no SOLIDWORKS code)", "value": t["independent_fe"], "repo_value": t["solidworks"], "delta_pct": t["delta_vs_solidworks_pct"], "script": "analysis/validation/xtool_boom_fea.py"},
             "status": "Verified" if ok else "Partially Verified",
             "status_reason": f"tip deflection {t['independent_fe']:.3f} vs {t['solidworks']:.3f} mm ({t['delta_vs_solidworks_pct']:+.1f} %); bending stress at x 0.10 m {sx['independent_fe']:.2f} vs beam {sx['beam']:.2f} MPa ({sx['delta_pct']:+.2f} %); root-corner peak {v['delta_vs_solidworks_pct']:+.1f} % (singular, not a design value); mesh change {c['mesh_change_tip_defl_pct']:+.2f} %",
             "limitations": ["verifies the computation, not the load case: the tip mass is 37 % low (STR-05) and no landing case exists (STR-11)", "same idealised fixed root as SOLIDWORKS; clamp compliance is not modelled by either"],
             "next_step": "Re-run both solvers with the CAD lift-unit mass and a clamp-compliant root; add a landing case."}
    (Path(__file__).parent / "claims_xtool.json").write_text(json.dumps({"generated": time.strftime("%Y-%m-%d %H:%M"), "author": "analysis/validation/xtool_boom_fea.py", "claims": [claim]}, indent=1), encoding="utf-8")


def main():
    if "--claims-only" in sys.argv:
        write_claim(json.loads((Path(__file__).parent / "xtool_boom_fea.json").read_text())); return
    gmsh.initialize(); gmsh.option.setNumber("General.Terminal", 0)
    runs = [solve(h) for h in (0.004, 0.0025)]
    gmsh.finalize()
    sw = {}
    for line in (ROOT / "cad/sim/results.txt").read_text().splitlines():
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1); sw[k] = float(v.split("|")[0])
    I = math.pi / 64 * (OD ** 4 - ID ** 4)
    hand_defl = F * L ** 3 / (3 * E * I) * 1000
    fine = runs[-1]
    res = {"generated": time.strftime("%Y-%m-%d %H:%M"), "script": "analysis/validation/xtool_boom_fea.py",
           "toolchain": f"gmsh {gmsh.__version__} 2nd-order tetrahedra + numpy/scipy C3D10 solver (this script); SuperLU direct solve",
           "inputs": {"L_m": L, "OD_m": OD, "ID_m": ID, "E_Pa": E, "nu": NU, "rho": RHO, "m_tip_kg": MTIP, "F_N": F, "r_block_m": RBLK},
           "runs": runs,
           "solidworks": {k: sw.get(k) for k in ("boom_vm_max", "boom_vm_max_fine", "boom_disp_max", "boom_hand_sigma", "boom_hand_defl")},
           "comparison": {"tip_deflection_mm": {"independent_fe": fine["tip_deflection_mm"], "solidworks": sw.get("boom_disp_max"), "beam_PL3_3EI": hand_defl,
                                                "delta_vs_solidworks_pct": 100 * (fine["tip_deflection_mm"] - sw["boom_disp_max"]) / sw["boom_disp_max"]},
                          "vm_max_MPa": {"independent_fe": fine["vm_max_MPa"], "solidworks_fine": sw.get("boom_vm_max_fine"),
                                         "delta_vs_solidworks_pct": 100 * (fine["vm_max_MPa"] - sw["boom_vm_max_fine"]) / sw["boom_vm_max_fine"],
                                         "note": "both peaks sit on the fully fixed root edge, a stress singularity: they grow with refinement and are not a design value"},
                          "sxx_x100_MPa": {"independent_fe": fine["sxx_x100_MPa"], "beam": fine["beam_sxx_x100_MPa"],
                                           "delta_pct": 100 * (fine["sxx_x100_MPa"] - fine["beam_sxx_x100_MPa"]) / fine["beam_sxx_x100_MPa"]},
                          "mesh_change_tip_defl_pct": 100 * (runs[1]["tip_deflection_mm"] - runs[0]["tip_deflection_mm"]) / runs[0]["tip_deflection_mm"]}}
    (Path(__file__).parent / "xtool_boom_fea.json").write_text(json.dumps(res, indent=1))
    write_claim(res)
    print(json.dumps(res["comparison"], indent=1)); print([{k: r[k] for k in ("h_m", "dof", "time_s")} for r in runs])


if __name__ == "__main__":
    main()
