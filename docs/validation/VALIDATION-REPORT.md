# Engineering validation report

Generated 2026-11-03 01:43 by `analysis/validation/report.py` from the files it cites. House style: docs/reference/REVIEW-STYLE.md.

## Verdict

**79 engineering claims checked: 38 Verified, 40 Partially Verified, 1 Unverified, 0 Failed.** A full-aircraft 3-D CFD now exists: seven runs on three meshes, all finished. It confirms the neutral point and the induced drag the sizing uses. Its absolute lift is still mesh-limited: a 2-D check with the same numerics shows the scheme loses lift at this wall spacing (CFD-12), and only the finest mesh lands within 4 % of AVL. It does not predict drag, because it is inviscid. The design failures cluster in four places: power at full hover thrust, the structural tip mass, stale documents and CAD, and the wing-bolt and joiner specification.

## What was changed

| Area | Change | Files |
|---|---|---|
| Full-aircraft CFD | New: CAD-derived outer mould line, three tetrahedral meshes, SU2 incompressible-Euler runs, independent post-processing and checks | `analysis/cfd3d/` |
| 3-D CFD view | New tab in Aerodynamics: whole aircraft with surface Cp or speed, streamlines, wake planes, symmetry slice, and the real surface, symmetry-plane and cut-volume mesh, with residual histories and results tables | `review/src/cfdviz.js`, `review/src/body.html` |
| Validation matrix | New chapter: claims map on the 3-D CAD model, every claim with equations, inputs, assumptions, evidence, independent check and status, plus manufacturing readiness | `analysis/validation/`, `review/src/claimsmap.js`, `docs/validation/VALIDATION-MATRIX.md` |
| Cross-tool FEA | New: boom study re-solved with gmsh + own C3D10 solver (no SOLIDWORKS code) | `analysis/validation/xtool_boom_fea.py` |
| Agent interface | New: `tools/vtol.py` CLI with JSON output over every pipeline step, and the integration notes | `tools/vtol.py`, `docs/validation/AGENT-INTERFACE.md` |
| Review text | Simulation chapter verdict and the stopped-rotor drag card updated to match the audit | `review/src/body.html` |
| Proof chains | New: every claim split into equations, variables and sources; arithmetic re-run from the cited files, hand-offs between claims value-checked; proof card per claim, dependency graph, equation pointers on the 3-D model | `analysis/validation/proofs.py`, `review/src/proofs.js` |
| Source audit | New: external sources checked value by value; every URL in the docs re-tested | `analysis/validation/source_audit.json`, `link_check.py` |
| Mesh audit | New: CFD meshes measured and scored against published gridding guidelines, with the meshing code behind each rule | `analysis/cfd3d/mesh_audit.py` |
| 3-D CFD view | Continuous slice (drag or sweep, three directions, Cp / speed / vorticity) and a vorticity volume replace the four fixed wake planes | `review/src/cfdviz.js`, `analysis/cfd3d/postprocess.py` |
| Website | 22 chapters merged into 12 with 2-4 tabs each; old links still resolve | `review/tools/restructure.py` |
| Command line | Numbered menu (`VTOL.bat`), `check`, `trace`, `prove`, `strict`, `sources`, `mesh-audit` | `tools/vtol.py` |

## Full-aircraft CFD

Solver: SU2 8.5.0 (win64 OpenMP), INC_EULER, FDS + MUSCL, implicit Euler, Green-Gauss gradients. Conditions: V 18.0 m/s, ρ 1.225 kg/m³, S_ref 0.772658 m², c_ref 0.3219 m, elevator 0.0°, off (no propeller model), sideslip 0.0°. Source: `analysis/cfd3d/out/cfd3d_results.json`.

