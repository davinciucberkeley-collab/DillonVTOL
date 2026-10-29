"""Independent hand checks of the aero / performance / propulsion / mass / stability / cost claims of C0.

Audit script (2026-10-29). numpy only. Reads the repo outputs READ-ONLY (analysis/results.json,
analysis/aero/aero_results.json, firmware/sitl/results_c0.json) to get the *repo* values and the geometry inputs,
then recomputes each claim with textbook formulas that do NOT call the repo's model code.

Run:  py analysis/validation/check_aero.py   -> analysis/validation/checks_aero.json  (< 1 s)

Each check prints: claim id | independent value | repo value | % delta | tolerance | pass.
"Shared" flags inputs/assumptions that the independent check has in common with the repo (not independent there).
Sources of textbook formulas:
  Re = rho V c / mu (ISA sea level, mu 1.789e-5 Pa s)
  thin-airfoil theory: Anderson, Fundamentals of Aerodynamics, ch. 4 (alpha_0L, Cm_c/4, a0 = 2 pi)
  lifting line with planform factor tau: a = a0 / (1 + a0 (1 + tau) / (pi AR)), tau ~ 0.17 rectangular AR 8-9 (Anderson fig. 5.20)
  Oswald e (straight wing): e = 1.78 (1 - 0.045 AR^0.68) - 0.64 (Raymer 5th ed. eq. 12.49)
  flat-plate skin friction: turbulent Cf = 0.074 Re^-0.2 (Schlichting), laminar Cf = 1.328 / sqrt(Re) (Blasius),
    composite with laminar run x_tr: Cf = Cf_t(Re) - x_tr (Cf_t(Re_tr) - Cf_l(Re_tr))  (Prandtl/Schlichting)
  form factors (Hoerner): wing 1 + 2 t/c + 60 (t/c)^4 ; body 1 + 1.5 / f^1.5 + 7 / f^3
  momentum-theory hover: P_ideal = T^1.5 / sqrt(2 rho A)
  stall: V = sqrt(2 W / (rho S CLmax)) ; Raymer CLmax_3D ~ 0.9 CLmax_2D (unswept)
  neutral point: h_n = 0.25 + eta V_h (a_t/a_w)(1 - de/da) + dh_fus ; de/da = 2 a_w / (pi AR)
    fuselage (Munk / Perkins & Hage, Raymer eq. 16.25): Cm_alpha_fus = K_f W_f^2 L_f / (c S) per deg
  GCI: Celik et al., J. Fluids Eng. 130 (2008) 078001
"""
import json, math, os, datetime
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
def load(p): return json.load(open(os.path.join(REPO, p), encoding="utf-8"))
R = load("analysis/results.json"); A = load("analysis/aero/aero_results.json")
SITL = load("firmware/sitl/results_c0.json") if os.path.exists(os.path.join(REPO, "firmware/sitl/results_c0.json")) else None
C0 = R["concepts"]["C0"]; P = C0["params"]; S_ = C0["sized"]; G_ = C0["geo"]; CG = C0["cg"]; BOM = C0["bom"]
g0 = 9.80665; rho = 1.225; mu = 1.789e-5
out = []

def rec(cid, what, indep, repo, tol_pct, shared="", note=""):
    d = None if (indep is None or repo in (None, 0)) else 100.0 * (indep - repo) / abs(repo)
    ok = None if d is None else abs(d) <= tol_pct
    out.append({"id": cid, "check": what, "independent": indep, "repo": repo, "delta_pct": None if d is None else round(d, 2),
                "tolerance_pct": tol_pct, "pass": ok, "shared_assumptions": shared, "note": note})
    ds = "   —  " if d is None else f"{d:+7.2f}%"
    iv = "—" if indep is None else f"{indep:.5g}"; rv = "—" if repo is None else f"{repo:.5g}"
    print(f"{cid:8s} {what[:58]:58s} indep {iv:>10s} repo {rv:>10s} {ds} tol {tol_pct:>4}% {'PASS' if ok else ('FAIL' if ok is False else 'n/a')}")

