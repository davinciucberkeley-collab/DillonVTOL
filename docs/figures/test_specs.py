"""Figure definitions for the test plan (t_<test id>), same Scene API and conventions as step_specs.py.
Set-ups follow the test plan's Setup/Procedure text; the caption is the test's own Pass line (annotate_steps.py)."""
import mathutils
from step_specs import UNIT, b_5_2, b_9_10, b_11_4


def _rs():
    return __import__('render_scenes')


def _coupon(S, loc=(0, 0, 0), name='coupon'):
    RS = _rs()
    S.box(name, (loc[0], loc[1], loc[2] + 0.004), (0.12, 0.05, 0.008), RS.mat('PETG grey', (0.55, 0.57, 0.6), 0.5))
    for i, (x, r) in enumerate(((-0.045, 0.0017), (-0.03, 0.0018), (-0.012, 0.0019), (0.0, 0.002), (0.014, 0.00205))):
        S.cyl(f'{name} hole{i}', (loc[0] + x, loc[1] - 0.01, loc[2] + 0.0075), (loc[0] + x, loc[1] - 0.01, loc[2] + 0.0085), r, RS.mat('hole', (0.04, 0.04, 0.04), 0.9), 20)
    S.cyl(f'{name} ring', (loc[0] + 0.04, loc[1] + 0.005, loc[2] + 0.0075), (loc[0] + 0.04, loc[1] + 0.005, loc[2] + 0.0085), 0.0128, RS.mat('hole', (0.04, 0.04, 0.04), 0.9), 48)


# ------------------------------------------------------------ components (C)
def t_c01(S):
    _coupon(S); S.calipers('calipers', (0.02, -0.07, 0.0), 0)
    S.label('coupon hole1', 'M3 clearance holes 3.4 / 3.6 mm'); S.label('coupon hole3', 'Insert holes 3.8 to 4.1 mm')
    S.label('coupon ring', 'Bore rings 25.5 to 25.7 mm and the 22.4 mm joiner bore'); S.label('calipers', 'Measure every hole at two diameters')
    S.view(25, 45, fit=['coupon', 'calipers'], lens=55, margin=1.3)


def t_c02(S):
    RS = _rs(); Z = 0.3                                                  # coupon clamped on a block so the jug hangs clear
    S.box('block', (-0.02, 0, Z / 2), (0.08, 0.06, Z), RS.mat('block', (0.72, 0.56, 0.36), 0.6)); _coupon(S, (0, 0, Z))
    S.cyl('screw', (0.0, -0.01, Z + 0.008), (0.0, -0.01, Z + 0.03), 0.0015, RS.mat('steel', (0.62, 0.63, 0.65), 0.3, metal=1.0), 12)
    S.box('hex key', (0.05, -0.01, Z + 0.033), (0.1, 0.004, 0.004), RS.mat('hex key', (0.15, 0.15, 0.16), 0.3, metal=0.8)); S.weight('jug', (0.1, -0.01, Z + 0.033), 1.0, w=0.07)
    S.label('screw', 'M3 x 12 screw and washer, bottomed in the insert'); S.label('hex key', 'Hex key held level: arm L = 100 mm')
    S.label('jug', 'Add 0.1 kg every 10 s until the insert turns (T = m g L)')
    S.view(30, 22, fit=['coupon', 'jug', 'hex key'], lens=50, margin=1.2)


def t_c03(S):
    RS = _rs(); wood = RS.mat('2x4', (0.72, 0.56, 0.36), 0.6)
    S.box('beam', (0.4, 0, 0.2), (1.2, 0.09, 0.04), wood); S.box('pivot block', (0.0, 0, 0.09), (0.09, 0.09, 0.18), wood)
    _coupon(S, (-0.2, 0, 0.0)); S.cyl('wire loop', (-0.2, -0.01, 0.01), (-0.2, -0.01, 0.18), 0.0012, RS.mat('wire', (0.6, 0.6, 0.62), 0.3, metal=1.0), 8)
    S.weight('jugs', (0.95, 0, 0.18), 3.0)
    S.label('pivot block', 'Pivot 0.2 m from the end: 5:1 lever'); S.label('coupon', 'Coupon clamped under the short end, screw hooked to the beam')
    S.label('jugs', '1 kg steps (49 N at the insert) every 15 s'); S.view(15, 26, lens=35)


