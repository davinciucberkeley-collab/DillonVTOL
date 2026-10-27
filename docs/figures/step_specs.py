"""Figure definitions for the build manual (b_<step>) and the test plan (t_<test id>).
Each function builds one scene with the figkit Scene API; the caption comes from the document itself
(annotate_steps.py reads the step's title and Check line, or the test's Pass line), so pictures and text agree.
Aircraft frame in these scenes (Blender): +X forward, +Z up, the aircraft's right side towards -Y.
Right-side instances are -1 (front unit) / -2 (rear unit), left-side -3 / -4 (cad/params.txt order)."""
import math

AL = 0.0254          # 1 in boom tube OD
R_FRONT, R_REAR = (0.391, -0.4337), (-0.550, -0.4337)        # right lift units (x, y) in the scene frame

UNIT = lambda k: [f'Lift_Motor-{k}', f'Motor_Mount_Upper-{k}', f'Motor_Mount_Cap-{k}', f'Prop_Plate-{k}', f'Lift_Prop-{k}']
WING = ['Wing_Panel_L', 'Wing_Panel_R', 'Aileron_L', 'Aileron_R', 'Wing_Saddle', 'Spar_Tube', 'Wing_Joiner', 'Joiner_Stop', 'Root_Tongue', 'Bolt_Pillar', 'Spar_Collar', 'Rear_Hardpoint', 'Horn_Hardpoint']
TAIL = ['H_Tail', 'Elevator', 'Fin', 'Rudder', 'Fin_Shoe', 'Crush_Sleeve']
BOOMS = ['Boom_Front', 'Boom_Rear_Stub', 'Splice_Plug', 'Motor_Mount_Upper', 'Motor_Mount_Cap', 'Lift_Motor', 'Gear_Clamp_Upper', 'Gear_Clamp_Lower']


# ============================================================ WP1 receiving
def b_1_1(S):
    S.part('Lift_Motor', (-0.45, 0.1, 0.004)); S.part('Lift_Motor', (-0.36, 0.1, 0.004), name='motor 2'); S.part('Pusher_Motor', (-0.27, 0.1, 0.004))
    S.part('Lift_Prop', (-0.1, 0.25, 0.004), (0, 0, 20)); S.part('Pusher_Prop_14in', (0.25, 0.28, 0.004), (90, 0, 0))
    for i in range(3): S.esc(f'esc{i}', (-0.45 + 0.08 * i, -0.08, 0.01))
    for i in range(3): S.part('Servo', (-0.12 + 0.06 * i, -0.06, 0.004), name=f'servo{i}')
    S.part('Flight_Controller', (0.12, -0.05, 0.004)); S.battery('pack1', (0.38, -0.1, 0.004)); S.battery('pack2', (0.38, 0.0, 0.004))
    S.tube('boom stock', (-0.7, -0.3, 0.017), (0.7, -0.3, 0.017))
    S.label('Lift_Motor', 'Motors: count 6, spin each by hand'); S.label('esc0', 'ESCs: 8, check the labels'); S.label('servo1', 'Servos: 5')
    S.label('Flight_Controller', 'Flight controller and its box contents'); S.label('pack2', 'Two 6S packs: voltage first'); S.label('boom stock', 'Tubes: measure in 1.3')
    S.view(15, 52, lens=40)


def b_1_3(S):
    S.tube('tube', (-0.25, 0, 0.0127), (0.25, 0, 0.0127)); S.calipers('calipers', (0.27, -0.02, 0.0))
    S.mark('od', (0.25, 0, 0.026)); S.mark('jaws', (0.18, -0.03, 0.01))
    S.label('od', 'Outside diameter at both ends and the middle'); S.label('jaws', 'Calipers zeroed; also wall thickness at the cut end')
    S.view(30, 32, fit=['calipers', 'od'], lens=50, margin=1.5)


def b_1_4(S):
    S.tube('socket', (-0.35, 0, 0.0127), (0.1, 0, 0.0127)); S.tube('joiner', (0.02, 0, 0.0127), (0.4, 0, 0.0127), od=0.0222, material=None)
    S.mark('fit', (0.08, 0, 0.026)); S.label('fit', 'Joiner slides into the socket tube by hand; no rock, no forcing')
    S.view(28, 26, fit=['fit'], lens=50, margin=3.5)