| Case | Tetrahedra | Iterations | log10 rms(p) drop | CL | CMy | CDi Trefftz | Own CL integration |
|---|---:|---:|---:|---:|---:|---:|---:|
| L1_a4.0 | 1,732,283 | 522 | 3.0 | 0.4846 | -0.0781 | 0.0088 | 0.4846 |
| L2_a0.0 | 3,957,746 | 659 | 8.3 | 0.1673 | -0.0354 | 0.0014 | 0.1673 |
| L2_a2.0 | 3,957,746 | 3000 | 7.1 | 0.3321 | -0.0542 | 0.0046 | 0.3321 |
| L2_a4.0 | 3,957,746 | 1064 | 5.2 | 0.4941 | -0.0723 | 0.0097 | 0.4941 |
| L2_a6.0 | 3,957,746 | 839 | 7.2 | 0.6572 | -0.0931 | 0.0167 | 0.6572 |
| L2_a8.0 | 3,957,746 | 558 | 7.5 | 0.8186 | -0.1165 | 0.0254 | 0.8186 |
| L3_a4.0 | 9,271,143 | 971 | 3.7 | 0.5104 | -0.0728 | 0.0106 | 0.5104 |
| L4_a4.0 | 23,261,119 | 2517 | 4.1 | 0.5229 | -0.0668 | 0.0115 | 0.5229 |

Meshes (`analysis/cfd3d/out/L*/mesh_stats.json`): L1 1,732,283 tets, min SICN 0.024; L2 3,957,746 tets, min SICN 0.027; L3 9,271,143 tets, min SICN 0.032.

| Check | Status | Result |
|---|---|---|
| CFD-01: 8 of 8 full-aircraft cruise cases ran to completion in SU2. | **Verified** | 8 of 8 cases finished with exit code 0; log10 rms(p) fell 3.0-8.3 orders; Cauchy[CL] 4e-06 at the last iteration |
| CFD-02: Grid convergence at alpha 4 deg (L2-L3-L4): CL 0.4941 / 0.5104 / 0.5229 on 3,957,746 / 9,271,143 / 23,261,119 tetrahedra. | **Partially Verified** | GCI_fine on CL 6.83 % (p 1.18); CMy oscillatory or zero change: no asymptotic estimate |
| CFD-03: SU2's reported forces equal an independent pressure integration over the same wall triangles. | **Verified** | largest CL difference 0.00 % |
| CFD-04: Boundary conditions behave: no flow through the symmetry plane; free stream recovered at the far field. | **Verified** | |v_y|/V <= 6.2e-16 on the symmetry plane; far-field |V|/V in 0.999-1.000 |
| CFD-05: Whole-aircraft lift-curve slope 4.67 /rad (alpha 0-6 deg, elevator 0). | **Verified** | CFD 4.67 vs AVL 5.06 /rad (-7.6 %); Helmbold wing alone 5.12 |
| CFD-06: CL 0.523 at alpha 4 deg, elevator 0, V 18 m/s (finest mesh). | **Verified** | +5.9 % against AVL on the finest mesh (L4); CL on L1/L2/L3/L4 0.4846, 0.4941, 0.5104, 0.5229 with a valid GCI (CFD-02) |
| CFD-07: Neutral point 39.7 % MAC from the CFD moment slope (static margin 11.7 % at the 28 % CG). | **Verified** | CFD 39.7 % vs AVL 38.4 % MAC (+1.3 pt; band 3 pt) |
| CFD-08: Induced drag from the Trefftz plane CDi 0.0115 at alpha 4 deg. | **Partially Verified** | Trefftz 0.0115 on the plane 0.3 m behind the wing TE vs CL^2/(pi e AR) 0.0121 (-5 %); planes further aft read 0.0108, 0.0099 as the trailing vortices dissipate on the tetrahedra, so the value depends on where it is measured |
| CFD-09: Cruise chord Reynolds number 3.92e+05: attached, lift-dominated flow, so inviscid CFD is admissible for lift and moment at alpha <= 8 deg. | **Verified** | Re matches the aero package (AERO-01); attached-flow range from the viscous section polar |
| CFD-10: The inviscid solver's surface CD (0.0345) is not a drag prediction: the part above the induced drag is numerical, and it falls with every mesh refinement. | **Verified** | surface CD at alpha 4: L1 0.0524 -> L2 0.0401 -> L3 0.0371 -> L4 0.0345 (falls with refinement); 0.0230 of the L4 value is above the Trefftz induced drag 0.0115 and is numerical (blunt clamp and motor bases, tetrahedra); profile drag stays with analysis/aero/drag_buildup.py |
| CFD-11: Wall Cp above the incompressible stagnation bound (Cp = 1) is a local numerical overshoot: it covers under 1 % of wall nodes in every case and its share falls 6-fold from L1 to L4 but not on every step, so it is a discretisation artefact, not a physical pressure. | **Partially Verified** | share of wall nodes with Cp > 1 at alpha 4: L1 0.74 % -> L2 0.21 % -> L3 0.11 % -> L4 0.13 % (does not fall monotonically); the L3 -> L4 rise is the htail (219 -> 761 nodes, peak Cp 1.54 -> 1.47); largest share in any case 0.74 %; peak Cp 2.18 on the gear (L1_a4.0) at a sharp corner or small leading-edge radius |
| CFD-12: At the 3-D meshes' lifting-surface spacing (mesh rev 2: L2, L3, L4), the SU2 scheme matches XFOIL's inviscid section lift at 4 deg within 5 % and its lift slope within 8 %, approaching XFOIL as the spacing is refined. | **Verified** | section cl at 4 deg vs XFOIL: L1 -14.6 %, L2 -4.3 %, L3 -4.9 %, L4 -2.9 %; lift slope: L1 -10.4 %, L2 -7.7 %, L3 -6.1 %, L4 -4.9 %; the slope rises toward XFOIL with each refinement |

