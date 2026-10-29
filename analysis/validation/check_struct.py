"""Independent structural, thermal and tolerance checks for the C0 lift + cruise VTOL audit.

Audit agent (structures / thermal / manufacturing), 2026-10-29. numpy only. Runs in a few seconds.
Reads (never writes) the repo's own inputs and outputs, recomputes every number from first principles,
and compares with the SOLIDWORKS / repo values. Writes analysis/validation/checks_struct.json.

Usage:  python analysis/validation/check_struct.py

Every check is keyed by the claim id used in analysis/validation/claims_struct.json (STR-xx, THM-xx, MFG-xx).
Estimates are marked EST in the 'notes'. Unknowns are None (shown as "—" in the claims file).

External property sources (checked 2026-10-29):
  6061-T6: E 69 GPa (all tempers), yield min 240 MPa / typical 270 MPa, fatigue 97 MPa @ 5e8 RR Moore,
           density 2.70 g/cm3 -- https://en.wikipedia.org/wiki/6061_aluminium_alloy (cites Aluminum Standards
           and Data 2006 SI, ASM Handbook Vol. 2, ASM/MatWeb data sheet). asm.matweb.com refused the connection
           and matweb.com returned 403 on 2026-10-29, so the handbook pages themselves were not opened.
  A2-70 stainless: M3 min tensile load 3522 N, min yield load 2264 N; M5 9928 N / 6382 N -- Fastenal
           "Torque Values for A2-70 or A4-70 Metric Stainless Steel Fasteners", Feb 2016,
           https://crafter.fastenal.com/static-assets/pdfs/technical-resources/Torque-Tension-Relationship-for-Metric-Stainless-Steel-Fasteners-A2-and-A4-70-Feb-2016.pdf
  Bolt shear = 0.6 x tensile (EST, common distortion-energy rule; not from a cited table).
"""
import json, math, os, time
import numpy as np

T0 = time.time()
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
J = lambda *p: os.path.join(ROOT, *p)
G = 9.81

# ------------------------------------------------------------------ inputs
P = {}
for line in open(J('cad', 'params.txt'), encoding='utf-8'):
    line = line.strip()
    if not line or line.startswith(('comp=', 'xcomp=', 'fast_', 'sched_', 'foil=')) or '=' not in line: continue
    k, v = line.split('=', 1)
    try: P[k] = float(v)
    except ValueError: P[k] = v
COMP = [l.strip()[5:].split('|') for l in open(J('cad', 'params.txt'), encoding='utf-8') if l.startswith('comp=')]
RES = json.load(open(J('analysis', 'results.json'), encoding='utf-8'))
C0 = RES['concepts']['C0']; ST = C0['struct']; SZ = C0['sized']; BASE = RES['base']; CG = C0['cg']
SIM = {}
for f in (J('cad', 'sim', 'results.txt'), J('cad', 'sim', 'thermal', 'results.txt')):
    for line in open(f, encoding='utf-8'):
        if line.startswith('#') or '=' not in line: continue
        k, v = line.split('=', 1); SIM[k] = float(v.split('|')[0])
TH_IN = json.load(open(J('analysis', 'thermal', 'thermal_inputs.json'), encoding='utf-8'))
TH_RES = json.load(open(J('analysis', 'thermal', 'thermal_results.json'), encoding='utf-8'))
HW = json.load(open(J('cad', 'hardware.json'), encoding='utf-8'))

# material (external, cited above); repo uses the SOLIDWORKS library typical yield 275 MPa
E_AL = 69e9; SY_MIN = 240e6; SY_TYP = 270e6; SY_REPO = P['matSig']; RHO_AL = 2700.0

out = {'generated': time.strftime('%Y-%m-%d %H:%M'), 'script': 'analysis/validation/check_struct.py',
       'material': {'E_Pa': E_AL, 'yield_min_Pa': SY_MIN, 'yield_typ_Pa': SY_TYP, 'yield_repo_Pa': SY_REPO,
                    'src': 'https://en.wikipedia.org/wiki/6061_aluminium_alloy (checked 2026-10-29)'},
       'checks': {}}
def put(cid, **kw): out['checks'][cid] = kw
def pct(a, b): return None if (a is None or b in (None, 0)) else round(100.0 * (a - b) / b, 2)

def tube_I(D, d): return math.pi / 64 * (D ** 4 - d ** 4)
def tube_A(D, d): return math.pi / 4 * (D ** 2 - d ** 2)

