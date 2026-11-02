"""Independent hand checks of the aero / performance / propulsion / mass / stability / cost claims of C0.

Audit script (2026-10-29, re-audited 2026-11-02 against the frozen design of 2026-11-01). numpy only.
Reads the repo outputs READ-ONLY (analysis/results.json, analysis/aero/aero_results.json, analysis/aero.json,
analysis/aero/out/*, analysis/mass/mass_budget.json, analysis/propulsion_data_2026-11-01.json, docs/DESIGN-BASIS.md,
docs/research/stall-margin.md) to get the *repo* values and the geometry inputs, then recomputes each claim with
textbook formulas that do NOT call the repo's model code.

Run:  py analysis/validation/check_aero.py   -> analysis/validation/checks_aero.json  (< 1 s)

Check ids are the claim ids in analysis/validation/claims_aero.json. A claim with more than one check has the extra
checks suffixed b, c, ... (AERO-02, AERO-02b, AERO-02c). Each claim's independent_check.script points here as
"analysis/validation/check_aero.py#AERO-xx".

Each check prints: id | independent value | repo value (or bound) | % delta | tolerance or relation | pass.
  rel "eq": pass if |delta| <= tolerance
  rel "ge": pass if independent >= repo value (the repo value is a lower bound, e.g. a requirement)
  rel "le": pass if independent <= repo value
"Shared" flags inputs/assumptions that the independent check has in common with the repo (not independent there).

Sources of textbook formulas:
  Re = rho V c / mu (ISA sea level, mu 1.789e-5 Pa s)
  thin-airfoil theory: Anderson, Fundamentals of Aerodynamics, ch. 4 (alpha_0L, Cm_c/4, a0 = 2 pi)
  lifting line with planform factor tau: a = a0 / (1 + a0 (1 + tau) / (pi AR)), tau ~ 0.17 rectangular (Anderson fig. 5.20)
  Oswald e (straight wing): e = 1.78 (1 - 0.045 AR^0.68) - 0.64 (Raymer 5th ed. eq. 12.49)
  flat-plate skin friction: turbulent Cf = 0.074 Re^-0.2 (Schlichting), laminar Cf = 1.328 / sqrt(Re) (Blasius),
    composite with laminar run x_tr: Cf = Cf_t(Re) - x_tr (Cf_t(Re_tr) - Cf_l(Re_tr))  (Prandtl/Schlichting)
  form factors (Hoerner): wing 1 + 2 t/c + 60 (t/c)^4 ; body 1 + 1.5 / f^1.5 + 7 / f^3
  momentum-theory hover: P_ideal = T^1.5 / sqrt(2 rho A); propeller ideal efficiency 2 / (1 + sqrt(1 + T/(q A)))
  stall: V = sqrt(2 W / (rho S CLmax)) ; Raymer CLmax_3D ~ 0.9 CLmax_2D (unswept)
  neutral point: h_n = 0.25 + eta V_h (a_t/a_w)(1 - de/da) + dh_fus ; de/da = 2 a_w / (pi AR)
    fuselage (Munk / Perkins & Hage, Raymer eq. 16.25): Cm_alpha_fus = K_f W_f^2 L_f / (c S) per deg
  GCI: Celik et al., J. Fluids Eng. 130 (2008) 078001
  pack sag: V_pack = n_s (V_rest - I_pack R_cell) (series cells, ohmic model)
External source values used here (each with URL and date checked):
  APC 14x8.5E performance file, https://www.apcprop.com/files/PER3_14x85E.dat (header "14x8.5E (14x85E.dat) v2022-0915",
    checked 2026-11-02), 6000 RPM rows at V 39.49 and 41.57 mph. The BOM pusher is the 14x8.5EP: EST that EP is the
    mirrored E geometry, so the E table applies.
  SunnySky X4110S KV400 17x5.8 maker thrust table, 22.2 V and 25 V (analysis/propulsion_data_2026-11-01.json S1).
  ArduPilot QHOVER "Adequate Power": hover above 70 % throttle dangerous (propulsion_data S13,
    https://ardupilot.org/plane/docs/qhover-mode.html, checked 2026-11-01).
  Pack continuous rating is a temperature limit: RCexplained Zeee pack test, continuous limit ~57-58 A set by temperature
    (https://www.radiocontrolinfo.com/understanding-the-true-c-rating-for-lipo-batteries-a-comprehensive-zeee-battery-performance-test/,
    checked 2026-11-02). Not used numerically; the transition check is a sag check (below).
  C11 acceptance limit R_cell <= 6.0 mOhm/cell and transition-sag criterion >= 3.2 V/cell (docs/test/TEST-PLAN.md C11,
    rev 2026-11-02). Resting voltage at 50 % SOC 3.80 V/cell is an EST.
"""
import json, math, os, re, datetime
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
def load(p): return json.load(open(os.path.join(REPO, p), encoding="utf-8"))
def text(p): return open(os.path.join(REPO, p), encoding="utf-8").read()
R = load("analysis/results.json"); A = load("analysis/aero/aero_results.json"); MB = load("analysis/mass/mass_budget.json")
PD = load("analysis/propulsion_data_2026-11-01.json"); SRC = {s["id"]: s for s in PD["sources"]}
C0 = R["concepts"]["C0"]; P = C0["params"]; S_ = C0["sized"]; G_ = C0["geo"]; CG = C0["cg"]; BOM = C0["bom"]
g0 = 9.80665; rho = 1.225; mu = 1.789e-5
out = []

