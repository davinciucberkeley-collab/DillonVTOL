# BOM savings and shipping check (2026-11-01)

Data: `analysis/bom_savings_2026-11-01.json`. All prices were checked 2026-11-01. "EST" means estimate. "—" means unknown.
Shipping quotes come from each store's own cart estimate to Berkeley CA 94720 (Shopify `cart/shipping_rates`; no checkout was started).

## Verdict

- **Adopt one change: the ESC swap.** It saves $19.98 in goods ($22.03 with tax). It also fixes a stock problem: the SoloGood listing shows "Only 1 left".
- **The $110 shipping allowance is too low.** Cart quotes plus estimates come to **$186.94** (+20 % on the estimated lines). Most of the gap comes from two China-shipped vendors: Holybro ($37.47) and RadioMaster ($30.00).
- **Net result: the reserve falls from $80.58 to $23.76.** The > $100 goal is not met.

## Line items

| BOM item | Now | Proposal | New | Δ | Source |
|---|---:|---|---:|---:|---|
| SoloGood 45A 4-pack ×2 | $79.98 | LANRC BLHeli_S 45A, 4-pack ×2 (45 A cont / 55 A 10 s, 2–6S, DShot600, 18 AWG, 6.6 g) | $60.00 | −$19.98 | https://www.amazon.com/dp/B0D2HS4Y4J |
| Hot-wire allowance | $40.00 EST | NICE-POWER 0–30 V 10 A supply (B0CRSS744F) $33.24 + Ni80 24 AWG 50 ft (B0CP9V3DBX) $8.49 | $41.73 | +$1.73 | Amazon search pages |
| Holybro MS5525 + PT40 | $59.99 | no change: Matek ASPD-4525 (ARSPD_TYPE 1) is out of stock at all US sellers (WREKD $59.99, GetFPV $64.99, RDQ $59.99) | $59.99 | 0 | see JSON |
| HTRC C150 charger | $56.99 | no change: nothing cheaper that delivers ≥ 126 W from AC (≥ 5 A on 6S) | $56.99 | 0 | Pyrodrone $57.99 + $8.19 shipping |

**ESC spec check.** Rating, firmware, protocol, size and lead gauge all match the SoloGood listing.

**ESC risks:**
- The seller is Sparkhobby, which charges $1.50 delivery per pack.
- Delivery is Nov 13, so it likely ships from China.
- The listing has only 3 ratings, and the page says "15 left".

