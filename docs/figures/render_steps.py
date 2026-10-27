"""Renders the step figures defined in step_specs.py with Blender (Cycles, GPU when available).
    blender -b --factory-startup -P docs/figures/render_steps.py -- [figure ids or prefixes ...]
No arguments renders all of them; 'b_4' renders every WP4 figure. Output: docs/figures/renders/steps/<id>.png/.json,
then python docs/figures/annotate_steps.py lays the callouts and captions."""
import os, sys, traceback
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import figkit, step_specs, test_specs
ALL = {**step_specs.SPECS, **test_specs.SPECS}

BENCH = ('b_1_', 'b_2_', 'b_3_', 'b_4_', 'b_5_1', 'b_5_2', 'b_5_3', 'b_6_1', 'b_9_', 't_c')
args = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
names = sorted(ALL)
if args: names = [n for n in names if any(n == a or n.startswith(a) for a in args)]
failed = []
for n in names:
    try:
        S = figkit.Scene(n, 'bench' if n.startswith(BENCH) else 'studio')
        ALL[n](S); S.render()
    except Exception:
        failed.append(n); traceback.print_exc()
print('FAILED:', ' '.join(failed) if failed else 'none')
