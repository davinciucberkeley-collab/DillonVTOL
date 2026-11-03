"""Proof chains: every claim broken down into the equations it uses, the variables in them, and where each variable's
value comes from. The checker re-runs the arithmetic and compares the result with the claim.

Rules this script keeps:
  * No input value is typed here. Each one is read from the file it cites (a JSON path or a key in a text file) when
    the script runs. The exceptions are physical constants and textbook coefficients, and each of those names its source.
  * Where a variable is another claim's output (for example, the wing area used by the cruise CL), the link is recorded,
    and the variable's value is compared with that claim's value. A mismatch is reported as a stale link: the chain is
    using an old number.
  * External sources (datasheets, papers, vendor pages) are linked by their SRC id in source_audit.json. That file holds
    the value-by-value check against the source itself.
  * A claim with no closed-form arithmetic (a convergence history, a CAD interference count, a drawing check) is listed
    as "evidence" with its files and the script that checked it. It is shown, not skipped.

Run:  py analysis/validation/proofs.py      -> analysis/validation/proofs.json   (< 1 s)
"""
import json, math, re, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
VAL = ROOT / "analysis" / "validation"


# ---------- readers: every value carries the place it was read from ----------
_cache = {}
def _json(f):
    if f not in _cache:
        _cache[f] = json.loads((ROOT / f).read_text(encoding="utf-8"))
    return _cache[f]

def J(f, path):
    """value at a dotted path in a JSON file; [i] indexes lists"""
    d = _json(f)
    for part in re.findall(r"[^.\[\]]+|\[\d+\]", path):
        d = d[int(part[1:-1])] if part.startswith("[") else d[part]
    return d, {"kind": "file", "ref": f"{f}#{path}"}

def KV(f, key):
    """key=value[|unit|note] line in a text file (cad/params.txt, cad/sim/results.txt)"""
    for i, line in enumerate((ROOT / f).read_text(encoding="utf-8").splitlines(), 1):
        if line.startswith(key + "="):
            return float(line.split("=", 1)[1].split("|")[0]), {"kind": "file", "ref": f"{f}:{i}"}
    raise KeyError(f"{key} not in {f}")

def K(value, why, src_id=None):
    """a physical constant or textbook coefficient, with its source"""
    s = {"kind": "constant", "ref": why}
    if src_id:
        s["src_id"] = src_id
    return value, s

def CI(claim_id, key):
    """a value the claim's own checker read and recorded in the claim's inputs (the checker script names the file)"""
    return float(CLAIMS[claim_id]["inputs"][key]), {"kind": "checker", "ref": f"{CLAIMS[claim_id]['source_file']} {claim_id}.inputs.{key}"}


def V(sym, tex, read, unit, desc, up=None, src_id=None, scale=1.0, upk=None):
    val, src = read
    if src_id:
        src["src_id"] = src_id
    out = {"sym": sym, "tex": tex, "value": val * scale if isinstance(val, (int, float)) else val, "unit": unit, "desc": desc, "src": src}
    if scale != 1.0:
        src["scaled"] = scale
    if up:
        out["from_claim"] = up
    if upk:
        out["link_factor"] = upk   # compare value x upk with the upstream claim (e.g. W / g against a mass)
    return out

def S(tex, expr, out, unit, desc=""):
    return {"tex": tex, "expr": expr, "out": out, "unit": unit, "desc": desc}


MAT = json.loads((VAL / "validation_matrix.json").read_text(encoding="utf-8"))
CLAIMS = {c["id"]: c for c in MAT["claims"]}
AUD = json.loads((VAL / "source_audit.json").read_text(encoding="utf-8")) if (VAL / "source_audit.json").exists() else {"sources": [], "claim_sources": {}}

RES, AER, PAR, SIM, CFD = "analysis/results.json", "analysis/aero/aero_results.json", "cad/params.txt", "cad/sim/results.txt", "analysis/cfd3d/out/cfd3d_results.json"
C0 = "concepts.C0"
g0 = lambda: V("g", "g", K(9.80665, "standard gravity, CGPM 1901 / ISO 80000-3"), "m/s²", "gravitational acceleration")
rho = lambda: V("rho", r"\rho", K(1.225, "ISA sea-level density", "SRC-19"), "kg/m³", "air density (ISA sea level)")


# ---------- the proofs ----------
# result: the step output compared with the claim's value; tol: % allowed; rel: "eq" (within tol) or "le" (result must not exceed bound)
P = {}

