# Engineering validation report

Generated 2026-10-29 05:01 by `analysis/validation/report.py` from the files it cites. House style: docs/reference/REVIEW-STYLE.md.

## Verdict

**78 engineering claims checked: 14 Verified, 44 Partially Verified, 11 Unverified, 9 Failed.** A full-aircraft 3-D CFD now exists: seven runs on three meshes, all finished. It confirms the neutral point and the induced drag the sizing uses. Its absolute lift is still mesh-limited: a 2-D check with the same numerics shows the scheme loses lift at this wall spacing (CFD-12), and only the finest mesh lands within 4 % of AVL. It does not predict drag, because it is inviscid. The design failures cluster in four places: power at full hover thrust, the structural tip mass, stale documents and CAD, and the wing-bolt and joiner specification.

## What was changed

| Area | Change | Files |
|---|---|---|
| Full-aircraft CFD | New: CAD-derived outer mould line, three tetrahedral meshes, SU2 incompressible-Euler runs, independent post-processing and checks | `analysis/cfd3d/` |
| 3-D CFD view | New tab in Aerodynamics: whole aircraft with surface Cp or speed, streamlines, wake planes, symmetry slice, and the real surface, symmetry-plane and cut-volume mesh, with residual histories and results tables | `review/src/cfdviz.js`, `review/src/body.html` |
| Validation matrix | New chapter: claims map on the 3-D CAD model, every claim with equations, inputs, assumptions, evidence, independent check and status, plus manufacturing readiness | `analysis/validation/`, `review/src/claimsmap.js`, `docs/validation/VALIDATION-MATRIX.md` |
| Cross-tool FEA | New: boom study re-solved with gmsh + own C3D10 solver (no SOLIDWORKS code) | `analysis/validation/xtool_boom_fea.py` |
| Agent interface | New: `tools/vtol.py` CLI with JSON output over every pipeline step, and the integration notes | `tools/vtol.py`, `docs/validation/AGENT-INTERFACE.md` |
| Review text | Simulation chapter verdict and the stopped-rotor drag card updated to match the audit | `review/src/body.html` |

## Full-aircraft CFD

Solver: SU2 8.5.0 (win64 OpenMP), INC_EULER, FDS + MUSCL, implicit Euler, Green-Gauss gradients. Conditions: V 18.0 m/s, ρ 1.225 kg/m³, S_ref 0.682022 m², c_ref 0.2842 m, elevator 0.0°, off (no propeller model), sideslip 0.0°. Source: `analysis/cfd3d/out/cfd3d_results.json`.

| Case | Tetrahedra | Iterations | log10 rms(p) drop | CL | CMy | CDi Trefftz | Own CL integration |
|---|---:|---:|---:|---:|---:|---:|---:|
| L1_a4.0 | 622,283 | 801 | 5.2 | 0.4557 | -0.0789 | 0.0080 | 0.4557 |
| L2_a0.0 | 1,795,211 | 2500 | 6.0 | 0.1389 | -0.0149 | 0.0011 | 0.1389 |
| L2_a2.0 | 1,795,211 | 1794 | 8.2 | 0.2953 | -0.0361 | 0.0036 | 0.2953 |
| L2_a4.0 | 1,795,211 | 2349 | 5.3 | 0.4495 | -0.0578 | 0.0079 | 0.4495 |
| L2_a6.0 | 1,795,211 | 719 | 6.4 | 0.6013 | -0.0813 | 0.0137 | 0.6013 |
| L2_a8.0 | 1,795,211 | 1183 | 7.5 | 0.7499 | -0.1076 | 0.0209 | 0.7499 |
| L3_a4.0 | 4,592,028 | 1351 | 4.8 | 0.4929 | -0.0667 | 0.0097 | 0.4929 |

Meshes (`analysis/cfd3d/out/L*/mesh_stats.json`): L1 622,283 tets, min SICN 0.011; L2 1,795,211 tets, min SICN 0.020; L3 4,592,028 tets, min SICN 0.027.