def rec(cid, what, indep, repo, tol_pct=0.0, shared="", note="", rel="eq"):
    d = None if (indep is None or repo in (None, 0)) else 100.0 * (indep - repo) / abs(repo)
    if d is None:
        ok = None
    elif rel == "eq":
        ok = abs(d) <= tol_pct
    elif rel == "ge":
        ok = indep >= repo
    else:
        ok = indep <= repo
    out.append({"id": cid, "check": what, "independent": indep, "repo": repo, "delta_pct": None if d is None else round(d, 2),
                "tolerance_pct": tol_pct if rel == "eq" else None, "relation": rel, "pass": ok, "shared_assumptions": shared, "note": note})
    ds = "   —  " if d is None else f"{d:+7.2f}%"
    iv = "—" if indep is None else f"{indep:.5g}"; rv = "—" if repo is None else f"{repo:.5g}"
    crit = f"tol {tol_pct:>4}%" if rel == "eq" else ("indep >= " if rel == "ge" else "indep <= ") + "repo"
    print(f"{cid:9s} {what[:58]:58s} indep {iv:>10s} repo {rv:>10s} {ds} {crit:>14s} {'PASS' if ok else ('FAIL' if ok is False else 'n/a')}")

# ---------------- geometry / conditions ----------------
m = S_["m"]; W = m * g0; S = S_["S"]; c = S_["chord"]; b = P["span"]; AR = b * b / S
Vc = P["Vc"]; q = 0.5 * rho * Vc**2

# AERO-01 Reynolds number at cruise (aero package chord vs current sizing chord)
Re_c = rho * Vc * c / mu
rec("AERO-01", "Cruise Re (rho V c / mu), current sizing chord", Re_c, A["conditions"]["cruise"]["Re"], 2.0,
    note="aero package geometry (chord %.4f m, MTOW %.3f kg) vs results.json (chord %.4f, MTOW %.3f)" %
    (A["geometry"]["chord_m"], A["geometry"]["MTOW_kg"], c, m))

# ---------------- 2-D section: thin-airfoil theory for NACA 2415 (AERO-02) ----------------
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
rec("AERO-02b", "2-D zero-lift angle deg: thin-airfoil vs XFOIL", math.degrees(a0L), sp["alpha_0L_deg"], 10.0)
rec("AERO-02c", "2-D Cm_c/4: thin-airfoil vs XFOIL", cm4, sp["Cm_c4"], 15.0)

# AERO-03 2-D drag: fully turbulent flat plate x Hoerner FF vs SU2 SA (fully turbulent) at alpha 2 deg, SU2 Re
cft = lambda Re: 0.074 / Re**0.2
cfl = lambda Re: 1.328 / math.sqrt(Re)
def cf_comp(Re, xtr):
    if xtr <= 0: return cft(Re)
    Rt = Re * xtr; return cft(Re) - xtr * (cft(Rt) - cfl(Rt))
FFw = lambda tc: 1 + 2 * tc + 60 * tc**4
Re_su2 = A["cfd"]["Re"]
cd_turb = 2 * cft(Re_su2) * FFw(0.15)
row2 = [r for r in A["comparison_2D"] if r["alpha_deg"] == 2][0]
rec("AERO-03", "2-D cd fully turbulent (2 Cf FF) vs SU2 SA alpha 2 (Re 3.50e5)", cd_turb, row2["su2_SA_CD"], 10.0)
# XFOIL transitional at the cruise Re: transition locations read from the committed XFOIL polar (an XFOIL output -> shared)
xf = np.array([[float(v) for v in l.split()[:7]] for l in text("analysis/aero/out/xfoil_n2415_cruise_ncrit9.txt").splitlines()
               if l.strip() and not l.lstrip().startswith("#")])
