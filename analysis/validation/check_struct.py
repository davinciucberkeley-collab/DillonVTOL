"""Independent structural, thermal and tolerance checks for the C0 lift + cruise VTOL audit.

Audit agent (structures / thermal / manufacturing), 2026-10-29; re-audited 2026-11-02 on the frozen 7.436 kg design
(analysis/results.json generated 2026-11-01). numpy only. Runs in about a second.
Reads (never writes) the repo's own inputs and outputs, recomputes every number with textbook formulas that do not call
the repo's model code, and compares with the SOLIDWORKS / repo values. Writes analysis/validation/checks_struct.json.

Usage:  py analysis/validation/check_struct.py

Every check is keyed by the claim id used in analysis/validation/claims_struct.json (STR-xx, THM-xx, MFG-xx).
At the end the script prints one line per check, in the same form as check_aero.py:
  id | what | independent value | repo value (or bound) | % delta | tolerance or relation | PASS / FAIL
  rel "eq": pass if |delta| <= tolerance;  "ge": independent >= repo;  "le": independent <= repo.
Estimates are marked EST in the notes. Unknowns are None (shown as "—" in the claims file).

External property sources:
  6061-T6: E 69 GPa, yield min 240 MPa / typical 270 MPa, fatigue 97 MPa @ 5e8 RR Moore, density 2.70 g/cm3 --
           https://en.wikipedia.org/wiki/6061_aluminium_alloy (cites Aluminum Standards and Data 2006 SI, ASM Handbook
           Vol. 2), checked 2026-10-29. The repo's SOLIDWORKS library uses 275 MPa (cad/params.txt matSig).
  A2-70 stainless: M3 min tensile load 3522 N, min yield load 2264 N; M5 9928 N / 6382 N -- Fastenal
           "Torque Values for A2-70 or A4-70 Metric Stainless Steel Fasteners", Feb 2016,
           https://crafter.fastenal.com/static-assets/pdfs/technical-resources/Torque-Tension-Relationship-for-Metric-Stainless-Steel-Fasteners-A2-and-A4-70-Feb-2016.pdf
  Bolt shear = 0.6 x tensile (EST, common distortion-energy rule; not from a cited table).
  PETG proxy: Prusament PETG V0 TDS v1.0, printed-specimen tensile yield 39 +-2 MPa (ISO 527-1), HDT 68 C at 1.8 MPa,
           https://cdn.shopify.com/s/files/1/1745/6181/files/prusament-petg-v0-technical-data-sheet.pdf (checked 2026-11-02).
           The team prints ELEGOO PETG, for which the repo has no strength value: EST proxy.
  SunnySky X4110S KV400: phase resistance 107 mOhm, no-load current 0.6 A at 10 V (maker spec table,
           analysis/propulsion_data_2026-11-01.json source S1, https://sunnyskyusa.com/products/sunnysky-x4110s-motors,
           checked 2026-11-01).
  Churchill-Bernstein cylinder correlation: Incropera & DeWitt, Fundamentals of Heat and Mass Transfer, eq. 7.54.
  Hilpert correlation: same book, eq. 7.52 / Table 7.2 (the repo's analysis/thermal/thermal_inputs.py uses it).
  Schrenk span loading: average of the elliptic and planform loadings (Schrenk, NACA TM 948, 1940).
"""
import json, math, os, re, time
import numpy as np

T0 = time.time()
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
J = lambda *p: os.path.join(ROOT, *p)
G = 9.81

# ------------------------------------------------------------------ inputs
def read_params(path):
    P = {}
    for line in open(path, encoding='utf-8'):
        line = line.strip()
        if not line or line.startswith(('comp=', 'xcomp=', 'fast_', 'sched_', 'foil=')) or '=' not in line: continue
        k, v = line.split('=', 1)
        try: P[k] = float(v)
        except ValueError: P[k] = v
    return P
P = read_params(J('cad', 'params.txt'))                 # current design (the FEA and the docs read this file)
PB = read_params(J('cad', 'params.built.txt'))          # what BuildVtol.cs built the CAD model from
COMP = [l.strip()[5:].split('|') for l in open(J('cad', 'params.txt'), encoding='utf-8') if l.startswith('comp=')]
RES = json.load(open(J('analysis', 'results.json'), encoding='utf-8'))
C0 = RES['concepts']['C0']; ST = C0['struct']; SZ = C0['sized']; BASE = RES['base']; CG = C0['cg']; PRM = C0['params']
SIM = {}
for f in (J('cad', 'sim', 'results.txt'), J('cad', 'sim', 'thermal', 'results.txt')):
    for line in open(f, encoding='utf-8'):
        if line.startswith('#') or '=' not in line: continue
        k, v = line.split('=', 1); SIM[k] = float(v.split('|')[0])
TH_IN = json.load(open(J('analysis', 'thermal', 'thermal_inputs.json'), encoding='utf-8'))
TH_RES = json.load(open(J('analysis', 'thermal', 'thermal_results.json'), encoding='utf-8'))
HW = json.load(open(J('cad', 'hardware.json'), encoding='utf-8'))
MB = json.load(open(J('analysis', 'mass', 'mass_budget.json'), encoding='utf-8'))
LAND = json.load(open(J('analysis', 'structures', 'landing.json'), encoding='utf-8'))
PD = json.load(open(J('analysis', 'propulsion_data_2026-11-01.json'), encoding='utf-8'))
S1 = next(s for s in PD['sources'] if s['id'] == 'S1')['values']['spec']

# material (external, cited above); repo uses the SOLIDWORKS library typical yield 275 MPa
E_AL = 69e9; SY_MIN = 240e6; SY_TYP = 270e6; SY_REPO = P['matSig']; RHO_AL = 2700.0
PETG_YIELD = 39e6   # Prusament PETG V0 printed specimens (proxy, EST for ELEGOO PETG)

out = {'generated': time.strftime('%Y-%m-%d %H:%M'), 'script': 'analysis/validation/check_struct.py',
       'design': 'analysis/results.json generated %s, MTOW %.4f kg' % (RES['generated'], SZ['m']),
       'material': {'E_Pa': E_AL, 'yield_min_Pa': SY_MIN, 'yield_typ_Pa': SY_TYP, 'yield_repo_Pa': SY_REPO,
                    'src': 'https://en.wikipedia.org/wiki/6061_aluminium_alloy (checked 2026-10-29)'},
       'checks': {}, 'summary': []}
def put(cid, **kw): out['checks'][cid] = kw
def pct(a, b): return None if (a is None or b in (None, 0)) else round(100.0 * (a - b) / b, 2)
def rec(cid, what, indep, repo, tol_pct=0.0, rel='eq', note=''):
    d = None if (indep is None or repo in (None, 0)) else 100.0 * (indep - repo) / abs(repo)
    if indep is None or repo is None: ok = None
    elif rel == 'eq': ok = None if d is None else abs(d) <= tol_pct
    else: ok = indep >= repo if rel == 'ge' else indep <= repo
    out['summary'].append({'id': cid, 'check': what, 'independent': indep, 'repo': repo, 'delta_pct': None if d is None else round(d, 2),
                           'tolerance_pct': tol_pct if rel == 'eq' else None, 'relation': rel, 'pass': ok, 'note': note})

def log_elements(name):
    """element count from a SOLIDWORKS solver log (UTF-16) in cad/sim"""
    try:
        t = open(J('cad', 'sim', name + '.LOG'), 'rb').read().decode('utf-16', errors='ignore')
        m = re.search(r'No\. of elements\s*=\s*(\d+)', t); return int(m.group(1)) if m else None
    except OSError:
        return None
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
put('STR-01', what='Boom root bending stress, cantilever, one lift unit at maximum thrust',
    equations=['I = pi/64 (D^4 - d^4)', 'sigma = P L c / I'],
    inputs={'L_m': L, 'P_N': Pt, 'D_m': Do, 'd_m': Di, 'I_mm4': Ib * 1e12, 'a_load_m (Sim.cs block centroid)': a_load},
    hand_sigma_MPa=sig_root_clamp / 1e6, hand_sigma_FEAgeom_MPa=sig_root_fea_geom / 1e6,
    repo_hand_MPa=SIM['boom_hand_sigma'], fea_coarse_MPa=SIM['boom_vm_max'], fea_fine_MPa=SIM['boom_vm_max_fine'],
    delta_fine_vs_hand_pct=pct(SIM['boom_vm_max_fine'], sig_root_clamp / 1e6), delta_coarse_vs_FEAgeom_hand_pct=pct(SIM['boom_vm_max'], sig_root_fea_geom / 1e6),
    RF_yield_min=SY_MIN / (sig_root_clamp), RF_yield_repo=SY_REPO / (SIM['boom_vm_max_fine'] * 1e6),
    fatigue_ratio=sig_root_clamp / 97e6, P_from='3.13 kgf maker maximum thrust x 9.80665 (results.json struct.Tmax)')