P["AERO-01"] = dict(vars=[rho(), V("V", "V", KV(PAR, "chord") and J(RES, f"{C0}.params.Vc"), "m/s", "cruise speed"),
                          V("c", "c", J(AER, "geometry.chord_m"), "m", "wing chord used by the aero package"),
                          V("mu", r"\mu", J(AER, "conditions.cruise.mu"), "Pa·s", "air viscosity (ISA)", src_id="SRC-19")],
                    steps=[S(r"Re = \frac{\rho V c}{\mu}", "rho*V*c/mu", "Re", "-", "Reynolds number at cruise")], result="Re", tol=0.5)

P["AERO-07"] = dict(vars=[V("W", "W", J(RES, f"{C0}.sized.W"), "N", "weight at MTOW", up="AERO-22", upk=1/9.80665), rho(),
                          V("S", "S", J(RES, f"{C0}.sized.S"), "m²", "wing area", up="AERO-08"),
                          V("CLmax", r"C_{L,\max}", J(AER, "CL_max_3D.adopted"), "-", "aircraft maximum lift coefficient", up="AERO-06")],
                    steps=[S(r"V_s = \sqrt{\frac{2W}{\rho S C_{L,\max}}}", "math.sqrt(2*W/(rho*S*CLmax))", "Vs", "m/s", "stall speed")], result="Vs", tol=0.5)

P["AERO-08"] = dict(vars=[V("m", "m", J(RES, f"{C0}.sized.m"), "kg", "MTOW", up="AERO-22"), g0(), rho(),
                          V("Vs", "V_s", J(RES, f"{C0}.params.Vs"), "m/s", "design stall speed", up="AERO-07"),
                          V("CLmax", r"C_{L,\max}", J(RES, f"{C0}.params.CLmax"), "-", "aircraft maximum lift coefficient", up="AERO-06")],
                    steps=[S("W = m g", "m*g", "W", "N", "weight"), S(r"S = \frac{2W}{\rho V_s^2 C_{L,\max}}", "2*W/(rho*Vs**2*CLmax)", "S", "m²", "wing area that stalls at V_s")],
                    result="S", tol=0.5)

P["AERO-09"] = dict(vars=[V("W", "W", J(RES, f"{C0}.sized.W"), "N", "weight", up="AERO-22", upk=1/9.80665), rho(),
                          V("V", "V", J(RES, f"{C0}.params.Vc"), "m/s", "cruise speed"),
                          V("S", "S", J(RES, f"{C0}.sized.S"), "m²", "wing area", up="AERO-08")],
                    steps=[S(r"C_L = \frac{2W}{\rho V^2 S}", "2*W/(rho*V**2*S)", "CL", "-", "cruise lift coefficient")], result="CL", tol=0.5)

P["AERO-11"] = dict(vars=[V("AR", "AR", J(RES, f"{C0}.sized.AR"), "-", "aspect ratio")],
                    steps=[S(r"e = 1.78\,(1 - 0.045\,AR^{0.68}) - 0.64", "1.78*(1-0.045*AR**0.68)-0.64", "e", "-", "Oswald efficiency, Raymer 5th ed. eq. 12.49 (straight wing)")],
                    result="e", rel="ge", note="The claim is that the sizing's e = 0.80 is conservative: it must not exceed Raymer's estimate.")

P["AERO-13"] = dict(vars=[V("CL", "C_L", J(RES, f"{C0}.sized.CL"), "-", "cruise CL", up="AERO-09"),
                          V("CD0", "C_{D0}", J(RES, f"{C0}.sized.CD0"), "-", "zero-lift drag", up="AERO-12"),
                          V("e", "e", J(RES, f"{C0}.params.e"), "-", "Oswald efficiency", up="AERO-11"),
                          V("AR", "AR", J(RES, f"{C0}.sized.AR"), "-", "aspect ratio")],
                    steps=[S(r"C_{Di} = \frac{C_L^2}{\pi e AR}", "CL**2/(math.pi*e*AR)", "CDi", "-", "induced drag"),
                           S(r"L/D = \frac{C_L}{C_{D0} + C_{Di}}", "CL/(CD0+CDi)", "LD", "-", "cruise lift-to-drag ratio")], result="LD", tol=0.5)