def b_1_5(S):
    S.part('Lift_Motor', (0, 0, 0.004), accent=True); S.label('Lift_Motor', 'Spin the bell: smooth, no rub, no play; shaft straight')
    S.mark('wires', S.at('Lift_Motor', 'front')); S.label('wires', 'Three phase leads intact; record the label (KV, batch)')
    S.view(35, 28, lens=60, margin=1.25)


def b_1_6(S):
    S.part('Lift_Prop', (0, 0, 0.11), (0, 0, 0)); S.cyl('balancer shaft', (0, -0.04, 0.11), (0, 0.04, 0.11), 0.0025, None or __import__('render_scenes').mat('steel', (0.62, 0.63, 0.65), 0.3, metal=1.0))
    S.box('balancer', (0, 0, 0.05), (0.04, 0.12, 0.1), __import__('render_scenes').mat('balancer', (0.2, 0.2, 0.22), 0.4))
    S.label('Lift_Prop', 'Prop on the balancer: blade stays level, no heavy side'); S.mark('hub', (0, 0, 0.125)); S.label('hub', 'Hub bore and blade roots: no cracks')
    S.view(20, 15, lens=50)


def b_1_7(S):
    S.esc('esc', (-0.15, 0, 0.01)); S.part('Servo', (0.0, 0, 0.004)); S.part('Flight_Controller', (0.15, 0, 0.004)); S.psu('supply', (0.3, 0.35, 0.0))
    S.label('esc', 'ESC: note firmware and the label'); S.label('Servo', 'Servo: centres and sweeps on a tester'); S.label('Flight_Controller', 'Flight controller: USB power, boots, LEDs')
    S.view(10, 40, lens=45, fit=['esc', 'Servo', 'Flight_Controller'], margin=1.6)


def b_1_8(S):
    S.battery('pack', (0, 0, 0.004)); S.box('checker', (0.12, 0.0, 0.012), (0.05, 0.03, 0.02), __import__('render_scenes').mat('checker', (0.15, 0.15, 0.17), 0.4))
    S.label('pack', 'No swelling or damage; record the serial'); S.label('checker', 'Cell checker: every cell within 0.02 V; storage charge')
    S.view(30, 35, lens=60)


def b_1_9(S):
    S.foam('2 in sheet', (0, 0.05, 0.0254), (1.2, 0.6, 0.0508)); S.foam('1 in sheet', (0, 0.05, 0.0635), (1.0, 0.5, 0.0254))
    S.tape_roll('tape', (0.5, -0.32, 0.0)); S.tape_roll('tape2', (0.38, -0.34, 0.0), (0.8, 0.8, 0.85))
    S.label('2 in sheet', 'FOAMULAR 2 in (wing cores): flat, no dents'); S.label('1 in sheet', '1 in sheet (tail, pod)'); S.label('tape', 'Skin tape: count the rolls against the BOM')
    S.view(25, 40, lens=40)


# ============================================================ WP2 printing
def b_2_1(S):
    S.printer('printer', (0, 0, 0)); S.box('test cube', (0, 0, 0.078), (0.02, 0.02, 0.02), __import__('render_scenes').mat('PETG grey', (0.55, 0.57, 0.6), 0.5))
    S.label('test cube', 'Calibration cube: 20.0 ± 0.1 mm each way'); S.label('printer', 'Bed level and first layer checked; bed size recorded (M8)')
    S.view(30, 30, lens=45)


def b_2_2(S):
    S.printer('printer', (0, 0, 0))
    S.box('coupon', (0, 0, 0.072), (0.08, 0.04, 0.008), __import__('render_scenes').mat('PETG grey', (0.55, 0.57, 0.6), 0.5))
    for i, x in enumerate((-0.025, -0.008, 0.01, 0.027)):
        S.cyl(f'hole{i}', (x, 0, 0.0755), (x, 0, 0.0765), 0.0017 + 0.0004 * i, __import__('render_scenes').mat('hole', (0.05, 0.05, 0.05), 0.8))
    S.label('coupon', 'P27 coupon: holes for 3.4, 4.0, 22.46 and 25.6 mm features'); S.label('hole2', 'Measure each hole; adjust the model if off by more than 0.1 mm')
    S.view(25, 45, fit=['coupon', 'printer'], lens=55)


