# Data sheet DS-G01 / DS-G09 — Weight and balance; CG versus pack station (no ballast)
DBF-TP-001 rev C data sheet · Test G01 · Date ____ · Operator ____ · Witness ____ · Article/serials ____

Method: two kitchen scales under the wing at stations x1 and x2 from the wing leading edge (or one scale + pivot). MAC = chord = 322.3 mm (results.json sized.chord 0.32233, generated 2026-11-01; cad/params.txt chord); x_LE of the wing at the saddle is the datum. CG % MAC = 100 × x_cg / 322.3.
Targets: 28 ± 2 % MAC (± 6.4 mm) with the pack and nothing in the bay (cg.pct.target; no ballast, R12); never aft of 30.4 % MAC (NP 38.4 % with the pod, aero_results neutral_point.AVL_pod_pct_MAC 38.40, − 8 % SM); within 20 mm of the thrust centroid at x = 90.3 mm aft of the LE (cg.thrustCentroid −0.0903 m). Mass ≤ 7.82 kg (4 × 3.130 / 1.6, R13).

| Configuration | x1 (mm) | m1 (kg) | x2 (mm) | m2 (kg) | Total (kg) | x_cg = (m1 x1 + m2 x2)/(m1+m2) (mm) | % MAC | Pass? |
|---|---|---|---|---|---|---|---|---|
| Empty (no pack; S09 limit ≤ 7.00 kg) | | | | | | | | |
| Pack at its mark x = 255 mm (flight config; G09: expected 28.0 % MAC) | | | | | | | | |
| Pack 30 mm forward (G09: expected 27.0 % MAC) | | | | | | | | |
| Pack 30 mm aft (G09: expected 29.0 % MAC) | | | | | | | | |

Predicted: take-off mass 7.44 kg (results.json sized.m); 28.0 % MAC at the pack mark, 27.0–29.0 % over ± 30 mm of pack travel (results.json cg.pct.target, pctFwd, pctAft; cg.xb 0.255 m); static margin 10.5 % aero / 10.2 % sizing at 28 % (aero_results neutral_point.static_margin_pct; results.json geo.SM). No ballast (DESIGN-BASIS R12 revised 2026-11-01). Pack position mark on the pod: ____ mm from the frame.
Lateral CG: tip scales L ____ kg R ____ kg (difference ≤ 2 % EST). Span tip-to-tip: ____ m (2.40 ± 0.02, I03).

## Result
PASS / FAIL · Deviations: ____ · Signed (TD) ______ Date ______
