"""Benchmark dataset: C0 against published small VTOL aircraft (web research, checked 2026-10-26).
Every row carries its source URL; derived columns (wing and disk loading, Wh/kg, W*V/P) are computed here.
Usage: python analysis/benchmarks/build_bench.py [out.csv]   (default analysis/benchmarks/aircraft.csv)
"""
import csv, math, sys
D = "2026-10-26"
g = 9.81
import os
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), "aircraft.csv")

def fmt(x, nd=1):
    if x is None: return "—"
    if isinstance(x, tuple):
        a, b = x
        return f"{a:.{nd}f}–{b:.{nd}f}" if abs(a-b) > 1e-9 else f"{a:.{nd}f}"
    if isinstance(x, str): return x
    return f"{x:.{nd}f}" if nd is not None else str(x)

def rng(f, *args):
    """apply f over args that may be tuples -> (min,max) or scalar"""
    if any(a is None for a in args): return None
    import itertools
    opts = [a if isinstance(a, tuple) else (a,) for a in args]
    vals = [f(*c) for c in itertools.product(*opts)]
    return (min(vals), max(vals)) if len(set(round(v, 6) for v in vals)) > 1 else vals[0]

def disk(m, n, d_in):
    return rng(lambda m, n, d: m*g/(n*math.pi*(d*0.0254/2)**2), m, n, d_in)

rows = []
def add(**k): rows.append(k)

# ---------------- reference ----------------
add(name="C0 (this project; design, not built)", cfg="Lift+cruise quadplane (4 lift + 1 pusher)",
    url="caller brief (repo analysis)", mtow=6.55, empty=None, payload=0.5, span=2.40, area=0.682, length=None,
    vc=20, vmax=None, vs=11.75, endur=12.7, endur_c="mission 120 s hover + 600 s cruise + 40 s transition, 20% reserve (design)",
    range_km=None, batt="2x 6S 6500 mAh LiPo", wh=144, bmass=0.82, nlift=4, prop=17, lmotor="—", cmotor="—",
    hover="—", price="$2,000 total budget cap", WVP=6.55*g*20/338,
    notes="Reference row. Predicted L/D 7.46, CD0 0.0445 (clean 0.0266), cruise 338 W, hover 916 W (FM 0.52 assumed). Empty mass not given; MTOW-battery-payload = 5.23 kg (derived). W*V/P from 338 W cruise.")

# ---------------- lift + cruise ----------------
add(name="DeltaQuad Evo", cfg="Lift+cruise quadplane (flying wing, 4 lift + pusher)",
    url="https://docs.deltaquad.com/evo/vehicle-specifications", mtow=10, empty=4.8, payload=(1, 3), span=2.69, area=0.84, length=0.75,
    vc=16.54, vmax=None, vs=None, endur=272, endur_c="dual battery, 90% battery use, low wind, sea level, low-altitude VTOL (manufacturer)",
    range_km=270, batt="2x 6S 22 Ah semi-solid-state Li-ion (Wh not published)", wh=2*6*3.7*22, bmass=4.0, nlift=4, prop=None,
    lmotor="—", cmotor="—", hover="—", price="—",
    WVP=(10-0)*g*16.54/(0.9*2*6*3.7*22/(272/60)),
    notes="Payload 3 kg single battery, 1 kg dual. Empty incl. 1 battery 6.8 kg -> battery ~2.0 kg each (derived). Wh assumes 3.7 V/cell nominal (estimate). W*V/P uses MTOW 10 kg, 90% of est. 977 Wh over 272 min; marketing best case. Tolerances 'provisional'.")

add(name="DeltaQuad Pro #CARGO", cfg="Lift+cruise quadplane (flying wing, 4 lift + pusher)",
    url="https://www.deltaquad.com/cargo (official page in search index; returned 404 on direct fetch 2026-10-26)", mtow=6.2, empty=None, payload=1.2,
    span=2.35, area=0.90, length=0.90, vc=None, vmax=None, vs=None, endur=(110, 165),
    endur_c="2+ h no payload; 1 h 50 at 1 kg payload; 2 h 45 with auxiliary LiPo and 400 g payload (manufacturer)",
    range_km=150, batt="—", wh=None, bmass=None, nlift=4, prop=None, lmotor="—", cmotor="—", hover="—", price="—", WVP=None,
    notes="Discontinued predecessor of Evo. Range 150 km from 2017 launch article (unmannedsystemstechnology.com, 403 on fetch). Values via search-index snippet of official page: medium confidence.")

