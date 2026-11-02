# Data sheet DS-S01 — Wing static proof load (limit 3.0 g)
DBF-TP-001 rev C data sheet · Test S01 · Date ____ · Operator ____ · Witness ____ · Article/serials ____

Article: complete wing on saddle + slip-fit joiner captured by the stop discs (C17 passed), M5 × 25 wing bolts 1.0 N·m EST (hardware-spec J10; DESIGN-BASIS rev 2026-11-01). Inverted on padded supports at ±0.10 m from centre. Tip gauges zeroed.

## Load schedule (TEST-PLAN.md S01; total 16.8 kg = 3.0 × (7.436 − 1.833) kg, results.json sized.m / m_wing generated 2026-11-01, elliptic; bags at 30 % chord of the 322 mm chord)
| Station from centre (m) | 0.1 | 0.3 | 0.5 | 0.7 | 0.9 | 1.1 | per side |
|---|---|---|---|---|---|---|---|
| Mass per side at 100 % (kg) | 1.78 | 1.72 | 1.62 | 1.44 | 1.17 | 0.67 | 8.40 |
| at 25 % | 0.44 | 0.43 | 0.40 | 0.36 | 0.29 | 0.17 | 2.10 |
| at 50 % | 0.89 | 0.86 | 0.81 | 0.72 | 0.59 | 0.33 | 4.20 |
| at 75 % | 1.33 | 1.29 | 1.21 | 1.08 | 0.88 | 0.50 | 6.30 |

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
Predicted: 17.6 mm (FEA idealised joiner, cad/sim/results.txt spar_tip_disp 26.3 mm × 3/4.5, run 2026-11-02); real 18–60 mm EST. Joiner (slip fit, rev B) slid out post-test: straightness ____ mm; stop discs intact: Y / N.

## Result
PASS / FAIL · Deviations: ____ · Signed (TD) ______ Date ______
