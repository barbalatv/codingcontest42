"""Rigorous per-tick creation bound for level 6, and correction of the headroom table.

The bound is the one already proven in training_l6_cellfirst/REPORT.md:

    U = min(NT, 12 + C_1 + C_2 + C_3),      total >= ceil(K * NT / U)

where C_a is the largest target chord of the a-th family of opposed emitters.
The 12 non-parallel emitter pairs meet in at most one cell each; each opposed pair
can additionally overlap along a whole chord, which is why 12 is NOT the cap
(enormous #2 creates 36 target cells in a single tick).

Everything this module prints is a proven bound: it can never exceed the length of an
existing valid program, which is checked for all 540 cases.
"""
import sys
sys.dont_write_bytecode = True
import csv
from functools import lru_cache
from sim import Machine, cases, programs, DATASETS

OPPOSED = ((0, 3), (1, 4), (2, 5))


@lru_cache(maxsize=None)
def chord_max(m, d1, d2):
    """Largest number of target cells two opposed rays can cover simultaneously."""
    best = 0
    L = 6 * m.r
    for p in range(L):
        for q in range(L):
            c = (m.rays[p][d1] & m.rays[q][d2] & m.target).bit_count()
            if c > best:
                best = c
    return best


def case_bound(m, K):
    nT = m.target.bit_count()
    C = [chord_max(m, a, b) for a, b in OPPOSED]
    U = min(nT, 12 + sum(C))
    lb = max(K, -(-(K * nT) // U))
    return nT, C, U, lb


def main():
    rows = []
    worst = None
    for ds in ('medium', 'large', 'enormous'):
        cs, ps = cases(ds), programs(ds)
        for i, (c, p) in enumerate(zip(cs, ps), 1):
            m = Machine(c)
            nT, C, U, lb = case_bound(m, c[2])
            T = len(p)
            assert lb <= T, f'{ds} #{i}: bound {lb} exceeds existing program {T}'
            rows.append(dict(dataset=ds, case=i, radius=c[0], K=c[2], target=nT,
                             C1=C[0], C2=C[1], C3=C[2],
                             U=U, rigorous_lb=lb, ticks=T, slack=T - lb))
            if worst is None or T - lb > worst['slack']:
                worst = rows[-1]
    with open('rigorous_bounds.csv', 'w', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print('all 540 cases: rigorous lower bound never exceeds the existing program length')
    for ds in ('medium', 'large', 'enormous'):
        sel = [r for r in rows if r['dataset'] == ds]
        print(f'  {ds:9s} ticks={sum(r["ticks"] for r in sel):5d}  '
              f'bound={sum(r["rigorous_lb"] for r in sel):5d}  slack={sum(r["slack"] for r in sel):5d}')
    print(f'  {"TOTAL":9s} ticks={sum(r["ticks"] for r in rows):5d}  '
          f'bound={sum(r["rigorous_lb"] for r in rows):5d}  slack={sum(r["slack"] for r in rows):5d}')
    print(f'\nlargest U = {max(r["U"] for r in rows)}, largest sum(C) = {max(r["C1"]+r["C2"]+r["C3"] for r in rows)}')
    print(f'cases with a non-empty chord contribution: {sum(1 for r in rows if r["C1"]+r["C2"]+r["C3"] > 0)}/540')
    print(f'worst single case: {worst["dataset"]} #{worst["case"]} ticks={worst["ticks"]} '
          f'bound={worst["rigorous_lb"]} slack={worst["slack"]}')
    print('\nNOTE: the bound is real but weak (slack ~78% of the total). It cannot and must not '
          'be read as achievable savings.')


if __name__ == '__main__':
    main()
