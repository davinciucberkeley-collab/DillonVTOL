#!/bin/sh
# Resume the L4 alpha-4 case (2026-11-02): the first leg was stopped at iteration 2124 to free the PC; its last
# restart write is iteration 2000. Warm-restarts from that file for the remaining 1000 of the 3000-iteration budget
# (run_cases.py keeps the first leg as history_leg1.csv and counts it in the summary), then the same steps as run_L4.sh.
cd "$(dirname "$0")/../.."
export PYTHONIOENCODING=utf-8
RESTART_FROM=L4_a4.0 ITERS=${ITERS:-1000} py analysis/cfd3d/run_cases.py run L4_a4.0
py analysis/cfd3d/run_cases.py summary
py analysis/cfd3d/postprocess.py L4_a4.0
echo "L4 done $(date)"