def b_2_3(S):
    RS = __import__('render_scenes')
    S.box('coupon', (0, 0, 0.004), (0.08, 0.04, 0.008), RS.mat('PETG grey', (0.55, 0.57, 0.6), 0.5))
    S.cyl('insert', (0.0, 0, 0.008), (0.0, 0, 0.0155), 0.0025, RS.mat('brass', (0.78, 0.6, 0.25), 0.3, metal=1.0), 16)
    S.soldering_iron('iron', (0.0, 0, 0.0158))
    S.label('insert', 'I01 insert pressed in square, flush to 0.1 mm'); S.label('iron', 'Iron at the insert temperature, light pressure, no tilt')
    S.view(35, 25, fit=['coupon', 'insert'], lens=70, margin=2.2)


def _bed_parts(S, items):
    """items: (part, x, y, rot) laid on the bed of a printer centred at the origin"""
    S.printer('printer', (0, 0, 0), 0.25)
    for k, (p, x, y, rot) in enumerate(items):
        S.part(p, (x, y, 0.068), rot, name=f'{p} {k}', accent=True)


def b_2_4(S):
    _bed_parts(S, [('Motor_Mount_Cap', -0.06, 0.05, (180, 0, 0)), ('Motor_Mount_Cap', 0.04, 0.05, (180, 0, 0)), ('Gear_Clamp_Upper', -0.06, -0.05, (180, 0, 0)), ('Gear_Clamp_Lower', 0.04, -0.06, (0, 0, 0))])
    S.label('Motor_Mount_Cap 0', 'P02 caps, flat face down'); S.label('Gear_Clamp_Upper 2', 'P07 gear clamps, split plane down')
    S.view(20, 50, fit=['printer'], lens=50)


def b_2_5(S):
    _bed_parts(S, [('Motor_Mount_Upper', -0.06, 0.06, (180, 0, 0)), ('Motor_Mount_Upper', 0.05, 0.06, (180, 0, 0)), ('Motor_Mount_Upper', -0.06, -0.05, (180, 0, 0)), ('Motor_Mount_Upper', 0.05, -0.05, (180, 0, 0)), ('Pusher_Cup', 0.0, 0.0, (0, 90, 0))])
    S.label('Motor_Mount_Upper 0', 'P01 motor mounts ×4, motor plate face down'); S.label('Pusher_Cup 4', 'P03 pusher cup, floor down')
    S.view(20, 50, fit=['printer'], lens=50)


def b_2_7(S):
    RS = __import__('render_scenes')
    S.part('Motor_Mount_Upper', (0, 0, 0.004), (180, 0, 0), accent=True)
    S.part('Lift_Motor', (0, 0, 0.04), (180, 0, 0), name='motor as jig')
    S.cyl('drill', (0.0125, 0, 0.0), (0.0125, 0, 0.12), 0.0017, RS.mat('drill bit', (0.3, 0.3, 0.32), 0.3, metal=1.0), 12)
    S.label('motor as jig', 'The motor itself locates the four holes (25 mm circle)'); S.label('drill', 'Drill 3.4 mm, then the 7.5 mm counterbore from the bore side')
    S.view(35, 30, lens=55, fit=['Motor_Mount_Upper', 'motor as jig'], margin=1.6)


def b_2_8(S):
    S.assembly(focus=['I01_M3_Insert-' + str(i) for i in range(1, 80)], context=UNIT(1)[1:3], lift=0.02)
    S.keep_near('I01_M3_Insert*', 'Motor_Mount_Upper-1', 0.05)
    S.label('Motor_Mount_Upper-1', 'Four inserts per motor-mount upper half'); S.label('Motor_Mount_Cap-1', 'Cap screws thread into them in 7.4')
    S.view(35, 30, fit=['Motor_Mount_Upper-1', 'Motor_Mount_Cap-1'], lens=50, margin=1.5)