P["AERO-14"] = dict(vars=[V("W", "W", J(RES, f"{C0}.sized.W"), "N", "weight", up="AERO-22", upk=1/9.80665),
                          V("LD", "L/D", J(RES, f"{C0}.sized.LD"), "-", "lift-to-drag ratio", up="AERO-13"),
                          V("V", "V", J(RES, f"{C0}.params.Vc"), "m/s", "cruise speed"),
                          V("ep", r"\eta_p", J(RES, f"{C0}.params.etaProp"), "-", "propeller efficiency (assumed)", up="AERO-15"),
                          V("em", r"\eta_m", J(RES, f"{C0}.params.etaMEc"), "-", "motor + ESC efficiency (assumed)")],
                    steps=[S(r"D = \frac{W}{L/D}", "W/LD", "D", "N", "cruise drag"), S(r"P = \frac{D\,V}{\eta_p \eta_m}", "D*V/(ep*em)", "P", "W", "electrical cruise power")],
                    result="P", tol=0.5)

P["AERO-15"] = dict(vars=[rho(), V("V", "V", J(RES, f"{C0}.params.Vc"), "m/s", "cruise speed"),
                          V("T", "T", J(RES, f"{C0}.sized.D_cruise"), "N", "cruise thrust = drag (analysis/results.json sized.D_cruise)"),
                          V("Dp", "D_p", KV(PAR, "pushProp"), "m", "pusher propeller diameter (14 in)", src_id="SRC-14")],
                    steps=[S(r"q = \tfrac12 \rho V^2", "0.5*rho*V**2", "q", "Pa", "dynamic pressure"), S(r"A = \pi D_p^2/4", "math.pi*Dp**2/4", "A", "m²", "disc area"),
                           S(r"\eta_{ideal} = \frac{2}{1 + \sqrt{1 + T/(qA)}}", "2/(1+math.sqrt(1+T/(q*A)))", "eta", "-", "momentum-theory upper bound on propeller efficiency")],
                    result="eta", rel="ge", note="The claim's 0.60 is an assumed efficiency; it must not exceed the ideal (momentum-theory) value. The APC maker value at the cruise point (0.737, check_aero.py AERO-15b) is the tighter bound.")

P["AERO-16"] = dict(vars=[V("n", "n", J(RES, f"{C0}.sized.nUnits"), "-", "lift units"),
                          V("T", "T", J(RES, f"{C0}.sized.Tunit_N"), "N", "thrust per unit in hover"), rho(),
                          V("A", "A", J(RES, f"{C0}.sized.A"), "m²", "disc area per rotor (17 in)"),
                          V("k", "k_{ctrl}", J(RES, f"{C0}.params.kCtrl"), "-", "control margin factor (assumed)"),
                          V("FMeta", r"FM\,\eta", J(RES, f"{C0}.sized.FMeta"), "-", "figure of merit x drive efficiency, from the maker's thrust table", src_id="SRC-01")],
                    steps=[S(r"P_{ideal} = \frac{T^{3/2}}{\sqrt{2\rho A}}", "T**1.5/math.sqrt(2*rho*A)", "Pi", "W", "ideal induced power per rotor"),
                           S(r"P_{hover} = \frac{n\,P_{ideal}\,k_{ctrl}}{FM\,\eta}", "n*Pi*k/FMeta", "P", "W", "electrical hover power")], result="P", tol=0.5)

P["AERO-17"] = dict(vars=[V("P", "P_{hover}", J(RES, f"{C0}.sized.P_hover"), "W", "hover power", up="AERO-16"),
                          V("Vp", "V_{pack}", J(RES, f"{C0}.params.Vpack"), "V", "pack nominal voltage (6S)", src_id="SRC-04")],
                    steps=[S(r"I = \frac{P_{hover}}{V_{pack}}", "P/Vp", "I", "A", "hover current at nominal voltage")], result="I", tol=0.5)

P["AERO-18"] = dict(vars=[V("n", "n", J(RES, f"{C0}.sized.nUnits"), "-", "lift units"),
                          V("Tmax", r"T_{\max}", J(RES, f"{C0}.params.Tmax_g"), "kg", "maximum static thrust per unit (maker table, 3130 g)", src_id="SRC-01", scale=1e-3),
                          V("m", "m", J(RES, f"{C0}.sized.m"), "kg", "MTOW", up="AERO-22")],
                    steps=[S(r"T/W = \frac{n\,T_{\max}}{m}", "n*Tmax/m", "TW", "-", "hover thrust-to-weight at full throttle")], result="TW", tol=0.5)

