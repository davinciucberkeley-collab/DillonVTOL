"""Bottom-up mass budget of the aircraft from the CAD model, the print settings and the bought parts, compared with the
sizing roll-up (analysis/results.json C0 cg.items). This is the reconciliation the audit asked for (STR-05, MFG-12).

Basis per item (every row records which one it uses):
  printed   docs/build/print-list.csv mass_g_est_each (CAD volume x material density x fill factor from the print settings
            in docs/build/BUILD-MANUAL.md §2); PA6-CF corrected from the 1.23 g/cm3 the CAD used to the TDS 1.17 g/cm3
            (Polymaker Fiberon PA6-CF20 TDS v1.1, source audit SRC-07)
  tube      cad/verification.txt volume x 2700 kg/m3 (6061, SRC-09)
  foam      cad/verification.txt volume x 32 kg/m3 (XPS 2 lb/ft3, SRC-15)
  vendor    the fixed vendor mass cad/verification.txt uses (with its source)
  hardware  cad/verification.txt fastener / insert volume x density (EST densities: steel 7.9, brass 8.5 g/cm3)
  est       not in the CAD; value and reason given in the row (EST)

Run:  py analysis/mass/mass_budget.py      -> analysis/mass/mass_budget.json (+ a table on stdout)
"""
import csv, json, re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent / "mass_budget.json"
RHO_PA6_TDS, RHO_PA6_CAD = 1.17, 1.23

# CAD part -> sizing group (analysis/sizing.mjs cg items)
GROUP = {
    "Lift units": ["Motor_Mount_Upper", "Motor_Mount_Cap", "Lift_Motor", "Lift_Prop", "Prop_Plate"],
    "Booms + clamps": ["Boom_Front", "Boom_Rear_Stub", "Splice_Plug", "Boom_Clamp_F_Upper", "Boom_Clamp_F_Lower", "Boom_Clamp_R_Upper", "Boom_Clamp_R_Lower"],
    "Wing": ["Wing_Panel_L", "Wing_Panel_R", "Aileron_L", "Aileron_R", "Wing_Saddle", "Spar_Tube", "Wing_Joiner", "Joiner_Stop", "Spar_Collar",
             "Rear_Hardpoint", "Bolt_Pillar", "Root_Tongue", "Horn_Hardpoint"],
    "Tail": ["H_Tail", "Elevator", "Fin", "Rudder", "Fin_Shoe", "Tail_Clamp_Upper", "Tail_Clamp_Cap", "Crush_Sleeve"],
    "Fuselage pod": ["Fuselage_Pod", "Canopy", "Battery_Tray", "FC_Tray", "Pitot_Tube", "Pitot_Clamp"],
    "Landing gear": ["Landing_Leg", "Gear_Clamp_Upper", "Gear_Clamp_Lower", "Gear_Fairing"],
    "Avionics": ["Flight_Controller"],
    "Pusher set": ["Pusher_Motor", "Pusher_Prop_14in", "Pusher_Cup", "Pusher_Adapter", "Prop_Washer", "N04_M6_Bullet_Nut"],
    "Servos (5)": ["Servo", "Servo_Tray", "Control_Horn", "Horn_Backplate", "Pushrod_Aileron", "Pushrod_Elevator", "Pushrod_Rudder"],
    "Battery (placed for CG)": ["Battery_6S_LiPo"],
}
SIZING_NAME = {"Lift units": ["Lift units, front", "Lift units, rear"], "Wing": ["Wing (foam/glass + spar)"]}
HARDWARE = re.compile(r"^(F\d\d|N\d\d|W\d\d|I\d\d)_")


def read_cad():
    rows = {}
    for line in (ROOT / "cad/verification.txt").read_text(encoding="utf-8").splitlines():
        m = re.match(r"^(\S+)\s*\|\s*(\d+)\s*\|\s*([\d.]+)\s*\|\s*([\d.]+)\s*\|\s*(.+)$", line)
        if m:
            rows[m.group(1)] = {"qty": int(m.group(2)), "each_g": float(m.group(3)), "total_g": float(m.group(4)), "basis": m.group(5).strip()}
    return rows


