# Data sheet DS-S01 — Wing static proof load (limit 3.0 g)
DBF-TP-001 rev C data sheet · Test S01 · Date ____ · Operator ____ · Witness ____ · Article/serials ____

Article: complete wing on saddle + slip-fit joiner captured by the stop discs (C17 passed), M5 × 25 wing bolts 0.5 N·m EST (hardware-spec J10; DESIGN-BASIS rev 2026-11-01). Inverted on padded supports at ±0.10 m from centre. Tip gauges zeroed.

## Load schedule (TEST-PLAN.md S01; total 16.8 kg = 3.0 × (7.438 − 1.835) kg, results.json sized.m / m_wing generated 2026-11-02, Schrenk (rev 2026-11-02, was elliptic); bags at 30 % chord of the 322 mm chord)
| Station from centre (m) | 0.1 | 0.3 | 0.5 | 0.7 | 0.9 | 1.1 | per side |
|---|---|---|---|---|---|---|---|
| Mass per side at 100 % (kg) | 1.59 | 1.56 | 1.51 | 1.42 | 1.29 | 1.03 | 8.40 |
| at 25 % | 0.40 | 0.39 | 0.38 | 0.36 | 0.32 | 0.26 | 2.10 |
| at 50 % | 0.79 | 0.78 | 0.75 | 0.71 | 0.64 | 0.52 | 4.20 |
| at 75 % | 1.19 | 1.17 | 1.13 | 1.07 | 0.96 | 0.78 | 6.30 |

Actual bag masses used (kitchen scale): ____ (attach list)

## Deflection log
| Step | Left tip (mm) | Right tip (mm) | Sounds / observations | Socket foam cover ok? | Saddle bolts ok? |
|---|---|---|---|---|---|
| 0 % | 0 | 0 | | | |
| 25 % | | | | | |
| 50 % | | | | | |
| 75 % | | | | | |
| 100 % (start of 30 s hold) | | | | | |
| 100 % (end of hold) | | | | | |
| 75 % | | | | | |
| 50 % | | | | | |
| 25 % | | | | | |
| 0 % immediately | | | | | |
| 0 % after 5 min (residual) | | | | | |

Pass: tip at 100 % ≤ 120 mm; residual ≤ 2 mm EST; joiner straight ≤ 0.5 mm over 0.76 m; no crush; no loosening.
Predicted: 19.1 mm (FEA idealised joiner, cad/sim/results.txt spar_tip_disp 28.7 mm × 3/4.5, run 2026-11-02 13:19, Schrenk 91.0 N·m); real 19–60 mm EST. Joiner (slip fit, rev B) slid out post-test: straightness ____ mm; stop discs intact: Y / N.

## Result
PASS / FAIL · Deviations: ____ · Signed (TD) ______ Date ______