P["AERO-19"] = dict(vars=[V("Ph", "P_{hover}", J(RES, f"{C0}.sized.P_hover"), "W", "hover power", up="AERO-16"),
                          V("Pc", "P_{cruise}", J(RES, f"{C0}.sized.P_cruise"), "W", "cruise power", up="AERO-14"),
                          V("Vl", "V_{loaded}", K(21.0, "pack voltage under hover load, 3.5 V per cell (analysis/sizing.mjs)"), "V", "loaded pack voltage")],
                    steps=[S(r"P_{trans} = P_{hover} + 2P_{cruise}", "Ph+2*Pc", "Pt", "W", "transition power (sizing assumption)"),
                           S(r"I = P_{trans}/V_{loaded}", "Pt/Vl", "I", "A", "transition current")], result="I", tol=0.5)

P["AERO-20"] = dict(vars=[V("E", "E_{pack}", J(RES, f"{C0}.sized.Epack_Wh"), "Wh", "pack energy", up="AERO-21"),
                          V("r", "r", J(RES, f"{C0}.params.reserve"), "-", "reserve fraction"),
                          V("eb", r"\eta_b", J(RES, f"{C0}.params.etaBatt"), "-", "battery discharge efficiency (assumed)"),
                          V("Ph", "P_h", J(RES, f"{C0}.sized.P_hover"), "W", "hover power", up="AERO-16"),
                          V("th", "t_h", J(RES, f"{C0}.params.tHover"), "s", "hover time per flight"),
                          V("tt", "t_t", J(RES, f"{C0}.params.tTrans"), "s", "transition time per flight"),
                          V("Pc", "P_c", J(RES, f"{C0}.sized.P_cruise"), "W", "cruise power", up="AERO-14")],
                    steps=[S(r"t_c = \frac{3600\,E_{pack}(1-r)\eta_b - P_h (t_h + t_t)}{P_c}", "(3600*E*(1-r)*eb - Ph*(th+tt))/Pc/60", "t", "min", "cruise time available")],
                    result="t", tol=0.5)

P["AERO-21"] = dict(vars=[V("C", "C", K(6.5, "Ovonic 6S 6500 mAh listing (docs/research/budget-energy-test.md:49)", "SRC-04"), "Ah", "pack capacity"),
                          V("Vp", "V", J(RES, f"{C0}.params.Vpack"), "V", "nominal voltage", src_id="SRC-04")],
                    steps=[S("E = C\\,V", "C*Vp", "E", "Wh", "pack energy")], result="E", tol=0.5)

P["AERO-22"] = dict(vars=[V("items", r"m_i", J(RES, f"{C0}.cg.items"), "kg", "mass items of the roll-up (13 rows: lift units, booms, wing, tail, battery, ...)")],
                    steps=[S(r"m = \sum_i m_i", "sum(i['m'] for i in items)", "m", "kg", "MTOW, sum of the items")], result="m", tol=0.5)

P["AERO-23"] = dict(vars=[V("tc", "t/c", J(RES, f"{C0}.params.tc"), "-", "thickness ratio"),
                          V("c", "c", J(RES, f"{C0}.sized.chord"), "m", "chord"),
                          V("b", "b", J(RES, f"{C0}.params.span"), "m", "span"),
                          V("rf", r"\rho_{foam}", J(RES, f"{C0}.params.rhoFoam"), "kg/m³", "XPS foam density (2 lb/ft³)", src_id="SRC-15"),
                          V("wg", "w", J(RES, f"{C0}.params.wGlass"), "kg/m²", "skin areal mass"),
                          V("S", "S", J(RES, f"{C0}.sized.S"), "m²", "wing area", up="AERO-08"),
                          V("ms", "m_{spar}", J(RES, f"{C0}.params.m_spar"), "kg", "spar and joiner mass"),
                          V("mh", "m_{hw}", J(RES, f"{C0}.params.mWingHardware"), "kg",
                            "printed wing hardpoints, pillar, tongue, stops, saddle plates (analysis/mass/mass_budget.json calibration; added to m_wing in analysis/model.js)")],
                    steps=[S(r"m_{wing} = 0.685\,(t/c)\,c^2 b\,\rho_{foam} + 2wS + m_{spar} + m_{hw}", "0.685*tc*c**2*b*rf + 2*wg*S + ms + mh", "mw", "kg",
                             "foam core (0.685 = NACA 4-digit area / (t c)) + skins + spar + printed hardware")], result="mw", tol=1.0)