def read_print():
    out = {}
    for r in csv.DictReader(open(ROOT / "docs/build/print-list.csv", encoding="utf-8")):
        parts = [p.strip() for p in r["cad_part"].split("+")]
        m = re.match(r"([\d.]+)", r["mass_g_est_each"] or "")
        if not m:
            continue
        g = float(m.group(1)); is_set = "set" in (r["mass_g_est_each"] or "") or len(parts) > 1
        qty = int(re.match(r"\d+", r["qty"]).group()) if re.match(r"\d+", r["qty"] or "") else 1
        pa6 = "PA6" in r["material"]
        if pa6:
            g *= RHO_PA6_TDS / RHO_PA6_CAD
        out[r["id"]] = {"parts": parts, "g_each": g, "qty": qty, "set": is_set, "material": r["material"], "fill": f"{r['walls']} walls, {r['infill_pct']} % {r['infill_pattern']}"}
    return out


def stl_centroid(path):
    """volume centroid of a closed binary STL (signed tetrahedra from the origin); None if unreadable"""
    import numpy as np
    b = path.read_bytes()
    if len(b) < 84:
        return None
    n = int.from_bytes(b[80:84], "little")
    if 84 + 50 * n != len(b):
        return None
    rec = np.frombuffer(b, dtype=np.dtype([("n", "<3f4"), ("v", "<9f4"), ("a", "<u2")]), count=n, offset=84)
    v = rec["v"].reshape(-1, 3, 3).astype(float)
    vol = np.einsum("ij,ij->i", v[:, 0], np.cross(v[:, 1], v[:, 2])) / 6.0
    if abs(vol.sum()) < 1e-15:
        return None
    return (vol[:, None] * v.sum(1) / 4.0).sum(0) / vol.sum()


def cad_cg(rows):
    """CG of the CAD assembly: each instance at its comp= placement (origin + rotation rows, cad/params.built.txt = the params the current CAD was built from) with the part's
    mesh centroid (cad/mesh/*.STL, part frame, metres) and its bottom-up mass per instance. Frame: X forward from the wing LE."""
    import numpy as np
    mass_each = {r["part"]: r["mass_g"] / r["qty"] for r in rows if r["qty"]}
    cents, tot, mom, missing = {}, 0.0, np.zeros(3), []
    for l in (ROOT / "cad/params.built.txt").read_text(encoding="utf-8").splitlines():
        if not l.startswith("comp="):
            continue
        f = l[5:].split("|"); name = f[0].split("~")[0]
        if name not in mass_each:
            continue
        if name not in cents:
            p = ROOT / "cad/mesh" / f"{name}.STL"
            cents[name] = stl_centroid(p) if p.exists() else None
        c = cents[name]
        if c is None:
            missing.append(name); continue
        o = np.array([float(f[1]), float(f[2]), float(f[3])]); Rm = np.array([float(x) for x in f[4].split(",")]).reshape(3, 3)
        x = o + Rm.T @ c      # rows of the matrix are the images of the part axes
        m = mass_each[name] / 1000; tot += m; mom += m * x
    return tot, mom, sorted(set(missing))