| Check | Status | Result |
|---|---|---|
| CFD-01: 7 of 7 full-aircraft cruise cases ran to completion in SU2. | **Partially Verified** | 7 of 7 cases finished with exit code 0; log10 rms(p) fell 4.8-8.2 orders; Cauchy[CL] 1e-05 at the last iteration |
| CFD-02: Grid convergence at alpha 4 deg: CL 0.4557 / 0.4495 / 0.4929 on 622,283 / 1,795,211 / 4,592,028 tetrahedra. | **Partially Verified** | GCI_fine on CL not computable: oscillatory or zero change: no asymptotic estimate; CMy oscillatory or zero change: no asymptotic estimate |
| CFD-03: SU2's reported forces equal an independent pressure integration over the same wall triangles. | **Verified** | largest CL difference 0.00 % |
| CFD-04: Boundary conditions behave: no flow through the symmetry plane; free stream recovered at the far field. | **Verified** | |v_y|/V <= 4.0e-16 on the symmetry plane; far-field |V|/V in 0.999-1.000 |
| CFD-05: Whole-aircraft lift-curve slope 4.42 /rad (alpha 0-6 deg, elevator 0). | **Partially Verified** | CFD 4.42 vs AVL 5.26 /rad (-16.1 %); Helmbold wing alone 5.30; the gap matches the under-resolution the 2-D check measures at this wall spacing (CFD-12), so the CFD slope is a lower bound, not evidence against AVL |
| CFD-06: CL 0.493 at alpha 4 deg, elevator 0, V 18 m/s (finest mesh). | **Partially Verified** | -4.1 % against AVL on the finest mesh (L3); CL on L1/L2/L3 0.4557, 0.4495, 0.4929 is not monotone, so the agreement is not yet grid-independent |
| CFD-07: Neutral point 42.3 % MAC from the CFD moment slope (static margin 14.3 % at the 28 % CG). | **Verified** | CFD 42.3 % vs AVL 39.8 % MAC |
| CFD-08: Induced drag from the Trefftz plane CDi 0.0097 at alpha 4 deg. | **Partially Verified** | Trefftz 0.0097 on the plane 0.3 m behind the wing TE vs CL^2/(pi e AR) 0.0095 (+1 %); planes further aft read 0.0089, 0.0080 as the trailing vortices dissipate on the tetrahedra, so the value depends on where it is measured |
| CFD-09: Cruise chord Reynolds number 3.46e+05: attached, lift-dominated flow, so inviscid CFD is admissible for lift and moment at alpha <= 8 deg. | **Verified** | Re matches the aero package (AERO-01); attached-flow range from the viscous section polar |
| CFD-10: The inviscid solver's surface CD (0.0371) is not a drag prediction. | **Unverified** | surface CD minus the Trefftz CDi is numerical (blunt clamp and motor bases, coarse tetrahedra); profile drag stays with analysis/aero/drag_buildup.py |
| CFD-11: Surface pressure stays within the incompressible stagnation bound (Cp <= 1) everywhere on the aircraft. | **Failed** | 2.41 on the htail (L2_a8.0); L1_a4.0: 2615 wall nodes above 1, L2_a0.0: 1938 wall nodes above 1, L2_a2.0: 2201 wall nodes above 1, L2_a4.0: 1846 wall nodes above 1, L2_a6.0: 1839 wall nodes above 1, L2_a8.0: 1872 wall nodes above 1, L3_a4.0: 1066 wall nodes above 1. Stagnation overshoot where the 0.9 mm horizontal-tail leading-edge radius and sharp box corners are resolved by only 1-2 mm elements |
| CFD-12: At the wall spacing of the 3-D meshes, the SU2 scheme reproduces the inviscid lift of the wing section. | **Failed** | at the L1/L2 wall spacing the section lift slope is -19 / -14 % against XFOIL inviscid; it closes to -5 % at 603 wall edges. Numerical dissipation at this resolution acts like viscous decambering, which explains most of the 3-D lift-slope gap to AVL (CFD-05): absolute lift from the 3-D runs is mesh-limited |

