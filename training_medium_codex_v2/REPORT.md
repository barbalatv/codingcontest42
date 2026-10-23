# Acceptance-cycle graph optimization v2

Baseline **5926**, best **5917**, saved **9**, improved **9/210**. Full independent Python and original JS validation PASS.

## Non-overlapping attribution

| Stage | Saved ticks |
|---|---:|
| history_dp | 3 |
| symmetry_graph_dp | 1 |
| new_edges_dp | 5 |

Generalized Bounce is an edge-generation step; DP is the optimizer combining those edges. Their savings are attributed only at the checkpoint that first improved the full program, never added again. `new_edges_dp` includes any downstream bounce/symmetry expansions enabled by a synthesized edge. No repeat-period breakthrough is claimed without a reduced interval trace.

## Improved cases

| Case | Before | After | Saved | First acceptance before/after |
|---|---:|---:|---:|---|
| 4 | 36 | 35 | 1 | 6/5 |
| 16 | 17 | 16 | 1 | 5/4 |
| 36 | 87 | 86 | 1 | 7/6 |
| 56 | 38 | 37 | 1 | 4/3 |
| 99 | 35 | 34 | 1 | 5/4 |
| 112 | 28 | 27 | 1 | 4/3 |
| 143 | 58 | 57 | 1 | 7/6 |
| 166 | 32 | 31 | 1 | 5/4 |
| 204 | 70 | 69 | 1 | 7/7 |

Exact acceptance times and selected paths are stored in `experiments/summary.json` and `experiments/selected_paths.json`. They distinguish setup savings from terminal or interior savings. Case 50 retains its verified 82-tick, 5-tick-per-copy strategy; no further reduction found.

## Implementation and correctness

Every library edge stores case (bank file), start/end physical pose, copy count 1-4, ticks, complete program, provenance and verification flag. All edges are replayed by independent Python simulation before insertion. The initial state is a separate vertex. DP tracks exact copy count, keeps one cheapest path per pose/count, bounds its frontier, and permits any final pose. Macros preserve intermediate pickup semantics. Library expansion includes physical reversals with endpoint holds, phase shifts, trajectories from nearby donor poses, all 8 opposed-pair permutations, endpoint-relaxed partial-emitter mutations and separately tested return bridges. Opposed symmetries are validated against every ray mask and each resulting edge is simulated.

C++ runs persistently and receives actual starting pose with clean relevant matter. Fixed-pose bridges use an explicit endpoint cost. Python validates every improving complete program with solve_l5.verify and original sandbox on a temporary full output before atomic replacement. Historical trajectories are independently verified before extraction. Generalized Bounce never assumes that physical reversal reverses matter.

## Experiments and limitations

Library: 16587 vertices, 106811 minimum-cost edges across available case banks. Search timings below are wall time summed within each stage; independent overlapping stages must not be summed as total elapsed time.

- pilot: {'queries': 10, 'seconds': 62.12489620014094, 'statuses': {'completed': 10}}
- all: {'queries': 210, 'seconds': 360.4621388002997, 'statuses': {'completed': 210}}
- focused: {'queries': 10, 'seconds': 95.20767090015579, 'statuses': {'completed': 10}}
- partial_cp: {'queries': 18, 'seconds': 19.23368540010415, 'statuses': {'INFEASIBLE': 12, 'UNKNOWN': 5, 'OPTIMAL': 1}}

Pilot: ten specified cases, then all-210 bounded search. A subsequent targeted run prioritizes actual DP path edges, allows longer macros and uses a new seed/budget. The first broad run used the earlier short-edge selector; its exact parameters are in logs and source-history patch scripts. Partial CP freezes 3-4 emitter trajectories and removes a tick from the others; results and UNKNOWN/INFEASIBLE statuses are retained. It does not repeat the previous unrestricted closed-cycle queries. No global CP-SAT search or exhaustive optimality proof is claimed. Deep target-case search stalled: new physical poses were generated, but their outgoing transitions were not cheap enough to improve the full route.

JS edge sampling results: `experiments/edge_js_validation.json`. Complete best-set validation: `validate_sandbox_medium.cjs`. Input, old best, baseline and new best SHA256 provenance: `experiments/sha256.json`. All original competition files, v1 results and Antigravity files remain unchanged. No commit or push performed for this experiment.

## Reproduction

Compile `engines/edge_search.cpp` once with MSVC `/O2 /EHsc /std:c++17`. The complete source is included. From the repository root:

```powershell
python training_medium_codex_v2/graph_cycles.py --mode pilot --ms 600 --queries 8 --seed 20000
python training_medium_codex_v2/symmetry_graph.py
python training_medium_codex_v2/graph_cycles.py --mode all --ms 180 --queries 3 --seed 40000
python training_medium_codex_v2/graph_cycles.py --mode focused --ms 1100 --queries 6 --seed 90000
python training_medium_codex_v2/partial_replan.py
python training_medium_codex_v2/finalize.py
node training_medium_codex_v2/validate_edges.cjs
```

For a fresh experiment use a new copy of this directory with its baseline as the initial best. Never reset an existing stronger best. The historical source bank depends on available local files; every retained edge records its actual origin. Replaying stored edge banks and selected paths does not require the historical files. Deterministic seeds are recorded; time-limited annealing may vary with hardware.

## Outcome interpretation

Eight saved ticks come from earlier first acceptance. Case 204 contributes one tick from a different transient route after the first acceptance; its setup remains 7 ticks and its steady 4-tick interval is unchanged. Terminal-only gain: 0. No faster sustained repeating cycle was found. Thus the minimum score goal is met, but the intended substantial repeating-cycle breakthrough is not achieved.

Historical DP contributes 3 already-known per-case programs from the read-only Antigravity best (cases 143, 166, 204); these are reuse gains, not newly synthesized improvements. The remaining 6 saved ticks are new: symmetry graph DP 1, synthesized-edge DP 5. See experiments/donor_attribution.json. Generalized Bounce alone: 0 verified ticks; partial CP: 0 verified ticks.

Elapsed session time: about 10 minutes. Broad pass: 361.47 seconds for 210 cases. Focused pass: 95.48 seconds for ten cases. Pilot: 62.77 seconds. These overlap with independent analyses and must not be added to infer elapsed time. Original JS independently checked 6626 sampled library edges / 89972 ticks; all 210 complete best programs also passed original JS and solve_l5.verify.