# ============================================================ WP3 tubes
def b_3_1(S):
    for k, y in enumerate((-0.05, 0.05)):
        S.tube(f'stock{k}', (-0.914, y, 0.0127), (0.914, y, 0.0127))
    for k, x in enumerate((-0.914 + 0.991, -0.914 + 0.991 + 0.4859 + 0.0015)):
        S.stripe(f'cut{k}', (x, 0, 0.0256), (0.003, 0.14, 0.001), (0.9, 0.1, 0.1))
    S.label('cut0', 'Cut 1: 991.0 mm front boom (T01)'); S.label('cut1', 'Cut 2: 485.9 mm stub (T02); rest is offcut')
    S.view(10, 50, fit=['cut0', 'cut1'], lens=35, margin=1.5)    # close on the marks; the tube ends run out of frame


def b_3_2(S):
    RS = __import__('render_scenes')
    S.tube('stock', (-0.4, 0, 0.0127), (0.4, 0, 0.0127)); S.box('cutter body', (0.1, 0, 0.0127), (0.04, 0.06, 0.07), RS.mat('cutter', (0.75, 0.15, 0.1), 0.4))
    S.stripe('mark', (0.1, 0, 0.0258), (0.002, 0.03, 0.001), (0.9, 0.1, 0.1))
    S.label('mark', 'Cut on the mark; square within 0.5 mm'); S.label('cutter body', 'Tube cutter: a few turns per pass, no crushing')
    S.view(30, 30, lens=50, fit=['cutter body'], margin=3.0)


def b_3_3(S):
    # 96 in socket tube from the fresh end: 800, 800, then 205 x 4, 1.5 mm kerf per cut (BUILD-MANUAL 3.3)
    L = 2.4384; x0 = -L / 2; S.tube('socket stock', (x0, 0, 0.0127), (x0 + L, 0, 0.0127))
    x, cuts = x0, []
    for k, n in enumerate((0.800, 0.800, 0.205, 0.205, 0.205, 0.205)):
        x += n; cuts.append(x); S.stripe(f'cut{k}', (x, 0, 0.0256), (0.003, 0.08, 0.001), (0.9, 0.1, 0.1)); x += 0.0015
    S.label('cut0', 'T03: 800 mm, cut twice'); S.label('cut3', 'T04: 205 mm × 4'); S.mark('slack', (x0 + L - 0.004, 0, 0.026))
    S.label('slack', 'About 11 mm left over: re-square no more than 0.5 mm')
    S.view(0, 60, lens=35, margin=1.0)


def b_3_5(S):
    S.tube('front boom', (0.0, 0, 0.0127), (0.991, 0, 0.0127))
    for k, (x, lab) in enumerate(((0.050, 'motor mount centre, 50.0'), (0.140, 'front gear clamp, 140.0'), (0.5262, 'wing clamp station, 526.2'), (0.901, 'rear gear clamp, 901.0'))):
        S.stripe(f'st{k}', (x, 0, 0.0256), (0.0015, 0.03, 0.001), (0.05, 0.05, 0.05)); S.mark(f'm{k}', (x, 0, 0.026)); S.label(f'm{k}', lab + ' mm from the front end')
    S.stripe('topline', (0.4955, 0, 0.0257), (0.991, 0.0012, 0.0005), (0.1, 0.3, 0.8)); S.mark('tl', (0.7, 0, 0.026)); S.label('tl', 'Top line along the whole tube: every part clocks to it')
    S.view(0, 60, lens=35)


def b_3_6(S):
    RS = __import__('render_scenes')
    S.tube('joiner', (-0.38, 0, 0.0127), (0.38, 0, 0.0127), od=0.0222); S.box('sandpaper', (0.2, 0, 0.0127), (0.06, 0.03, 0.03), RS.mat('sandpaper', (0.8, 0.6, 0.35), 0.95))
    S.label('sandpaper', '400-grit around the joiner where it binds; refit often'); S.view(30, 30, lens=45, fit=['sandpaper'], margin=3.5)


def b_3_7(S):
    S.assembly(focus=['F04_M3x40_SHCS*', 'Splice_Plug-1'], context=['Boom_Front-1', 'Boom_Rear_Stub-1', 'Motor_Mount_Upper-2', 'Motor_Mount_Cap-2'], lift=0.02)
    S.label('Splice_Plug-1', 'Splice cross-holes are drilled later, in situ (WP7 step 7.6)'); S.view(30, 30, fit=['Motor_Mount_Upper-2', 'Motor_Mount_Cap-2'], lens=50, margin=2.0)