# ---------------- geometry / conditions ----------------
m = S_["m"]; W = m * g0; S = S_["S"]; c = S_["chord"]; b = P["span"]; AR = b * b / S
Vc = P["Vc"]; q = 0.5 * rho * Vc**2

# AERO-01 Reynolds number at cruise (aero package used chord 0.284176; sizing chord now c)
Re_c = rho * Vc * c / mu
rec("AERO-01", "Cruise Re (rho V c / mu), current sizing chord", Re_c, A["conditions"]["cruise"]["Re"], 2.0,
    note="aero package geometry (chord 0.2842 m, S 0.6820) is one sizing iteration behind results.json (chord %.4f, S %.4f)" % (c, S))

# ---------------- 2-D section: thin-airfoil theory for NACA 2415 ----------------
mc, pc = 0.02, 0.40
th = np.linspace(0, math.pi, 200001); x = 0.5 * (1 - np.cos(th))
dz = np.where(x < pc, 2 * mc / pc**2 * (pc - x), 2 * mc / (1 - pc)**2 * (pc - x))
trap = lambda y: float(np.sum(0.5 * (y[1:] + y[:-1]) * np.diff(th)))
a0L = -(1 / math.pi) * trap(dz * (np.cos(th) - 1))
A1 = 2 / math.pi * trap(dz * np.cos(th)); A2 = 2 / math.pi * trap(dz * np.cos(2 * th))
cm4 = math.pi / 4 * (A2 - A1)
sp = A["section_polars"]["n2415_cruise_ncrit9"]
rec("AERO-02", "2-D lift slope /rad: thin-airfoil 2*pi vs XFOIL", 2 * math.pi, sp["CL_alpha_per_rad"], 10.0,
    note="thickness correction 2pi(1+0.77 t/c)=%.3f brackets XFOIL from above" % (2 * math.pi * (1 + 0.77 * 0.15)))
rec("AERO-03", "2-D zero-lift angle deg: thin-airfoil vs XFOIL", math.degrees(a0L), sp["alpha_0L_deg"], 10.0)
rec("AERO-04", "2-D Cm_c/4: thin-airfoil vs XFOIL", cm4, sp["Cm_c4"], 15.0)

# AERO-05 2-D drag: fully turbulent flat plate x Hoerner FF vs SU2 SA (fully turbulent) at alpha 2 deg
cft = lambda Re: 0.074 / Re**0.2
cfl = lambda Re: 1.328 / math.sqrt(Re)
def cf_comp(Re, xtr):
    if xtr <= 0: return cft(Re)
    Rt = Re * xtr; return cft(Re) - xtr * (cft(Rt) - cfl(Rt))
FFw = lambda tc: 1 + 2 * tc + 60 * tc**4
Re2d = A["cfd"]["Re"] if "Re" in A["cfd"] else 350257.0
cd_turb = 2 * cft(Re2d) * FFw(0.15)
row2 = [r for r in A["comparison_2D"] if r["alpha_deg"] == 2][0]
rec("AERO-05", "2-D cd fully turbulent (2 Cf FF) vs SU2 SA alpha 2", cd_turb, row2["su2_SA_CD"], 10.0)
# XFOIL transitional, xtr ~0.58 top / 0.96 bottom (from the XFOIL table: transition location is an XFOIL output, so 'shared')
cd_mix = (cf_comp(Re2d, 0.584) + cf_comp(Re2d, 0.960)) * FFw(0.15)
rec("AERO-06", "2-D cd composite lam/turb (XFOIL xtr) vs XFOIL alpha 2", cd_mix, row2["xfoil_CD"], 20.0,
    shared="transition locations taken from the XFOIL table")

# AERO-07 CLmax 2-D adopted 1.30 (from a paper abstract) -- no independent computation possible here
nf = A["CL_max_2D"]
spread = [nf["xfoil_stall_Re"], nf["neuralfoil_stall_Re"], nf["su2_SA_cruise_Re"]["CL_max"]]
rec("AERO-07", "2-D CLmax: mean of XFOIL/NeuralFoil/SU2 vs adopted 1.30", float(np.mean(spread)), nf["adopted_2D"], 10.0,
    shared="all three are repo solver outputs; spread %.2f-%.2f" % (min(spread), max(spread)))