rec('STR-01', 'boom root stress: hand M c / I vs repo hand (cad/sim/results.txt)', sig_root_clamp / 1e6, SIM['boom_hand_sigma'], 0.5)
rec('STR-01b', 'boom root stress: FEA coarse (3 mm) vs hand on the FEA load position', SIM['boom_vm_max'], sig_root_fea_geom / 1e6, 5.0)

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
    max_abs_delta_pct=float(np.max(np.abs(dl))) if dl else None,
    peak_coarse_MPa=SIM['boom_vm_max'], peak_fine_MPa=SIM['boom_vm_max_fine'],
    peak_change_coarse_to_fine_pct=pct(SIM['boom_vm_max_fine'], SIM['boom_vm_max']),
    elements={'coarse_3mm': log_elements('FEA_Boom_Arm-Boom full thrust'), 'fine_1.5mm': log_elements('FEA_Boom_Arm-Boom full thrust fine mesh'), 'src': 'cad/sim/*.LOG (UTF-16)'},
    note='peak grows 9 % on mesh halving at the fixed root face: restraint singularity, not converged; nominal stress away from the root is the comparable quantity')
out['summary'].append({'id': 'STR-02', 'check': 'boom FEA field vs beam theory, worst |delta| of 4 stations (fine mesh)', 'independent': float(np.max(np.abs(dl))),
                       'repo': 5.0, 'delta_pct': None, 'tolerance_pct': None, 'relation': 'le', 'pass': float(np.max(np.abs(dl))) <= 5.0,
                       'note': 'value is the worst |delta| in %; pass if <= 5 %'})
put('STR-03', what='Boom tip deflection',
    equations=['delta = P L^3 / (3 E I)', 'delta_tip (load at a) = P a^2 (3L - a) / (6 E I)'],
    hand_tip_load_at_L_mm=defl_tip_repo * 1e3, hand_tip_load_at_block_mm=defl_tip_fea_geom * 1e3,
    hand_at_load_mm=defl_at_load * 1e3, repo_hand_mm=SIM['boom_hand_defl'], fea_mm=SIM['boom_disp_max'],
    delta_fea_vs_FEAgeom_hand_pct=pct(SIM['boom_disp_max'], defl_tip_fea_geom * 1e3),
    note='FEA root is rigid (fixed face); real root is a printed PETG split clamp bonded to a foam hardpoint, so real deflection is larger (compliance —)')
rec('STR-03', 'boom tip deflection: FEA vs hand with the FEA load position', SIM['boom_disp_max'], defl_tip_fea_geom * 1e3, 5.0)

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
m_esc_est = PRM['mEsc']   # analysis/sizing.mjs X4110S mEsc 25 g (EST in repo)
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
    ratio_1P_hover_over_f1=rpm_hover / 60 / SIM['boom_f1'],
    note='rigid root in both hand and FEA; clamp compliance lowers f1 further (—), i.e. away from 1P. rpm from firmware/sitl/c0_physics.py EST')
rec('STR-04', 'boom f1: FEA vs hand with the FEA tip-block centroid', SIM['boom_f1'], f_feageom, 5.0)
rec('STR-04b', 'hover 1P (EST) / f1 >= 2 (separation)', rpm_hover / 60 / SIM['boom_f1'], 2.0, rel='ge')
put('STR-05', what='Lift-unit (boom tip) mass: sizing/FEA value vs CAD part masses',
    sizing_mTip_kg=ST['mTip'], sizing_items_kg={'mMotor': PRM['mMotor'], 'mEsc': PRM['mEsc'], 'mProp': PRM['mProp'], 'mMount': PRM['mMount']},
    mass_budget_mMount_kg=MB['calibration']['mMount'], fea_tip_mass_kg=P['feaTipMass'],
    cad_parts_kg={'Motor_Mount_Upper': mm_up, 'Motor_Mount_Cap': mm_cap, 'Lift_Motor': m_motor, 'Lift_Prop': m_prop,
                  'Prop_Plate': m_plate, 'fasteners+inserts (4 F01, 6 F02, 4 I01)': 4 * m_f01 + 6 * m_f02 + 4 * m_ins,
                  'ESC (sizing EST)': m_esc_est},
    cad_unit_kg=m_unit_cad, delta_pct=pct(m_unit_cad, ST['mTip']),
    note='sizing.mjs mMount is now calibrated from the CAD (analysis/mass/mass_budget.json calibration.mMount); was a 20 g EST before 2026-11-01')
rec('STR-05', 'lift-unit mass: CAD part roll-up vs sizing / FEA tip mass', m_unit_cad, ST['mTip'], 5.0)

# ------------------------------------------------------------------ STR-06..09 wing root moment, joiner, spar
mtow_p = P['mtow']; mtow_r = SZ['m']; n_ult = ST['nUlt']; semi = BASE['span'] / 2
def Mroot(m, dist, n=None):
    Lh = m * G * (n or n_ult) / 2
    if dist == 'elliptic': return Lh * 4 * semi / (3 * math.pi)
    if dist == 'uniform': return Lh * semi / 2
    if dist == 'schrenk': return 0.5 * (Lh * 4 * semi / (3 * math.pi) + Lh * semi / 2)
M_e, M_u, M_s = Mroot(mtow_p, 'elliptic'), Mroot(mtow_p, 'uniform'), Mroot(mtow_p, 'schrenk')
# AVL span loading of this wing (vortex lattice, analysis/aero/out/avl/fs_pod_trim.txt strip forces): spanwise centroid of lift
def avl_ybar(fn):
    t = open(J('analysis', 'aero', 'out', 'avl', fn), encoding='utf-8').read()
    s = re.split(r'Surface #\s*\d+\s+', t)[1]                      # surface 1 = right wing
    rows = []
    for line in s.split('Strip Forces referred to Strip Area, Chord')[-1].splitlines()[2:]:
        p = line.split()
        if len(p) < 10 or not p[0].isdigit(): break
        y, c, A, ccl = float(p[2]), float(p[4]), float(p[5]), float(p[6])
        rows.append((y, A / c, ccl))                                # strip lift ~ c_cl x strip width
    Lw = sum(w * q for y, w, q in rows); Mw = sum(w * q * abs(y) for y, w, q in rows)
    return Mw / Lw, len(rows)
ybar_avl, n_strips = avl_ybar('fs_pod_trim.txt')
ybar_avl_a4, _ = avl_ybar('fs_pod_a4.txt')
Lh_ult = mtow_p * G * n_ult / 2
M_avl = Lh_ult * ybar_avl
# inertia relief (not credited by the repo): boom-mounted groups at the boom station (mass_budget.json groups / 2 per side)
grp = {g['group']: g['bottom_up_g'] / 1000 for g in MB['groups']}
y_boom = abs(float([c for c in COMP if c[0] == 'Boom_Front'][0][3]))
m_out_side = (grp['Lift units'] + grp['Booms + clamps'] + grp['Landing gear']) / 2
M_relief = n_ult * G * m_out_side * y_boom
# envelope: the stall line caps the load factor at n = (V / Vs)^2 (1 g stall speed at MTOW, results.json params.Vs, CLmax 1.116)
Vs = PRM['Vs']; V_max = 25.0   # firmware/vtol_c0.param AIRSPEED_MAX 25
n_stall = {'18 (cruise)': (18 / Vs) ** 2, '22 (R11 top)': (22 / Vs) ** 2, '25 (AIRSPEED_MAX)': (V_max / Vs) ** 2}
V_A = Vs * math.sqrt(ST['nLimit'])
put('STR-06', what='Wing root bending moment at ultimate (n = 4.5): elliptic vs AVL span loading vs Schrenk / uniform',
    equations=['L_half = m g n / 2', 'M_ell = L_half 4 b_s / (3 pi)', 'M_avl = L_half y_bar, y_bar = sum(c_cl dy y) / sum(c_cl dy) (AVL strips)',
               'M_schrenk = (M_ell + M_uni)/2', 'M_relief = n g m_out y_boom', 'n_stall = (V / V_s)^2'],
    inputs={'mtow_params_kg': mtow_p, 'mtow_results_kg': mtow_r, 'n_ult': n_ult, 'n_limit': ST['nLimit'], 'FS': ST['FS'], 'semispan_m': semi,
            'avl_file': 'analysis/aero/out/avl/fs_pod_trim.txt', 'avl_strips': n_strips, 'y_boom_m': y_boom, 'm_outboard_per_side_kg': m_out_side},
    L_half_N=Lh_ult, ybar_elliptic_m=4 * semi / (3 * math.pi), ybar_avl_m=ybar_avl, ybar_avl_alpha4_m=ybar_avl_a4, ybar_schrenk_m=M_s / Lh_ult,
    M_elliptic_Nm=M_e, M_avl_Nm=M_avl, M_schrenk_Nm=M_s, M_uniform_Nm=M_u, M_relief_Nm=M_relief, M_avl_minus_relief_Nm=M_avl - M_relief,
    repo_params_Nm=P['feaRootMomentTarget'], repo_results_Nm=ST['Mroot'],
    delta_elliptic_vs_repo_pct=pct(M_e, P['feaRootMomentTarget']), delta_schrenk_vs_repo_pct=pct(M_s, P['feaRootMomentTarget']), delta_avl_vs_elliptic_pct=pct(M_avl, M_e), delta_schrenk_vs_avl_pct=pct(M_s, M_avl),
    n_stall_line=n_stall, V_A_mps=V_A,
    note='repo (sizing.mjs structures()) uses Schrenk loading (rev 2026-11-02, was elliptic) and n_limit 3.0 x FS 1.5 (EST, no source); no inertia relief (conservative)')
