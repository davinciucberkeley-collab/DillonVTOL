# CAPSTONE Design–Build–Fly: Lift + Cruise VTOL (student capstone)

A hybrid VTOL with four vertical lift rotors for takeoff and landing, and a pusher prop and fixed wing for cruise. The lift rotors stop in cruise. The aircraft is built and flight-tested on a **fixed $2,000 budget** (hardware, spares, test gear, tax and shipping) by **2027-04-30**.

## ▶ View the design review online

**[davinciucberkeley-collab.github.io/DillonVTOL](https://davinciucberkeley-collab.github.io/DillonVTOL/)**: opens in any browser, with no download and no sign-in.

GitHub's file view can't display the review: at 29 MB it only shows the raw source. Use the link above, or download the repository and double-click `VTOL-Review.html`. The review is one self-contained report: the decision, the design, build and fly, and proof and validation. It includes interactive charts, a rotatable SOLIDWORKS model, the 3-D CFD and a claims map with a proof for each of its 79 claims.

| Document | View online | File in this repository |
|---|---|---|
| Design review DBF-RPT-001, issue 6 | [open](https://davinciucberkeley-collab.github.io/DillonVTOL/VTOL-Review.html) | [`VTOL-Review.html`](VTOL-Review.html) |
| Build manual DBF-MAN-001 (14 work packages, step by step) | [open](https://davinciucberkeley-collab.github.io/DillonVTOL/build-manual.html) | [`build-manual.html`](build-manual.html) · source [`docs/build/BUILD-MANUAL.md`](docs/build/BUILD-MANUAL.md) |
| Test and evaluation plan DBF-TP-001 | [open](https://davinciucberkeley-collab.github.io/DillonVTOL/test-plan.html) | [`test-plan.html`](test-plan.html) · source [`docs/test/TEST-PLAN.md`](docs/test/TEST-PLAN.md) |
| Flight software setup DBF-SW-001 | [open](https://davinciucberkeley-collab.github.io/DillonVTOL/flight-software.html) | [`flight-software.html`](flight-software.html) · source [`firmware/README.md`](firmware/README.md) |
| Hot-wire templates (1:1) | [open](https://davinciucberkeley-collab.github.io/DillonVTOL/templates.html) | [`templates.html`](templates.html) |
| Drawing set DBF-DRW-001 rev G (9 sheets) | [open](https://davinciucberkeley-collab.github.io/DillonVTOL/cad/drawings/DBF-DRW-001.PDF) | [`cad/drawings/DBF-DRW-001.PDF`](cad/drawings/DBF-DRW-001.PDF) (GitHub shows it directly) |

## Current design (v0.4.0, resized 2026-11-02)

The numbers below come from `analysis/results.json` (sizing) and `analysis/aero/aero_results.json` (aerodynamics).

| | |
|---|---|
| Layout | C0: 4-lift twin-boom quadplane, H-tail with twin rudders on the booms, pusher on the pod; best of 29 configurations that keep the lift rotors stopped in cruise (`analysis/tradestudy.json`) |
| Span / wing | 2.4 m, 0.774 m² (chord 322.3 mm, AR 7.45; `analysis/results.json` C0 `sized.S`, `sized.chord`, `sized.AR`), NACA 2415, XPS foam core with packing-tape skin |
| MTOW | 7.438 kg (`analysis/results.json` C0 `sized.m`); bottom-up 7.416 kg (`analysis/mass/mass_budget.json`); hard cap 25 kg |
| Lift / pusher | 5 × SunnySky X4110S 400KV; 17 × 5.5 in lift props; APC 14×8.5EP pusher (`analysis/results.json` C0 `params.name`) |
| Hover / cruise | 1132 W hover (51.0 A at 22.2 V); 296 W at 18 m/s cruise by the sizing, 258 W by the aero build-up; hover T/W 1.68 on maker data (`analysis/results.json` `sized.P_hover`, `I_hover`, `P_cruise`, `TW`; `analysis/aero/aero_results.json` `drag.cruise.P_elec_W`) |
| Energy | 1 × Ovonic 6S 6500 mAh LiPo, 144.3 Wh; 12.0 min cruise available at 18 m/s after 2 min hover + 40 s transition, with a 20 % reserve (`sized.t_cruise_avail_min`, `params.EBattFixed`) |
| Aerodynamics | CD0 0.0425 (0.0266 clean + stopped rotors, booms and gear), L/D 8.71 at 18 m/s (9.97 by the component build-up); stall 11.75 m/s at CL_max 1.115 (R11 ≤ 12 m/s, margin 2.1 %; `aero_results.json` `stall`); neutral point 38.4 % MAC with the pod (AVL), static margin 10.4 % at the 28 % CG (`aero_results.json` `neutral_point`) |
| CFD | Full-aircraft SU2 (inviscid) on four meshes up to 23.3 M cells: CL 0.523 at 4°, grid uncertainty ±6.8 % (GCI); neutral point 39.7 % MAC, within 1.3 points of AVL (`analysis/cfd3d/out/cfd3d_results.json`) |
| Structure | 6061-T6 booms, spar sockets and a 0.76 m slip-fit joiner; joiner reserve factor 1.41 on yield at 4.5 g with the Schrenk root moment 91.0 N·m (275 / 194.7 MPa, `analysis/results.json` C0 `struct.MS_J`, `struct.sigJ`, `struct.Mroot`) |
| CAD | SOLIDWORKS model with drawing set DBF-DRW-001 rev G: 75 part files (`cad/model/*.SLDPRT` in git), 397 components including every screw, nut, washer and insert; 0 unexplained interferences and 0 drawing overlaps (`cad/verification.txt`, `cad/drawings/layout-check.txt`) |
| Avionics | CoreWing F405 Wing V2 + ArduPlane 4.7.2 stable QuadPlane; parameter file `firmware/vtol_c0.param` checked; SITL scenarios A–G passed on the earlier sizing, re-run on the current sizing pending |
| Validation | 79 claims, each with its equations, inputs and sources: 40 Verified, 38 Partially Verified, 1 Unverified, 0 Failed (`analysis/validation/validation_matrix.json`); the 29 with arithmetic re-run to the same number (`analysis/validation/proofs.json`) |
| Budget | **$1,854.55 committed** (goods $1,598.69 × 1.1025 tax + $91.99 shipping); **$145.45 reserve** (`analysis/results.json` C0 `bom`) |

## Repository layout

| Path | What it is |
|---|---|
| `VTOL-Review.html`, `*.html` at the root | The review and its companion pages (generated by `review/build.mjs`) |
| `docs/DESIGN-BASIS.md` | Requirements R1–R20 (Given vs Assumed), design outcomes |
| `docs/research/` | Parts research with prices, URLs and dates; `hardware-spec.md` (fasteners and fits), `configurations.md` (trade-study literature), `aerodynamics.md`, `firmware.md` |
| `docs/build/` | Build manual, cut / print / wiring lists, hot-wire template generator |
| `docs/test/` | Test plan, test matrix, flight test cards, data-reduction scripts |
| `docs/purchasing/C0_BOM.csv` | Purchasing list grouped by vendor, with order-tracking columns |
| `analysis/` | Sizing model and script, vortex-lattice check, trade study, independent checks (`verify.py`) |
| `analysis/aero/` | XFOIL, NeuralFoil, AVL, drag build-up and SU2 CFD (`run_all.py`) |
| `firmware/` | ArduPlane parameter files, setup guide, checklists, parameter checker, SITL scripts and results |
| `cad/` | SOLIDWORKS model generator, drawings, simulations and outputs. See [`cad/README.md`](cad/README.md) |
| `review/` | Page sources (`src/`), companion-page renderer and build script |

## Regenerate everything

```bash
node analysis/sizing.mjs        # sizing + BOM  -> analysis/results.json
node analysis/vlm.mjs           # aero check    -> analysis/aero.json
node analysis/export_bom.mjs    # purchasing    -> docs/purchasing/C0_BOM.csv
py -3 analysis/verify.py        # independent checks (expects "FAILED CHECKS: none")
node analysis/tradestudy.mjs    # 29-variant trade study -> analysis/tradestudy.json
py -3 analysis/aero/run_all.py  # aerodynamics and CFD -> analysis/aero/aero_results.json (--skip-cfd for the fast tools)
py -3 firmware/tools/check_params.py firmware/vtol_c0.param
node review/build.mjs           # review and companion pages
```

The CAD and simulations need SOLIDWORKS 2025 with Simulation on Windows:

```bash
powershell -ExecutionPolicy Bypass -File cad/build.ps1   # params -> parts, assembly, drawings, meshes
cad/Sim.exe cad/params.txt cad/sim                      # FEA + modal + thermal -> cad/sim/results.txt
```

## Working rules (from CLAUDE.md)

- Every number cites its source: a repo file, a formula shown in the review, or a URL with the date checked.
- Estimates are labelled `est`. Unknowns are shown as "—" and never invented.

## Open items for the team

1. **Approve and order.** Client approval and Order A (test motors, packs, charger) by 2026-11-02.
2. **Flying site and legal path.** Ask UCPD/Risk Services by 2026-11-06 and request Richmond Field Station.
3. **Thrust stand first.** Qualify every motor and ESC before any flight; C0 has no hover motor-out tolerance.
4. **Measure.** Each chapter of the review lists what the team still has to measure; the overview gathers them in one list.
5. **Battery access.** The pod as modelled seals the pack under 35 mm of foam, and its bay allows only ± 5 mm of CG slide. Cut the access well before skinning and settle the bay length (build manual §8.2 items 18–21; [`docs/research/team-crosscheck.md`](docs/research/team-crosscheck.md)).
6. **Bench checks from the team cross-check.** Servo rail with all five servos stalled (12.5 A against the 8 A BEC), per-motor current cap at 26 A, clamp re-torque after 24 h, and the compass interference test (firmware guide 6.3a).
7. **Nautical Wings props.** A sponsorship offer for carbon props was reported by the team in October 2026. If it is confirmed in writing, the reserve rises from $145.45 to about $229.43 (EST). The retail props stay in the BOM until then.

## Team repositories

[DBF-VTOL](https://github.com/davinciucberkeley-collab/DBF-VTOL) holds the team's inventory and electrical overview ([view online](https://claude.ai/artifact/C6JEuXWN4B4Aoay5zHU3Pg)), the Fusion model, the concept models and the Nautical Wings prop spec sheet. It is built on the earlier v0.3.1 sizing. [`docs/research/team-crosscheck.md`](docs/research/team-crosscheck.md) records which of its findings apply to this v0.4.0 design and what was done about each one.