def b_3_8(S):
    S.assembly(focus=['F05_M3x30_SHCS*', 'Landing_Leg-1'], context=['Gear_Clamp_Upper-1', 'Gear_Clamp_Lower-1', 'Boom_Front-1'], lift=0.02)
    S.label('Landing_Leg-1', 'Leg cross-hole drilled later through the gear clamp (WP8 step 8.7)'); S.view(30, 30, fit=['Gear_Clamp_Upper-1', 'Gear_Clamp_Lower-1'], lens=50, margin=2.2)


# ============================================================ WP4 foam cores
def b_4_1(S):
    S.airfoil_plate('root template', (0.15, -0.1, 0.0), 0.2842); S.airfoil_plate('tip template', (0.15, 0.15, 0.0), 0.2842)
    for o in ('root template', 'tip template'): S.objs[o].location.z = 0.02
    S.label('root template', 'Root template: NACA 2415 at 1:1, glued to hardboard'); S.label('tip template', 'Tip template, same chord; check the scale bar')
    S.view(15, 25, lens=50)


def b_4_2(S):
    S.foam('sheet', (0, 0, 0.0254), (0.9, 0.35, 0.0508)); S.bow('bow', (0.0, -0.45, 0.06), (0.0, 0.45, 0.06), 0.4); S.psu('supply', (0.6, 0.3, 0.0))
    S.label('bow', '1.3 m bow, 0.4-0.5 mm nichrome, wire taut'); S.label('supply', 'Bench supply: start low, raise until it cuts cleanly')
    S.view(35, 25, lens=40)


def b_4_3(S):
    S.foam('scrap', (0, 0, 0.0254), (0.3, 0.3, 0.0508)); S.stripe('kerf', (0, 0, 0.0509), (0.3, 0.0015, 0.0005), (0.1, 0.1, 0.1))
    S.bow('bow', (0.0, -0.25, 0.03), (0.0, 0.25, 0.03), 0.25)
    S.label('kerf', 'Measure the kerf; it sets the template offset'); S.view(35, 35, lens=45)


def b_4_4(S):
    S.foam('sheet', (0, 0, 0.0254), (2.4384, 1.2192, 0.0508))
    for k, (x, w) in enumerate(((-0.6, 1.14), (0.62, 1.14))):
        S.stripe(f'blk{k}', (x, -0.3, 0.0509), (w, 0.0015, 0.0005)); S.stripe(f'blk{k}b', (x, 0.0042, 0.0509), (w, 0.0015, 0.0005))
        S.mark(f'b{k}', (x, -0.15, 0.051)); S.label(f'b{k}', f'Core block F01 #{k + 1}: 1140 × 304 mm')
    S.view(10, 60, lens=35)


def b_4_5(S):
    S.foam('block', (0, 0, 0.0254), (1.14, 0.3042, 0.0508))
    S.airfoil_plate('root template', (0.57, -0.155, 0.003), 0.2842, rot_z=90); S.airfoil_plate('tip template', (-0.576, -0.155, 0.003), 0.2842, rot_z=90)
    S.bow('bow', (0.6, -0.05, 0.03), (-0.6, -0.05, 0.03), 0.35)
    S.label('root template', 'Root template pinned, leading edge aligned'); S.label('tip template', 'Tip template: same datum line'); S.label('bow', 'Two operators call stations as the wire moves')
    S.view(40, 30, lens=40)


def b_4_6(S):
    S.foam('panel', (0, 0, 0.0254), (1.14, 0.2842, 0.0508)); S.tube('hot tube', (0.57, -0.06, 0.03), (-0.1, -0.06, 0.03))
    S.label('hot tube', 'Heated 1 in tube cuts the 26.0 mm spar channel, 800 mm from the root'); S.view(35, 30, lens=40, fit=['panel'], margin=0.9)