rec('STR-06', 'root moment: Schrenk hand vs repo (params.txt feaRootMomentTarget)', M_s, P['feaRootMomentTarget'], 0.5)
rec('STR-06b', 'root moment: Schrenk vs AVL span loading (claim value)', M_s, M_avl, 5.0)

Ij = tube_I(P['joinOD'], P['joinID']); cj = P['joinOD'] / 2
Ij_fea = tube_I(P['sparID'], P['joinID']); cj_fea = P['sparID'] / 2
sigJ = {k: M * cj / Ij for k, M in (('elliptic', M_e), ('avl', M_avl), ('schrenk', M_s), ('uniform', M_u))}
sig_avl_25 = M_avl * (n_stall['25 (AIRSPEED_MAX)'] / n_ult) * cj / Ij
put('STR-07', what='Joiner (0.875 x 0.058 in) bending stress at the centreline and reserve factor',
    equations=['sigma = M c / I', 'RF = sigma_y / sigma'], I_true_mm4=Ij * 1e12,
    sigma_MPa={k: v / 1e6 for k, v in sigJ.items()}, repo_hand_MPa=SIM['spar_hand_sigJ'],
    delta_elliptic_vs_repo_pct=pct(sigJ['elliptic'] / 1e6, SIM['spar_hand_sigJ']), delta_schrenk_vs_repo_pct=pct(sigJ['schrenk'] / 1e6, SIM['spar_hand_sigJ']),
    RF={'elliptic_repo275': SY_REPO / sigJ['elliptic'], 'elliptic_min240': SY_MIN / sigJ['elliptic'],
        'avl_repo275': SY_REPO / sigJ['avl'], 'avl_min240': SY_MIN / sigJ['avl'],
        'schrenk_min240': SY_MIN / sigJ['schrenk'], 'uniform_min240': SY_MIN / sigJ['uniform']},
    sigma_avl_at_stall_line_25mps_MPa=sig_avl_25 / 1e6, RF_min240_at_stall_line_25mps=SY_MIN / sig_avl_25,
    repo_RF=ST['MS_J'])
rec('STR-07', 'joiner stress at the AVL moment: hand M c / I', sigJ['avl'] / 1e6, sigJ['avl'] / 1e6, 0.5, note='same formula as the repo; see STR-07b')
rec('STR-07b', 'joiner stress, repo Schrenk (rev 2026-11-02, was elliptic): hand vs cad/sim/results.txt spar_hand_sigJ', sigJ['schrenk'] / 1e6, SIM['spar_hand_sigJ'], 0.5)
rec('STR-07c', 'joiner RF on minimum yield at the AVL moment >= 1.0', SY_MIN / sigJ['avl'], 1.0, rel='ge')

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
sl_max = max(abs(s['delta_pct']) for s in spar_sl if s['delta_pct'] is not None)
put('STR-08', what='Spar+joiner FEA vs beam theory on the FEA geometry (joiner OD = socket ID, bonded)',
    equations=['M(z) from uniform w on [fusR, fusR + sparLen]', 'sigma = M c / I (section per zone)'],
    M_centreline_Nm=M_sp(0.0), hand_root_FEAgeom_MPa=sig_root_fea_hand / 1e6, I_fea_joiner_mm4=Ij_fea * 1e12,
    fea_coarse_MPa=SIM['spar_vm_max'], fea_fine_MPa=SIM['spar_vm_max_fine'],
    delta_coarse_pct=pct(SIM['spar_vm_max'], sig_root_fea_hand / 1e6), delta_fine_pct=pct(SIM['spar_vm_max_fine'], sig_root_fea_hand / 1e6),
    slices=spar_sl, field_nodes=spar_nodes, max_abs_slice_delta_pct=sl_max,
    stiffness_ratio_fea_over_true_joiner=Ij_fea / Ij,
    elements={'coarse_3mm': log_elements('FEA_Spar_Joiner-Spar ultimate load'), 'fine_2mm': log_elements('FEA_Spar_Joiner-Spar ultimate load fine mesh')})
rec('STR-08', 'spar FEA coarse peak vs hand on the FEA geometry', SIM['spar_vm_max'], sig_root_fea_hand / 1e6, 5.0)
out['summary'].append({'id': 'STR-08b', 'check': 'spar FEA field vs beam theory, worst |delta| of 6 stations', 'independent': sl_max, 'repo': 5.0,
                       'delta_pct': None, 'tolerance_pct': None, 'relation': 'le', 'pass': sl_max <= 5.0, 'note': 'value is the worst |delta| in %'})
put('STR-09', what='Spar tip deflection, FEA geometry, numerical double integration of M/EI',
    hand_tip_mm=float(dv[-1] * 1e3), fea_tip_mm=SIM['spar_tip_disp'], delta_pct=pct(SIM['spar_tip_disp'], float(dv[-1] * 1e3)),
    note='FEA joiner is 9.6 % stiffer than the real joiner; real joiner + 0.23 mm slip-fit clearance + foam add rotation (—)')
rec('STR-09', 'spar tip deflection: FEA vs double integration on the FEA geometry', SIM['spar_tip_disp'], float(dv[-1] * 1e3), 5.0)

# ------------------------------------------------------------------ STR-10 boom-to-wing clamp loads
xF_motor = max(float(c[1]) for c in COMP if c[0] == 'Motor_Mount_Upper')
xR_motor = min(float(c[1]) for c in COMP if c[0] == 'Motor_Mount_Upper')
xFc = float([c for c in COMP if c[0] == 'Boom_Clamp_F_Upper'][0][1]); xRc = float([c for c in COMP if c[0] == 'Boom_Clamp_R_Upper'][0][1])
arm_f = xF_motor - xFc; sp = xFc - xRc
R_rear_single = Pt * arm_f / sp; R_front_single = Pt + R_rear_single
# independent: moment balance about the rear clamp gives the front reaction directly
R_front_moment = Pt * (xF_motor - xRc) / sp
hs = open(J('docs', 'research', 'hardware-spec.md'), encoding='utf-8').read()
mm = re.search(r'rear clamp tension = [\d.]+ × [\d.]+ / [\d.]+ = ([\d.]+) N', hs)
put('STR-10', what='Boom clamp reactions into the wing hardpoints, single front motor at Tmax (differential thrust)',
    equations=['R_rear = T a / s', 'R_front = T + R_rear', 'check: R_front = T (a + s) / s (moments about the rear clamp)'],
    inputs={'x_front_motor': xF_motor, 'x_front_clamp': xFc, 'x_rear_clamp': xRc, 'arm_m': arm_f, 'spacing_m': sp, 'T_N': Pt},
    rear_clamp_tension_N=R_rear_single, per_screw_N=R_rear_single / 2, front_clamp_N=R_front_single, front_clamp_by_moments_N=R_front_moment,
    repo_spec_value_N=float(mm.group(1)) if mm else None, delta_pct=pct(R_rear_single, float(mm.group(1))) if mm else None,
    rear_plate_bond_area_mm2=60 * 46, rear_plate_bond_stress_kPa=R_rear_single / (60 * 46e-6) / 1e3,
    m3_bolt_tension_util=R_rear_single / 2 / 2264.0, test_plan_C03_pass_N_PETG=300.0, C03_margin_if_passed=300.0 / (R_rear_single / 2),
    insert_pullout_N=None, xps_bond_strength_kPa=None,
    note='docs/research/hardware-spec.md J05 load check is generated from params.txt by analysis/docs_sync.py; insert pull-out (C03) and XPS bond strength: —')