xr = xf[np.argmin(abs(xf[:, 0] - 2.0))]
Re_xf = sp["Re"]
cd_mix = (cf_comp(Re_xf, xr[5]) + cf_comp(Re_xf, xr[6])) * FFw(0.15)
rec("AERO-03b", "2-D cd composite lam/turb (XFOIL xtr) vs XFOIL alpha 2 (Re 3.94e5)", cd_mix, xr[2], 20.0,
    shared="transition locations %.3f top / %.3f bottom from the XFOIL polar" % (xr[5], xr[6]))

# AERO-04 CFD mesh study GCI (Celik 2008) at alpha 10
ms = A["cfd"]["mesh_study"]["alpha_10"]
N = ms["cells"]; h1, h2, h3 = [N[k] ** -0.5 for k in ("L3", "L2", "L1")]
r21, r32 = h2 / h1, h3 / h2
def gci(f1, f2, f3):
    e21, e32 = f2 - f1, f3 - f2; s = np.sign(e32 / e21); p = 1.0
    for _ in range(200):
        qp = math.log((r21**p - s) / (r32**p - s)); p = abs(math.log(abs(e32 / e21)) + qp) / math.log(r21)
    ea = abs((f1 - f2) / f1); return p, 1.25 * ea / (r21**p - 1) * 100
pC, gC = gci(ms["CL"]["L3"], ms["CL"]["L2"], ms["CL"]["L1"])
rec("AERO-04", "SU2 GCI_fine on CL at alpha 10 (%)", gC, ms["GCI_CL"]["GCI_fine_pct"], 10.0, note="order p %.2f, r21 %.3f, r32 %.3f" % (pC, r21, r32))

# AERO-05 CLmax 2-D adopted 1.30 (from a paper abstract) -- no hand method; the repo solvers bracket it
nf = A["CL_max_2D"]
spread = [nf["xfoil_stall_Re"], nf["neuralfoil_stall_Re"], nf["su2_SA_cruise_Re"]["CL_max"]]
rec("AERO-05", "2-D CLmax: mean of XFOIL/NeuralFoil/SU2 vs adopted 1.30", float(np.mean(spread)), nf["adopted_2D"], 10.0,
    shared="all three are repo solver outputs; spread %.2f-%.2f" % (min(spread), max(spread)))

# ---------------- 3-D lift ----------------
CLmax3 = 0.9 * nf["adopted_2D"]
rec("AERO-06", "3-D CLmax: Raymer 0.9 x CLmax_2D vs adopted (critical section)", CLmax3, A["CL_max_3D"]["adopted"], 5.0,
    shared="CLmax_2D 1.30 is the same input")
Vs_ind = math.sqrt(2 * W / (rho * S * CLmax3))
CL_R11 = 2 * W / (rho * S * 12.0**2)
m_R11 = 0.5 * rho * S * 12.0**2 * P["CLmax"] / g0
rec("AERO-07", "Stall speed m/s with Raymer CLmax (sizing S, MTOW)", Vs_ind, P["Vs"], 3.0,
    note="R11 (12 m/s) fails below CLmax %.3f (%.1f %%) or above MTOW %.3f kg (+%.3f kg)" %
    (CL_R11, 100 * (CL_R11 / P["CLmax"] - 1), m_R11, m_R11 - m))
S_ind = 2 * W / (rho * P["Vs"]**2 * P["CLmax"])
rec("AERO-08", "Wing area m2 from stall (same formula, arithmetic only)", S_ind, S, 0.5, shared="same formula and inputs")
CL_c = 2 * W / (rho * Vc**2 * S)
rec("AERO-09", "Cruise CL at 18 m/s", CL_c, S_["CL"], 0.5, shared="same formula")
tau = 0.17
a_w = 2 * math.pi / (1 + 2 * math.pi * (1 + tau) / (math.pi * AR))
rec("AERO-10", "Wing lift slope /rad: lifting line (a0 2pi, tau .17) vs repo VLM", a_w, load("analysis/aero.json")["wing_CLa_per_rad"], 7.0,
    note="Helmbold in sizing gives %.3f" % G_["aw"])
ARt = G_["hSpan"]**2 / G_["Sh"]; a_t = 2 * math.pi / (1 + 2 * math.pi * (1 + tau) / (math.pi * ARt))
deda = 2 * a_w / (math.pi * AR); eta_t = 0.9
CLa_ac = a_w + eta_t * a_t * G_["Sh"] / S * (1 - deda)
rec("AERO-10b", "Aircraft CL_alpha /rad (wing + tail, no pod) vs AVL no pod", CLa_ac, A["lift_curve"]["CL_alpha_per_rad"]["AVL_aircraft_nopod"], 7.0)