# ------------------------------------------------------------------ STR-01..05 boom arm
L = P['feaBoomL']; Pt = P['feaTipForce']; Do, Di = P['boomOD'], P['boomID']
Ib = tube_I(Do, Di); c_b = Do / 2; EIb = E_AL * Ib
sig_root_clamp = Pt * L * c_b / Ib                      # load at clamp-to-motor distance (repo hand)
# Sim.cs places the load on the top face of a tip block of radius rBlk ending at L: load centroid L - rBlk
rBlk = math.sqrt(P['feaTipMass'] / (P['matRho'] * math.pi * (Do / 2 + 0.05)))
a_load = L - rBlk
sig_root_fea_geom = Pt * a_load * c_b / Ib
defl_tip_repo = Pt * L ** 3 / (3 * EIb)
defl_at_load = Pt * a_load ** 3 / (3 * EIb)
defl_tip_fea_geom = Pt * a_load ** 2 * (3 * L - a_load) / (6 * EIb)   # deflection at the free end, load at a
put('STR-01', what='Boom root bending stress, cantilever, tip thrust',
    equations=['I = pi/64 (D^4 - d^4)', 'sigma = P L c / I'],
    inputs={'L_m': L, 'P_N': Pt, 'D_m': Do, 'd_m': Di, 'I_mm4': Ib * 1e12, 'a_load_m (Sim.cs block centroid)': a_load},
    hand_sigma_MPa=sig_root_clamp / 1e6, hand_sigma_FEAgeom_MPa=sig_root_fea_geom / 1e6,
    repo_hand_MPa=SIM['boom_hand_sigma'], fea_coarse_MPa=SIM['boom_vm_max'], fea_fine_MPa=SIM['boom_vm_max_fine'],
    delta_fine_vs_hand_pct=pct(SIM['boom_vm_max_fine'], sig_root_clamp / 1e6),
    RF_yield_min=SY_MIN / (sig_root_clamp), RF_yield_repo=SY_REPO / (SIM['boom_vm_max_fine'] * 1e6),
    fatigue_ratio=sig_root_clamp / 97e6)

# FEA field slices (independent re-extraction of the SOLIDWORKS nodal von Mises, cad/sim/fields/boom.json)
def field_slices(path, stations, half_w, Mfun, cfun, Ifun, r_min_fun):
    f = json.load(open(path, encoding='utf-8'))
    n = np.array(f['nodes'], float).reshape(-1, 3)
    vm = np.array([np.nan if v is None else v for v in f['fields']['von_MPa']], float)
    ax = int(np.argmax(n.max(0) - n.min(0)))                 # beam axis = longest extent
    others = [i for i in range(3) if i != ax]
    r = np.hypot(n[:, others[0]], n[:, others[1]])
    res = []
    for s in stations:
        m = (np.abs(n[:, ax] - s) < half_w) & (r > r_min_fun(s)) & np.isfinite(vm)
        fe = float(np.nanmax(vm[m])) if m.any() else None
        hand = Mfun(s) * cfun(s) / Ifun(s) / 1e6
        res.append({'station_m': s, 'n_nodes': int(m.sum()), 'fea_max_vm_MPa': None if fe is None else round(fe, 2),
                    'hand_MPa': round(hand, 2), 'delta_pct': pct(fe, hand)})
    return res, int(len(n))

boom_sl, boom_nodes = field_slices(J('cad', 'sim', 'fields', 'boom.json'), [0.05, 0.10, 0.20, 0.30], 0.003,
                                   lambda x: Pt * (a_load - x), lambda x: c_b, lambda x: Ib, lambda x: 0.98 * c_b)
dl = [s['delta_pct'] for s in boom_sl if s['delta_pct'] is not None]
put('STR-02', what='Boom FEA nodal von Mises vs beam theory along the arm (fine mesh field export) + mesh convergence',
    equations=['sigma(x) = P (a - x) c / I, a = L - rBlk (Sim.cs tip block)'],
    slices=boom_sl, field_nodes=boom_nodes, mean_abs_delta_pct=float(np.mean(np.abs(dl))) if dl else None,
    peak_coarse_MPa=SIM['boom_vm_max'], peak_fine_MPa=SIM['boom_vm_max_fine'],
    peak_change_coarse_to_fine_pct=pct(SIM['boom_vm_max_fine'], SIM['boom_vm_max']),
    elements={'coarse_3mm': 50583, 'fine_1.5mm': 253709, 'src': 'cad/sim/*.LOG (UTF-16)'},
    note='peak grows 9 % on mesh halving at the fixed root face: restraint singularity, not converged; nominal stress away from the root is the comparable quantity')
put('STR-03', what='Boom tip deflection',
    equations=['delta = P L^3 / (3 E I)', 'delta_tip (load at a) = P a^2 (3L - a) / (6 E I)'],
    hand_tip_load_at_L_mm=defl_tip_repo * 1e3, hand_tip_load_at_block_mm=defl_tip_fea_geom * 1e3,
    hand_at_load_mm=defl_at_load * 1e3, repo_hand_mm=SIM['boom_hand_defl'], fea_mm=SIM['boom_disp_max'],
    delta_fea_vs_FEAgeom_hand_pct=pct(SIM['boom_disp_max'], defl_tip_fea_geom * 1e3),
    note='FEA root is rigid (fixed face); real root is a printed PETG split clamp bonded to a foam hardpoint, so real deflection is larger (compliance —)')

# modal
m_beam = RHO_AL * tube_A(Do, Di) * L
k_b = 3 * EIb / L ** 3
def fn(mtip, a=L):
    k = 3 * EIb / a ** 3
    return math.sqrt(k / (mtip + 0.24 * m_beam)) / (2 * math.pi)
# lift-unit mass from the CAD roll-up (cad/verification.txt per-part masses)
ver = open(J('cad', 'verification.txt'), encoding='utf-8').read()
def vmass(name):
    for line in ver.splitlines():
        if line.startswith(name + ' ') or line.startswith(name + '|'):
            return float(line.split('|')[2]) / 1000.0
    return None
