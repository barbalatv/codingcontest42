# Medium algorithmic breakthrough experiment

Baseline: **5917**. Best: **5917**. Saved: **0**. Improved cases: **0/210**. Verification: **PASS**. Algorithmic success criterion: **NOT_MET**.

The experiment did not produce a faster validated full program or cycle. The best file is a protected copy of the v2 incumbent. This is a negative result; no optimality or global impossibility claim is made. No new answers were submitted or pushed.

## Implemented algorithms

- Isolated regression-root fix: the entire invalid root is skipped after checking every word; partial masks are never used. Original sources remain unchanged. A fixture injects an invalid 3-beam endpoint followed by a valid 2-beam endpoint on a one-cell pattern. Legacy returns no program; fixed returns a valid one-tick program.
- Six-emitter meet-in-the-middle: symbolic suffix requirements are regressed at each depth. Exact 0-3-tick bridges enumerate all feasible individual emitter paths for a fixed meeting pose, subject to a bounded Cartesian-product size. Emitters remain active when needed. Every proposed concatenation is replayed with true acceptance/clearing semantics.
- Structured chord macro beam: holds/aligned moves of opposed emitters and simultaneous four-emitter clipper plans over 2/3 ticks; intermediate states are not pruned by material score inside a macro. Temporary target erasure and skirting matter are permitted.
- Acceptance frontier: reuses v2 graph/DP, keeps alternate accepting endpoints, synthesizes transitions from newly reached poses, supports 2/3-copy closures modulo verified opposed-pair relabeling, and minimizes total program cost.
- Exact static-pose enumeration: checks all distinct active rays and inactive emitters for useful one-tick repeating patterns, with safe cardinality filtering. No current case was improved.
- Multi-copy flood/carve annealing: preserves endpoint motion/parity, simulates every intermediate pickup, mutates root poses and directs 2/3 beams toward missing/dirty cells. Tested periods with 2/3/4 pickups.
- Whole-emitter trajectory synthesis: precomputes complete closed individual emitter walks for short horizons, coordinate-optimizes an entire emitter trajectory, jointly replaces opposed chord pairs and selected non-opposed pairs, and scores exact material/count evolution. Longer horizons use bounded sampled/triangular/incumbent-guided template catalogs, not exhaustive catalogs.
- Local exact repair: CP-SAT is restricted to concrete near-solutions from C++ and nearby roots. It enforces iff acceptance and cleanup at every tick. No fresh broad global CP-SAT sweep was run.

## Results by experiment

| Experiment | Queries | Measured query wall time, s | Evaluations | Saved |
|---|---:|---:|---:|---:|
| pilot | 110 | 42.127 | 129721071 | 0 |
| chain | 177 | 107.614 | 359066158 | 0 |
| multi_flood | 32 | 52.212 | 18781448 | 0 |
| static | 193 | 0.391 | 28986668 | 0 |
| synthesis | 14 | 31.085 | 586677136 | 0 |
| coupled | 6 | 19.298 | 243327852 | 0 |
| synthesis_macro | 10 | 40.584 | 648466227 | 0 |
| guided_macro | 10 | 46.393 | 636022267 | 0 |
| near_cp | 6 | 7.064 | 0 | 0 |
| discovery | 72 | 25.720 | 90150932 | 0 |

Query times include IPC and engine geometry/template preparation. They do not include all Python graph work and compilation. Some independent read-only CP work overlapped C++ work, so summed query time is not elapsed session time. Elapsed session time was approximately 34 minutes. Full raw configurations, seeds, widths, horizons and counters are in the JSONL logs. Every run used an explicit bounded search budget.

## Ablation and attribution

| Requested source of improvement | Saved ticks |
|---|---:|
| Regression-root fix | 0 |
| Six-emitter bidirectional bridge | 0 |
| Macro-chord lookahead | 0 |
| New multi-copy cycles | 0 |
| Pose-frontier chaining | 0 |
| Setup optimization | 0 |
| Local CP-SAT/LNS repair | 0 |

Old and fixed regression were compared on all 11 priority cases at the same nominal width, horizon and time ceiling. The root bug is real, but the incumbent endpoints are valid and the root fix therefore did not improve them. The controlled root fixture isolates the bug. See `experiments/root_regression_test.json`.