# ---------------- drag ----------------
e_ray = 1.78 * (1 - 0.045 * AR**0.68) - 0.64
rec("AERO-11", "Oswald e: Raymer 12.49 >= sizing e 0.80 (conservative)", e_ray, P["e"], rel="ge",
    note="repo build-up fit %s; AVL inviscid %.3f" % (A["drag"].get("e_oswald_fit", "—"), A["trim_cruise"]["e_AVL"]))
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
rec("AERO-12", "CD0 total: independent build-up (xtr .30, +10%) vs sizing", CD0_ind, S_["CD0"], 15.0,
    shared="bluff items (stopped motors/props, clamps, legs, feet, canopy) reuse repo Hoerner CdA = %.4f m2" % parts["bluff_shared"],
    note="fully turbulent bound CD0 %.4f; repo build-up %.4f" % (cda_t / S, A["drag"]["CD0_total"]))
LD_ind = CL_c / (CD0_ind + CL_c**2 / (math.pi * e_ray * AR))
rec("AERO-13", "Cruise L/D: independent CD0 + Raymer e vs sizing", LD_ind, S_["LD"], 10.0)
LD_turb = CL_c / (cda_t / S + CL_c**2 / (math.pi * e_ray * AR))
P_ind = W / LD_ind * Vc / (P["etaProp"] * P["etaMEc"])
rec("AERO-14", "Cruise electrical power W (same eta 0.60 x 0.85)", P_ind, S_["P_cruise"], 10.0, shared="etaProp 0.60, etaMEc 0.85 (EST)",
    note="fully turbulent bound: L/D %.2f, P %.0f W" % (LD_turb, W / LD_turb * Vc / (P["etaProp"] * P["etaMEc"])))

# ---------------- pusher efficiency (AERO-15) ----------------
Ap = math.pi * (14 * 0.0254 / 2)**2; Tc = S_["D_cruise"]
eta_i = 2 / (1 + math.sqrt(1 + Tc / (q * Ap)))
# APC 14x8.5E, 6000 RPM rows (https://www.apcprop.com/files/PER3_14x85E.dat, v2022-0915, checked 2026-11-02):
#   V mph, Pe, thrust N, power W, torque N m
APC = [(39.49, 0.7345, 8.745, 210.200, 0.335), (41.57, 0.7403, 7.896, 198.216, 0.315)]
V_mph = Vc / 0.44704                                     # 1 mph = 0.44704 m/s (exact, NIST SP 811)
fr = (V_mph - APC[0][0]) / (APC[1][0] - APC[0][0])
apc = [APC[0][k] + fr * (APC[1][k] - APC[0][k]) for k in range(5)]
eta_apc, T_apc, Psh_apc = apc[1], apc[2], apc[3]
rec("AERO-15", "Pusher eta: 0.80 x momentum-ideal >= sizing EST 0.60", 0.80 * eta_i, P["etaProp"], rel="ge",
    note="ideal %.3f at T = D_cruise %.2f N; 0.80 profile/swirl factor is EST" % (eta_i, Tc))
rec("AERO-15b", "Pusher eta: APC 14x8.5E maker Pe at 18 m/s, 6000 rpm >= 0.60", eta_apc, P["etaProp"], rel="ge",
    note="interpolated at %.2f mph: thrust %.3f N (cruise drag %.3f N), shaft %.1f W, Pe %.4f" % (V_mph, T_apc, Tc, Psh_apc, eta_apc))
rec("AERO-15c", "Pusher eta: 0.80 x momentum-ideal vs APC maker Pe", 0.80 * eta_i, eta_apc, 5.0,
    note="APC thrust at 6000 rpm vs required %+.2f %% (so 6000 rpm is the cruise operating point)" % (100 * (T_apc / Tc - 1)))
P_cr_apc = Tc * Vc / (eta_apc * P["etaMEc"])

# ---------------- hover ----------------
D = P["liftD"]; Ad = math.pi * D * D / 4; T_unit = W / 4; Tg = T_unit / g0 * 1000
s1 = SRC["S1"]["values"]["17x5.8"]
t22 = np.array(s1["22.2V"], float); t25 = np.array(s1["25V"], float)       # columns: A, gf, W, g/W
P_unit_tab = float(np.interp(Tg, t22[:, 1], t22[:, 2]))
I_unit_tab = float(np.interp(Tg, t22[:, 1], t22[:, 0]))
P_h_tab = 4 * P_unit_tab * P["kCtrl"]
rec("AERO-16", "Hover power W: maker table (all rows) interpolated x kCtrl", P_h_tab, S_["P_hover"], 5.0,
    shared="SunnySky 17x5.8 table (BOM buys 17x5.5) and kCtrl 1.10 (EST)")