Geometry: 12 defeaturing rules recorded in `analysis/cfd3d/out/oml_fidelity.json` and in the review. Each rebuilt part's bounding box is compared with its STEP solid.

## Cross-tool structural check (boom)

Toolchain: gmsh 4.15.2 2nd-order tetrahedra + numpy/scipy C3D10 solver (this script); SuperLU direct solve. Source: `analysis/validation/xtool_boom_fea.json`.

| Quantity | Independent FE | SOLIDWORKS | Beam theory | Difference |
|---|---:|---:|---:|---:|
| Tip deflection, mm | 3.102 | 3.155 | 3.348 | -1.7 % vs SOLIDWORKS |
| Bending stress at x = 0.10 m, MPa | 27.45 | — | 27.51 | -0.2 % vs beam |
| Peak von Mises (root corner), MPa | 36.6 | 38.6 | — | -5.2 % (both peaks sit on the fully fixed root edge, a stress singularity: they grow with refinement and are not a design value) |
| Mesh change in tip deflection | +0.02 % | | | |

Same inputs, different mesher, element formulation and solver. The tip deflection and the stress away from the root corner agree, so the SOLIDWORKS study is reproduced. Both use the CAD-calibrated tip mass (STR-05).

## Proof chains (every claim re-run from its cited inputs)

Source: `analysis/validation/proofs.json` (`proofs.py`, 2026-11-03 01:43). Each input is read from the file it cites when the script runs; constants name their source.

- 29 claims have closed-form arithmetic; 29 re-run to the claimed number. Not reproduced: none.
- 33 hand-offs from one claim's result to another's input; 33 carry the same number. Stale: none.
- 50 claims have no closed-form arithmetic (convergence, CAD checks, drawings); their proof is the evidence files and the independent check.
- One page per claim: `docs/validation/proofs/` (`py tools/vtol.py prove all`).

## External sources

Source: `analysis/validation/source_audit.json` (value-by-value check against each page or PDF). 23 sources: confirmed 10, not fetchable 8, not found on page 1, partially confirmed 1, unreachable 3. 51 of 79 claims rest on at least one.
Every URL in the docs (`link_check.py`): 599 of 691 load, 4 dead, 72 block automated checks. Dead: https://avesis.erciyes.edu.tr/yayin/0e967406-3720-4460-b125-1dec2b27685c, https://www.cstsales.com/carbon_tube.html, https://www.deltaquad.com/cargo, https://www.nasa.gov/wp-content/uploads/2015/10/s3001_guidelines_for_risk_management_-_ver_g_-_10-25-2017.pdf.

## CFD mesh against published standards

