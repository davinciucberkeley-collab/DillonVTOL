# Design basis — Lift + Cruise VTOL (v0.4.0, 2026-10-21)

Status: v0.4.0 (2026-10-21). v0.4: full engineering draft — exact hardware and fits (docs/research/hardware-spec.md),
aerodynamic package with CFD (docs/research/aerodynamics.md) that resized the wing and added leg fairings, CAD rev B with every
fastener, build manual DBF-MAN-001, test plan DBF-TP-001, flight software (firmware/), 29-variant trade study
(docs/research/configurations.md). 2026-11-02: R21 added (full-mission ambient ≤ 25 °C, from the thermal re-run; it replaces the 35 °C "hot day" estimate that no requirement set). 2026-10-25: values re-based on the R11 wing re-size, chord 266.6 mm, MTOW 6.45 kg (CAD model rev C, drawing DBF-DRW-001 rev D; R11 now met). 2026-10-25: re-based on the 11.75 m/s design stall target, chord 284.2 mm, MTOW 6.55 kg, CAD model rev D, drawing DBF-DRW-001 rev E (docs/research/stall-margin.md; R11 met with a 2.1 % speed / 4.1 % CL_max margin; thermal analysis docs/research/thermal.md). v0.3.1 (2026-10-13): project-audit fixes. v0.3: R6 clarified as a hard cap incl. tax and shipping; R7 reserve revised;
budget redesign (C0 4-lift, X4110S, 6061 tubes, taped XPS wing). v0.3.1: project-audit fixes (see
"Design outcomes" below). Previous: v0.2. Team decisions 2026-10-13: scratch-built airframe (no kit);
R10/R11 and R14 delegated to the reviewer and set as below; project is part
of a UC Berkeley capstone course (bears on R19).
"Given" = stated in docs/VTOL-REVIEW-PROMPT.md or CLAUDE.md.
"Assumed" = proposed here; needs team confirmation. Values marked (est.) are
engineering estimates, not measured or looked up.

## Requirements