# ---------------- 3-D lift ----------------
CLmax3 = 0.9 * nf["adopted_2D"]
rec("AERO-08", "3-D CLmax: Raymer 0.9 x CLmax_2D vs adopted (critical section)", CLmax3, A["CL_max_3D"]["adopted"], 5.0,
    shared="CLmax_2D 1.30 is the same input")
Vs_ind = math.sqrt(2 * W / (rho * S * CLmax3))
rec("AERO-09", "Stall speed m/s with Raymer CLmax (sizing S, MTOW)", Vs_ind, P["Vs"], 3.0,
    note="with CLmax 10%% low (%.3f) Vs = %.2f m/s > R11 12 m/s; R11 fails below CLmax %.3f" %
    (0.9 * A["CL_max_3D"]["adopted"], math.sqrt(2 * W / (rho * S * 0.9 * A["CL_max_3D"]["adopted"])), 2 * W / (rho * S * 144)))
S_ind = 2 * W / (rho * P["Vs"]**2 * P["CLmax"])
rec("AERO-10", "Wing area m2 from stall (same formula, arithmetic only)", S_ind, S, 0.5, shared="same formula and inputs")
CL_c = 2 * W / (rho * Vc**2 * S)
rec("AERO-11", "Cruise CL at 18 m/s", CL_c, S_["CL"], 0.5, shared="same formula")
tau = 0.17
a_w = 2 * math.pi / (1 + 2 * math.pi * (1 + tau) / (math.pi * AR))
rec("AERO-12", "Wing lift slope /rad: lifting line (a0 2pi, tau .17) vs repo VLM", a_w, load("analysis/aero.json")["wing_CLa_per_rad"], 7.0,
    note="Helmbold in sizing gives %.3f" % G_["aw"])
ARt = G_["hSpan"]**2 / G_["Sh"]; a_t = 2 * math.pi / (1 + 2 * math.pi * (1 + tau) / (math.pi * ARt))
deda = 2 * a_w / (math.pi * AR); eta_t = 0.9
CLa_ac = a_w + eta_t * a_t * G_["Sh"] / S * (1 - deda)
rec("AERO-13", "Aircraft CL_alpha /rad (wing + tail, no pod) vs AVL no pod", CLa_ac, A["lift_curve"]["CL_alpha_per_rad"]["AVL_aircraft_nopod"], 7.0)

# ---------------- drag ----------------
e_ray = 1.78 * (1 - 0.045 * AR**0.68) - 0.64
rec("AERO-14", "Oswald e: Raymer 12.49 vs sizing e 0.80", e_ray, P["e"], 5.0, note="repo build-up fit %.3f" % A["drag"]["e_oswald_fit"])
# independent component build-up (streamlined parts recomputed; bluff items reuse the repo's Hoerner CdA -> shared)
items = {i["component"]: i["CdA_m2"] for i in A["drag"]["items"]}
def comp_cda(xtr):
    S_exp = S - 2 * 0.08 * c
    wing = cf_comp(rho * Vc * c / mu, xtr) * FFw(0.15) * 2 * (1 + 0.2 * 0.15) * S_exp
    hc = G_["hC"]; htail = cf_comp(rho * Vc * hc / mu, xtr) * FFw(0.09) * 2 * 1.02 * G_["Sh"]
    vfin = cf_comp(rho * Vc * G_["vC"] / mu, xtr) * FFw(0.09) * 2 * 1.02 * G_["Sv"]
    Lp, Dp = 0.85, 0.16; f = Lp / Dp
    pod = cft(rho * Vc * Lp / mu) * (1 + 1.5 / f**1.5 + 7 / f**3) * (0.75 * math.pi * Dp * Lp)
    Lb = G_["booms"][0]["x1"] - G_["booms"][0]["x0"]
    booms = 2 * cft(rho * Vc * Lb / mu) * math.pi * 0.0254 * Lb
    bluff = sum(v for k, v in items.items() if not k.startswith(("Wing profile", "H-tail", "Fins", "Pod (", "Booms (2)", "Leakage")))
    sub = wing + htail + vfin + pod + booms + bluff
    return 1.10 * sub, {"wing": wing, "htail": htail, "vfins": vfin, "pod": pod, "booms": booms, "bluff_shared": bluff}