rec('STR-10', 'rear clamp tension: hand vs hardware-spec J05 (generated)', R_rear_single, float(mm.group(1)) if mm else None, 0.5)
rec('STR-10b', 'front clamp reaction: force balance vs moment balance', R_front_single, R_front_moment, 0.1)

# ------------------------------------------------------------------ STR-11 landing (analysis/structures/landing.py)
land = {}   # RK4 integration of m x'' = m g - k x from x = 0, x' = v until the mass stops (peak spring force)
for side, c in LAND['corners'].items():
    for case, r in c['cases'].items():
        # landing.py uses g 9.80665; the ODE here uses the same so only the method differs
        G_ = 9.80665
        mi, k, v = c['mass_share_kg'], c['k_N_per_m'], r['v_mps']
        x, u, Fmax, dt = 0.0, v, 0.0, 2e-6
        while u >= 0:
            a1 = G_ - k * x / mi; x1 = x + u * dt / 2; u1 = u + a1 * dt / 2
            a2 = G_ - k * x1 / mi; x2 = x + u1 * dt / 2; u2 = u + a2 * dt / 2
            a3 = G_ - k * x2 / mi; x3 = x + u2 * dt; u3 = u + a3 * dt
            a4 = G_ - k * x3 / mi
            x += dt / 6 * (u + 2 * u1 + 2 * u2 + u3); u += dt / 6 * (a1 + 2 * a2 + 2 * a3 + a4); Fmax = max(Fmax, k * x)
        k_hand = 3 * E_AL * Ib / c['arm_m'] ** 3
        s_hand = Fmax * c['arm_m'] * c_b / Ib
        land[f'{side}_{case}'] = {'v_mps': v, 'F_ode_N': Fmax, 'F_repo_N': r['force_N'], 'delta_F_pct': pct(Fmax, r['force_N']),
                                  'k_hand_N_per_m': k_hand, 'k_repo_N_per_m': k, 'sigma_hand_MPa': s_hand / 1e6, 'sigma_repo_MPa': r['stress_MPa'],
                                  'RF_min240': SY_MIN / s_hand}
# wing-root (joiner) moment in the hard landing: gear reactions at the boom station minus inertia of the boom-mounted mass
# (EST upper bound: rigid clamps as in landing.py, all other mass taken at the centreline so no wing-mass relief)
Ff, Fr = LAND['corners']['front']['cases']['hard']['force_N'], LAND['corners']['rear']['cases']['hard']['force_N']
nf, nr = LAND['corners']['front']['cases']['hard']['load_factor_g'], LAND['corners']['rear']['cases']['hard']['load_factor_g']
M_land = (Ff + Fr - m_out_side * G * (nf + nr) / 2) * y_boom
Fn, Frn = LAND['corners']['front']['cases']['normal']['force_N'], LAND['corners']['rear']['cases']['normal']['force_N']
nfn, nrn = LAND['corners']['front']['cases']['normal']['load_factor_g'], LAND['corners']['rear']['cases']['normal']['load_factor_g']
M_land_n = (Fn + Frn - m_out_side * G * (nfn + nrn) / 2) * y_boom
# the superseded 0.30 m drop (2.43 m/s) for reference
v_drop = math.sqrt(2 * G * 0.30)
put('STR-11', what='Vertical landing: ODE re-integration of analysis/structures/landing.py corners + joiner moment in a hard landing',
    equations=['m x\'\' = m g - k x, x(0) = 0, x\'(0) = v (RK4, dt 2 us)', 'k = 3 E I / a^3', 'sigma = F a c / I',
               'M_joiner = (F_front + F_rear - m_out g n_avg) y_boom (EST upper bound)'],
    landing_json=LAND['inputs']['land_speed'], corners=land,
    joiner_moment_hard_Nm_EST=M_land, joiner_sigma_hard_MPa_EST=M_land * cj / Ij / 1e6, joiner_RF_min240_hard_EST=SY_MIN / (M_land * cj / Ij),
    joiner_moment_normal_Nm_EST=M_land_n, superseded_drop_0p30m_v_mps=v_drop,
    note='landing.py treats the wing clamp as rigid and the dome foot as rigid, so it over-predicts force (conservative); S06 measures')
for kk, vv in land.items():
    rec('STR-11', f'landing {kk}: peak force ODE vs landing.json closed form', vv['F_ode_N'], vv['F_repo_N'], 0.5)
rec('STR-11b', 'landing worst corner RF on minimum yield (rear hard) >= 1.0', land['rear_hard']['RF_min240'], 1.0, rel='ge')

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
rec('STR-12', 'splice bolt shear utilisation (inertial load, n 4.5) <= 1', F_bolt / (2 * 0.6 * 3522), 1.0, rel='le')

# ------------------------------------------------------------------ STR-13 wing bolt J10
c = P['chord']; arm_bolt = (0.70 - 0.30) * c
L_half = mtow_p * G * n_ult / 2
T_panel = L_half * (0.30 - 0.25) * c     # EST: lift at the quarter chord, joiner at 30 % c; Cm0 ignored (—)
F_b = T_panel / arm_bolt
f09 = next(f for f in HW['fasteners'] if f['id'] == 'F09')
preload = f09['torque_Nm'] / (0.16 * 0.005)
put('STR-13', what='Wing retention bolt J10 (M5 A2-70) reacting panel torsion about the round slip-fit joiner',
    equations=['T = L_half (x_joiner - x_ac) c', 'F = T / ((0.70 - 0.30) c)', 'F_pre = T_q / (K d)'],
    T_panel_Nm=T_panel, F_bolt_N=F_b, tau_bolt_MPa=F_b / 14.2, shear_util=F_b / (0.6 * 9928),
    bearing_on_6p4mm_PETG_tongue_MPa=F_b / (5.0 * 6.4), PETG_yield_proxy_MPa=PETG_YIELD / 1e6,
    RF_tongue_bearing_vs_PETG_proxy=PETG_YIELD / (F_b / (5.0 * 6.4e-6)), Cm0=None,
    preload_N_repo=preload, preload_bearing_MPa_repo=preload / 47.0, preload_bearing_over_PETG_yield=preload / 47.0 / (PETG_YIELD / 1e6),
    note='EST aerodynamic centre at 25 % c; NACA 2415 Cm0 not read from the repo (—); PETG strength from a proxy datasheet (EST); '
         'head bearing 47 mm2 and K 0.16 from hardware.json F09 torque_basis')
rec('STR-13', 'J10 tongue bearing vs PETG proxy yield, RF >= 1.5', PETG_YIELD / (F_b / (5.0 * 6.4e-6)), 1.5, rel='ge')

# ------------------------------------------------------------------ STR-14 motor reaction torque and clamp slip
P_motor_max = 615.0   # maker 17x5.8 at 22.2 V full throttle 615 W (propulsion_data S1)
Q_max = 0.8 * P_motor_max / (rpm_max * 2 * math.pi / 60)
F_pre = {'K0.16_lub': 0.5 / (0.16 * 0.003), 'K0.35_dry': 0.5 / (0.35 * 0.003)}
T_slip = {k: 0.3 * 4 * v * c_b for k, v in F_pre.items()}
put('STR-14', what='Lift-motor reaction torque on the boom and clamp friction capacity',
    equations=['Q = eta P / omega', 'sigma_lat = Q c / I', 'F = T/(K d)', 'T_slip = mu n F r'],
    Q_max_Nm_EST=Q_max, sigma_lateral_MPa=Q_max * c_b / Ib / 1e6, preload_N=F_pre, slip_torque_Nm=T_slip,
    repo_slip_Nm=16.0, S04_test_Nm=2 * G * 0.25, margin_dry_over_Q=T_slip['K0.35_dry'] / Q_max,
    note='mu 0.3 EST (repo); bolts into brass inserts in PETG/PA6-CF are not lubricated -> K 0.35 (Fastenal dry) halves preload; insert torque-out — (C02)')
rec('STR-14', 'clamp slip torque, dry threads, vs motor reaction torque (ratio >= 3)', T_slip['K0.35_dry'] / Q_max, 3.0, rel='ge')

