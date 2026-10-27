# Benchmarks: C0 against published aircraft and the literature

Checked 2026-10-26. Data: `analysis/benchmarks/aircraft.csv` (22 published small VTOL aircraft plus C0, rebuilt by
`analysis/benchmarks/build_bench.py`, every row with its source URL) and `analysis/benchmarks/literature.csv`
(37 values from papers, theses, maker data and ArduPilot documentation). How design reviews elsewhere are laid out:
`docs/research/review-formats.md`. Values marked EST are engineering estimates; "—" means not published.

## 1. Why this study

C0 had been checked only against its own models. This study asks two questions: does C0 look like the small lift +
cruise aircraft that actually fly, and are its modelling assumptions in line with published measurements? Where the
answer showed room for improvement inside the fixed $2,000 budget, the design was changed (§4).

## 2. C0 against 22 aircraft

Sixteen lift + cruise aircraft (DeltaQuad Evo and Pro, Foxtech Baby Shark 260 and Loong 2160, MakeFlyEasy Fighter,
Striver Mini and Freeman 2300, JOUAV CW-007, CW-10 and CW-20E, Avy Aera, ALTI Transition, Mugin-2 Pro, two
Skywalker X8 quadplane builds, U. Michigan QuadPlane) and six tilt-rotor or tailsitter aircraft for contrast.

| Metric | C0 | Published aircraft (aircraft.csv) | Reading |
|---|---|---|---|
| Wing loading, kg/m² | 9.6 | 6.9 (DeltaQuad Pro) to 15.9 (Fighter) for battery lift + cruise | lower middle; set by the 12 m/s stall limit |
| Disk loading, N/m² | 110 | 126 to 315 above 3 kg | lowest: efficient hover, large stopped props |
| Battery energy per kg MTOW, Wh/kg | 22 | 51 (Aera) to 98 (Evo, EST) | lowest: C0's mission is 12 min, theirs 1 to 4 h |
| Battery mass fraction | 0.13 | 0.20 to 0.40 | lowest, for the same reason |
| Cruise speed, m/s | 20 → **18** (§4) | 16 to 24; most 16.5 to 20 | 18 is inside the common band |
| W·V/P (= L/D × propulsive efficiency) | 3.8 at 20 m/s, 4.4 at 18 m/s | 3.5 (WingtraOne) to 8.4 (Evo, upper bound) | below the better lift + cruise aircraft |

Data quality: endurance figures are maker claims (one used Baby Shark seller reports about 30 min flown against a
2.5 h claim); battery energy is published by only three makers, the rest assume 3.7 V per cell; W·V/P values for
the published aircraft assume 90 to 100 % of the pack is used and are upper bounds. C0's W·V/P at 18 m/s:
6.55 × 9.81 × 18 / 264 = 4.4 *(calc, `analysis/cruise_speed_trade.json`)*.

The battery and mass-fraction gaps are a consequence of the requirement, not a defect: R10 asks for 10 min cruise and
2 min hover with 20 % reserve, and the cheapest pack that meets it (and the 60 A hover current) is what the sizing
picks. A long-endurance aircraft would carry three to four times the battery fraction.

## 3. C0's assumptions against the literature

