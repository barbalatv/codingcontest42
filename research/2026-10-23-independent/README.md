# Independent Level 6 optimization

Merged score: 17732 ticks across medium, large and enormous. These results are locally validated, not submitted to the contest platform by this agent.

The independent snapshot improved 19,062 to 17,766 ticks across 226 cases. Integration preserves each shorter program from the newer GitHub commits and the independent result. See integration.json for final dataset totals. Example and small also preserve the best available answers.

Methods: stochastic cycle retiming, targeted two/three-beam repair, segment-tree composition of write/erase effects, suffix-requirement window reduction, and dynamic emitter-path repair using effect equivalence and weakest preconditions. No global-optimality claim.

All 553 cases are checked with solve_l5.verify and the final files with the original JavaScript simulator via node validate_l6_sandbox.cjs.

New C++ engines and run_*.py drivers are in the repository root. Build engines with compile_helper.py under MSVC before running a corresponding driver. Candidate directories and compiled binaries from these independent experiments are not included. Per-run JSON records are experimental gains against their respective input snapshots and overlap; do not sum them. independent_summary.json records the isolated final snapshot, while integration.json records the published combination.