cda_c, parts = comp_cda(0.30)       # EST laminar run 30 % chord (taped foam surface), +10 % interference/leakage (EST)
cda_t, _ = comp_cda(0.0)            # fully turbulent bound
CD0_ind = cda_c / S
rec("AERO-15", "CD0 total: independent build-up (xtr .30, +10%) vs sizing", CD0_ind, S_["CD0"], 15.0,
    shared="bluff items (stopped motors/props, clamps, legs, feet, canopy) reuse repo Hoerner CdA = %.4f m2" % parts["bluff_shared"],
    note="fully turbulent bound CD0 %.4f; repo build-up %.4f" % (cda_t / S, A["drag"]["CD0_total"]))
LD_ind = CL_c / (CD0_ind + CL_c**2 / (math.pi * e_ray * AR))
rec("AERO-16", "Cruise L/D: independent CD0 + Raymer e vs sizing", LD_ind, S_["LD"], 10.0)
LD_turb = CL_c / (cda_t / S + CL_c**2 / (math.pi * e_ray * AR))
P_ind = W / LD_ind * Vc / (P["etaProp"] * P["etaMEc"])
rec("AERO-17", "Cruise electrical power W (same eta 0.60 x 0.85)", P_ind, S_["P_cruise"], 10.0, shared="etaProp 0.60, etaMEc 0.85 (EST)",
    note="fully turbulent bound: L/D %.2f, P %.0f W" % (LD_turb, W / LD_turb * Vc / (P["etaProp"] * P["etaMEc"])))
CLs = math.sqrt(math.pi * e_ray * AR * CD0_ind); Vs_ld = math.sqrt(2 * W / (rho * S * CLs))
rec("AERO-38", "Speed for max L/D m/s (CL* = sqrt(pi e AR CD0)) vs cruise trade", Vs_ld,
    load("analysis/cruise_speed_trade.json")["crossCheck"]["Vstar_mps"], 5.0, note="18 m/s is 1.4x V*; chosen as R11 lower bound")
# pusher propulsive efficiency: momentum-theory ideal at the cruise thrust, 14 in prop
Ap = math.pi * (14 * 0.0254 / 2)**2; Tc = S_["D_cruise"]
eta_i = 2 / (1 + math.sqrt(1 + Tc / (q * Ap)))
rec("AERO-18", "Pusher eta: 0.80 x momentum-ideal vs EST 0.60", 0.80 * eta_i, P["etaProp"], 15.0,
    note="ideal %.3f; 0.80 profile/swirl factor is EST; no forward-flight prop data in repo" % eta_i)

# ---------------- hover ----------------
D = P["liftD"]; Ad = math.pi * D * D / 4; T_unit = W / 4; Tg = T_unit / g0 * 1000
tab = np.array(P["thrustTable"], float)
P_unit_tab = float(np.interp(Tg, tab[:, 0], tab[:, 1]))
P_h_tab = 4 * P_unit_tab * P["kCtrl"]
rec("AERO-19", "Hover power W: maker table interpolated in power x kCtrl", P_h_tab, S_["P_hover"], 5.0,
    shared="SunnySky table (17x5.8 prop; BOM buys 17x5.5) and kCtrl 1.10")