| ID | Requirement | Source |
|----|-------------|--------|
| R1 | Configuration: vertical lift rotors for takeoff/landing, pusher prop + fixed wing for cruise, lift rotors stopped in cruise. | Given |
| R2 | MTOW 8–15 kg target; hard cap < 25 kg (55 lb). Exact MTOW is a design output from budget and mission; the current value is in "Design outcomes" below (generated from analysis/results.json). | Given |
| R3 | Wingspan 2–3 m. | Given |
| R4 | Breaks down so the largest piece fits in a standard car. Working envelope (est.): largest piece ≤ 1.5 × 0.5 × 0.4 m; to be replaced by the team's measured car (M-item). | Given (envelope Assumed) |
| R5 | Two people can carry it assembled; a team of 4 handles it routinely. Assembly from transport to flight-ready ≤ 15 min (est.). | Given (time Assumed) |
| R6 | Total physical spend ≤ $2,000, **fixed — cannot be expanded** (team, 2026-10-13). Inside the cap: all hardware, spares, both flight packs, charger, test gear, shipping and sales tax. Outside the cap: FAA/AMA fees (not hardware). On hand at $0: 3D printer and hand tools only. | Given |
| R7 | Budget holds a second flight pack and spares; crash-repair reserve = whatever remains under the R6 cap, target ≥ $100 (est.). The current reserve is in "Design outcomes" below. | 2nd pack/spares Given; reserve Assumed (revised 2026-10-13) |
| R8 | Built and flight-tested (hover, transition, cruise, back-transition, landing) by 2027-04-30. | Given |
| R9 | Mission: VTOL takeoff → hover → transition → cruise → back-transition → hover → vertical land. | Given |
| R10 | Endurance: ≥ 10 min cruise + ≥ 2 min total hover per flight, with ≥ 20 % battery energy reserve at landing. | Assumed |
| R11 | Cruise speed 18–22 m/s; stall speed ≤ 12 m/s at MTOW (est.), designed to 11.75 m/s to hold a 4.1 % CL_max margin (docs/research/stall-margin.md, 2026-10-25); transition complete above 1.3 × stall (AIRSPEED_MIN set to 16 m/s ≥ 15.6). | Assumed |
| R12 | Payload: none beyond avionics (revised 2026-11-01: the 0.5 kg future-sensor reserve was removed; at the CAD-calibrated mass it cost about 0.7 kg of MTOW and took hover T/W to the R13 limit, and it had been acting as CG ballast, which the lengthened pod nose now replaces; analysis/mass/mass_budget.py, analysis/geometry.mjs POD). A future sensor is a design change. | Assumed |
| R13 | Hover thrust-to-weight ≥ 1.6 at MTOW with all lift motors, on the maker's 22.2 V thrust table (revised 2026-11-01). Basis: T-Motor's VTOL propulsion guide gives 1.6 minimum, 2.0 recommended (https://shop.tmotor.com/blog/vtol-propulsion-system-selection-guide, checked 2026-11-01); the earlier "storage-low voltage" clause is dropped because no source defines thrust at that state. Confirmed on the thrust stand (DBF-TP-001 C07). | Assumed |
| R14 | Lift motor-out in cruise: aircraft continues as a fixed wing and lands (hard). Lift motor-out in hover: controlled vertical landing is *desired*, scored in the Pugh matrix and decided by the 4-lift vs 8-lift cost comparison (§7). | Assumed (team deferred choice, 2026-10-13) |
| R15 | Pusher-out in cruise: aircraft can re-enter hover (QAssist / VTOL recovery) and land vertically. | Assumed |
| R16 | Wind: operate in steady wind ≤ 5 m/s, gusts ≤ 8 m/s (est.). | Assumed |
| R17 | Flight controller: open-source autopilot with maintained lift + cruise VTOL support (ArduPilot QuadPlane or PX4 VTOL; current support to be verified in §10). | Assumed |
| R18 | Legal (FAA): fly under 49 U.S.C. § 44809 via the higher-education educational provision (Pub. L. 115-254 § 350) or under Part 107; operators pass TRUST (or hold a Part 107 certificate); aircraft registered and marked; Remote ID by broadcast module (14 CFR 89.115(a)) or flown inside a FRIA (89.115(b)); VLOS; ≤ 400 ft AGL in Class G, authorization in controlled airspace. | Assumed path; rules cited below |
| R19 | Legal (campus): on-campus outdoor flight needs a UAS Flight Request ≥ 7 business days ahead, a post-flight report within 3 business days, and ≥ $1M liability insurance (AMA membership satisfies it for recreational users). Recreational use is limited to registered student orgs and "University of California courses (including senior projects)". Site limits: Richmond Field Station 400 ft AGL; Clark Kerr track 200 ft AGL; La Loma field below 20 ft within the fences; 6 a.m. to sunset; no flying on game or graduation days. Only RFS supports transition testing (≥ 30 m AGL). Liability cover is per pilot. Off-campus sites follow their own managers' approvals. | Assumed path; policy cited below (checked 2026-10-13) |
| R20 | Safety: hardware arming switch / kill, failsafe RTL-then-land on link loss, geofence. Implementation (rev 2026-11-01): Amass AS150U battery plug (70 A continuous / 140 A for 1 min on 10 AWG, Amass AS150U-F datasheet; the XT90-S is rated 40 A continuous, below the hover current, docs/research/propulsion-margin-data.md) as the physical disconnect, anti-spark contact confirmed on receipt + RC arm switch + ArduPilot arming checks; geofence per site ceiling. | Assumed |
| R21 | Full-mission ambient envelope: no full mission (and no flight with a transition, which reaches the same lift-unit peak, TEST-PLAN F06–F13) when the air temperature measured at the field before the flight is above **25 °C**. Basis: the flight campaign is in Berkeley in spring, where the April average high is 20 °C / 67 °F (NOAA NCEI 1991–2020 normals via https://www.currentresults.com/Weather/California/city-temperature-april.php, checked 2026-11-02); the thermal model at 25 °C (`docs/research/thermal.md`, `cad/sim/thermal/results.txt`, run 2026-11-02 with a 6.0 mΩ/cell pack and 2.0 W on the FC board) puts the lift motor can at a 75 °C mission peak (80 °C EST limit, +5 K), the pack at 53 °C at touchdown (60 °C, +7 K) and the pusher can at 76 °C after 600 s of cruise (80 °C EST, +4 K); ESC 62 / 70 °C, FC 60 / 85 °C. All temperatures move 1 K per 1 K of ambient, so 25 °C is where the lift motor, battery and pusher still pass with 4–7 K margin. **Set by the analysis, not by the team**; it can be revisited once C08, C11 and F08 (TEST-PLAN) replace the loss and resistance estimates. Verified by TEST-PLAN §4 rule 9 (reading written on every flight card). | Assumed (set by analysis 2026-11-02) |

### Rule sources (checked 2026-10-13)
- 49 U.S.C. § 44809(a) conditions; § 350 educational note: https://www.law.cornell.edu/uscode/text/49/44809
- 14 CFR 107.51 (87 kt, 400 ft AGL, 3 sm visibility, cloud clearance): https://www.law.cornell.edu/cfr/text/14/107.51
- 14 CFR 89.115 (broadcast module / FRIA, VLOS): https://www.law.cornell.edu/cfr/text/14/89.115
- UC Berkeley UAS (Drone) Policy, effective 2018-05-15, revised 2025-04-04: https://oercs.berkeley.edu/policies/campus-policy-library/unmanned-aircraft-system-drone-policy
- FAA Educational Users page (https://www.faa.gov/uas/educational_users/) returned HTTP 403 on 2026-10-13; not verified.
- R21 climate basis: Berkeley April average high 67 °F / 20 °C, NOAA NCEI 1991–2020 normals as tabulated at https://www.currentresults.com/Weather/California/city-temperature-april.php (checked 2026-11-02).

## Design outcomes
<!-- gen:outcomes -->
- Generated by analysis/docs_sync.py from analysis/results.json (2026-11-01), analysis/aero/aero_results.json (2026-11-02) and analysis/mass/mass_budget.json. Do not edit inside this block.
- Mass: MTOW 7.44 kg (R2: below the 8–15 kg working target, under the 25 kg cap). Every item the sizing does not derive from geometry is calibrated to the CAD roll-up with the print settings (analysis/mass/mass_budget.py: bottom-up 7.42 kg).
- Wing: S 0.774 m², chord 322.3 mm, AR 7.45, span 2.4 m, sized on CL_max 1.115 at the 11.75 m/s design stall (R11 ≤ 12 m/s); the aero package gives stall 11.75 m/s at its CL_max 1.115 (2.1 % speed margin to R11).
- Propulsion (R13): 4 × SunnySky X4110S 400KV + LANRC 45A + 17x5.5 prop lift units; hover T/W 1.68 on the maker's 22.2 V table, hover 1132 W / 51.0 A, transition peak 82 A (EST, 20 s); pack Ovonic 6S 6500 100C (2-pack).
- Endurance (R10): 12.0 min cruise available after 120 s hover + 40 s transition with the 20 % reserve (design margin 11.5 min).
- CG and stability: battery at x = 0.255 m (fits: furthest forward station 0.339 m) puts the CG at 28 % MAC with no ballast; neutral point 38.2 % MAC; static margin 10.2 %.
- Structure: joiner 195 MPa at 4.5 g ultimate (Schrenk root moment 91.0 N·m): reserve factor 1.41 on the 275 MPa library yield, 1.23 on the 240 MPa minimum. Boom first mode 25.9 Hz with the 326 g lift unit. FEA (cad/sim/results.txt): boom 38.633 MPa, spar 191.233 MPa.
- Landing (analysis/structures/landing.py): touchdown at Q_LAND_FINAL_SPD 0.3 m/s (firmware/vtol_c0.param) gives reserve factor ≥ 3.04 on the 6061-T6 minimum yield at every gear corner, and ≥ 1.65 at twice that speed (hard touchdown); the booms are treated as cantilevers from rigid wing clamps, which over-predicts the load.
- Budget (R6/R7): committed $1854.55 incl. 10.25 % tax and $92 shipping; crash reserve $145.45 (R7 met).
<!-- /gen:outcomes -->
- C0 4-lift twin boom, unchanged as the concept: the 29-variant trade study (analysis/tradestudy.json) ranks the C0 family first among layouts that meet R1; a quad tailsitter scores higher but breaks R1.
- Rev 2026-11-01 (design iteration after the engineering audit): sizing calibrated to the CAD mass roll-up; payload allowance removed (R12); pod nose lengthened 0.15 m so the CG reaches its target without ballast; R13 restated on a published basis; battery plug changed to the AS150U; one XT60 per lift ESC at the boom disconnects; final landing descent set to 0.3 m/s (firmware); wing bolt M5 × 25 with at least two threads past the nylock in the worst case. Reasons and evidence: docs/validation/VALIDATION-REPORT.md.
- R10 needs the printed teardrop leg fairings (the drag build-up without them fails R10).
- R14: hover motor-out not met by C0; the 8-lift layouts exceed the cap. Accepted with hover limits (≤ 5 m AGL, ≤ 60 s).
- R17: ArduPlane 4.7.2 stable includes the CoreWingF405WingV2 target. Parameter file firmware/vtol_c0.param passes the checker; SITL scenarios A–G pass (firmware/sitl/README.md); THR_MAX 85 caps the pusher until bench test M1.
- Thermal and FEA results: docs/research/thermal.md and cad/sim/results.txt (re-run on the current CAD). Thermal re-run 2026-11-02 at the 25 °C R21 ceiling: every component passes, lift motor +5 K, pusher +4 K, pack +7 K (6.0 mΩ/cell acceptance, TEST-PLAN C11).

## Assumptions the team most needs to confirm
1. R14 motor-out in hover. Resolved for v0.3.1: not met by C0; accepted with hover limits because no motor-out-tolerant layout fits the R6 cap.
2. R10/R11 mission. Endurance and speed set battery mass, which sets MTOW and cost.
3. R18/R19 legal path and flying site. Which certificate path (44809 educational vs Part 107), whether the project is a registered student org or a UC course, and which field. A transition test needs a long VLOS field.
4. R7 crash reserve: "what remains under the cap, target ≥ $100" (current value in Design outcomes). 2026-11-01: shipping was re-priced vendor by vendor (the $110 allowance was an estimate; cart quotes and published thresholds, docs/research/bom-savings.md), the avionics and servos move to one ReadyMadeRC order (free shipping), the ESCs to an equally rated LANRC 4-pack, and the spare X4110S is held as reserve cash (spare ESCs and props stay in the kit; SunnySky USA ships free in the US). Still estimates: OnlineMetals shipping ($50) and the RMRC free-shipping rule (not cart-verified).
5. R4 car envelope. Measure the actual car.
6. R12 payload: none since 2026-11-01. Any real payload raises MTOW and needs the sizing re-run.
7. ~~Build vs kit~~ — resolved 2026-10-13: scratch build.
8. R19: the policy names senior projects explicitly; confirm institutional sponsorship for the § 350 educational path and request Richmond Field Station.
9. R2: sign off the MTOW in Design outcomes (below the 8–15 kg working target).

## Repo contents at Step 1
CLAUDE.md; docs/VTOL-REVIEW-PROMPT.md; docs/reference/REVIEW-STYLE.md;
docs/reference/lift-cruise-reference.png. No CAD, no requirements doc
(before this file), no sizing scripts, no BOM.