P["AERO-26"] = dict(vars=[V("hn", "h_n", J(AER, "neutral_point.AVL_pod_pct_MAC"), "%MAC", "neutral point (AVL, with pod)", up="AERO-25"),
                          V("hcg", "h_{cg}", J(RES, f"{C0}.cg.pct.target"), "%MAC", "CG target")],
                    steps=[S("SM = h_n - h_{cg}", "hn-hcg", "SM", "%MAC", "static margin")], result="SM", tol=0.5)

P["AERO-27"] = dict(vars=[V("Sh", "S_h", J(RES, f"{C0}.geo.Sh"), "m²", "horizontal tail area"), V("lh", "l_h", J(RES, f"{C0}.geo.lh"), "m", "tail arm"),
                          V("S", "S", J(RES, f"{C0}.sized.S"), "m²", "wing area", up="AERO-08"), V("c", "c", J(RES, f"{C0}.sized.chord"), "m", "chord")],
                    steps=[S(r"V_h = \frac{S_h l_h}{S c}", "Sh*lh/(S*c)", "Vh", "-", "horizontal tail volume coefficient")], result="Vh", tol=0.5)

P["AERO-29"] = dict(vars=[V("CD0", "C_{D0}", J(RES, f"{C0}.sized.CD0"), "-", "zero-lift drag", up="AERO-12"),
                          V("e", "e", J(RES, f"{C0}.params.e"), "-", "Oswald efficiency", up="AERO-11"),
                          V("AR", "AR", J(RES, f"{C0}.sized.AR"), "-", "aspect ratio"),
                          V("W", "W", J(RES, f"{C0}.sized.W"), "N", "weight", up="AERO-22", upk=1/9.80665), rho(),
                          V("S", "S", J(RES, f"{C0}.sized.S"), "m²", "wing area", up="AERO-08")],
                    steps=[S(r"C_L^* = \sqrt{\pi e AR\,C_{D0}}", "math.sqrt(math.pi*e*AR*CD0)", "CLs", "-", "CL for maximum L/D"),
                           S(r"V^* = \sqrt{\frac{2W}{\rho S C_L^*}}", "math.sqrt(2*W/(rho*S*CLs))", "Vs", "m/s", "speed for maximum L/D")], result="Vs", tol=0.5)

# ---- structures and heat (SOLIDWORKS study inputs from cad/params.txt; results from cad/sim/results.txt) ----
E_ = lambda: V("E", "E", KV(PAR, "matE"), "Pa", "Young's modulus, 6061-T6", src_id="SRC-09")
P["STR-01"] = dict(vars=[V("P", "P", KV(PAR, "feaTipForce"), "N", "maximum thrust of one lift unit (maker 3.13 kgf, results.json struct.Tmax)"),
                         V("L", "L", KV(PAR, "feaBoomL"), "m", "boom cantilever length"),
                         V("D", "D", KV(PAR, "boomOD"), "m", "boom OD (1.000 in)"), V("d", "d", KV(PAR, "boomID"), "m", "boom ID")],
                   steps=[S(r"I = \frac{\pi}{64}(D^4 - d^4)", "math.pi/64*(D**4-d**4)", "I", "m⁴", "second moment of area"),
                          S(r"\sigma = \frac{P L\,(D/2)}{I}", "P*L*(D/2)/I/1e6", "sig", "MPa", "root bending stress, beam theory")],
                   result="sig", tol=0.5, note="Beam theory at the clamp; the claim value is this beam stress (the FEA peak at the fixed face is a singularity, STR-02).")

P["STR-03"] = dict(vars=[V("P", "P", KV(PAR, "feaTipForce"), "N", "maximum thrust of one lift unit"), V("L", "L", KV(PAR, "feaBoomL"), "m", "boom length"),
                         V("D", "D", KV(PAR, "boomOD"), "m", "boom OD"), V("d", "d", KV(PAR, "boomID"), "m", "boom ID"), E_()],
                   steps=[S(r"I = \frac{\pi}{64}(D^4 - d^4)", "math.pi/64*(D**4-d**4)", "I", "m⁴", ""),
                          S(r"\delta = \frac{P L^3}{3EI}", "P*L**3/(3*E*I)*1e3", "delta", "mm", "tip deflection, cantilever")], result="delta", tol=10.0,
                   note="Full-length cantilever; the FEA clamps over the block, so it is a little stiffer.")

