# Heat dissipation: lift units, pod (battery, avionics) and pusher (C0 frozen design, 18 m/s cruise, run of 2026-11-02)

Baseline: concept C0, 4-lift twin-boom quadplane. Heat sources are the four SunnySky X4110S lift motors with their LANRC BLHeli_S 45 A ESCs on the booms (`docs/purchasing/C0_BOM.csv`), a fifth X4110S as the pusher in the PA6-CF cup at the pod tail (`docs/purchasing/C0_BOM.csv` "X4110S 400KV (pusher)", `analysis/sizing.mjs` PUSHER = X4110S), the Ovonic 6S 6500 pack in the foam battery bay, and the flight controller in the avionics bay. Loads are taken from `analysis/results.json` (generated 2026-11-01, C0 sized, as recorded in `analysis/thermal/thermal_inputs.json` generated 2026-11-02: MTOW 7.44 kg, hover 1,131.3 W, 282.8 W per lift unit, cruise 295.4 W, transition 1,722 W, pack currents 53.9 / 82.0 / 13.3 A in hover / transition / cruise, cruise available 12.1 min), geometry from `cad/params.txt` and `docs/research/hardware-spec.md`. Every run is reproducible: `py analysis/thermal/thermal_inputs.py` (loads, film coefficients) → `cad\Thermal.exe cad\params.txt analysis\thermal\thermal_inputs.json cad\sim\thermal` (SOLIDWORKS Simulation) → `py analysis/thermal/thermal_report.py` (renders, findings table, `analysis/thermal/thermal_results.json`).

History (one line): earlier runs (2026-10-25, 2026-10-27) used the 6.55 kg design, a 35 °C "hot day" that no requirement set, a 7.5 mΩ/cell pack and 3.5 W lumped on the FC; the 2026-11-02 run uses the frozen 7.44 kg loads, the 25 °C ceiling of `docs/DESIGN-BASIS.md` R21, the 6.0 mΩ/cell C11 acceptance limit and 2.0 W on the FC board only, because those are now the requirement, the bench acceptance value and the itemised estimate (`analysis/thermal/thermal_inputs.py` comments).

Verdict first (design ambient 25 °C = R21 ceiling; standard day 20 °C = design value − 5 K because the problem is linear; every temperature is the maximum in the body from `cad/sim/thermal/results.txt`, table as printed by `py analysis/thermal/thermal_report.py`):

| Component | Case | Peak at 25 °C | 20 °C day | Limit | Margin | Status |
|---|---|---|---|---|---|---|
| Lift motor can | hover 60 s (flight rule, ≤ 60 s per hover) | **59 °C** | 54 °C | 80 °C EST (test plan) | +21 K | pass |
| Lift motor can | hover 90 s (bench C08) | 73 °C | 68 °C | 80 °C EST | +7 K | pass, < 10 K margin |
| Lift motor can | mission peak (end of hover + transition, 80 s) | **75 °C** | 70 °C | 80 °C EST | +5 K | pass, < 10 K margin |
| Lift motor can | steady hover (upper bound, never reached) | 185 °C | 180 °C | 80 °C EST | −105 K | bound only |
| Lift ESC (boom underside, prop wash) | hover 60 s | 50 °C | 45 °C | 70 °C EST (test plan) | +20 K | pass |
| Lift ESC | hover 90 s (C08) | 60 °C | 55 °C | 70 °C EST | +10 K | pass |
| Lift ESC | mission peak (80 s) | **62 °C** | 57 °C | 70 °C EST | +8 K | pass, < 10 K margin |
| Lift ESC | steady hover (bound) | 98 °C | 93 °C | 70 °C EST | −28 K | bound only |
| PA6-CF motor mount | mission peak | **73 °C** | 68 °C | HDT 173 °C | +100 K | pass |
| PA6-CF motor mount | steady hover (bound) | 185 °C | 180 °C | HDT 173 °C | −12 K | bound only (a PETG mount, HDT 68 °C, fails from about 82 s of hover) |
| 6061 boom at the clamp | any | 26 °C | 21 °C | — | — | the PETG boom clamps never see heat |
| Battery pack (R_pack at the 6.0 mΩ/cell C11 limit, sealed bay) | mission end | **53 °C** | 48 °C | 60 °C (test plan) | +7 K | pass, < 10 K margin |
| Flight controller board (2.0 W, sealed bay) | mission end | 60 °C | 55 °C | 85 °C (STM32F405RGT6 rating) | +25 K | pass |
| XPS pod foam | mission (bounded by its hottest neighbour) | 60 °C | 55 °C | 74 °C max use | +14 K | pass |
| Pusher motor can (X4110S) | after 600 s cruise | **76 °C** | 71 °C | 80 °C EST | +4 K | pass, < 10 K margin |
| Pusher motor can | steady cruise (bound) | 77 °C | 72 °C | 80 °C EST | +3 K | bound only |
| PA6-CF pusher cup | steady cruise (bound) | 77 °C | 72 °C | HDT 173 °C | +96 K | pass |

