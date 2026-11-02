# Agent and tool interface

How a team member or an AI agent runs, checks and extends the engineering pipeline without editing page code.
Written 2026-10-29 with the full-aircraft CFD and the validation matrix.

## Layers

| Layer | What lives there | Who changes it |
|---|---|---|
| Inputs | `cad/params.txt` (from `cad/params.mjs`), `cad/hardware.json`, `analysis/results.json` (from `analysis/sizing.mjs`) | design decisions |
| Computation | `analysis/` scripts: sizing, aero package, `analysis/cfd3d/` (geometry → mesh → SU2 → post), `cad/*.cs` (SOLIDWORKS CAD, FEA, thermal) | engineers / agents, through the CLI |
| Evidence | solver outputs: `analysis/cfd3d/out/cases/*/` (case.cfg, su2.log, history.csv, restart_flow.csv), `cad/sim/*.LOG`, `analysis/aero/out/` | written only by the solvers |
| Verification | `analysis/validation/` checks (`check_aero.py`, `check_struct.py`, `xtool_boom_fea.py`), `analysis/cfd3d/verify_cfd.py`, merged by `build_matrix.py` into `validation_matrix.json` | independent of the computation scripts |
| Presentation | `review/` (build.mjs embeds the JSON; `src/cfdviz.js`, `src/claimsmap.js`, …) | reads JSON only, computes nothing that is reported |

The page never computes an engineering number that it reports. It draws what the computation and verification layers wrote, so a result can be re-generated, diffed and audited without opening the page code.

## Start here if you have never used a command line

1. Open the project folder in File Explorer and double-click **`VTOL.bat`**. A window opens with a numbered menu.
2. Type a number and press Enter. For a first look:
   - **1** opens the review website.
   - **2** re-checks every claim.
   - **3** explains one claim step by step: type an ID such as `AERO-14`.
3. When a step finishes, press Enter to return to the menu. Type **0** to close it.

The menu runs the same commands listed below. You need Python (`py`) for everything, and Node.js only for option 7, which rebuilds the website. Nothing in the menu changes the design; it only re-runs checks and writes reports.

| You want to… | Menu | Command |
|---|---|---|
| See the review website | 1 | `py tools/vtol.py open` |
| Check that every claim still holds after a design change | 2 | `py tools/vtol.py check` |
| Show someone why one number is right | 3 | `py tools/vtol.py trace AERO-14` |
| Hand someone a one-page proof | 4 | `py tools/vtol.py prove AERO-14` (or `all`) → `docs/validation/proofs/` |
| Check the datasheets and papers behind the numbers | 5 | `py tools/vtol.py sources --recheck` |
| Judge whether the CFD mesh is good enough | 6 | `py tools/vtol.py mesh-audit` |
| Gate a release (fails on stale numbers) | — | `py tools/vtol.py strict` |

## Command-line interface

`py tools/vtol.py <command> [--json]`. `--json` prints one JSON object on stdout. Exit code 0 means success and 1 means a step failed or a check found a problem. Running `py tools/vtol.py` with no command opens the menu.

| Command | Runs | Typical time on the team workstation (i7-13700H, 20 threads) |
|---|---|---|
| `check` | every independent check, the matrix and the proof chains (`analysis/validation/proofs.py`), with a summary of what changed since the last check | ~10 s |
| `trace <ID>` | one claim: each step with its numbers, each input and the file, claim or source it comes from | < 1 s |
| `prove <ID>` / `prove all` | proof sheets in `docs/validation/proofs/` (Markdown; GitHub renders the equations) | < 2 s |
| `strict` | exits 1 if any arithmetic fails to re-run for a claim not already marked Failed, any hand-off between claims is stale, or any input has no source | < 1 s |
| `sources [--recheck]` | the external sources and their check status; `--recheck` re-tests every URL in the docs (`link_check.py`) | < 1 s, or a few minutes with `--recheck` |
| `mesh-audit` | `analysis/cfd3d/mesh_audit.py`: measures the three CFD meshes and scores them against published gridding guidelines | ~20 s |
| `open` | opens `VTOL-Review.html` in the default browser | < 1 s |
| `status` | inventory of inputs, meshes, CFD cases, claim counts | < 1 s |
| `geometry` | `analysis/cfd3d/build_geometry.py`: CFD outer mould line from `cad/params.txt`, fidelity against `cad/model/VTOL_Concept.STEP` | ~70 s |
| `mesh --level N` | `build_mesh.py N`: half-model tetrahedral mesh, `mesh_stats.json` | 30–50 s |
| `cfd run <case> [--restart-from <case>] [--iters N]` | `run_cases.py run`: SU2 8.5 INC_EULER | L1 ~10 min, L2 ~15–45 min, L3 hours |
| `cfd summary / post / pack / verify` | results table, post-processing (forces, Trefftz, grids), viewer pack, CFD claims | 1–2 min per case |
| `validate` | same as `check` (kept for scripts that call it) | ~10 s |
| `xtool boom` | gmsh + own C3D10 solver against the SOLIDWORKS boom FEA | a few minutes |
| `claims [--component] [--status] [--discipline]` | query the matrix | < 1 s |
| `compare <git-ref>` | key results now against another commit (design-iteration diff) | < 1 s |
| `report` | `node review/build.mjs` | ~20 s |

Example agent loop after a design change: `vtol status --json` → `vtol geometry` → `vtol mesh --level 2` → `vtol cfd run L2_a4.0` → `vtol cfd post L2_a4.0` → `vtol check --json` → `vtol strict` → `vtol compare HEAD --json` → `vtol report`.

## Why a CLI first, and when MCP is worth it

A CLI is the smallest interface that every agent framework and every team member can already use, and it keeps each step a plain, logged process. An MCP server becomes worth writing when several agents work concurrently and need typed tool schemas (for example `run_case(name, restart_from)`) and long-running job handles. The CLI is shaped so an MCP server can wrap it one command per tool with no logic of its own, because each command already has stable arguments and a JSON result.

## Integrations and what each one needs

| Tool | Status | What it needs |
|---|---|---|
| SOLIDWORKS 2025 (CAD, Simulation) | in use (`cad/*.cs`, C# API) | the licensed workstation; Flow Simulation is not on this licence |
| gmsh 4.15.2 (Python) | in use: CFD geometry and meshes, cross-tool FEA meshes | installed (`pip`) |
| SU2 8.5.0 | in use: 2-D sections and full-aircraft 3-D | `C:\Users\dillo\tools\su2` (env `SU2_CFD` to override) |
| CalculiX (ccx) | **not installed** | binary for Windows; `xtool_boom_fea.py` writes the same mesh, BCs and load, so a `.inp` export is the next step to run it there |
| Team member's Gmsh/CalculiX application | not connected | its input format (or its repository); the hand-off file would be the gmsh `.msh` / `.brep` written by `analysis/cfd3d/` |
| Onshape | not connected | API keys (access + secret) for the team's document, plus document/workspace IDs |
| Autodesk Fusion | not connected | Autodesk Platform Services app credentials (client ID/secret) and the hub/project |
| Celedon DaVinci | not connected | its API documentation and credentials, which this repository does not contain; nothing was implemented against it |

No integration that needs credentials was attempted.