def main():
    cad, prn = read_cad(), read_print()
    by_part = {}
    for pid, r in prn.items():
        if r["parts"][0].startswith("(") or r["parts"][0] in ("—", "—", ""):
            continue
        share = r["g_each"] / len(r["parts"]) if r["set"] else r["g_each"]
        for cp in r["parts"]:   # a set's mass is split by CAD volume between its halves
            by_part[cp] = {"pid": pid, "g_each": share, "fill": r["fill"], "material": r["material"]}
    if True:   # split clamp-set masses by the halves' CAD volumes instead of evenly
        for pid, r in prn.items():
            if r["set"] and len(r["parts"]) > 1 and all(p in cad for p in r["parts"]):
                v = [cad[p]["total_g"] / cad[p]["qty"] for p in r["parts"]]
                for p, vi in zip(r["parts"], v):
                    by_part[p]["g_each"] = r["g_each"] * vi / sum(v)
    items, rows = [], []
    for name, c in cad.items():
        b = c["basis"]
        if name in by_part:
            g = by_part[name]["g_each"] * c["qty"]; basis = f"printed ({by_part[name]['pid']}, {by_part[name]['fill']}, docs/build/print-list.csv)"
        elif name == "Landing_Leg":
            # the CAD leg body includes the printed dome foot revolved as aluminium (cad/BuildVtol.cs Leg()); weigh the tube alone
            # from its stock size and length (cad/params.txt legOD / legID / legLen); the PETG foot is the P23 row below
            pv = {k: float(v) for k, v in (l.split("=", 1) for l in (ROOT / "cad/params.built.txt").read_text(encoding="utf-8").splitlines() if l[:3] == "leg" and "=" in l and "|" not in l)}
            g = c["qty"] * 3.14159265 / 4 * (pv["legOD"] ** 2 - pv["legID"] ** 2) * pv["legLen"] * 2700 * 1000
            basis = "tube: pi/4 (OD^2 - ID^2) x legLen x 2700 kg/m3 from cad/params.txt (the CAD body wrongly includes the foot as aluminium)"
        elif "6061" in b:
            g = c["total_g"]; basis = "tube: CAD volume x 2700 kg/m3 (SRC-09)"
        elif "rhoFoam" in b:
            g = c["total_g"]; basis = "foam: CAD volume x 32 kg/m3 (SRC-15)"
        elif b.startswith("fixed"):
            g = c["total_g"]; basis = "vendor: " + b
        elif HARDWARE.match(name):
            g = c["total_g"]; basis = "hardware: " + b
        else:
            g = c["total_g"]; basis = "CAD solid (no print-list row): " + b
        grp = next((k for k, v in GROUP.items() if name in v), "Fasteners and inserts" if HARDWARE.match(name) else "Other")
        rows.append({"part": name, "qty": c["qty"], "mass_g": round(g, 2), "group": grp, "basis": basis})
    # not in the CAD (EST rows carry their reason)
    R = json.loads((ROOT / "analysis/results.json").read_text(encoding="utf-8"))["concepts"]["C0"]; P, S = R["params"], R["sized"]
    wet = 2 * (S["S"] + R["geo"]["Sh"] + R["geo"]["Sv"])        # wing + tail skins, both faces
    est = [("ESCs (4 lift + 1 pusher)", 5 * P["mEsc"] * 1000, "Lift units", "EST: 25 g each (analysis/sizing.mjs mEsc; maker mass not on the pages read)"),
           ("Skins: packing tape on wing and tail", P["wGlass"] * wet * 1000, "Wing", f"EST: {P['wGlass']} kg/m2 (sizing wGlass) x {wet:.3f} m2 (both faces of S + S_h + S_v)"),
           ("Pod frames, rails, canopy flange (P20, P22)", 65 + 9, "Fuselage pod", "printed EST (print-list P20 65 g, P22 9 g)"),
           ("Saddle root plates + side tabs (P13)", 2 * 35, "Wing", "printed EST (print-list P13 2 x 35 g; part of the Wing_Saddle body in the CAD)"),
           ("Dome feet (P23)", 4 * 6, "Landing gear", "printed EST (print-list P23 4 x 6 g)"),
           ("GPS pad, harness anchors (P24)", 3 * 7, "Avionics", "printed EST (print-list P24)"),
           ("Avionics not modelled (GPS, receiver, Remote ID, airspeed, telemetry)", (P["mAvionics"] - 0.040) * 1000, "Avionics", "EST: sizing mAvionics 0.25 kg minus the 40 g flight controller in the CAD"),
           ("Wiring", (P["mWiring"] + 4 * P["mWirePerLift"]) * 1000, "Wiring", "EST: sizing mWiring + 4 x mWirePerLift"),
           ("Payload allowance", P["mPayload"] * 1000, "Payload allowance (bay)", "requirement R12")]
    for n, g, grp, why in est:
        rows.append({"part": n, "qty": 1, "mass_g": round(g, 2), "group": grp, "basis": why})
    groups = {}
    for r in rows:
        groups[r["group"]] = groups.get(r["group"], 0) + r["mass_g"]
    sz = {i["name"]: i["m"] * 1000 for i in R["cg"]["items"]}
    cmp = []
    for g, v in sorted(groups.items(), key=lambda x: -x[1]):
        names = SIZING_NAME.get(g, [g]); s = sum(sz.get(n, 0) for n in names) if any(n in sz for n in names) else None
        cmp.append({"group": g, "bottom_up_g": round(v, 1), "sizing_g": None if s is None else round(s, 1), "delta_g": None if s is None else round(v - s, 1)})
    tot = sum(groups.values())
    # calibrated constants for analysis/sizing.mjs (kg): what the sizing model should carry for each item it does not derive from geometry
    pm = lambda *names: sum(r["mass_g"] for r in rows if r["part"] in names) / 1000
    PB = {l.split("=", 1)[0]: l.split("=", 1)[1] for l in (ROOT / "cad/params.built.txt").read_text(encoding="utf-8").splitlines() if "=" in l and not l.startswith("comp=")}   # the built CAD
    WING_PRINTED = ("Spar_Collar", "Rear_Hardpoint", "Bolt_Pillar", "Root_Tongue", "Horn_Hardpoint", "Joiner_Stop", "Saddle root plates + side tabs (P13)")
    # screws and inserts that sit at each lift unit (hardware-spec J01/J02): 4 x F01 motor screws, 6 x F02 mount-clamp screws, 4 x I01
    # inserts; moved from the fastener group to the lift unit so the boom-tip mass (FEA, modal) carries them
    each = {r["part"]: r["mass_g"] / r["qty"] for r in rows if r["qty"]}
    tip_hw = (4 * each.get("F01_M3x8_SHCS", 0) + 6 * each.get("F02_M3x16_SHCS", 0) + 4 * each.get("I01_M3_Insert", 0)) / 1000
    cal = {"mMount": round(pm("Motor_Mount_Upper", "Motor_Mount_Cap", "Prop_Plate") / 4 + tip_hw, 4),
           "boomClamp": round(pm("Splice_Plug", "Boom_Clamp_F_Upper", "Boom_Clamp_F_Lower", "Boom_Clamp_R_Upper", "Boom_Clamp_R_Lower") / 4, 4),
           "mFus": round(groups["Fuselage pod"] / 1000, 4), "mGear": round(groups["Landing gear"] / 1000, 4),
           "mAvionics": round(groups["Avionics"] / 1000, 4), "mPusherSet": round(groups["Pusher set"] / 1000, 4),
           "mServos": round(groups["Servos (5)"] / 1000, 4), "mWingHardware": round(pm(*WING_PRINTED), 4),
           "mFasteners": round(groups.get("Fasteners and inserts", 0) / 1000 - 4 * tip_hw, 4),
           "mTailHardware": round(pm("Fin_Shoe", "Tail_Clamp_Upper", "Tail_Clamp_Cap", "Crush_Sleeve"), 4),
           "sigmaTail": round(pm("H_Tail", "Elevator", "Fin", "Rudder") / (float(PB["hC"]) * float(PB["hSpan"]) + 2 * float(PB["vH"]) * float(PB["vC"])) + 2 * P["wGlass"], 4)}
    cal["_why"] = {"mMount": "motor mount upper + cap (PA6-CF, solid, TDS density) + steel prop plate, per lift unit",
                   "boomClamp": "splice plugs + front and rear boom clamp sets, per clamp position (2 per boom x 2 booms)",
                   "mFus": "pod foam, canopy, trays, pitot, printed frames (EST)", "mGear": "legs, gear clamps, fairings, dome feet",
                   "mAvionics": "flight controller (CAD) + other avionics (EST) + printed pads", "mPusherSet": "motor, prop, cup, adapter, washer, nut (ESC in mEsc)",
                   "mServos": "5 servos + trays + horns + pushrods", "mWingHardware": "printed wing hardpoints, pillar, tongue, stops, saddle plates",
                   "mFasteners": "every screw, nut, washer and heat-set insert in the CAD", "mTailHardware": "fin shoes, tail clamps, crush sleeves",
                   "sigmaTail": "kg/m2: CAD tail foam (stabiliser 9 mm, fins) over S_h + S_v, plus the two tape skins (2 x wGlass)"}
    # CG stations from the CAD placements (x forward from the wing LE), for the sizing's CG build-up. Pod contents are kept
    # relative to the pod nose (cad/params.txt podProfile noseX), wing-mounted items relative to the wing LE or the chord.
    import numpy as np
    me = {r["part"]: r["mass_g"] / r["qty"] for r in rows if r["qty"]}; grp = {r["part"]: r["group"] for r in rows}
    acc = {}
    for l in (ROOT / "cad/params.built.txt").read_text(encoding="utf-8").splitlines():
        if not l.startswith("comp="):
            continue
        f = l[5:].split("|"); n = f[0].split("~")[0]
        if n not in me:
            continue
        c = stl_centroid(ROOT / "cad/mesh" / f"{n}.STL")
        if c is None:
            continue
        x = (np.array([float(v) for v in f[1:4]]) + np.array([float(v) for v in f[4].split(",")]).reshape(3, 3).T @ c)[0]
        a = acc.setdefault(grp[n], [0.0, 0.0]); a[0] += me[n]; a[1] += me[n] * x
    gx = {g: a[1] / a[0] for g, a in acc.items()}
    pv = {l.split("=", 1)[0]: l.split("=", 1)[1] for l in (ROOT / "cad/params.built.txt").read_text(encoding="utf-8").splitlines() if "=" in l and not l.startswith("comp=")}
    nose0 = float(re.search(r"noseX=([\d.]+)", pv["podProfile"]).group(1)); chord0 = float(pv["chord"])
    cal["stations"] = {"cad_noseX": nose0, "cad_chord": chord0,
                       "pod_from_nose": round(nose0 - gx["Fuselage pod"], 4), "avionics_from_nose": round(nose0 - gx["Avionics"], 4),
                       # physical limit, not the current station: the CAD rev D layout put the pack front face 0.184 m behind the nose tip,
                       # where the nose taper still clears its 48 x 50 mm section at battY (pack centre 0.261 m behind the tip); same nose shape since
                       "battery_fwd_limit_from_nose": 0.261,
                       "fasteners_frac_chord": round(gx["Fasteners and inserts"] / chord0, 4), "wing_frac_chord": round(gx["Wing"] / chord0, 4),
                       "gear_frac_chord": round(gx["Landing gear"] / chord0, 4),
                       "_why": "group centroids of the CAD instances (mesh centroid at each comp= placement); the battery's forward limit is the CAD rev D battery station, the furthest forward the 6S pack is shown to fit in the nose taper"}
    out = {"script": "analysis/mass/mass_budget.py", "inputs": ["cad/verification.txt", "docs/build/print-list.csv", "analysis/results.json"], "calibration": cal,
           "total_kg": round(tot / 1000, 4), "sizing_mtow_kg": S["m"], "groups": cmp, "rows": rows,
           "est_share_kg": round(sum(r["mass_g"] for r in rows if r["basis"].startswith("EST") or "EST" in r["basis"][:12]) / 1000, 3),
           "note": "Printed masses are estimates until parts are weighed (test plan); everything else is CAD geometry x sourced density or a vendor mass."}
    OUT.write_text(json.dumps(out, indent=1), encoding="utf-8", newline="\n")
    print(f"{'group':34s} {'bottom-up g':>12s} {'sizing g':>10s} {'delta g':>9s}")
    for c in cmp:
        print(f"{c['group']:34s} {c['bottom_up_g']:12.1f} {('—' if c['sizing_g'] is None else f'{c[chr(115)+chr(105)+chr(122)+chr(105)+chr(110)+chr(103)+chr(95)+chr(103)]:.1f}'):>10s} {('—' if c['delta_g'] is None else f'{c[chr(100)+chr(101)+chr(108)+chr(116)+chr(97)+chr(95)+chr(103)]:+.1f}'):>9s}")
    print(f"TOTAL bottom-up {tot/1000:.3f} kg vs sizing MTOW {S['m']:.3f} kg ({(tot/1000 - S['m'])/S['m']*100:+.1f} %)")


if __name__ == "__main__":
    main()
