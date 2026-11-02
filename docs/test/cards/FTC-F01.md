# Flight test card FTC-F01 — First lift-off and QSTABILIZE hops

DBF-TP-001 rev C · Test F01 · Review step: F3 (start); ArduPilot QuadPlane tuning step 5 · Requirements: R13, R20

**Prerequisites (signed in test-matrix.csv):** G05 tethered hover passed; G03 vibration clean; E05 failsafes; I02 site approved

**Configuration:** Full aircraft, pack only, no ballast (R12; G01 CG 28 % MAC). Mode slot 1 QSTABILIZE. Q_M_THST_HOVER 0.25, Q_A_THR_MIX_MAN 0.1 (first-flight values, firmware/vtol_c0.param s4). MS4525DO airspeed sensor at 0x28 detected (E08). Props on. No tether.

**Weather limits:** Steady <= 3 m/s EST, gusts <= 5 m/s EST; 10-30 degC.

**Predicted:** Hover throttle ~0.59 = 1,859 g / 3,130 g (results.json sized.Tunit_g, generated 2026-11-01; params.Tmax_g); hover current 51.0 A at 22.2 V (sized.I_hover); hover power 1,131 W (sized.P_hover).

**Crew:** TD, SO, PIC, GCS (VO = SO) · **Duration:** 1 session, 2 packs

## Pre-flight (every flight)
- [ ] Flight request approved for today and site (R19); Remote ID powered, broadcast seen (E12); registration mark on the pod; PIC TRUST/AMA documents on site (R18).
- [ ] Weather recorded at the field: wind steady ____ m/s, gusts ____ m/s (limit on this card), air temp ____ degC (F06-F13: <= 25 degC, DESIGN-BASIS R21 / TEST-PLAN.md s4 rule 9), visibility >= 3 sm, no precipitation.
- [ ] Weight and CG per G01: take-off mass ____ kg (<= 7.82 kg = 4 x 3.130 / 1.6, R13), CG ____ % MAC (28 +-2, never aft of 30.5), pack at its mark (G09); no ballast, nothing in the bay (R12): Y / N; leg fairings on: Y / N.
- [ ] Props: correct rotation, screws witness-marked, no nicks; pusher spin check.
- [ ] Witness lines on boom clamps, gear clamps, wing bolts unmoved.
- [ ] Packs >= 4.15 V/cell; pack strapped (J18); plugged in LAST through the AS150U.
- [ ] GCS: firmware hash ____; parameters checked with check_params.py; FENCE_ALT_MAX = site ceiling; FENCE_RADIUS = ____ m; EKF/GPS ok (sats >= 10, HDOP <= 1.5); compass consistent; airspeed 0 +-1 m/s, blow test >= 6 m/s.
- [ ] RC: arm switch CH5 off, mode CH6 in slot for this card, E-stop CH7 off, Q_ASSIST CH8 auto, RTL CH9 off; LQ >= 90 %.
- [ ] Range: crew line 30 m upwind, fire bag + extinguisher + first aid at the line, spectators behind, no people downrange, sky scan.
- [ ] Crew brief: TD states the build-up points, abort word "ABORT", who calls what. Timer ready.

## Hover limits on this aircraft (R14 accepted limitation, DESIGN-BASIS.md)
Hover-only flights: <= 5 m AGL and <= 60 s per hover; cool motors < 45 degC between hovers. C0 cannot survive a lift-motor failure in hover.

## Transition rule (firmware/README.md 9.6; SITL finding)
Start every transition at the upwind field edge and turn as soon as 'Transition done' appears: a straight transition reached the 300 m fence circle ~6 s after transition end in SITL. Telemetry: CRSF on the handset (or the ELRS MAVLink overlay); no separate radio.

## Build-up points (in order; stop and review the log between points when the card says so)
1. [ ] Arm in QSTABILIZE, disarm immediately (arming procedure check).
2. [ ] Arm; raise throttle slowly until the gear goes light; set down. Watch for oscillation (ArduPilot step 5).
3. [ ] Lift to 0.5 m, hold 5 s, land.
4. [ ] Lift to 1 m, hold 10 s, land. Motors < 45 degC before the next point.
5. [ ] At 1 m: +-5 deg roll input, then +-5 deg pitch input, land. Total hover time this flight <= 60 s.

## Abort criteria (card-specific items first, then the universal list)
- Any oscillation at lift-off: throttle down at once; halve Q_A_RAT_* P/I/D per tuning step 6 before the next attempt.
- Attitude error > 15 deg; drift > 3 m from the pad; lift output > 70 % to hold 1 m (expected ~59 %).
Universal (TEST-PLAN.md s5): VIBE > 30 m/s2 or rising clipping; attitude error > 15 deg; any oscillation; sag-compensated voltage < 21.0 V or < 1,625 mAh remaining (firmware low-battery RTL point; critical 19.8 V / 1,300 mAh -> QLAND); motor can > 80 degC EST after landing; wind above the card limit; LQ < 70 % EST or any failsafe message; EKF/GPS/compass warning; people or animals inside the range; manned aircraft converging.

## Data to record
QTUN.ThO (hover throttle), ATT roll/pitch vs DesRoll/DesPitch, VIBE X/Y/Z and Clip, BAT Curr/Volt, RCOU C5-C8, MSG.

## Pass criteria
- [ ] No oscillation at any point; attitude error < 15 deg (review F2).
- [ ] VIBE < 30 m/s2, clipping 0 (ArduPilot measuring vibration, checked 2026-10-21).
- [ ] Hover output < 60 % (review F2); expected ~0.59 = 1,859 / 3,130 g (calc; results.json sized.Tunit_g): only 1 point of margin, so an output of 60-62 % is recorded and reviewed against the C07 thrust (R13 limit 1 / 1.6 = 0.625).
- [ ] Hover current 51.0 A +-15 % EST at 22.2 V (results.json sized.I_hover).
- [ ] Motors <= 80 degC EST after landing.

## Run log

| Run | Time | Pack V/cell start | Wind | Point reached | Result | Notes |
|---|---|---|---|---|---|---|
| 1 | | | | | | |
| 2 | | | | | | |
| 3 | | | | | | |

## Post-flight (every flight)
- [ ] IR temperatures within 30 s: M1 ____ M2 ____ M3 ____ M4 ____ pusher ____ ESC max ____ pack ____ degC (any unit 15 degC hotter than its neighbours or pack > 60 degC EST grounds the aircraft).
- [ ] Pack: resting V/cell ____; mAh returned on charge ____.
- [ ] Airframe walk-round: witness lines, prop nicks, foam skin, gear.
- [ ] Log copied from the SD card and named `YYYY-MM-DD_F01_r<n>_C0.bin`; run `docs/test/analysis/log_summary.py` on it.
- [ ] Post-flight report filed within 3 business days for on-campus flights (R19).
- [ ] Result: PASS / PASS WITH LIMITS / FAIL. TD ______ SO ______ PIC ______ Date ______