# ============================================================ WP5 skins and wing
def b_5_1(S):
    RS = __import__('render_scenes')
    S.foam('panel', (0, 0, 0.0254), (1.14, 0.2842, 0.0508)); S.box('sanding block', (0.1, 0.0, 0.065), (0.2, 0.07, 0.025), RS.mat('sanding block', (0.75, 0.55, 0.3), 0.9))
    S.label('sanding block', 'Sand smooth; fill dents with glue and foam dust'); S.view(30, 30, lens=40, fit=['sanding block'], margin=4.0)


def b_5_2(S):
    S.foam('test panel', (0, 0, 0.0254), (0.25, 0.25, 0.0508)); S.stripe('tape a', (0, -0.05, 0.0512), (0.25, 0.05, 0.0006), (0.92, 0.92, 0.9))
    S.kitchen_scale('scale', (0.25, 0, 0)); S.label('tape a', 'Skin a 0.25 m square exactly as the wing'); S.label('scale', 'Weigh before and after: gives the skin mass per m²')
    S.view(30, 35, lens=50)


def b_5_3(S):
    S.foam('panel', (0, 0, 0.0254), (1.14, 0.2842, 0.0508))
    for k in range(5): S.stripe(f'tape{k}', (-0.4 + 0.0, -0.11 + 0.05 * k, 0.0512), (0.32, 0.048, 0.0006), (0.93, 0.93, 0.9))
    S.heat_gun('heat gun', (-0.1, 0.0, 0.12))
    S.label('tape2', 'Tape spanwise, 10 mm overlap, smoothed with a card'); S.label('heat gun', 'Heat gun briefly to shrink and seal; never on bare foam')
    S.view(30, 35, lens=40)


def b_5_7(S):
    S.assembly(focus=['F09_M5x20_BHCS*', 'N02_M5_Nylock*', 'Bolt_Pillar*'], context=['Wing_Saddle', 'Root_Tongue'], ghost=['Wing_Panel_L', 'Wing_Panel_R'], lift=0.02)
    S.label('Bolt_Pillar-1', 'M5 × 20 wing bolts through the pillars, 1.0 N·m'); S.view(25, 40, fit=['Wing_Saddle-1'], lens=45, margin=1.8)


# ============================================================ WP6 tail
def b_6_1(S):
    S.airfoil_plate('tail template', (0.12, 0.0, 0.02), 0.1015, code='0009'); S.airfoil_plate('fin root', (0.12, 0.2, 0.02), 0.1597, code='0009'); S.airfoil_plate('fin tip', (0.12, -0.2, 0.02), 0.1038, code='0009')
    S.label('tail template', 'Stabiliser NACA 0009, chord 101.5 mm'); S.label('fin root', 'Fin root 159.7 mm'); S.label('fin tip', 'Fin tip 103.8 mm')
    S.view(15, 30, lens=50)


def b_6_4(S):
    S.assembly(focus=['H_Tail-1', 'Fin*'], context=[], lift=0.02)
    S.label('H_Tail-1', 'Skin the stabiliser and fins as the wing (5.3)'); S.view(30, 30, lens=40)


def b_6_5(S):
    S.assembly(focus=['Elevator-1', 'Rudder*'], context=['H_Tail-1', 'Fin*'], lift=0.02)
    S.label('Elevator-1', 'Tape hinge on the top surface, gap set with a spacer'); S.label('Rudder-1', 'Rudders hinged the same way, both sides')
    S.view(35, 30, lens=40)


def b_6_6(S):
    S.assembly(focus=['Control_Horn-5', 'Horn_Backplate-3'], context=['H_Tail-1', 'Elevator-1'], lift=0.02)
    S.label('Control_Horn-5', 'Elevator horn on the top surface at z +21 mm, bolted through the backplate'); S.view(40, 35, fit=['Control_Horn-5'], lens=50, margin=6)


def b_6_7(S):
    S.assembly(focus=['Fin_Shoe*'], context=['Fin*', 'Rudder*', 'H_Tail-1'], lift=0.02)
    S.label('Fin_Shoe-1', 'Fin root bonded 21 mm deep into the shoe, square to the flange'); S.view(30, 25, fit=['Fin_Shoe-1', 'Fin-1'], lens=50, margin=1.4)