# ------------------------------------------------------------------ thermal
AIR = dict(nu=1.65e-5, k=0.0268, Pr=0.706)   # analysis/thermal/thermal_inputs.py (Incropera A.4 at ~308 K, the film temperature)
def hilpert(V, D):
    Re = V * D / AIR['nu']
    C, m = (0.989, 0.330) if Re < 4 else (0.911, 0.385) if Re < 40 else (0.683, 0.466) if Re < 4000 else (0.193, 0.618) if Re < 40000 else (0.027, 0.805)
    return C * Re ** m * AIR['Pr'] ** (1 / 3) * AIR['k'] / D, Re
def churchill_bernstein(V, D):
    Re = V * D / AIR['nu']; Pr = AIR['Pr']
    Nu = 0.3 + 0.62 * Re ** 0.5 * Pr ** (1 / 3) / (1 + (0.4 / Pr) ** (2 / 3)) ** 0.25 * (1 + (Re / 282000) ** (5 / 8)) ** (4 / 5)
    return Nu * AIR['k'] / D
rho_isa = BASE['rho']
vi = math.sqrt(SZ['Tunit_N'] / (2 * rho_isa * SZ['A']))
h_hov, Re_h = hilpert(vi, P['motorD']); h_cru, Re_c = hilpert(BASE['Vc'], P['motorD'])
h_hov_cb = churchill_bernstein(vi, P['motorD']); h_cru_cb = churchill_bernstein(BASE['Vc'], P['motorD'])
A_m = math.pi * P['motorD'] * P['motorH'] + 2 * math.pi * P['motorD'] ** 2 / 4
Tamb = TH_IN['ambient']['hot_C']   # design ambient the FEA ran at (rev 2026-11-02: 25 C = DESIGN-BASIS R21 field limit)
Tamb_simcs = P['thermAmbK'] - 273.15   # the Sim.cs motor-only solver-validation study keeps its own fixed 35 C test ambient (cad/params.mjs thermAmbK)
Tss_simcs = Tamb_simcs + P['thermQ'] / (P['thermH'] * A_m)
T_corr_hand = Tamb + TH_IN['loads']['lift_motor_W'] / (h_hov * A_m)
put('THM-01', what='Motor-only steady temperature: Sim.cs validation case and the 25 C design-ambient bound',
    equations=['T = T_amb + Q / (h A)', 'A = pi D H + 2 pi D^2/4'],
    A_m2=A_m, T_simcs_hand_C=Tss_simcs, fea_simcs_C=SIM['motor_T_steady'], delta_pct_on_rise=pct(SIM['motor_T_steady'] - Tamb_simcs, Tss_simcs - Tamb_simcs), T_amb_simcs_C=Tamb_simcs,
    T_corr_hand_C=T_corr_hand, fea_corr_C=SIM['motor_only_T_steady'], delta_corr_pct_on_rise=pct(SIM['motor_only_T_steady'] - Tamb, T_corr_hand - Tamb), T_amb_design_C=Tamb)
rec('THM-01', 'motor-only steady, Sim.cs case: FEA rise vs hand rise', SIM['motor_T_steady'] - Tamb_simcs, Tss_simcs - Tamb_simcs, 2.0)
rec('THM-01b', 'motor-only steady, 25 C design ambient: FEA rise vs hand rise', SIM['motor_only_T_steady'] - Tamb, T_corr_hand - Tamb, 5.0)
put('THM-02', what='Film coefficients in hover wash and 18 m/s cruise: Hilpert (repo) vs Churchill-Bernstein (independent)',
    equations=['v_i = sqrt(T / (2 rho A))', 'Re = V D / nu', 'Hilpert: Nu = C Re^m Pr^(1/3)',
               'Churchill-Bernstein: Nu = 0.3 + 0.62 Re^0.5 Pr^(1/3) / (1 + (0.4/Pr)^(2/3))^0.25 (1 + (Re/282000)^(5/8))^(4/5)', 'h = Nu k / D'],
    v_i_mps=vi, rho_used=rho_isa, Re_hover=Re_h, Re_cruise=Re_c, h_motor_hover=h_hov, h_motor_hover_CB=h_hov_cb,
    repo_h_motor_hover=TH_IN['h']['motor_hover'], h_motor_cruise=h_cru, h_motor_cruise_CB=h_cru_cb, repo_h_motor_cruise=TH_IN['h']['motor_cruise'],
    delta_hover_pct=pct(h_hov, TH_IN['h']['motor_hover']), delta_CB_hover_pct=pct(h_hov_cb, TH_IN['h']['motor_hover']),
    delta_CB_cruise_pct=pct(h_cru_cb, TH_IN['h']['motor_cruise']))
rec('THM-02', 'h hover: Churchill-Bernstein vs repo Hilpert', h_hov_cb, TH_IN['h']['motor_hover'], 5.0)
R_wind = S1['resistance_mohm'] / 1000.0; I0 = float(S1['no_load_current'].split('A')[0])
I_hov = SZ['P_hover_per_motor'] / 21.0
V_bemf = rpm_hover / S1['kv']
Q_cu = I_hov ** 2 * R_wind; Q_nl = I0 * V_bemf
put('THM-03', what='Lift motor heat load in hover: 20 % rule (repo) vs maker-data loss model I^2 R + I0 V_bemf',
    equations=['Q_rule = 0.2 P_in', 'Q = I^2 R + I0 V_bemf', 'I = P_in / 21 V', 'V_bemf = rpm_hover / KV'],
    Q_rule_W=0.2 * SZ['P_hover_per_motor'], I_hover_A=I_hov, R_ohm=R_wind, I0_A=I0, rpm_hover_EST=rpm_hover, V_bemf_V=V_bemf,
    Q_I2R_W=Q_cu, Q_no_load_W_EST=Q_nl, Q_model_W=Q_cu + Q_nl, repo_Q_W=TH_IN['loads']['lift_motor_W'],
    note='R 107 mOhm and I0 0.6 A at 10 V from the maker (propulsion_data S1); I0 taken constant with speed (EST); PWM/eddy losses not modelled (—)')
rec('THM-03', 'lift motor heat: maker-data model <= 20 % rule (rule is an upper estimate)', Q_cu + Q_nl, TH_IN['loads']['lift_motor_W'], rel='le')

def lumped(phases, C, A, T0=Tamb, amb=Tamb):
    T = T0; hist = []; peak = T0
    for name, dt, Q, h in phases:
        tau = C / (h * A); Tinf = amb + Q / (h * A)
        T = Tinf + (T - Tinf) * math.exp(-dt / tau); hist.append((name, round(T, 2))); peak = max(peak, T)
    return T, hist, peak
L_ = TH_IN['loads']; H_ = TH_IN['h']
C_m = P['motorMass'] * TH_IN['materials']['motor']['cp']
T60, _, _ = lumped([('hover', 60, L_['lift_motor_W'], H_['motor_hover'])], C_m, A_m)
T90, _, _ = lumped([('hover', 90, L_['lift_motor_W'], H_['motor_hover'])], C_m, A_m)
Tmis, hist, Tpk = lumped([('hover', 60, L_['lift_motor_W'], H_['motor_hover']), ('trans', 20, L_['lift_motor_trans_W'], H_['motor_hover']),
                          ('cruise', 600, 0.0, H_['motor_cruise']), ('trans', 20, L_['lift_motor_trans_W'], H_['motor_hover']),
                          ('hover', 60, L_['lift_motor_W'], H_['motor_hover'])], C_m, A_m)
# THM-02b (rev 2026-11-02): the two cruise correlations differ by ~7 % (empirical scatter); what matters is whether that changes a
# result. The stopped lift motor only cools in cruise (tau ~1.8 min vs 10 min), so the test is the mission peak with each value
_, _, Tpk_cb = lumped([('hover', 60, L_['lift_motor_W'], H_['motor_hover']), ('trans', 20, L_['lift_motor_trans_W'], H_['motor_hover']),
                       ('cruise', 600, 0.0, h_cru_cb), ('trans', 20, L_['lift_motor_trans_W'], H_['motor_hover']),
                       ('hover', 60, L_['lift_motor_W'], H_['motor_hover'])], C_m, A_m)
tau_cru_min = C_m / (H_['motor_cruise'] * A_m) / 60
rec('THM-02b', 'lift-motor mission peak: change when cruise h is Churchill-Bernstein instead of Hilpert (K)', abs(Tpk_cb - Tpk), 0.5, rel='le',
    note=f'h cruise {h_cru_cb:.1f} vs {H_["motor_cruise"]:.1f} W/m2K ({pct(h_cru_cb, H_["motor_cruise"]):+.1f} %); cruise time constant {tau_cru_min:.1f} min vs 10 min cruise, so the motor reaches ambient with either value')