Geometry: 12 defeaturing rules recorded in `analysis/cfd3d/out/oml_fidelity.json` and in the review. Each rebuilt part's bounding box is compared with its STEP solid.

## Cross-tool structural check (boom)

Toolchain: gmsh 4.15.2 2nd-order tetrahedra + numpy/scipy C3D10 solver (this script); SuperLU direct solve. Source: `analysis/validation/xtool_boom_fea.json`.

| Quantity | Independent FE | SOLIDWORKS | Beam theory | Difference |
|---|---:|---:|---:|---:|
| Tip deflection, mm | 2.652 | 2.703 | 2.840 | -1.9 % vs SOLIDWORKS |
| Bending stress at x = 0.10 m, MPa | 25.80 | — | 25.80 | +0.0 % vs beam |
| Peak von Mises (root corner), MPa | 36.0 | 36.8 | — | -2.0 % (both peaks sit on the fully fixed root edge, a stress singularity: they grow with refinement and are not a design value) |
| Mesh change in tip deflection | +0.04 % | | | |

Same inputs, different mesher, element formulation and solver. The tip deflection and the stress away from the root corner agree, so the SOLIDWORKS study is reproduced. The study's load case is the separate issue: its tip mass is 37 % low (STR-05).

## Failed claims

- **AERO-19** (Whole aircraft): Transition: 2 x 20 s at hover power; transition power 1437 W / 68.4 A; SITL forward transition in 15 s. *The repo's own transition current (68 A) and SITL peak (79 A) exceed its 60 A continuous pack assumption; no transition corridor / wing-lift-vs-speed analysis exists.* Next: Do a transition-corridor calc and bench-test pack at 80 A for 20 s.
- **AERO-30** (Whole aircraft): DESIGN-BASIS / stall-margin.md state S 0.682 m2, chord 284.2 mm, CL_max 1.114, MTOW 6.552 kg, cruise 12.3 min (13.7 build-up), round legs 8.6 min. *The governing docs quote numbers from the 20 m/s design that current outputs do not reproduce (15.8 vs 12.3 min; S 0.676 vs 0.682; CL_max 1.121 vs 1.114).* Next: Regenerate DESIGN-BASIS numbers from results.json / aero_results.json after closing the loop.
- **MFG-01** (Whole aircraft): "Everything here is generated from analysis/results.json ... re-run the build and the CAD follows" (CAD rev D, drawings rev E, FEA all on the current sizing). *CAD, FEA inputs and the drawing set are one sizing behind (chord +0.84 %, MTOW +0.21 %, boom arm +0.36 %, root moment +0.21 %). Small, conservative, but the "CAD follows" claim is false today and the drawings carry a 284.2 mm chord.* Next: Run build.ps1 (params.mjs -> BuildVtol -> Drawings -> Sim) and bump CAD to rev E / drawings to rev F, or freeze the sizing.
- **MFG-04** (Whole aircraft): docs/research/hardware-spec.md is the single fastener/joint spec (hardware.json is its twin). *The joint sections the builders read contradict the fits table and the CAD in four places; J11 in particular tells the team to glue in a part that must slide out for transport.* Next: Rewrite J05, J07, J10, J11 from params.txt; add a revision line.
- **CFD-12** (Wing): At the wall spacing of the 3-D meshes, the SU2 scheme reproduces the inviscid lift of the wing section. *at the L1/L2 wall spacing the section lift slope is -19 / -14 % against XFOIL inviscid; it closes to -5 % at 603 wall edges. Numerical dissipation at this resolution acts like viscous decambering, which explains most of the 3-D lift-slope gap to AVL (CFD-05): absolute lift from the 3-D runs is mesh-limited* Next: Re-mesh the wing, tail and fins at about 2 mm wall spacing (about 300 wall edges per section) and re-run alpha 0, 4, 8; keep the other parts at the current sizes.
- **MFG-09** (Wing): Wing bolt J10: M5 x 20 screw end 0.6 mm past the nylock. *Nominal 0.57 mm is already below one thread pitch; RSS range -0.38 to +1.52 mm, WC -1.33 to +2.47 mm: a real chance the nylon insert is not engaged on the only retention bolt of each panel.* Next: Use M5 x 25 with a deeper nut pocket, or a steel insert/threaded plate; verify >= 2 threads past the nylon on first article.
- **CFD-11** (Tail): Surface pressure stays within the incompressible stagnation bound (Cp <= 1) everywhere on the aircraft. *2.41 on the htail (L2_a8.0); L1_a4.0: 2615 wall nodes above 1, L2_a0.0: 1938 wall nodes above 1, L2_a2.0: 2201 wall nodes above 1, L2_a4.0: 1846 wall nodes above 1, L2_a6.0: 1839 wall nodes above 1, L2_a8.0: 1872 wall nodes above 1, L3_a4.0: 1066 wall nodes above 1. Stagnation overshoot where the 0.9 mm horizontal-tail leading-edge radius and sharp box corners are resolved by only 1-2 mm elements* Next: Refine the tail and fin leading edges (curvature sizing below 0.3 mm) and re-run; check the overshoot falls with refinement.
- **AERO-18** (Lift propulsion): Hover T/W is 1.92 at MTOW (R13 requires >= 1.6). *T/W 1.92 needs ~111 A; at the repo's own 60 A pack limit T/W is 1.27, below R13's 1.6, and at storage-low voltage it is lower still.* Next: Measure pack + 4-motor full-throttle current/thrust on the stand; either justify > 90 A or change pack/prop.
- **STR-05** (Lift propulsion): Lift-unit (boom tip) mass is 0.242 kg (motor 165 + ESC 25 + prop 32 + mount 20 g), used in FEA, modal and CG. *The modelled PA6-CF motor mount is 88.7 g against the 20 g allowance, so the real tip mass is ~37 % higher than every structural and modal input uses.* Next: Feed CAD part masses back into sizing.mjs (mMount ~0.085 kg) and re-run sizing, modal, CG and landing checks.