P["STR-04"] = dict(vars=[V("mt", "m_{tip}", KV(PAR, "feaTipMass"), "kg", "lift-unit mass at the tip", up="STR-05"),
                         V("L", "L", KV(PAR, "feaBoomL"), "m", "boom length"), V("D", "D", KV(PAR, "boomOD"), "m", "OD"), V("d", "d", KV(PAR, "boomID"), "m", "ID"),
                         E_(), V("rm", r"\rho_{Al}", KV(PAR, "matRho"), "kg/m³", "6061 density", src_id="SRC-09")],
                   steps=[S(r"I = \frac{\pi}{64}(D^4 - d^4)", "math.pi/64*(D**4-d**4)", "I", "m⁴", ""),
                          S(r"m_b = \rho_{Al}\frac{\pi}{4}(D^2 - d^2)L", "rm*math.pi/4*(D**2-d**2)*L", "mb", "kg", "boom mass"),
                          S(r"f_1 = \frac{1}{2\pi}\sqrt{\frac{3EI}{(m_{tip} + 0.24\,m_b)L^3}}", "math.sqrt(3*E*I/((mt+0.24*mb)*L**3))/(2*math.pi)", "f", "Hz",
                            "first bending mode, cantilever with tip mass (Rayleigh)")], result="f", tol=10.0)

P["STR-05"] = dict(vars=[V("mo", "m_{motor}", J(RES, f"{C0}.params.mMotor"), "kg", "lift motor", src_id="SRC-01"),
                         V("me", "m_{ESC}", J(RES, f"{C0}.params.mEsc"), "kg", "ESC (estimate)"),
                         V("mp", "m_{prop}", J(RES, f"{C0}.params.mProp"), "kg", "lift propeller"),
                         V("mm", "m_{mount}", J("analysis/mass/mass_budget.json", "calibration.mMount"), "kg", "motor mount halves + prop plate, from the CAD (mass_budget.py calibration)")],
                   steps=[S(r"m_{unit} = m_{motor} + m_{ESC} + m_{prop} + m_{mount}", "mo+me+mp+mm", "mu", "kg", "lift-unit (boom tip) mass")],
                   result="mu", tol=0.5, note="Sizing roll-up; the independent CAD part roll-up (check_struct.py STR-05) agrees within 1.5 %.")

STRUCT_CHK = "analysis/validation/checks_struct.json"
P["STR-06"] = dict(vars=[V("m", "m", KV(PAR, "mtow"), "kg", "MTOW in cad/params.txt", up="AERO-22"), g0(),
                         V("n", "n_{ult}", KV(PAR, "feaNult"), "-", "ultimate load factor (3 x 1.5, team-set estimate)"),
                         V("yb", r"\bar{y}", J(STRUCT_CHK, "checks.STR-06.ybar_avl_m"), "m",
                           "spanwise centre of lift from the AVL strip loads (analysis/aero/out/avl/fs_pod_trim.txt, integrated by check_struct.py)")],
                   steps=[S(r"L_{half} = \frac{m g\, n_{ult}}{2}", "m*g*n/2", "Lh", "N", "lift on one wing"),
                          S(r"M_{root} = L_{half}\,\bar{y}", "Lh*yb", "M", "N·m", "root moment, AVL span loading")], result="M", tol=0.5,
                   note="The sizing uses elliptic lift (centre of lift 4 (b/2) / 3 pi = 0.509 m); the AVL centre of lift is 7 % further out.")

P["STR-07"] = dict(vars=[V("M", "M", J(STRUCT_CHK, "checks.STR-06.M_avl_Nm"), "N·m", "root moment at ultimate, AVL span loading", up="STR-06"),
                         V("D", "D", KV(PAR, "joinOD"), "m", "joiner OD (0.875 in)"), V("d", "d", KV(PAR, "joinID"), "m", "joiner ID")],
                   steps=[S(r"I = \frac{\pi}{64}(D^4 - d^4)", "math.pi/64*(D**4-d**4)", "I", "m⁴", ""),
                          S(r"\sigma = \frac{M (D/2)}{I}", "M*(D/2)/I/1e6", "sig", "MPa", "joiner bending stress at the centreline")], result="sig", tol=0.5)