def t_c04(S):
    RS = _rs(); _coupon(S)
    S.box('nut plate', (0.0, -0.01, -0.002), (0.03, 0.03, 0.004), RS.mat('aluminium', (0.8, 0.81, 0.83), 0.3, metal=1.0))
    S.torque_driver('driver', (0.0, -0.01, 0.0085)); S.stripe('witness', (0.004, -0.01, 0.0087), (0.006, 0.0015, 0.0003), (0.9, 0.1, 0.1))
    S.label('driver', 'Torque M3 x 8 to 0.6 N·m through the 4.5 mm floor'); S.label('witness', 'Paint mark: re-check after 24 h and after 60 °C')
    S.view(35, 30, fit=['coupon', 'driver'], lens=55, margin=1.3)


def t_c05(S):
    S.tube('socket', (-0.45, 0, 0.0127), (0.1, 0, 0.0127)); S.tube('joiner', (0.0, 0, 0.0127), (0.76, 0, 0.0127), od=0.0222)
    S.vise('vise', (-0.3, 0, -0.08)); S.calipers('calipers', (0.3, -0.08, 0.0))
    S.mark('tip', (0.76, 0, 0.026)); S.label('tip', 'Lever the free end at 0.76 m; read the play with a ruler')
    S.label('calipers', 'OD at 3 points, wall at both ends'); S.label('vise', 'One socket clamped'); S.view(25, 25, lens=35)


def t_c07(S):
    b_11_4(S); S.labels.clear(); S.ir_thermometer('ir', (0.2, -0.25, 0.42), (1, 0.5, 0))
    S.label('Lift_Motor-1', 'Every motor: throttle 20 to 100 % in 10 % steps, 5 s each'); S.label('ir', 'IR temperature of the can after the sweep')


def t_c08(S):
    t_c07(S); S.labels.clear()
    S.label('Lift_Motor-1', 'Hold hover thrust (1,638 g) for 90 s'); S.label('ir', 'Can and ESC temperature every 15 s')


def t_c09(S):
    RS = _rs(); alu = RS.mat('6061 aluminium', (0.80, 0.81, 0.83), 0.28, metal=1.0)
    S.part('Pusher_Motor', (0, 0, 0.42), (0, 90, 0), accent=True); S.part('Pusher_Adapter', (0.03, 0, 0.42), (0, 90, 0), sit=False)
    S.part('Pusher_Prop_14in', (0.045, 0, 0.42), (0, 90, 0), sit=False)
    S.box('beam', (-0.25, 0, 0.405), (0.56, 0.025, 0.025), alu); S.box('post', (-0.25, 0, 0.2), (0.04, 0.04, 0.38), alu)
    S.label('Pusher_Motor', 'Pusher X4110S with APC 14 x 8.5EP on the stand adapter'); S.label('beam', 'Thrust read through the C06 stand'); S.view(40, 20, lens=40)


def t_c11(S):
    RS = _rs(); S.battery('pack', (0, 0, 0)); S.box('charger', (-0.25, 0.05, 0.04), (0.18, 0.14, 0.08), RS.mat('charger', (0.12, 0.12, 0.13), 0.4))
    S.box('watt meter', (0.17, 0.0, 0.01), (0.07, 0.04, 0.02), RS.mat('watt meter', (0.12, 0.12, 0.13), 0.4)); S.ir_thermometer('ir', (0.1, -0.2, 0.15), (-0.4, 1, -0.4))
    S.wire('lead', [(0.08, 0, 0.03), (0.12, 0, 0.03), (0.15, 0, 0.02)])
    S.label('charger', 'Full charge, then the balance readout at rest'); S.label('watt meter', 'Discharge at 15 A: log Wh, Ah and V every 30 s')
    S.label('ir', 'Pack temperature by IR'); S.view(25, 35, lens=45)


def t_c12(S):
    RS = _rs(); S.part('Servo', (0, 0, 0.3), (0, 0, 0), accent=True)       # on a block tall enough for the jug to hang clear
    S.box('block', (0, 0, 0.15), (0.06, 0.04, 0.3), RS.mat('block', (0.72, 0.56, 0.36), 0.6))
    S.box('arm', (0.025, 0, 0.342), (0.05, 0.006, 0.003), RS.mat('servo arm', (0.9, 0.9, 0.9), 0.5)); S.weight('jug', (0.05, 0, 0.342), 1.6, w=0.045)
    S.label('arm', '50 mm arm, centred at 1500 µs'); S.label('jug', 'Masses until the arm stalls (1.6 kg = 8 kg·cm); 2 s maximum'); S.view(30, 24, lens=50, margin=1.45)