mm_up, mm_cap, m_motor, m_prop, m_plate = vmass('Motor_Mount_Upper'), vmass('Motor_Mount_Cap'), vmass('Lift_Motor'), vmass('Lift_Prop'), vmass('Prop_Plate')
m_f01, m_f02, m_ins = vmass('F01_M3x8_SHCS'), vmass('F02_M3x16_SHCS'), vmass('I01_M3_Insert')
m_esc_est = 0.025   # analysis/sizing.mjs X4110S mEsc 25 g (EST in repo)
m_unit_cad = mm_up + mm_cap + m_motor + m_prop + m_plate + 4 * m_f01 + 4 * m_f02 + 4 * m_ins + 2 * m_f02 + m_esc_est
f_repo_mass = fn(P['feaTipMass']); f_cad_mass = fn(m_unit_cad); f_feageom = fn(P['feaTipMass'], a_load)
rpm_max = 7100.0   # firmware/sitl/c0_physics.py lift_rpm_max EST (0.8 x KV 400 x 22.2 V)
rpm_hover = rpm_max * math.sqrt(SZ['Tunit_N'] / ST['Tmax'])
put('STR-04', what='Boom first bending mode, Euler-Bernoulli cantilever with tip mass (Rayleigh 0.24 m_beam)',
    equations=['f = 1/(2 pi) sqrt(3 E I / ((m_tip + 0.24 m_beam) L^3))'],
    m_beam_kg=m_beam, k_N_per_m=k_b, f_repo_tipmass_Hz=f_repo_mass, f_load_at_block_centroid_Hz=f_feageom,
    f_cad_tipmass_Hz=f_cad_mass, repo_hand_Hz=SIM['boom_hand_fn'], fea_Hz=SIM['boom_f1'],
    delta_fea_vs_hand_pct=pct(SIM['boom_f1'], f_repo_mass), delta_fea_vs_blockgeom_hand_pct=pct(SIM['boom_f1'], f_feageom),
    rotor_1P_hover_Hz_EST=rpm_hover / 60, rotor_2P_hover_Hz_EST=2 * rpm_hover / 60, rotor_1P_max_Hz_EST=rpm_max / 60,
    note='rigid root in both hand and FEA; clamp compliance lowers f1 further (—). rpm from firmware/sitl/c0_physics.py EST')
put('STR-05', what='Lift-unit (boom tip) mass: sizing/FEA value vs CAD part masses',
    sizing_mTip_kg=ST['mTip'], sizing_mount_kg=0.020,
    cad_parts_kg={'Motor_Mount_Upper': mm_up, 'Motor_Mount_Cap': mm_cap, 'Lift_Motor': m_motor, 'Lift_Prop': m_prop,
                  'Prop_Plate': m_plate, 'fasteners+inserts (4 F01, 6 F02, 4 I01)': 4 * m_f01 + 6 * m_f02 + 4 * m_ins,
                  'ESC (sizing EST)': m_esc_est},
    cad_unit_kg=m_unit_cad, delta_pct=pct(m_unit_cad, ST['mTip']),
    note='CAD mount alone is %.0f g vs the 20 g mMount allowance (analysis/sizing.mjs X4110S)' % ((mm_up + mm_cap) * 1000))

# ------------------------------------------------------------------ STR-06..09 wing root moment, joiner, spar
mtow_p = P['mtow']; mtow_r = SZ['m']; n_ult = ST['nUlt']; semi = BASE['span'] / 2
def Mroot(m, dist):
    Lh = m * G * n_ult / 2
    if dist == 'elliptic': return Lh * 4 * semi / (3 * math.pi)
    if dist == 'uniform': return Lh * semi / 2
    if dist == 'schrenk': return 0.5 * (Lh * 4 * semi / (3 * math.pi) + Lh * semi / 2)
M_e, M_u, M_s = Mroot(mtow_p, 'elliptic'), Mroot(mtow_p, 'uniform'), Mroot(mtow_p, 'schrenk')
put('STR-06', what='Wing root bending moment at ultimate (n = 4.5): elliptic vs uniform vs Schrenk',
    equations=['L_half = m g n / 2', 'M_ell = L_half 4 b_s / (3 pi)', 'M_uni = L_half b_s / 2', 'M_schrenk = (M_ell + M_uni)/2'],
    inputs={'mtow_params_kg': mtow_p, 'mtow_results_kg': mtow_r, 'n_ult': n_ult, 'n_limit': ST['nLimit'], 'FS': ST['FS'], 'semispan_m': semi},
    M_elliptic_Nm=M_e, M_uniform_Nm=M_u, M_schrenk_Nm=M_s, repo_params_Nm=P['feaRootMomentTarget'], repo_results_Nm=ST['Mroot'],
    delta_elliptic_vs_repo_pct=pct(M_e, P['feaRootMomentTarget']), schrenk_vs_elliptic_pct=pct(M_s, M_e),
    note='no inertia relief from wing/boom/lift-unit mass (conservative); rectangular planform -> Schrenk is the usual first estimate')