# ============================================================ WP7 booms
def b_7_5(S):
    S.assembly(focus=['Splice_Plug-1', 'Motor_Mount_Upper-2', 'Motor_Mount_Cap-2'], context=['Boom_Rear_Stub-1'], ghost=['Boom_Front-1'], lift=0.02)
    S.label('Splice_Plug-1', 'Plug 40 mm into the front boom; stub slid on until the tubes butt'); S.label('Motor_Mount_Upper-2', 'Rear mount centred over the butt, 35 mm each side')
    S.view(30, 28, fit=['Motor_Mount_Upper-2'], lens=50, margin=3.0)


def b_7_7(S):
    S.assembly(focus=[], context=['Boom_Front-1', 'Boom_Rear_Stub-1', 'Splice_Plug-1'] + UNIT(1)[:3], lift=0.15)
    S.vise('vise', (0.0, -0.4337, 0.0)); S.phone('phone', (0.35, -0.25, 0.12))
    S.label('vise', 'Clamp at the wing-clamp station (526.2 mm)'); S.label('Lift_Motor-1', 'Tap the front motor; phone app records the ringing'); S.label('phone', 'Spectrum app: first bending mode near 32 Hz')
    S.view(30, 25, lens=40)


def b_7_8(S):
    S.assembly(focus=[], context=['Boom_Front-1'] + UNIT(1), lift=0.1)
    z = S.at('Boom_Front-1', 'top').z
    S.esc('esc', (0.30, -0.4337 - 0.016, z - 0.012), 0); S.objs['esc'].rotation_euler.x = math.radians(90)
    S.label('esc', 'ESC on the boom side, inside the prop disc, in the wash (not underneath)'); S.view(40, 22, fit=['Motor_Mount_Upper-1', 'esc'], lens=50, margin=2.2)


# ============================================================ WP8 pod
def b_8_2(S):
    RS = __import__('render_scenes')
    S.assembly(focus=[], context=[], ghost=['Fuselage_Pod-1'], lift=0.02)
    lo, hi = S.bbox(['Fuselage_Pod-1']); cz = (lo.z + hi.z) / 2
    for k, x in enumerate((hi.x - 0.08, 0.30, 0.15, 0.0, lo.x + 0.1)):
        S.cyl(f'frame{k}', (x - 0.003, 0, cz), (x + 0.003, 0, cz), 0.055 if 0 < k < 4 else 0.04, RS.mat('PETG frame', (0.85, 0.42, 0.08), 0.45))
    S.label('frame1', 'P20 frames bonded in the bays (nose ring, 3 mid frames, tail ring)'); S.view(25, 25, fit=['Fuselage_Pod-1'], lens=45)


def b_8_2a(S):
    S.assembly(focus=['FC_Tray-1', 'Flight_Controller-1'], context=['Battery_Tray-1', 'Battery_6S_LiPo-1'], ghost=['Fuselage_Pod-1', 'Canopy-1'], lift=0.02)
    S.label('Flight_Controller-1', 'Flight controller on 5 mm standoffs'); S.label('Battery_6S_LiPo-1', 'Battery bay vented: nose inlet and aft slot')
    S.view(30, 25, fit=['Fuselage_Pod-1'], lens=45)


# ============================================================ WP9 electrical (photoreal where it helps; the wiring diagram variants carry the rest)
def b_9_2(S):
    RS = __import__('render_scenes')
    S.battery('pack', (-0.1, 0, 0.004)); S.wire('red', [(-0.02, -0.01, 0.03), (0.06, -0.01, 0.03), (0.12, -0.01, 0.03)], (0.8, 0.1, 0.08), 0.0025)
    S.wire('black', [(-0.02, 0.01, 0.03), (0.06, 0.01, 0.03), (0.12, 0.01, 0.03)], (0.06, 0.06, 0.06), 0.0025)
    S.box('xt90', (0.15, 0, 0.03), (0.04, 0.03, 0.018), RS.mat('xt90', (0.85, 0.75, 0.2), 0.4))
    S.label('xt90', 'XT90-S male on the pack: cut one lead at a time'); S.label('red', 'Solder, then 2:1 heat shrink over each joint')
    S.view(30, 35, lens=55)