Source: `analysis/cfd3d/out/mesh_audit.json` (`mesh_audit.py`, 2026-11-03 01:24). 21 pass, 32 fail, 19 do not apply to an inviscid tetrahedral mesh. Mesh rev 2. All 4 levels are valid (no inverted cells), 1.32 / 1.33 / 1.36 apart (grid-study minimum 1.3), and the far field is 105 reference chords away (guideline 100). The wing LE spacing refines with the level (0.91 / 0.62 / 0.44 / 0.32 % c) but is still above the 0.1 % c viscous-grid guideline, which this inviscid study is not built to meet. CL at alpha 4 on L2-L3-L4 is in the asymptotic range (e32/e21 = 1.31 > 1), so CFD-02 has a valid GCI. Regional spacing ratios deviate from the global ratio by up to 21 % (worst: wake_3c, L1->L2). Standards met on some level: STD-01, STD-05, STD-07, STD-11, STD-12, STD-13, STD-14, STD-15, STD-16; not met: STD-02, STD-03, STD-04, STD-05, STD-06, STD-07, STD-14, STD-15.

What a passing mesh needs:

- Far field at >= 100 semispans (120 m) for DPW-8; far cells can stay large, so the extra cost is small.
- Wing and H-tail chordwise spacing near 0.1 % local chord at LE and TE (0.1 % of the 0.322 m chord = 0.32 mm), graded to coarser cells mid-chord (anisotropic surface mesh), for a viscous-grade grid.
- Pod nose spacing under 1 % c_ref (3.22 mm) for DPW-8; L4 is at 1.14 % today.