Conclusions: (1) at 25 °C every component passes, and the three that set the ceiling — lift motor (+5 K), pusher (+4 K) and pack (+7 K) — are why R21 is 25 °C: every temperature rises 1 K per 1 K of ambient, so a 30 °C day would put the pusher 1 K over its limit and the lift motor at its limit; (2) the lift motor, its ESC and the pusher margins rest on estimated losses (20 % of input, 4 %, 15 % × 75 %), so C08 (lift unit) and the G03 / F08 IR checks (pusher) must measure them, and TEST-PLAN C08 lowers the R21 ceiling if the measured lift-unit rise is larger than modelled; (3) the battery bay is effectively adiabatic (XPS k 0.029 W/mK), so the pack rise is set by its resistance: 4.7 K per mΩ/cell over a mission, which is why C11 rejects packs above 6.0 mΩ/cell and §6 of the test plan limits the pack start temperature. Printed PA6-CF parts stay ≥ 96 K under their HDT in flight; PETG would not be acceptable for the motor mounts (73 °C peak vs HDT 68 °C) but is fine for the boom clamps (boom at 26 °C).

Images (`analysis/thermal/img/`, thermal-camera style, inferno scale from the ambient to the case maximum, hot spot marked): `lift_unit_hover_30_60_90.png` (a), `lift_unit_mission.png` (a, end of hover / end of transition / end of mission), `lift_unit_steady.png` (a, bound), `pod_mission_end.png` and `pod_end_cruise.png` (b, centreline section through the battery and avionics bays), `pusher_cruise.png`, `thermal_mission_history.png` (c, all components vs limits through the mission), `lift_unit_hover_history.png` (continuous hover). The SOLIDWORKS plots are in `cad/sim/thermal/THERM_*.png`; the studies are saved in `cad/sim/thermal/THERM_*.SLDPRT`.

## 1. Method and tool choice

**Tool.** SOLIDWORKS Simulation 2025 thermal studies (steady state and transient) driven from `cad/Thermal.cs`, the same API pattern as `cad/Sim.cs` (which is unchanged; `analysis/verify.py` still reads `cad/sim/results.txt`). Flow Simulation is not licensed, so convection is applied as film coefficients from textbook correlations on each exposed face (section 3), not computed. Studies build their own simplified multi-body parts from `cad/params.txt` and do not open `cad/model/`:

| Study set | Bodies (material) | Loads | Cases |
|---|---|---|---|
| M motor-only | Ø48 × 32 can (6061 library, then the lumped motor material) | `thermQ` / `thermH` / `thermAmbK` of `cad/Sim.cs` (35 °C, `cad/params.mjs` thermAmbK), then this analysis' Q and h at 25 °C | steady (validation), 90 s transient (validation of the lumped value) |
| L lift unit | motor can on the PA6-CF mount block 70 × 46 × 36 with the Ø25.6 bore (hardware-spec J02), 0.40 m of 6061 boom, ESC lump 55 × 28 × 12 on its 3 mm foam pad under the boom ahead of the mount (J15) | motor + ESC heat | steady hover; continuous hover 0–120 s; the mission chain |
| P pod | Ø160 × 1,000 XPS cylinder (`params.txt` fusR, fusL) with the battery bay and the avionics bay (`params.txt bay*`), battery block 155 × 50 × 48, FC block 52 × 32 × 17, a 3 mm air gap round both | battery I²R per phase, FC 2.0 W | the mission chain |
| K pusher | Ø48 × 32 can (X4110S lump, 165 g) in the PA6-CF cup (Ø55.6 × 30 long, 4.5 floor, 3 wall EST; `cad/mesh/meta.json` Pusher_Cup) in a Ø80 foam ring; the can protrudes 6.5 mm past the cup rim | motor loss in cruise | steady cruise; 600 s cruise transient |