def b_9_10(S):
    RS = __import__('render_scenes')
    S.assembly(focus=[], context=['Fuselage_Pod-1', 'Canopy-1', 'Wing_Saddle'], lift=0.0)
    S.battery('pack', (0.6, 0.35, 0.004)); S.box('watt meter', (0.45, 0.3, 0.01), (0.07, 0.04, 0.02), RS.mat('watt meter', (0.12, 0.12, 0.13), 0.4))
    S.wire('lead', [(0.53, 0.35, 0.03), (0.49, 0.32, 0.02), (0.42, 0.3, 0.02), (0.3, 0.1, 0.05)])
    S.label('watt meter', 'Watt meter in line; props OFF'); S.label('pack', 'First power-up through the XT90-S; watch for heat or smoke')
    S.view(35, 35, lens=40)


# ============================================================ WP10 avionics
def b_10_5(S):
    S.assembly(focus=['Pitot_Tube-1', 'Pitot_Clamp-1'], context=[], ghost=['Wing_Panel_L', 'Fuselage_Pod-1'], lift=0.02)
    S.label('Pitot_Tube-1', 'PT40 pitot forward of the left wing, tubing to the sensor'); S.label('Fuselage_Pod-1', 'MS5525 board inside the pod nose, strapped to 0x77')
    S.view(40, 30, fit=['Wing_Panel_L', 'Fuselage_Pod-1'], lens=40)


def b_10_6(S):
    S.assembly(focus=['Battery_6S_LiPo-1', 'Battery_Tray-1'], context=['FC_Tray-1', 'Flight_Controller-1'], ghost=['Fuselage_Pod-1', 'Canopy-1'], lift=0.02)
    S.label('Battery_6S_LiPo-1', 'Pack centred at x = +0.189 m, straps through the tray'); S.view(25, 25, fit=['Fuselage_Pod-1'], lens=45)


# ============================================================ WP11 firmware
def b_11_3(S):
    S.assembly(focus=['Lift_Motor*', 'Pusher_Motor-1'], context=['*'], lift=0.0)
    for k in range(1, 5): S.label(f'Lift_Motor-{k}', {1: 'M1 front-right, CCW', 2: 'M4 rear-right, CW', 3: 'M3 front-left, CW', 4: 'M2 rear-left, CCW'}[k])
    S.label('Pusher_Motor-1', 'M5 pusher'); S.view(270, 80, lens=35, margin=1.1)   # nose up: right of the aircraft on the right of the picture


def b_11_4(S):
    S.assembly(focus=UNIT(1)[:5], context=[], lift=0.42)
    RS = __import__('render_scenes')
    S.box('beam', (0.39 - 0.0, -0.4337, 0.405), (0.56, 0.025, 0.025), RS.mat('6061 aluminium', (0.80, 0.81, 0.83), 0.28, metal=1.0))
    S.label('Lift_Motor-1', 'Thrust stand: one lift unit, the stand of test C06'); S.view(35, 25, fit=['Lift_Prop-1', 'beam'], lens=45)


# ============================================================ WP12 weight and balance
def b_12_1(S):
    S.assembly(focus=[], context=['Boom_Front-1', 'Boom_Rear_Stub-1', 'Splice_Plug-1'] + UNIT(1) + UNIT(2) + ['Gear_Clamp_Upper-1', 'Gear_Clamp_Lower-1', 'Gear_Clamp_Upper-2', 'Gear_Clamp_Lower-2'], lift=0.06)
    S.kitchen_scale('scale', (-0.08, -0.4337, 0)); S.label('scale', 'Each assembly on the scale; log against the predicted mass'); S.view(30, 25, lens=40)


def b_12_4(S):
    RS = __import__('render_scenes')
    S.assembly(focus=[], context=['*'], lift=0.1)
    S.box('pivot', (0.0, 0.0, 0.05), (0.9, 0.02, 0.1), RS.mat('pivot', (0.55, 0.42, 0.28), 0.6))
    S.label('pivot', 'Balance on the centreline (nose to tail): no wing drops'); S.view(90, 20, lens=40)


SPECS = {k: v for k, v in dict(globals()).items() if k.startswith(('b_', 't_')) and callable(v)}
