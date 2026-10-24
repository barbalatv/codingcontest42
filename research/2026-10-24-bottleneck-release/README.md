# Level 6 submission release — 2026-10-24

**LOCAL_PASS: 540 cases, 15629 ticks.** The three submission answers in `level-6/`
are byte-identical to `training_l6_bottleneck/best/`.

| Dataset | Previous submission | New submission | Cases |
|---|---:|---:|---:|
| Medium | 5904 | 5904 | 210 |
| Large | 5047 | 5035 | 190 |
| Enormous | 4706 | 4690 | 140 |
| TOTAL | 15657 | **15629** | 540 |

Upload the three answer files from `level-6/`, or extract
[answers_level6_15629.zip](answers_level6_15629.zip). The ZIP contains exactly
these three answers. Previous submission bytes are retained in
`previous_submission/`; [delivery.json](delivery.json) records all digests.

Submission files were still at 15657 despite a stronger 15639-tick local bank.
This promotion saves 28 submission ticks: 18 from prior bank consolidation and
10 from the new experiment. The bottleneck experiment saved 10 ticks across
9 Enormous cases: standalone
weighted beam 1, iterative EMA 1, Cell-Assignment LNS 2, standard beam + LNS 4,
weighted beam + LNS 2. CP-SAT independently reproduced two overlapping
shortenings and contributes no additional marginal savings. See
[the research report](../../training_l6_bottleneck/REPORT.md) for controlled
comparisons, all 140 screened cases, the memory-limited failed repair attempt,
and the successful bounded retry. Sources, original diagnostic archive,
experimental records, candidates, checkpoints and reports are included.
Compiled binaries, object files and Python caches are excluded from Git.

Research preservation receipts, `summary.json`, and the report describe the
completed experiment before this later authorized submission promotion and
GitHub publication. They remain historical evidence. The old strict preservation
check in `training_l6_bottleneck/validate.py` intentionally expects the original
submission files and Git attributes; use this release verifier after promotion.

```powershell
python -B training_l6_bottleneck/build.py
python -B research/2026-10-24-bottleneck-release/verify.py
```

The verifier checks C++ replay, Python Sim, `solve_l5.verify`, the original JS
sandbox, strict acceptance count and final-tick acceptance, ZIP/source/destination
byte identity, and the research artifact manifest. See [validation.json](validation.json).
Platform submission has not been performed. Global optimality is not claimed.
