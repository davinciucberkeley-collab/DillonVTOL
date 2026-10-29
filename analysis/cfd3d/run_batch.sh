#!/bin/sh
# Case schedule used for the 2026-10-29 runs (see run_cases.py): continue L2 alpha 4 from its own restart, coarse grid,
# alpha sweep warm-started from the converged alpha-4 solution, then the fine grid from scratch.
cd "$(dirname "$0")/../.."
export ITERS=${ITERS:-2500}
RESTART_FROM=L2_a4.0 python analysis/cfd3d/run_cases.py run L2_a4.0
python analysis/cfd3d/run_cases.py run L1_a4.0
RESTART_FROM=L2_a4.0 python analysis/cfd3d/run_cases.py run L2_a0.0 L2_a2.0 L2_a6.0 L2_a8.0
python analysis/cfd3d/run_cases.py run L3_a4.0
python analysis/cfd3d/run_cases.py summary