**Mission chain.** The API rejects time curves on loads (`ICWHeatPower::SetTimeCurve` returns error 3 for every array layout tried), so a mission is run as one transient study per phase, each starting from the last saved step of the previous one (`ThermalStudyOptions.UseTemperatureFromThermalStudy2`, `ThermalStudyNameUsedForInitialTemperature`, `TimeSteps` = that step). Phases: hover 60 s → transition 20 s → cruise 600 s → transition 20 s → hover 60 s (`analysis/sizing.mjs` tHover 120 / tTrans 40 / tCruise 600 s, split as the review's duty chart `review/src/app.js drawDuty`; test plan F12 flies ≥ 1 min hover at each end). Time step 5 s (20 s in cruise); the same mesh in every study of a chain so the initial field maps node to node.

**Transient output fix.** `cad/README.md` recorded that the transient thermal API "returned no saved time steps" (2026-10-13). The study then had no initial temperature and the thermostat flag on the heat load was left at its default. With (1) an initial-temperature load on all bodies (`AddTemperature`, `TemperatureType` 0 = initial), (2) `IncludeThermostat2 = false` on every heat-power load of a transient study (the default fails `HeatPowerEndEdit` with error 6 "select vertex for thermostat"), and (3) `StudyResultOptions.SaveResultsForSolutionStepsOption = 0` (all steps), `Results.GetMaximumAvailableSteps()` returns every step (18 for 90 s at 5 s) and `GetMinMaxThermal(0, step, null, 2)` reads each one. `GetTimeOrFrequencyAtEachStep` returns DBNull, so step times are reconstructed from `TimeIncrement`. Probed layouts (2026-10-25): `Mesh.GetNodes()` = [id, x, y, z] per node; `Mesh.GetElements()` = 16 values per element (id, 10 node ids, centroid …); `Results.GetThermalValues(step, null, 2)` = 10 values per node (id, T, three gradients, resultant, three fluxes, resultant); `GetThermalComponentForAllStepsAtNode(0, node, null, 2)` = [step, t, T] per step; `GetThermalForEntities(0, step, null, faces, 2)` = [id, T] for the nodes on the faces.

**Field export.** For each case the surface triangles (tet faces that appear once) and nodal temperatures are written to `cad/sim/thermal/fields/*.json`; `analysis/thermal/thermal_report.py` renders them in a thermal-camera style (inferno palette from the ambient to the case maximum, scale bar in °C, hot-spot marker with the maximum) and decimates them by vertex clustering for the web page (`analysis/thermal/thermal_results.json`, section 7).

## 2. Heat loads (all per `analysis/thermal/thermal_inputs.json`, generated 2026-11-02)

| Source | Load | Basis |
|---|---|---|
| Lift motor, hover | **56.6 W** each | EST 20 % of the 282.8 W hover input per unit (`cad/params.mjs` thermQ rule: 80 % motor + ESC efficiency); `cad/sim/results.txt` motor_Q uses the same 56.6 W. Conservative: the reseller-listed 112 mΩ winding resistance gives only I²R ≈ 20 W at the 13.5 A hover current per motor (282.8 W / 21 V) *(calc)*, so 20 % also covers iron, bearing and ESC-side losses |
| Lift motor, transition | 86.1 W each | the same 20 % of P_trans / 4 (1,722 W / 4; `sizing.mjs` P_trans = P_hover + 2 P_cruise = 1,131.3 + 2 × 295.4) for 20 s |
| Lift ESC | **11.3 W** hover, 17.2 W transition | EST 4 % of the unit input. LANRC publishes no efficiency ("—"); FET conduction loss scales as I_rms² R_ds(on) and is 60–80 % of inverter loss (TI SSZTB57). Added on top of the 20 % motor figure, so the unit total (24 %) is conservative |
| Lift motor + ESC, cruise | 0 | lift rotors stopped (R1); cooled by the 18 m/s freestream |
| Battery pack | **104.5 W** hover, **242.1 W** transition, 6.4 W cruise | I²R with R_pack = 6 × 6.0 mΩ = 36 mΩ, the C11 acceptance limit (`docs/test/TEST-PLAN.md`; Ovonic publishes no resistance, "—"). I = P / 21 V (`sizing.mjs`): 53.9 / 82.0 / 13.3 A. This is the bounding pack; heat ∝ R, so a pack at half the limit makes half the heat |
| Pusher motor + ESC, cruise | 44.3 W total: **33.2 W** motor, 11.1 W ESC | P_cruise 295.4 W × (1 − η_mec 0.85) (`results.json` base.etaMEc); 75/25 split EST. The pusher is the same X4110S as the lift units; SunnySky publishes no thermal data ("—") |
| Flight controller board | 2.0 W | EST itemisation (`thermal_inputs.py`): STM32F405 ~0.3 W + OSD/sensors ~0.2 W + 5 V BEC loss ~0.45 W + servo BEC loss ~1.05 W. The RX, GPS and Remote ID heat their own housings, so they are not on the board (the earlier 3.5 W lump double-counted ~1.5 W). CoreWing publishes no figure |

Mission energy check: the battery heat over the mission is 104.5 × 120 + 242.1 × 40 + 6.4 × 600 = 26.0 kJ *(calc)*, 6.9 % of the 377 kJ the mission draws from the pack (`results.json` sized E_Wh 99.5 Wh × 3600 / η_batt 0.95) — consistent with a pack at its resistance limit.

## 3. Cooling: film coefficients from correlations

Air at ~308 K: ν 1.65 × 10⁻⁵ m²/s, k 0.0268 W/mK, Pr 0.706 (Incropera & DeWitt, *Fundamentals of Heat and Mass Transfer*, 6th ed., Table A.4). The properties were kept at ~308 K when the ambient moved to 25 °C (`thermal_inputs.py`); between 298 and 308 K ν falls about 6 % and k about 3 % (same table), which raises h by a few per cent — a small conservative bias.

**Prop wash.** Induced velocity at the disc v_i = √(T / 2ρA) with T = 18.23 N per unit (`results.json` sized Tunit_N), A = 0.1464 m² (Ø17 in disc), ρ 1.225 → **v_i = 7.13 m/s** (far wake 14.3 m/s). The motor, mount and ESC sit under the disc, so the near-disc value is used (conservative by up to 2× on velocity, ~1.5× on h).

| Surface | Correlation | Re | Nu | h, W/m²K |
|---|---|---|---|---|
| Lift motor can, hover | Hilpert cylinder in crossflow, D 48 mm, V = v_i (eq. 7.52, Table 7.2) | 20,736 | 80.0 | **44.6** |
| Boom tube, hover | Hilpert, D 25.4 mm | 10,973 | 54.0 | 56.9 |
| Mount block, hover | laminar flat plate, L 70 mm (eq. 7.30) | 30,241 | 102.8 | 39.4 |
| ESC, hover | laminar flat plate, L 55 mm | 23,760 | 91.1 | 44.4 |
| Lift motor / boom / mount / ESC, cruise 18 m/s | the same correlations at V_c | — | — | 84.5 / 100.9 / 62.6 / 70.6 |
| Pod skin, cruise | mixed flat plate, L 1.00 m (eq. 7.38) | 1.09 × 10⁶ | 1,453 | 38.9 |
| Pod skin, hover | Churchill–Chu horizontal cylinder, D 0.16 m, ΔT 10 K (eq. 9.34); wash on the pod neglected | Ra 3.38 × 10⁶ | — | 3.4 |
| Pusher can, cruise | laminar flat plate over the 32 mm can in the axial freestream + prop inflow (EST form) | 34,909 | 110.5 | 92.5 |
| Cup inner annulus | EST half the can value | — | — | 46.3 |
| Battery and FC faces to bay air | EST free convection in a closed bay (Incropera Table 1.1, gases 2–25) | — | — | 5.0 |
| Radiation, for scale | 4 ε σ T³ at 330 K, ε 0.9 EST; not applied (conservative) | — | — | 7.3 |

**Ambient.** Design ambient 25 °C = the full-mission ceiling of `docs/DESIGN-BASIS.md` R21 (no full mission above 25 °C, measured at the field before each flight; TEST-PLAN §4 rule 9). Standard day 20 °C = the Berkeley April average high, 20 °C / 67 °F (NOAA NCEI 1991–2020 normals via https://www.currentresults.com/Weather/California/city-temperature-april.php, checked 2026-11-02). All studies are linear (constant properties, convection only, no radiation), so every standard-day temperature is the design value minus 5 K. `cad/Sim.cs` still uses `cad/params.mjs` thermAmbK 308.15 K (35 °C) for its motor check, so the motor values in `cad/sim/results.txt` are 10 K higher than the same case at 25 °C.

## 4. Materials

| Material | k, W/mK | c_p, J/kgK | ρ, kg/m³ | Limit | Source |
|---|---|---|---|---|---|
| 6061 boom | 167 | 896 | 2,700 | — | SOLIDWORKS library "6061-T6 (SS)" (`params.txt` matLib) |
| Motor lump (X4110S) | 30 EST | 470 EST (band 385–500) | 165 g / can volume = 2,849 | can 80 °C EST (test plan abort table; SunnySky publishes no limit) | mass `budget-lift.md` A3; c_p mass-weighted Cu/steel/Al (`review/src/app.js` TH) |
| Pusher lump (X4110S) | 30 EST | 470 EST | 165 g / can volume = 2,849 | can 80 °C EST | `cad/params.txt` motorMass, `budget-lift.md` A3; `sizing.mjs` mPusherSet (pusher = lift motor type) |
| PA6-CF mount, cup | 0.35 EST | 1,500 EST | 1,170 | HDT **173 °C** at 1.8 MPa | Polymaker Fiberon PA6-CF20 TDS v1.1 (`airframe-materials.md`) |
| PETG (boom clamps, trays; not a heat path here) | — | — | — | HDT **68 °C** (0.45 and 1.80 MPa), Tg ~80 °C | Prusament PETG TDS v1.1 (2022); MatterHackers PETG sheet (checked 2026-10-25) |
| XPS pod foam | 0.0289 | 1,300 EST | 32 (sizing rhoFoam) | max use **74 °C** (165 °F) | Owens Corning FOAMULAR 150 product data sheet: R-5 per inch at 75 °F mean (ASTM C518) → k = 0.0254 / 0.88 = 0.0289 W/mK *(calc)*; maximum use temperature 165 °F (74 °C) (datasheet PDF cited in `airframe-materials.md`, read 2026-10-25) |
| LiPo pack | 1.0 EST (through-plane 0.5–1, in-plane 20–30) | 1,100 | 0.82 kg / 155 × 50 × 48 box = 2,204 | **60 °C** | c_p: Lin et al., arXiv 2112.09768 (20 Ah pouch, 541 J/K at 0.489 kg) and Chalmers calorimetry (~1,100); mass `results.json` pick.kg; limit `TEST-PLAN.md` C11 / rule 8 |
| FC board (STM32F405RGT6) | 5 EST | 800 EST | 1,500 EST | **85 °C** (−40 to +85 °C ambient rating of the 6-suffix part, https://hken.rs-online.com/web/p/microcontrollers/7468217, checked 2026-11-02), applied to the board temperature, which is conservative; CoreWing publishes no board rating ("—") | `thermal_inputs.py` limits |
| ESC lump | 5 EST | 800 EST | 1,500 EST | 70 °C EST (test plan; LANRC publishes none, "—") | — |
| Foam mounting pad | 0.04 EST | 1,300 EST | 40 EST | — | hardware-spec J15 |

## 5. Validation

| Check | FEA | Reference | Δ |
|---|---|---|---|
| Motor-only steady with the `cad/Sim.cs` inputs (Q 56.57 W, h 44.65, 6061 library, 35 °C Sim.cs ambient) | **185.60 °C** | `cad/sim/results.txt` motor_T_steady 185.60 °C; hand T_amb + Q/(hA) = 185.03 °C (A = 0.008445 m²) | 0.0 % / +0.3 % |
| Motor-only steady with this analysis' inputs (Q 56.6 W, h 44.6 Hilpert, lumped motor k 30, 25 °C) | 178.2 °C | hand 175.0 °C | +1.8 % (internal gradient of the k = 30 lump) |
| Motor-only 90 s transient, c_p 470 J/kgK, `Sim.cs` inputs (35 °C) | **88.4 °C** | lumped capacitance 88.2 °C, τ = m c_p/(hA) = 205.7 s (`review/src/app.js` TH); i.e. 78.2 °C from 25 °C | +0.2 K |
| Lift-unit steady vs motor-only (25 °C) | 185.1 °C | 178.2 °C: the motor base sits on the PA6-CF floor (k 0.35) instead of convecting, and the boom path carries < 1 W (boom max 26.4 °C) | consistent |
| ESC steady in prop wash | 98.5 °C | hand Q/(hA): 11.31 W / (44.4 × 0.00353 m²) = 72.2 K → 97.2 °C | +1.3 K |
| Pusher steady (X4110S) | 77.3 °C | hand 33.2 W / (92.5 × 0.00664 m²) = 54.1 K → 79.1 °C (the cup wall conducts a little away) | −1.8 K |
| Battery rise over the mission | 28.2 K (25.0 → 53.2 °C) | adiabatic 26.0 kJ / (0.82 kg × 1,100 J/kgK) = 28.9 K | −0.7 K: the foam bay is adiabatic to within 3 % |
| Transient steps saved | 18 of 18 (90 s / 5 s), and every step per phase | `cad/README.md` 2026-10-13: "returned no saved time steps" | fixed (§1) |

The structural FEA–hand bands of `analysis/verify.py` (15 %) are met by every pair above; the thermal pairs are within 2 %.

## 6. Results (design ambient 25 °C)

### 6.1 Lift unit (motor + PA6-CF mount + boom + ESC)

Continuous hover from 25 °C (`lift_unit_hover_history.png`): motor can 44 / 59 / 73 / 85 °C at 30 / 60 / 90 / 120 s; ESC 39 / 50 / 60 / 67 °C; mount maximum (the floor under the motor) 42 / 58 / 71 / 83 °C; boom < 26 °C throughout. The can crosses the 80 °C EST limit at about 108 s of uninterrupted hover (78.9 °C at 105 s, 80.9 °C at 110 s); the ESC stays under 70 °C to 120 s. Time constant of the lump in prop wash ≈ 257 s *(calc: −120 / ln(1 − 59.7 / 160.1), the 120 s rise over the 160.1 K steady rise)*, so the steady state (185 °C) is never approached in flight.

Mission (`lift_unit_mission.png`, `thermal_mission_history.png`): 59 °C after the 60 s take-off hover, **75 °C at the end of the 20 s transition** (loads × 1.52 for P_trans: 1,722 / 1,131.3 *(calc)*), cooling in cruise with the rotors stopped (h 84.5 W/m²K at 18 m/s) to 26 °C by 680 s, then 74 °C again after the back-transition and landing hover. The ESC peaks at 62 °C and ends at 60 °C. The mount tracks the motor base within 2 K (73 °C peak), 100 K under the PA6-CF HDT. Because the peak comes at the end of the first hover + transition, any flight with a take-off hover followed by a transition (TEST-PLAN F06–F13) reaches it, not only the full mission. For the bench protocol C08 each run must start at ambient (TEST-PLAN C08 now cools to within 5 K of ambient): a run started 20 K warm adds most of that excess to its peak (e^(−90/257) = 0.70 of it after 90 s *(calc)*). The "3 × 90 s with 30 s rests" limit-finding run was not re-modelled in this run (—).

Sensitivity: the 20 % loss is the dominant assumption. At the reseller-listed 112 mΩ winding resistance the hover I²R is 20 W; with 10 W of iron and bearing loss (EST) the unit loss would be ~30 W and every rise above ambient scales by 30 / 56.6 (mission peak ≈ 52 °C at 25 °C *(calc: 25 + 50.2 K × 30 / 56.6)*). C08 measures this directly (fit the time constant and the 90 s rise); TEST-PLAN C08 turns a measured 90 s rise above 52 K (can) or 42 K (ESC) into a lower R21 ceiling *(calc: 47.8 K × 55 / 50.2 and 34.6 K × 45 / 36.7)*.

### 6.2 Pod: battery and avionics bays

`pod_mission_end.png` and `pod_end_cruise.png` are centreline sections. The battery warms 6.9 K in the take-off hover (104.5 W), 5.4 K in the 20 s transition (242.1 W), 3.7 K over the 600 s cruise (6.4 W), 5.3 K in the back-transition and 6.9 K in the landing hover: **53 °C at touchdown from a 25 °C start** (53.2 °C, `pod_mission_end_Battery`), 6.8 K under the 60 °C limit. Only about 2 % of the heat leaves through the foam (0.029 W/mK) and the 5 W/m²K bay air film, so the pack is adiabatic: the rise is Q·t / (m c_p) and scales with the pack resistance, 28.2 K / 6.0 = 4.7 K per mΩ/cell over a mission *(calc)*. At a measured 4 mΩ/cell (EST, typical of a 100C 6,500 mAh pack) the rise is 18.8 K (44 °C at touchdown) *(calc: 28.2 × 4 / 6.0)*. On a 20 °C day with the limit pack: 48 °C. The rise adds to the pack's start temperature, which is why the test plan limits it to 60 − 4.7 × R_cell °C (§6) and keeps the packs shaded.

The flight-controller board reaches 60 °C at the end of the mission with 2.0 W on the 52 × 32 × 17 mm block under a sealed canopy (h 5, no radiation), 25 K under the STM32F405 rating. It is still rising at touchdown (about 0.04 K/s over the landing hover), so a longer sortie ends warmer; the steady value was not computed (—). Radiation (≈ 7 W/m²K equivalent at ε 0.9) and a vented bay would both lower it.

### 6.3 Pusher (X4110S) in the PA6-CF cup (cruise)

Steady cruise 77 °C can / 77 °C cup floor / 74 °C cup wall / 51 °C foam tail ring; from 25 °C the can is at 32 / 42 / 53 / 63 / 70 °C after 20 / 60 / 120 / 200 / 300 s of cruise and **76 °C after 600 s** (76.0 °C, `pusher_endcruise_Motor`; τ ≈ 153 s for the 165 g can *(calc: −120 / ln(1 − 28.4 / 52.3))*, so cruise is quasi-steady after 5–6 min; `pusher_cruise.png`). The cup is 96 K under its HDT and the foam ring 23 K under the XPS maximum-use temperature (74 °C). The can sits 4 K under the 80 °C EST limit after 600 s and 3 K under it at steady state.

What sets this number: the loss, 33.2 W = 295.4 W × (1 − 0.85) × 0.75, is an estimate stacked on an estimate (η_mec 0.85 is the sizing assumption for motor + ESC; the 75 % share is EST). The lift units run the same motor at 283 W input with the sizing's 20 % rule; the pusher at 295 W input is 4 % above that, so a loss in the 25–45 W range is plausible and the model is not obviously pessimistic. The C0 flight model (`firmware/sitl/c0_physics.py --validate`, APC data, η_prop ≈ 0.74) needs only 200 W in cruise, which would cut the loss by about a third *(calc: 200 / 295.4)*; until it is measured the sizing value stands. The film coefficient is not the lever: the FEA applies the free-stream value (92.5 W/m²K at 18 m/s) to every exposed face of the can, including the faces inside the cup annulus (only the cup's own inner wall gets half), so no venting of the cup can lower the predicted temperature — it can only make the model's assumption true. At a 20 W loss the steady rise would be 31.5 K → 57 °C *(calc: 52.3 K × 20 / 33.2)*.

### 6.4 Recommendations

1. **Battery bay ventilation (design change, keep).** Add a ram-air inlet at the nose and an exit slot at the rear of the battery bay (two openings of ~15 × 30 mm EST, through the foam, skinned with the tape covering) so cruise air sweeps the pack. With even 20 W/m²K on the 0.037 m² pack surface (0.74 W/K; pack m c_p 902 J/K, τ ≈ 1,220 s) the 12.3 K accumulated by the end of the first transition relaxes during the 600 s cruise toward the cruise equilibrium of 6.4 W / 0.74 W/K = 8.6 K, ending cruise at 10.9 K of rise instead of 16.0 K *(calc: 8.6 + (12.3 − 8.6) e^(−600/1,220))*; adding the 12.2 K of the back-transition and landing hover, touchdown is about 48 °C at 25 °C with the limit pack *(calc, EST)*, about 40 °C with a 4 mΩ/cell pack *(calc, heat ∝ R)*. The vents turn a 7 K margin into about 12 K.
2. **Pack acceptance 6.0 mΩ/cell (adopted).** TEST-PLAN C11 rejects packs above 6.0 mΩ/cell for full missions; record the measured value on the pack label, shade the packs before flight and respect the start-temperature limit 60 − 4.7 × R_cell °C (TEST-PLAN §6).
3. **Keep the hover limits and the IR checks; measure the loss.** The ≤ 60 s per hover rule (test plan rule 3) leaves 21 K on the can and 20 K on the ESC; the 80 s hover + transition leaves 5 K and 8 K at 25 °C with the 20 % loss estimate. C08 must replace the estimate (fit τ and the 90 s rise from ambient) and, if the rise exceeds 52 K (can) or 42 K (ESC), lower the R21 ceiling as TEST-PLAN C08 states; abort at 80 °C can / 70 °C ESC.
4. **ESC placement.** The model gives the ESC the full prop-wash film (44 W/m²K) although it sits on the boom underside, in the boom's wake; move it to the boom side or top face ahead of the mount (J15), heat-shrink side to the flow, and keep the 3 mm foam pad (it isolates the ESC from the warm mount, not from the boom, which stays at ambient). An ESC loss of 2 % instead of 4 % halves its rise (mission peak 43 °C *(calc: 25 + 36.7 / 2)*).
5. **Vent the avionics bay** (two 8 mm holes in the canopy, forward-facing and aft EST) and mount the FC on 5 mm standoffs: the board passes by 25 K sealed, but it is still warming at touchdown; measure the FC current-sensor board in G03 as the test plan requires (≤ 60 °C).
6. **Pusher: measure first, then decide the cup.** The cup (Ø55.6 × 30) sits entirely inside the Ø56 × 30 tail-ring bore (`cad/mesh/meta.json` Pusher_Cup), so slots in its wall would open into foam, not air; they only work together with matching radial channels through the tail ring to the skin (four Ø10 mm EST, cup wall → foam → outer skin at the boat-tail), and even then they would only realise the free-stream film the model already assumes. So: (a) G03 tied-down run at cruise throttle (≈ 13.3 A pack current, `results.json` sized I_cruise at 18 m/s) for 3 min with the IR thermometer on the can every 30 s, and the IR check after F08's cruise legs; model predictions to compare against, from a 25 °C start: 42 °C after 60 s, 53 °C after 120 s, 70 °C after 300 s, i.e. rises of 17 / 28 / 45 K. (b) If the measured can tracks the model (rise ≥ 28 K after a 120 s leg: the 33 W loss is real), the loss, not the cup, must come down: check the pusher prop/throttle match and the ESC timing, and fit an aluminium spider floor (3 mm, four arms to the skin EST) as a conducting path — the PA6-CF floor at k 0.35 W/mK carries < 1 W today. (c) If the measured rise stays ≤ 17 K after 120 s, the loss is ≤ 20 W EST *(calc: rise ∝ loss, 28.4 K × 20 / 33.2)*, the steady can at 25 °C is ≤ 57 °C and no change is needed; the cup stays closed. In all cases the XPS tail ring (51 °C bound vs 74 °C max use) and the PA6-CF cup (77 °C vs HDT 173 °C) are not the limiting parts.
7. **Materials confirmed:** PA6-CF for the four motor mounts and the pusher cup (73 °C mission peak / 185 °C hover bound vs HDT 173 °C); PETG only where the model shows ambient (boom clamps, trays, fin shoes). A PETG motor mount would pass its HDT at about 82 s of hover (mount 67.1 °C at 80 s, 69.3 °C at 85 s, `lift_unit_hover` history).

## 7. Outputs for the review page

`analysis/thermal/thermal_results.json` (compact, < 1 MB):

```
generated, tool, ambient_C {hot, standard, note}      # hot = the 25 C design ambient (key name kept for cad/Thermal.cs)
inputs_summary {results_json, loads_W{}, h_W_m2K{}, v_i_mps, mission[{name, dt_s}], limits_C{}}
validation {val_*}                      # motor-only checks of section 5
results {<key>: value}                  # every line of cad/sim/thermal/results.txt
findings [{component, case, peak_C, peak_std_C, limit_C, limit_src, margin_K, status, note}]
histories {lift_unit_mission, pod_mission, pusher_cruise, lift_unit_hover}   # {body: {t[], T[]}} max-in-body vs time, s / °C
images [paths]                          # analysis/thermal/img/*.png
fields {lift_unit{steady_hover, hover_90s, end_hover5}, pod{end_hover5}, pusher{end_cruise}}
       # each: vertices [x,y,z,...] m in the study frame, temps_C per vertex, tris 0-based, cell_m
```

Study frames: lift unit — boom axis X, up Y, motor at the origin on top of the mount; pod — pod axis X (nose +X), up Y, pod local = global − (noseX, yPod, 0), noseX = tailX + fusL (`cad/Thermal.cs`); pusher — cup axis X. `status` is pass (margin ≥ 10 K), pass with < 10 K margin (0–10 K), or fail (< 0).

## 8. Limitations

1. **Loss fractions are estimates.** Lift motor 20 % of input (the `params.mjs` rule; the bench C08 run replaces it), ESC 4 %, pusher 15 % × 75 %: none is from a datasheet (SunnySky and LANRC publish none, "—"). Every lift-unit and pusher rise scales linearly with them.
2. **Film coefficients are textbook correlations, not CFD.** Prop wash at the disc value v_i (not the 2 v_i far wake), no rotor-bell self-pumping, no boom wake on the ESC, and the pusher in axial flow modelled as a flat plate. Air properties at ~308 K. Radiation is left out everywhere (ε 0.9 would add ~7 W/m²K to the exposed surfaces, i.e. 15 % more cooling on the motors and more than double on the FC in its bay). Both choices are conservative for every component except the ESC (see §6.4 item 4).
3. **Lumped motor.** The can is one isotropic body (k 30, c_p 470 J/kgK, 165 g) with uniform volumetric heat; winding and magnet temperatures are not resolved, and the test-plan limits are can-surface values measured by IR. The c_p band 385–500 J/kgK moves the 90 s value by a few kelvin (`cad/README.md`).
4. **Geometry simplified.** Cylindrical pod of fusR without the nose ellipse and boat-tail; the printed battery and FC trays are omitted (3 mm PETG between pack and foam adds insulation, already effectively adiabatic); the mount's 1.2 mm split gap and the motor's Ø25 bolt circle are not modelled (uniform contact over the Ø48 floor is optimistic for the mount, pessimistic for the motor); the boom is 0.40 m long with ambient convection at both ends; the ESC size is an estimate.
5. **Bay air at ambient.** The battery and FC faces that see bay air convect to 25 °C air at 5 W/m²K; in a sealed bay the air warms, so those faces are optimistic by up to the full 5 W/m²K (small for the pack, significant for the FC).
6. **Chained transients with constant loads per phase.** The API rejects time curves, so the 20 s transitions are rectangular pulses at P_trans; the hover–cruise handovers are instantaneous; cruise cooling of the lift unit uses the 18 m/s film from t = 80 s.
7. **Ambient.** 25 °C is the R21 ceiling, measured at the field; solar load on a black pack or motor on the ground before take-off is not included (it adds to the start temperature: the IR check before flight). `cad/Sim.cs` motor values in `cad/sim/results.txt` remain at its 35 °C ambient.
8. **Not measured yet.** C08 (motor/ESC heat), C11 (pack resistance and temperature), G03/G04 (FC, connectors, pusher at cruise throttle), F03 (3 × 60 s hovers), F08 (pusher after cruise legs) in `docs/test/TEST-PLAN.md` are the measurements that close every estimate above.

**API notes for the next run** (`cad/Thermal.cs`): the library material "6061-T6 (SS)" raises a modal "Plasticity – von Mises … switching to Linear Elastic" dialog in thermal studies that blocks the API — use a custom material with the library's k / c_p / ρ instead; a body takes the name of the last feature that modifies it, so the last cut on the foam is named `Foam`; `FeatureExtrusion3` direction/offset flags are probed by checking the resulting body box (`Ext`), cuts by the removed volume and the centroid shift (`CutRange`); study names must not contain commas or periods; the solver runs as a separate `hstar` process, so the pod chain takes tens of minutes when other solvers share the cores.