P_ideal = T_unit**1.5 / math.sqrt(2 * rho * Ad)
P_h_mt = 4 * P_ideal * P["kCtrl"] / (0.65 * 0.80)
rec("AERO-16b", "Hover power W: momentum theory, FM 0.65, eta_m+esc 0.80 (EST)", P_h_mt, S_["P_hover"], 10.0, shared="kCtrl 1.10")
rec("AERO-16c", "Disk loading N/m2", T_unit / Ad, S_["diskLoading"], 0.5, shared="same formula")

# hover current (AERO-17): nominal, and loaded with the ohmic sag model at the C11 limit
Vrest = 3.80; Rcell = 0.006; ns = 6                       # EST 50 % SOC rest voltage; C11 limit 6.0 mOhm/cell (rev 2026-11-02)
V0 = ns * Vrest; Rp = ns * Rcell
I_h_nom = P_h_tab / P["Vpack"]
rec("AERO-17", "Hover current A at 22.2 V from the maker-table hover power", I_h_nom, S_["I_hover"], 5.0, shared="kCtrl 1.10",
    note="direct table current x kCtrl: 4 x %.2f A x %.2f = %.1f A" % (I_unit_tab, P["kCtrl"], 4 * I_unit_tab * P["kCtrl"]))
I_h_sag = (V0 - math.sqrt(V0**2 - 4 * Rp * S_["P_hover"])) / (2 * Rp)
rec("AERO-17b", "Hover current A, sag model (3.80 V rest, 6.0 mOhm) vs 21.0 V", I_h_sag, S_["I_hover_loaded"], 5.0,
    note="pack under hover load %.2f V (%.3f V/cell); repo assumes 21.0 V" % (V0 - Rp * I_h_sag, (V0 - Rp * I_h_sag) / ns))

# ---------------- T/W (AERO-18 maker table; AERO-32 sag-aware) ----------------
Tmax22 = t22[-1, 1]; m_bu = MB["total_kg"]
TW_bu = 4 * Tmax22 / 1000 / m_bu
rec("AERO-18", "T/W on maker 22.2 V table with bottom-up CAD mass vs repo", TW_bu, S_["TW"], 2.0,
    shared="maker max thrust 3130 gf (17x5.8)",
    note="bottom-up mass %.4f kg (mass_budget.json); R13 >= 1.6 holds up to MTOW %.3f kg" % (m_bu, 4 * Tmax22 / 1000 / 1.6))
rec("AERO-18b", "T/W on maker 22.2 V table >= R13 1.6", 4 * Tmax22 / 1000 / m, 1.6, rel="ge")
kT = math.log(t25[-1, 1] / t22[-1, 1]) / math.log(25 / 22.2)
kI = math.log(t25[-1, 0] / t22[-1, 0]) / math.log(25 / 22.2)
def tw_sag(vrest, rcell, mass):
    V = 22.2
    for _ in range(100):
        Im = t22[-1, 0] * (V / 22.2)**kI
        V = ns * vrest - 4 * Im * ns * rcell
    T = t22[-1, 1] * (V / 22.2)**kT
    return V, Im, T, 4 * T / 1000 / mass
V_sag, I_sag, T_sag, TW_sag = tw_sag(Vrest, Rcell, m)
TW_req = 1 / 0.70                                          # ArduPilot S13: hover > 70 % throttle dangerous -> T/W >= 1/0.7
_, _, _, TW_sag37 = tw_sag(3.70, Rcell, m)
rec("AERO-32", "T/W at mid-pack under sag (3.80 V, 6.0 mOhm) >= 1/0.70", TW_sag, TW_req, rel="ge",
    note="power-law fit of maker full-throttle rows: thrust exp %.3f, current exp %.3f; pack %.2f V, %.1f A/motor, %.0f gf/motor; "
         "at 3.70 V/cell rest (EST) T/W %.3f; ESC/wiring resistance and avionics current ignored (optimistic)" % (kT, kI, V_sag, I_sag, T_sag, TW_sag37))

# ---------------- transition (AERO-19): sag check at the C11 limit ----------------
V_cell_tr = Vrest - S_["I_trans"] * Rcell
rec("AERO-19", "Transition: cell V at 82 A, 6.0 mOhm, 50% SOC >= C11 3.2 V", V_cell_tr, 3.2, rel="ge",
    note="pack %.2f V; R_cell that just reaches 3.2 V: %.2f mOhm; 82 A = (P_hover + 2 P_cruise) / 21.0 V (EST), 2 x 20 s" %
    (ns * V_cell_tr, 1000 * (Vrest - 3.2) / S_["I_trans"]))

