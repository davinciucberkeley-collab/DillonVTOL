// Cruise-speed trade for C0 (2026-10-26), prompted by the benchmark study (docs/research/benchmarks.md): both the
// literature (best-L/D speed just above stall) and the comparable aircraft (most cruise at 16.5-20 m/s) put C0's
// 20 m/s cruise well above its best-L/D speed.
// Run: node analysis/cruise_speed_trade.mjs -> writes analysis/cruise_speed_trade.json and prints the table.
// Read-only on the rest of the repo: reads analysis/results.json, writes ONLY analysis/cruise_speed_trade.json.
//
// Method: analysis/model.js size() (F1-F12) with C0's sized parameters and its fixed pack (2 x 144.3 Wh / 0.82 kg),
// varying only Vc. The wing is sized by stall (F4), so S, mass and hover are unchanged; cruise CL, L/D, power,
// current and the cruise time the fixed pack allows change. Propeller efficiency is held at 0.60 (EST) for every
// speed, which favours no speed. Speeds below 18 m/s are shown for reference only: R11 sets cruise at 18-22 m/s.
import { createRequire } from 'module';
import { readFileSync, writeFileSync } from 'fs';
const require = createRequire(import.meta.url);
const M = require('./model.js');
const R = JSON.parse(readFileSync(new URL('./results.json', import.meta.url)));
const P0 = { ...R.concepts.C0.params };
const R11 = [18, 22];

const s0 = M.size(P0);
// independent cross-check (literature, docs/research/benchmarks.md): CL* = sqrt(CD0 pi e AR), V* = sqrt(2W/(rho S CL*)),
// (L/D)max = 0.5 sqrt(pi e AR / CD0), V_minpower = V* / 3^0.25
const CLs = Math.sqrt(s0.CD0 * Math.PI * P0.e * s0.AR);
const Vstar = Math.sqrt(2 * s0.W / (P0.rho * s0.S * CLs));
const LDmax = 0.5 * Math.sqrt(Math.PI * P0.e * s0.AR / s0.CD0);

const rows = [];
for (let V = 14; V <= 22; V++) {
  const s = M.size({ ...P0, Vc: V });
  rows.push({ Vc: V, inR11: V >= R11[0] && V <= R11[1], CL: s.CL, LD: s.LD, D_N: s.D_cruise, P_cruise_W: s.P_cruise,
              I_cruise_A: s.I_cruise, t_cruise_avail_min: s.t_cruise_avail_min, overStall: V / P0.Vs, S: s.S, m: s.m });
}
const base = rows.find(r => r.Vc === P0.Vc);
for (const r of rows) r.dP_pct = 100 * (r.P_cruise_W / base.P_cruise_W - 1);

console.log(`C0 cruise-speed trade (fixed pack ${P0.EBattFixed} Wh; S ${s0.S.toFixed(3)} m2, m ${s0.m.toFixed(2)} kg, CD0 ${s0.CD0.toFixed(4)})`);
console.log(`cross-check: CL* ${CLs.toFixed(3)}, V* (best L/D) ${Vstar.toFixed(1)} m/s, (L/D)max ${LDmax.toFixed(2)}, V min-power ${(Vstar / 3 ** 0.25).toFixed(1)} m/s`);
console.log(' Vc  R11  V/Vs   CL     L/D   D N   P W    dP %   I A   cruise min');
for (const r of rows) console.log(`${String(r.Vc).padStart(3)}  ${r.inR11 ? 'yes' : ' no'}  ${r.overStall.toFixed(2)}  ${r.CL.toFixed(3)}  ${r.LD.toFixed(2).padStart(5)}  ${r.D_N.toFixed(2)}  ${r.P_cruise_W.toFixed(0).padStart(4)}  ${r.dP_pct.toFixed(1).padStart(6)}  ${r.I_cruise_A.toFixed(1)}  ${r.t_cruise_avail_min.toFixed(1)}`);

writeFileSync(new URL('./cruise_speed_trade.json', import.meta.url), JSON.stringify({
  generated: '2026-10-26', note: 'analysis/cruise_speed_trade.mjs; model.js size() with C0 params, fixed pack, Vc varied; etaProp held at 0.60 (EST)',
  baselineVc: P0.Vc, R11, crossCheck: { CLstar: CLs, Vstar_mps: Vstar, LDmax, Vminpower_mps: Vstar / 3 ** 0.25 }, rows },
  (k, v) => typeof v === 'number' ? +v.toPrecision(6) : v, 1));