def t_c13(S):
    S.assembly(focus=[], context=['*'], lift=0.0); S.ir_thermometer('ir', (0.7, -0.6, 0.35), (-1, 1, -0.4))
    S.label('ir', 'During the tied-down run (G03): IR on each connector, ESC and the pack lead')
    S.label('Fuselage_Pod-1', 'Connectors and the FC current sensor in the pod'); S.view(40, 30, lens=40)


def t_c14(S):
    b_5_2(S)


def t_c15(S):
    RS = _rs(); S.part('Lift_Prop', (0, 0, 0.11)); S.cyl('bolt', (0, -0.08, 0.11), (0, 0.08, 0.11), 0.003, RS.mat('steel', (0.62, 0.63, 0.65), 0.3, metal=1.0))
    for k, y in enumerate((-0.06, 0.06)): S.cyl(f'glass{k}', (0, y, 0.0), (0, y, 0.1), 0.03, RS.mat('glass', (0.85, 0.9, 0.95), 0.05, alpha=0.4))
    S.label('Lift_Prop', 'Prop on a bolt between two glasses: it must not settle heavy-side down'); S.label('bolt', 'Calipers on the hub bore first'); S.view(15, 15, lens=50)


def t_c16(S):
    S.assembly(focus=['Landing_Leg-1', 'F05_M3x30_SHCS*', 'N01_M3_Nylock*'], context=['Gear_Clamp_Upper-1', 'Gear_Clamp_Lower-1'], lift=0.02)
    S.label('Landing_Leg-1', '205 mm leg offcut in the gear-clamp socket'); S.label('Gear_Clamp_Upper-1', 'F05 M3 x 30 cross-bolt: clears the tube, 0.5 N·m')
    S.view(30, 20, fit=['Gear_Clamp_Upper-1', 'Gear_Clamp_Lower-1'], lens=50, margin=2.4)


def t_c17(S):
    S.assembly(focus=['Wing_Joiner-1'], context=['Wing_Saddle-1', 'Joiner_Stop*', 'Spar_Tube*'], ghost=['Wing_Panel_L', 'Wing_Panel_R'], lift=0.02)
    S.label('Wing_Joiner-1', 'Joiner slid through the saddle into both sockets by hand'); S.label('Joiner_Stop-1', 'Joiner stops: push from each tip, they must hold')
    S.view(20, 35, fit=['Wing_Panel_L-1', 'Wing_Panel_R-1'], lens=40)


# ------------------------------------------------------------ structure (S)
def t_s02(S):
    S.assembly(focus=['Boom_Front-1', 'Boom_Rear_Stub-1'], context=['Boom_Clamp_F_Upper-1', 'Boom_Clamp_F_Lower-1', 'Boom_Clamp_R_Upper-1', 'Boom_Clamp_R_Lower-1'] + UNIT(1)[:3], lift=0.5)
    z = S.at('Motor_Mount_Cap-1', 'bottom').z; S.weight('jug', (0.391, -0.4337, z), 3.0); S.dial_gauge('gauge', (0.391, -0.36, z - 0.42))
    S.label('jug', 'Hang 1, 2 and 3 kg at the front motor station (arm 0.462 m)'); S.label('gauge', 'Deflection at the motor station each step')
    S.label('Boom_Clamp_F_Upper-1', 'Boom held in its real wing clamps'); S.view(30, 22, fit=['Boom_Front-1', 'jug'], lens=40)


def t_s03(S):
    S.assembly(focus=[], context=['*'], lift=0.0); z = S.at('Motor_Mount_Upper-1', 'top').z
    S.phone('phone', (0.391, -0.4337 - 0.03, z + 0.01), (90, 0, 0))
    S.label('phone', 'Phone taped to the motor mount: accelerometer app logging'); S.label('Lift_Motor-1', 'Tap the motor 10 times, vertical then lateral; first FFT peak')
    S.view(40, 25, fit=['Boom_Front-1'], lens=40)


def t_s04(S):
    RS = _rs()
    S.assembly(focus=['Motor_Mount_Upper-1', 'Motor_Mount_Cap-1'], context=['Boom_Front-1', 'Boom_Rear_Stub-1', 'Boom_Clamp_F_Upper-1', 'Boom_Clamp_F_Lower-1', 'Boom_Clamp_R_Upper-1', 'Boom_Clamp_R_Lower-1'], lift=0.5)
    z = S.at('Motor_Mount_Cap-1', 'bottom').z
    S.box('lever', (0.391, -0.4337 - 0.125, z), (0.02, 0.25, 0.01), RS.mat('lever', (0.72, 0.56, 0.36), 0.6)); S.weight('jug', (0.391, -0.4337 - 0.25, z), 2.0)
    S.stripe('witness', (0.391, -0.4337, S.at('Motor_Mount_Upper-1', 'top').z + 0.001), (0.004, 0.06, 0.0004), (0.9, 0.1, 0.1))
    S.label('jug', '2 kg on a 0.25 m lever: 4.9 N·m about the boom'); S.label('witness', 'Paint witness line across clamp and tube must not break')
    S.view(35, 25, fit=['Motor_Mount_Upper-1', 'jug', 'lever'], lens=45, margin=1.3)


