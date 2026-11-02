"""Vertical-landing loads on the gear and booms (STR-11), 2026-11-01.

Model (each of the four gear corners separately): the corner's share of the landing mass falls at the touchdown speed onto a
spring made of the boom cantilevered from its nearest wing clamp (k = 3 E I / a^3, a = clamp-to-gear distance along the boom,
clamp taken as rigid: this overstates stiffness, so it overstates force and stress) in series with the foot (rigid PETG dome:
no added compliance). Energy balance with gravity:  1/2 m v^2 + m g d = 1/2 k d^2  ->  d = (m g + sqrt((m g)^2 + k m v^2)) / k,
F = k d, boom bending at the clamp M = F a, sigma = M (D/2) / I. The leg tube itself is short and axially loaded.

Cases (speeds from the flight software, not chosen to pass):
  normal  touchdown at the ArduPilot final-descent speed the parameter file leaves at its default (Q_LAND_FINAL_SPD)
  hard    twice that speed (a 2x speed margin, EST: covers a late flare or a gust at touchdown; 4x the energy)
Pass: normal RF >= 1.5 on the 6061-T6 minimum yield, hard RF >= 1.0 (no yield).

Run:  py analysis/structures/landing.py    -> analysis/structures/landing.json
"""
import json, math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
G = 9.80665


def params():
    out, comps = {}, []
    for l in (ROOT / "cad/params.txt").read_text(encoding="utf-8").splitlines():
        if l.startswith("comp="):
            f = l[5:].split("|"); comps.append((f[0], float(f[1]), float(f[2]), float(f[3])))
        elif "=" in l and "|" not in l:
            k, v = l.split("=", 1)
            try:
                out[k] = float(v)
            except ValueError:
                pass
    return out, comps


def main():
    P, comps = params()
    R = json.loads((ROOT / "analysis/results.json").read_text(encoding="utf-8"))["concepts"]["C0"]
    prop = json.loads((ROOT / "analysis/propulsion_data_2026-11-01.json").read_text(encoding="utf-8"))
    src = next(x for x in prop["followup"]["sources"] if x["id"] == "F12")   # ArduPilot source, ArduPlane/quadplane.cpp defaults
    v_norm = src["values"]["Q_LAND_FINAL_SPD_default_mps"]
    land = {"param": "Q_LAND_FINAL_SPD", "default_mps": v_norm, "url": src["url"], "checked": src["checked"]}
    for l in (ROOT / "firmware/vtol_c0.param").read_text(encoding="utf-8").splitlines():   # the value the aircraft will fly with
        if l.startswith("Q_LAND_FINAL_SPD,"):
            v_norm = float(l.split(",")[1].split()[0]); land["set_in"] = "firmware/vtol_c0.param"; land["value_mps"] = v_norm
    land.setdefault("value_mps", v_norm)
    m = R["sized"]["m"]; xcg = R["cg"]["target"]
    E, D, d = P["matE"], P["boomOD"], P["boomID"]
    I = math.pi / 64 * (D ** 4 - d ** 4)
    yld_min = 240e6   # 6061-T6 minimum yield (source audit SRC-09: Wikipedia 6061 aluminium alloy, 240 MPa minimum, 2026-11-01)
    gears = sorted({c[1] for c in comps if c[0] == "Gear_Clamp_Upper"})
    clamps = {"front": next(c[1] for c in comps if c[0] == "Boom_Clamp_F_Upper"), "rear": next(c[1] for c in comps if c[0] == "Boom_Clamp_R_Upper")}
    xf, xr = max(gears), min(gears)
    share = {"front": (xcg - xr) / (xf - xr) / 2, "rear": (xf - xcg) / (xf - xr) / 2}   # per corner, static moment balance
    out = {"script": "analysis/structures/landing.py", "inputs": {"mtow_kg": m, "x_cg_m": xcg, "E_Pa": E, "boom_OD_m": D, "boom_ID_m": d, "I_m4": I,
           "yield_min_Pa": yld_min, "land_speed": land}, "corners": {}}
    for side, xg in (("front", xf), ("rear", xr)):
        a = abs(xg - clamps[side]); k = 3 * E * I / a ** 3; mi = m * share[side]
        out["corners"][side] = {"gear_x_m": xg, "clamp_x_m": clamps[side], "arm_m": a, "k_N_per_m": k, "mass_share_kg": mi, "cases": {}}
        for case, v in (("normal", v_norm), ("hard", 2 * v_norm)):
            dd = (mi * G + math.sqrt((mi * G) ** 2 + k * mi * v ** 2)) / k
            F = k * dd; M = F * a; s = M * (D / 2) / I
            out["corners"][side]["cases"][case] = {"v_mps": v, "deflection_mm": dd * 1e3, "force_N": F, "load_factor_g": F / (mi * G),
                                                   "moment_Nm": M, "stress_MPa": s / 1e6, "RF_yield_min": yld_min / s,
                                                   "pass": yld_min / s >= (1.5 if case == "normal" else 1.0)}
    (ROOT / "analysis/structures").mkdir(exist_ok=True)
    (ROOT / "analysis/structures/landing.json").write_text(json.dumps(out, indent=1), encoding="utf-8", newline="\n")
    for side, c in out["corners"].items():
        for case, r in c["cases"].items():
            print(f"{side:5s} {case:6s} v {r['v_mps']:.2f} m/s  d {r['deflection_mm']:.1f} mm  F {r['force_N']:.0f} N  n {r['load_factor_g']:.1f} g  sigma {r['stress_MPa']:.0f} MPa  RF {r['RF_yield_min']:.2f}  {'pass' if r['pass'] else 'FAIL'}")


if __name__ == "__main__":
    main()