add(name="Foxtech Baby Shark 260 VTOL", cfg="Lift+cruise quadplane (4 lift + pusher)",
    url="https://www.suasnews.com/2019/01/foxtech-baby-shark-260-vtol/", mtow=12, empty=5.5, payload=6.5, span=2.5, area=None, length=None,
    vc=None, vmax=100/3.6, vs=(15, 16), endur=150, endur_c="'Max flight time 2.5 hours', no conditions (manufacturer); a used-unit seller on discuss.ardupilot.org reports max ~30 min flown",
    range_km=None, batt="suggested 2x 6S 5000 mAh LiPo (lift) + 6S 30000-40000 mAh Li-ion (cruise)", wh=(2*6*3.7*5+6*3.7*30, 2*6*3.7*5+6*3.7*40),
    bmass=None, nlift=4, prop=16.5, lmotor="4x T-motor MN505 KV260, 60 A ESC", cmotor="4120 KV500, 15x8 wood prop, 100 A ESC",
    hover="—", price="—", WVP=None,
    notes="Empty = 'total weight 5.5 kg without battery'; frame 2.68 kg. Max payload 6.5 kg INCLUDES battery. Wh from suggested packs at 3.7 V/cell (estimate). 2.5 h is marketing.")

add(name="Foxtech Loong 2160 VTOL", cfg="Lift+cruise quadplane (4 lift + tractor 'puller')",
    url="https://docs.px4.io/main/en/frames_vtol/vtol_quadplane_foxtech_loong_2160.html", mtow=(7, 8.5), empty=None, payload=1.5, span=2.16, area=None, length=1.2,
    vc=17, vmax=None, vs=None, endur=90, endur_c="'up to 1 h 30 min depending on weather and takeoff weight' (PX4 docs)",
    range_km=None, batt="recommended 12S 22 Ah (linked product named 6S 22000 mAh - conflict)", wh=(6*3.7*22, 12*3.7*22), bmass=None,
    nlift=4, prop=None, lmotor="—", cmotor="—", hover="hover current up to 120 A on 12S power module", price="—", WVP=None,
    notes="'~7 kg takeoff weight excluding payload'; MTOW range = 7 to 7+1.5 kg payload (derived). Battery voltage ambiguous so Wh range spans 6S-12S.")

add(name="MakeFlyEasy Fighter VTOL", cfg="Lift+cruise quadplane (4+1)",
    url="https://ardupilot.org/plane/docs/common-makeflyeasy-fighter-vtol.html", mtow=11.5, empty=None, payload=2.5, span=2.43, area=0.725, length=1.45,
    vc=(17, 20), vmax=None, vs=10, endur=None, endur_c="—", range_km=150, batt="—", wh=None, bmass=None, nlift=4, prop=None,
    lmotor="—", cmotor="—", hover="—", price="—", WVP=None,
    notes="Range 150 km at 600 g load. 4+1 per zbotic.in retailer. Stall 10 m/s at MTOW wing loading 15.9 kg/m2 implies CLmax ~2.5 -> almost certainly not at MTOW / marketing.")

add(name="MakeFlyEasy Striver Mini VTOL", cfg="Lift+cruise quadplane (4+1)",
    url="https://ardupilot.org/plane/docs/common-makeflyeasy-striver-mini-vtol.html", mtow=7.5, empty=None, payload=1.0, span=2.1, area=0.59, length=1.2,
    vc=(18, 21), vmax=None, vs=None, endur=107, endur_c="19 m/s, 600 g load, 6S 22000 mAh, 6.8 kg takeoff, (manufacturer test)",
    range_km=115, batt="6S 22000 mAh (test condition)", wh=6*3.7*22, bmass=None, nlift=4, prop=None, lmotor="—", cmotor="—", hover="—", price="—",
    WVP=6.8*g*19/(0.9*6*3.7*22/(107/60)),
    notes="MTOW listed as '<7.5 kg'. Wh assumes 3.7 V/cell (Li-ion type implied, estimate). W*V/P at 6.8 kg, 90% usable energy assumed. Wh/kg uses the 6.8 kg test mass.")