P_ideal = T_unit**1.5 / math.sqrt(2 * rho * Ad)
P_h_mt = 4 * P_ideal * P["kCtrl"] / (0.65 * 0.80)
rec("AERO-20", "Hover power W: momentum theory, FM 0.65, eta_m+esc 0.80 (EST)", P_h_mt, S_["P_hover"], 10.0, shared="kCtrl 1.10")
rec("AERO-21", "Disk loading N/m2", T_unit / Ad, S_["diskLoading"], 0.5, shared="same formula")
# T/W: repo uses maker max thrust at 615 W/motor (27.7 A). Power-limited by the repo's own 60 A pack assumption:
Pmax_60 = 60 * 21.0 / 4
T60 = float(np.interp(Pmax_60, tab[:, 1], tab[:, 0]))
TW60 = 4 * T60 / 1000 / m
rec("AERO-22", "T/W limited to 60 A pack at 21.0 V vs repo T/W", TW60, S_["TW"], 10.0,
    note="repo T/W needs 4 x 27.7 = 111 A; R13 needs >= 1.6")
rec("AERO-23", "Transition current A vs pack 60 A continuous (repo own value)", S_["I_trans"], 60.0, 0.0,
    note="SITL scenario A peak %s A" % (SITL["scenarios"][0]["peak_current_A"] if SITL else "—"))

# ---------------- energy ----------------
E_use = C0["pick"]["Wh"] * (1 - P["reserve"]) * P["etaBatt"] * 3600
t_hov = P["tHover"] + P["tTrans"]
t_ind = (E_use - P_h_tab * t_hov) / P_ind / 60
rec("AERO-24", "Cruise time available min (indep. hover + cruise power)", t_ind, S_["t_cruise_avail_min"], 15.0,
    shared="pack 144.3 Wh, reserve 20 %, etaBatt 0.95, 40 s transition at hover power")
rec("AERO-25", "Pack energy Wh = 6.5 Ah x 22.2 V", 6.5 * 22.2, C0["pick"]["Wh"], 0.5)

# ---------------- mass / CG ----------------
mi = np.array([i["m"] for i in CG["items"]]); xi = np.array([i["x"] for i in CG["items"]])
rec("AERO-26", "MTOW kg: sum of CG item list", float(mi.sum()), m, 0.5, shared="all item masses are repo EST/maker values")
foam = 0.685 * 0.15 * c * c * b * P["rhoFoam"]
mw = foam + 2 * P["wGlass"] * S + P["m_spar"]
rec("AERO-27", "Wing mass kg: NACA area 0.685 t c^2 x span x foam + tape + spar", mw, S_["m_wing"], 5.0,
    shared="foam 32 kg/m3, tape 0.06 kg/m2, spar tubes (not weighed)")
xcg = float((mi * xi).sum() / mi.sum())
rec("AERO-28", "CG %MAC from item moments", -xcg / c * 100, CG["pct"]["target"], 2.0, shared="item stations from repo")
mnp = mi[:-1]; xnp = xi[:-1]
rec("AERO-29", "CG %MAC without payload", float(-(mnp * xnp).sum() / mnp.sum() / c * 100), CG["pct"]["noPayload"], 2.0)

# ---------------- stability ----------------
Vh = G_["Sh"] * G_["lh"] / (S * c); Vv = G_["Sv"] * G_["lh"] / (S * b)
rec("AERO-30", "Horizontal tail volume Vh", Vh, G_["Vh"], 1.0, note="Raymer tab 6.4 homebuilt typical 0.50: C0 is 30 % below")
rec("AERO-31", "Vertical tail volume Vv", Vv, G_["Vv"], 1.0, note="Raymer homebuilt typical 0.04: C0 is 25 % below")
hn_np = 0.25 + eta_t * Vh * (a_t / a_w) * (1 - deda)
rec("AERO-32", "Neutral point %MAC wing+tail (no pod) vs AVL no pod", hn_np * 100, A["neutral_point"]["AVL_nopod_pct_MAC"], 5.0,
    note="AeroSandbox VLM gives %.1f %% (repo, unexplained +6 pts)" % A["neutral_point"]["AeroSandbox_VLM_pct_MAC"])