Ij = tube_I(P['joinOD'], P['joinID']); cj = P['joinOD'] / 2
Ij_fea = tube_I(P['sparID'], P['joinID']); cj_fea = P['sparID'] / 2
sigJ = {k: M * cj / Ij for k, M in (('elliptic', M_e), ('schrenk', M_s), ('uniform', M_u))}
put('STR-07', what='Joiner (0.875 x 0.058 in) bending stress at the centreline and reserve factor',
    equations=['sigma = M c / I', 'RF = sigma_y / sigma'], I_true_mm4=Ij * 1e12,
    sigma_MPa={k: v / 1e6 for k, v in sigJ.items()}, repo_hand_MPa=SIM['spar_hand_sigJ'],
    delta_elliptic_vs_repo_pct=pct(sigJ['elliptic'] / 1e6, SIM['spar_hand_sigJ']),
    RF={'elliptic_repo275': SY_REPO / sigJ['elliptic'], 'elliptic_min240': SY_MIN / sigJ['elliptic'],
        'schrenk_min240': SY_MIN / sigJ['schrenk'], 'uniform_min240': SY_MIN / sigJ['uniform']},
    repo_RF=ST['MS_J'])

# spar FEA: model-consistent hand and field slices. FEA geometry: joiner OD = spar ID 0..jL, spar fusR..fusR+sparLen
jL = P['joinLen'] / 2; z0 = P['fusR']; z1 = P['fusR'] + P['sparLen']; w = P['feaWingForce'] / P['sparLen']
def M_sp(z):  # bending moment from uniform w on [z0, z1], fixed at z = 0
    a = max(z, z0); return w * (z1 - a) ** 2 / 2 + (w * (z1 - z0) * (z0 - z) if z < z0 else 0.0) if z < z1 else 0.0
def I_sp(z):
    if z < z0: return Ij_fea
    if z < jL: return tube_I(P['sparOD'], P['joinID'])
    return tube_I(P['sparOD'], P['sparID'])
def c_sp(z): return cj_fea if z < z0 else P['sparOD'] / 2
sig_root_fea_hand = M_sp(0.0) * cj_fea / Ij_fea
spar_sl, spar_nodes = field_slices(J('cad', 'sim', 'fields', 'spar.json'), [0.03, 0.06, 0.20, 0.30, 0.50, 0.70], 0.003,
                                   M_sp, c_sp, I_sp, lambda z: 0.98 * c_sp(z))
# tip deflection by double integration of M/EI
zz = np.linspace(0, z1, 8001); kap = np.array([M_sp(z) / (E_AL * I_sp(z)) for z in zz])
th = np.concatenate([[0], np.cumsum(0.5 * (kap[1:] + kap[:-1]) * np.diff(zz))])
dv = np.concatenate([[0], np.cumsum(0.5 * (th[1:] + th[:-1]) * np.diff(zz))])
put('STR-08', what='Spar+joiner FEA vs beam theory on the FEA geometry (joiner OD = socket ID, bonded)',
    equations=['M(z) from uniform w on [fusR, fusR + sparLen]', 'sigma = M c / I (section per zone)'],
    M_centreline_Nm=M_sp(0.0), hand_root_FEAgeom_MPa=sig_root_fea_hand / 1e6, I_fea_joiner_mm4=Ij_fea * 1e12,
    fea_coarse_MPa=SIM['spar_vm_max'], fea_fine_MPa=SIM['spar_vm_max_fine'],
    delta_coarse_pct=pct(SIM['spar_vm_max'], sig_root_fea_hand / 1e6), delta_fine_pct=pct(SIM['spar_vm_max_fine'], sig_root_fea_hand / 1e6),
    slices=spar_sl, field_nodes=spar_nodes,
    stiffness_ratio_fea_over_true_joiner=Ij_fea / Ij,
    elements={'coarse_3mm': 55584, 'fine_2mm': 147172})
put('STR-09', what='Spar tip deflection, FEA geometry, numerical double integration of M/EI',
    hand_tip_mm=float(dv[-1] * 1e3), fea_tip_mm=SIM['spar_tip_disp'], delta_pct=pct(SIM['spar_tip_disp'], float(dv[-1] * 1e3)),
    note='FEA joiner is 9.7 % stiffer than the real joiner; real joiner + 0.23 mm slip-fit clearance + foam add rotation (—)')

# ------------------------------------------------------------------ STR-10 boom-to-wing clamp loads
xs = {c[0]: float(c[1]) for c in COMP if c[0] in ('Motor_Mount_Upper', 'Boom_Clamp_F_Upper', 'Boom_Clamp_R_Upper', 'Gear_Clamp_Upper')}
xF_motor = max(float(c[1]) for c in COMP if c[0] == 'Motor_Mount_Upper')
xR_motor = min(float(c[1]) for c in COMP if c[0] == 'Motor_Mount_Upper')
xFc = float([c for c in COMP if c[0] == 'Boom_Clamp_F_Upper'][0][1]); xRc = float([c for c in COMP if c[0] == 'Boom_Clamp_R_Upper'][0][1])
arm_f = xF_motor - xFc; sp = xFc - xRc
R_rear_single = Pt * arm_f / sp; R_front_single = Pt + R_rear_single
put('STR-10', what='Boom clamp reactions into the wing hardpoints, single front motor at Tmax (differential thrust)',
    equations=['R_rear = T a / s', 'R_front = T + R_rear'],
    inputs={'x_front_motor': xF_motor, 'x_front_clamp': xFc, 'x_rear_clamp': xRc, 'arm_m': arm_f, 'spacing_m': sp, 'T_N': Pt},
    rear_clamp_tension_N=R_rear_single, per_screw_N=R_rear_single / 2, front_clamp_N=R_front_single,
    repo_spec_value_N=114.0, delta_pct=pct(R_rear_single, 114.0),
    rear_plate_bond_area_mm2=60 * 46, rear_plate_bond_stress_kPa=R_rear_single / (60 * 46e-6) / 1e3,
    m3_bolt_tension_util=R_rear_single / 2 / 2264.0,
    insert_pullout_N=None, xps_bond_strength_kPa=None,
    note='hardware-spec J05 uses superseded coordinates (0.3709 / -0.0716 / -0.1909); insert pull-out and XPS bond strength: —')