add(name="MakeFlyEasy Freeman 2300 VTOL", cfg="Lift+cruise quadplane (4+1)",
    url="https://rcdrone.top/products/makeflyeasy-freeman-2300-rc-plane (403 on direct fetch; values from search summary)", mtow=8, empty=None, payload=1.0,
    span=2.3, area=None, length=1.07, vc=65/3.6, vmax=None, vs=None, endur=80, endur_c="claimed; 80 km range with 1000 g load (retailer)",
    range_km=80, batt="—", wh=None, bmass=None, nlift=4, prop=None, lmotor="—", cmotor="—", hover="—", price="—", WVP=None,
    notes="Retailer listing only; low confidence. Length is fuselage.")

add(name="JOUAV CW-007", cfg="Fixed-wing VTOL (subtype not stated by maker; lift+cruise assumed - verify)",
    url="https://jouav.com/products/cw-007.html", mtow=6.8, empty=None, payload=1.0, span=2.2, area=None, length=1.3,
    vc=61.2/3.6, vmax=None, vs=None, endur=55, endur_c="max flight time; 'theoretical values from lab tests' (manufacturer)",
    range_km=None, batt="battery (unspecified)", wh=None, bmass=None, nlift=None, prop=None, lmotor="—", cmotor="—",
    hover="wind limit takeoff/landing 10 m/s", price="—", WVP=None, notes="Length is fuselage. Configuration not explicitly stated on page.")

add(name="JOUAV CW-10", cfg="Lift+cruise ('fixed wing and quadrotor hybrid')",
    url="https://www.vision-systems.com/embedded/article/16750971/uav-with-fixed-wing-and-quadrotor-hybrid-design-to-be-shown-at-xponential",
    mtow=None, empty=None, payload=(1.0, 2.0), span=8.5*0.3048, area=None, length=None, vc=44*0.44704, vmax=67*0.44704, vs=None,
    endur=90, endur_c="'up to 90 minutes' (2017 trade-show article)", range_km=None, batt="—", wh=None, bmass=None, nlift=4, prop=None,
    lmotor="—", cmotor="—", hover="—", price="—", WVP=None, notes="2017 article; payload 2.2-4.4 lb. MTOW not published. Possibly superseded model.")

add(name="JOUAV CW-20E", cfg="Fixed-wing VTOL (lift+cruise family; subtype not stated on page)",
    url="https://www.jouav.com/flightSystem/cw-25e.html", mtow=24.9, empty=None, payload=(5, 6), span=3.5, area=None, length=2.07,
    vc=72/3.6, vmax=None, vs=None, endur=(150, 180), endur_c="150 min spec table; 180 min with 2 kg payload in overview (conflict)",
    range_km=None, batt="—", wh=None, bmass=None, nlift=None, prop=None, lmotor="—", cmotor="—", hover="—", price="—", WVP=None,
    notes="Upper end of size range; payload 5 vs 6 kg conflict on same page.")

add(name="Avy Aera", cfg="Lift+cruise (4 VTOL motors + pusher)", url="https://avy.eu/product/aera", mtow=19.5, empty=None, payload=(2, 3),
    span=2.4, area=None, length=1.5, vc=23, vmax=140/3.6, vs=None, endur=(60, 75), endur_c="standard battery: 60 min spec table vs 75 min text (conflict); extended 100-120 min",
    range_km=(80, 130), batt="1 kWh smart battery", wh=1000, bmass=None, nlift=4, prop=None, lmotor="—", cmotor="—", hover="—", price="—",
    WVP=19.5*g*23/(1000/(115000/23/3600)),
    notes="Span taken from 'W' of 1500x2400x300 L×W×H (inferred). Max speed 140 km/h from avy.eu/discover. W*V/P: MTOW, 115 km range at MTOW, 23 m/s, all 1000 Wh used (upper-bound estimate).")

add(name="ALTI Transition (hybrid)", cfg="Lift+cruise quadplane, petrol pusher + electric lift (hybrid)",
    url="https://www.ust-media.com/ust-magazine/UST008/files/assets/basic-html/page-23.html", mtow=12, empty=None, payload=2, span=2.745, area=None,
    length=1.925, vc=None, vmax=30, vs=None, endur=(240, 360), endur_c="4-6 h wing-borne, still being tested (magazine profile); later claims 8-12 h",
    range_km=300, batt="battery for VTOL only; petrol cruise", wh=None, bmass=None, nlift=4, prop=None, lmotor="custom Al/steel motors", cmotor="petrol engine, pusher",
    hover="—", price="—", WVP=None, notes="Fuel cruise - endurance not comparable to battery aircraft. Later article cites 16 kg MTOW (conflict).")

