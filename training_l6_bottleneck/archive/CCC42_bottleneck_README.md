# CCC42 Enormous — Acceptance-Aware Tail Diagnostics

Read-only Phase 1 implementation of Hard-Core First/Bottleneck Re-weighting research.

## Files
- `ccc42_bottleneck_diagnose.py`: per-copy physical trace and diagnostics. No repository modifications.
- `ccc42_bottleneck_tests.py`: synthetic invariant tests (acceptance reset, within-window churn, skirting cleanup).

## Run locally (Windows PowerShell)

```powershell
python .\ccc42_bottleneck_tests.py
python .\ccc42_bottleneck_diagnose.py --repo 'C:\Users\user\Documents\CCC42' --dataset enormous --verify-independent
```

To use another accepted answer bank:

```powershell
python .\ccc42_bottleneck_diagnose.py --repo 'C:\Users\user\Documents\CCC42' --dataset enormous --bank 'C:\Users\user\Documents\CCC42\training_l6_full540\best\answer_level-6_4-enormous.txt'
```

The default answer bank is `training_l6_full540/best/`. Output is written to `<repo>/training_l6_bottleneck/results/`:
- `enormous_tail_diagnostics.csv` — one row per accepted copy.
- `enormous_tail_diagnostics.json` — summary plus geometry cell indices for weight masks.

## Interpretation

- `late_unique_final`: number of target cells whose *last* 0->1 transition occurs in the final 5 ticks of that copy.
- `late_build`: subset created only once during the copy, for the first and last time in that window.
- `late_churn`: target cells whose final creation in the window is a rebuild after an earlier creation.
- `late_rebuild_events`: all repeated 0->1 transitions in the window (even if later erased).
- `late_clean`: distinct skirting cells cleared in the last 5 ticks.
- `late_dirty`: distinct skirting cells contaminated in the last 5 ticks.
- `sparse_tail`: `0 < late_unique_final <= 10` (descriptive, not proof of opportunity).
- `slow_tail`: last-5 target creation rate <=65% of earlier in-copy rate.
- `focused_candidate`: sparse + slow and copy duration >=10 ticks. This is an experimental filter, not a lower bound.

**Critical acceptance semantics:** use the post-command/post-beam but pre-pickup matter to detect new cells at acceptance. The following tick MUST use the actual post-pickup matter. `pre_matter[t-1]` cannot be used as the prior state across an acceptance.

## Independent exploratory replay results on published best

Reconstructed the official per-tick model directly from the repository's input geometry and 140 published best answer files (4706 ticks, 210 accepted copies). All 140 accepted required K.

- 53/210 accepted copies had <=10 late-final target cells (49 unique cases).
- Median final-5 late-built unique cells: 16; mean: 16.58.
- 47 copies cleared at least one skirting cell during their final five ticks.
- 25 copies had a last-tail rebuild of a target first built before the tail window (narrow churn definition).
- Mean last-tick target new cells: 3.25.

These are observations, not proof that the tail can be shortened or that a 450-tick improvement is possible. The independent exploratory replay followed original physics, but did not itself invoke the original JS sandbox validator. The Python script asserts exact equivalence with repository Sim on every tick, and with `--verify-independent` additionally uses `solve_l5.verify`.

## Next step

Test reweighted beam against its identical unweighted control using the same frozen incumbent, seeds, width and time limits. Do not rewrite original engines. The current `Engine.ask` protocol is a whitespace-delimited streaming input to C++, not JSON; extending it requires changing both copies of the reader/writer. Disable all weight effects for an all-100 baseline to verify parity first. The C++ code has separate scoring sites in `stateScore`, `snapshotScore` and `commandExpand` that must be audited together.