P["THM-01"] = dict(vars=[V("Ta", "T_{amb}", J("analysis/thermal/thermal_inputs.json", "ambient.hot_C"), "°C", "design ambient 25 °C (DESIGN-BASIS R21)"), V("Q", "Q", KV(PAR, "thermQ"), "W", "heat into the motor", up="THM-03"),
                         V("h", "h", KV(PAR, "thermH"), "W/m²K", "convection coefficient (estimate)", up="THM-02"),
                         V("D", "D", KV(PAR, "motorD"), "m", "motor diameter"), V("H", "H", KV(PAR, "motorH"), "m", "motor height")],
                   steps=[S(r"A = \pi D H + 2\frac{\pi D^2}{4}", "math.pi*D*H + 2*math.pi*D**2/4", "A", "m²", "motor outer area"),
                          S(r"T = T_{amb} + \frac{Q}{hA}", "Ta + Q/(h*A)", "T", "°C", "steady temperature, lumped")], result="T", tol=2.0)

P["THM-03"] = dict(vars=[V("Pin", "P_{in}", J(RES, f"{C0}.sized.P_hover_per_motor"), "W", "electrical power per lift motor in hover (P_hover / 4, analysis/results.json)")],
                   steps=[S(r"Q = 0.2\,P_{in}", "0.2*Pin", "Q", "W", "heat at 80 % motor efficiency (estimate)")], result="Q", tol=0.5)

P["MFG-05"] = dict(vars=[V("ID", "ID_{socket}", KV(PAR, "sparID"), "mm", "spar socket ID", scale=1e3), V("OD", "OD_{joiner}", KV(PAR, "joinOD"), "mm", "joiner OD", scale=1e3)],
                   steps=[S("c = ID_{socket} - OD_{joiner}", "ID-OD", "c", "mm", "nominal diametral clearance")], result="c", tol=1.0)

P["CFD-09"] = dict(vars=[V("V", "V", J(CFD, "conditions.V_mps"), "m/s", "free-stream speed"), V("c", "c", J(CFD, "conditions.c_ref_m"), "m", "reference chord"),
                         V("mu", r"\mu", K(1.81e-5, "dynamic viscosity of air at 15 °C (ISA)", "SRC-19"), "Pa·s", ""), rho()],
                   steps=[S(r"Re = \frac{\rho V c}{\mu}", "rho*V*c/mu", "Re", "-", "Reynolds number the inviscid run does not model")], result="Re", tol=0.5)

# AERO-01 helper: the KV call above only guards that params.txt exists; V reads Vc from results.json
P["AERO-01"]["vars"][1] = V("V", "V", J(RES, f"{C0}.params.Vc"), "m/s", "cruise speed")


# ---------- evaluate ----------
def evaluate(cid, spec):
    ns = {"math": math}
    vars_ = {}
    for v in spec["vars"]:
        ns[v["sym"]] = v["value"]
        if isinstance(v["value"], (int, float)):
            vars_[v["sym"]] = v["value"]
    ns["_vars"] = vars_
    steps = []
    for s in spec["steps"]:
        val = eval(s["expr"], {"__builtins__": {"sum": sum}}, ns)   # expressions are the fixed strings above
        ns[s["out"]] = val
        steps.append({**s, "value": val})
    c = CLAIMS[cid]; got = ns[spec["result"]]; want = c.get("value")
    rel = spec.get("rel", "eq"); tol = spec.get("tol", 0.5)
    if want is None or not isinstance(want, (int, float)):
        delta, ok = None, None
    else:
        delta = 100.0 * (got - want) / abs(want) if want else None
        ok = (abs(delta) <= tol) if rel == "eq" else (got >= want if rel == "ge" else got <= want)
    # link check: a variable taken from another claim should carry that claim's number
    for v in spec["vars"]:
        up = v.get("from_claim")
        if up and up in CLAIMS and isinstance(CLAIMS[up].get("value"), (int, float)) and isinstance(v["value"], (int, float)):
            uv = CLAIMS[up]["value"]; nu = lambda u: (u or "").replace("²", "2").replace("³", "3").replace("^", "").replace(" ", "").replace("·", "")
            k = v.get("link_factor"); same_units = bool(k) or nu(CLAIMS[up].get("units")) == nu(v["unit"])
            d = 100.0 * (v["value"] * (k or 1) - uv) / abs(uv) if uv else None
            v["link"] = {"claim_value": uv, "claim_units": CLAIMS[up].get("units"), "delta_pct": d,
                         "state": "consistent" if (d is not None and abs(d) <= 1.0) else ("units differ" if not same_units else "stale")}
    return {"kind": "computed", "vars": spec["vars"], "steps": steps, "result": {"symbol": spec["result"], "value": got, "unit": spec["steps"][-1]["unit"],
            "claim_value": want, "claim_units": c.get("units"), "delta_pct": delta, "tol_pct": tol, "relation": rel, "reproduced": ok}, "note": spec.get("note", "")}


