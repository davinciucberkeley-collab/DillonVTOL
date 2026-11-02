# Proof sheets

One page per claim: the calculation re-run with its numbers, every input and where it comes from, the independent check, and the claims it feeds.

| Claim | Status | Re-run | Statement |
|---|---|---|---|
| [AERO-19](AERO-19.md) | Failed | ✓ | Transition: 2 x 20 s at hover power; transition power 1437 W / 68.4 A; SITL forward transition in 15 s. |
| [AERO-30](AERO-30.md) | Failed | evidence | DESIGN-BASIS / stall-margin.md state S 0.682 m2, chord 284.2 mm, CL_max 1.114, MTOW 6.552 kg, cruise 12.3 min (13.7 build-up), round legs 8.6 min. |
| [MFG-01](MFG-01.md) | Failed | evidence | "Everything here is generated from analysis/results.json ... re-run the build and the CAD follows" (CAD rev D, drawings rev E, FEA all on the current sizing). |
| [MFG-04](MFG-04.md) | Failed | evidence | docs/research/hardware-spec.md is the single fastener/joint spec (hardware.json is its twin). |
| [CFD-10](CFD-10.md) | Unverified | evidence | The inviscid solver's surface CD (0.0371) is not a drag prediction. |
| [MFG-10](MFG-10.md) | Unverified | evidence | Fastener schedule gives torque for every joint (0.15-1.0 N m) applied by the hanging-mass method. |
| [MFG-11](MFG-11.md) | Unverified | evidence | All foam bonds use "foam-safe glue" and structural small parts 5-min epoxy. |
| [AERO-12](AERO-12.md) | Partially Verified | evidence | Zero-lift drag: sizing CD0 0.0447 (0.0266 clean + rotors/booms); component build-up 0.0411. |
| [AERO-13](AERO-13.md) | Partially Verified | ✓ | Cruise L/D is 8.62 (sizing) / 9.48 (build-up) at 18 m/s. |
| [AERO-22](AERO-22.md) | Partially Verified | ✓ | MTOW closes at 6.54 kg (cap < 25 kg met; below the 8-15 kg target of R2). |
| [AERO-24](AERO-24.md) | Partially Verified | evidence | CG at 28 % MAC with the battery at x = +0.188 m; 34.7 % MAC without payload. |
| [AERO-26](AERO-26.md) | Partially Verified | ✓ | Static margin 11.8 % MAC at 28 % CG; 5.2 % with no payload. |
| [AERO-29](AERO-29.md) | Partially Verified | ✓ | 18 m/s cruise is the R11 speed closest to best L/D (V* 12.6 m/s). |
| [AERO-31](AERO-31.md) | Partially Verified | evidence | C0 committed spend $1,896.79 (goods $1,620.67 + 10.25 % tax + $110 shipping), leaving a $103.21 reserve under the $2,000 cap. |
| [CFD-01](CFD-01.md) | Partially Verified | evidence | 7 of 7 full-aircraft cruise cases ran to completion in SU2. |
| [CFD-02](CFD-02.md) | Partially Verified | evidence | Grid convergence at alpha 4 deg: CL 0.4557 / 0.4495 / 0.4929 on 622,283 / 1,795,211 / 4,592,028 tetrahedra. |
| [CFD-05](CFD-05.md) | Partially Verified | evidence | Whole-aircraft lift-curve slope 4.42 /rad (alpha 0-6 deg, elevator 0). |
| [CFD-06](CFD-06.md) | Partially Verified | evidence | CL 0.493 at alpha 4 deg, elevator 0, V 18 m/s (finest mesh). |
| [CFD-08](CFD-08.md) | Partially Verified | evidence | Induced drag from the Trefftz plane CDi 0.0097 at alpha 4 deg. |
| [MFG-02](MFG-02.md) | Partially Verified | evidence | Interference check: 277 interferences = 193 intended insert press fits + 84 slivers (0.45 cm3) - no real clashes. |
| [MFG-03](MFG-03.md) | Partially Verified | evidence | Drawing DBF-DRW-001 rev E: zoned layout with a self-check of overlaps; dimensions, tolerances and fits read from params.txt. |
| [MFG-12](MFG-12.md) | Partially Verified | evidence | Modelled mass 6.36 kg is consistent with the 6.55 kg sizing MTOW, which also carries wiring, ESCs, skins, avionics and payload. |
| [AERO-10](AERO-10.md) | Verified | evidence | Lift-curve slopes: wing VLM 4.71 /rad (vlm.mjs), aircraft AVL 5.03 (no pod) / 5.24 (pod). |
| [AERO-11](AERO-11.md) | Verified | ✓ | Sizing uses Oswald e = 0.80 (AVL inviscid 0.94; build-up fit 0.86). |
| [AERO-25](AERO-25.md) | Verified | evidence | Neutral point 39.8 % MAC (AVL with pod; sizing 39.6 %). |
| [CFD-03](CFD-03.md) | Verified | evidence | SU2's reported forces equal an independent pressure integration over the same wall triangles. |
| [CFD-04](CFD-04.md) | Verified | evidence | Boundary conditions behave: no flow through the symmetry plane; free stream recovered at the far field. |
| [CFD-12](CFD-12.md) | Failed | evidence | At the wall spacing of the 3-D meshes, the SU2 scheme reproduces the inviscid lift of the wing section. |
| [MFG-09](MFG-09.md) | Failed | evidence | Wing bolt J10: M5 x 20 screw end 0.6 mm past the nylock. |
| [AERO-05](AERO-05.md) | Unverified | evidence | Adopted 2-D CL_max of the NACA 2415 is 1.30 (wind-tunnel, Genc, Lock, Kaynak 2008, Re 2e5). |
| [MFG-06](MFG-06.md) | Unverified | evidence | Spar sockets are bonded into hot-wired channels (FT05, 26.0 +-0.5 mm) and the joiner then slides through the saddle into both sockets. |
| [STR-13](STR-13.md) | Unverified | evidence | Wing panel retention bolt J10 (one M5 A2 per side, 70 % chord) only stops the panel sliding off and rotating; bending is in the joiner. |
| [AERO-03](AERO-03.md) | Partially Verified | evidence | SU2 2-D RANS (SA, fully turbulent) NACA 2415 at Re 3.5e5: cd 0.0155 at alpha 2 deg; XFOIL transitional cd 0.0092. |
| [AERO-04](AERO-04.md) | Partially Verified | evidence | SU2 2-D mesh study at alpha 10 deg: GCI_fine 22.5 % on CL (p 0.61), 20.9 % on CD, with the actual refinement ratios (corrected 2026-10-29; the repo previously reported 12.7 % / 15.1 % from an assumed r = sqrt(2)). |
| [AERO-06](AERO-06.md) | Partially Verified | evidence | Trimmed 3-D CL_max is 1.121 (critical-section method on AVL strip loads). |
| [AERO-07](AERO-07.md) | Partially Verified | ✓ | Stall speed at MTOW is 11.75 m/s, meeting R11 (<= 12 m/s) with a 4.1 % CL_max margin. |
| [AERO-23](AERO-23.md) | Partially Verified | ✓ | Wing mass 1.378 kg (foam + tape skin + 0.675 kg aluminium spar/joiner). |
| [MFG-05](MFG-05.md) | Partially Verified | ✓ | Joiner is a slip fit in the spar sockets (FT01): -0.076 / +0.534 mm, measure on receipt and lap or shim. |
| [STR-06](STR-06.md) | Partially Verified | ✓ | Wing root bending moment at ultimate (n 4.5 = 3.0 x 1.5) is 73.6 N m (elliptic lift). |
| [STR-07](STR-07.md) | Partially Verified | ✓ | Joiner 0.875 x 0.058 in at the centreline: 157.5 MPa at ultimate, RF 1.75 on yield (governing wing member). |
| [STR-08](STR-08.md) | Partially Verified | evidence | Spar + joiner FEA at ultimate: 154.7 MPa (2 mm mesh), 146.6 MPa (3 mm); agrees with the 157.5 MPa hand calc (-1.8 %). |
| [STR-09](STR-09.md) | Partially Verified | evidence | Spar tip deflection 23.2 mm at ultimate (FEA). |
| [AERO-01](AERO-01.md) | Verified | ✓ | Cruise chord Reynolds number is 3.50e5 at 18 m/s (stall 2.34e5). |
| [AERO-02](AERO-02.md) | Verified | evidence | XFOIL NACA 2415 at Re 3.5e5 (Ncrit 9): cl_alpha 6.83 /rad, alpha_0L -2.01 deg, Cm_c/4 -0.0535, cd_min 0.0083. |
| [AERO-08](AERO-08.md) | Verified | ✓ | Wing: S 0.676 m2, chord 0.282 m, AR 8.52 on a 2.4 m span. |
| [AERO-09](AERO-09.md) | Verified | ✓ | Cruise CL is 0.478 at 18 m/s. |
| [CFD-09](CFD-09.md) | Verified | ✓ | Cruise chord Reynolds number 3.46e+05: attached, lift-dominated flow, so inviscid CFD is admissible for lift and moment at alpha <= 8 deg. |
| [CFD-11](CFD-11.md) | Failed | evidence | Surface pressure stays within the incompressible stagnation bound (Cp <= 1) everywhere on the aircraft. |
| [AERO-27](AERO-27.md) | Partially Verified | ✓ | Tail volumes V_h 0.35 and V_v 0.030 (S_h 0.0868 m2, S_v 0.0634 m2, l_h 0.768 m). |
| [AERO-28](AERO-28.md) | Partially Verified | evidence | Cruise trim at alpha 3.9 deg with elevator -4.06 deg; stall trim elevator -8.2 deg. |
| [CFD-07](CFD-07.md) | Verified | evidence | Neutral point 42.3 % MAC from the CFD moment slope (static margin 14.3 % at the 28 % CG). |
| [STR-10](STR-10.md) | Unverified | evidence | Boom-to-wing clamps: single motor at Tmax puts ~114 N tension into the rear clamp (57 N per M3 screw into inserts). |
| [STR-12](STR-12.md) | Unverified | evidence | Boom splice J04 (printed plug + 2 x M3 cross-bolts at the rear motor) carries axial and torsional load; no strength figure is given. |
| [MFG-08](MFG-08.md) | Partially Verified | evidence | Splice plug (FT04, 23.2 +-0.2 in 23.622 +-0.203 ID) aligns the tubes; cross-bolts carry the load. |
| [STR-02](STR-02.md) | Partially Verified | evidence | Boom FEA mesh refinement (3 mm -> 1.5 mm) is a convergence check of the 36.8 MPa peak. |
| [STR-03](STR-03.md) | Partially Verified | ✓ | Boom tip deflection at max thrust 2.70 mm FEA vs 2.84 mm hand (-4.8 %). |
| [STR-04](STR-04.md) | Partially Verified | ✓ | Boom first bending mode 34.4 Hz FEA vs 32.3 Hz hand; test pass band 26-41 Hz. |
| [STR-14](STR-14.md) | Partially Verified | evidence | Clamp friction (4 x M3 at 0.5 N m, mu 0.3) gives ~16 N m about the boom axis, so no cross-bolts are needed at the clamps. |
| [MFG-07](MFG-07.md) | Verified | evidence | Split clamps (bore 25.6 +-0.2, 1.2 mm split gap) always grip the 1.000 in tube before the halves touch, for printed bore error < 1.0 mm. |
| [STR-01](STR-01.md) | Verified | ✓ | Front boom arm (1.000 x 0.035 in 6061-T6, 462 mm cantilever) at one lift unit's max thrust 30.7 N: root stress 35.0 MPa hand / 36.8 MPa FEA, RF 8.2 on yield. |
| [XT-01](XT-01.md) | Verified | evidence | The SOLIDWORKS boom study (cad/Sim.cs Boom) is reproduced by an independent mesher and solver. |
| [AERO-18](AERO-18.md) | Failed | ✓ | Hover T/W is 1.92 at MTOW (R13 requires >= 1.6). |
| [STR-05](STR-05.md) | Failed | ✗ | Lift-unit (boom tip) mass is 0.242 kg (motor 165 + ESC 25 + prop 32 + mount 20 g), used in FEA, modal and CG. |
| [THM-03](THM-03.md) | Unverified | ✓ | Lift motor heat 45.6 W in hover = 20 % of 228 W input (EST, 80 % motor+ESC efficiency). |
| [AERO-16](AERO-16.md) | Partially Verified | ✓ | Hover electrical power is 912 W (228 W/motor) at 6.54 kg with 4 x X4110S + 17 in props. |
| [THM-01](THM-01.md) | Partially Verified | ✓ | Lift motor steady-state bound 143.9 deg C (Sim.cs: 45.8 W, h 50) / 163.5 deg C (correlation h 42.9); never reached in a 60-90 s hover. |
| [THM-02](THM-02.md) | Partially Verified | evidence | Film coefficient on the lift motor: 42.9 W/m2K in hover wash (v_i 6.68 m/s), 84.5 W/m2K at 18 m/s cruise (Hilpert). |
| [THM-04](THM-04.md) | Partially Verified | evidence | Lift motor can: 62.7 C after a 60 s hover, 73.8 C at 90 s, mission peak 76.2 C on a 35 C day (limit 80 C EST). |
| [THM-05](THM-05.md) | Partially Verified | evidence | Lift ESC on the boom: 55.5 C after a 60 s hover, 65.1 C mission peak (limit 70 C EST). |
| [AERO-15](AERO-15.md) | Unverified | ✓ | Pusher (X4110S + APC 14x8.5EP) propulsive efficiency 0.60 at cruise. |
| [AERO-14](AERO-14.md) | Partially Verified | ✓ | Cruise electrical power is 262 W (11.8 A) at 18 m/s. |
| [THM-08](THM-08.md) | Partially Verified | evidence | Pusher motor in the PA6-CF cup: 80.4 C after 600 s cruise, over the 80 C limit (EST); PA6-CF parts stay under HDT 173 C. |
| [AERO-17](AERO-17.md) | Partially Verified | ✓ | Hover current 41.1 A at 22.2 V (43.5 A at 21.0 V loaded), inside the 60 A continuous pack assumption. |
| [AERO-20](AERO-20.md) | Partially Verified | ✓ | Cruise time available 15.8 min after 2 min hover + 40 s transition and 20 % reserve (R10 needs 10, design margin 11.5). |
| [AERO-21](AERO-21.md) | Partially Verified | ✓ | Flight pack Ovonic 6S 6500 mAh: 144.3 Wh, 0.82 kg (176 Wh/kg), $69.50 each (2-pack). |
| [THM-06](THM-06.md) | Partially Verified | evidence | Battery pack ends the hot-day mission at 59.2 C against the 60 C limit (sealed bay). |
| [STR-11](STR-11.md) | Unverified | evidence | Landing gear: 0.30 m drop gives 2.43 m/s and 8-32 g on bare legs; expected to fail without compliant feet (no structural analysis). |
| [THM-07](THM-07.md) | Partially Verified | evidence | Flight controller in the closed pod bay reaches 96.8 C at mission end (no limit stated). |
