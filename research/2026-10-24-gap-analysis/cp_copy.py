"""Exact minimum-length "one copy" planner for level 6 using CP-SAT.

Given a concrete machine state (pose, active mask, empty relevant matter), find the
shortest block of ticks that produces exactly one accepted copy and ends with an
empty relevant board (so the next copy can be planned the same way).
"""
import sys
sys.dont_write_bytecode = True
from ortools.sat.python import cp_model
from sim import Machine, cases, programs, DATASETS


def ray_table(m, track):
    L = 6 * m.r
    n = m.rel.bit_count()
    return [[(m.rays[pos][track] >> c) & 1 for pos in range(L)] for c in range(n)]


def _and(mdl, a, b, name):
    v = mdl.NewBoolVar(name)
    mdl.AddBoolAnd([a, b]).OnlyEnforceIf(v)
    mdl.AddBoolOr([a.Not(), b.Not(), v])
    return v


def _and3(mdl, a, b, c, name):
    v = mdl.NewBoolVar(name)
    mdl.AddBoolAnd([a, b, c]).OnlyEnforceIf(v)
    mdl.AddBoolOr([a.Not(), b.Not(), c.Not(), v])
    return v


def _or(mdl, a, b, name):
    v = mdl.NewBoolVar(name)
    mdl.AddBoolOr([a, b]).OnlyEnforceIf(v)
    mdl.AddImplication(a, v)
    mdl.AddImplication(b, v)
    return v


def solve_copy(m, start_pos, start_active, p, time_limit=10.0, workers=8):
    """Return a list of p token rows, or None.  Verified exactly afterwards."""
    L = 6 * m.r
    n = m.rel.bit_count()
    tgt = [c for c in range(n) if (m.target >> c) & 1]
    forb = [c for c in range(n) if (m.forbidden >> c) & 1]
    mdl = cp_model.CpModel()

    pos = [[mdl.NewIntVar(0, L - 1, f'p{t}_{i}') for i in range(6)] for t in range(p)]
    act = [[mdl.NewBoolVar(f'a{t}_{i}') for i in range(6)] for t in range(p)]

    for i in range(6):
        for t in range(p):
            prevp = start_pos[i] if t == 0 else pos[t - 1][i]
            preva = ((start_active >> i) & 1) if t == 0 else act[t - 1][i]
            mdl.AddAllowedAssignments([prevp, pos[t][i]],
                                      [(v, (v + d) % L) for v in range(L) for d in (-1, 0, 1)])
            same = mdl.NewBoolVar(f'same{t}_{i}')
            mdl.Add(pos[t][i] == prevp).OnlyEnforceIf(same)
            mdl.Add(pos[t][i] != prevp).OnlyEnforceIf(same.Not())
            toggled = mdl.NewBoolVar(f'tg{t}_{i}')
            mdl.Add(act[t][i] != preva).OnlyEnforceIf(toggled)
            mdl.Add(act[t][i] == preva).OnlyEnforceIf(toggled.Not())
            mdl.AddImplication(toggled, same)

    table = {i: ray_table(m, i) for i in range(6)}
    matter_prev = [None] * n
    for t in range(p):
        hit = []
        for c in range(n):
            terms = []
            for i in range(6):
                v = mdl.NewBoolVar(f'v{t}_{i}_{c}')
                mdl.AddElement(pos[t][i], table[i][c], v)
                terms.append(_and(mdl, act[t][i], v, f'b{t}_{i}_{c}'))
            h = mdl.NewIntVar(0, 6, f'h{t}_{c}')
            mdl.Add(h == sum(terms))
            hit.append(h)
        last = (t == p - 1)
        matter_next = []
        for c in range(n):
            h2 = mdl.NewBoolVar(f'h2_{t}_{c}')
            mdl.Add(hit[c] == 2).OnlyEnforceIf(h2)
            mdl.Add(hit[c] != 2).OnlyEnforceIf(h2.Not())
            h3 = mdl.NewBoolVar(f'h3_{t}_{c}')
            mdl.Add(hit[c] >= 3).OnlyEnforceIf(h3)
            mdl.Add(hit[c] < 3).OnlyEnforceIf(h3.Not())
            prev = matter_prev[c]
            lit = h2 if prev is None else _or(mdl, prev, h2, f"o{t}_{c}")
            mat = _and(mdl, lit, h3.Not(), f'm{t}_{c}')
            matter_next.append(mat)
            if last:
                if c in tgt:
                    mdl.Add(mat == 1)
                elif c in forb:
                    mdl.Add(mat == 0)
        matter_prev = matter_next

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = time_limit
    solver.parameters.num_workers = workers
    st = solver.Solve(mdl)
    if st not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return None
    rows = []
    for t in range(p):
        row = []
        for i in range(6):
            pv = start_pos[i] if t == 0 else solver.Value(pos[t - 1][i])
            cv = solver.Value(pos[t][i])
            av = solver.Value(act[t][i])
            pv_active = ((start_active >> i) & 1) if t == 0 else solver.Value(act[t - 1][i])
            if av != pv_active:
                row.append('T')
            elif (cv - pv) % L == 1:
                row.append('B')
            elif (cv - pv) % L == L - 1:
                row.append('F')
            else:
                row.append('-')
        rows.append(tuple(row))
    return rows


def verify_block(m, state, rows):
    s = state
    accepts = 0
    for r in rows:
        old = s
        s = m.step(s, r)
        if s[3] != old[3]:
            accepts += 1
    ok = accepts == 1 and s[2] == 0
    return ok, accepts, s


if __name__ == '__main__':
    ds = sys.argv[1] if len(sys.argv) > 1 else 'medium'
    idx = int(sys.argv[2]) if len(sys.argv) > 2 else 0
    maxp = int(sys.argv[3]) if len(sys.argv) > 3 else 4
    tl = float(sys.argv[4]) if len(sys.argv) > 4 else 10.0
    case = cases(ds)[idx]
    prog = programs(ds)[idx]
    m = Machine(case)
    st = m.initial_state()
    first = None
    for t, line in enumerate(prog, 1):
        old = st
        st = m.step(st, line)
        if st[3] != old[3]:
            first = t
            break
    print(f'{ds} case {idx+1}: r={case[0]} K={case[2]} nT={m.target.bit_count()} nrel={m.rel.bit_count()} T={len(prog)} first={first}')
    print(' post-accept pose', st[0], 'active', format(st[1], '06b'))
    for p in range(1, maxp + 1):
        rows = solve_copy(m, st[0], st[1], p, tl)
        if not rows:
            print(f'  p={p}: UNSAT/timeout')
            continue
        ok, acc, st2 = verify_block(m, st, rows)
        print(f'  p={p}: model says FOUND, verified={ok} accepts={acc} leftover={st2[2]}')
        for r in rows:
            print('     ', ' '.join(r))
        if ok:
            break