def main():
    out = {"generated": time.strftime("%Y-%m-%d %H:%M"), "script": "analysis/validation/proofs.py",
           "rules": "Inputs are read from the cited files at run time; constants name their source; links to other claims are value-checked.",
           "claims": {}, "sources": {s["id"]: {k: s[k] for k in ("title", "kind", "url", "status", "checked", "note", "values") if k in s} for s in AUD["sources"]}}
    for cid, c in CLAIMS.items():
        if cid in P:
            pr = evaluate(cid, P[cid])
        else:
            pr = {"kind": "evidence", "note": "No closed-form arithmetic to re-run: the evidence files and the independent check below are the proof."}
        pr["equations"] = c.get("equations", [])
        pr["evidence"] = c.get("evidence", [])
        pr["check"] = c.get("independent_check")
        pr["external"] = AUD.get("claim_sources", {}).get(cid, [])
        ups = sorted({v["from_claim"] for v in pr.get("vars", []) if v.get("from_claim")})
        pr["upstream"] = ups
        out["claims"][cid] = pr
    # downstream links and a node/edge graph for the page
    for cid, pr in out["claims"].items():
        pr["downstream"] = sorted(k for k, q in out["claims"].items() if cid in q["upstream"])
    lcf = VAL / "link_check.json"
    if lcf.exists():   # liveness of every URL in the docs (link_check.py)
        lc = json.loads(lcf.read_text(encoding="utf-8")); cn = lc.get("counts", {})
        out["link_check"] = {"n": lc.get("n"), "ok": cn.get("ok", 0), "dead": cn.get("dead", 0), "blocked": cn.get("blocked", 0),
                             "other": sum(v for k, v in cn.items() if k not in ("ok", "dead", "blocked")), "generated": lc.get("generated"),
                             "dead_urls": [l["url"] for l in lc.get("links", []) if l.get("status") == "dead" or (l.get("status_code") in (404, 410))][:20]}
    # typeset form of each plain-text equation (equations_tex.json, keyed by the exact text); the page falls back to the text
    eqt = json.loads((VAL / "equations_tex.json").read_text(encoding="utf-8"))["equations"]
    used = {e for p in out["claims"].values() for e in p["equations"]}
    out["equation_tex"] = {e: eqt[e] for e in sorted(used) if e in eqt}
    for e in sorted(used - set(eqt)):
        print(f"no typeset form in equations_tex.json: {e!r}")
    comp = [p for p in out["claims"].values() if p["kind"] == "computed"]
    links = [v["link"] for p in comp for v in p["vars"] if "link" in v]
    out["summary"] = {"claims": len(out["claims"]), "computed": len(comp), "evidence_only": len(out["claims"]) - len(comp),
                      "reproduced": sum(1 for p in comp if p["result"]["reproduced"] is True), "not_reproduced": sum(1 for p in comp if p["result"]["reproduced"] is False),
                      "links": len(links), "links_consistent": sum(1 for l in links if l["state"] == "consistent"), "links_stale": sum(1 for l in links if l["state"] == "stale"),
                      "with_external_source": sum(1 for p in out["claims"].values() if p["external"])}
    (VAL / "proofs.json").write_text(json.dumps(out, indent=1, default=float), encoding="utf-8", newline="\n")
    print(json.dumps(out["summary"], indent=1))
    for cid, p in out["claims"].items():
        if p["kind"] == "computed":
            r = p["result"]; flag = {True: "ok ", False: "OFF", None: " - "}[r["reproduced"]]
            stale = [f"{v['sym']}<-{v['from_claim']} {v['link']['delta_pct']:+.2f}%" for v in p["vars"] if v.get("link", {}).get("state") == "stale"]
            print(f"{flag} {cid:8s} {r['value']:.6g} vs {r['claim_value']} ({'—' if r['delta_pct'] is None else f'{r[chr(100)+chr(101)+chr(108)+chr(116)+chr(97)+chr(95)+chr(112)+chr(99)+chr(116)]:+.2f}%'})  {' '.join(stale)}")


if __name__ == "__main__":
    main()
