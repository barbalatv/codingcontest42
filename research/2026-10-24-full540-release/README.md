# Level 6 — submission update, 2026-10-24

The three submission answers in `level-6/` are promoted byte for byte from
`training_l6_full540/best/`. Total: **15657 ticks, 540 cases, LOCAL_PASS**.

| Dataset | Previous submission | New submission | Cases |
|---|---:|---:|---:|
| Medium | 5946 | 5904 | 210 |
| Large | 5112 | 5047 | 190 |
| Enormous | 4741 | 4706 | 140 |
| Total | 15799 | **15657** | 540 |

The research comparison used a stronger frozen baseline of 15721; the final
experiment saves 64 ticks against that baseline. See
[the full report](../../training_l6_full540/REPORT.md) and
[the preceding Cell-First report](../../training_l6_cellfirst/REPORT.md).
Both accumulated research directories are included with sources, reports,
graphs, candidates, checkpoints, and raw experiment records. Build outputs,
Python caches, and temporary lock files are excluded from Git.

Upload the three `.txt` answers from `level-6/`, or extract them from
[answers_level6_15657.zip](answers_level6_15657.zip). The archive contains exactly
these three files. The previous submission files are preserved in
`previous_submission/`; [delivery.json](delivery.json) records both old and new
SHA256 digests.

The complete new answers passed C++ state replay, independent Python verification,
and the unchanged original JavaScript sandbox validator. Source, promoted, ZIP,
and staged Git bytes are checked during publication. Platform submission has
not been performed; global optimality of the total is not claimed.

Historical research preservation receipts describe the workspace **before** this
authorized promotion. Exactly three protected submission answers and the two
Git publication rules (`.gitignore`, `.gitattributes`) change in this release;
all other originally protected files retain their bytes. The historical
`training_l6_full540/validate_final.py` intentionally expects the earlier frozen
workspace. For the promoted release, use the verifier below instead.

From the repository root (Python and Node required; build uses MSVC on Windows):

```powershell
python training_l6_full540/build.py cellfirst.cpp
python research/2026-10-24-full540-release/verify.py
```

The final promotion receipt is [validation.log](validation.log).