def t_s05(S):
    S.assembly(focus=['Lift_Motor-1', 'Motor_Mount_Upper-1'], context=['Motor_Mount_Cap-1', 'Boom_Front-1'], lift=0.5)
    S.weight('jug', tuple(S.at('Motor_Mount_Cap-1', 'bottom')), 5.0)
    S.label('jug', 'Hang 6.26 kg (2 x max thrust) from the bell for 60 s'); S.label('Motor_Mount_Upper-1', 'Motor screws from inside the bore, 0.6 N·m with Loctite 242')
    S.view(30, 20, fit=['Motor_Mount_Upper-1', 'jug'], lens=45, margin=1.3)


def t_s06(S):
    RS = _rs(); S.assembly(focus=[], context=['*'], lift=0.30)
    S.box('tape measure', (0.62, -0.62, 0.15), (0.02, 0.02, 0.30), RS.mat('tape measure', (0.95, 0.8, 0.1), 0.4))
    S.label('tape measure', 'Lift to 0.30 m under the feet, release level'); S.label('Landing_Leg-1', 'Inspect legs, clamps, fairings and the ballast mount after each drop')
    S.view(35, 18, lens=38)


def t_s07(S):
    S.assembly(focus=['Aileron_L-1'], context=['Wing_Panel_L-1', 'Horn_Hardpoint-2', 'Control_Horn-4'], lift=0.3)
    S.weight('jug', tuple(S.at('Aileron_L-1', 'end-x')), 0.3)
    S.label('jug', 'Jug on a string at 25 % of the aileron chord; servo holds 20°'); S.label('Aileron_L-1', 'Then inspect the joiner and spar for marks')
    S.view(25, 25, fit=['Aileron_L-1', 'jug'], lens=45)


def t_s08(S):
    RS = _rs()
    S.box('load space', (0, 0, 0.2), (1.5, 0.5, 0.4), RS.mat('car space', (0.3, 0.55, 0.9), 0.3, alpha=0.12), 0)
    S.part('Wing_Panel_L', (0.0, -0.13, 0.0), (0, 0, 90), name='wing panel L'); S.part('Wing_Panel_R', (0.0, -0.13, 0.06), (0, 0, 90), name='wing panel R')
    S.part('Fuselage_Pod', (0.05, 0.13, 0.0), (0, 0, 0), name='pod')
    S.label('load space', 'Measured car load space (R4 envelope 1.5 x 0.5 x 0.4 m, estimate)'); S.label('wing panel L', 'Wing panels off the saddle; joiner slid out')
    S.label('pod', 'Pod piece with the saddle'); S.view(30, 35, lens=38)


def t_s09(S):
    S.part('Motor_Mount_Upper', (0, 0, 0.032), accent=True); S.kitchen_scale('scale', (0, 0, 0))
    S.label('scale', 'Every part on the 5 kg / 1 g scale'); S.label('Motor_Mount_Upper', 'Log against the CAD mass roll-up'); S.view(30, 30, lens=60, fit=['scale'], margin=1.6)


def t_s10(S):
    RS = _rs(); S.assembly(focus=[], context=['Battery_Tray-1', 'Battery_6S_LiPo-1'], ghost=['Fuselage_Pod-1', 'Canopy-1'], lift=0.3)
    S.box('ballast', (0.15, 0, S.at('Battery_Tray-1', 'top').z + 0.02), (0.08, 0.05, 0.035), RS.mat('ballast', (0.35, 0.33, 0.3), 0.7))
    S.weight('jug', (0.15, 0, S.at('Fuselage_Pod-1', 'bottom').z), 5.0)
    S.label('ballast', '0.500 kg ballast on its strap at x = +0.15 m'); S.label('jug', 'Static pull of 8 kg down, forward and sideways; no movement')
    S.view(25, 20, fit=['Fuselage_Pod-1', 'jug'], lens=40)


