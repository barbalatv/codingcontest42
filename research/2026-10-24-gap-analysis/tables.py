"""Regenerate headroom.csv / worklist.csv / summary.json with corrected semantics.

Two numbers are kept strictly apart:

  rigorous_lb   - proven lower bound (see bound.py). Never exceeds the existing program.
  heuristic_gap - T - (first_accept + sampled_need*(K-1)), where sampled_need comes from
                  random sampling of brush poses. This is a PRIORITISATION SCORE only.
                  It is not a bound: it can be negative (sampling missed a better brush)
                  and it ignores transit, skirting cleanup and multi-cell chords.

The previous report called heuristic_gap "excess" and summed it as achievable savings.
That was wrong and is retracted.
"""
import sys
sys.dont_write_bytecode = True
import csv
import json
import statistics
from sim import Machine, cases, programs
from bound import case_bound


def main():
    rows = []
    for ds in ('medium', 'large', 'enormous'):
        cs, ps = cases(ds), programs(ds)
        for i, (c, p) in enumerate(zip(cs, ps), 1):
            m = Machine(c)
            st, acc, _ = m.run(p)
            nT, C, U, lb = case_bound(m, c[2])
            K, T = c[2], len(p)
            first = acc[0]
            iv = [b - a for a, b in zip(acc, acc[1:])]
            brush = max((t['new_target'] for t in m.run(p, want_trace=True)[2]), default=0)
            rows.append(dict(dataset=ds, case=i, radius=c[0], K=K, target=nT,
                             skirting=m.forbidden.bit_count(), ticks=T,
                             first_accept=first,
                             copy_interval=(round(statistics.mean(iv), 2) if iv else ''),
                             rigorous_lb=lb, rigorous_slack=T - lb,
                             U=U, chords=f'{C[0]}/{C[1]}/{C[2]}',
                             best_tick_paint=brush,
                             heuristic_gap=''))
    # heuristic gap needs the sampled brush library, which lives in seeds.txt
    import re
    seeds = {}
    try:
        for line in open('seeds.txt'):
            if line.startswith('case '):
                kv = dict(re.findall(r'(\w+)=(-?\d+)', line))
                seeds[int(line.split()[1])] = int(kv.get('best_sampled_brush', 0))
    except FileNotFoundError:
        pass
    for k, r in enumerate(rows):
        brush = seeds.get(k, r['best_tick_paint'])
        need = max(-(-r['target'] // max(brush, 1)), -(-r['target'] // 12))
        r['sampled_clean_brush'] = brush
        r['sampled_need'] = need
        if r['K'] > 1:
            r['heuristic_gap'] = r['ticks'] - (r['first_accept'] + need * (r['K'] - 1))
        else:
            r['heuristic_gap'] = r['ticks'] - need
    with open('headroom.csv', 'w', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    neg = [r for r in rows if int(r['heuristic_gap']) < 0]
    pos = sorted([r for r in rows if int(r['heuristic_gap']) >= 10], key=lambda r: -int(r['heuristic_gap']))
    with open('worklist.csv', 'w', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(pos)

    summary = dict(
        ticks=sum(r['ticks'] for r in rows),
        rigorous_lb=sum(r['rigorous_lb'] for r in rows),
        rigorous_slack=sum(r['rigorous_slack'] for r in rows),
        heuristic_gap_sum=sum(int(r['heuristic_gap']) for r in rows),
        heuristic_gap_positive_sum=sum(int(r['heuristic_gap']) for r in rows if int(r['heuristic_gap']) > 0),
        rows_with_negative_heuristic_gap=len(neg),
        worklist_cases=len(pos),
        worklist_gap=sum(int(r['heuristic_gap']) for r in pos),
        by_dataset={})
    for ds in ('medium', 'large', 'enormous'):
        sel = [r for r in rows if r['dataset'] == ds]
        summary['by_dataset'][ds] = dict(
            cases=len(sel), ticks=sum(r['ticks'] for r in sel),
            rigorous_lb=sum(r['rigorous_lb'] for r in sel),
            heuristic_gap=sum(int(r['heuristic_gap']) for r in sel))
    json.dump(summary, open('summary.json', 'w'), indent=1)

    print(f'rows: {len(rows)}, negative heuristic gap: {len(neg)} (sampling artefact)')
    print(f'ticks {summary["ticks"]}, rigorous LB {summary["rigorous_lb"]} '
          f'(slack {summary["rigorous_slack"]})')
    print(f'heuristic gap sum {summary["heuristic_gap_sum"]}, worklist {len(pos)} cases '
          f'/ {summary["worklist_gap"]} ticks')
    print('NOTE: heuristic gap is a prioritisation score, not achievable savings.')
    for r in pos[:10]:
        print('  %-9s #%-4s K=%-3s nT=%-4s T=%-4s brush=%-3s need=%-3s gap=%s' % (
            r['dataset'], r['case'], r['K'], r['target'], r['ticks'],
            r['sampled_clean_brush'], r['sampled_need'], r['heuristic_gap']))


if __name__ == '__main__':
    main()