# ------------------------------------------------------------------ STR-11 landing
h_drop = 0.30; v_imp = math.sqrt(2 * G * h_drop)
xg_f = float([c for c in COMP if c[0] == 'Gear_Clamp_Upper'][0][1]); xg_r = min(float(c[1]) for c in COMP if c[0] == 'Gear_Clamp_Upper')
xcg = CG['target']; frac_front = (xcg - xg_r) / (xg_f - xg_r)
land = {}
for n in (8.0, 16.0, 32.0):
    F_leg = mtow_p * G * n * frac_front / 2           # per front leg
    M_clamp = F_leg * (xg_f - xFc) - m_unit_cad * G * n * arm_f   # gear reaction up minus lift-unit inertia down
    s = M_clamp * c_b / Ib
    land[str(int(n))] = {'F_leg_N': F_leg, 'M_front_clamp_Nm': M_clamp, 'sigma_boom_MPa': s / 1e6, 'RF_min240': SY_MIN / s,
                         'leg_axial_bearing_on_socket_MPa': F_leg / tube_A(P['legOD'], P['legID']) / 1e6}
put('STR-11', what='Hard landing: front gear load into the front boom arm (static-equivalent n g)',
    equations=['v = sqrt(2 g h)', 'n = 2(1 + h/s) (linear spring, repo)', 'F_leg = m g n f_front / 2',
               'M = F_leg (x_gear - x_clamp) - m_unit g n (x_motor - x_clamp)'],
    v_impact_mps=v_imp, front_fraction=frac_front, cases=land, repo_strokes=ST['strokes'],
    note='no FEA or test of this case in the repo; legs assumed vertical (axial); lift-unit mass from CAD (STR-05)')

# ------------------------------------------------------------------ STR-12 boom splice J04
m_tail_side = 0.5 * C0['sized']['m_tail'] + vmass('Boom_Rear_Stub') + vmass('Tail_Clamp_Cap') + vmass('Tail_Clamp_Upper') + vmass('Fin_Shoe') + 1.5 * vmass('Servo')
x_tail = -0.85; xsplice = xR_motor
M_splice = m_tail_side * G * n_ult * (xsplice - x_tail)
F_bolt = M_splice / 0.036
put('STR-12', what='Boom splice (J04): 2 x M3 cross-bolts at x +-18 mm carrying vertical bending as a shear couple',
    inputs={'m_tail_side_kg (EST roll-up)': m_tail_side, 'arm_m (EST)': xsplice - x_tail, 'n': n_ult, 'bolt_pitch_m': 0.036},
    M_splice_Nm=M_splice, F_per_bolt_N=F_bolt, bolt_double_shear_MPa=F_bolt / (2 * 5.03), bolt_shear_util=F_bolt / (2 * 0.6 * 3522),
    tube_bearing_MPa=F_bolt / (2 * 0.003 * (Do - Di) / 2 * 1e6), free_play_rotation_deg_WC=math.degrees((0.4 + 0.4) / 36.0),
    tail_aero_load_N=None,
    note='tail aerodynamic load: — (not in repo); clamp friction of the 70 mm motor mount around the splice also carries load (—)')

# ------------------------------------------------------------------ STR-13 wing bolt J10
c = P['chord']; arm_bolt = (0.70 - 0.30) * c
L_half = mtow_p * G * n_ult / 2
T_panel = L_half * (0.30 - 0.25) * c     # EST: lift at the quarter chord, joiner at 30 % c; Cm0 ignored (—)
F_b = T_panel / arm_bolt
put('STR-13', what='Wing retention bolt J10 (M5 A2-70) reacting panel torsion about the round slip-fit joiner',
    equations=['T = L_half (x_joiner - x_ac) c', 'F = T / ((0.70 - 0.30) c)'],
    T_panel_Nm=T_panel, F_bolt_N=F_b, tau_bolt_MPa=F_b / 14.2, shear_util=F_b / (0.6 * 9928),
    bearing_on_6p4mm_PETG_tongue_MPa=F_b / (5.0 * 6.4), PETG_strength_MPa=None, Cm0=None,
    preload_N_repo=1250.0, preload_bearing_MPa_repo=27.0,
    note='EST aerodynamic centre at 25 % c; NACA 2415 Cm0 not read from the repo (—); PETG strength not in the repo (—)')

