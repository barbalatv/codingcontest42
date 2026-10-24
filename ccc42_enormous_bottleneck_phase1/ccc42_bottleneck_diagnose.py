#!/usr/bin/env python3
"""CCC42 Level 6: acceptance-aware bottleneck diagnostics (read-only).

Place in <repo>/training_l6_bottleneck/diagnose.py or run with --repo.
Requires the repository's existing solve_l6 / optimize_l6_compact modules.
"""
from __future__ import annotations

import argparse
import csv
import json
import statistics
import sys
from collections import Counter
from pathlib import Path


def bits(mask: int):
    while mask:
        b = mask & -mask
        yield b.bit_length() - 1
        mask ^= b


def analyze_case(sim, program, *, dataset: str, index: int, radius: int,
                 K: int, n_target: int, tail_ticks: int = 5,
                 assert_physics: bool = True):
    """Produce per-copy statistics using matter *before acceptance reset*.

    sim implements the repository optimize_l6_compact.Sim interface.
    The simulated post-reset state is the only correct state for the next tick.
    """
    state = sim.initial()
    first_build = {}
    last_build = {}
    ever_built = 0
    events = []
    t_prev_accept = 0
    copies = []
    for t, command in enumerate(program, 1):
        prev_state = state
        state = sim.step(prev_state, command)
        pos, active, post_matter, accepted = state
        before_matter = prev_state[2]

        one = two = three = 0
        for emitter in range(6):
            if (active >> emitter) & 1:
                ray = sim.rays[pos[emitter]][emitter]
                three |= two & ray
                two |= one & ray
                one |= ray

        # Exactly the state the sandbox considers for acceptance.
        pre_matter = (before_matter | two) & ~three
        pickup = (pre_matter & sim.target) == sim.target and not (pre_matter & sim.forbidden)
        expected_post = pre_matter & ~sim.target if pickup else pre_matter

        if assert_physics:
            assert (accepted - prev_state[3]) == int(pickup), (
                dataset, index, t, "acceptance count differs")
            assert post_matter == expected_post, (
                dataset, index, t, "post-acceptance matter differs")

        newly_built = pre_matter & ~before_matter & sim.target
        rebuilt = newly_built & ever_built
        target_erased = before_matter & ~pre_matter & sim.target
        skirt_cleaned = before_matter & ~pre_matter & sim.forbidden
        skirt_added = pre_matter & ~before_matter & sim.forbidden

        for cell in bits(newly_built):
            first_build.setdefault(cell, t)
            last_build[cell] = t
        ever_built |= newly_built

        events.append(dict(t=t, new=newly_built, rebuilt=rebuilt,
                           erased=target_erased, clean=skirt_cleaned,
                           dirtied=skirt_added, pre=pre_matter))

        if not pickup:
            continue

        window_start = max(t_prev_accept + 1, t - tail_ticks + 1)
        tail = [ev for ev in events if ev["t"] >= window_start]
        early = [ev for ev in events if ev["t"] < window_start]

        # Cells whose *last* 0->1 transition occurs in the tail.
        last_touched = {cell for cell, tick in last_build.items()
                        if tick >= window_start}
        # Among those: first creation vs recreation of an earlier target.
        late_build = {cell for cell in last_touched
                      if first_build[cell] == last_build[cell]}
        late_churn_final = last_touched - late_build
        # Additional within-window recreation events (may overlap late_build).
        late_rebuilt = set(bits(0))  # explicit set, independent of final state
        late_clean = set()
        late_dirty = set()
        late_erased = set()
        for ev in tail:
            late_rebuilt.update(bits(ev["rebuilt"]))
            late_clean.update(bits(ev["clean"]))
            late_dirty.update(bits(ev["dirtied"]))
            late_erased.update(bits(ev["erased"]))

        n_new = sum(ev["new"].bit_count() for ev in tail)
        early_rate = (sum(ev["new"].bit_count() for ev in early) / len(early)
                      if early else None)
        tail_rate = n_new / len(tail)
        sparse = 0 < len(last_touched) <= 10
        slow_tail = (early_rate is not None and early_rate > 0
                     and tail_rate <= 0.65 * early_rate)
        # A focused search criterion, *not* a proven reserve/optimality bound.
        candidate = sparse and slow_tail and t - t_prev_accept >= 10

        copies.append(dict(
            dataset=dataset, case=index, copy=accepted, K=K,
            radius=radius, target_cells=n_target, program_ticks=len(program),
            interval_ticks=t - t_prev_accept, acceptance_tick=t,
            tail_window_ticks=len(tail),
            late_build=len(late_build), late_churn=len(late_churn_final),
            late_rebuild_events=sum(ev["rebuilt"].bit_count() for ev in tail),
            late_rebuilt_unique=len(late_rebuilt),
            late_unique_final=len(last_touched),
            late_clean=len(late_clean), late_dirty=len(late_dirty),
            late_erased=len(late_erased), late_creation_events=n_new,
            last_tick_new=tail[-1]["new"].bit_count(),
            early_rate=round(early_rate, 6) if early_rate is not None else None,
            tail_rate=round(tail_rate, 6),
            sparse_tail=int(sparse), slow_tail=int(slow_tail),
            focused_candidate=int(candidate),
            # Geometry-indexed cells, consistent with solve_l4.geometry(radius).
            bottleneck_cell_ids=sorted(last_touched),
            cleanup_cell_ids=sorted(late_clean),
        ))
        t_prev_accept = t
        events.clear()
        first_build.clear()
        last_build.clear()
        ever_built = 0

    assert state[3] == K, (dataset, index, "accepted", state[3], K)
    assert t_prev_accept == len(program), (dataset, index, "trailing commands")
    return copies