Ordinary and chord beam, and six-emitter bridge, were evaluated at equal nominal budgets. The final compact-case discovery sweep used the same seed for all three methods. Actual query time can be smaller than its ceiling when the bounded horizon is exhausted. Detailed fragment/edge counts are in `summary.json`; a valid equal-cost edge is not a score improvement.

## Why the tested hypotheses did not yield a score gain

The 11 requested cases already use short, strongly optimized intervals. Shortening an edge from the incumbent accepting pose failed in the bounded searches. Relaxed equal-cost searches generated new verified endpoints, but outgoing edges from those endpoints did not produce a cheaper complete route. Thus setup, repetition, and terminal costs were evaluated together rather than counting isolated edges as gains.

The meet-in-the-middle bridge has explicit limits: sparse regression beam, meeting depth up to 3, and a Cartesian-product cap. It is not a complete arbitrary-depth six-emitter solver. Symbolic tails may admit intermediate acceptances; exact replay rejects incompatible concatenations. Macro search is limited to the implemented structured chord operators and beam width. Negative results do not refute either method in general.

The whole-trajectory search reached small remaining defects, including one wrong material cell. Local CP-SAT returned INFEASIBLE for five specific nearby-root submodels and UNKNOWN for one. A deeper case-41 five-tick/two-copy query with radius-3 root neighborhood was INFEASIBLE. These are only statements about the exact recorded models, not proofs that a shorter global trajectory does not exist. Longer-horizon sampled templates and greedy coordinate optimization also remain incomplete.

## Validation and preservation

CPP_PYTHON_STATE_EQUIVALENCE_PASS 210 10117
TRACE_EQUIVALENCE_PASS 210 cases 10117 states including seeded random continuation
MEDIUM_SANDBOX_VALIDATION: PASS, 210 cases, 5917 ticks
ROOT_REGRESSION_ORIGINAL_JS_PASS

The C++ engine, independent Python simulator and original JS match on 10117 states across all 210 incumbent programs with 20 seeded random continuation commands per case. Positions, activation, relevant matter and pickup count are compared. JS edge sampling is separately recorded in `experiments/edge_validation.json`. All original competition files, v1/v2 bests and Antigravity results were read only; their protected tracked paths have no diff. SHA256 provenance is in `experiments/sha256.json`.

## Reproduction

Use Python 3.11, OR-Tools, Node.js and MSVC C++17. All engine sources and local copies of referenced C++ dependencies are included. Compile once per source version with `/O2 /EHsc /std:c++17`.

Current interfaces:

```powershell
python training_medium_breakthrough/chain_experiment.py --ms 900 --width 96 --roots 2
python training_medium_breakthrough/multi_experiment.py --no-single
python training_medium_breakthrough/synthesis_experiment.py --macro --indices 168,51,133,198,36,145,159,50,139,41 --ms 4500 --seed 1400000 --tag guided_macro
python training_medium_breakthrough/setup_discovery.py
python training_medium_breakthrough/test_native.py
python training_medium_breakthrough/compare_traces.py
node training_medium_breakthrough/compare_traces.cjs
node training_medium_breakthrough/validate_sandbox_medium.cjs
python training_medium_breakthrough/finalize.py
```

Initial beam ablation used `geometry_search_v1.cpp`; compile that snapshot to `geometry_search.exe`, then run `run_geometry.py --mode pilot --ms 700 --width 56 --seed 71000`. Restore current geometry source for later experiments. Initial synthesis used `trajectory_synthesis_v1.cpp`; coupled/non-hinted macro synthesis used `trajectory_synthesis_v2.cpp`. Compile the desired snapshot to `trajectory_synthesis.exe` and use `synthesis_experiment.py --old-input` for either old input protocol. The current source accepts incumbent trajectory hints and uses the default input protocol. Archived source hashes distinguish these versions. Time-limited heuristics may vary across hardware.

Best file: `best/answer_level-6_2-medium.txt`. Results CSV has a header and no improvement records because no improvement passed the criterion.

Measured search-query wall time including the deeper local repair: 375.41 seconds. This excludes engineering, compilation, graph work and verification.
