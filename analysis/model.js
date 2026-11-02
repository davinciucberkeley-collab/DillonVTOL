/* Lift + cruise VTOL sizing model. Single source of truth: run by analysis/sizing.mjs (Node)
   and embedded verbatim in review/vtol-review.html for the live chain and sliders.
   Units: SI unless the name says otherwise. G = 9.80665 m/s^2.

   F1  hover thrust per thrust unit  T = m g / n_units          (n_units = n_lift, or n_lift/2 for coaxial)
   F2  ideal hover power per unit    P_i = T^1.5 / sqrt(2 rho A),  A = pi D^2 / 4   (momentum theory); coax pair: 2 (T/2)^1.5 / sqrt(2 rho A)
   F3  electrical hover power        P_h = n_units * P_i * k_coax * k_ctrl / (FM*eta_me)
         FM*eta_me interpolated from the motor maker's thrust table at the hover thrust (calibFMeta).
   F4  wing area from stall          S = 2 m g / (rho Vs^2 CLmax)
   F5  cruise lift coefficient       CL = 2 m g / (rho Vc^2 S)
   F6  drag polar                    CD = CD0_clean + sum(CdA)/S + CL^2 / (pi e AR)
   F7  cruise electrical power       P_c = (m g / (L/D)) Vc / (eta_prop * eta_me_c)
   F8  mission energy                E = P_h (t_hover + t_trans) + P_c t_cruise
   F9  pack energy needed            E_pack = E / ((1 - reserve) * eta_batt)
   F10 battery mass                  m_b = E_pack / e_spec        (or a fixed real pack mass)
   F11 wing mass                     m_w = S [rho_foam 0.68 (t/c) c + 2 w_glass (1 + r_resin)] + m_spar
   F12 MTOW closure                  m = m_fixed + m_lift + m_booms + m_wing + m_tail + m_b ; iterate to 1e-4 kg
*/
(function(root){
const G = 9.80665;

function calibFMeta(T_g, P_W, D_m, rho){            // one thrust-table point -> FM * eta_motor_esc
  const T = T_g/1000*G, A = Math.PI*D_m*D_m/4;
  return (Math.pow(T,1.5)/Math.sqrt(2*rho*A))/P_W;
}
function interpFMeta(table, D, rho, T_g){            // table: [[thrust_g, power_W], ...] ascending
  const pts = table.map(([t,p])=>[t, calibFMeta(t,p,D,rho)]);
  if(T_g<=pts[0][0]) return pts[0][1];
  for(let i=1;i<pts.length;i++) if(T_g<=pts[i][0]){
    const [t0,f0]=pts[i-1],[t1,f1]=pts[i]; return f0+(f1-f0)*(T_g-t0)/(t1-t0); }
  return pts[pts.length-1][1];
}

function size(p){
  let m = p.m_guess || 10, it = 0, r = {};
  for(it=0; it<300; it++){
    const W = m*G;
    // hover (F1–F3)
    const nUnits = p.coax ? p.nLift/2 : p.nLift;
    const A = Math.PI*p.liftD*p.liftD/4;
    const Tunit = W/nUnits;
    const Tmotor_g = Tunit/G*1000/(p.coax?2:1)*(p.coax?p.kCoax:1); // per-motor thrust (coax: each motor works harder)
    const FMeta = p.FMetaFixed || interpFMeta(p.thrustTable, p.liftD, p.rho, p.coax ? Tunit/G*1000/2 : Tunit/G*1000);
    // coax: the 22 % loss is measured against two isolated rotors each carrying T/2, so the baseline is 2 (T/2)^1.5 / sqrt(2 rho A)
    const Pi_unit = p.coax ? 2*Math.pow(Tunit/2,1.5)/Math.sqrt(2*p.rho*A) : Math.pow(Tunit,1.5)/Math.sqrt(2*p.rho*A);
    const P_hover = nUnits*Pi_unit*(p.coax?p.kCoax:1)*p.kCtrl/FMeta;
    // wing (F4–F6)
    const S = 2*W/(p.rho*p.Vs*p.Vs*p.CLmax);
    const AR = p.span*p.span/S, chord = S/p.span;
    const CL = 2*W/(p.rho*p.Vc*p.Vc*S);
    const CdA_extra = p.nLift/(p.coax?2:1)*p.CdA_rotor + p.nBooms*p.CdA_boom;
    const CD0 = p.CD0_clean + CdA_extra/S;
    const CDi = CL*CL/(Math.PI*p.e*AR);
    const LD = CL/(CD0+CDi);
    const P_cruise = (W/LD)*p.Vc/(p.etaProp*p.etaMEc);
    // energy (F8–F10)
    const E_Wh = (P_hover*(p.tHover+p.tTrans) + P_cruise*p.tCruise)/3600;
    const Epack_req_Wh = E_Wh/((1-p.reserve)*p.etaBatt);
    const m_batt = p.mBattFixed || Epack_req_Wh/p.eSpec;
    const Epack_Wh = p.mBattFixed ? p.EBattFixed : Epack_req_Wh;
    // structure (F11)
    const sigmaWing = p.rhoFoam*0.68*p.tc*chord + 2*p.wGlass*(1+p.rResin);
    const m_wing = S*sigmaWing + p.m_spar + (p.mWingHardware || 0);   // printed hardpoints, pillar, tongue, stops, saddle plates (analysis/mass/mass_budget.json)
    const S_tail = p.tailAreaRatio*S;
    const m_tail = S_tail*p.sigmaTail + (p.mTailHardware || 0);       // fin shoes, tail clamps, crush sleeves (analysis/mass/mass_budget.json)
    const m_booms = p.boomTotalLen*p.boomLin + p.nBooms*2*p.boomClamp;
    const m_lift = p.nLift*(p.mMotor+p.mEsc+p.mProp+p.mMount);
    const m_fixed = p.mFus + p.mGear + p.mAvionics + p.mPusherSet + p.mServos + p.mWiring + p.nLift*p.mWirePerLift + p.mPayload + (p.mFasteners || 0);   // + every screw, nut, washer, insert (CAD)
    const m_new = m_fixed + m_lift + m_booms + m_wing + m_tail + m_batt;
    const TW = (p.nLift*p.Tmax_g/1000/(p.coax?p.kCoax:1))/m_new;
    r = {m:m_new, W:m_new*G, nUnits, Tunit_N:Tunit, Tunit_g:Tunit/G*1000, Tmotor_g, A, FMeta, Pi_unit, P_hover,
         S, AR, chord, CL, CD0, CDi, LD, D_cruise:W/LD, P_cruise, E_Wh, Epack_req_Wh, Epack_Wh, m_batt,
         sigmaWing, m_wing, S_tail, m_tail, m_booms, m_lift, m_fixed, CdA_extra, TW,
         TW_motorOut: p.nLift>4 ? TW*(p.nLift-2)/p.nLift : 0,
         I_hover:P_hover/p.Vpack, I_cruise:P_cruise/p.Vpack,
         P_hover_per_motor: P_hover/p.nLift,
         endurance_ok: Epack_Wh*(1-p.reserve)*p.etaBatt >= E_Wh - 1e-9,
         t_cruise_avail_min: Math.max(0,(Epack_Wh*(1-p.reserve)*p.etaBatt*3600 - P_hover*(p.tHover+p.tTrans))/P_cruise/60),
         diskLoading:Tunit/A, wingLoading:W/S};
    if(Math.abs(m_new-m)<1e-4){ m=m_new; break; }
    m = m + 0.6*(m_new-m);
  }
  r.iter = it+1; r.converged = it<299;
  return r;
}

const api = {G, size, calibFMeta, interpFMeta};
if(typeof module!=='undefined' && module.exports) module.exports = api; else root.VTOLModel = api;
})(this);