add(name="Mugin-2 Pro 2930 VTOL", cfg="Lift+cruise quadplane, gasoline cruise + electric lift (hybrid)",
    url="https://www.muginuav.com/product/mugin-2-pro/", mtow=23, empty=None, payload=3, span=2.93, area=0.97, length=2.021,
    vc=(21, 23), vmax=None, vs=18, endur=(120, 300), endur_c="2 h at 3 kg/2.5 L fuel; 4.5 h at 1 kg/5 L; 'up to 5 h' (manufacturer)",
    range_km=None, batt="VTOL battery unspecified; 5 L fuel", wh=None, bmass=None, nlift=None, prop=None, lmotor="—", cmotor="gasoline engine",
    hover="—", price="—", WVP=None, notes="Length from unlabeled overall dims. Search snippet of an older page gave 100.85 dm2 / 7.8 kg empty / 5 kg payload (conflict).")

add(name="Skywalker X8 quadplane (ArduPilot 'Tale of Two Quadplanes')", cfg="Lift+cruise quadplane conversion (flying wing, 4 lift + pusher)",
    url="https://discuss.ardupilot.org/t/a-tale-of-two-quadplanes/18856", mtow=5.1, empty=None, payload=None, span=None, area=None, length=None,
    vc=None, vmax=None, vs=None, endur=25, endur_c="rough calculation, not measured (builder)", range_km=None, batt="2x 4S 5800 mAh LiPo parallel",
    wh=2*4*3.7*5.8, bmass=None, nlift=4, prop=14, lmotor="4x T-Motor 3510-13 700 kV, 40 A ESC", cmotor="SK3 40xx, 13x8.5 prop, 85 A ESC",
    hover="measured hover up to 60 A (~888 W at 14.8 V nominal, derived); transition spikes >90 A", price="—", WVP=None,
    notes="Hobby build, measured currents (approximate - one pack metered). Cruise ~10 A measured after prop change (~148 W derived), speed not stated. Hover W/kg ~174 (derived).")

add(name="Skywalker X8 quadplane (ArduPilot 'Build 4')", cfg="Lift+cruise quadplane conversion (flying wing, lift + pusher)",
    url="https://discuss.ardupilot.org/t/skywalker-x8-quadplane-build-4/42083", mtow=7, empty=5, payload=None, span=None, area=0.96, length=None,
    vc=17, vmax=None, vs=None, endur=(5, 60), endur_c="~5 min on vertical battery (test); up to ~60 min with 2 forward packs (unverified)",
    range_km=60, batt="4S 5000 mAh (lift) + 1-2x 4S 8000 mAh (cruise)", wh=(4*3.7*5+4*3.7*8, 4*3.7*5+2*4*3.7*8), bmass=None, nlift=4, prop=(12, 13),
    lmotor="SunnySky 3120-1100 kV (count not stated)", cmotor="SK3 4240-740 kV, 13x8", hover="measured 60 A hover, 90 A peak (~888 W at 14.8 V, derived)",
    price="—", WVP=7*g*17/(10*14.8),
    notes="Measured: <10 A cruise at 17 m/s airspeed (W*V/P is upper bound since <10 A). Lift prop 12x4.8 vs 13 in conflict; 4 lift motors assumed. Area 96 dm2 with wing extensions. Range estimated.")

add(name="U. Michigan QuadPlane (Mathur & Atkins, arXiv 2301.12316)", cfg="Lift+cruise quadplane (4 vertical pushers + tractor), academic",
    url="https://arxiv.org/html/2301.12316v1", mtow=1.684, empty=None, payload=None, span=1.2192, area=0.1524*1.2192, length=None,
    vc=None, vmax=None, vs=10.09, endur=None, endur_c="—", range_km=None, batt="4S 2650 mAh LiPo", wh=4*3.7*2.65, bmass=None, nlift=4, prop=9.5,
    lmotor="920 kV, 30 A ESC", cmotor="920 kV, 9.5x4.5", hover="—", price="—", WVP=None,
    notes="Below 3 kg target range; included for wind-tunnel-measured aero (paper reports increased drag/reduced thrust from rotor-wing interaction). Area = span x 6 in chord (derived). AR 8 stated.")