Lf, Wf = 0.85, 0.16
xq = (0.45 + 0.25 * c) / Lf
Kf = float(np.interp(xq, [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7], [0.005, 0.006, 0.008, 0.012, 0.018, 0.027, 0.042]))  # approx. digitization of Perkins & Hage / Raymer fig. 16.14, +/-30 %
Cma_f = Kf * Wf**2 * Lf / (c * S) * 180 / math.pi
dh_pod = -Cma_f / CLa_ac
hn = hn_np + dh_pod
rec("AERO-33", "Neutral point %MAC with pod (Munk/Perkins-Hage) vs AVL pod", hn * 100, A["neutral_point"]["AVL_pod_pct_MAC"], 5.0,
    note="pod shift %.1f %% MAC (K_f %.3f at x/L %.2f) vs AVL %.1f; stopped props not modelled by either" % (dh_pod * 100, Kf, xq, A["neutral_point"]["pod_shift_pct_MAC"]))
rec("AERO-34", "Static margin %MAC at CG 28 %", (hn - 0.28) * 100, A["neutral_point"]["static_margin_pct"]["CG_28pct"], 25.0)
rec("AERO-35", "Static margin %MAC with no payload", (hn - CG["pct"]["noPayload"] / 100) * 100, A["neutral_point"]["static_margin_pct"]["CG_no_payload"], 30.0)

# ---------------- CFD mesh study GCI (Celik 2008) at alpha 10 ----------------
ms = A["cfd"]["mesh_study"]["alpha_10"]
N = ms["cells"]; h1, h2, h3 = [N[k] ** -0.5 for k in ("L3", "L2", "L1")]
r21, r32 = h2 / h1, h3 / h2
def gci(f1, f2, f3):
    e21, e32 = f2 - f1, f3 - f2; s = np.sign(e32 / e21); p = 1.0
    for _ in range(200):
        qp = math.log((r21**p - s) / (r32**p - s)); p = abs(math.log(abs(e32 / e21)) + qp) / math.log(r21)
    ea = abs((f1 - f2) / f1); return p, 1.25 * ea / (r21**p - 1) * 100
pC, gC = gci(ms["CL"]["L3"], ms["CL"]["L2"], ms["CL"]["L1"])
rec("AERO-36", "SU2 GCI_fine on CL at alpha 10 (%)", gC, ms["GCI_CL"]["GCI_fine_pct"], 10.0, note="order p %.2f" % pC)

# ---------------- cost ----------------
goods = sum(l["qty"] * l["unit"] for l in BOM["lines"])
tot = goods * 1.1025 + BOM["shipping"]
rec("AERO-37", "BOM committed total $ (goods x 1.1025 + $110 ship)", tot, BOM["total"], 0.1, shared="all unit prices and shipping EST from repo")

res = {"generated": datetime.date.today().isoformat(), "script": "analysis/validation/check_aero.py",
       "inputs_read_only": ["analysis/results.json", "analysis/aero/aero_results.json", "analysis/aero.json", "firmware/sitl/results_c0.json"],
       "intermediate": {"Re_cruise": Re_c, "alpha0L_thin_deg": math.degrees(a0L), "cm4_thin": cm4, "a_w": a_w, "a_t": a_t, "deda": deda,
                        "CD0_indep": CD0_ind, "CD0_fully_turbulent": cda_t / S, "parts_CdA_m2": parts, "e_raymer": e_ray, "LD_indep": LD_ind,
                        "LD_fully_turbulent": LD_turb, "P_cruise_indep_W": P_ind, "eta_ideal_pusher": eta_i, "P_hover_table_W": P_h_tab,
                        "P_hover_momentum_W": P_h_mt, "T_per_motor_at_60A_g": T60, "TW_60A": TW60, "Kf": Kf, "dh_pod": dh_pod, "hn": hn,
                        "GCI_p": pC},
       "checks": out}
json.dump(res, open(os.path.join(HERE, "checks_aero.json"), "w", encoding="utf-8"), indent=1, default=float)
print(f"\n{sum(1 for o in out if o['pass'])} pass / {sum(1 for o in out if o['pass'] is False)} fail / {len(out)} checks -> analysis/validation/checks_aero.json")