def summary(rows, programs_total):
    def avg(key):
        return round(statistics.mean(row[key] for row in rows), 3)
    def median(key):
        return statistics.median(row[key] for row in rows)
    return dict(
        cases=len({r["case"] for r in rows}),
        copies=len(rows), total_program_ticks=programs_total,
        sparse_tail_copies=sum(r["sparse_tail"] for r in rows),
        sparse_tail_cases=len({r["case"] for r in rows if r["sparse_tail"]}),
        focused_candidate_copies=sum(r["focused_candidate"] for r in rows),
        focused_candidate_cases=len({r["case"] for r in rows if r["focused_candidate"]}),
        late_clean_copies=sum(r["late_clean"] > 0 for r in rows),
        late_churn_copies=sum(r["late_churn"] > 0 for r in rows),
        late_rebuild_copies=sum(r["late_rebuilt_unique"] > 0 for r in rows),
        median_late_final_cells=median("late_unique_final"),
        mean_late_final_cells=avg("late_unique_final"),
        median_last_tick_new=median("last_tick_new"),
        mean_last_tick_new=avg("last_tick_new"),
        mean_late_creation_events=avg("late_creation_events"),
    )


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--repo", type=Path,
                    default=Path(__file__).resolve().parent.parent)
    ap.add_argument("--dataset", choices=["medium", "large", "enormous"],
                    default="enormous")
    ap.add_argument("--bank", type=Path, default=None,
                    help="Answer text file; defaults to training_l6_full540/best")
    ap.add_argument("--tail", type=int, default=5)
    ap.add_argument("--out", type=Path, default=None)
    ap.add_argument("--verify-independent", action="store_true",
                    help="Also check the original independent Python verify()")
    args = ap.parse_args()
    assert 1 <= args.tail <= 128
    repo = args.repo.resolve()
    sys.path.insert(0, str(repo / "training_l6_full540"))
    from common import cases, name, load_programs, exact
    from optimize_l6_compact import Sim

    bank = args.bank or repo / "training_l6_full540" / "best" / name(args.dataset)
    cc = cases(args.dataset)
    pp = load_programs(bank)
    assert len(cc) == len(pp), (len(cc), len(pp))
    result = []
    for i, (case, prog) in enumerate(zip(cc, pp), 1):
        if args.verify_independent:
            exact(case, prog)
        r, pat, K = case
        result.extend(analyze_case(
            Sim(case), prog, dataset=args.dataset, index=i,
            radius=r, K=K, n_target=len(pat),
            tail_ticks=args.tail))
    report = summary(result, sum(map(len, pp)))
    report.update(dataset=args.dataset, bank=str(bank), tail_ticks=args.tail)
    out = args.out or repo / "training_l6_bottleneck" / "results"
    out.mkdir(parents=True, exist_ok=True)
    js = out / f"{args.dataset}_tail_diagnostics.json"
    csvfile = out / f"{args.dataset}_tail_diagnostics.csv"
    js.write_text(json.dumps({"summary": report, "copies": result},
                              indent=2, ensure_ascii=False), encoding="utf-8")
    fields = [key for key in result[0] if not key.endswith("_cell_ids")]
    with csvfile.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows({k: row[k] for k in fields} for row in result)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    print("Output:", csvfile, "and", js)


if __name__ == "__main__":
    main()