# ------------------------------------------------------------ electrical and ground (E, G)
def t_e01(S):
    RS = _rs(); b_9_10(S); S.labels.clear()
    S.box('multimeter', (0.3, 0.45, 0.02), (0.08, 0.15, 0.03), RS.mat('multimeter', (0.95, 0.75, 0.1), 0.4))
    S.label('watt meter', 'Power through the watt meter: watch 60 s for heat or smoke'); S.label('multimeter', 'Continuity and polarity first; then pack voltage vs the FC reading')


def t_e08(S):
    S.assembly(focus=['Pitot_Tube-1'], context=['Pitot_Clamp-1', 'Wing_Panel_L-1'], lift=0.3)
    S.label('Pitot_Tube-1', 'Blow gently into the pitot: airspeed rises; baro and airspeed both detected')
    S.view(35, 25, fit=['Pitot_Tube-1', 'Pitot_Clamp-1'], lens=45, margin=1.8)


def t_e12(S):
    S.assembly(focus=[], context=['Fuselage_Pod-1', 'Canopy-1'], lift=0.0); S.phone('phone', (0.55, -0.35, 0.15), (75, 0, 30))
    S.label('phone', 'Remote ID receiver app shows the BeeID serial and position'); S.label('Canopy-1', 'BeeID module powered from the FC 5 V pad'); S.view(30, 30, lens=45)


def t_g03(S):
    RS = _rs(); S.assembly(focus=[], context=['*'], lift=0.0)
    for k, (x, y) in enumerate(((0.301, -0.4337), (-0.46, -0.4337), (0.301, 0.4337), (-0.46, 0.4337))):
        S.cyl(f'stake{k}', (x + 0.25, y * 1.6, -0.1), (x + 0.25, y * 1.6, 0.12), 0.008, RS.mat('stake', (0.5, 0.5, 0.52), 0.35, metal=1.0), 12)
        S.wire(f'tie{k}', [(x, y, 0.06), (x + 0.12, y * 1.3, 0.08), (x + 0.25, y * 1.6, 0.1)], (0.85, 0.45, 0.1), 0.003)
    S.label('stake0', 'Four ties of 50 kg or more from the leg clamps to stakes'); S.label('Lift_Prop-1', 'Props on; everyone 5 m away behind a barrier'); S.view(35, 30, lens=38)


def t_e09(S):
    t_g03(S)


def t_g06(S):
    RS = _rs(); S.assembly(focus=['Pusher_Prop_14in-1', 'Pusher_Motor-1'], context=['*'], lift=0.0)
    S.cyl('stake', (-1.3, 0, -0.1), (-1.3, 0, 0.12), 0.008, RS.mat('stake', (0.5, 0.5, 0.52), 0.35, metal=1.0), 12)
    S.wire('tether', [(-0.6, 0, 0.1), (-0.95, 0, 0.1), (-1.3, 0, 0.1)], (0.85, 0.45, 0.1), 0.003)
    S.box('scale', (-0.95, 0, 0.1), (0.03, 0.03, 0.1), RS.mat('luggage scale', (0.15, 0.32, 0.75), 0.4))
    S.label('scale', 'Tail tied to a stake through the scale; nose free to pull'); S.label('Pusher_Motor-1', '60 % and 100 % for 10 s each; IR on the can and ESC'); S.view(30, 25, lens=38)


def t_g07(S):
    S.assembly(focus=['Wing_Panel_L', 'Wing_Panel_R', 'Wing_Joiner', 'H_Tail', 'Elevator', 'Fin', 'Rudder'], context=['*'], lift=0.0)
    S.label('Wing_Panel_L-1', 'Slide the joiner in, bolt both panels (C17)'); S.label('H_Tail-1', 'Tail unit on the stubs: 4 screws')
    S.label('Boom_Front-1', 'Booms: 4 screws each; stopwatch from car to armed'); S.view(35, 30, lens=38)


def t_g09(S):
    RS = _rs(); S.assembly(focus=['Battery_6S_LiPo-1'], context=['Battery_Tray-1'], ghost=['Fuselage_Pod-1', 'Canopy-1'], lift=0.06)
    S.box('ballast', (0.15, 0, S.at('Battery_Tray-1', 'top').z + 0.02), (0.08, 0.05, 0.035), RS.mat('ballast', (0.35, 0.33, 0.3), 0.7))
    S.label('ballast', 'Weigh with and without the 0.5 kg ballast, and with it moved ± 30 mm'); S.label('Battery_6S_LiPo-1', 'Record the pack station for each case')
    S.view(25, 25, fit=['Fuselage_Pod-1'], lens=45)


SPECS = {k: v for k, v in dict(globals()).items() if k.startswith('t_') and callable(v)}