**Hot-wire sizing (estimate):**
- Resistance per metre: R = ρ/A = 1.12e-6 / 2.051e-7 = 5.46 Ω/m (ρ from https://en.wikipedia.org/wiki/Nichrome).
- A 1.4 m wire has R = 7.6 Ω.
- At 2 A this needs 15.3 V and 31 W, which is within the supply's rating.

## Shipping to 94720

| Vendor | Cost | Basis |
|---|---:|---|
| SunnySky USA (6 motors) | $0.00 | cart: free domestic over $100 |
| RaceDayQuads (GPS + BeeID) | $6.49 | cart: USPS Ground Advantage |
| RadioMaster (TX + RX) | $30.00 | cart "Standard"; ships from CN, 10–20 working days |
| Holybro (airspeed) | $37.47 | cart: DHL/FedEx Air; ships from CN |
| EMAX USA (5 servos) | $8.99 | cart "Standard" |
| Amazon | $4.99 + $3.00 | JeeFly delivery (BOM note) + LANRC $1.50 ×2; the rest is free over $35 |
| Home Depot, Harbor Freight | $0.00 | store pickup |
| OnlineMetals (3 tubes, 96 in box) | $50 EST | UPS rate shown only at checkout; > 48 in surcharge about $32 (atoship.com 2026, unofficial) |
| ReadyMadeRC, Bolt Depot, Neu Racing | $10 EST each | rates shown only at checkout |

Totals:
- Quoted: $90.94.
- Estimated: $80.00, or $96.00 with the +20 % contingency.
- **New allowance: $186.94.**
- Import duties on the CN-shipped items: —.

## Budget after the changes

| Goods | Tax 10.25 % | Shipping | Total | Reserve |
|---:|---:|---:|---:|---:|
| $1,622.95 | $166.35 | $186.94 | $1,976.24 | **$23.76** |

## Flags found while checking

- The CoreWing F405 Wing V2 is "Unavailable" at ReadyMadeRC.
- The BeeID is out of stock at RDQ. It is in stock at newbeedrone.com for $39.99.
- The SoloGood ESC shows "Only 1 left".

## Next levers (not yet priced)

- Get a real OnlineMetals UPS quote. It is the largest unknown.
- Re-check US stock of the Matek ASPD-4525. It costs the same as the Holybro kit and would avoid most of the $37.47 shipping.

## Consolidation (follow-up, 2026-11-01)

**Verdict:** move all seven avionics and servo lines into one ReadyMadeRC (RMRC) order. Most of the China shipping goes away.
- Goods go up by $22.39 ($369.66 to $392.05).
- About $93 of vendor shipping is removed (RadioMaster $30.00, Holybro $37.47, RDQ $6.49, EMAX $8.99, RMRC EST $10).
- RMRC policy: free shipping when the cheapest rate is under 5 % of the order total (https://www.readymaderc.com/pages/shipping-returns). For this order that limit is $19.60. Small-parcel cart quotes to 94720 were $6.49–$14.99, so the order should ship free. This is an estimate; it was not cart-verified.

| Item | Was (vendor, $) | RMRC $ | Stock |
|---|---|---:|---|
| Pocket Crush ELRS | RadioMaster CN, 64.99 | 76.99 | In Stock |
| RP3 V2 | RadioMaster CN, 19.99 | 22.96 | Backorder (ProgressiveRC has it in stock at $21.99) |
| Airspeed: RMRC MS4525DO + pitot | Holybro CN MS5525, 59.99 | 59.99 | In Stock |
| GPS: RMRC SAM-M10Q-5883 | RDQ HGLRC M100, 20.49 | 24.99 | In Stock |
| BeeID v1.1 | RDQ (now out of stock), 36.99 | 39.99 | Only 2 left |
| CoreWing F405 Wing V2, unsoldered pins | RMRC soldered (unavailable), 67.26 | 67.18 | Backorder, "Nov 2026" |
| ES3005HV ×5 | EMAX USA, 99.95 | 99.95 | In Stock |

**Flight controller**
- The unsoldered CoreWing is the same board as the one in the BOM: 12 outputs (1–10 DShot), the same timer groups, a 90 A sensor and an 8 A servo BEC (https://ardupilot.org/plane/docs/common-CoreWingF405WingV2.html). The output map in `vtol_c0.param` therefore stays unchanged.
- The Wing Mini V2 ($52.13, in stock) was rejected. Its 4 A servo BEC is below the 8 A check in `firmware/README.md` §7.
- In-stock fallback: Kakute H743-Wing at $107.42. It needs an output remap.

**Airspeed sensor:** the RMRC sensor is an MS4525DO, so set `ARSPD_TYPE` to 1 (it is 5 now). Its address is 0x28, so the 0x76/0x77 address-strap step for the MS5525 is no longer needed.

**Free-shipping thresholds:**
- RMRC: the 5 % rule above.
- RaceDayQuads, GetFPV and Pyrodrone: free at $199.
- SunnySky: free at $100 (cart quote $0 for the 6 motors).

OnlineMetals still has no cart quote, because getting one requires entering a checkout address.

**Shipping:**
- Quoted: $7.99 (Amazon).
- Estimated: $70 (OnlineMetals $50, Bolt Depot $10, Neu Racing $10, RMRC $0), or $84 with the +20 % contingency.
- **New allowance: $91.99.**

**Budget with the LANRC ESC swap, the priced hot wire and consolidation:**

| Goods | Tax | Shipping | Total | Reserve |
|---:|---:|---:|---:|---:|
| $1,645.34 | $168.65 | $91.99 | $1,905.98 | **$94.02** |

**Risks**
- RMRC holds the whole order until the backordered FC and RP3 arrive.
- The 5 % shipping rule has not been verified on a cart.
- Only 2 BeeID units are left.
- OnlineMetals is still an estimate.