# ---------------- contrast configurations ----------------
add(name="Wingcopter 178 Heavy Lift (delivery)", cfg="CONTRAST: tilt-rotor (4 rotors)",
    url="https://wingcopter.com/wp-content/uploads/2021/02/Technical-Details-Wingcopter-178-Heavy-Lift-A-Delivery-Variant-1-1.pdf",
    mtow=18, empty=8.4, payload=6, span=1.78, area=None, length=1.46, vc=24, vmax=42, vs=14, endur=(35, 120),
    endur_c="max 120 min; range table 35/50/85/100 min for 2/3/4/4 batteries at 6/4/2/0 kg payload, ideal conditions, 30% reserve",
    range_km=(40, 120), batt="2-4x LiPo 22.2 V 16 Ah", wh=(2*22.2*16, 4*22.2*16), bmass=(3.6, 7.2), nlift=4, prop=None, lmotor="—", cmotor="same rotors tilted",
    hover="multicopter mode max 2 min at a time", price="—", WVP=15.7*g*(120000/6000)/(0.7*4*22.2*16/(100/60)),
    notes="Battery ~1.8 kg each derived from (12.0-8.4)/2. 14 m/s = fixed-wing minimum speed (not stall). W*V/P: 4 batt, 0 kg payload (15.7 kg), 120 km in 100 min, 70% of 1421 Wh used.")

add(name="Quantum Systems Trinity F90+", cfg="CONTRAST: tilt-rotor (flying wing, 3 rotors)",
    url="https://www.ferntech.co.nz/trinity-f90-plus-fixed-wing-mapping-drone", mtow=5.0, empty=None, payload=0.7, span=2.394, area=None, length=None,
    vc=17, vmax=None, vs=None, endur=(60, 90), endur_c="60 min default limit; 90+ min unlocked (export-controlled)", range_km=100,
    batt="Wh not published", wh=None, bmass=1.5, nlift=None, prop=None, lmotor="—", cmotor="—", hover="—", price="NZ$32,798 (currency not stated; discontinued)", WVP=None,
    notes="Battery mass 1.5 kg -> 30% of MTOW. Rotor count not on cited page.")

add(name="WingtraOne Gen II", cfg="CONTRAST: tailsitter", url="https://wingtra.com/wingtraone-gen-ii-drone/", mtow=4.8, empty=None, payload=0.8,
    span=1.25, area=None, length=None, vc=16, vmax=None, vs=None, endur=59, endur_c="'up to 59 min', conditions in KB (manufacturer)",
    range_km=None, batt="2x 99 Wh Li-ion (pair)", wh=198, bmass=None, nlift=2, prop=None, lmotor="—", cmotor="—", hover="—", price="—",
    WVP=4.5*g*16/(198/(59/60)),
    notes="Older docs list MTOW 4.5 kg; 3.7 kg with batteries (volatusdrones.ca/korec). Span from retailers. W*V/P at 4.5 kg, 100% of 198 Wh (upper bound).")

add(name="Autel Dragonfish Lite", cfg="CONTRAST: tilt-rotor", url="https://www.gpsworld.com/autel-robotics-tilt-rotor-dragonfish-lite-and-pro-uavs-available-in-us/",
    mtow=5.5, empty=None, payload=1.0, span=1.6, area=None, length=0.965, vc=None, vmax=30, vs=None, endur=(75, 81),
    endur_c="75 min (GPS World) vs 81 min (Autel brochure)", range_km=None, batt="—", wh=None, bmass=None, nlift=None, prop=None,
    lmotor="—", cmotor="—", hover="—", price="—", WVP=None, notes="4.5 kg incl. 2 batteries. Max speed is series-wide. Values via search summaries of retailer/press pages.")