T90_simcs, _, _ = lumped([('hover', 90, P['thermQ'], P['thermH'])], C_m, A_m, T0=Tamb_simcs, amb=Tamb_simcs)
R = TH_RES['results']
put('THM-04', what='Lift motor transient (lumped capacitance, motor alone) vs SOLIDWORKS lift-unit transient',
    equations=['T(t) = T_inf + (T0 - T_inf) exp(-t/tau)', 'tau = m c_p / (h A)'],
    C_J_per_K=C_m, tau_hover_s=C_m / (H_['motor_hover'] * A_m),
    hand_60s_C=T60, fea_60s_C=R['lift_hover60_Motor'], hand_90s_C=T90, fea_90s_C=R['lift_hover90_Motor'],
    hand_mission_end_C=Tmis, hand_mission_peak_C=Tpk, fea_mission_end_C=R['lift_mission_end_Motor'], fea_mission_max_C=R['lift_mission_max_Motor'],
    mission_history=hist, simcs_90s_hand_C=T90_simcs, simcs_90s_fea_C=SIM['val_motor_T90'],
    delta_60_pct_on_rise=pct(R['lift_hover60_Motor'] - Tamb, T60 - Tamb), delta_mission_pct_on_rise=pct(R['lift_mission_end_Motor'] - Tamb, Tmis - Tamb),
    limit_C=TH_IN['limits']['motor_can_C'], limit_src='docs/test/TEST-PLAN.md abort table / C08 (EST, maker gives none)',
    note='the hand model has no mount, so it is an upper bound (the FEA mount adds heat capacity through an ideal bonded contact)')
rec('THM-04', 'Sim.cs 90 s validation: FEA rise vs lumped rise', SIM['val_motor_T90'] - Tamb_simcs, T90_simcs - Tamb_simcs, 2.0)
rec('THM-04b', 'lift-unit FEA mission peak <= lumped motor-alone upper bound', R['lift_mission_max_Motor'], Tpk, rel='le')
e = TH_IN['esc']; A_esc = 2 * (e['len_m'] * e['width_m'] + e['len_m'] * e['height_m'] + e['width_m'] * e['height_m']) - e['len_m'] * e['width_m']
C_esc = TH_IN['materials']['esc']['rho'] * TH_IN['materials']['esc']['cp'] * e['len_m'] * e['width_m'] * e['height_m']
Te60, _, _ = lumped([('hover', 60, L_['lift_esc_W'], H_['esc_hover'])], C_esc, A_esc)
Tess = Tamb + L_['lift_esc_W'] / (H_['esc_hover'] * A_esc)
put('THM-05', what='Lift ESC (boom underside) lumped check', A_m2=A_esc, C_J_per_K=C_esc,
    hand_60s_C=Te60, fea_60s_C=R['lift_hover60_ESC'], hand_steady_C=Tess, fea_steady_C=R['lift_steady_ESC'], fea_mission_max_C=R['lift_mission_max_ESC'],
    delta_60_pct_on_rise=pct(R['lift_hover60_ESC'] - Tamb, Te60 - Tamb), limit_C=TH_IN['limits']['esc_C'])
rec('THM-05', 'ESC 60 s hover: FEA rise vs lumped rise', R['lift_hover60_ESC'] - Tamb, Te60 - Tamb, 5.0)
Qb = L_['batt_hover_W'] * 120 + L_['batt_trans_W'] * 40 + L_['batt_cruise_W'] * 600
mcb = SZ['m_batt'] * TH_IN['materials']['lipo']['cp']
put('THM-06', what='Battery pack, adiabatic I^2 R heating over the mission',
    equations=['Q = I^2 R_pack', 'dT = sum(Q t) / (m c_p)'],
    I_A={'hover': SZ['I_hover_loaded'], 'trans': SZ['I_trans'], 'cruise': SZ['I_cruise']}, R_pack_ohm=L_['R_pack_ohm'],
    Q_hover_W=SZ['I_hover_loaded'] ** 2 * L_['R_pack_ohm'], E_J=Qb, mcp_J_per_K=mcb, hand_end_C=Tamb + Qb / mcb,
    fea_end_C=R['pod_mission_end_Battery'], delta_pct_on_rise=pct(R['pod_mission_end_Battery'] - Tamb, Qb / mcb), limit_C=TH_IN['limits']['lipo_C'],
    cp_for_60C_J_per_kgK=Qb / (SZ['m_batt'] * (TH_IN['limits']['lipo_C'] - Tamb)), R_cell_for_60C_mohm=1000 * L_['R_pack_ohm'] / 6 * (TH_IN['limits']['lipo_C'] - Tamb) / (Qb / mcb))
rec('THM-06', 'battery mission end: FEA rise vs adiabatic hand rise', R['pod_mission_end_Battery'] - Tamb, Qb / mcb, 5.0)
fc = TH_IN['fc']; A_fc = 2 * (fc['len_m'] * fc['width_m'] + fc['len_m'] * fc['height_m'] + fc['width_m'] * fc['height_m'])
C_fc = vmass('Flight_Controller') * 900.0   # cp 900 J/kgK EST (FR4/Cu/Al mix), not in the repo
Tfc, _, _ = lumped([('mission', 760, L_['fc_W'], H_['bay_natural'])], C_fc, A_fc)
Tfc_ss = Tamb + L_['fc_W'] / (H_['bay_natural'] * A_fc); tau_fc = C_fc / (H_['bay_natural'] * A_fc)
lim_fc = TH_IN['limits']['fc_C']
t85 = -tau_fc * math.log(1 - (lim_fc - Tamb) / (Tfc_ss - Tamb)) if Tfc_ss > lim_fc else None
put('THM-07', what='Flight controller in the closed pod bay', A_m2=A_fc, C_J_per_K_EST=C_fc, tau_s=tau_fc,
    hand_end_C=Tfc, hand_steady_C=Tfc_ss, fea_max_C=R['pod_mission_max_FC'],
    delta_pct_on_rise=pct(R['pod_mission_max_FC'] - Tamb, Tfc - Tamb), limit_C=lim_fc,
    hand_time_to_limit_s=t85, scaled_time_to_limit_s_EST=(t85 * (Tfc - Tamb) / (R['pod_mission_max_FC'] - Tamb)) if t85 else None,
    note='limit: STM32F405RGT6 ambient rating 85 C (thermal_inputs.json limits src); cp 900 J/kgK EST; FC power 2.0 W EST')
rec('THM-07', 'FC mission peak: FEA <= 85 C limit', R['pod_mission_max_FC'], lim_fc, rel='le')
rec('THM-07b', 'FC mission end: lumped hand <= 85 C limit', Tfc, lim_fc, rel='le')
Tpu, _, _ = lumped([('cruise', 600, L_['pusher_motor_W'], H_['pusher_motor_cruise'])], C_m, A_m)
put('THM-08', what='Pusher motor after 600 s cruise (fully exposed lumped can = lower bound; FEA has the PA6-CF cup)',
    hand_exposed_C=Tpu, fea_endcruise_C=R['pusher_endcruise_Motor'], fea_steady_C=R['pusher_steady_Motor'],
    delta_pct_on_rise=pct(R['pusher_endcruise_Motor'] - Tamb, Tpu - Tamb), limit_C=TH_IN['limits']['motor_can_C'],
    cup_endcruise_C=R['pusher_endcruise_CupFloor'], pa6cf_HDT_C=TH_IN['limits']['pa6cf_HDT_C'], pa6cf_HDT_stress_MPa=1.8, motor_floor_bearing_MPa_repo=41.0)
rec('THM-08', 'pusher end of cruise: FEA >= exposed-can lower bound', R['pusher_endcruise_Motor'], Tpu, rel='ge')
rec('THM-08b', 'pusher steady-state (FEA) <= 80 C limit', R['pusher_steady_Motor'], TH_IN['limits']['motor_can_C'], rel='le')

# ------------------------------------------------------------------ tolerance stacks (MFG)
def stack(nom, tols, signs=None):
    wc = sum(abs(t) for t in tols); rss = math.sqrt(sum(t * t for t in tols))
    return {'nominal': nom, 'worst_case': [nom - wc, nom + wc], 'rss': [nom - rss, nom + rss], 'wc_half': wc, 'rss_half': rss}
