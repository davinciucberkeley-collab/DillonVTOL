# Cross-check against the team's DBF-VTOL repository

Date checked: 2026-11-03. Source: [davinciucberkeley-collab/DBF-VTOL](https://github.com/davinciucberkeley-collab/DBF-VTOL)
at commit `77913e9`. It was read only and not modified. DBF-VTOL holds the team's inventory, electrical, Fusion and
concept work, and it is built on design **v0.3.1**: MTOW 6.18 kg, two packs, 20 m/s cruise. This repository is on
**v0.4.0**: MTOW 7.438 kg, one pack, 18 m/s cruise (`analysis/results.json`). So each DBF-VTOL finding below was
re-checked against v0.4.0 before it was used here, and every number was re-sourced. "—" = unknown.

## 1. Verdict

Four DBF-VTOL findings still apply to v0.4.0 and a fifth applies in part. All five are now open items in this repo (§2). Six are already covered here
by a different fix (§3). Two are team resources that are linked here, not copied (§4).

| # | Finding (from DBF-VTOL) | Applies to v0.4.0? | Action here |
|---|---|---|---|
| X1 | The battery cannot be lifted out of the pod | **Yes**: the bay is sealed under 35 mm of foam | Fixed in the CAD: access well, longer bay (§2.1) |
| X2 | Servo stall current exceeds the FC servo BEC | **Yes**: the wiring list assumed 1.5 A per servo; the vendor gives 2.5 A | Wiring list corrected; bench test added (§2.2) |
| X3 | A lift motor at full throttle exceeds the X4110S 26 A / 30 s rating | **Yes**: 27.7 A full throttle; `Q_M_BAT_CURR_MAX` caps only the total | Open item; set `Q_M_SPIN_MAX` from the thrust stand (§2.3) |
| X4 | Printed PETG clamp preload relaxes over days | **Yes**: same PETG clamps | Re-torque rule added (§2.4) |
| X5 | Power trunk near the GPS compass | Partly: geometry differs; field estimated | CompassMot step added (§2.5) |

## 2. Findings that apply

### 2.1 X1: the battery is sealed in the pod

DBF-VTOL `fusion/motion_clearance.md` (2026-11-02) reports that the pack "cannot be lifted out" of its Fusion pod.
The same check on this repo's SOLIDWORKS pod finds the same problem for a different reason.

- Pack: x +0.1775 to +0.3325 m, top at y −0.027 m (`cad/params.txt` comp Battery_6S_LiPo at x 0.255, y −0.052;
  `battL` 0.155, `battH` 0.050).
- Battery bay cut: from y −0.080 to y −0.020 m (`cad/BuildVtol.cs` line 672: sketch at −0.080, cut 0.060).
- Canopy pocket: from `canopyY` +0.015 m upward, x +0.1575 to +0.480 m (`cad/params.txt`).
- A vertical ray cast through `cad/mesh/Fuselage_Pod.STL` above the pack hits pod faces at y −20.0 mm and +15.0 mm
  at x = 0.19, 0.22, 0.255 and 0.29 m (z = 0 and 0.02 m). So there is **35 mm of solid foam** between the bay
  ceiling and the canopy pocket over the whole pack. Only at x ≥ 0.30 m, where the avionics bay begins (`bayX0`), is
  it open. That 150 mm opening (`bayX0`–`bayX1`) is shorter than the 155 mm pack and holds the FC tray.
- BUILD-MANUAL 8.1 cuts the bay "out of the middle layers before lamination", so the built pod would match the CAD.
  The pack could not be loaded after lamination or swapped between flights (13.13 lists two packs).

**Found while checking X1:** the bay was cut 165 mm long for the 155 mm pack (`battL`/2 + 5 mm). So the pack could
slide only ± 5 mm, while BUILD-MANUAL 8.5 and 12.2 trim the CG by sliding it ± 30 mm (± 3.3 mm CG window,
`analysis/results.json` cg.cgBattFwd / cgBattAft). ± 5 mm gives about ± 0.55 mm of CG *(calc: 0.82 / 7.438 × 5)*.

**Fix (CAD rebuilt 2026-11-03, drawing DBF-DRW-001 rev G; `cad/BuildVtol.cs` Fuselage, BatteryTray; `cad/params.mjs` xFC):**
- **Access well** from the bay ceiling (y −0.020) up to the canopy pocket floor (`canopyY` +0.015), over x `battX` ±
  (`battL`/2 + 0.005), z ± 0.026. The canopy pocket is a half-ellipse in plan (centre x +0.31875, semi-axes 0.16125 in
  x and `canopyR` 0.055 in z). At the pack's rear face (x +0.1775) its half-width is
  0.055 × √(1 − (0.14125 / 0.16125)²) = **26.5 mm** *(calc)*, against the pack's 24 mm half-width (`battW` 0.048). So
  the pack passes up through the hatch with 2.5 mm a side at the tight end. The pack must be at its centre mark to come
  out.
- **Bay** 225 mm long: pack + 2 × (30 mm slide + 5 mm), x +0.1425 to +0.3675. **Tray P21** 220 mm long, so the pack
  stays on it at both marks.
- **FC tray** moved from x +0.375 to +0.4075, with its rear edge 10 mm ahead of the bay's front end. Otherwise the
  longer bay would have cut away the floor under its rear bosses. Its CG effect is below (§2.1a).

**§2.1a Result of the rebuild** (`cad/verification.txt` 2026-11-03 14:38 against the committed 11:00 run):
- 397 components, 263 interferences: 189 insert press fits and 74 others totalling 244.0 mm³, unchanged. So the change
  adds no clash.
- `cad/drawings/layout-check.txt` has no overlaps. The revision table on sheet 1 was compacted to keep it that way.
- A ray cast through the new `cad/mesh/Fuselage_Pod.STL` above the pack (x 0.18–0.33 m, z 0 and 0.023 m) hits no pod
  face from the pack top to the canopy, so the pack has a clear path out. The bay floor runs from x +0.1425 to +0.3675.
- Mass: the pod is 371.7 g (was 386.0 g, −14.3 g of foam) and the tray 46.4 g (was 34.6 g, +11.7 g). The modelled
  total is 6.683 kg (was 6.686 kg).
- CG: the foam and tray changes sit at the pack station, x +0.255. That is 0.345 m ahead of the CG at about x −0.090
  (the 86.9–93.6 mm aft of the LE window, LE at x 0). The FC group moves 32.5 mm forward: FC 40 g + tray 11.6 g +
  4 × F07 0.66 g + 4 × I01 0.44 g = 56.0 g. ΔCG = (−14.3 × 0.345 + 11.7 × 0.345 + 56.0 × 0.0325) / 7438 g ≈
  **+0.12 mm forward** *(calc)*, against the ± 3.3 mm window. The sizing (`analysis/results.json`, frozen 2026-11-01) is
  not re-run.
  `analysis/mass/mass_budget.py` lumps all 418 g of avionics at the FC station. Re-calibrating with it would move the
  sizing CG by about 1.8 mm *(calc: 0.418 × 0.0325 / 7.438)*, which overstates the real 0.12 mm. So the calibration file
  is left at its committed values.

### 2.2 X2: servo stall current against the 8 A servo BEC

- EMAX ES3005HV: "Maximum Current - (6.0V) 2.5A Max (7.4V) 3.2A (8.4V) 3.6A Max". Running current at no load is
  450 mA at 6.0 V ([3DXR product page](https://www.3dxr.co.uk/fixed-wing-c27/fixed-wing-accesories-c172/servos-c117/emax-es3005hv-all-purpose-hv-metal-gear-digital-servo-p5924),
  checked 2026-11-03. The EMAX USA page returned HTTP 429, so it was not read).
- The CoreWing F405 Wing V2 servo BEC is rated 8 A continuous, 14 A peak (`docs/purchasing/C0_BOM.csv`;
  `docs/build/wiring.csv` A06).
- Five servos on the 6 V rail: 5 × 2.5 = **12.5 A** if all stall at once *(calc)*. That is above the 8 A continuous
  rating and 1.5 A under the 14 A peak. A single binding surface adds 2.5 A to the running load.
- `docs/build/wiring.csv` previously said "~1.5 peak EST" per servo and "< 8 A" in total. Both lines now carry the
  vendor figure.

**What the team must measure:** at 6 V, with a clamp meter on the servo rail, hold each surface against its stop in
turn, then all five together. Pass: under 8 A sustained, under 14 A for the duration of a full-stick input, and no
FC brownout or reboot. If it fails, add a separate 6 V servo UBEC (the spare 5 V 5 A UBEC, wiring A07, is the wrong
voltage).

### 2.3 X3: one lift motor at full throttle exceeds its rating

- SunnySky X4110S 400KV: "Max Continuous Current: 26A / 30S"; "Max Continuous Power: 577W"
  ([ReadyMadeRC](https://www.readymaderc.com/products/details/86945-sunnysky-xs-high-power-x4110s-brushless-motor-400kv),
  checked 2026-11-03).
- One X4110S on the 17 in prop draws 27.7 A at 22.2 V full throttle (`docs/research/budget-lift.md` A3, as quoted in
  BUILD-MANUAL §10 power path).
- `Q_M_BAT_CURR_MAX 85` (`firmware/vtol_c0.param`) limits the **total** battery current, not each motor. Hover is
  12.7–13.5 A per motor (BUILD-MANUAL §10). But a hard attitude correction or a gust in hover can drive one motor to
  full output while the total stays under 85 A.

**Action:** on the thrust stand (TEST-PLAN thrust-stand series), record the DShot throttle at which one motor reaches
26 A on a full pack. Set `Q_M_SPIN_MAX` to that fraction (default 0.95) if it is lower. Record the thrust lost at the
cap: hover T/W is 1.68 on maker data (`analysis/results.json` `sized.TW`), so any cap reduces control authority.

### 2.4 X4: PETG clamp preload relaxes

DBF-VTOL `docs/research/tolerance-analysis.md` §5 applies a PETG creep law (its source S8, 22 h test, extrapolated
beyond that). It estimates preload relaxation of about 12 % in a day and 30 % in a week at 23 °C, faster when hot.
This repo uses the same printed PETG split clamps at 0.5 N·m EST (`docs/research/hardware-spec.md`). Witness marks are
already painted (BUILD-MANUAL 5.7, 7.x), but no re-torque interval was set.

**Action:** re-torque every printed-clamp screw 24 h after first assembly. After that, re-check torque against the
witness marks before each flight day, and after any day the aircraft sat in a hot car. If a screw needs more than
about 30° to return to torque, record it. If that happens twice, move that clamp to PA6-CF. (Rule after DBF-VTOL
tolerance-analysis §5 M3, numbers EST.)

### 2.5 X5: power trunk near the compass

The GPS/compass sits on a pad on the canopy top (`docs/build/print-list.csv` P24), at about y +0.073 m (canopy top
`canopyY` 0.015 + 0.0548 from `cad/mesh/Canopy.STL`, + 3 mm pad). The power path runs from the pack to the FC PDB at
y ≈ −0.009 m (`cad/params.txt` Flight_Controller). If the GPS sits right above the FC, the closest approach is about
0.065 m (EST: the GPS x station is not modelled). The field of one straight wire is B = μ₀I / 2πr = 2×10⁻⁷ × I / r.
That gives about 157 µT at hover 51.0 A and about 252 µT at the 82.1 A transition estimate *(calc, single wire,
EST)*. A twisted +/− pair cancels most of it.

**Action:** twist the pack leads to the PDB. Mount the GPS as far forward or aft of the FC as the canopy allows. Run
CompassMot at commissioning. ArduPilot's procedure (Copter docs; the Plane page links to it): "If it is less than 30%
then your compass interference is acceptable"; 31–60 % is a "grey zone"; above 60 %, move the compass
([ardupilot.org](https://ardupilot.org/copter/docs/common-compass-setup-advanced.html), checked 2026-11-03). Added
as firmware/README step 6.3a.

## 3. Already covered here by a different fix

| DBF-VTOL finding (v0.3.1) | Status in v0.4.0 |
|---|---|
| XT90S rated below the transition current | Replaced by the Amass AS150U, 70 A continuous (DESIGN-BASIS R20) |
| Lift current above the 90 A sensor | `Q_M_BAT_CURR_MAX 85` (BUILD-MANUAL §8.2 item 16 keeps the 3 A margin open) |
| DShot / PWM timer-group conflicts; PWM12 shared with the LED pad | Output map S5–S9 DShot, servos off DShot groups, S12 unused (`firmware/README.md` §4.4; `tools/check_params.py`) |
| Tube tolerances make the joiner fit bind | FT01 / FT06 and measurement M1 (`docs/research/hardware-spec.md` §5) |
| Printed holes come out small | Every bore and insert hole set by first-article coupon M2 (`hardware-spec.md` §5) |
| Pusher ground clearance 36 mm (proposed wheels to raise it) | v0.4.0 has 44.8 mm on the legs, ≥ 30 mm required (BUILD-MANUAL 8.6) |

## 4. Team resources linked, not copied

- **Inventory & electrical overview** (Tristan Hottier): purchasing, kit bins, wiring blueprint DBF-ELE-001, receiving
  and LiPo storage. It is built on the v0.3.1 BOM, so cross-check its quantities against `docs/purchasing/C0_BOM.csv`.
  [Online, view only](https://claude.ai/artifact/C6JEuXWN4B4Aoay5zHU3Pg).
- **Nautical Wings Aerospace carbon props**: a sponsorship offer reported by the team in October 2026, not yet
  confirmed in writing (DBF-VTOL `docs/research/nautical-wings-props.md`, which also has a spec sheet and acceptance
  tests). The props it would replace cost $76.17 in goods here: JeeFly 1755 2 × $18.60 + spare pair $18.60 + APC
  14x8.5EP 3 × $6.79 (`docs/purchasing/C0_BOM.csv`). That is $83.98 with the 10.25 % tax *(calc)*. If the props are
  free, the reserve rises from $145.45 to about **$229.43** (EST: shipping and any import cost are unknown, —). Until
  the offer is confirmed in writing, the BOM keeps the retail props.