| Assumption | C0 | Literature (literature.csv) | Verdict |
|---|---|---|---|
| CD0 rise from lift rotors and booms | 0.0266 → 0.0445 (+67 %) | retraction cuts parasitic drag 36 to 38 %; FW-VTOL CD0 +35 % in a sizing model | typical |
| Stopped lift unit drag area | 0.0022 m² per unit (prop + motor + mount, `aero_results.json`) | Hoerner/Pollet model 0.1 σ A_disk: 0.0015 to 0.0022 m² for the prop alone (σ EST) | at the low end: the prop alone could reach our whole-unit value |
| Prop parked across the flow | not modelled | braked 2-blade rotors across the chord add 25 to 30 % drag vs aligned | supports the stop-pawl test (review §3 M1) |
| Cruise propeller efficiency | 0.60 | about 0.65 measured peak for small props; 0.74 to 0.76 APC predictions at our point | conservative; kept |
| Hover FM·η (electrical) | 0.516, from the X4110S maker table | 0.567 from T-Motor MN5008 data at the same thrust; rotor FM 0.58 to 0.67 | conservative; kept (it is our motor's own data) |
| Transition energy | 40 s at 1590 W (64 kJ) | about 29 kJ scaled from a 25 kg quadplane (EST) | conservative; kept |
| LiPo specific energy | 176 Wh/kg (the chosen pack's label: 144.3 Wh / 0.82 kg) | 154 to 159 Wh/kg for 6S 10 Ah packs | label-based; the 0.95 usable factor and 20 % reserve cover part of the gap |
| Oswald e | 0.80 | 0.798 from Raymer's correlation at AR 8.45 | typical |
| Hover T/W | 1.91 | about 2.0 (25 kg quadplane), "about 2:1" (ArduPilot users) | typical |
| Static margin | 11.5 % with payload, 4.9 % empty | 5 to 15 % (Drela) | empty case just below; the 0.5 kg ballast rule restores 11.5 % |
| Tail volumes | Vh 0.35, Vv 0.03 | Vh 0.30 to 0.60, Vv 0.02 to 0.05 (Drela); 0.50 / 0.04 homebuilt (Raymer) | inside the UAV range, light against homebuilt values |
| **Cruise speed** | **20 m/s** | best L/D just above stall; a quadplane study finds the optimum at 12 m/s for an 11.9 m/s stall | **20 m/s is far above C0's best-L/D speed of 12.6 m/s** |

Independent cross-check from the literature equations, using C0's own polar:
CL* = √(CD0 π e AR) = 0.972, V* = √(2W / (ρ S CL*)) = 12.6 m/s, (L/D)max = ½ √(π e AR / CD0) = 10.9
*(calc, `analysis/cruise_speed_trade.mjs`)*.

## 4. Decisions

1. **Adopted: cruise at 18 m/s instead of 20 m/s.** R11 sets cruise at 18 to 22 m/s; 18 m/s is the edge of that band
   closest to the best-L/D speed. With the same pack, cruise power falls from 338 W to 264 W (−22 %), cruise current
   from 15.2 A to 11.9 A, and the cruise time the pack allows rises from 12.3 to 15.7 min against R10's 10 min
   (`analysis/cruise_speed_trade.json`). Mass, wing, CAD, drawings and structure do not change: the wing is sized by
   stall. 18 m/s is 1.53 × the design stall and 2 m/s above AIRSPEED_MIN (16 m/s), so the transition schedule is
   unchanged. Updated: `analysis/sizing.mjs` Vc, the aero package (cruise Reynolds number 3.5 × 10⁵), the flight
   parameter file (AIRSPEED_CRUISE 18) and every page that quotes cruise.
2. **Kept, conservative:** propeller efficiency 0.60, hover FM·η 0.516 and the 64 kJ transition. The literature puts
   all three on the safe side, so the predicted margins are, if anything, understated.
3. **Not changed: battery size.** A larger battery fraction would match the published aircraft but buys endurance the
   requirements do not ask for, and the 18 m/s cruise already raises the energy margin by 28 %. A Li-ion 21700 pack
   (about 230 Wh/kg at cell level) remains an option if a longer mission is ever wanted; it would need checking against
   the 72 A transition peak.
4. **Not changed: tail volumes.** Both are inside the published UAV range and the AVL static margin is positive in
   every loading with the ballast rule. Flight test F-series pitch and yaw doublets will show whether more fin is needed.
5. **Test emphasis added:** the car-roof stopped-rotor test (review §3 M1) now also records whether the props park
   along or across the flow, since the literature shows a 25 to 30 % drag difference.

## 5. Sources

Every aircraft and literature value above traces to a row in `analysis/benchmarks/aircraft.csv` or
`analysis/benchmarks/literature.csv`, each with its URL and the date checked. Principal sources:

- Pollet, Delbecq, Budinger, Moschetta et al., fixed-wing VTOL UAV sizing, ICAS 2022-0383: https://icas.org/icas_archive/ICAS2022/data/papers/ICAS2022_0383_paper.pdf (checked 2026-10-26)
- Mathur and Atkins, wind-tunnel testing of a quadplane, arXiv 2301.12316: https://arxiv.org/abs/2301.12316 (checked 2026-10-26)
- Mathur and Atkins, quadplane cruise-speed optimisation, arXiv 2411.08661: https://arxiv.org/html/2411.08661v1 (checked 2026-10-26)
- Brandt and Selig, small propeller performance, AIAA 2011-1255: https://m-selig.web.engr.illinois.edu/pubs/BrandtSelig-2011-AIAA-2011-1255-LRN-Propellers.pdf (checked 2026-10-26)
- Russell, Jung, Willink, Glasner, small multirotor rotor performance, NASA 2016: https://rotorcraft.arc.nasa.gov/Publications/files/72-2016-374.pdf (checked 2026-10-26)
- Drela, MIT 16.Unified design rules (tail volumes, static margin): https://web.mit.edu/16.unified/www/SPRING/systems/Lab_Notes/desrules.pdf (checked 2026-10-26)
- DeltaQuad Evo specifications: https://docs.deltaquad.com/evo/vehicle-specifications (checked 2026-10-26)
- Wingcopter 178 technical data: https://wingcopter.com/wp-content/uploads/2021/02/Technical-Details-Wingcopter-178-Heavy-Lift-A-Delivery-Variant-1-1.pdf (checked 2026-10-26)
- NASA NPR 7123.1D, PDR and CDR entrance and success criteria: https://explorers.larc.nasa.gov/APSMEX25/SMEX/pdf_files/NASA02_NPR_7123_1D.pdf (checked 2026-10-26)
