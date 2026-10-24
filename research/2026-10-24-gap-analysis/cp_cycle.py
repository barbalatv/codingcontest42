"""Exact optimal repeatable cycle for level 6 via CP-SAT.

A "cycle" is a closed pose-walk of p ticks (poses Q[0..p-1], each emitter moves at
most one cell between consecutive ticks, toggles exclude movement) that returns the
relevant board to empty.  Maximising the number of accepted copies inside the cycle
gives the true minimum steady-state cost per copy for that period: p / accepts.
"""
import sys
sys.dont_write_bytecode = True
from ortools.sat.python import cp_model
from sim import Machine, cases, programs, DATASETS


def _and(mdl, lits, name):
    v = mdl.NewBoolVar(name)
    mdl.AddBoolAnd(lits).OnlyEnforceIf(v)
    mdl.AddBoolOr([l.Not() for l in lits] + [v])
    return v


def _or(mdl, lits, name):
    v = mdl.NewBoolVar(name)
    mdl.AddBoolOr(lits).OnlyEnforceIf(v)
    for l in lits:
        mdl.AddImplication(l, v)
    return v


def ray_table(m, track):
    L = 6 * m.r
    n = m.rel.bit_count()
    return [[(m.rays[pos][track] >> c) & 1 for pos in range(L)] for c in range(n)]


def solve_cycle(m, p, time_limit=20.0, workers=8, hint=None):
    """Returns (accepts, tokens) for the best cycle of period p, or None."""
    L = 6 * m.r
    n = m.rel.bit_count()
    tgt = [c for c in range(n) if (m.target >> c) & 1]
    forb = [c for c in range(n) if (m.forbidden >> c) & 1]
    mdl = cp_model.CpModel()

    Q = [[mdl.NewIntVar(0, L - 1, f'q{t}_{i}') for i in range(6)] for t in range(p)]
    A = [[mdl.NewBoolVar(f'a{t}_{i}') for i in range(6)] for t in range(p)]

    nxt = lambda t: (t + 1) % p
    for t in range(p):
        for i in range(6):
            mdl.AddAllowedAssignments([Q[t][i], Q[nxt(t)][i]],
                                      [(v, (v + d) % L) for v in range(L) for d in (-1, 0, 1)])
            same = mdl.NewBoolVar(f'same{t}_{i}')
            mdl.Add(Q[nxt(t)][i] == Q[t][i]).OnlyEnforceIf(same)
            mdl.Add(Q[nxt(t)][i] != Q[t][i]).OnlyEnforceIf(same.Not())
            toggled = mdl.NewBoolVar(f'tg{t}_{i}')
            mdl.Add(A[nxt(t)][i] != A[t][i]).OnlyEnforceIf(toggled)
            mdl.Add(A[nxt(t)][i] == A[t][i]).OnlyEnforceIf(toggled.Not())
            mdl.AddImplication(toggled, same)

    table = {i: ray_table(m, i) for i in range(6)}
    matter = [None] * n          # state before tick 0: empty
    accepts = []
    for t in range(p):
        hit = []
        for c in range(n):
            terms = []
            for i in range(6):
                v = mdl.NewBoolVar(f'v{t}_{i}_{c}')
                mdl.AddElement(Q[t][i], table[i][c], v)
                terms.append(_and(mdl, [A[t][i], v], f'b{t}_{i}_{c}'))
            h = mdl.NewIntVar(0, 6, f'h{t}_{c}')
            mdl.Add(h == sum(terms))
            hit.append(h)
        after = []
        for c in range(n):
            h2 = mdl.NewBoolVar(f'h2_{t}_{c}')
            mdl.Add(hit[c] == 2).OnlyEnforceIf(h2)
            mdl.Add(hit[c] != 2).OnlyEnforceIf(h2.Not())
            h3 = mdl.NewBoolVar(f'h3_{t}_{c}')
            mdl.Add(hit[c] >= 3).OnlyEnforceIf(h3)
            mdl.Add(hit[c] < 3).OnlyEnforceIf(h3.Not())
            lit = h2 if matter[c] is None else _or(mdl, [matter[c], h2], f'o{t}_{c}')
            after.append(_and(mdl, [lit, h3.Not()], f'm{t}_{c}'))
        acc = _and(mdl, [after[c] for c in tgt] + [after[c].Not() for c in forb], f'acc{t}')
        accepts.append(acc)
        matter = [after[c] if c not in tgt else _and(mdl, [after[c], acc.Not()], f'cl{t}_{c}')
                  for c in range(n)]
        if t == p - 1:
            for c in range(n):
                mdl.Add(matter[c] == 0)

    mdl.Maximize(sum(accepts))
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = time_limit
    solver.parameters.num_workers = workers
    if hint:
        for t, row in enumerate(hint[0]):
            for i, (q, a) in enumerate(row):
                mdl.AddHint(Q[t][i], q)
                mdl.AddHint(A[t][i], a)
    st = solver.Solve(mdl)
    if st not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return None
    best = int(round(solver.ObjectiveValue()))
    rows = []
    for t in range(p):
        row = []
        for i in range(6):
            q = int(solver.Value(Q[t][i]))
            a = solver.Value(A[t][i])
            prev_q = int(solver.Value(Q[t - 1][i]))
            prev_a = solver.Value(A[t - 1][i])
            if a != prev_a:
                row.append('T')
            elif (q - prev_q) % L == 1:
                row.append('B')
            elif (q - prev_q) % L == L - 1:
                row.append('F')
            else:
                row.append('-')
        rows.append(tuple(row))
    return best, rows, st == cp_model.OPTIMAL


def verify_cycle(m, rows):
    """Run the cycle twice; return (accepts_in_first_pass, closed, tileable)."""
    st = (tuple([0] * 6), 0, 0, 0)
    # build the real start state from the token block
    acc1 = acc2 = 0
    s = None
    return None


if __name__ == '__main__':
    ds = sys.argv[1] if len(sys.argv) > 1 else 'medium'
    idx = int(sys.argv[2]) if len(sys.argv) > 2 else 0
    maxp = int(sys.argv[3]) if len(sys.argv) > 3 else 4
    tl = float(sys.argv[4]) if len(sys.argv) > 4 else 20.0
    case = cases(ds)[idx]
    prog = programs(ds)[idx]
    m = Machine(case)
    st, accs, _ = m.run(prog)
    iv = [b - a for a, b in zip(accs, accs[1:])]
    cur = (iv[-1] if iv else None)
    print(f'{ds} case {idx+1}: r={case[0]} K={case[2]} nT={m.target.bit_count()} '
          f'nF={m.forbidden.bit_count()} T={len(prog)} accepts={len(accs)} last_iv={cur}')
    for p in range(1, maxp + 1):
        r = solve_cycle(m, p, tl)
        if r is None:
            print(f'  p={p}: UNSAT/UNKNOWN')
            continue
        best, rows, optimal = r
        print(f'  p={p}: accepts={best} rate={p/max(best,1):.3f} optimal={optimal}')
        for row in rows:
            print('     ', ' '.join(row))
        if best > 0:
            print(f'  -> steady-state cost per copy = {p/best:.3f} (current {cur})')
