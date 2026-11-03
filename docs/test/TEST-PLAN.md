# Test and evaluation plan — C0 lift + cruise VTOL

**Document DBF-TP-001 rev C** · 2026-11-02 (rev B 2026-10-21) · Status: draft for team review
Applies to: C0 4-lift twin-boom quadplane, frozen design of 2026-11-01 (`analysis/results.json` generated 2026-11-01: MTOW 7.44 kg, `concepts.C0.sized.m` 7.4380; `analysis/mass/mass_budget.json`; `cad/params.txt` mtow 7.437998; C0 flight model `firmware/sitl/c0_physics.py --validate` (`firmware/sitl/validation_c0.json`): mass 7.438 kg, stall 11.75 m/s, static margin 10.41 %; aero build-up `analysis/aero/aero_results.json` generated 2026-11-02; CAD build `cad/verification.txt` 2026-11-01 and FEA `cad/sim/results.txt` 2026-11-02; thermal analysis `docs/research/thermal.md`, re-run 2026-11-02 at the 25 °C design ambient of R21; firmware `firmware/vtol_c0.param` on ArduPlane 4.7.2 stable; BOM `docs/purchasing/C0_BOM.csv`). Cruise 18 m/s.

Revision history (old numbers live in git history, not here): rev A → rev B 2026-10-21 (v0.4 re-base; tests C16, C17, S10, G09, F13, F09 added); 2026-10-25 twice (R11 wing re-size, then the 11.75 m/s design stall target; thermal rules added); 2026-10-27 (cruise 20 → 18 m/s). **Rev C, 2026-11-02:** every prediction and pass line re-based on the frozen 7.44 kg design with the formula shown; payload and ballast removed (R12 revised 2026-11-01), so S10 is withdrawn and G09 becomes a battery-station check; hot-day rules replaced by the R21 field-temperature ceiling (25 °C); pack acceptance 6.0 mΩ/cell (C11); battery plug AS150U (R20), ESC LANRC BLHeli_S 45A, GPS RMRC SAM-M10Q-5883, airspeed RMRC MS4525DO (`docs/purchasing/C0_BOM.csv`, `docs/research/bom-savings.md`); new open items §12 items 18–21. 2026-11-03: drawing rev F (item 21 resolved; R1 and the printer-offset test now use rev F); static margin 10.4 % (AVL).

Conventions: every number names its source as a repo file, a shown formula *(calc)*, or a URL with the date checked. **EST** = engineering estimate. **—** = unknown, never invented. Numbers quoted from `analysis/results.json` are `concepts.C0.*` unless stated; `aero_results.json` = `analysis/aero/aero_results.json`. Requirement IDs R1–R21 are from `docs/DESIGN-BASIS.md`. "Review §N" and "review MN.k" refer to the chapters and measurements of design review DBF-RPT-001.

Companion files: `docs/test/test-matrix.csv` (one row per test), `docs/test/cards/` (printable test cards and data sheets), `docs/test/analysis/` (data-reduction scripts with sample data).

---

## 1. Purpose and scope

This plan takes the aircraft from incoming parts to a verified full mission (R9) and closes every requirement R1–R21 by **T**est, **A**nalysis, **I**nspection or **D**emonstration with a numeric pass/fail criterion. It covers:

- incoming inspection and coupon tests (series C),
- structural proof and stiffness tests on the built airframe (series S),
- electrical and avionics bench tests including SITL (series E),
- ground tests on the complete aircraft (series G),
- flight tests from first lift-off to the full mission (series F),
- documentary inspections for budget, legal and configuration (series I).

Out of scope: the browser flight-simulator code (outside the project brief), destructive ultimate-load tests (no spare joiner or wing in the budget, `docs/purchasing/C0_BOM.csv`), and any test that needs equipment outside the BOM unless a zero-cost substitute is given here (§13 Gaps).

## 2. Test philosophy

1. **Build-up.** No test runs until its prerequisites have passed (matrix column "Prerequisites"). The order is component → structure → bench → ground → tethered → free hover → forward flight → transition → mission, matching the review's F0–F7 build-up (§13 "Build-up test matrix").
2. **Predict before you measure.** Every test lists the analysis prediction (from `analysis/results.json`, `aero_results.json`, `cad/sim/results.txt`, `cad/verification.txt` or `firmware/vtol_c0.param`) so the result either validates the model or triggers a re-run of `analysis/sizing.mjs`.
3. **Incremental risk.** Each flight card adds one new thing. Hover exposure is limited (≤ 5 m AGL, ≤ 60 s per hover on hover-only flights, §10 "Transition and threshold table") because C0 has no lift-motor-out tolerance (R14, `docs/DESIGN-BASIS.md` design outcomes).
4. **Cheap instrumentation.** Everything uses BOM test gear (watt meter, IR thermometer, 20 kg load cell + HX711 + Nano, LiPo bag, ammo can: `docs/purchasing/C0_BOM.csv` "Test & safety"), hand tools on hand (R6), household items (water jugs, sandbags, kitchen scale, phone) and the flight controller's own logs. Telemetry is CRSF to the handset or the ELRS MAVLink overlay (`docs/research/firmware.md` §4 R7/R9); no telemetry radio is needed or budgeted.
5. **One owner per test, one sheet per run.** Results go on the data sheet in `docs/test/cards/`, then into the matrix status column.

## 3. Roles

| Role | Duties | Minimum qualification |
|---|---|---|
| **Test director (TD)** | Owns the test card, calls go/no-go, holds the abort authority, signs the data sheet. | Has read this plan and the card; not the pilot. |
| **Safety officer (SO)** | Range clear, fire bag + extinguisher + first-aid kit, LiPo handling, crowd line, calls "abort" for any safety breach. | TRUST or Part 107 (R18). |
| **Pilot in command (PIC)** | Flies; is the only person who touches the transmitter; has passed SITL rehearsal E06 (§[flighttest] M1 of the review). | TRUST (or Part 107), AMA member for liability (R19), ≥ 1 h SITL on `firmware/vtol_c0.param`. |
| **GCS operator (GCS)** | Reads the handset CRSF telemetry (or Mission Planner over the ELRS MAVLink overlay / CoreWing BLE-WiFi near the pad): battery, mode, altitude, VIBE, EKF status every 30 s; saves logs. | Has run E06 scenarios. |
| Visual observer (VO) | Keeps VLOS on the aircraft and the sky (R18); part of the 4-person team. | — |

Crew roles are the review's (§[flighttest] "Crew, field procedure and charging") with the test director added. Names: — (assign in the matrix "Crew" column at sign-off).

## 4. Safety rules

1. **Props off** for every bench test unless the card says otherwise. Battery is plugged in last through the AS150U plug (R20, `docs/DESIGN-BASIS.md`) and unplugged first.
2. **Arming.** RC arm switch (CH5, `RC5_OPTION,153`) only; no stick arming (`ARMING_RUDDER,0`); arming only in VTOL modes (`Q_OPTIONS` bit 18). Motor emergency stop on CH7 (`RC7_OPTION,31`). Source: `firmware/vtol_c0.param` §7–8.
3. **LiPo.** Charge and store in the LiPo bag inside the ammo can; never unattended; crashed pack isolated outdoors 30 min (§[flighttest] review). Fire bag within 5 m of any powered test.
4. **Thrust stand and tied-down runs.** Prop plane never in line with a person; 3 m clear radius; eye protection; stand bolted or sandbagged so that it cannot move at 3.13 kgf (X4110S max, `docs/research/budget-lift.md` A3) × 4.
5. **Structural tests.** Nobody under a loaded wing; load in 1 kg steps; a second person watches the joiner region.
6. **Flight.** VLOS at all times; geofence `FENCE_ALT_MAX,110` m home-relative (SITL breach peak 113.1 m, under the 121.9 m (400 ft) limit, `firmware/sitl/README.md` scenario F; R18); crowd line 30 m from the take-off point and never under the flight path; flight path over open ground only; no people downrange during transitions.
7. **No ballast, no payload.** R12 (revised 2026-11-01) removed the 0.5 kg payload reserve; the lengthened pod nose and the pack at x = 0.255 m put the CG at 28 % MAC with nothing in the bay (`results.json cg.xb` 0.2550, `cg.pct.noPayload` 28; static margin 10.40 % AVL, `aero_results.json neutral_point.static_margin_pct.CG_28pct`, and 10.24 % sizing, `geo.SM`). Nothing is carried in the bay. Any added mass is a design change (R12): re-run the sizing and G01 before flying it.
8. **Post-flight.** IR thermometer on every motor, ESC and the pack within 30 s of landing (§[testing] M1 of the review): pack > 60 °C EST or any unit 15 °C hotter than its neighbours grounds the aircraft.
9. **Field temperature ceiling (R21).** No full mission (F11, F12) and no flight with a transition (F06–F13) when the air temperature measured at the field before the flight is above 25 °C; write the reading on the card. Basis: the thermal model at a 25 °C ambient (`docs/research/thermal.md`; `cad/sim/thermal/results.txt`, 2026-11-02) puts the lift motor can at a 75 °C mission peak (limit 80 °C EST, +5 K), the lift ESC at 62 °C (70 °C EST, +8 K), the pack at the 6.0 mΩ/cell acceptance limit at 53 °C at touchdown (60 °C, +7 K) and the pusher can at 76 °C after 600 s of cruise (80 °C EST, +4 K). The lift-unit peak comes at the end of the take-off hover + first transition, which every flight from F06 on contains, hence the wider scope here than R21's "full mission" (all temperatures are linear in ambient: +1 K per 1 K). The ≤ 60 s per hover rule (§2 item 3) and the post-flight IR limits (rule 8) stay; pack rules are in §6 and C11.

## 5. Abort criteria (all tests)

Any crew member can call "ABORT". The PIC then: in hover → land now (QLAND if ≥ 5 m); in forward flight → select QHOVER/QLAND if airspeed < 13 m/s or RTL (CH9) otherwise. Universal abort triggers:

| Trigger | Threshold | Source |
|---|---|---|
| Vibration | VIBE X/Y/Z > 30 m/s² sustained or clipping count rising | ArduPilot "Measuring Vibration" (ardupilot.org/plane/docs/common-measuring-vibration.html, checked 2026-10-21) |
| Attitude error in hover | > 15° | review §[flighttest] F2 |
| Oscillation | Any visible attitude or altitude oscillation | ArduPilot QuadPlane tuning step 5 (ardupilot.org/plane/docs/quadplane-vtol-tuning-process.html, checked 2026-10-21) |
| Battery | Sag-compensated voltage < 21.0 V (3.5 V/cell) or < 1,625 mAh remaining on any non-mission flight (the firmware's low-battery RTL point) | `firmware/vtol_c0.param` BATT_LOW_VOLT, BATT_LOW_MAH, BATT_FS_LOW_ACT 1 (RTL); critical 19.8 V / 1,300 mAh → QLAND |
| Temperature | Motor can > 80 °C EST after a hover; ESC > 70 °C EST | review §[testing] T3; ESC limit EST (LANRC publishes none, —) |
| Wind | Steady > 5 m/s or gusts > 8 m/s (R16); for F01–F06, steady > 3 m/s EST | R16; EST for early flights |
| RC link | LQ < 70 % EST or any failsafe message | EST |
| GCS/EKF | "EKF variance", "GPS glitch", compass inconsistent | ArduPilot pre-arm/EKF messages |
| Fence proximity | Aircraft within 50 m of the 300 m fence circle in fixed-wing flight (a straight transition reaches it ~6 s after "Transition done", `firmware/sitl/README.md`) | `FENCE_RADIUS,300`; SITL finding |
| People or animals inside the range | any | — |
| Airspace | Any manned aircraft within sight and converging | R18 VLOS and right-of-way |

## 6. Go/no-go and weather limits

Go for any flight test requires all of:

- Prerequisite tests passed and signed in the matrix.
- Flight request approved (R19: ≥ 7 business days ahead; RFS for transition tests, ≥ 30 m AGL), Remote ID module powered and broadcasting (R18), registration marking on the airframe, PIC's TRUST/AMA documents on site.
- Pre-flight checklist complete (`firmware/checklists.md` if present; otherwise card §"Pre-flight").
- Weather: steady wind ≤ 5 m/s, gusts ≤ 8 m/s (R16); for first flights F01–F06 steady ≤ 3 m/s EST; visibility ≥ 3 sm and cloud clearance per 14 CFR 107.51 (`docs/DESIGN-BASIS.md` rule sources); no precipitation; air temperature 10–30 °C for hover-only flights F01–F05 (ArduPilot tuning guide recommends 15–25 °C for first flights; the extended band is EST) and **≤ 25 °C, measured at the field before the flight, for every flight with a transition (F06–F13) and every full mission (R21, §4 rule 9)**. Wind measured with a phone anemometer app or a hand-held anemometer if borrowed (§13 Gaps); otherwise the nearest METAR/NWS point, recorded on the card.
- Daylight: 6 a.m. to sunset (R19 site rule).
- **Pack temperature and resistance** (R21; `docs/research/thermal.md` §6.2): only packs whose C11 resistance is ≤ 6.0 mΩ/cell fly F11/F12 (a pack above it does not fly a full mission); packs and aircraft shaded until plug-in; pack start temperature by IR ≤ 60 − 4.7 × R_cell (mΩ) °C for a full mission *(calc: the sealed-bay pack rises 28.2 K over the mission at 6.0 mΩ/cell, 53.2 °C from 25 °C, `cad/sim/thermal/results.txt pod_mission_max_Battery`; heat ∝ R, so 28.2 / 6.0 = 4.7 K per mΩ/cell)*, i.e. ≤ 31.8 °C for a pack at the limit; hovers stay ≤ 60 s; if C08 measured a 90 s can rise above 52 K, the field ceiling is lowered as C08 states; abort at 80 °C can / 70 °C ESC as §5.
- No ballast and no payload (§4 rule 7); take-off mass and CG per G01/G09.
- Two charged packs (≥ 4.15 V/cell), one spare prop set, spare ESC, repair kit on site. (No spare motor, servo or pushrods are in the BOM, `docs/DESIGN-BASIS.md` assumption 4: a motor, servo or pushrod failure ends the session until a replacement is bought from the reserve.)

## 7. Range setup

- Take-off pad: 3 × 3 m flat mown grass or hard surface, clear of obstacles 20 m radius, marked with the geofence home point.
- Crew line 30 m upwind of the pad for hover-only flights (F01–F05). For flights with a transition (F06 onward) it moves 30 m to the crosswind side of the take-off point, because transitions start into wind and the crew must never be under the flight path (§4 rule 6). Spectators behind the crew line. Fire bag, extinguisher and first-aid kit at the crew line.
- Transition runway: a straight ≥ 200 m EST into wind at ≥ 30 m AGL (review M[schedule].1: under 200 m or a ceiling under 30 m blocks R9 at that site). **Transitions start at the upwind field edge with an immediate turn after "Transition done"** (`firmware/README.md` §9.6; SITL: a straight transition reached the 300 m fence circle about 6 s after transition end). GPS-walk the field and set `FENCE_RADIUS` to the usable radius (default 300 m, `firmware/vtol_c0.param` §10).
- Tether anchor (G05): two sandbag-weighted ground stakes, 2 × 4 m lines of ≥ 50 kg rated cord to the landing-leg clamps, slack so the aircraft can reach 1.5 m.
- Site ceilings: RFS 400 ft, Clark Kerr 200 ft, La Loma 20 ft inside the fences (R19). Only RFS supports transition tests.

## 8. Verification cross-reference matrix

Method: T test, A analysis, I inspection, D demonstration. Status is "open" for every line at rev C except where a SITL portion is done (E05, E06).

| Req | Requirement (short) | Method | Test ID(s) | Pass criterion (numeric) | Status |
|---|---|---|---|---|---|
| R1 | Lift rotors + pusher + wing; lift rotors stopped in cruise | I, D | I03, F07, F12 | Built aircraft matches `cad/drawings/DBF-DRW-001.PDF` sheet 1 (rev F, 2026-11-03); log shows lift motor outputs (RCOU C5–C8) at `Q_M_PWM_MIN` (1000) for ≥ 95 % of cruise time | open |
| R2 | MTOW 8–15 kg target, < 25 kg cap; outcome 7.44 kg | T | S09, G01 | Take-off mass with pack, no ballast ≤ 7.82 kg = 4 × 3.130 / 1.6 *(calc: the R13 limit with the maker's 3.130 kgf per motor, `params.Tmax_g`; replace 3.130 by the lowest C07 max thrust once measured)* and < 25 kg; predicted 7.44 kg (`sized.m`; mass budget bottom-up 7.42 kg, `analysis/mass/mass_budget.json`). The rev B rule "MTOW × 1.15" would give 8.55 kg, above the R13 limit, so it no longer governs | open |
| R3 | Span 2–3 m | I | I03 | Tip-to-tip 2.40 ± 0.02 m (`results.json base.span`) | open |
| R4 | Largest piece fits a standard car | D | S08 | Longest piece ≤ 1.2 m (`geo.longestPiece`); pod piece ≤ 0.5 m with the joiner slid out (`cad/README.md` wing root); every piece fits in the team's car with the hatch closed | open |
| R5 | Two-person carry; assembly ≤ 15 min | D | S08, G07 | Two people carry the assembled aircraft 50 m; median of 3 assembly runs ≤ 15 min | open |
| R6 | Spend ≤ $2,000 incl. tax and shipping | I | I01 | Ledger of receipts ≤ $2,000.00 (BOM committed $1,854.17) | open |
| R7 | Second pack, spares, reserve ≥ $100 target | I | I01 | Two packs, spare ESCs (3 in the two 4-packs), spare prop pair received (no spare motor: held as reserve cash, `docs/DESIGN-BASIS.md` assumption 4); reserve = 2,000 − ledger ≥ $100 (BOM $145.83) | open |
| R8 | Flight-tested by 2027-04-30 | D | F12 | F12 passed and dated ≤ 2027-04-30 | open |
| R9 | Mission: VTOL take-off → hover → transition → cruise → back-transition → hover → vertical land | D | F12 | One continuous flight with all phases in the log, no failsafe, undamaged landing | open |
| R10 | ≥ 10 min cruise + ≥ 2 min hover, ≥ 20 % energy reserve | T, A | C11, F08, F13, F12 | F12 log: cruise ≥ 600 s, hover ≥ 120 s, remaining ≥ 20 % of measured usable capacity (C11) and ≥ 1,300 mAh (`BATT_CRT_MAH`); cruise power ≤ 356 W *(calc: (0.8 × 144.3 × 0.95 − 1,131.9 × 160/3600) × 3600/600 = 356 W; `sized.P_hover`, `base.tHover` + `base.tTrans` 160 s, `base.reserve`, `base.etaBatt`, `packs[0].Wh`)*; predicted 258–296 W at the 18 m/s design cruise (`aero_results.json drag.cruise.P_elec_W`, `sized.P_cruise`) | open |
| R11 | Cruise 18–22 m/s; stall ≤ 12 m/s; transition complete ≥ 1.3 × Vs | T, A | F08, F09, C09 | Trimmed cruise at 20 ± 2 m/s calibrated airspeed; measured Vs ≤ 12.0 m/s (predicted 11.75 m/s, `aero_results.json stall.V_stall_mps`, 2.1 % speed margin; 11.75 m/s in the C0 flight model, `c0_physics.py --validate`; 12.0–12.5 = team decision, aero §9; > 12.5 fail, `docs/research/aerodynamics.md` M2); `AIRSPEED_MIN` 16 ≥ 1.3 × measured Vs (Vs ≤ 12.3); airspeed calibration error ≤ 10 % | open |
| R12 | Payload: none beyond avionics (revised 2026-11-01) | I | G01, G09, F12 | Nothing in the bay and no ballast on any flight; CG at 28 ± 2 % MAC with the pack alone (G01) | open |
| R13 | Hover T/W ≥ 1.6 at MTOW with all lift motors, on the maker's 22.2 V thrust table | T | C07, F03 | Each motor ≥ 2.98 kgf max at 22.2 V on the stand (= 1.6 × 7.438 / 4 = 2.975 *(calc, `sized.m`)*; maker 3.13 kgf, predicted T/W 1.68, `sized.TW`); learned `Q_M_THST_HOVER` ≤ 0.60 (review F2 "lift output < 60 %"; expected 0.59, §12 item 19) | open |
| R14 | Lift motor-out: cruise continues (hard); hover (desired, not met by C0) | A, D, I | E06, F07, I03 | SITL motor-fail scenario in hover (documents the accepted limitation; open — not in the A–G set); cruise with lift motors stopped shown in F07; hover limits ≤ 5 m AGL / ≤ 60 s written on every hover card | open |
| R15 | Pusher-out in cruise → re-enter hover and land | D | E06, F10 | SITL D (transition timeout → QRTL) done; in flight: pusher to idle at ≥ 60 m, Q_ASSIST engages below 13 m/s, QLAND completes, altitude loss ≤ 30 m EST | SITL done; flight open |
| R16 | Operate in steady wind ≤ 5 m/s, gusts ≤ 8 m/s | D, A | F07, F12 | At least one F07 or F12 flight in recorded steady wind 3–5 m/s with attitude error < 15°; gusts to 8 m/s by analysis only (margin: `AIRSPEED_MIN` 16 vs Vs 11.75) | open |
| R17 | Open-source autopilot with maintained VTOL support | I | E11 | Flight firmware is ArduPlane 4.7.2 stable for CoreWingF405WingV2 (`firmware/vtol_c0.param` header; `docs/research/firmware.md` §4 R10/R20: beta risk closed) | open (firmware identified; flash check pending) |
| R18 | FAA: 44809/Part 107, TRUST, registration, Remote ID, VLOS, ≤ 400 ft | I, T | I02, E12 | Documents on file; BeeID serial on uasdoc.faa.gov; broadcast seen on a Remote ID app; `FENCE_ALT_MAX` 110 m (SITL peak 113.1 m) | open |
| R19 | Campus: flight request, post-flight report, $1M liability | I | I02 | Approved request on file ≥ 7 business days before each on-campus flight; AMA card per pilot | open |
| R20 | Arming switch/kill, failsafe RTL-then-land, geofence | T, D | E05, E06, F05, F10 | SITL B/C/E/F/G done (`firmware/sitl/results/summary.json`; repeated on the C0 airframe model 2026-10-25 and 2026-10-27, `firmware/sitl/results_c0.json`, on the 6.55 kg model, §12 item 20); bench and in flight: RC loss → QLAND (hover) / RTL → QRTL (cruise); low battery → RTL, critical → QLAND; fence breach → RTL; AS150U disconnect and CH7 E-stop demonstrated | SITL done; hardware/flight open |
| R21 | Full-mission ambient ≤ 25 °C, measured at the field before each flight | I, A | §4 rule 9, §6, C08, C11, F03, F08, F12 | Air temperature read at the field and written on every F06–F13 card, ≤ 25 °C; C08, C11 and F08 measurements confirm the thermal model (`docs/research/thermal.md`) or lower the ceiling as C08 states | open |

Every requirement has at least one verifying test. R14 (hover motor-out) and R16 (8 m/s gusts) are closed by analysis plus a limited demonstration because a full test would risk the aircraft.

## 9. Test series

Each test lists: objective · article/config · setup and instrumentation · procedure · data · pass/fail · predicted value · risk and mitigation · duration · crew · prerequisite tests. Dates are in `docs/test/test-matrix.csv` and §11.

### 9.1 Series C — component and coupon tests

#### C01 — Printed hole and bore coupon (first article)
- **Objective.** Set the printer's as-printed offsets so every bore and insert hole meets `docs/research/hardware-spec.md` §5b (FT02, FT07, FT08) and the rev F drawing tolerance block, which adds a ±0.5 mm EST row for hot-wired foam (`cad/README.md` drawing set).
- **Article.** One coupon per material (ELEGOO PETG, Polymaker PA6-CF20) printed on the team printer: M3 clearance holes modelled 3.4 / 3.6 mm, insert holes 3.8 / 3.9 / 4.0 / 4.1 mm, a 25.4 mm bore ring modelled 25.5 / 25.6 / 25.7 mm (hardware-spec M2), plus a 22.4 mm joiner bore ring (FT06 slip fit, 22.455 ± 0.20).
- **Instrumentation.** Calipers (hand tools, R6) or drill-shank gauges.
- **Procedure.** (1) Print both coupons with the production profile. (2) Measure each hole at two diameters. (3) Choose the model value that prints 3.4, 4.0, 22.46 and 25.6 ± 0.1 mm. (4) Record the offsets in `cad/params.mjs` notes.
- **Data.** Hole ID vs modelled value, per material.
- **Pass.** A model value exists for each target within ± 0.1 mm; otherwise adjust flow/scale and reprint (fail = no setting reaches ± 0.2 mm).
- **Predicted.** Desktop FDM ± 0.5 %, floor ± 0.5 mm (Xometry FDM tolerances via hardware-spec §5b, checked 2026-10-21): expect holes 0.2–0.4 mm undersize.
- **Risk.** PA6-CF needs a hardened nozzle (review §[build] "Prints"); if the printer cannot, PETG mounts are not acceptable near motors (HDT ~68 °C, review M[propulsion].2) → Gap list.
- **Duration** 3 h print + 0.5 h. **Crew** 1. **Prereq.** Filament received (Order B).

![**Figure C01.** Printed hole and bore coupon (first article): set-up rendered from the CAD model (test gear illustrative).](figures/t_c01.svg)

#### C02 — Heat-set insert torque-out, PETG and PA6-CF
- **Objective.** Confirm the 0.5 N·m EST working torque (hardware-spec §2d) has ≥ 2× margin to insert spin-out.
- **Article.** 3 ruthex RX-M3x5.7 inserts per material in the C01 coupon (4.0 mm holes, boss Ø ≥ 8 mm, hardware-spec §2c).
- **Setup.** M3 × 12 screw, washer; hex key with a known arm; hanging masses (water bottles: 1.0 L = 1.00 kg, kitchen scale). Torque T = m g L (hardware-spec §2d: 0.6 N·m at L = 60 mm needs 1.02 kg).
- **Procedure.** (1) Install inserts with a soldering iron at the filament vendor's temperature. (2) Thread the screw to bottom against the washer. (3) Hang mass at L = 100 mm, increase in 0.1 kg steps (0.098 N·m) every 10 s until the insert turns. (4) Record the spin-out torque; repeat for all 6.
- **Data.** Spin-out torque per insert; failure mode (insert spins / plastic cracks).
- **Pass.** Every insert ≥ 1.0 N·m (hardware-spec M3: fails the 0.5 N·m working torque if any spins below 1.0 N·m).
- **Predicted.** — (torque-out in these plastics not published; hardware-spec "Unknowns").
- **Risk.** Coupon cracks at the boss: redesign the boss diameter before printing real parts.
- **Duration** 1 h. **Crew** 1. **Prereq.** C01.

![**Figure C02.** Heat-set insert torque-out, PETG and PA6-CF: set-up rendered from the CAD model (test gear illustrative).](figures/t_c02.svg)

#### C03 — Heat-set insert pull-out, PETG and PA6-CF
- **Objective.** Measure the axial holding force of one M3 insert in each material.
- **Setup (zero-cost).** Lever rig: 1.2 m length of 2×4 pivoted on a block 0.2 m from one end (5:1 ratio); the coupon clamped under the short end with the screw hooked to the beam by a wire loop; water jugs hung from the long end. Or, where available, the thrust-stand load cell (C06) in series with a turnbuckle (not in BOM).
- **Procedure.** (1) Fit a M3 × 16 screw with a washer and a wire loop. (2) Add 1 kg steps at the long end (= 49 N at the insert) every 15 s. (3) Stop at pull-out or at 20 kg (981 N at the insert). (4) Three inserts per material.
- **Data.** Pull-out force per insert; failure mode.
- **Pass.** Minimum ≥ 300 N in PETG and ≥ 400 N in PA6-CF (EST: 10 × the 30.7 N full-thrust pull of one lift unit if a single screw carried it, `results.json struct.Tmax`; the PA6-CF figure adds margin for the motor mount's 0.6 N·m screw preload, hardware-spec J01).
- **Predicted.** — (not published).
- **Risk.** Lever rig slips: use a cleat under the coupon and keep hands clear.
- **Duration** 1 h. **Crew** 2. **Prereq.** C02.

![**Figure C03.** Heat-set insert pull-out, PETG and PA6-CF: set-up rendered from the CAD model (test gear illustrative).](figures/t_c03.svg)

#### C04 — Motor-floor crush and relaxation (PA6-CF)
- **Objective.** Confirm the 4.5 mm PA6-CF motor floor holds a 0.6 N·m screw preload for 24 h (hardware-spec M3), with the rev B Ø7.5 counterbore and Ø7.0 washer (`cad/README.md` fasteners).
- **Procedure.** Torque an M3 × 8 with washer to 0.6 N·m (0.61 kg at L = 100 mm) through the coupon floor (printed with the Ø7.5 counterbore) into an aluminium nut plate; mark the head; wait 24 h at room temperature and again after 1 h at 60 °C EST in a sunny car or by a heat gun with the IR thermometer; re-apply 0.6 N·m and measure the angle turned.
- **Pass.** Re-torque angle ≤ 30° (hardware-spec M3); washer seats flat in the Ø7.5 counterbore with no edge contact.
- **Predicted.** — (PA6-CF compressive creep not published).
- **Duration** 0.5 h + 24 h. **Crew** 1. **Prereq.** C01.

![**Figure C04.** Motor-floor crush and relaxation (PA6-CF): set-up rendered from the CAD model (test gear illustrative).](figures/t_c04.svg)

#### C05 — Tube receipt measurement and joiner fit
- **Objective.** Verify the three 6061-T6 tube sizes against the fit table FT01–FT04 (hardware-spec §5b) before cutting.
- **Procedure.** (1) Calipers: OD at 3 points along each tube, wall at both ends; record. (2) Slide the 0.875 in joiner into both 1.000 × 0.058 in socket tubes by hand. (3) With one socket clamped, measure the free-end play of the joiner at 0.76 m: lever the tip and read the vertical movement with a ruler. (4) Check leg (FT03) and splice plug (FT04) fits.
- **Pass.** OD within ± 0.102 mm and wall within ± 0.051 mm of nominal (hardware-spec §5a); joiner enters by hand (diametral clearance −0.076 to +0.534 mm, FT01); wingtip-equivalent play ≤ 5 mm at 1.2 m (`docs/research/budget-airframe.md` M4). Tight: lap. Loose > 0.30 mm: one tape wrap (FT01 action).
- **Predicted.** Nominal clearance 0.23 mm (`cad/README.md` joiner).
- **Duration** 1 h. **Crew** 1. **Prereq.** Order B received.

![**Figure C05.** Tube receipt measurement and joiner fit: set-up rendered from the CAD model (test gear illustrative).](figures/t_c05.svg)

#### C06 — Thrust-stand build and calibration (review T1, accuracy 2 % of reading)
- **Objective.** Calibrate the 20 kg load cell + HX711 + Arduino Nano stand (BOM "Test & safety") so lift and pusher thrust are trusted to ± 2 % of reading at the hover point.
- **Setup.** Pivot-beam stand: motor on one arm, load cell under the other, arms equal (1:1) so thrust = cell reading; the watt meter in the pack lead; a servo tester or the FC in motor-test mode drives the ESC (DShot150 per `firmware/vtol_c0.param` §3; for a servo tester use the ESC's PWM mode). Water jugs as masses: 1.00 L = 0.998 kg at 20 °C; verify each jug on a kitchen scale.
- **Procedure.** (1) Zero. (2) Load 0, 0.5, 1, 2, 3, 5, 10 kg (use the jug positions on the arm so the moment arm equals the motor's). (3) Read the HX711 at each step, up and down. (4) Fit a line; record gain and offset in the Nano sketch. (5) Repeat after 10 min powered to check drift. (6) Tare with the motor and prop fitted.
- **Pass.** Error ≤ 2 % of reading from 0.5 to 5 kg and ≤ 2 % FS (0.4 kg) above (review T1 "2 % FS" superseded: 2 % FS = 400 g is 22 % of the 1,859 g hover point, `sized.Tunit_g` 1,858.9 *(calc)*). Hysteresis ≤ 1 %. Drift ≤ 20 g over 10 min.
- **Predicted.** HX711 24-bit on a 20 kg cell: resolution ≪ 1 g; linearity is set by the stand geometry (EST).
- **Risk.** Stand flexes under 3 kgf: brace it; re-check calibration with the motor arm loaded by a jug at the motor station.
- **Duration** 4 h build + 1 h. **Crew** 2. **Prereq.** Order A received.

![**Figure C06.** Thrust stand for C06 and C07: the lift unit on one arm of a 1:1 pivot beam, the load cell under the other, so thrust equals the cell reading (render of the real motor, mount and prop; the stand is illustrative).](figures/thrust_stand.svg)

#### C07 — Lift motor thrust curve, every motor (review T2, R13 strict)
- **Objective.** Measure thrust, current, voltage and electrical power vs throttle for each of the 5 X4110S motors (4 lift + pusher; no spare in the BOM) with the JeeFly 1755 prop and a LANRC BLHeli_S 45A ESC on the flight pack, and derive the hover operating point and FM·η.
- **Setup.** C06 stand; watt meter in the pack lead; IR thermometer; throttle in 10 % steps from 20 to 100 % (10 points), 5 s dwell, 20 s rest; pack voltage ≥ 24.0 V (4.0 V/cell) at the start and the 100 % point repeated at 22.2 V to match the maker table voltage.
- **Procedure.** (1) Tare. (2) Step throttle; log thrust, V, A, W at each dwell. (3) Note the throttle at 1,859 g (hover, `sized.Tunit_g`) and 3,130 g (maker max). (4) 100 % for 10 s: record max thrust and current. (5) IR temperature of the can after the sweep. (6) Repeat for every motor, same ESC; then one motor on each of the other ESCs.
- **Data.** 10-point table per motor; reduce with `docs/test/analysis/thrust_stand.py` (fits T = a·thr^b and P_elec vs T, reports throttle at hover, FM·η at hover, and `Q_M_THST_EXPO` fit).
- **Pass.** Max thrust ≥ 2.98 kgf per motor at 22.2 V (R13: 1.6 × 7.438 kg / 4 = 2.975 kgf *(calc, `sized.m`; the 1.6 is R13's minimum hover T/W, T-Motor VTOL propulsion guide, `docs/DESIGN-BASIS.md` R13)*); electrical power at 1,859 g ≤ 339 W per motor (= 1,359 W / 4, rounded down; 1,359 W is the hover power at which 10 min cruise at the sizing's 295.6 W at 18 m/s is no longer available: (0.8 × 144.3 × 0.95 − 295.6 × 600/3600) × 3600 / 160 s *(calc, `results.json base`, `sized.P_cruise`)*); motor-to-motor spread at hover ≤ 5 % in thrust at equal throttle; max current ≤ 36 A (80 % of the 45 A ESC rating, EST).
- **Predicted.** Maker table at 22.2 V, 17 × 5.8: 1,500 g / 8.1 A / 180 W; 2,000 g / 13.1 A / 291 W; 3,130 g / 27.7 A / 615 W (`docs/research/budget-lift.md` A3). Sizing hover point: 1,859 g at 283.0 W, FM·η 0.505 (`sized.Tunit_g`, `P_hover_per_motor`, `FMeta`); ideal power 130.0 W = T^1.5 / √(2 ρ A), A = 0.1464 m² (`sized.Pi_unit`, `sized.A`). Expected hover throttle ≈ 0.59 = 1,859 / 3,130 *(calc)*. The 17 × 5.5 JeeFly is not the maker's 17 × 5.8 (`docs/purchasing/C0_BOM.csv`): expect a few % less thrust at equal power (EST); the 2.98 kgf pass line is 5 % under the maker's 3.13 kgf, so a 17 × 5.5 shortfall above 5 % fails R13.
- **Risk.** ESC desync at full throttle on DShot150: lower `Q_M_SPIN_MIN`, check ESC timing in BLHeli configurator. Prop strike: cage the stand.
- **Duration** 0.5 h per motor, 4 h total. **Crew** 2. **Prereq.** C06.

![**Figure C07.** Lift motor thrust curve, every motor: set-up rendered from the CAD model (test gear illustrative).](figures/t_c07.svg)

#### C08 — Hover-duty heat (review T3, expanded)
- **Objective.** Validate the lift-unit thermal model (`docs/research/thermal.md` §6.1) and the lumped motor model (`cad/sim/thermal/results.txt val_motor_T90_lumped`), and replace the 20 % loss estimate that sets every lift-unit temperature (thermal.md §6.1 sensitivity) with a measured rise and time constant.
- **Setup.** C06 stand; thrust held at 1,859 g (hover, `sized.Tunit_g`) by throttle; IR thermometer on the motor can (bell) and ESC heat-shrink every 15 s; ambient logged.
- **Procedure.** (1) Start at ambient. (2) Hold hover thrust 90 s, reading temperatures every 15 s. (3) Cool with the prop at idle until the can is within 5 K of ambient (EST; a run started warm adds most of its excess to the peak, so runs from 45 °C are not comparable). (4) Repeat 3 times. (5) One run of 3 × 90 s with only 30 s rests (worst case, never flown) to find the limit. (6) Fit the time constant.
- **Pass.** From a start at ambient, the rise above ambient after 90 s is ≤ 52 K on the can and ≤ 42 K on the ESC *(calc: the rises at which the model's mission peak reaches the 80 °C / 70 °C EST limits at the 25 °C R21 ceiling: 47.8 K × 55 / 50.2 and 34.6 K × 45 / 36.7, all temperatures scaling with the loss; `cad/sim/thermal/results.txt` lift_hover90 and lift_mission_max)*; can ≤ 80 °C and ESC ≤ 70 °C EST absolute; no ESC cut-out; measured time constant ≥ 100 s (review M[simulation].2: under 100 s invalidates the lumped model). **Above 52 K / 42 K** the R21 field ceiling for flights with a transition drops to 80 − 50.2 × (measured can rise / 47.8) °C (and the ESC equivalent, 70 − 36.7 × (rise / 34.6)), whichever is lower, until the thermal model is re-run with the measured loss *(calc)*.
- **Predicted.** Lift-unit model (`docs/research/thermal.md` §6.1; SOLIDWORKS transient, motor + PA6-CF mount + boom + ESC in prop wash, 56.6 W = 20 % of 283.0 W per motor EST, ESC 4 % EST, re-run 2026-11-02): rise above ambient at 30 / 60 / 90 s **can +18.7 / +34.2 / +47.8 K, ESC +13.9 / +25.3 / +34.6 K** (73 °C / 60 °C at 90 s at the 25 °C R21 ceiling, 68 °C / 55 °C at 20 °C; `cad/sim/thermal/results.txt` lift_hover30/60/90); the can crosses 80 °C at ≈ 108 s, the ESC is at 67 °C after 120 s of continuous hover; τ ≈ 257 s *(calc: −120 / ln(1 − 59.7 / 160.1), the 120 s rise over the 160.1 K steady rise)*. Motor-only lumped check 88.2 °C at 90 s from the `cad/Sim.cs` 35 °C ambient (53.2 K rise, τ 205.7 s, c 470 J/kgK EST; `val_motor_T90_lumped`), i.e. 78.2 °C from 25 °C; steady upper bound 185.1 °C at 25 °C (`lift_steady_Motor`, never reached).
- **Duration** 2 h. **Crew** 2. **Prereq.** C07.

![**Figure C08.** Hover-duty heat: set-up rendered from the CAD model (test gear illustrative).](figures/t_c08.svg)

#### C09 — Pusher thrust curve, X4110S + APC 14 × 8.5EP (review T4, expanded)
- **Objective.** Static thrust and current of the pusher set; set `TKOFF_THR_MAX`, confirm the transition current budget, and confirm `THR_MAX` 85 by **bench measurement M1** (pusher power at full pack).
- **Setup.** C06 stand with the pusher adapter (M6 bolt-on, hardware-spec J03b); throttle 20–100 % in 10 % steps. **M1:** a pack at ≥ 25.0 V (full charge); 100 % for ≤ 3 s, then 85 % (`THR_MAX`) for 10 s; record W, A, V, thrust and the can temperature by IR.
- **Pass.** Static thrust ≥ 1.5 kgf at 60 % throttle (review T4); peak current ≤ 40 A (review M[propulsion].3; above that drop to a 13 × 8 prop); prop runout by eye < 1 mm at the tip (FT10 spin check); M1: electrical power at `THR_MAX` on a full pack ≤ 615 W (X4110S rating at 22.2 V, `docs/research/budget-lift.md` A3), else lower `THR_MAX` and re-check the level speed at full throttle ≥ `AIRSPEED_MAX` 25 m/s in F08.
- **Predicted.** — (no vendor table for 14 × 8.5EP on the X4110S, `docs/research/pusher-battery-servo.md` §1b). Cruise thrust needed 8.38 N = 0.85 kgf at 18 m/s (sizing, `sized.D_cruise`) or 7.32 N = 0.75 kgf (aero build-up, `aero_results.json drag.cruise.D_N`); P_cruise 295.6 W / 13.3 A (sizing) or 258.2 W / 11.6 A (aero) at η_prop 0.6 EST (`sized.P_cruise`, `sized.I_cruise`, `aero_results.json mission`). C0 flight model (`firmware/sitl/c0_physics.py --validate`, 2026-11-02, APC 14 × 8.5 data, EST motor model): cruise 200 W at η_prop ≈ 0.74; static 3.35 kgf at 626 W / 28.2 A on 22.2 V; ≈ 890 W at 100 % on 25.2 V, so `THR_MAX` 85 ≈ 547 W (est., throttle³ scaling, `firmware/vtol_c0.param`). Pusher can 76 °C after 600 s of cruise at 25 °C (thermal.md §6.3; loss 33.2 W EST).
- **Duration** 1 h. **Crew** 2. **Prereq.** C06.

![**Figure C09.** Pusher thrust curve, X4110S + APC 14 × 8.5EP: set-up rendered from the CAD model (test gear illustrative).](figures/t_c09.svg)

#### C10 — Stopped-prop behaviour and drag (review T5 + §[iterations] M1)
- **Objective.** Confirm an unpowered lift prop does not windmill at cruise speed and measure its drag.
- **Setup (zero-cost).** Motor + prop on a mast on a car roof rack (or held out of a window on a 1 m pole by a passenger — only on a closed lot), unpowered, 18 m/s = 65 km/h = 40 mph *(calc: 64.8 km/h, 40.3 mph)* by the car speedometer; phone video; for drag, the unit on a pivot arm with a luggage scale (Gaps) or the HX711 load cell reading the arm force.
- **Pass.** No windmilling (review T5); prop stops ≤ 30° from the airflow direction (review M[iterations].1); drag ≤ 0.8 N per stopped unit EST (model 0.44 N at 18 m/s = ½ × 1.225 × 18² × 0.00222 with CdA_rotor 0.00222 m², `aero_results.json drag.CdA_per_rotor_unit` *(calc)*; `docs/research/aerodynamics.md` M3: ΔP > 60 W across four units means the prop Cd EST is low and a prop-parking scheme is needed).
- **Risk.** Road safety: closed lot, driver only drives, ≤ 65 km/h.
- **Duration** 1 h. **Crew** 3. **Prereq.** C07.

![**Figure C10.** C10 set-up: one unpowered lift unit on a pivot arm above the roof rack; the luggage scale reads the drag while the camera records where the prop parks.](figures/car_roof.svg)

#### C11 — Battery capacity, sag and internal resistance
- **Objective.** Measure usable energy, voltage sag at hover and transition current, and per-cell internal resistance of both Ovonic 6S 6500 packs.
- **Setup.** Discharge load = two lift motors on the C06 stand or the tied-down airframe at a constant current near cruise (15 A, above `sized.I_cruise` 13.3 A at 18 m/s, so conservative for capacity EST; review M[mass].4 said 16 A) with the watt meter logging Wh, V, A; the IR thermometer on the pack; cell voltages by the charger's balance readout at rest.
- **Procedure.** (1) Full charge (4.20 V/cell). (2) Rest 30 min; record resting V. (3) Discharge at 15 ± 2 A until 3.50 V/cell under load (21.0 V); log Wh, Ah, V every 30 s (watt meter readout on phone video). (4) At 50 % delivered Ah, pause and apply a 10 s step to 54 A (hover at the loaded-pack voltage, `sized.I_hover_loaded` 53.9 A = 1,131.9 W / 21.0 V) and a 3 s step to 82 A (transition, `sized.I_trans` 82.1 A = 1,723 W / 21.0 V, EST): record V before and during. Two motors on the stand reach about 55 A at most (2 × 27.7 A, maker table), so the 82 A step needs all four lift motors on the tied-down airframe (G03 restraint) or a second stand. (5) Rest 30 min; record recovery voltage and pack temperature. (6) Recharge, log mAh returned. (7) Reduce with `docs/test/analysis/battery_test.py`.
- **Pass.** Delivered ≥ 110 Wh from 4.20 to 3.50 V/cell at 15 A (0.8 × 144.3 × 0.95 = 109.7 Wh *(calc)*: the energy the sizing assumes usable before the 20 % reserve); sag ≥ 3.37 V/cell at 54 A (3.70 − 54 × 0.0060: the 6.0 mΩ/cell acceptance restated, rev 2026-11-02) and ≥ 3.2 V/cell at the 82 A step (review M[propulsion].4); **per-cell internal resistance ≤ 6.0 mΩ** (R_cell = ΔV_pack / (6 × ΔI) from the 54 A step *(calc)*; the acceptance limit the thermal model runs at, `analysis/thermal/thermal_inputs.py` R_cell, so that the pack ends a full mission at 25 °C (R21) at 53 °C, 7 K under the 60 °C limit, `docs/research/thermal.md` §6.2; a pack above 6.0 mΩ/cell does not fly F11/F12) — write the measured value on the pack label; pack ≤ 60 °C EST after discharge; both packs within 3 % of each other. Note: from a 3.70 V/cell rest the sag line at 54 A is met only up to 5.6 mΩ/cell *(calc: (3.70 − 3.40) / 53.9 A)*, so the sag line, not the 6.0 mΩ limit, may decide (§12 item 18).
- **Predicted.** 144.3 Wh nameplate (`packs[0].Wh`); loaded-pack voltage 21.0 V at hover (`firmware/vtol_c0.param` BATT_LOW_VOLT comment); mission needs 99.6 Wh at the load (`sized.E_Wh`), 104.8 Wh from the pack (99.5 / 0.95 *(calc, `base.etaBatt`)*), landing at 27 % of nameplate *(calc: (144.3 − 104.8) / 144.3 = 27.4 %)*. Pack temperature rise over a full mission ≈ 4.7 K per mΩ/cell in the sealed bay *(calc: 28.2 K at 6.0 mΩ/cell, `pod_mission_max_Battery` 53.2 °C from 25 °C, thermal.md §6.2)*; with the battery-bay vents (BUILD-MANUAL 8.2a) about 48 °C at touchdown from 25 °C at 6.0 mΩ/cell (thermal.md §6.4 item 1, EST).
- **Risk.** Over-discharge: watch 3.5 V/cell; LiPo bag under the pack.
- **Duration** 2 h per pack. **Crew** 2. **Prereq.** C06.

![**Figure C11.** Battery capacity, sag and internal resistance: set-up rendered from the CAD model (test gear illustrative).](figures/t_c11.svg)

#### C12 — Servo torque, speed and centering (EMAX ES3005HV × 5, no spare)
- **Objective.** Confirm each of the five flight servos (2 ailerons, elevator, 2 rudders; `docs/purchasing/C0_BOM.csv`) meets its rating at the FC servo-rail voltage and centres repeatably. The BOM carries no spare servo: a failed servo is replaced from the $145.83 reserve (BOM "Crash reserve left under $2,000").
- **Setup.** Servo on a bench block, 50 mm arm, luggage scale or hanging jug on a string over a pulley (zero-cost: masses only), bench 6.0 V from the FC BEC or a UBEC (hardware kit, BOM); servo tester or FC output.
- **Procedure.** (1) Centre at 1500 µs; mark. (2) Hang masses at 50 mm until the arm stalls (torque = m g × 0.05 m: 8 kg·cm = 0.785 N·m needs 1.60 kg at 50 mm *(calc)*); hold ≤ 2 s to avoid heating. (3) Command ± 45°, measure travel. (4) Return to centre 10 times from each side; measure the arm tip position. (5) Time a 60° sweep by phone video (30 fps).
- **Pass.** Stall ≥ 6.4 kg·cm at 6.0 V (80 % of the 8 kg·cm rating, EST; rating from `docs/research/budget-avionics.md` §6, shop.emax-usa.com checked 2026-10-13); centring repeatability ≤ 1° (≤ 0.9 mm at 50 mm *(calc)*, EST); no buzzing at centre under 1 kg·cm; all five within 10 % of each other.
- **Predicted.** 8 kg·cm at 6.0 V, 10 at 7.4 V (budget-avionics §6). Hinge-moment need: ≤ 4 kg·cm per aileron (review M[controls].3; measured in S07). Pushrods: 2-56 Du-Bro Kwik-Link cut to the CAD lengths (ailerons 48 mm, elevator 40 mm, rudders 102 mm, `cad/mesh/meta.json`; `cad/params.txt` rodAileron / rodElevator / rodRudder); the 5-pack covers five surfaces with no spare pushrod.
- **Duration** 1.5 h. **Crew** 1. **Prereq.** Order B.

![**Figure C12.** Servo torque, speed and centering (EMAX ES3005HV × 5, no spare): set-up rendered from the CAD model (test gear illustrative).](figures/t_c12.svg)

#### C13 — Harness, connector and ESC heating
- **Objective.** Confirm the 12 AWG ESC feeds, 14 AWG pusher/BEC feeds, the AS150U battery plug and the XT60H connectors (BOM) stay cool at hover and transition current.
- **Setup.** Run during G03 (tied-down full-system run); IR thermometer on each connector, the pack lead, each ESC and the FC current-sensor board.
- **Pass.** Any connector or wire ≤ 60 °C EST after 60 s hover current + 10 s transition current; ESC ≤ 70 °C EST; no discolouration.
- **Predicted.** 12.7 A per lift ESC at hover (51.0 / 4 *(calc)*; 13.5 A at 21 V) and ≈ 20.5 A in transition (1,723 W / 4 / 21 V *(calc)*); pack lead 51.0 A hover (53.9 A at 21 V), 82.1 A transition EST for ≈ 20 s (`sized.I_hover`, `I_hover_loaded`, `I_trans`); AS150U 70 A continuous / 140 A for 1 min on 10 AWG (`docs/DESIGN-BASIS.md` R20, Amass datasheet), so the transition peak sits inside the 1 min rating; XT60H 30 A continuous per ESC (`docs/purchasing/C0_BOM.csv`). Lift ESC on the boom in prop wash (BUILD-MANUAL 7.8): 50 °C after a 60 s hover and 62 °C at the mission peak at the 25 °C R21 ceiling (`docs/research/thermal.md` §6.1, 4 % loss EST).
- **Duration** in G03. **Crew** 2. **Prereq.** G03 setup.

![**Figure C13.** Harness, connector and ESC heating: set-up rendered from the CAD model (test gear illustrative).](figures/t_c13.svg)

#### C14 — Tape-skin mass sample (review M[structures].4)
- **Objective.** Check the wing skin mass assumption before the sizing is frozen for the build.
- **Procedure.** Cut a 0.5 m² XPS sample, weigh on the kitchen scale, tape one side as per the build, weigh again.
- **Pass.** ≤ 0.1 kg/m² per side (review M[structures].4); otherwise update `base.wGlass` (0.06 kg/m², `results.json`) and re-run `analysis/sizing.mjs`.
- **Duration** 0.5 h. **Crew** 1. **Prereq.** Foam and tape received.

![**Figure C14.** Tape-skin mass sample: set-up rendered from the CAD model (test gear illustrative).](figures/t_c14.svg)

#### C15 — Prop and hub inspection
- **Objective.** Hub thickness for screw length (hardware-spec M5), balance and runout.
- **Procedure.** Calipers on the JeeFly 1755 and APC 14 × 8.5EP hubs; static balance on a bolt through the hub between two glasses (zero-cost); spin each prop on its motor at 30 % with a card held near the tip to see runout.
- **Pass.** Prop screw engagement 4.5–8.0 mm (hardware-spec M5); balance: no preferred rest position after 3 trials or sanded until so; tip runout < 1 mm by eye.
- **Duration** 1 h. **Crew** 1. **Prereq.** Order A.

![**Figure C15.** Prop and hub inspection: set-up rendered from the CAD model (test gear illustrative).](figures/t_c15.svg)

#### C16 — Gear-clamp F05 M3 × 30 and motor counterbore Ø7.5 first-article fit (new in rev B)
- **Objective.** Confirm the two spec values the CAD changed because they could not be built: F05 is M3 × 30 (its nut and head must clear the leg tube in the gear clamp) and the motor counterbores are Ø7.5 (the Ø7.0 washer does not fit Ø6.5) (`cad/README.md` fasteners; `cad/hardware.json`; `cad/drawings/DBF-DRW-001.PDF` sheet 5).
- **Article.** One printed gear clamp pair (PETG) with a 205 mm leg offcut; one motor-mount upper half (PA6-CF).
- **Procedure.** (1) Fit the leg in the gear clamp socket (FT03) and the F05 M3 × 30 cross-bolt with its nylock: check head and nut clearance to the leg tube and that the bolt passes through the leg's Ø3.4 hole (hardware-spec J07). (2) Torque to 0.5 N·m EST; mark. (3) Motor mount: drop a Ø7.0 washer into each Ø7.5 counterbore; fit an M3 × 8 from inside the bore and measure the tip proud of the 4.5 mm floor (hardware-spec M4). (4) Bolt a motor on and check the screw tip ≤ 3.2 mm proud.
- **Pass.** F05 passes with ≥ 0.5 mm clearance between the nut/head and the leg tube; nylock engages ≥ 2 threads past the nut; washers seat flat in all 4 counterbores; screw tip ≤ 3.2 mm (hardware-spec M4; > 3.3 mm reaches the windings).
- **Predicted.** `cad/verification.txt` "rotation check F05 … box extents x 33.0 mm" (M3 × 30 modelled); 0 cut warnings.
- **Duration** 1 h. **Crew** 1. **Prereq.** C01.

![**Figure C16.** Gear-clamp F05 M3 × 30 and motor counterbore Ø7.5 first-article fit: set-up rendered from the CAD model (test gear illustrative).](figures/t_c16.svg)

#### C17 — Joiner slip fit and joiner-stop retention (new in rev B)
- **Objective.** Verify the rev B change that the joiner is a slip fit (not bonded) in the saddle and sockets, slides out for transport (R4), and is captured by the two printed `Joiner_Stop` discs bonded 300 mm inside the spar sockets (`cad/README.md` wing root; `cad/hardware.json` J11/FT06 "SLIP FIT, NOT BONDED"; `cad/verification.txt` Joiner_Stop 2 × 5.0 g).
- **Procedure.** (1) With the saddle and both wing panels built, slide the joiner through the saddle bores and into both sockets by hand; measure the push force with the kitchen scale (push the joiner end against the scale). (2) Bolt both panels (M5 × 25 per `docs/DESIGN-BASIS.md` rev 2026-11-01, N02 nylock, 0.5 N·m EST, J10). (3) Push the joiner axially from each wingtip end with 10 kg (98 N) by hand on a bathroom scale: the stop disc must hold. (4) Unbolt one panel, slide the joiner out: time it and check the pod transport piece measures ≤ 0.5 m (R4 envelope). (5) Repeat the slide-in/out 10 times; re-measure the push force.
- **Pass.** Joiner enters and leaves by hand with ≤ 5 kg push (EST) and no tape wrap needed beyond FT01's rule; stop discs do not move at 98 N (≥ 2 × the ~50 N EST axial load from a one-wheel landing side load, EST); push force unchanged after 10 cycles (no wear > 0.05 mm on the joiner OD); pod piece ≤ 0.5 m long with the joiner out.
- **Predicted.** FT06 band −0.072 to +0.532 mm (hardware-spec §5b); joiner engagement 0.30 m per side, 13.5 diameters (`struct.engage`, `engageD`).
- **Duration** 1 h. **Crew** 2. **Prereq.** C05, saddle and panels built.

![**Figure C17.** Joiner slip fit and joiner-stop retention: set-up rendered from the CAD model (test gear illustrative).](figures/t_c17.svg)

### 9.2 Series S — structural tests on the built airframe

#### S01 — Wing static proof load (limit load, 3.0 g)
- **Objective.** Prove the wing, joiner, joiner stops, sockets and saddle at limit load and compare tip deflection with the FEA.
- **Article.** Complete wing (both panels on the saddle and joiner, M5 wing bolts torqued to 0.5 N·m EST, hardware-spec J10), no aileron servos needed.
- **Setup.** Wing inverted on two padded supports at the pod width (saddle edges, ≈ 0.1 m each side of centre); ruler or dial gauge at each tip against a fixed reference; sandbags or water jugs (kitchen-scale-weighed, ± 10 g) at six stations per side.
- **Load schedule.** Total 16.8 kg = n × (m − m_wing) = 3.0 × (7.438 − 1.835) *(calc; `sized.m`, `sized.m_wing`; the wing's own 1.83 kg already loads the spar in the inverted position, so this is slightly above 3.0 g at the root — conservative)*. Schrenk spanwise (mean of elliptic and uniform, the loading the sizing and FEA use since 2026-11-02; STR-06: within 1.7 % of the AVL loading of this wing): per side, stations at 0.1 / 0.3 / 0.5 / 0.7 / 0.9 / 1.1 m from centre: 1.59 / 1.56 / 1.51 / 1.42 / 1.29 / 1.03 kg *(calc: Schrenk integral over 0.2 m bins of the 1.2 m semi-span, sum 8.40 kg per side; was elliptic 1.78 / 1.72 / 1.62 / 1.44 / 1.17 / 0.67 kg, which put the tip under-loaded; data sheet `cards/DS-S01.md`)*. Chordwise at 30 % chord (spar line; chord 0.322 m, `cad/params.txt` chord 0.322333).
- **Procedure.** (1) Zero the tip gauges. (2) Load symmetrically in four increments (25, 50, 75, 100 % of schedule), reading both tips each step; listen for cracking; look at the socket foam cover and the saddle bolts. (3) Hold 100 % for 30 s (review M[structures].1). (4) Unload in the same steps. (5) Record residual tip deflection after 5 min. (6) Slide the joiner out and inspect for marks or bow against a straight edge; check the stop discs are still bonded.
- **Pass.** Tip deflection at 100 % ≤ 120 mm (10 % of the 1.2 m semi-span, review M[structures].1); residual ≤ 2 mm EST; no permanent set in the joiner (straightness ≤ 0.5 mm over 0.76 m, EST); no foam crush at the sockets; no bolt loosening; stop discs intact.
- **Predicted.** Spar tip 19.1 mm at 3.0 g, scaled from the FEA 28.7 mm at 4.5 g (`cad/sim/results.txt spar_tip_disp` 28.70 × 3/4.5 *(calc)*; FEA run 2026-11-02 13:19 at the Schrenk root moment 91.0 N·m, `struct.Mroot`). The FEA bonds an idealised joiner (OD = socket ID), so the real wing with 0.23 mm joiner clearance and foam compliance will deflect more; between 19 and 60 mm is the expected band (EST). Root moment at 3.0 g: 60.7 N·m, Schrenk *(calc; `struct.Mroot` 91.03 × 3/4.5)*; joiner stress 129.8 MPa, RF 2.12 on 275 MPa yield (`struct.sigJ` 194.7 MPa × 3/4.5 *(calc)*).
- **Risk.** A failure drops 17 kg of bags: nobody under the wing; pad the floor.
- **Duration** 2 h. **Crew** 3. **Prereq.** C05, C17, wing built.

![**Figure S01.** S01 set-up: the wing inverted on padded supports at the saddle edges, weighed bags along the spar line at six stations per side, a gauge at each tip.](figures/proof_load.svg)

#### S02 — Boom static stiffness (review M[simulation].1)
- **Objective.** Measure boom tip deflection under a known load with the real printed clamp to check the FEA boundary condition.
- **Setup.** One boom clamped in its front and rear wing clamps on the wing (or in a bench fixture using the real clamps); a jug of known mass hung at the front motor station (arm Lb = 0.488 m, `struct.Lb`); ruler/dial gauge at the motor station.
- **Procedure.** Hang 1.0, 2.0, 3.0 kg (9.8–29.4 N, up to the 30.7 N full-thrust case `struct.Tmax`); read deflection each step and after removal.
- **Pass.** Deflection at 3.0 kg ≤ 1.5 × prediction = 4.7 mm (review M[simulation].1 rule; 1.5 × FEA 3.16 mm = 4.73 mm *(calc)*, rounded down); residual 0; no clamp slip (witness line).
- **Predicted.** 3.35 mm hand (P L³ / 3EI, `struct.defl_max`), 3.16 mm FEA at 30.7 N (`cad/sim/results.txt boom_disp_max`, run 2026-11-02 at the arm Lb 0.488 m).
- **Duration** 1 h. **Crew** 2. **Prereq.** Booms built.

![**Figure S02.** Boom static stiffness: set-up rendered from the CAD model (test gear illustrative).](figures/t_s02.svg)

#### S03 — Boom modal tap test (review M[structures].2)
- **Objective.** First bending frequency of each boom with the lift unit fitted, vs the hand 25.9 Hz / FEA 27.75 Hz.
- **Setup.** Aircraft assembled on its gear; phone taped to the motor mount running a free accelerometer logging app (e.g. phyphox, phyphox.org, free; EST adequacy: phone IMU rates 100–400 Hz give ≤ 50–200 Hz bandwidth); tap the motor with a rubber mallet handle.
- **Procedure.** 10 taps per boom, vertical then lateral; export the accelerometer CSV; FFT in the app or with numpy; read the first peak.
- **Pass.** f1 within 21–33 Hz EST (hand 25.9 Hz − 20 % to FEA 27.75 Hz + 20 % *(calc)*) in both planes; and not within ± 15 % of the hover rotor frequency or twice it (review M[structures].2). Hover rpm comes from C07 throttle and the no-load 8,880 rpm × throttle fraction EST (BLHeli_S has no telemetry on these ESCs, —).
- **Predicted.** 25.9 Hz hand at the 0.488 m arm (`struct.fn`), 27.75 Hz FEA (`cad/sim/results.txt boom_f1`, 2026-11-02); a compliant clamp lowers it (`analysis/sizing.mjs` comment on fn).
- **Duration** 1 h. **Crew** 2. **Prereq.** S02.

![**Figure S03.** Boom modal tap test: set-up rendered from the CAD model (test gear illustrative).](figures/t_s03.svg)

#### S04 — Boom clamp and splice slip proof (hardware-spec M7, review M[structures].5)
- **Objective.** Prove the printed clamps and the rear splice do not slip under full thrust or torsion.
- **Procedure.** (1) Torsion: hang 2 kg on a 0.25 m lever (4.9 N·m, hardware-spec M7) from a motor mount, then from the tail clamp; check the paint witness line. (2) Bending: hang 1.5 × Tmax = 46.0 N (4.69 kg *(calc; `struct.Tmax`)*) from the front motor station with the rear free (review M[structures].5); check rotation at the clamps with a protractor app.
- **Pass.** Witness line unmoved; rotation ≤ 1°; no crack (review M[structures].5).
- **Predicted.** Clamp friction capacity about 16 N·m about the boom axis at 0.5 N·m per screw, μ 0.3 EST (hardware-spec J04); clamp moment 15.0 N·m (`struct.Mclamp` 14.98), i.e. the EST capacity has only ≈ 7 % margin, so the S04 torsion test decides; socket shear 12.0 MPa (`struct.tauSock`).
- **Duration** 1 h. **Crew** 2. **Prereq.** C02, booms built.

![**Figure S04.** Boom clamp and splice slip proof: set-up rendered from the CAD model (test gear illustrative).](figures/t_s04.svg)

#### S05 — Motor-mount pull and insert test on real parts
- **Objective.** Confirm the as-printed PA6-CF motor mounts (rev B: upper half with the 4.5 mm floor + lower cap, `cad/README.md` printed clamps) and their inserts hold the motor at full thrust with margin.
- **Procedure.** With a motor bolted to its mount (0.6 N·m, Loctite 242, hardware-spec J01; screws from inside the bore) and the mount clamped on a boom, hang 2 × Tmax = 61.4 N (6.26 kg *(calc)*) from the motor bell in the thrust direction for 60 s; then torque one spare mount's insert to 1.0 N·m to confirm C02 on the real geometry.
- **Pass.** No crack, no insert movement, screws unchanged on re-torque (≤ 30°).
- **Predicted.** Lift unit reaction at full thrust 30.7 N (`struct.Tmax`).
- **Duration** 0.5 h. **Crew** 2. **Prereq.** C02, C03, C16, mounts printed.

![**Figure S05.** Motor-mount pull and insert test on real parts: set-up rendered from the CAD model (test gear illustrative).](figures/t_s05.svg)

#### S06 — Landing-gear drop test (review M[structures].3)
- **Objective.** Show the gear and booms survive the design hard touchdown without yielding (rev 2026-11-01: the design case is 2 × the firmware's final descent speed, `Q_LAND_FINAL_SPD` 0.3 m/s in `firmware/vtol_c0.param`, so 0.6 m/s; the old 0.3 m / 2.4 m/s drop yields the booms and is not a design case).
- **Setup.** Airframe at flight mass (pack fitted, `analysis/results.json` C0 sized.m) with the FC powered and logging (`LOG_DISARMED,1` temporarily) or a phone accelerometer in the bay; level concrete with a 3 mm rubber mat; leg fairings fitted; a straight-edge and feeler gauges for boom straightness before and after.
- **Procedure.** Drops from 10 mm, then 20 mm under the feet (h = v²/2g: 0.6 m/s needs 18.4 mm), three each, released level; after each drop check each boom against the straight-edge at the gear clamp and the paint witness lines on every clamp.
- **Pass.** No permanent bend (straight-edge gap unchanged within 0.1 mm), no clamp slip (witness lines intact), no crack in the gear clamps; peak vertical acceleration at the bay ≤ the predicted front-corner value in `analysis/structures/landing.json` (hard case), since that model treats the clamps as rigid and so over-predicts the force.
- **Predicted.** `analysis/structures/landing.py` → `landing.json` (MTOW 7.4380 kg; boom cantilever from its wing clamp as the spring, 6061-T6 minimum yield 240 MPa): at 0.6 m/s the front corner sees 6.6 g and 123 MPa (RF 1.96), the rear corner 13.5 g and 146 MPa (RF 1.65); at the normal 0.3 m/s touchdown RF ≥ 3.04.
- **Risk.** Damage to the pod: the drop is onto the gear only, pad the pod with foam.
- **Duration** 1 h. **Crew** 2. **Prereq.** S01, gear built.

![**Figure S06.** Landing-gear drop test: set-up rendered from the CAD model (test gear illustrative).](figures/t_s06.svg)

#### S07 — Control-surface hinge moment and joiner/spar post-test inspection
- **Objective.** (a) Measure the aileron hinge moment to size the servo margin (review M[controls].3); (b) inspect the joiner, sockets and saddle after S01 and S06.
- **Procedure.** (a) Spring/luggage scale (Gaps; zero-cost: hang a jug from a string over the trailing edge) on a built aileron at 25 % of its chord behind the hinge with the surface held by the servo at 20° in an 18 m/s stream (car-roof, as C10) or, failing that, static estimate from Ch = ½ ρ V² S_a c_a Ch_δ δ with Ch_δ EST −0.5/rad and the hand calc on the card. (b) Slide the joiner out; straight-edge; look for socket foam crush and saddle bolt witness marks.
- **Pass.** (a) Hinge moment ≤ 4 kg·cm (review M[controls].3, half of 8 kg·cm). (b) No set > 0.5 mm; no crush.
- **Predicted.** — (hinge moment not computed in the repo, `docs/research/pusher-battery-servo.md` caveat 5).
- **Duration** 1.5 h. **Crew** 2. **Prereq.** S01.

![**Figure S07.** Control-surface hinge moment and joiner/spar post-test inspection: set-up rendered from the CAD model (test gear illustrative).](figures/t_s07.svg)

#### S08 — Transport, car fit and two-person carry (R4, R5)
- **Objective.** Demonstrate break-down into the measured car and the assembled carry.
- **Procedure.** (1) Measure the team car's load space (review M[model3d].2). (2) Break the aircraft into its transport pieces (wing panels off the saddle, joiner slid out of the pod piece, booms off at the field breakdown joint — 4 screws per boom, hardware-spec J05; tail off with four screws, `cad/README.md` tail). (3) Load everything with the pack box and tools; close the hatch. (4) Two people carry the assembled aircraft 50 m over grass and set it down; no part touched the ground.
- **Pass.** All pieces fit; longest piece 1.20 m (`geo.longestPiece`) ≤ measured clear length (R4 working envelope 1.5 × 0.5 × 0.4 m, `docs/DESIGN-BASIS.md` R4); pod piece ≤ 0.5 m with the joiner out; carry completed without strain or contact.
- **Duration** 1 h. **Crew** 2. **Prereq.** C17, airframe built.

![**Figure S08.** Transport, car fit and two-person carry (R4, R5): set-up rendered from the CAD model (test gear illustrative).](figures/t_s08.svg)

#### S09 — Built component masses and empty weight (review M[model3d].1)
- **Objective.** Weigh every part as it comes off the bench and the empty airframe, and compare with the sizing mass roll-up and the CAD roll-up.
- **Procedure.** Kitchen scale (5 kg, 1 g) per part; bathroom scale or two kitchen scales for the assembled airframe; log against `cad/verification.txt` "Mass roll-up" (2026-11-01: modelled 6.678 kg incl. pack; fasteners 229.1 g, printed 1,406.1 g, tubes 1,691.3 g, foam 1,228.8 g without skins, vendor 2,123.0 g), the mass budget (`analysis/mass/mass_budget.json`, bottom-up 7.416 kg) and the sizing items (`cg.items`).
- **Pass.** Empty mass without pack ≤ 7.00 kg (= 7.82 − 0.82: the R13 take-off limit of §8 R2 minus the 0.82 kg pack, `pick.kg` *(calc)*); otherwise re-run `analysis/sizing.mjs`. Predicted 6.62 kg (7.438 − 0.82 *(calc)*).
- **Predicted.** Wing 1.833, booms + clamps 0.745, lift units 1.302, tail 0.177, pod 0.567, gear 0.517, avionics 0.418, fasteners and inserts 0.164, pusher set 0.257, servos (5) 0.266, wiring 0.37 EST kg (`cg.items`, calibrated to the CAD roll-up by `analysis/mass/mass_budget.py`).
- **Duration** ongoing. **Crew** 1. **Prereq.** none.

![**Figure S09.** Built component masses and empty weight: set-up rendered from the CAD model (test gear illustrative).](figures/t_s09.svg)

#### S10 — Ballast-mount retention (withdrawn in rev C)
- **Withdrawn 2026-11-02.** There is no payload and no ballast (R12 revised 2026-11-01, §4 rule 7), so nothing in the bay needs a retention test. The ID is kept so the cards and matrix stay aligned. If a payload is ever added (a design change under R12), reinstate this test with that payload's mass.

### 9.3 Series E — electrical and avionics bench tests

All E tests: **props off**, aircraft on a bench, pack through the AS150U plug, fire bag at hand.

#### E01 — Power-up, smoke test and sensor calibration
- **Objective.** First power-up of the integrated avionics; calibrate the FC voltage and current sensors.
- **Procedure.** (1) Continuity and polarity check of the harness with a multimeter (hand tools; Gaps if none). (2) Power through the AS150U plug with the watt meter in line; watch for heat/smoke for 60 s. (3) Idle current. (4) Compare FC `BATT` voltage with a multimeter at the balance lead: set `BATT_VOLT_MULT`. (5) With motors at a steady 20 % (props off, brief) compare FC current with the watt meter at two points: set `BATT_AMP_PERVLT` (`firmware/vtol_c0.param` §9 says to calibrate both).
- **Pass.** Idle current ≤ 1.0 A EST; FC voltage within ± 0.1 V of the meter; current within ± 5 % at ≥ 5 A.
- **Predicted.** Board defaults 11.05 V/V and 64 A/V (`firmware/vtol_c0.param`).
- **Duration** 1 h. **Crew** 2. **Prereq.** C13 harness built, E11.

![**Figure E01.** Power-up, smoke test and sensor calibration: set-up rendered from the CAD model (test gear illustrative).](figures/t_e01.svg)

#### E02 — ESC protocol, motor order, direction and spin thresholds
- **Procedure.** Mission Planner motor test in the ArduPilot order (Motor1 front-right CCW on S5, 2 rear-left CCW on S6, 3 front-left CW on S7, 4 rear-right CW on S8, pusher on S9; `firmware/vtol_c0.param` §2); set direction with DShot commands (`SERVO_DSHOT_ESC,2`) or BLHeli passthrough; find the lowest output that spins every motor (`Q_M_SPIN_ARM`) and that gives a little thrust (`Q_M_SPIN_MIN`) per the tuning guide step 4 (checked 2026-10-21); pusher on S9 responds to throttle only in fixed-wing modes.
- **Pass.** All four lift motors spin in the correct position/direction at the test's 10 % command; `Q_M_SPIN_ARM` ≥ the measured spin threshold + 0.02; no desync at 100 % for 3 s (props off).
- **Predicted.** `Q_M_SPIN_ARM` 0.10, `Q_M_SPIN_MIN` 0.15 (param file defaults).
- **Duration** 1 h. **Crew** 2. **Prereq.** E01.

![**Figure E02.** ESC protocol, motor order, direction and spin thresholds: diagram.](figures/e02_motor_order.svg)

#### E03 — Servo direction, throws and centering on the airframe (5 servos)
- **Procedure.** In MANUAL and FBWA: stick right → right aileron up; stick back → elevator up; rudder right → both rudders (S4 left boom, S11 right boom) trailing edge right; in FBWA roll the aircraft and check surfaces counter the motion. Measure throws with a ruler at the trailing edge; set `SERVOn_MIN/MAX/TRIM/REVERSED`.
- **Pass.** Correct sense on all 5 servos; aileron ± 20° EST, elevator ± 20° EST, rudder ± 20° EST (no repo values, —; typical sport-plane throws); surfaces return to within 1 mm of neutral; no binding at full throw; servo current at full throw ≤ 1 A each EST. Elevator reserve at stall: trim needs about −7.8° elevator at Vs (`aero_results.json stall.trim_at_Vstall.elevator_deg`; −8.0° in the C0 flight model, `c0_physics.py --validate`), so the elevator throw must be ≥ 15° EST.
- **Duration** 1 h. **Crew** 2. **Prereq.** C12, E01.

![**Figure E03.** Servo direction, throws and centering on the airframe (5 servos): diagram.](figures/e03_servo_throws.svg)

#### E04 — RC link: channel map, switches, telemetry and range walk
- **Procedure.** Check AETR on CH1–4, arm CH5, mode CH6 six positions (`FLTMODE1–6`), E-stop CH7, Q_ASSIST CH8, RTL CH9. CRSF telemetry on the handset (battery V/A, mode, GPS, LQ) and, if used, the ELRS MAVLink overlay to Mission Planner (`docs/research/firmware.md` §4 R7/R9: switchable, not simultaneous with CRSF). Range walk: aircraft on the bench outdoors, powered; walk the transmitter 300 m away (the `FENCE_RADIUS`) with LQ/RSSI on the transmitter screen; the second person watches a servo move.
- **Pass.** All switches map; LQ ≥ 90 % EST at 300 m with the antenna vertical; handset telemetry shows battery voltage within 0.1 V of the FC and the mode name; failsafe not triggered.
- **Predicted.** — (ELRS range at the Pocket's output power not in repo).
- **Duration** 1 h. **Crew** 2. **Prereq.** E01.

![**Figure E04.** RC link: channel map, switches, telemetry and range walk: diagram.](figures/e04_range_walk.svg)

#### E05 — Failsafe bench test (hardware portion; SITL portion done)
- **SITL evidence (done 2026-10-21).** `firmware/sitl/results/summary.json`: scenarios B (RC loss in cruise → RTL → QRTL), C (RC loss in hover → QLAND), D (transition timeout 15 s → QRTL), E (low battery → RTL → QRTL), F (fence 110 m → RTL, peak 113.1 m), G (ELRS MAVLink override loss → QLAND) all PASS on ArduPlane 4.7.2; 133 parameters read back equal. **Repeated 2026-10-25 on the C0 airframe model** (`firmware/sitl/c0_physics.py` on SITL's JSON interface; `firmware/sitl/results_c0.json`): 7/7 PASS with `vtol_c0.param` unchanged, 131 parameters checked, none mismatched (`firmware/sitl/README.md` C0 section).
- **Hardware procedure.** Props off, armed in QLOITER on the bench with GPS lock (outdoors): (1) switch the transmitter off → expect QLAND within `FS_LONG_TIMEOUT` 5 s + 1.5 s short; (2) set `BATT_LOW_MAH` temporarily to 6,400 → expect the low action RTL (`BATT_FS_LOW_ACT,1`); `BATT_CRT_MAH` to 6,400 → QLAND (`BATT_FS_CRT_ACT,4`); restore 1,625 / 1,300; (3) set `FENCE_ALT_MAX` to 1 m and lift the aircraft 2 m by hand → fence breach message; restore 110; (4) E-stop CH7 stops all motors at 20 % command; (5) AS150U pull under load.
- **Pass.** Each failsafe produces the configured mode within the timeout; parameters restored and verified with `firmware/tools/check_params.py`.
- **Duration** 1.5 h. **Crew** 2. **Prereq.** E04.

![**Figure E05.** Failsafe bench test: diagram.](figures/e05_failsafes.svg)

#### E06 — SITL rehearsal (review F0, §[flighttest] M1): scripted portion done, pilot portion open
- **Done.** Scripted scenarios A–G passed 2026-10-21 (`firmware/sitl/README.md`; `firmware/sitl/results/`): nominal AUTO mission with VTOL land 0.1 m from home, forward transition 10 s, "Transition airspeed reached 16.0" 5 s after start. Attitude-tracking RMS 0.67°/0.62° (VTOL), 4.5°/1.7° (fixed wing). **C0 airframe model, 2026-10-25** (`firmware/sitl/results_c0.json`): 7/7 again; scenario A forward transition 13 s / 144 m with no altitude loss, 17.5 m/s at "Transition done", peak 70.6 A; back-transition 7 s / 34 m with 1.7 m altitude loss and a −17°/+33° pitch swing (the airbrake phase pitches to the 30° VTOL limit and stalls the wing); VTOL land 0.0 m from home. **Re-run 2026-10-27 at the 18 m/s cruise** (`AIRSPEED_CRUISE` 18): 7/7; scenario A forward transition 15 s / 166 m, 16 m/s 10 s after start, no altitude loss, peak 55.8 A; back-transition 4 s / 29 m, no altitude loss, 79 A peak, −18°/+33° pitch swing; VTOL land 0.0 m from home. The 15 s transition sits at the ≤ 15 s pass line of F07 and the 166 m distance is above the 100 m line, as the 144 m of the 20 m/s run was: the turn-at-once rule (§7) stands.
- **Open.** (1) Each pilot hand-flies the **C0 airframe model** (`firmware/sitl/run_c0_sitl.ps1`, Mission Planner on TCP 127.0.0.1:5760; the generic QuadPlane only if the model will not start) with the Pocket Crush as a joystick: three back-transitions from 18 m/s to see the airbrake pitch-up (F06–F13 watch item), QLOITER take-off, FBWA transition from the upwind edge with an immediate turn, failed transition (throttle low → QRTL), RC loss in cruise, RC loss in hover, low battery, fence; (2) `SIM_ENGINE_FAIL` on one lift motor in hover (documents the R14 limitation; not in the A–G set).
- **Pass.** Every pilot recovers a failed transition and a pusher-out without ground contact in 3 of 3 attempts and keeps inside the 300 m fence after a transition (review M[flighttest].1: a pilot who cannot does not fly F06–F12).
- **Duration** 2 h per pilot. **Crew** PIC + GCS. **Prereq.** E11.

#### E07 — Compass and GPS calibration
- **Procedure.** Outdoors, away from steel; Mission Planner compass calibration (`COMPASS_AUTO_ROT,2` detects the external compass orientation); accelerometer calibration; check HDOP and satellite count after 2 min; heading vs a phone compass at 4 headings.
- **Pass.** Calibration fitness "good"; heading error ≤ 10° at all four headings EST; HDOP ≤ 1.5, satellites ≥ 10 EST; no "compass inconsistent".
- **Duration** 0.5 h. **Crew** 1. **Prereq.** E01.

![**Figure E07.** Compass and GPS calibration: diagram.](figures/e07_compass_cal.svg)

#### E08 — Airspeed sensor bench check (RMRC MS4525DO at 0x28)
- **Procedure.** The RMRC MS4525DO answers at I²C 0x28, so it does not clash with the onboard SPL06 baro at 0x76 and needs no address strap (`firmware/vtol_c0.param` ARSPD_TYPE 1 comment; `docs/research/bom-savings.md`; it replaces the Holybro MS5525DSO). On the bench: confirm the baro and the airspeed sensor are both detected (no "ARSPD: no sensor found", baro healthy); pitot fitted (hardware-spec J16); cover and uncover, blow gently: reading ≥ 6 m/s (ArduPilot airspeed calibration page, checked 2026-10-21); zero with the tube covered; leak check.
- **Pass.** Both sensors detected on bus 0; static reading 0 ± 1 m/s; blow test ≥ 6 m/s; reading holds for 10 s with the pitot sealed.
- **Duration** 0.5 h. **Crew** 1. **Prereq.** E01.

![**Figure E08.** Airspeed sensor bench check (MS4525DO at 0x28): set-up rendered from the CAD model (test gear illustrative).](figures/t_e08.svg)

#### E09 — Bench vibration and ESC thermal soak (tied-down, props on)
- Runs as part of G03; recorded separately. **Pass.** VIBE X/Y/Z < 30 m/s² and clipping = 0 during a 60 s hover-throttle run (ArduPilot vibration page, checked 2026-10-21); ESC ≤ 70 °C EST.

![**Figure E09.** Bench vibration and ESC thermal soak (tied-down, props on): set-up rendered from the CAD model (test gear illustrative).](figures/t_e09.svg)

#### E10 — Telemetry links
- **Procedure.** (1) CRSF telemetry on the handset: confirm the sensors listed (battery, GPS, mode, LQ/RSSI) during the E04 range walk. (2) ELRS MAVLink overlay (if enabled on the RX/TX): Mission Planner connects; note that RC then arrives as `RC_CHANNELS_OVERRIDE` and that loss → QLAND (SITL G). (3) CoreWing BLE/WiFi (`SERIAL1_PROTOCOL,2`): bench link only; measure the drop-out range by walking away.
- **Pass.** Handset telemetry present at 300 m (E04); MAVLink overlay, if used, holds a GCS link at ≥ 300 m EST; BLE/WiFi range recorded (expected tens of metres, —).
- **Predicted.** — (ELRS MAVLink range not in repo). No SiK radio is planned (`docs/research/firmware.md` §4 R9).
- **Duration** 0.5 h. **Crew** 2. **Prereq.** E04.

#### E11 — Firmware and parameter inspection (R17)
- **Procedure.** Flash ArduPlane 4.7.2 stable for CoreWingF405WingV2 (`firmware/vtol_c0.param` header: firmware.ardupilot.org/Plane/stable/CoreWingF405WingV2, checked 2026-10-21); load `firmware/vtol_c0.param` twice (Q_ENABLE reboot, per its header); run `firmware/tools/check_params.py`; record the firmware version string and git hash. The 2027-02-22 beta go/no-go is closed (stable 4.7.2 includes the target, `docs/research/firmware.md` §4 R20); the date stays as the integration milestone.
- **Pass.** Firmware is a stable release with QuadPlane; zero parameter mismatches (SITL read-back of 133 parameters was equal); all arming checks enabled (`ARMING_SKIPCHK,0`).
- **Duration** 1 h. **Crew** 1. **Prereq.** FC received.

#### E12 — Remote ID check (R18)
- **Procedure.** Look up the BeeID serial at uasdoc.faa.gov (review M[schedule].3); power the module; confirm broadcast with a free Remote ID receiver app on a phone (e.g. OpenDroneID OSM, free, Android) showing the serial and position.
- **Pass.** Serial listed; broadcast received at 30 m EST.
- **Duration** 0.5 h. **Crew** 1. **Prereq.** BeeID received, registration done.

![**Figure E12.** Remote ID check (R18): set-up rendered from the CAD model (test gear illustrative).](figures/t_e12.svg)

### 9.4 Series G — ground tests on the complete aircraft

#### G01 — Weight and balance (review M[cg].1)
- **Procedure.** Two kitchen scales at known stations: the front legs and the rear legs each on a board across one scale (Figure G01), or one scale and a pivot. Weigh with the pack and nothing in the bay (no ballast, §4 rule 7); compute CG from the moments. Mark the CG target on the pod. Move the pack to bring the CG within 2 cm of the thrust centroid.
- **Pass.** Take-off mass ≤ 7.82 kg (R2 line, §8); CG at 28 ± 2 % MAC (target `cg.pct.target` 28; ± 2 % MAC = ± 6.4 mm *(calc, MAC = chord 0.3223 m)*) with no ballast; CG never aft of 30.4 % MAC (= neutral point 38.4 % − 8 % SM, `aero_results.json neutral_point.AVL_pod_pct_MAC` 38.40, review M[cg].1 rule *(calc)*); CG within 20 mm of the thrust centroid at x = −0.0903 m from the LE (`cg.thrustCentroid`).
- **Predicted.** Take-off mass 7.44 kg (`sized.m`); CG at 28 % MAC with the pack at x = 0.255 m (`cg.xb`), 27.0–29.0 % MAC over ± 30 mm of pack travel (`cg.pctFwd`, `pctAft`); static margin 10.4 % at 28 % (AVL with pod, `aero_results.json`; 10.41 % in `c0_physics.py --validate`), 10.2 % by the sizing (`geo.SM`).
- **Duration** 1 h. **Crew** 2. **Prereq.** S09, avionics fitted.

![**Figure G01.** G01 and G09: the front legs and the rear legs each on a board across one kitchen scale; the CG follows from the two readings and the two gear stations.](figures/cg_weigh.svg)

#### G09 — CG versus pack station (rev C: replaces the ballast check)
- **Objective.** Confirm that the pack alone sets the CG with no ballast (R12 revised 2026-11-01; `results.json cg`), and map the CG against the pack station so the field crew knows how far the pack may sit from its mark.
- **Procedure.** Repeat G01 with the pack (1) at its mark x = 0.255 m, (2) 30 mm forward, (3) 30 mm aft; record the pack station and CG for each.
- **Pass.** CG 28 ± 2 % MAC at the mark; all three points inside 26–30 % MAC and none aft of 30.5 % MAC (G01 rule); the pack mark and its ± tolerance written on the pod and on every flight card.
- **Predicted.** 28.0 / 27.0 / 29.0 % MAC (`cg.pct.target`, `cg.pctFwd`, `cg.pctAft`): ± 30 mm of pack moves the CG ± 3.3 mm *(calc: (−0.08695 − (−0.09356)) / 2 m, `cg.cgBattFwd`, `cgBattAft`)*; static margin 11.4 / 9.4 % at the forward / aft points (`aero_results.json neutral_point.static_margin_pct`).
- **Duration** 0.5 h. **Crew** 2. **Prereq.** G01.

![**Figure G09.** CG versus pack station: set-up rendered from the CAD model (test gear illustrative).](figures/t_g09.svg)

#### G02 — Hand-carry sensor sanity walk
- **Procedure.** Powered, disarmed, logging on (`LOG_DISARMED,1` temporarily): carry the aircraft 50 m and back at walking speed, pitch and roll it ± 30° by hand; watch the handset/GCS HUD, airspeed and EKF.
- **Pass.** Attitude follows within 5°; GPS track matches the walk; no EKF or compass warnings; airspeed stays < 3 m/s.
- **Duration** 0.5 h. **Crew** 2. **Prereq.** E07, E08.

#### G03 — Full-system tied-down run (review T6, expanded; includes C13, E09)
- **Objective.** All four lift motors and the pusher under load on the airframe: pack sag, harness heat, vibration, EMI, and the pitch/roll authority check.
- **Setup.** Aircraft strapped to a heavy bench or to ground stakes by the landing-leg clamps with ≥ 4 ratchet or rope ties rated ≥ 50 kg each (total restraint > 4 × 3.13 kgf = 12.5 kgf, `budget-lift.md` A3); props on; everyone ≥ 5 m away behind a barrier; watt meter in line; IR thermometer; logging.
- **Procedure.** (1) Arm in QSTABILIZE; raise throttle to the C07 hover throttle (~59 %, §C07) for 60 s; (2) 3 s at 100 % on all four (review M[propulsion].4 burst); (3) in FBWA, pusher to 100 % for 10 s (G06 may be combined); (4) full transition current: hover throttle plus pusher 75 % (`TKOFF_THR_MAX`) for 10 s; (5) read temperatures within 30 s; (6) download the log.
- **Pass.** Pack ≥ 3.4 V/cell at hover draw and ≥ 3.2 V/cell in the burst (review T6, §[mass] M1); hover current 51.0 A ± 15 % EST at 22.2 V (53.9 A at 21 V); transition current ≤ 85 A (`Q_M_BAT_CURR_MAX`; the 82.1 A estimate is only 3 A under it, §12 item 19); VIBE < 30 m/s², clipping 0; motors/ESCs/connectors within the C08/C13 limits; no desync; no loose fasteners after (witness marks).
- **Predicted.** 51.0 A hover at 22.2 V, 53.9 A at 21 V, 82.1 A transition EST (`sized.I_hover`, `I_hover_loaded`, `I_trans`).
- **Risk.** Restraint failure: tie to the leg clamps not the legs; check knots; nobody in the rotor plane.
- **Duration** 2 h. **Crew** 3. **Prereq.** S04, E02, E03, E05, G01.

![**Figure G03.** Full-system tied-down run: set-up rendered from the CAD model (test gear illustrative).](figures/t_g03.svg)

#### G04 — Compass interference (compassmot) check
- **Procedure.** During G03 step 1, run Mission Planner's CompassMot with the throttle raised to hover; or read the compass field change in the log (`MAG` vs `RCOU`).
- **Pass.** Interference ≤ 30 % EST (the ArduPilot compassmot page returned HTTP 404 on 2026-10-21; 30 % is the figure commonly quoted by that page — treat as EST until re-checked); heading change < 10° between idle and hover throttle.
- **Duration** in G03. **Prereq.** E07.

#### G05 — Tethered hover (review F2)
- **Setup.** Two 4 m tether lines to the leg clamps from stakes 3 m apart, slack to 1.5 m; grass; crew 10 m away; wind ≤ 3 m/s EST; no ballast (§4 rule 7).
- **Procedure.** QSTABILIZE: arm, throttle up slowly until light on the gear, back down (ArduPilot step 5 lift-off check); then lift to 1 m, hold 30 s, land. Then QHOVER, 1 m, 30 s. Three cycles, motors cooled < 45 °C between (review F3).
- **Pass.** 30 s stable at 1 m; attitude error < 15°; lift output < 60 % (review F2); VIBE < 30; no oscillation; tether never taut.
- **Predicted.** Hover throttle ≈ 0.59 (1,859 / 3,130 *(calc)*).
- **Duration** 2 h. **Crew** 4. **Prereq.** G03, G04, G09, flight request approved, I02.

![**Figure G05.** G05 set-up: two slack tethers from stakes to the front gear clamps keep the first hovers within a few metres; the crew stays 10 m away.](figures/tethered_hover.svg)

#### G06 — Pusher ground run on the airframe
- **Procedure.** Aircraft tail-tied to a stake through the luggage scale (Gaps; zero-cost: the HX711 load cell in line), nose free to pull: FBWA, throttle 60 % and 100 % for 10 s each; IR temperature on the pusher can and ESC; watch the tail boom stubs and fins for buffet.
- **Pass.** Static pull ≥ 1.5 kgf at 60 % (review T4) on the airframe; current ≤ 40 A; no tail buffet visible; stubs do not flex visibly; pusher prop ground clearance ≥ 40 mm with the aircraft loaded (CAD 44.8 mm, `cad/verification.txt` 2026-11-01).
- **Duration** 0.5 h. **Crew** 3. **Prereq.** C09, G03.

![**Figure G06.** Pusher ground run on the airframe: set-up rendered from the CAD model (test gear illustrative).](figures/t_g06.svg)

#### G07 — Assembly and breakdown time (R5)
- **Procedure.** Stopwatch, two people, from the loaded car to armed pre-flight (review M[model3d].3), including sliding the joiner in and bolting both panels (C17), the booms (4 screws each) and the tail (4 screws); three runs on different days; then breakdown back into the car.
- **Pass.** Median assembly ≤ 15 min; no tool other than the hex keys; witness marks aligned after assembly.
- **Duration** 1.5 h. **Crew** 2. **Prereq.** S08.

![**Figure G07.** Assembly and breakdown time (R5): set-up rendered from the CAD model (test gear illustrative).](figures/t_g07.svg)

#### G08 — Field procedure rehearsal
- **Procedure.** Full dry run of a flight session at the site without arming: set-up, pre-flight checklist, crew calls, abort call, post-flight temperatures, log download, pack change, field charging (review M[flighttest].2: time one full charge at the field supply).
- **Pass.** Checklist completed with no missed item; charge time per pack ≤ 1.5 h (review M[flighttest].2) on the field supply (— source to be found, Gaps).
- **Duration** 2 h. **Crew** 4. **Prereq.** G05 planned.

![**Figure G08.** Field procedure rehearsal: diagram.](figures/g08_field_layout.svg)

### 9.5 Series F — flight tests

All flight tests use the card in `docs/test/cards/`. Common rules: weight and CG per G01/G09 recorded on the card, no ballast (§4 rule 7); field air temperature recorded, ≤ 25 °C for F06–F13 (R21, §4 rule 9); two packs; ≤ 5 m AGL and ≤ 60 s per hover on hover-only flights (R14 mitigation, §10); transitions start at the upwind field edge with an immediate turn (§7); post-flight temperatures within 30 s; logs downloaded and named before the next flight (§10). Hover tests at any approved site; F06 onward at RFS only (R19).

![**Figure 9.5.** The flight-test build-up: each flight only after the one before it passes, from first hops to the full mission.](figures/flight_buildup.svg)

| ID | Title | Review step | Build-up points | Pass criteria (summary; full on the card) | Prereq |
|---|---|---|---|---|---|
| F01 | First lift-off, QSTABILIZE hops | F3 start | lift-off and set down; 1 m hover 10 s; ± 5° roll/pitch inputs | no oscillation; attitude error < 15°; VIBE < 30; clipping 0 | G05 |
| F02 | QHOVER hover-throttle learn and notch log (two 60 s batch-logged hovers) | F3 | 1–3 m, 2 × 60 s with `INS_LOG_BAT_MASK,1`, `INS_LOG_BAT_OPT,4` (`docs/research/firmware.md` D13) | learned `Q_M_THST_HOVER` 0.3–0.6 and ≤ 0.60; FFT peak identified; front/rear output split ≤ 15 % (review M[cg].2) | F01 |
| F03 | QLOITER free hover, 3 × 60 s, thermal | F3 | ≤ 5 m AGL; position hold; 1 m/s translations | hold within 2 m EST; motors ≤ 80 °C; cooled < 45 °C between; hover current 51.0 A ± 15 % at 22.2 V (`sized.I_hover`); predicted can 59 °C / ESC 50 °C after a 60 s hover at 25 °C (thermal.md §6.1) | F02 |
| F04 | Q-mode handling at low forward speed | F4 | box pattern at 5–8 m/s, ≤ 10 m AGL | no unexpected Q_ASSIST; attitude error < 15°; airspeed sensor reads 5–8 m/s ± 2 | F03 |
| F05 | Hover failsafes and R20 demonstration | — | at 20 m AGL EST over the pad: RC off → QLAND; `FENCE_ALT_MAX` temporarily 25 m, climb → RTL; low battery forced → RTL; critical forced → QLAND | each action within timeout; touchdown within 5 m of the pad EST | F04, E05 |
| F06 | Partial transitions (Q_ASSIST on) | F5 | ≥ 30 m AGL from the upwind edge; FBWA with throttle until 12 m/s then back to QHOVER; × 3; watch the back-transition pitch-up (C0 SITL model, ≤ 2 m loss) | airspeed rising within 6 s (review F5); altitude loss ≤ 10 m EST; lift motors re-engage on back-transition | F05, I02 (RFS) |
| F07 | Full transition, circuit, back-transition, QLAND | F6 | after 3 × F06: FBWA to `AIRSPEED_MIN` 16 from the upwind edge, immediate turn, one circuit at 18 m/s, back-transition, QLAND | transition ≤ 15 s and ≤ 100 m (review M[controls].2); turn started ≤ 3 s after "Transition done"; lift outputs at min in cruise (R1); QLAND touchdown ≤ 1 m/s EST | F06 × 3 |
| F08 | Airspeed calibration and cruise performance | F6+ | `ARSPD_AUTOCAL` 5 min circuits; then reciprocal passes (≥ 15 s steady each, ≥ 60 s per heading in total) at 18, 20 and 22 m/s; record current | `ARSPD_RATIO` 1.5–3.0 and airspeed vs GPS mean error ≤ 10 % (review M[controls].1); cruise power ≤ 356 W / 16.0 A at 22.2 V *(calc, R10 line)*; predicted at 18 m/s 258–296 W, 11.6–13.3 A (`aero_results.json drag.cruise`, `mission.I_cruise_A`, `sized.P_cruise`, `sized.I_cruise`); pusher can ≤ 80 °C EST by IR after the legs (thermal.md §6.3: 76 °C after 600 s at 25 °C, loss EST) | F07 |
| F13 | Gear-fairing A/B at 18 m/s (new in rev B) | — | same reciprocal legs as F08 with fairings on, then (separate flight) fairings removed; watt-meter/BAT power at 18 m/s | with fairings ≤ 356 W (R10); predicted 258 W faired vs 389 W bare (`aero_results.json drag.gear_faired_case`, `gear_round_case`; bare legs leave 9.1 min of cruise, `mission.round_legs`, so R10 fails without them); ΔP ≥ 100 W confirms the fairings are load-bearing for R10 | F08 |
| F09 | Stall-speed determination in fixed-wing mode (new in rev B; replaces the rev A margin approach) | aero M2 | ≥ 80 m AGL EST, Q_ASSIST forced off, FBWA, idle, decelerate ≤ 0.3 m/s² to the pitch break; three runs; recover; then with Q_ASSIST auto note the assist speed | measured Vs (calibrated) ≤ 12.0 m/s = pass (R11; predicted 11.75, 11.75 in the C0 flight model); 12.0–12.5 = team decision (aero §9 option: accept); > 12.5 = fail; altitude loss ≤ 30 m EST; `AIRSPEED_MIN` 16 ≥ 1.3 × Vs (Vs ≤ 12.3) | F08 |
| F10 | Fixed-wing failsafes: pusher-out (R15), RC loss in cruise (R20) | — | ≥ 60 m AGL EST: pusher throttle to idle in FBWA → Q_ASSIST → QLAND; separate flight: RC off in cruise → RTL → QRTL | hover re-entered with altitude loss ≤ 30 m EST; RTL → QRTL → land within `RTL_RADIUS` 100 m of home | F09 |
| F11 | Mission dress rehearsal (half duration) | F7 prep | 1 min hover, transition, 5 min cruise at 18 m/s, back-transition, 1 min hover, land | projected full-mission energy ≤ C11 usable: energy used in F11 + the energy of its 300 s cruise segment ≤ C11 delivered Wh × 0.8 *(predicted: (1,131.9 × 160 + 295.6 × 300) / 3600 = 74.9 Wh for F11, + 24.6 Wh = 99.6 Wh = 91 % of 109.7 Wh; `sized.P_hover`, `sized.P_cruise`, transitions at hover power as in the sizing)*; all phases logged; no failsafe. (The rev B line "≤ 60 % of usable" is withdrawn: the frozen design predicts 68 % for F11, so it would fail a healthy aircraft.) | F10, F13 |
| F12 | Full mission (R8, R9, R10) | F7 | ≥ 1 min hover, transition, ≥ 10 min cruise at 18–22 m/s, back-transition, ≥ 1 min hover, vertical land; no ballast; fairings on; field air ≤ 25 °C (R21); wind 3–5 m/s if available (R16) | landing ≥ 20 % of C11 usable energy and ≥ 1,300 mAh (predicted 27 % of nameplate, C11); no failsafe (note: `BATT_LOW_MAH` 1,625 = 30 % will trigger the low-battery RTL before a full mission ends, §12 item 18); aircraft undamaged; dated ≤ 2027-04-30 | F11 × 2 |

![**Figure F09.** Stall-speed test profile: level at cruise, idle, slow down at no more than 0.3 m/s² to the pitch break and record the airspeed, then recover. Three runs.](figures/stall_profile.svg)

Cards: `docs/test/cards/FTC-F01.md` … `FTC-F13.md`.

#### F01 — First lift-off, QSTABILIZE hops

See the F01 row in the table above and its card in docs/test/cards/ for the full procedure.

![**Figure F01.** First lift-off, QSTABILIZE hops: plan view and profile.](figures/f01_hops.svg)

#### F02 — QHOVER hover-throttle learn and notch log (two 60 s batch-logged hovers)

See the F02 row in the table above and its card in docs/test/cards/ for the full procedure.

![**Figure F02.** QHOVER hover-throttle learn and notch log (two 60 s batch-logged hovers): plan view and profile.](figures/f02_hover_learn.svg)

#### F03 — QLOITER free hover, 3 × 60 s, thermal

See the F03 row in the table above and its card in docs/test/cards/ for the full procedure.

![**Figure F03.** QLOITER free hover, 3 × 60 s, thermal: plan view and profile.](figures/f03_loiter.svg)

#### F04 — Q-mode handling at low forward speed

See the F04 row in the table above and its card in docs/test/cards/ for the full procedure.

![**Figure F04.** Q-mode handling at low forward speed: plan view and profile.](figures/f04_low_speed_box.svg)

#### F05 — Hover failsafes and R20 demonstration

See the F05 row in the table above and its card in docs/test/cards/ for the full procedure.

![**Figure F05.** Hover failsafes and R20 demonstration: plan view and profile.](figures/f05_hover_failsafes.svg)

#### F06 — Partial transitions (Q_ASSIST on)

See the F06 row in the table above and its card in docs/test/cards/ for the full procedure.

![**Figure F06.** Partial transitions (Q_ASSIST on): plan view and profile.](figures/f06_partial_transitions.svg)

#### F07 — Full transition, circuit, back-transition, QLAND

See the F07 row in the table above and its card in docs/test/cards/ for the full procedure.

![**Figure F07.** Full transition, circuit, back-transition, QLAND: plan view and profile.](figures/f07_transition_circuit.svg)

#### F08 — Airspeed calibration and cruise performance

See the F08 row in the table above and its card in docs/test/cards/ for the full procedure.

![**Figure F08.** Airspeed calibration and cruise performance: plan view and profile.](figures/f08_airspeed_legs.svg)

#### F13 — Gear-fairing A/B at 18 m/s

See the F13 row in the table above and its card in docs/test/cards/ for the full procedure.

![**Figure F13.** Gear-fairing A/B at 18 m/s: plan view and profile.](figures/f13_fairing_ab.svg)

#### F10 — Fixed-wing failsafes: pusher-out (R15), RC loss in cruise (R20)

See the F10 row in the table above and its card in docs/test/cards/ for the full procedure.

![**Figure F10.** Fixed-wing failsafes: pusher-out (R15), RC loss in cruise (R20): plan view and profile.](figures/f10_fw_failsafes.svg)

#### F11 — Mission dress rehearsal (half duration)

See the F11 row in the table above and its card in docs/test/cards/ for the full procedure.

![**Figure F11.** Mission dress rehearsal (half duration): plan view and profile.](figures/f11_rehearsal.svg)

#### F12 — Full mission (R8, R9, R10)

See the F12 row in the table above and its card in docs/test/cards/ for the full procedure.

![**Figure F12.** Full mission (R8, R9, R10): plan view and profile.](figures/f12_full_mission.svg)

### 9.6 Series I — documentary inspections

| ID | Title | Req | Procedure | Pass |
|---|---|---|---|---|
| I01 | Budget ledger audit | R6, R7 | Every receipt (goods, tax, shipping) logged against `docs/purchasing/C0_BOM.csv` "Actual USD"; sum; spares (3 ESCs, prop pair) and second pack checked in; note that no spare motor, servo or pushrods are held | Total ≤ $2,000.00; reserve ≥ $100 target (BOM: $1,854.17 committed, $145.83 reserve); spares on the shelf |
| I02 | Legal and site compliance | R18, R19 | Checklist from review §[schedule] "Compliance checklist": legal path chosen (by 2026-11-06), TRUST per pilot, registration + marking, BeeID serial (E12), AMA per pilot, flight request ≥ 7 business days, post-flight report ≤ 3 business days, site ceiling in `FENCE_ALT_MAX` (≤ 110) | All items "done" before the first flight; a request on file for each flight date |
| I03 | Configuration inspection | R1, R3, R14 | Built aircraft against `cad/drawings/DBF-DRW-001.PDF` sheet 1: 4 lift rotors, pusher, wing, tail with rudders; span 2.40 m; disc clearance pusher-to-rear-lift ≥ 20 mm (`cad/params.txt` discClear 106.1 mm; `cad/verification.txt` 105.0 mm from the 21:38 build); pusher ground clearance ≥ 40 mm (44.8 mm, `cad/verification.txt`); hover limits and the R21 ceiling printed on the cards | Matches drawing; span 2.40 ± 0.02 m; clearances met; cards carry the limits |

## 10. Data management

**Log naming.** `YYYY-MM-DD_<TestID>_<run>_<article>.<ext>`, e.g. `2027-03-13_F01_r2_C0.bin`. Flight logs: copy the `.bin` from the FC SD card after every flight (`LOG_BITMASK,65535`, `firmware/vtol_c0.param`), never fly on a card you have not copied. Bench data: CSV from the watt-meter video transcription or the Nano serial log. Store under `docs/test/data/<series>/` (not created at rev B; add to git LFS or an external drive if > 100 MB). SITL evidence stays in `firmware/sitl/results/` (generic model) and `firmware/sitl/results_c0/` (C0 airframe model).

**ArduPilot log extraction** (`docs/test/analysis/log_summary.py`, pymavlink if installed, else the text export from Mission Planner):

| Message | Fields | Used for |
|---|---|---|
| `VIBE` | VibeX/Y/Z, Clip0–2 | abort criteria; < 30 m/s², clipping 0 |
| `BAT` | Volt, VoltR, Curr, CurrTot, EnrgTot, Temp | sag, current per phase, energy for R10, cruise power for F08/F13 |
| `RCOU` | C1–C12 | lift outputs (C5–C8) for hover throttle, front/rear split, "stopped in cruise" (R1); pusher C9 |
| `CTUN` | NavPitch, Pitch, ThrOut, As (airspeed), E2T | cruise throttle and airspeed |
| `QTUN` | ThrOut, ThO, DAlt, Alt, DCRt, CRt, TrnMs (transition) | hover throttle, climb rate, transition timing |
| `ARSP` | Airspeed, DiffPress, Temp, RawPress, Ratio | calibration (F08), stall speed (F09) |
| `MODE` | Mode, ModeNum, Rsn | phase timing, failsafe actions |
| `GPS` | Spd, HDop, NSats | ground speed for airspeed calibration |
| `ATT` | Roll, Pitch, DesRoll, DesPitch | attitude error; pitch break in F09 |
| `ISBH/ISBD` | batch IMU samples | notch filter FFT (F02) |
| `MSG`, `EV`, `ERR` | text | failsafe and arming events |

**Reduction scripts** (each ships with a sample dataset and has been run on it):
- `thrust_stand.py` — fits thrust vs throttle (power law), thrust vs electrical power, reports throttle and power at the hover point (1,859 g), FM·η against the sizing 0.505, max thrust vs the 2.98 kgf pass, hover power vs the 339 W pass, and a `Q_M_THST_EXPO` estimate.
- `battery_test.py` — integrates Wh and Ah from a discharge log, finds the sag at the 54 A and 82 A step loads, estimates per-cell internal resistance, applies the C11 pass criteria (≤ 6.0 mΩ/cell) and prints the full-mission pack start-temperature limit 60 − 4.7 × R_cell.
- `log_summary.py` — parses a `.bin` (pymavlink) or a Mission Planner text export (`.log`) and prints hover throttle, VIBE max/clip, current and voltage min/mean per mode, airspeed stats, mode timeline and the R10 phase durations; cruise current pass 16.0 A.

**Test report template** (`docs/test/cards/REPORT-TEMPLATE.md`): header (test ID, rev, date, site, crew, article serials, firmware hash, weather), configuration and deviations from the card, run table (run, time, condition, result), measured vs predicted table with pass/fail, anomalies, log file names, decision (pass / pass with limits / fail), sign-off (TD, SO).

## 11. Schedule

Dates come from the review schedule (`review/src/app.js drawGantt` rows, §11) and the order-by table (§11 "Order-by dates"). Dates are the review's plan (EST).

| Window | Review milestone | Tests |
|---|---|---|
| 2026-10-21 | SITL scripted scenarios | E05 (SITL part), E06 (scripted part) — done |
| 2026-10-25 | SITL on the C0 airframe model | E05, E06 scripted parts repeated 7/7 — done (`firmware/sitl/results_c0.json`) |
| 2026-11-02 → 11-09 | Order A (2 motors, props, 1 ESC pack, test kit, packs, charger) | — |
| 2026-11-16 → 12-04 | Thrust stand T1–T5 | C06, C07 (2 motors), C08, C09, C10, C11, C15 |
| 2026-12-07 → 12-14 | Order B (airframe, propulsion, avionics) | — |
| 2026-12-15 → 2027-01-03 | before build | C01, C02, C03, C04, C16 (coupons and first articles must precede printing the real parts), C05, C14, E11 (first flash), E12 (serial lookup) |
| 2027-01-04 → 02-19 | Airframe build | C07 (remaining 3 motors; no spare in the BOM), C12, C17, S09 (ongoing), S02, S03, S04, S05 as sub-assemblies finish (S10 withdrawn) |
| 2027-01-11 → 02-19 | SITL rehearsal | E06 (every pilot, hand-flown) |
| 2027-02-19 → 02-26 | Proof load, drop test, CG | S01, S06, S07, S08, G01, G09 |
| 2027-02-22 | integration milestone (former R17 go/no-go, closed) | E11 (final firmware) |
| 2027-02-22 → 03-12 | Avionics integration + bench | E01–E05 (hardware), E07–E10, G02, G03 (+ C13, E09), G04, G06, G07, G08, I01, I03 |
| 2027-03-03 | first flight request filed (≥ 7 business days) | I02 |
| 2027-03-13 → 03-31 | Hover tests | G05, F01–F05 |
| 2027-04-03 → 04-17 | Transition tests (RFS) | F06–F11, F13 |
| 2027-04-17 → 04-18 | Full mission | F12 |
| 2027-04-18 → 04-30 | Buffer: repair, weather, re-fly | re-runs |

Critical dependencies: any Order B item arriving after 2027-02-15 pushes first hover past 2027-03-13 (review M[schedule].2); the RFS approval decides whether F06–F13 can happen at all (review risk register).

## 12. Inconsistencies: rev A list and their status at rev C

| # | Item | Status at rev C (2026-11-02) |
|---|---|---|
| 1 | Thrust-stand accuracy "2 % FS" | **Resolved:** C06 passes at 2 % of reading (0.5–5 kg). |
| 2 | 2-minute notch hover vs 60 s hover limit | **Resolved by the firmware:** two 60 s batch-logged hovers (`INS_LOG_BAT_OPT,4`; `docs/research/firmware.md` D13); F02 card. |
| 3 | 5 m hover limit vs 30 m transition / 20 m failsafe altitudes | **Open** (team acceptance at sign-off, §14). |
| 4 | T2 pass 2.4 kgf vs R13 | **Resolved:** 2.98 kgf at 7.438 kg (1.6 × 7.438 / 4, C07). |
| 5 | 17 × 5.8 maker data vs 17 × 5.5 BOM prop | **Open:** C07 measures the real combination. |
| 6 | Low battery QLAND (review) vs RTL (param) | **Resolved:** low → RTL at 21.0 V / 1,625 mAh, critical → QLAND at 19.8 V / 1,300 mAh (`firmware/vtol_c0.param` §9; SITL E); E05/F05 test this. |
| 7 | Fence 120 m vs 110 m | **Resolved:** 110 m, SITL breach peak 113.1 m (< 121.9 m). |
| 8 | Drop test expected to fail on bare legs | **Resolved by the design case:** the drop is at 2 × `Q_LAND_FINAL_SPD` = 0.6 m/s (S06), RF ≥ 1.65 (`analysis/structures/landing.json`); compliant feet stay optional (FOAMULAR offcuts, zero cost). |
| 9 | MS5525DSO I²C address conflict | **Resolved:** the BOM now carries the RMRC MS4525DO at 0x28, `ARSPD_TYPE,1` (no clash with the baro at 0x76; E08 checks both are detected). |
| 10 | No telemetry radio | **Resolved:** CRSF telemetry to the handset or ELRS MAVLink overlay; SiK radio removed from the Gaps list (E04/E10). |
| 11 | 4 vs 5 servos | **Resolved:** 5 servos everywhere (`results.json cg.items` "Servos (5)", BOM, param S4/S11); no spare servo (BOM change). |
| 12 | Stall speed | Predicted Vs 11.75 m/s (`aero_results.json stall`, CL_max,3D 1.115 = sizing CL_max; 2.1 % speed margin to R11) and 11.75 m/s in the C0 flight model; **F09 decides**; the pass band and the team-decision band are stated there. |
| 13 | Static margin without payload | **Resolved by the design (2026-11-01):** no payload, no ballast; the pack alone puts the CG at 28 % MAC, static margin 10.4 % (AVL) / 10.2 % (sizing) (§4 rule 7, G01, G09). S10 withdrawn. |
| 14 | Cruise power | Two predictions: 296 W (sizing) and 258 W (aero build-up) at 18 m/s against the R10 threshold 356 W (§8); F08/F13 measure. Bare legs: 389 W → R10 fails (9.1 min), so the fairings are flight-critical for R10 (F13). |
| 15 | Param file header MTOW and hover throttle | **Resolved 2026-11-02:** `firmware/vtol_c0.param` comments now quote 7.44 kg and an expected learned hover throttle of ~0.59 (1,858.9 / 3,130 g). |
| 16 | Thermal margins (`docs/research/thermal.md`, re-run 2026-11-02) | **Mitigated by R21:** at the 25 °C ceiling the lift motor peaks at 75 °C (+5 K to 80 °C EST), the ESC at 62 °C (+8 K), the pack at the 6.0 mΩ/cell limit at 53 °C (+7 K, sealed bay) and the pusher at 76 °C after 600 s (+4 K); the motor and ESC losses are estimates, so C08, C11, G03, F03 and F08 measure them and C08 can lower the ceiling. |
| 17 | Back-transition pitch-up in the C0 SITL model | **Open:** the airbrake phase pitches to the 30° VTOL limit and briefly stalls the wing (−17°/+33° swing, ≤ 2 m loss, `firmware/sitl/README.md` Gains item 1). Watch item on F06–F13; first remedy lower `Q_TRANS_DECEL`. |
| 18 (new, rev C) | Battery limits vs the frozen mission | **Resolved 2026-11-02:** (a) the planned full mission lands at 27.4 % of nameplate (1 − 99.51 / 0.95 / 144.3), so `BATT_LOW_MAH` moves from 1,950 (30 %) to 1,625 mAh (25 %): above the 20 % reserve (`BATT_CRT_MAH` 1,300, R10) and 2.4 points below the planned landing, so the low-battery RTL fires only on an overrun and F12 can pass; (b) the C11 sag line at 54 A is now ≥ 3.37 V/cell (3.70 − 54 × 0.0060), the 6.0 mΩ/cell acceptance restated, instead of 3.4 V (which implied 5.6 mΩ). |
| 19 (new, rev C) | Lift margins at the frozen mass | **Open:** predicted transition current 82.1 A EST sits 3 A under `Q_M_BAT_CURR_MAX` 85, which then throttles the lift motors; expected hover throttle 0.59 sits just under the F02 pass line 0.60 (review F2) and R13's 1 / 1.6 = 0.625. C07, G03 and F02 measure them. |
| 20 (new, rev C) | SITL evidence predates the frozen mass | **Open:** the C0 SITL scenarios A–G (`firmware/sitl/results_c0.json`, 2026-10-27) ran on the 6.55 kg model; `c0_physics.py --validate` now models 7.438 kg. Re-run the scenarios before E06's pilot portion. |
| 21 (new, rev C) | Drawing DBF-DRW-001 not regenerated | **Resolved 2026-11-03:** rev F carries no ballast note (GA note 4: no payload, no ballast), title block rev F; I03 inspects against rev F. |

## 13. Gaps — equipment not in the BOM

Zero-cost substitutes are used wherever possible; items below are only needed if the substitute fails. Prices are live reads with the date; none is in the $1,854.17 committed spend (R6 cannot be raised; these would come from the $145.83 reserve, BOM).

| Need | Zero-cost substitute used in this plan | If the substitute fails | Price, URL (date checked) |
|---|---|---|---|
| Masses for proof load and calibration | Water jugs (1 L = 1 kg) and sandbags weighed on a kitchen scale | — | $0 |
| Kitchen scale (5 kg, 1 g) and bathroom scale | Borrow; most households have one | Amazon kitchen scale | — (not priced; typical $10–15 EST) |
| Luggage/spring scale (pusher pull, hinge moment, stopped-rotor drag) | HX711 load cell from the thrust stand in line | Hanging luggage scale 50 kg | — (not priced; typical $8–12 EST) |
| Calipers, multimeter, hex keys | Hand tools on hand (R6 "hand tools") | — | $0 if on hand; otherwise — |
| Torque wrench 0.1–1 N·m | Hanging-mass method on the hex key (hardware-spec §2d) | — | $0 |
| Phone accelerometer / spectrum app | phyphox (free, phyphox.org) or similar | — | $0 |
| Anemometer | Phone app + nearest METAR/NWS; improvised wind sock | Hand-held anemometer | — (typical $12–20 EST) |
| Telemetry during transitions | CRSF telemetry on the handset; ELRS MAVLink overlay for a GCS (`docs/research/firmware.md` §4) | — (no radio needed) | $0 |
| Field power for the charger | Charge at home between sessions; two packs = 2 flights per session | Car 12 V (the HTRC C150 is AC/DC, `docs/research/budget-energy-test.md` §2) with a 12 V lead | — |
| Compliant landing feet (S06) | FOAMULAR offcuts under the dome feet; TPU print if a spool is on hand | TPU filament | — |
| Spare servo / pushrods (removed from the BOM) | None: a failure ends the session; buy from the reserve | EMAX ES3005HV $19.99 (shop.emax-usa.com, checked 2026-10-13 in `docs/research/budget-avionics.md` §6); Du-Bro 2-56 pushrods $12.48 (BOM line) | from the $145.83 reserve |
| Tether lines and stakes | Rope and tent stakes on hand | — | $0 |
| Hardened nozzle for PA6-CF | Check the team printer (review §[build]) | Hardened steel nozzle | — |
| Remote ID receiver app | OpenDroneID OSM (free Android app) | — | $0 |
| pymavlink for log reduction | Mission Planner text export + `log_summary.py` text mode | `pip install pymavlink` (free; already used for SITL, `firmware/sitl/README.md`) | $0 |

## 14. Open items for team sign-off

1. Accept the exposure of hovering to 30 m for transitions, 20 m for failsafe tests and 80 m for the stall determination, given the R14 limitation (§12 item 3).
2. Decide the R11 stall-speed acceptance band before F09 (design target 11.75 m/s, `docs/research/stall-margin.md` §5 measured-stall rule): pass ≤ 12.0 m/s; 12.0–12.5 m/s accept or add 5 % wing area (`docs/research/aerodynamics.md` §9 item 3).
3. Confirm whether compliant feet are fitted before S06 (optional; §12 item 8).
4. Assign names to the roles and the matrix "Crew" column.
5. Confirm the test site(s) and file the first flight request by 2027-03-03.
6. Decide whether a spare servo is bought from the reserve before the flight phase (no spare in the BOM).