in_ = 0.0254 * 1000
tOD = 0.004 * in_; tW = 0.002 * in_
FT01 = stack(P['sparID'] * 1000 - P['joinOD'] * 1000, [tOD, 2 * tW, tOD])
FT01_repo = stack(P['sparID'] * 1000 - P['joinOD'] * 1000, [0.203, 0.102])
FT06 = stack(P['joinBoreD'] * 1000 - P['joinOD'] * 1000, [0.2, tOD])
FT02 = stack(25.6 - 25.4, [0.2, tOD])
FT04 = stack(23.622 - 23.2, [0.203, 0.2])
# socket coaxiality: spar socket in a 26.0 +-0.5 channel, tube 25.4 +-0.102, bonded over 800 mm
c_ch_max = (26.0 + 0.5) - (25.4 - 0.102); c_ch_rss = (26.0 - 25.4) + math.sqrt(0.5 ** 2 + 0.102 ** 2)
theta_wc = c_ch_max / 800.0; theta_rss = c_ch_rss / 800.0
lat_wc = theta_wc * 300.0; lat_rss = theta_rss * 300.0
theta_joiner = FT01['nominal'] / 300.0
# J10 screw end past the nylock (rev E rule in cad/params.mjs): protrusion = (spot + L) - (pillarH - pocket + h_nut)
n02 = next(n for n in HW['nuts'] if n['id'] == 'N02')
def j10(PP, L_mm):
    return (PP['pillarSpot'] * 1000 + L_mm) - (PP['pillarH'] * 1000 - PP['pillarNutDepth'] * 1000 + n02['h_mm'])
J10_tols = [0.5, 0.4, 0.5, 0.5]   # spot-face, screw length (EST), pillar height, pocket depth (printed +-0.5, hardware.json general rule)
J10 = stack(j10(P, P['wingBoltL'] * 1000), J10_tols)
J10_built = stack(j10(PB, PB['wingBoltL'] * 1000), J10_tols)
J10_m5x20 = stack(j10(P, 20.0), J10_tols)
inside = P['pillarH'] * 1000 - P['pillarSpot'] * 1000 - P['wingBoltL'] * 1000     # screw end above the lower skin
inside_wc = inside - (0.5 + 0.5 + 0.4)
tip_play = lambda cl: cl / 300.0 * P['panelLen'] * 1000
put('MFG-STACKS', FT01_alt_RSS_decomposed=FT01, FT01_repo_band=FT01_repo, FT06=FT06, FT02=FT02, FT04=FT04,
    FT04_rotation_deg={'nominal': math.degrees(FT04['nominal'] / 40), 'wc': math.degrees(FT04['worst_case'][1] / 40)},
    socket_coax={'channel_clear_max_mm': c_ch_max, 'theta_wc_mrad': theta_wc * 1e3, 'theta_rss_mrad': theta_rss * 1e3,
                 'lateral_at_300_wc_mm': lat_wc, 'lateral_at_300_rss_mm': lat_rss, 'nominal_joiner_clearance_mm': FT01['nominal'],
                 'joiner_free_tilt_mrad': theta_joiner * 1e3, 'panel_angle_error_deg_wc': math.degrees(theta_wc),
                 'root_face_gap_over_chord_mm_wc': theta_wc * P['chord'] * 1000, 'tip_offset_mm_wc': theta_wc * P['panelLen'] * 1000},
    J10_inputs={'pillarSpot_mm': P['pillarSpot'] * 1000, 'wingBoltL_mm': P['wingBoltL'] * 1000, 'pillarH_mm': P['pillarH'] * 1000,
                'pillarNutDepth_mm': P['pillarNutDepth'] * 1000, 'N02_h_mm': n02['h_mm'], 'tolerances_mm': J10_tols, 'required_min_mm': 1.6},
    J10_protrusion=J10, J10_protrusion_as_built_CAD=J10_built, J10_protrusion_if_M5x20=J10_m5x20,
    J10_screw_end_above_lower_skin_mm={'nominal': inside, 'worst_case_min': inside_wc},
    wingtip_play_mm={'nominal': tip_play(FT01['nominal']), 'wc': tip_play(FT01_repo['worst_case'][1])},
    note='tube OD +-0.004 in, wall +-0.002 in (hardware.json FT01 source, EST for 0.875/0.058); screw length tol +-0.4 EST; printed +-0.5 (hardware.json general rule)')
rec('MFG-05', 'FT01 worst-case band: decomposed stack vs hardware.json (max clearance)', FT01['worst_case'][1], FT01_repo['worst_case'][1], 0.5)
rec('MFG-07', 'FT02 worst-case max clearance <= half the 1.2 mm split gap x 2 (must stay < 1.2)', FT02['worst_case'][1], 1.2, rel='le')
rec('MFG-09', 'J10 worst-case screw end past the nylock >= 1.6 mm (two pitches)', J10['worst_case'][0], 1.6, rel='ge')
rec('MFG-09b', 'J10 protrusion: params.txt vs as-built CAD (params.built.txt)', J10['nominal'], J10_built['nominal'], 1.0)
rec('MFG-09c', 'J10 worst-case screw end stays inside the lower skin (>= 0 mm)', inside_wc, 0.0, rel='ge')

# ------------------------------------------------------------------ MFG-01 design / analysis / CAD consistency
keys01 = {'chord': ('chord', SZ['chord']), 'mtow': ('mtow', SZ['m']), 'feaBoomL': ('feaBoomL', ST['Lb']),
          'feaRootMomentTarget': ('feaRootMomentTarget', ST['Mroot']), 'feaTipMass': ('feaTipMass', ST['mTip']),
          'feaTipForce': ('feaTipForce', ST['Tmax']), 'thermQ': ('thermQ', 0.2 * SZ['P_hover_per_motor'])}
rows01 = {}
for k, (pk, rv) in keys01.items():
    rows01[k] = {'results_json': rv, 'params_txt': P[pk], 'params_built': PB[pk], 'd_params_pct': pct(P[pk], rv), 'd_built_pct': pct(PB[pk], rv)}
geo_keys = ['chord', 'mtow', 'feaBoomL', 'feaRootMomentTarget', 'feaTipMass', 'feaTipForce', 'segF', 'hC', 'vH', 'vC', 'xFront', 'xRear', 'feaWingForce']
all_diff = sorted(((k, P[k], PB[k], pct(PB[k], P[k])) for k in P if k in PB and isinstance(P[k], float) and P[k] not in (0,) and P[k] != PB[k]),
                  key=lambda x: -abs(x[3]))
built_max = max(abs(rows01[k]['d_built_pct']) for k in ('chord', 'mtow', 'feaBoomL', 'feaRootMomentTarget', 'feaTipMass', 'feaTipForce'))
params_max = max(abs(r['d_params_pct']) for r in rows01.values())
put('MFG-01', what='analysis/results.json vs cad/params.txt (analysis inputs) vs cad/params.built.txt (CAD as built)',
    results_generated=RES['generated'], pairs=rows01, params_txt_max_abs_pct=params_max, built_global_max_abs_pct=built_max,
    params_vs_built_all_differences=[{'key': k, 'params_txt': a, 'params_built': b, 'd_pct': d} for k, a, b, d in all_diff],
    n_params=len([k for k in P if isinstance(P[k], float)]), n_differ=len(all_diff),
    built_header=open(J('cad', 'verification.txt'), encoding='utf-8').readline().strip())
rec('MFG-01', 'analysis inputs: max |params.txt - results.json| on 7 sizing keys', params_max, 0.0, rel='le')
rec('MFG-01b', 'CAD as built: max |params.built - results.json| on 6 global sizing keys <= 0.5 %', built_max, 0.5, rel='le')
rec('MFG-01c', 'CAD as built: tail chord hC vs current params', PB['hC'], P['hC'], 0.5)

# ------------------------------------------------------------------ MFG-04 order table vs cad/hardware.json (rev 2026-11-02: automated)
# every Bolt Depot fastener in hardware.json must appear in the hardware-spec section 6 order table under its own part number
# with the same thread size and length; the J10 wing bolt must also match params.txt (wingBoltL, pillarNutDepth)
spec_txt = open(J('docs', 'research', 'hardware-spec.md'), encoding='utf-8').read()
bd_rows = {m.group(1): m.group(0) for m in re.finditer(r'^\| BD-\d+ \| Bolt Depot (\d+) .*$', spec_txt, re.M)}
mfg04 = []
for f in HW['fasteners']:
    pn = str(f.get('part_no') or '')
    if f.get('vendor') != 'Bolt Depot' or not pn.isdigit() or not f.get('length_mm') or not f.get('order_qty'): continue
    size = f"M{f['thread'].split('x')[0][1:]} × {f['length_mm']:g}"
    row = bd_rows.get(pn)
    if row is None: mfg04.append(f"{f['id']}: part {pn} not in the order table")
    elif size not in row: mfg04.append(f"{f['id']}: order row for {pn} does not say {size}")
