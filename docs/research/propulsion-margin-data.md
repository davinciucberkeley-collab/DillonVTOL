# Propulsion margin data (R13 hover T/W)

Checked 2026-11-01. Machine-readable copy: `analysis/propulsion_data_2026-11-01.json` (source IDs S1–S19).
Rows marked **EST** are this note's own arithmetic, with the formula shown. Unknown = "—".

**Basis (EST):** MTOW 6.95 kg (midpoint of 6.9–7.0 kg). R13 needs T/W ≥ 1.6, so each of the 4 motors
needs 1.6 × 6950 / 4 = **2780 gf**.

## 1. SunnySky X4110S KV400, maker tables (S1)

Source: [sunnyskyusa.com product JSON](https://sunnyskyusa.com/products/sunnysky-x4110s-motors.js), `description` → "KV400" tab
(the HTML page returns HTTP 429). Motor rating: 45A/30s, 1125 W, 6S max, 107 mΩ, 165 g. The KV400
"Recommended Prop" list is 15×5.5, 16×6, 18×6.1 and 17×5.8. **So the maker lists 18×6.1 as compatible with KV400 on 6S.**

### Top of each table (full rows are in the JSON)

| Prop | V | Row | A | gf | W | g/W | 100 % load temp |
|---|---|---|---|---|---|---|---|
| 15×5.5 | 22.2 | max | 18.8 | 2430 | 417 | 5.82 | 53 ℃ |
| 15×5.5 | 25 | max | 22.3 | 2840 | 558 | 5.09 | — |
| 16×6 | 22.2 | 2600 | 21.8 | 2600 | 484 | 5.37 | 65 ℃ |
| 16×6 | 22.2 | max | 26.6 | 2930 | 591 | 4.96 | |
| 16×6 | 25 | max | 31.7 | 3400 | 793 | 4.29 | — |
| 17×5.8 | 22.2 | 2600 | 19.9 | 2600 | 442 | 5.89 | 75 ℃ |
| 17×5.8 | 22.2 | max | 27.7 | 3130 | 615 | 5.09 | |
| 17×5.8 | 25 | 3000 | 23.3 | 3000 | 583 | 5.15 | — |
| 17×5.8 | 25 | max | 33.3 | 3600 | 833 | 4.32 | |
| 18×6.1 | 22.2 | 2600 | 20.7 | 2600 | 460 | 5.66 | 83 ℃ |
| 18×6.1 | 22.2 | max | 32.2 | 3300 | 715 | 4.62 | |
| 18×6.1 | 25 | 3500 | 34.6 | 3500 | 865 | 4.05 | — |
| 18×6.1 | 25 | max | 38.4 | 3720 | 960 | 3.88 | |

**Table defects (as published):** the 16×6 / 25 V row "26 A, 2300 gf, 650 W" is out of sequence (likely a typo; excluded below).
The 18×6.1 / 22.2 V rows at 500, 1000, 1250 and 2000 gf are identical to the 17×5.8 rows, so treat the 18×6.1 table as low confidence below 2600 gf.

### What the tables imply for R13 (EST)

T/W = 4 × T_max / 6950 g. Current at 2780 gf: linear interpolation between bracketing rows; pack current = 4 × motor current.

| Prop | V | T/W at full throttle | Motor A at 2780 gf | Pack A at 2780 gf |
|---|---|---|---|---|
| 15×5.5 | 22.2 | 1.40 | — (above table max) | — |
| 16×6 | 22.2 | 1.69 | 24.4 | 98 |
| 17×5.8 | 22.2 | 1.80 | 22.5 | 90 |
| 18×6.1 | 22.2 | 1.90 | 23.7 | 95 |
| 17×5.8 | 25 | 2.07 | 20.6 | 82 |
| 18×6.1 | 25 | 2.14 | 21.3 | 85 |

The maker tables are at supply voltage on their stand. Thrust at sagging pack terminal voltage is not published ("—").
At the R13 point the pack must source **about 82–98 A**, above the 60 A continuous the repo assumes for the LiPo.

## 2. Ovonic 6S 6500 mAh 100C and independent LiPo data

| Item | Value | Source |
|---|---|---|
| Rating | 100C continuous, 200C burst | [ovonicshop.com](https://www.ovonicshop.com/products/ovonic-100c-22-2v-6500mah-6s-ec5-lipo-battery) (S2, seller) |
| Mass | 825 g ±20 g | same |
| Size | 149 × 46 × 56.5 mm | same |
| Internal resistance | — (not published) | same |
| Independent voltage at 80–100 A | **—, none found** | searched RCGroups, Reddit, YouTube, review sites |
| Independent DCIR per cell | **—, none found** | same |
| Temperature rise | **—, none found** | same |

The closest result is a [CNHL blog](https://chinahobbyline.com/blogs/news/ovonic-vs-cnhl-lipo-battery-comparison) (S3). CNHL is a competing brand,
the page returned HTTP 429, and the packs tested were a 6S 5500 mAh and a 4S 6500 mAh. It is not evidence for this pack.
No 6S 6000–8000 mAh LiPo in this price range had credible independent high-current test data either.
**The pack's sag at the R13 current has to come from our own bench test.**

## 3. Molicel P50B / P45B (6S2P Li-ion option)

| Cell | Continuous A | Impedance | Mass | Capacity | Source |
|---|---|---|---|---|---|
| P50B | 60 A (80 ℃ cut-off) | AC 6.5 mΩ (30 % SOC), **DC 12.8 mΩ (50 % SOC)** | 71 g max | 5000 typ / 4850 min mAh, 260 Wh/kg | [Molicel TDS v1.1](https://www.fsaeonline.com/content/Molicel-TDS--INR-21700-P50B-80122.pdf) (S4, maker); [molicel.com](https://www.molicel.com/product/inr-21700-p50b/) (S5) |
| P45B | 45 A max | 13.8 mΩ max | — | 4.5 Ah, 16.2 Wh | [molicel.com](https://www.molicel.com/inr21700-p45b/) (S6, maker) |
| P45B (Mooch) | **35 A recommended** for comparisons; the 50 A datasheet figure is temperature-limited | relative only | — | 4477 / 4488 mAh measured | [budgetlightforum, 2022-05-17](https://budgetlightforum.com/t/bench-test-results-molicel-p45b-50a-4500mah-21700/70213) (S7, independent) |
| P50B (Mooch) | — (rating not confirmed; thread blocked) | — | — | rated 5000 mAh | [e-cigarette-forum](https://www.e-cigarette-forum.com/threads/bench-test-results-molicel-p50b-60a-5000mah-21700.988690) (S8) |

**6S2P P50B (EST):** pack resistance from cells alone = 6 × 12.8 / 2 = 38.4 mΩ, so about 3.5 V sag at 90 A.
Capacity 10 Ah, energy 6 × 3.6 × 10 = 216 Wh, cell mass 12 × 71 = 852 g max, continuous 2 × 60 = 120 A (80 ℃ cut-off).
On Mooch's P45B logic, the 2P current to empty without overheating is lower than 120 A. A P50B number is —.

## 4. Connectors

| Connector | Continuous | Burst | Condition | Source |
|---|---|---|---|---|
| XT90 (Amass XT90H-M) | 45 A ("RC") | 90 A ("MC") | 10 AWG | [Amass datasheet V1.2](https://www.batimex.pl/zdjecia/pdf/xt90h-m.pdf) (S9, maker) |
| XT90 (Amass) | 45 A | 90 A | 10 AWG; 4 h / 1 min, ΔT < 60 ℃ | [Holybro](https://docs.holybro.com/power-module-and-pdb/power-module/connector-and-wire-rating) (S10) |
| XT90-S anti-spark | — | — | not listed | — |
| EC5 (E-flite) | > 120 A | — | with 10 AWG wire | [Horizon EFLAEC502](https://www.horizonhobby.com/product/connector-ec5-battery-2/EFLAEC502.html), [EFLAEC503](https://horizonhobby.com/product/connector-ec5-device-and-ec5-battery-set/EFLAEC503.html) (S11, maker) |

At 82–98 A, a genuine XT90 is over its 45 A continuous rating but within its 90 A, 1-minute rating only up to 90 A. EC5 has no published burst or ΔT condition.

## 5. SoloGood 45A ESC (S12)

[amazon.com/dp/B0DJQVGSBC](https://www.amazon.com/dp/B0DJQVGSBC), product description: **45 A continuous, 55 A for 10 s**, 2–6S, EFM8BB21F16G,
DShot 150/300/600, 6 g, **18 AWG × 80 mm power leads**. BEC and efficiency: —. Seller data only.
At 20–24 A per motor (table above) the ESC is at about half its rating. The 18 AWG leads are the item to check.

## 6. Hover T/W guidance

| Guidance | Battery state defined? | Source |
|---|---|---|
| Hover ideally ~50 % throttle; > 70 % "dangerous" | No | [ArduPilot QHOVER](https://ardupilot.org/plane/docs/qhover-mode.html) (S13) |
| Learned Q_M_THST_HOVER ~0.3–0.6; higher means not enough thrust | Thrust is voltage-scaled between 4.2 V/cell and 3.3 V/cell (LiPo), sag-compensated by default | [ArduPilot QuadPlane tuning](https://ardupilot.org/plane/docs/quadplane-vtol-tuning-process.html) (S14) |
| MOT_THST_HOVER usually 0.2–0.6 | No | [ArduPilot Copter](https://ardupilot.org/copter/docs/ac_throttlemid.html) (S15) |
| T/W minimum 1.6, recommended 2.0, professional 2.2–2.5 | No | [T-Motor guide, 2025-12-01](https://shop.tmotor.com/blog/vtol-propulsion-system-selection-guide) (S16, vendor) |
| Forum users: 1.2–1.5 (2022), 2–2.2 (2024) | No | [ArduPilot Discourse](https://discuss.ardupilot.org/t/recommended-thrust-to-weight-ratio-for-a-hybrid-vtol-uav/80510) (S17, not official) |
| DeltaQuad Evo MTOW 10 kg; Foxtech Loong 2160 ~7 kg + ~1.5 kg payload, "up to 120A" in hover | Lift-motor max thrust not published, so T/W is — | [DeltaQuad](https://docs.deltaquad.com/evo/vehicle-specifications) (S18), [PX4 Loong](https://docs.px4.io/main/en/frames_vtol/vtol_quadplane_foxtech_loong_2160) (S19) |

**EST:** ArduPilot's hover value is a fraction of maximum thrust, so a hover value of 0.5 means T/W = 1 / 0.5 = 2.0, and 0.3–0.6 means T/W of 1.7–3.3.
Because thrust is scaled to battery voltage between the max and min settings, the hover fraction is measured with sag compensation, not at a fixed state of charge.
PX4 docs gave no T/W recommendation. No peer-reviewed quadplane T/W value was retrieved, because the Wiley review returned HTTP 403.
None of these sources defines T/W at storage voltage. R13's "storage-low" condition is the project's own, stricter choice.

## Follow-up (checked 2026-11-01; JSON `followup`, IDs F1–F12)

### 18-inch props for the X4110S

| Prop | Seller | Price | CW+CCW | Mass/prop | Hub | Source |
|---|---|---|---|---|---|---|
| JeeFly 1855 (18×5.5) | Amazon, $4.99 delivery Nov 12–23 | **$19.99 / pair** | yes | — | 4 mm + 3 mm side holes @ 12 mm (same as JeeFly 1755) | [B0FJ22MCVJ](https://www.amazon.com/dp/B0FJ22MCVJ) (F1) |
| SunnySky Eolo carbon 18×6.5 | sunnyskyusa.com | $96.99 (pair/single —) | — | — | 15 mm bolt pattern | [sunnyskyusa.com](https://sunnyskyusa.com/products/eolo-carbon-fiber-uav-propellers-18x6-5-inch.js) (F2) |
| Tiger 18×6.1 carbon | GetFPV (US) | $25.19 / pair | yes | — | — | [getfpv.com](https://www.getfpv.com/tiger-18x6-1-carbon-fiber-props-pair.html) (F3), **out of stock** |
| T-Motor NS18×6 | store.tmotor.com (CN) | $82.99 / pair | L = CW, R = CCW | 17 g | — | [store.tmotor.com](https://store.tmotor.com/goods.php?id=964) (F4) |

SunnySky does not sell an 18×6.1. No in-stock 18×6.1 from a US seller was found. The only cheap in-stock 18-inch prop is the JeeFly 1855, and SunnySky publishes no X4110S table for 18×5.5 ("—").

### Connectors (Amass datasheets)

| Connector | Rated (continuous) | Short-time | Wire | Source |
|---|---|---|---|---|
| XT60H-M | 30 A | 60 A | 12 AWG | [Amass V1.2](https://cdn.eicom.ru/media/PDF/XT60H-M.pdf) (F9). Holybro: 4 h / 1 min, ΔT < 60 ℃ (S10) |
| XT90H-M | 45 A | 90 A | 10 AWG | S9 |
| **XT90S-F (anti-spark)** | **40 A** | 90 A | 10 AWG; contact resistance 0.56 mΩ vs 0.30 mΩ for XT90H | [Amass V1.2](https://sparks.gogo.co.nz/assets/_site_/downloads/XT90S_SPEC.pdf) (F5) |
| AS150U-F | 70 A (4 h, ΔT < 60 ℃) | 140 A (1 min, < 80 ℃) | 8 AWG. Wire table at ΔT 60/85 ℃: 8 AWG 80/90 A, 10 AWG 70/80 A, 12 AWG 40/50 A | [Amass sheet (LCSC)](https://atta.szlcsc.com/upload/public/pdf/source/20220706/9099BAC3F8F6B9A2C79768E315F09F94.pdf) (F6) |
| AS150U set | 75 A | 140 A | 8 AWG | [Neu Racing, $17.26](https://neuracing.us/product/as150u/) (F7, seller) |
| AS150 (7 mm), XT150 | — | — | — | no Amass sheet found (F8) |

**Boom disconnect (EST, from the coordinator's 28 A hover / 64 A full-thrust figures):** an XT60H carries the hover current at 93 % of its 30 A rating, and 64 A is above its 60 A 1-minute rating.
An XT90H carries 64 A within its 90 A 1-minute rating. An AS150U carries 64 A within its 70 A continuous rating.

### SoloGood 45A ESC (F10)

There is no maker motor or prop pairing, temperature rating or thermal protection in the [listing](https://www.amazon.com/dp/B0DJQVGSBC) ("—"). It has 6 ratings, averaging 3.7 of 5.

### ArduPilot QuadPlane landing descent (F11, F12)

| Parameter | Default | Units | Range | Source |
|---|---|---|---|---|
| Q_LAND_FINAL_SPD | 0.5 | m/s | 0.3–2 (step 0.1) | [params](https://ardupilot.org/plane/docs/parameters.html); default from [quadplane.cpp](https://raw.githubusercontent.com/ArduPilot/ardupilot/master/ArduPlane/quadplane.cpp) (same in Plane-4.5 branch) |
| Q_LAND_FINAL_ALT | 6 | m | 0.5–50 (step 0.1) | same |
| Q_LAND_SPEED | — | — | — | not in the current parameter list. The code notes that land-speed parameters moved from cm/s to m/s in Plane 4.5 (Jan 2024) |

Below Q_LAND_FINAL_ALT + 6 m, the code blends the descent speed linearly down to Q_LAND_FINAL_SPD at Q_LAND_FINAL_ALT.
