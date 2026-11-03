# Data sheet DS-C11 — Battery capacity, sag and internal resistance
DBF-TP-001 rev C data sheet · Test C11 · Date ____ · Operator ____ · Witness ____ · Article/serials ____

Pack: Ovonic 6S 6500 100C s/n ____ (A / B) · nameplate 144.3 Wh (results.json packs[0]) · charger HTRC C150 · load: ____ · watt meter s/n ____ · LiPo bag under the pack.

Full charge: resting ____ V (≥ 25.1) · cells (balance readout) ____ / ____ / ____ / ____ / ____ / ____ · pack temp start ____ °C

## Discharge log at 15 ± 2 A (cruise current 13.3 A at 18 m/s, results.json sized.I_cruise; 15 A kept as the conservative load EST) (every 30 s; or film the watt meter and transcribe). Save as CSV `t_s,volt_V,curr_A` for battery_test.py.
| t (s) | V (V) | I (A) | Ah | Wh | Note |
|---|---|---|---|---|---|
| 0 | | | | | |
| … | | | | | |
| end (21.0 V under load) | | | | | |

## Step loads at ~50 % delivered Ah
| Step | I before (A) | V before (V) | I during (A) | V during (V) | ΔV (V) | R_pack = ΔV/ΔI (mΩ) | R_cell = R_pack / 6 (mΩ) |
|---|---|---|---|---|---|---|---|
| 10 s at 54 A (hover at 21 V, results.json sized.I_hover_loaded 53.9 A) | | | | | | | |
| 3 s at 82 A (transition, sized.I_trans 82.1 A EST; needs all four lift motors) | | | | | | | |

Pass: delivered ≥ 110 Wh to 3.50 V/cell under load; V/cell ≥ 3.37 at 54 A (3.70 − 54 × 0.0060), ≥ 3.2 at 82 A; **R_cell ≤ 6.0 mΩ** (acceptance limit of the thermal model, analysis/thermal/thermal_inputs.py; a pack above it does not fly F11/F12; TEST-PLAN C11, DESIGN-BASIS R21); pack ≤ 60 °C EST; packs within 3 %. From a 3.70 V/cell rest the 3.4 V/cell line at 54 A allows only 5.6 mΩ/cell (calc), so record both.
Delivered Wh ____ · Ah ____ · min V/cell at 54 A ____ · at 82 A ____ · R_cell ____ mΩ (≤ 6.0: Y / N; written on the pack label ☐) · max pack start temperature for a full mission 60 − 4.7 × R_cell = ____ °C (TEST-PLAN C11, §6) · temp end ____ °C · recovery V after 30 min ____ · mAh returned on charge ____

## Result
PASS / FAIL · Deviations: ____ · Signed (TD) ______ Date ______