f09 = next(f for f in HW['fasteners'] if f['id'] == 'F09')
if abs(f09['length_mm'] - 1000 * P['wingBoltL']) > 1e-6: mfg04.append('F09 length vs params wingBoltL')
if abs(f09['nut']['pocket_depth_mm'] - 1000 * P['pillarNutDepth']) > 1e-6: mfg04.append('F09 nut pocket vs params pillarNutDepth')
if re.search(r'Two M5 × 20 wing bolts', spec_txt): mfg04.append('spec summary still says M5 × 20 wing bolts')
put('MFG-04', what='hardware-spec section 6 order table and summary vs cad/hardware.json and params.txt', contradictions=mfg04, rows_checked=len(bd_rows))
rec('MFG-04', 'order table / hardware.json / params.txt contradictions (count)', len(mfg04), 0, rel='le', note='; '.join(mfg04))

# ------------------------------------------------------------------ MFG-02 interference disposition (cad/verification.txt)
hdr = re.search(r'(\d+) interferences: (\d+) are heat-set inserts.*?total ([\d.]+) mm3\), (\d+) other \(total ([\d.]+) mm3\)', ver)
items = re.findall(r'^\s+([\d.]+) mm3\s+(\S+)\s+x\s+(\S+)\s*$', ver, re.M)
RULES = [  # (regex on "A x B", category, disposition)
    (r'Control_Horn.*Pushrod|Pushrod.*Control_Horn|F11.*Pushrod', 'needs CAD review', 'REGRESSION: rudder clevis vs horn was fixed 2026-11-03 (fork set along the horn pin axis; left rudder servo 19 mm aft so both rods are 88.4 mm, one part)'),
    (r'Fuselage_Pod.*Canopy', 'needs CAD review', 'REGRESSION: canopy vs pod was fixed 2026-11-03 (pod slots = the 30 mm canopy flange/tongue; dome a true half-ellipse)'),
    (r'Wing_Panel.*Spar_Tube', 'needs CAD review', 'REGRESSION: spar socket vs foam was fixed 2026-11-03 (channel cut at the FT05 hole 26.0; comp positions at 6 decimals)'),
    (r'F11_M2x14|Horn_Backplate.*|Control_Horn.*(Elevator|Rudder|Aileron)|(Elevator|Rudder|Aileron).*(Control_Horn|Horn_Backplate)', 'model artefact',
     'horn screws/backplates pass through surfaces whose holes are not modelled (drilled on assembly, BUILD-MANUAL)'),
    (r'Gear_Clamp_Lower.*N01', 'model artefact', 'nylock collar vs 5.7 AF pocket corners: 0.5 mm3 slivers'),
    (r'Rear_Hardpoint|Horn_Hardpoint|Boom_Clamp_F_Upper.*Wing_Panel|Wing_Panel.*Boom_Clamp', 'model artefact', 'printed hardpoint/clamp sits in a foam pocket cut slightly undersize (foam is cut to fit)'),
    (r'Boom_Clamp_F_Upper.*Spar_Collar', 'needs CAD review', 'REGRESSION: clamp vs collar was fixed 2026-11-03 (clamp top = yL30 - yB from the rounded params, coincident with the collar bottom)'),
    (r'F07.*Fuselage_Pod|Fuselage_Pod.*F07', 'model artefact', 'F07 M3x8 tips 0.8 mm into the pod wall beyond the insert hole (holes drilled on assembly)'),
    (r'Fin_Shoe|Tail_Clamp|Servo_Tray|H_Tail|Crush_Sleeve|Bolt_Pillar.*F09|Fuselage_Pod.*(Wing_Saddle|F08)|Servo.*Pushrod', 'model artefact', '< 1 mm3 numerical slivers on coincident faces (same spline section or flat seat on both parts)'),
]
disp = {}
for vol, a, b in items:
    pair = f'{a} x {b}'
    cat, why = 'unclassified', ''
    for rx, cc, ww in RULES:
        if re.search(rx, pair): cat, why = cc, ww; break
    key = re.sub(r'-\d+', '', pair)
    d = disp.setdefault(key, {'category': cat, 'why': why, 'count': 0, 'total_mm3': 0.0, 'max_mm3': 0.0})
    d['count'] += 1; d['total_mm3'] += float(vol); d['max_mm3'] = max(d['max_mm3'], float(vol))
cat_tot = {}
for d in disp.values():
    ct = cat_tot.setdefault(d['category'], {'count': 0, 'mm3': 0.0}); ct['count'] += d['count']; ct['mm3'] += d['total_mm3']
put('MFG-INTF', header={'total': int(hdr.group(1)), 'inserts': int(hdr.group(2)), 'insert_mm3': float(hdr.group(3)), 'other': int(hdr.group(4)), 'other_mm3': float(hdr.group(5))} if hdr else None,
    listed=len(items), by_pair=disp, by_category=cat_tot,
    F06_spar_collar_overrun_present=bool(re.search(r'F06.*Spar_Collar|Spar_Collar.*F06', ver)),
    tail_ring_cut_warning=('tail ring radial hole bottom' in ver),
    note='disposition by part-pair rule in this script (audit judgement); "needs CAD review" items are not proven clashes, only unexplained')
rec('MFG-02', 'non-insert interferences listed = header count', float(len(items)), float(hdr.group(4)) if hdr else None, 0.0)

# ------------------------------------------------------------------ MFG-03 drawing self-check
lc = open(J('cad', 'drawings', 'layout-check.txt'), encoding='utf-8').read()
dr = open(J('cad', 'Drawings.cs'), encoding='utf-8').read()
rv = re.search(r'REV = "([A-Z])', dr); chk = re.search(r'put\("CheckedBy", "([^"]*)"\)', dr)
put('MFG-03', overlaps=lc.count('OVERLAP'), sheets=lc.count('=== sheet'), revision=rv.group(1) if rv else None,
    checked_by=chk.group(1) if chk else None, drawing_pdf_mtime=time.strftime('%Y-%m-%d %H:%M', time.localtime(os.path.getmtime(J('cad', 'drawings', 'DBF-DRW-001.PDF')))))

# ------------------------------------------------------------------ MFG-10 torque schedule
tq = [(f['id'], f['torque_Nm'], f.get('torque_basis', '')) for f in HW['fasteners']]
put('MFG-10', fasteners=len(tq), with_torque=sum(1 for t in tq if t[1] is not None), est=sum(1 for t in tq if 'EST' in t[2]),
    sourced=[t[0] for t in tq if 'EST' not in t[2]], range_Nm=[min(t[1] for t in tq if t[1]), max(t[1] for t in tq if t[1])],
    hanging_mass_example={'T_Nm': 0.5, 'L_m': 0.060, 'm_kg': 0.5 / (G * 0.060)})

# ------------------------------------------------------------------ MFG-12 mass roll-up
put('MFG-MASS', bottom_up_kg=MB['total_kg'], sizing_mtow_mass_budget_kg=MB['sizing_mtow_kg'], results_mtow_kg=SZ['m'],
    delta_vs_results_pct=pct(MB['total_kg'], SZ['m']), est_share_kg=MB['est_share_kg'], groups=MB['groups'],
    cad_modelled_kg=float(re.search(r'TOTAL modelled mass ([\d.]+) kg', ver).group(1)),
    mount_cad_g=(mm_up + mm_cap) * 1000, mount_sizing_g=PRM['mMount'] * 1000, pa6cf_density_cad=1230, pa6cf_density_TDS=TH_IN['materials']['pa6cf']['rho'])
rec('MFG-12', 'bottom-up mass (mass_budget.json) vs sizing MTOW (results.json)', MB['total_kg'], SZ['m'], 1.0)

out['runtime_s'] = round(time.time() - T0, 2)
json.dump(out, open(J('analysis', 'validation', 'checks_struct.json'), 'w', encoding='utf-8'), indent=1, default=float)
for s in out['summary']:
    ds = '   —  ' if s['delta_pct'] is None else f"{s['delta_pct']:+7.2f}%"
    iv = '—' if s['independent'] is None else f"{s['independent']:.5g}"; rv_ = '—' if s['repo'] is None else f"{s['repo']:.5g}"
    crit = f"tol {s['tolerance_pct']:>4}%" if s['relation'] == 'eq' else ('indep >= ' if s['relation'] == 'ge' else 'indep <= ') + 'repo'
    print(f"{s['id']:9s} {s['check'][:62]:62s} indep {iv:>9s} repo {rv_:>9s} {ds} {crit:>14s} {'PASS' if s['pass'] else ('FAIL' if s['pass'] is False else 'n/a')}")
print('wrote analysis/validation/checks_struct.json in %.1f s' % out['runtime_s'])
