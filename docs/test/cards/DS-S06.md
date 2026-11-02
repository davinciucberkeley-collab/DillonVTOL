# Data sheet DS-S06 — Landing-gear drop test (0.6 m/s design hard touchdown)
DBF-TP-001 rev C data sheet · Test S06 · Date ____ · Operator ____ · Witness ____ · Article/serials ____

Article: airframe at flight mass 7.44 kg with the pack fitted (results.json sized.m; TEST-PLAN.md S06); leg fairings fitted; FC logging (LOG_DISARMED 1, restore after) or phone accelerometer at the CG. Surface: level concrete with a 3 mm rubber mat. Straight-edge and feeler gauges on each boom before and after.
Pass: no permanent bend (straight-edge gap unchanged within 0.1 mm), witness lines intact, no crack in the gear clamps; peak vertical acceleration ≤ the front-corner value of analysis/structures/landing.json (hard case 6.6 g). Predicted at 0.6 m/s (2 × Q_LAND_FINAL_SPD 0.3 m/s; h = v²/2g = 18.4 mm): front corner 6.6 g / 123 MPa (RF 1.96), rear corner 13.5 g / 146 MPa (RF 1.65) on 240 MPa minimum yield (landing.json).

| Drop | Height under feet (m) | Peak accel (g) | Source (IMU log / phone) | Leg set? | Gear clamp / boom clamp witness | Fairings ok? | Boom straight-edge gap (mm) | Pod contact? |
|---|---|---|---|---|---|---|---|---|
| 1 | 0.010 | | | | | | | |
| 2 | 0.010 | | | | | | | |
| 3 | 0.010 | | | | | | | |
| 4 | 0.020 | | | | | | | |
| 5 | 0.020 | | | | | | | |
| 6 | 0.020 | | | | | | | |
Estimated stroke from n = 2(1 + h/s): s = 2h/(n − 2) = ____ mm.

## Result
PASS / FAIL · Deviations: ____ · Signed (TD) ______ Date ______