# ---------------- energy ----------------
E_use = C0["pick"]["Wh"] * (1 - P["reserve"]) * P["etaBatt"] * 3600
t_hov = P["tHover"] + P["tTrans"]
t_ind = (E_use - P_h_tab * t_hov) / P_ind / 60
t_apc = (E_use - S_["P_hover"] * t_hov) / P_cr_apc / 60
rec("AERO-20", "Cruise time available min (indep. hover + cruise power)", t_ind, S_["t_cruise_avail_min"], 15.0,
    shared="pack 144.3 Wh, reserve 20 %, etaBatt 0.95, 40 s transition at hover power",
    note="with APC maker eta %.3f instead of 0.60: cruise %.0f W, %.2f min (sizing is conservative)" % (eta_apc, P_cr_apc, t_apc))
s2 = SRC["S2"]["values"]
rec("AERO-21", "Pack energy Wh = maker 6.5 Ah x 22.2 V", s2["capacity_mAh"] / 1000 * s2["voltage_V"], C0["pick"]["Wh"], 0.5)
rec("AERO-21b", "Pack mass kg: maker listing 825 +/- 20 g vs sizing", s2["net_weight_g"] / 1000, C0["pick"]["kg"], 2.5,
    note="tolerance = maker's +/- 20 g on 825 g (2.4 %)")

# ---------------- mass / CG ----------------
mi = np.array([i["m"] for i in CG["items"]]); xi = np.array([i["x"] for i in CG["items"]])
rec("AERO-22", "MTOW kg: sum of CG item list", float(mi.sum()), m, 0.5, shared="item masses are the sizing's")
rec("AERO-22b", "MTOW kg: bottom-up CAD/vendor roll-up vs sizing", m_bu, m, 2.0,
    note="estimated (unweighed, printed/EST) share %.3f kg = %.1f %% of the roll-up" % (MB["est_share_kg"], 100 * MB["est_share_kg"] / m_bu))
foam = 0.685 * 0.15 * c * c * b * P["rhoFoam"]
mw = foam + 2 * P["wGlass"] * S + P["m_spar"] + P["mWingHardware"]
rec("AERO-23", "Wing mass kg: 0.685 t c^2 b foam + tape + spar + hardware", mw, S_["m_wing"], 5.0,
    shared="foam 32 kg/m3 (SRC-15), tape 0.06 kg/m2 (EST), spar 0.675 kg and hardware 0.253 kg (mass_budget.json calibration)")
wing_bu = [g for g in MB["groups"] if g["group"] == "Wing"][0]["bottom_up_g"] / 1000
rec("AERO-23b", "Wing mass kg: bottom-up CAD wing group vs sizing", wing_bu, S_["m_wing"], 5.0,
    note="the bottom-up wing group also carries the tail tape skins (EST ~%.0f g)" % (1000 * 2 * P["wGlass"] * (G_["Sh"] + G_["Sv"])))
xcg = float((mi * xi).sum() / mi.sum())
rec("AERO-24", "CG %MAC from item moments", -xcg / c * 100, CG["pct"]["target"], 2.0, shared="item stations from repo",
    note="payload allowance is 0 kg (R12), so the no-payload CG is the same")

# ---------------- stability ----------------
Vh = G_["Sh"] * G_["lh"] / (S * c); Vv = G_["Sv"] * G_["lh"] / (S * b)
rec("AERO-27", "Horizontal tail volume Vh", Vh, G_["Vh"], 1.0, note="Raymer tab 6.4 homebuilt typical 0.50: C0 is 30 % below")
rec("AERO-27b", "Vertical tail volume Vv", Vv, G_["Vv"], 1.0, note="Raymer homebuilt typical 0.04: C0 is 25 % below")
hn_np = 0.25 + eta_t * Vh * (a_t / a_w) * (1 - deda)
Lf, Wf = 0.85, 0.16
xq = (0.45 + 0.25 * c) / Lf
Kf = float(np.interp(xq, [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7], [0.005, 0.006, 0.008, 0.012, 0.018, 0.027, 0.042]))  # approx. digitization of Perkins & Hage / Raymer fig. 16.14, +/-30 %
Cma_f = Kf * Wf**2 * Lf / (c * S) * 180 / math.pi
dh_pod = -Cma_f / CLa_ac
hn = hn_np + dh_pod
rec("AERO-25", "Neutral point %MAC with pod (Munk/Perkins-Hage) vs AVL pod", hn * 100, A["neutral_point"]["AVL_pod_pct_MAC"], 5.0,
    note="pod shift %.1f %% MAC (K_f %.3f at x/L %.2f) vs AVL %.1f; stopped props not modelled by either" % (dh_pod * 100, Kf, xq, A["neutral_point"]["pod_shift_pct_MAC"]))