## Manufacturing readiness

- **Wing (panels, spar sockets, joiner, saddle, wing bolt)**: Not ready. Blocking: No alignment jig for bonding the spar sockets coaxial with the saddle bores: 0.45 mm WC offset vs 0.23 mm clearance (MFG-06); J10 nylock engagement 0.57 mm nominal, can be negative (MFG-09); hardware-spec J11 says bond the joiner; FT06 says slip fit (MFG-04); Drawing sheet 4 at chord 284.2 mm vs current sizing 281.8 mm; no foam tolerance class; 6 layout overlaps (MFG-01, MFG-03); Adhesive product/cure unspecified (MFG-11); Root moment on elliptic loading; S01 proof schedule inherits it (STR-06)
- **Booms (tubes, splice, boom clamps, wing hardpoints)**: Needs minor specification. Blocking: F06 M3 x 35 overruns the spar-collar insert hole ~1.0 mm (MFG-02); Splice free play up to 1.2 deg, no straightness check (MFG-08, STR-12); Insert pull-out and hardpoint-to-foam bond strength unknown for 103-134 N clamp loads (STR-10); J05 load check on stale coordinates (MFG-04)
- **Lift propulsion (motor mounts, motors, props, ESCs)**: Needs minor specification. Blocking: Mount mass 88.7 g vs 20 g allowance: tip mass +37 %, modal/landing inputs stale (STR-05); Prop screw length waits on JeeFly hub thickness (M5); Motor thermal margin 3.8 K on estimated losses (THM-03/04); C08 required before flight; PA6-CF floor crush/creep under 41 MPa screw bearing unknown (M3, THM-08)
- **Landing gear (legs, gear clamps, feet, fairings)**: Not ready. Blocking: Compliant feet not designed and not in the BOM; bare legs 8-32 g, front boom yields above ~20 g (STR-11); No landing load case in FEA; Gear clamp nylock pockets undersize (MFG-02)
- **Tail (stabiliser, fins, rudders, tail clamps, servos)**: Needs minor specification. Blocking: Horn screw holes not modelled (10 screw-through-solid interferences) (MFG-02); Servo tab hole pattern EST until M6; Tail aero loads not computed for the splice/clamps (STR-12)
- **Fuselage pod (foam body, saddle-to-pod, canopy, trays)**: Not ready. Blocking: Pod internal structure (frames, rails, bay walls) undefined in CAD (BUILD-MANUAL 8.2 #8); inserts for J11/J13 have nothing designed to sit in; FC hole pattern unknown (M6); Battery-bay vents recommended by the thermal study not in CAD (THM-06)
- **Cruise propulsion (pusher motor, cup, adapter, prop)**: Needs minor specification. Blocking: Pusher can 80.4 C vs 80 C limit EST; decision moved to F08 (THM-08); APC hub 11.2 mm vs 8 mm modelled; adapter screw length EST; Tail-ring cut that removed nothing (verification.txt warning)
- **Battery and avionics installation**: Needs minor specification. Blocking: FC predicted 90-97 C in the closed bay with no limit or mitigation (THM-07); Pack ends at 59 C vs 60 C limit; IR acceptance rule needed (THM-06); CoreWing hole pattern sources conflict (hardware.json unknowns)
- **Fasteners, inserts and adhesives (aircraft-wide)**: Needs minor specification. Blocking: All torques EST; insert torque-out unknown; no torque tool (MFG-10); Adhesive products/cure/prep unspecified (MFG-11); Spec text contradicts CAD in J05/J07/J10/J11 (MFG-04)

## What remains unverified or not run

- Hover and transition CFD: need rotor modelling (actuator disk in SU2 is compressible-only; resolved rotors need sliding/overset meshes). Not run, and not shown as if it were.
- Viscous full-aircraft CFD (drag, separation, stall): needs prism layers on every part; the drag build-up stays the drag source.
- Power-on cruise (pusher slipstream), trimmed elevator, sideslip: not modelled.
- CalculiX is not installed, so the team's Gmsh/CalculiX workflow was not run; the gmsh mesh and load case in `xtool_boom_fea.py` are the hand-off.
- Prices could not be re-checked where vendor sites rate-limited (see AERO-31).

## Next steps (in order)

1. Measure pack + four-motor full-throttle current and thrust on the stand (AERO-18, AERO-19): decides whether hover T/W meets R13.
2. Feed CAD part masses back into the sizing (motor mount 88.7 g vs 20 g allowance), then re-run sizing, FEA, modal, CG and a landing case (STR-05, STR-11).
3. Regenerate CAD, drawings and FEA on the current sizing; rewrite the contradicting joint specs J05/J07/J10/J11; lengthen the wing bolt (MFG-01, MFG-04, MFG-09).
4. Re-mesh the wing, tail and fins at about 2 mm wall spacing with finer leading edges and re-run α 0/4/8 (CFD-12, CFD-11, CFD-02); then a viscous full-aircraft run for drag.
5. Install CalculiX and run the boom and spar cases from the gmsh meshes as a second independent structural solver.

## Demonstration for the weekly meeting (10 minutes)

1. Aerodynamics → *Whole aircraft: 3-D CFD*: rotate the aircraft, switch α 0–8°, toggle *Surface mesh* and *Volume cut* to show the real computational mesh, open the residual history.
2. The results table: SU2's CL against our own pressure integration, the three-mesh study (not yet monotone), CFD against AVL, and the 2-D check that explains the gap (CFD-12).
3. Validation matrix → *Claims map*: click the wing, open one Verified and one Failed claim, show the evidence files and the independent check.
4. `py tools/vtol.py claims --status Failed` and `py tools/vtol.py compare HEAD~4`: how an agent queries and diffs the design.

