# Medium training experiment

Baseline: 5946. Best: 5926. Saved: 20. Cases improved: [21, 50, 66, 83, 106, 120].

MEDIUM_SANDBOX_VALIDATION: PASS, 210 cases, 5926 ticks
Best SHA256: `2593f83ac11984cd2a24dcbfbff6ce314a321a70de07a26a1bbab2bd66eb3071`

## Additive attribution

| Method | Saved ticks |
|---|---:|
| native_acceptance_tail | 6 |
| terminal_bounce | 14 |
| Setup portion of native LNS (already counted) | 3 |
| CP-SAT (including CP LNS) | 0 |
| Meet-in-the-middle (not run) | 0 |

Native acceptance LNS saved 6 ticks: 3 from earlier first acceptance (cases 21, 66, 83), and 3 from terminal-copy refinements (cases 50, 106, 120). Reusing the shortened terminal trajectory as alternating physically reversed paths saved another 14 ticks in case 50. These gains are sequential and do not overlap. Setup attribution describes the portion of program shortened, and is included in native LNS, not an additional gain.

## Search evidence

The model enforces exact material evolution, iff acceptance and target clearing at EVERY intermediate tick. It supports 1-4 acceptances and unrestricted intermediate target destruction/skirting pollution. Closed cycles use actual acceptance states. Root-neighborhood candidates require a separately synthesized exact setup, including its beam effects. No such CP candidate improved the incumbent. INFEASIBLE refers only to each stated horizon and pose restriction; UNKNOWN is not an impossibility proof.

Full baseline traces: `experiments/trace.json`. Simulator equivalence: 10146 states, 210 baseline programs plus 20 seeded random continuation ticks each; compared positions, activation, relevant matter and acceptance count against original JS. Three fixed incumbent multi-copy trajectories were reproduced by CP-SAT with OPTIMAL status.

CP model/search timings (wall seconds, includes model construction):

- joint_log: {'queries': 7, 'seconds': 29.711452200077474, 'statuses': {'INFEASIBLE': 2, 'UNKNOWN': 5}}
- pilot_log: {'queries': 32, 'seconds': 117.52995959972031, 'statuses': {'INFEASIBLE': 5, 'UNKNOWN': 27}}
- tail_log: {'queries': 126, 'seconds': 197.30279910028912, 'statuses': {'UNKNOWN': 116, 'INFEASIBLE': 10}}

Native complete-pass wall time is the final DONE entry in `experiments/native_tail.log` (210 cases, 450 ms per neighborhood, windows 8/12/16). The bounce pilot took about 6.6 s including Python startup and all successful JS validations; the subsequent all-210 pass took 0.85 s with no extra gain. Zeroes in its historical CSV entries mean timing was not instrumented per update.

## Reproduction

Run from repository root with Python 3.11, OR-Tools, Node and MSVC:

```powershell
python training_medium_codex/exact_acceptance.py --mode trace
python training_medium_codex/compare_traces.py
node training_medium_codex/compare_traces.cjs
python training_medium_codex/test_cp_witness.py
python training_medium_codex/exact_acceptance.py --mode pilot --seconds 4
python training_medium_codex/run_joint.py
python training_medium_codex/run_native_tail.py
python training_medium_codex/terminal_bounce.py
python training_medium_codex/bounce_all.py
python training_medium_codex/finalize.py
```

Compile `engines/acceptance_tail.cpp` once with `/O2 /EHsc /std:c++17`. Python coordinates a persistent C++ engine. CP and native experiments were explored concurrently; for deterministic checkpoint attribution, reproduce them sequentially. Use baseline as initial best for a fresh replay; never overwrite an existing stronger best. Original contest inputs/answers and Antigravity files were not modified. No commit or PR created.