rec("AERO-25b", "Neutral point %MAC wing+tail (no pod) vs AVL no pod", hn_np * 100, A["neutral_point"]["AVL_nopod_pct_MAC"], 5.0)
rec("AERO-25c", "Neutral point %MAC: AeroSandbox VLM vs AVL pod (cross-tool)", A["neutral_point"]["AeroSandbox_VLM_pct_MAC"],
    A["neutral_point"]["AVL_pod_pct_MAC"], 5.0, shared="both repo tools on the same geometry")
rec("AERO-26", "Static margin %MAC at CG 28 % (hand NP - CG)", (hn - CG["pct"]["target"] / 100) * 100, A["neutral_point"]["static_margin_pct"]["CG_28pct"], 25.0,
    note="difference in points: %+.2f %% MAC" % ((hn - CG["pct"]["target"] / 100) * 100 - A["neutral_point"]["static_margin_pct"]["CG_28pct"]))

# ---------------- AERO-29 speed for max L/D ----------------
CLs = math.sqrt(math.pi * e_ray * AR * CD0_ind); Vs_ld = math.sqrt(2 * W / (rho * S * CLs))
CLs_rep = math.sqrt(math.pi * P["e"] * S_["AR"] * S_["CD0"]); Vs_rep = math.sqrt(2 * W / (rho * S * CLs_rep))
rec("AERO-29", "Speed for max L/D m/s: independent polar vs sizing polar", Vs_ld, Vs_rep, 5.0,
    note="sizing polar V* %.3f m/s (results.json CD0, e, AR, W, S); analysis/cruise_speed_trade.json still holds %.3f (stale, 2026-10-27); 18 m/s = %.2f V*" %
    (Vs_rep, load("analysis/cruise_speed_trade.json")["crossCheck"]["Vstar_mps"], Vc / Vs_rep))

# ---------------- AERO-30 governing docs vs results.json ----------------
def block(path, tag):
    t = text(path); i = t.index("<!-- gen:%s -->" % tag); return t[i:t.index("<!-- /gen:%s -->" % tag)]
def num(blk, pat):
    mt = re.search(pat, blk); return float(mt.group(1).replace(",", "")) if mt else None
db = block("docs/DESIGN-BASIS.md", "outcomes"); sm = block("docs/research/stall-margin.md", "stall_status")
NPs = G_["hn"] * 100
doc_items = [  # (doc, label, regex, repo value, printed decimals)
    ("DESIGN-BASIS", "MTOW kg", r"MTOW ([\d.]+) kg", m, 2), ("DESIGN-BASIS", "S m2", r"S ([\d.]+) m²", S, 3),
    ("DESIGN-BASIS", "chord mm", r"chord ([\d.]+) mm", c * 1000, 1), ("DESIGN-BASIS", "AR", r"AR ([\d.]+)", S_["AR"], 2),
    ("DESIGN-BASIS", "CL_max", r"CL_max ([\d.]+)", P["CLmax"], 3), ("DESIGN-BASIS", "T/W", r"T/W ([\d.]+)", S_["TW"], 2),
    ("DESIGN-BASIS", "hover W", r"hover (\d+) W", S_["P_hover"], 0), ("DESIGN-BASIS", "hover A", r"W / ([\d.]+) A", S_["I_hover"], 1),
    ("DESIGN-BASIS", "transition A", r"transition peak (\d+) A", S_["I_trans"], 0),
    ("DESIGN-BASIS", "cruise min", r"([\d.]+) min cruise available", S_["t_cruise_avail_min"], 1),
    ("DESIGN-BASIS", "NP %MAC", r"neutral point ([\d.]+) % MAC", NPs, 1), ("DESIGN-BASIS", "SM %MAC", r"static margin ([\d.]+) %", G_["SM"] * 100, 1),
    ("DESIGN-BASIS", "spend $", r"committed \$([\d.,]+)", BOM["total"], 2), ("DESIGN-BASIS", "reserve $", r"crash reserve \$([\d.,]+)", BOM["crash"], 2),
    ("stall-margin", "chord mm", r"chord ([\d.]+) mm", c * 1000, 1), ("stall-margin", "S m2", r"S ([\d.]+) m²", S, 3),
    ("stall-margin", "MTOW kg", r"MTOW ([\d.]+) kg", m, 3), ("stall-margin", "cruise min", r"cruise ([\d.]+) min", S_["t_cruise_avail_min"], 2)]
doc_rows = []
for doc, lab, pat, rv, dp in doc_items:
    dv = num(db if doc == "DESIGN-BASIS" else sm, pat)
    ok = dv is not None and abs(dv - rv) <= 0.5 * 10**(-dp) + 1e-9
    doc_rows.append({"doc": doc, "item": lab, "doc_value": dv, "repo_value": rv, "match": ok})