# ------------------------------------------------------------------ STR-14 motor reaction torque and clamp slip
P_motor_max = 615.0   # firmware/sitl/c0_physics.py: maker motor max 615 W
Q_max = 0.8 * P_motor_max / (rpm_max * 2 * math.pi / 60)
F_pre = {'K0.16_lub': 0.5 / (0.16 * 0.003), 'K0.35_dry': 0.5 / (0.35 * 0.003)}
T_slip = {k: 0.3 * 4 * v * c_b for k, v in F_pre.items()}
put('STR-14', what='Lift-motor reaction torque on the boom and clamp friction capacity',
    equations=['Q = eta P / omega', 'sigma_lat = Q c / I', 'F = T/(K d)', 'T_slip = mu n F r'],
    Q_max_Nm_EST=Q_max, sigma_lateral_MPa=Q_max * c_b / Ib / 1e6, preload_N=F_pre, slip_torque_Nm=T_slip,
    repo_slip_Nm=16.0, M7_test_Nm=2 * G * 0.25,
    note='mu 0.3 EST (repo); bolts into brass inserts in PETG/PA6-CF are not lubricated -> K 0.35 (Fastenal dry) halves preload; insert torque-out —')

# ------------------------------------------------------------------ thermal
AIR = dict(nu=1.65e-5, k=0.0268, Pr=0.706)   # analysis/thermal/thermal_inputs.py (Incropera A.4 at ~308 K)
def hilpert(V, D):
    Re = V * D / AIR['nu']
    C, m = (0.989, 0.330) if Re < 4 else (0.911, 0.385) if Re < 40 else (0.683, 0.466) if Re < 4000 else (0.193, 0.618) if Re < 40000 else (0.027, 0.805)
    return C * Re ** m * AIR['Pr'] ** (1 / 3) * AIR['k'] / D, Re
rho_isa = BASE['rho']; rho_35 = 101325 / (287.05 * 308.15)
vi = math.sqrt(SZ['Tunit_N'] / (2 * rho_isa * SZ['A'])); vi35 = math.sqrt(SZ['Tunit_N'] / (2 * rho_35 * SZ['A']))
h_hov, Re_h = hilpert(vi, P['motorD']); h_hov35, _ = hilpert(vi35, P['motorD']); h_cru, Re_c = hilpert(BASE['Vc'], P['motorD'])
A_m = math.pi * P['motorD'] * P['motorH'] + 2 * math.pi * P['motorD'] ** 2 / 4
Tamb = 35.0
Tss_simcs = Tamb + P['thermQ'] / (P['thermH'] * A_m)
put('THM-01', what='Motor-only steady temperature, Sim.cs inputs (Q 45.8 W, h 50) and correlation h',
    equations=['T = T_amb + Q / (h A)', 'A = pi D H + 2 pi D^2/4'],
    A_m2=A_m, T_simcs_hand_C=Tss_simcs, fea_simcs_C=SIM['motor_T_steady'], delta_pct_on_rise=pct(SIM['motor_T_steady'] - Tamb, Tss_simcs - Tamb),
    T_corr_hand_C=Tamb + TH_IN['loads']['lift_motor_W'] / (h_hov * A_m), fea_corr_C=SIM['motor_only_T_steady'])
put('THM-02', what='Film coefficients (Hilpert cylinder) in hover wash and 18 m/s cruise',
    equations=['v_i = sqrt(T / (2 rho A))', 'Re = V D / nu', 'Nu = C Re^m Pr^(1/3)', 'h = Nu k / D'],
    v_i_mps=vi, v_i_35C_mps=vi35, rho_used=rho_isa, rho_35C=rho_35, Re_hover=Re_h, h_motor_hover=h_hov, h_motor_hover_35C=h_hov35,
    repo_h_motor_hover=TH_IN['h']['motor_hover'], h_motor_cruise=h_cru, repo_h_motor_cruise=TH_IN['h']['motor_cruise'],
    delta_hover_pct=pct(h_hov, TH_IN['h']['motor_hover']))
R_wind = 0.112; I_hov = SZ['P_hover_per_motor'] / 21.0
put('THM-03', what='Lift motor heat load: 20 % rule vs I^2 R',
    Q_rule_W=0.2 * SZ['P_hover_per_motor'], I_hover_A=I_hov, Q_I2R_W=I_hov ** 2 * R_wind,
    Q_no_load_W=None, repo_Q_W=TH_IN['loads']['lift_motor_W'],
    note='112 mOhm winding R is a reseller value quoted in docs/research/thermal.md; no-load current I0 not in the repo (—)')

def lumped(phases, C, A, T0=Tamb):
    T = T0; hist = []
    for name, dt, Q, h in phases:
        tau = C / (h * A); Tinf = Tamb + Q / (h * A)
        T = Tinf + (T - Tinf) * math.exp(-dt / tau); hist.append((name, round(T, 2)))
    return T, hist
L_ = TH_IN['loads']; H_ = TH_IN['h']
C_m = P['motorMass'] * TH_IN['materials']['motor']['cp']
T60, _ = lumped([('hover', 60, L_['lift_motor_W'], H_['motor_hover'])], C_m, A_m)
T90, _ = lumped([('hover', 90, L_['lift_motor_W'], H_['motor_hover'])], C_m, A_m)
Tmis, hist = lumped([('hover', 60, L_['lift_motor_W'], H_['motor_hover']), ('trans', 20, L_['lift_motor_trans_W'], H_['motor_hover']),
                     ('cruise', 600, 0.0, H_['motor_cruise']), ('trans', 20, L_['lift_motor_trans_W'], H_['motor_hover']),
                     ('hover', 60, L_['lift_motor_W'], H_['motor_hover'])], C_m, A_m)