add(name="Heewing T2 Cruza VTOL", cfg="CONTRAST: tilt-rotor tricopter (3 motors, 2 tilt servos)",
    url="https://www.fpv24.com/en/heewing/heewing-t2-cruza-vtol-fpv-glider-airplane-pnp-black", mtow=(2.0, 3.5), empty=None, payload=None, span=1.2, area=None, length=1.11,
    vc=None, vmax=None, vs=None, endur=None, endur_c="—", range_km=None, batt="6S LiPo 2000-20000 mAh (not incl.)", wh=None, bmass=None, nlift=3, prop=10,
    lmotor="3x 2812 (fpv24) vs 3x 3110 (rotorama) - conflict", cmotor="shared tilting motors", hover="—", price="EUR 779.90 PNP (fpv24); EUR 723.79 (rotorama)", WVP=None,
    notes="Below 3 kg at low end. Configuration inferred from parts list (3 motors + 2 tilt servos).")

add(name="TiltOne box-wing (Univ. Pisa / SkyBox, NATO STO-MP-AVT-323-27)", cfg="CONTRAST: tilt-wing box-wing, 4 props (academic)",
    url="https://publications.sto.nato.int/publications/STO%20Meeting%20Proceedings/STO-MP-AVT-323/MP-AVT-323-27.pdf", mtow=11, empty=None, payload=0.3,
    span=1.0, area=0.5, length=1.0, vc=19.5, vmax=None, vs=15.6, endur=39, endur_c="design: 5 min hover + ~34 min cruise on 80% of capacity (calculated)",
    range_km=40, batt="2x 6S 10000 mAh 15C LiPo", wh=2*6*3.7*10, bmass=None, nlift=4, prop=13, lmotor="Kv 490 (bench: 3.35 kgf max, ~35 A)", cmotor="same (tilt-wing), 13x6",
    hover="calc hover 1417 W, cruise 569 W", price="—", WVP=11*g*19.5/569,
    notes="11 kg is a design mass cap, not weighed. L/D max ~6 (AVL/XFOIL est.). Stall 15.6 m/s 'very conservative'. AR not meaningful for box-wing (b^2/S = 2). Hover W/kg 129 (derived).")

hdr = ["name","configuration","source_url","date_checked","mtow_kg","empty_mass_kg","payload_kg","wingspan_m","wing_area_m2","length_m",
       "cruise_speed_ms","max_speed_ms","stall_speed_ms","endurance_min","endurance_condition","range_km","battery","battery_mass_kg",
       "n_lift_rotors","lift_prop_in","lift_motor","cruise_prop_motor","hover_limits","price_usd",
       "wing_loading_kgm2_DERIVED","disk_loading_Nm2_DERIVED","battery_Wh_DERIVED","battery_Wh_per_kg_MTOW_DERIVED","aspect_ratio_DERIVED",
       "battery_mass_fraction_DERIVED","payload_fraction_DERIVED","W_V_over_P_DERIVED","notes"]
with open(OUT, "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f); w.writerow(hdr)
    for r in rows:
        m = r["mtow"]
        mm = 6.8 if r["name"].startswith("MakeFlyEasy Striver") else m
        wl = rng(lambda m, a: m/a, mm, r["area"]) if r["area"] else None
        dl = disk(m, r["nlift"], r["prop"]) if (r["nlift"] and r["prop"] and m) else None
        if r["name"].startswith("C0"): dl = 110.0
        whkg = rng(lambda e, m: e/m, r["wh"], mm) if (r["wh"] and m) else None
        ar = rng(lambda b, a: b*b/a, r["span"], r["area"]) if (r["span"] and r["area"] and "box-wing" not in r["name"]) else None
        bf = rng(lambda b, m: b/m, r["bmass"], m) if (r["bmass"] and m) else None
        pf = rng(lambda p, m: p/m, r["payload"], m) if (r["payload"] and m) else None
        w.writerow([r["name"], r["cfg"], r["url"], D, fmt(m,2), fmt(r["empty"],2), fmt(r["payload"],2), fmt(r["span"],3), fmt(r["area"],3),
                    fmt(r["length"],3), fmt(r["vc"],1), fmt(r["vmax"],1), fmt(r["vs"],2), fmt(r["endur"],0), r["endur_c"], fmt(r["range_km"],0),
                    r["batt"], fmt(r["bmass"],2), fmt(r["nlift"],0), fmt(r["prop"],1), r["lmotor"], r["cmotor"], r["hover"], r["price"],
                    fmt(wl,1), fmt(dl,0), fmt(r["wh"],0), fmt(whkg,0), fmt(ar,2), fmt(bf,2), fmt(pf,2), fmt(r["WVP"],1), r["notes"]])
print(len(rows), "rows")