n_ok = sum(r["match"] for r in doc_rows)
rec("AERO-30", "Docs generated blocks: numbers matching results.json", float(n_ok), float(len(doc_rows)), 0.0,
    note="mismatches: " + (", ".join(f"{r['doc']} {r['item']} {r['doc_value']} vs {r['repo_value']:.4g}" for r in doc_rows if not r["match"]) or "none"))

# ---------------- cost ----------------
goods = sum(l["qty"] * l["unit"] for l in BOM["lines"])
tot = goods * 1.1025 + BOM["shipping"]
rec("AERO-31", "BOM committed total $ (goods x 1.1025 + shipping)", tot, BOM["total"], 0.1, shared="all unit prices and shipping from repo")
rec("AERO-31b", "Crash reserve $ = cap 2000 - total (R7 target >= 100)", BOM["cap"] - tot, BOM["crash"], 0.1,
    note="R7 target >= $100 (est.); reserve is %.1f %% of the cap" % (100 * (BOM["cap"] - tot) / BOM["cap"]))

res = {"generated": datetime.date.today().isoformat(), "script": "analysis/validation/check_aero.py",
       "id_rule": "check id = claim id in claims_aero.json; extra checks of the same claim are suffixed b, c",
       "inputs_read_only": ["analysis/results.json", "analysis/aero/aero_results.json", "analysis/aero.json",
                            "analysis/aero/out/xfoil_n2415_cruise_ncrit9.txt", "analysis/mass/mass_budget.json",
                            "analysis/propulsion_data_2026-11-01.json", "analysis/cruise_speed_trade.json",
                            "docs/DESIGN-BASIS.md", "docs/research/stall-margin.md"],
       "external_values": {"APC_14x8.5E_6000rpm": {"url": "https://www.apcprop.com/files/PER3_14x85E.dat", "checked": "2026-11-02",
                                                   "rows_V_mph_Pe_T_N_P_W_Q_Nm": APC},
                           "ArduPilot_hover_throttle_limit": {"value": 0.70, "src": "propulsion_data S13"},
                           "C11_R_cell_limit_ohm": Rcell, "C11_transition_sag_V_per_cell": 3.2, "V_rest_50pct_SOC_EST": Vrest,
                           "pack_continuous_is_thermal": "https://www.radiocontrolinfo.com/understanding-the-true-c-rating-for-lipo-batteries-a-comprehensive-zeee-battery-performance-test/ (checked 2026-11-02)"},
       "intermediate": {"Re_cruise": Re_c, "alpha0L_thin_deg": math.degrees(a0L), "cm4_thin": cm4, "a_w": a_w, "a_t": a_t, "deda": deda,
                        "CD0_indep": CD0_ind, "CD0_fully_turbulent": cda_t / S, "parts_CdA_m2": parts, "e_raymer": e_ray, "LD_indep": LD_ind,
                        "LD_fully_turbulent": LD_turb, "P_cruise_indep_W": P_ind, "eta_ideal_pusher": eta_i,
                        "pusher_APC_interp": {"V_mph": V_mph, "Pe": eta_apc, "thrust_N": T_apc, "shaft_W": Psh_apc, "torque_Nm": apc[4]},
                        "P_cruise_with_APC_eta_W": P_cr_apc, "t_cruise_with_APC_eta_min": t_apc,
                        "P_hover_table_W": P_h_tab, "P_hover_momentum_W": P_h_mt, "I_hover_sag_A": I_h_sag,
                        "TW_maker_bottom_up_mass": TW_bu, "m_max_for_TW_1p6_kg": 4 * Tmax22 / 1000 / 1.6,
                        "TW_sag": {"k_thrust": kT, "k_current": kI, "V_pack": V_sag, "I_motor_A": I_sag, "I_pack_A": 4 * I_sag,
                                   "T_motor_gf": T_sag, "TW": TW_sag, "TW_required": TW_req, "TW_at_3p70V_rest": TW_sag37},
                        "transition_cell_V": V_cell_tr, "R_cell_limit_for_3p2V_mohm": 1000 * (Vrest - 3.2) / S_["I_trans"],
                        "stall_R11_CLmax_min": CL_R11, "stall_R11_m_max_kg": m_R11,
                        "Vstar_sizing_polar": Vs_rep, "Kf": Kf, "dh_pod": dh_pod, "hn": hn, "GCI_p": pC, "doc_rows": doc_rows},
       "checks": out}
json.dump(res, open(os.path.join(HERE, "checks_aero.json"), "w", encoding="utf-8", newline="\n"), indent=1, default=float)
print(f"\n{sum(1 for o in out if o['pass'])} pass / {sum(1 for o in out if o['pass'] is False)} fail / {len(out)} checks -> analysis/validation/checks_aero.json")