T90_simcs, _ = lumped([('hover', 90, P['thermQ'], P['thermH'])], C_m, A_m)
R = TH_RES['results']
put('THM-04', what='Lift motor transient (lumped capacitance) vs SOLIDWORKS lift-unit transient',
    equations=['T(t) = T_inf + (T0 - T_inf) exp(-t/tau)', 'tau = m c_p / (h A)'],
    C_J_per_K=C_m, tau_hover_s=C_m / (H_['motor_hover'] * A_m),
    hand_60s_C=T60, fea_60s_C=R['lift_hover60_Motor'], hand_90s_C=T90, fea_90s_C=R['lift_hover90_Motor'],
    hand_mission_end_C=Tmis, fea_mission_end_C=R['lift_mission_end_Motor'], fea_mission_max_C=R['lift_mission_max_Motor'],
    mission_history=hist, simcs_90s_hand_C=T90_simcs, simcs_90s_fea_C=SIM['val_motor_T90'],
    delta_60_pct_on_rise=pct(R['lift_hover60_Motor'] - Tamb, T60 - Tamb), delta_mission_pct_on_rise=pct(R['lift_mission_end_Motor'] - Tamb, Tmis - Tamb),
    limit_C=80.0, limit_src='docs/test/TEST-PLAN.md abort table (EST, maker gives none)')
e = TH_IN['esc']; A_esc = 2 * (e['len_m'] * e['width_m'] + e['len_m'] * e['height_m'] + e['width_m'] * e['height_m']) - e['len_m'] * e['width_m']
C_esc = TH_IN['materials']['esc']['rho'] * TH_IN['materials']['esc']['cp'] * e['len_m'] * e['width_m'] * e['height_m']
Te60, _ = lumped([('hover', 60, L_['lift_esc_W'], H_['esc_hover'])], C_esc, A_esc)
Tess = Tamb + L_['lift_esc_W'] / (H_['esc_hover'] * A_esc)
put('THM-05', what='Lift ESC (boom underside) lumped check', A_m2=A_esc, C_J_per_K=C_esc,
    hand_60s_C=Te60, fea_60s_C=R['lift_hover60_ESC'], hand_steady_C=Tess, fea_steady_C=R['lift_steady_ESC'],
    delta_60_pct_on_rise=pct(R['lift_hover60_ESC'] - Tamb, Te60 - Tamb), limit_C=70.0)
Qb = L_['batt_hover_W'] * 120 + L_['batt_trans_W'] * 40 + L_['batt_cruise_W'] * 600
mcb = SZ['m_batt'] * TH_IN['materials']['lipo']['cp']
put('THM-06', what='Battery pack, adiabatic I^2 R heating over the mission',
    equations=['Q = I^2 R_pack', 'dT = sum(Q t) / (m c_p)'],
    I_A={'hover': SZ['I_hover_loaded'], 'trans': SZ['I_trans'], 'cruise': SZ['I_cruise']}, R_pack_ohm=L_['R_pack_ohm'],
    Q_hover_W=SZ['I_hover_loaded'] ** 2 * L_['R_pack_ohm'], E_J=Qb, mcp_J_per_K=mcb, hand_end_C=Tamb + Qb / mcb,
    fea_end_C=R['pod_mission_end_Battery'], delta_pct_on_rise=pct(R['pod_mission_end_Battery'] - Tamb, Qb / mcb), limit_C=60.0)
fc = TH_IN['fc']; A_fc = 2 * (fc['len_m'] * fc['width_m'] + fc['len_m'] * fc['height_m'] + fc['width_m'] * fc['height_m'])
C_fc = vmass('Flight_Controller') * 900.0   # cp 900 J/kgK EST (FR4/Cu/Al mix), not in the repo
Tfc, _ = lumped([('mission', 760, L_['fc_W'], H_['bay_natural'])], C_fc, A_fc)
put('THM-07', what='Flight controller in the closed pod bay', A_m2=A_fc, C_J_per_K_EST=C_fc,
    hand_end_C=Tfc, hand_steady_C=Tamb + L_['fc_W'] / (H_['bay_natural'] * A_fc), fea_max_C=R['pod_mission_max_FC'],
    delta_pct_on_rise=pct(R['pod_mission_max_FC'] - Tamb, Tfc - Tamb), limit_C=None,
    note='no FC temperature limit in the repo (—); cp 900 J/kgK EST')
Tpu, _ = lumped([('cruise', 600, L_['pusher_motor_W'], H_['pusher_motor_cruise'])], C_m, A_m)
put('THM-08', what='Pusher motor after 600 s cruise (fully exposed lumped can = lower bound; FEA has the PA6-CF cup)',
    hand_exposed_C=Tpu, fea_endcruise_C=R['pusher_endcruise_Motor'], fea_steady_C=R['pusher_steady_Motor'],
    delta_pct_on_rise=pct(R['pusher_endcruise_Motor'] - Tamb, Tpu - Tamb), limit_C=80.0,
    mount_steady_bound_C=R['lift_steady_Mount'], pa6cf_HDT_C=173.0, pa6cf_HDT_stress_MPa=1.8, motor_floor_bearing_MPa_repo=41.0)