Standards: AIAA DPW-4 gridding guidelines, item 2g (https://www.aiaa-dpw.org/Workshop4/gridding_guidelines_4.html, checked 2026-11-01); AIAA DPW-8/AePW-4 gridding guidelines v3 (2024-07-01), CRM slide (https://www.aiaa-dpw.org/ref/gridding_guidelines_v3_07012024.pdf, checked 2026-11-01); AIAA DPW-8/AePW-4 gridding guidelines v3, CRM slide (https://www.aiaa-dpw.org/ref/gridding_guidelines_v3_07012024.pdf, checked 2026-11-01); AIAA DPW-4 gridding guidelines, item 2h-i (medium grid) (https://www.aiaa-dpw.org/Workshop4/gridding_guidelines_4.html, checked 2026-11-01); AIAA DPW-4 gridding guidelines, item 2h-iv (https://www.aiaa-dpw.org/Workshop4/gridding_guidelines_4.html, checked 2026-11-01); AIAA DPW-4 gridding guidelines, item 2j; DPW-8 v3 'Wing TE base >> 8 cells' (https://www.aiaa-dpw.org/Workshop4/gridding_guidelines_4.html, checked 2026-11-01); AIAA DPW-8/AePW-4 gridding guidelines v3, wall-normal slide (https://www.aiaa-dpw.org/ref/gridding_guidelines_v3_07012024.pdf, checked 2026-11-01); AIAA DPW-8/AePW-4 gridding guidelines v3, wall-normal slide; DPW-4 item 2f (https://www.aiaa-dpw.org/ref/gridding_guidelines_v3_07012024.pdf, checked 2026-11-01); Celik et al. 2008, J. Fluids Eng. 130(7) 078001, Step 2 (https://qa12.asme.org/wwwasmeorg/media/ResourceFiles/Shop/Journals/JFENumAccuracy.pdf, checked 2026-11-01); NASA NPARC Alliance V&V, 'Examining Spatial (Grid) Convergence' (https://www.grc.nasa.gov/www/wind/valid/tutorial/spatconv.html, checked 2026-11-01); Celik et al. 2008, Step 3 (https://qa12.asme.org/wwwasmeorg/media/ResourceFiles/Shop/Journals/JFENumAccuracy.pdf, checked 2026-11-01); Celik et al. 2008, Step 2; DPW-4 item 2e (https://qa12.asme.org/wwwasmeorg/media/ResourceFiles/Shop/Journals/JFENumAccuracy.pdf, checked 2026-11-01); AIAA DPW-4 gridding guidelines, item 2c (https://www.aiaa-dpw.org/Workshop4/gridding_guidelines_4.html, checked 2026-11-01); gmsh 4.15.2 API docstring, getElementQualities (installed package) (py -c "import gmsh; help(gmsh.model.mesh.getElementQualities)", checked 2026-11-01).

## Failed claims


## Manufacturing readiness

- **Wing (panels, spar sockets, joiner, saddle, wing bolt)**: Not ready. Blocking: No joiner-through-saddle jig when bonding the spar sockets: up to 0.48 mm root-face gap and 0.09 deg panel error WC (MFG-06); Drawings built one iteration back (chord 320.8 vs 321.9 mm, tail chord -0.60 %); 22 layout overlaps; no foam tolerance class; unchecked (MFG-01, MFG-03); Adhesive product/cure unspecified (MFG-11); S01 proof schedule is elliptic; AVL loading is 7 % higher; hard landing loads the joiner to ~105 N m EST (STR-06, STR-07, STR-11)
- **Booms (tubes, splice, boom clamps, wing hardpoints)**: Needs minor specification. Blocking: Front clamp upper half overlaps the bonded spar collar (2 x 3.9 mm3, unexplained) (MFG-02); Splice free play up to 1.2 deg, no straightness check (MFG-08, STR-12); Insert pull-out (C03) and hardpoint-to-foam bond strength unknown for 96-127 N clamp loads (STR-10)
- **Lift propulsion (motor mounts, motors, props, ESCs)**: Needs minor specification. Blocking: Prop screw length waits on JeeFly hub thickness (M5); Motor can mission peak 75.2 C vs 80 C EST (4.8 K) at 25 C; lumped motor-alone bound 80.6 C; C08 required before flight (THM-03/04); PA6-CF floor crush/creep under 41 MPa screw bearing unknown (C04, THM-08)
- **Landing gear (legs, gear clamps, feet, fairings)**: Needs minor specification. Blocking: Landing model (rigid clamp and foot) not yet checked by the S06 drop test (STR-11); Hard-landing joiner moment ~105 N m EST exceeds the flight ultimate case; inspect after S06 (S07, STR-07)
- **Tail (stabiliser, fins, rudders, tail clamps, servos)**: Needs minor specification. Blocking: Rudder pushrod passes through Control_Horn-1 in the CAD (101 mm3, unexplained) (MFG-02); Servo tab hole pattern EST until M6; Tail aero loads not computed for the splice/clamps (STR-12)
- **Fuselage pod (foam body, saddle-to-pod, canopy, trays)**: Not ready. Blocking: Pod internal structure (frames, rails, bay walls) undefined in CAD (BUILD-MANUAL 8.2 #8); inserts for J11/J13 have nothing designed to sit in; FC hole pattern unknown (M6); Canopy overlaps the pod in the as-built CAD (22 entries, 154 mm3); re-check after the rebuild (MFG-02); Battery-bay vents not in the CAD; pack passes at 25 C only for C11-accepted packs, and c_p is an estimate (THM-06)
- **Cruise propulsion (pusher motor, cup, adapter, prop)**: Needs minor specification. Blocking: Pusher can 76.0 C after 600 s cruise, steady 77.3 C vs 80 C EST at 25 C; losses and limit are estimates (C09, F08, THM-08); APC hub 11.2 mm vs 8 mm modelled; adapter screw length EST; Tail-ring cut that removed nothing (verification.txt warning)
- **Battery and avionics installation**: Needs minor specification. Blocking: FC 60.3 C at mission end vs 85 C STM32F405 rating; steady bound 89.7 C passes 85 C after ~45 min powered: limit ground power-on time (THM-07); Pack 53.2 C at mission end for <= 6.0 mOhm/cell (C11) at <= 25 C; reaches 60 C at 7.3 mOhm/cell or c_p 908 J/kgK (THM-06); CoreWing hole pattern sources conflict (hardware.json unknowns)
- **Fasteners, inserts and adhesives (aircraft-wide)**: Needs minor specification. Blocking: 11 of 13 torques EST pending C02/C04; no torque tool (MFG-10); Adhesive products/cure/prep unspecified (MFG-11); Drawing sheets carry the rev E fastener sizes only after the CAD rebuild (MFG-01c)

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
3. Proof and validation → *Claims map*: click an equation pointer (STR-07 joiner stress), hover a symbol in the proof to see where its number comes from; *Proof chains*: follow AERO-22 (mass) through to AERO-20 (cruise time).
4. Double-click `VTOL.bat`, option 3, `THM-01`: the stale convection coefficient. Then `py tools/vtol.py strict`, which blocks a release on it.
5. Aerodynamics → 3-D CFD → mesh scorecard: why the CFD lift is mesh-limited, rule by rule with the meshing code.