# ------------------------------------------------------------------ tolerance stacks (MFG)
def stack(nom, tols, signs):
    wc = sum(abs(t) for t in tols); rss = math.sqrt(sum(t * t for t in tols))
    return {'nominal': nom, 'worst_case': [nom - wc, nom + wc], 'rss': [nom - rss, nom + rss], 'wc_half': wc, 'rss_half': rss}
in_ = 0.0254 * 1000
tOD = 0.004 * in_; tW = 0.002 * in_
FT01 = stack(P['sparID'] * 1000 - P['joinOD'] * 1000, [tOD, 2 * tW, tOD], None)
FT01_repo = stack(P['sparID'] * 1000 - P['joinOD'] * 1000, [0.203, 0.102], None)
FT06 = stack(P['joinBoreD'] * 1000 - P['joinOD'] * 1000, [0.2, tOD], None)
FT02 = stack(25.6 - 25.4, [0.2, tOD], None)
FT04 = stack(23.622 - 23.2, [0.203, 0.2], None)
# socket coaxiality: spar socket in a 26.0 +-0.5 channel, tube 25.4 +-0.102, bonded over 800 mm
c_ch_max = (26.0 + 0.5) - (25.4 - 0.102); c_ch_rss = (26.0 - 25.4) + math.sqrt(0.5 ** 2 + 0.102 ** 2)
theta_wc = c_ch_max / 800.0; theta_rss = c_ch_rss / 800.0
lat_wc = theta_wc * 300.0; lat_rss = theta_rss * 300.0
# J10 screw protrusion past the nylock: spot 2.0, screw 20, pillar 26.0, pocket 9.6, nut 5.0
prot_nom = (2.0 + 20.0) - (P['pillarH'] * 1000 - P['pillarNutDepth'] * 1000 + 5.0)
J10 = stack(prot_nom, [0.5, 0.4, 0.5, 0.5], None)
# wingtip play from FT01 clearance over 300 mm engagement, at 1.12 m panel
tip_play = lambda cl: cl / 300.0 * P['panelLen'] * 1000
put('MFG-STACKS', FT01_alt_RSS_decomposed=FT01, FT01_repo_band=FT01_repo, FT06=FT06, FT02=FT02, FT04=FT04,
    FT04_rotation_deg={'nominal': math.degrees(FT04['nominal'] / 40), 'wc': math.degrees(FT04['worst_case'][1] / 40)},
    socket_coax={'channel_clear_max_mm': c_ch_max, 'theta_wc_mrad': theta_wc * 1e3, 'theta_rss_mrad': theta_rss * 1e3,
                 'lateral_at_300_wc_mm': lat_wc, 'lateral_at_300_rss_mm': lat_rss, 'nominal_joiner_clearance_mm': FT01['nominal']},
    J10_protrusion=J10, wingtip_play_mm={'nominal': tip_play(FT01['nominal']), 'wc': tip_play(FT01_repo['worst_case'][1])},
    note='tube OD +-0.004 in, wall +-0.002 in (hardware.json FT01 source, EST for 0.875/0.058); screw length tol +-0.4 EST; printed +-0.5 (hardware.json general rule)')

# ------------------------------------------------------------------ MFG-01 params / results drift
put('MFG-01', what='cad/params.txt vs current analysis/results.json',
    results_generated=RES['generated'], pairs={
        'chord_m': [P['chord'], SZ['chord']], 'mtow_kg': [P['mtow'], SZ['m']], 'feaBoomL_m': [P['feaBoomL'], ST['Lb']],
        'feaRootMomentTarget_Nm': [P['feaRootMomentTarget'], ST['Mroot']], 'thermQ_W': [P['thermQ'], 0.2 * SZ['P_hover_per_motor']]},
    deltas_pct={'chord': pct(P['chord'], SZ['chord']), 'mtow': pct(P['mtow'], SZ['m']), 'Lb': pct(P['feaBoomL'], ST['Lb']),
                'Mroot': pct(P['feaRootMomentTarget'], ST['Mroot'])})
# MFG interference interpretation (screw length past the hole = volume / screw section)
put('MFG-INTF', F06_into_spar_collar_mm=7.01 / (math.pi * 1.5 ** 2), F11_through_horn_mm=8.41 / (math.pi * 1.0 ** 2),
    F07_into_pod_mm=4.75 / (math.pi * 1.5 ** 2),
    note='interference volume / nominal screw cross-section (calc) from cad/verification.txt')
put('MFG-MASS', cad_total_kg=6.357, sizing_params_kg=P['mtow'], sizing_results_kg=SZ['m'],
    mount_cad_g=(mm_up + mm_cap) * 1000, mount_sizing_g=20.0, pa6cf_density_cad=1230, pa6cf_density_TDS=1170)

out['runtime_s'] = round(time.time() - T0, 2)
json.dump(out, open(J('analysis', 'validation', 'checks_struct.json'), 'w', encoding='utf-8'), indent=1, default=float)
for k, v in out['checks'].items():
    keys = [x for x in v if any(s in x for s in ('delta', 'hand', 'fea', 'RF', 'sigma'))][:6]
    print(k, {x: (round(v[x], 3) if isinstance(v[x], float) else v[x]) for x in keys if not isinstance(v[x], (list, dict))})
print('wrote analysis/validation/checks_struct.json in %.1f s' % out['runtime_s'])
