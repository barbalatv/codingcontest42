import sys, os, time, argparse
from pathlib import Path
from ortools.sat.python import cp_model

from solve_l6 import parse, origins, delta
from optimize_l6 import ROOT, Machine, Done, load_programs, save_programs
from optimize_l6_compact import Sim
from solve_l5 import verify
from phase2_run import atomic_save

def solve_multi(case, program, H, copies=2, offset=0, seconds=10.0, workers=8):
    r, pat, K = case
    sim = Sim(case)
    states = sim.prefix(program)
    accepted = [s for s in states if s[3] > 0]
    if not accepted:
        return None, "NO_ACCEPTED"
    anchor, activation = accepted[0][:2]
    m = Machine(*case)
    L = 6 * r
    model = cp_model.CpModel()
    P = {}
    A = {}
    Z = {}

    for t in range(H + 1):
        D = min(t, H - t) + offset
        for i in range(6):
            P[t, i] = model.new_int_var(-D, D, f'p{t}_{i}')
            A[t, i] = model.new_bool_var(f'a{t}_{i}')
            if not offset and t in (0, H):
                model.add(A[t, i] == bool(activation >> i & 1))
            if t:
                dd = model.new_int_var(-1, 1, f'd{t}_{i}')
                model.add(dd == P[t, i] - P[t - 1, i])
                model.add_allowed_assignments(
                    [dd, A[t - 1, i], A[t, i]],
                    [(d, a, b) for d in (-1, 0, 1) for a in (0, 1) for b in (0, 1) if d == 0 or a == b]
                )
                Z[t, i] = {}
                for q in range(-D, D + 1):
                    z = model.new_bool_var(f'z{t}_{i}_{q}')
                    model.add(P[t, i] == q).only_enforce_if(z)
                    Z[t, i][q] = z
                model.add(sum(Z[t, i].values()) == A[t, i])

    for i in range(6):
        model.add(P[H, i] == P[0, i])
        model.add(A[H, i] == A[0, i])

    before = {}
    after = {}
    accept = {t: model.new_bool_var(f'accept{t}') for t in range(1, H + 1)}
    cellids = [k for k in range(len(m.cells)) if (m.target | m.forbidden) >> k & 1]
    transition = [(prev, h, 0 if h >= 3 else 1 if h == 2 else prev) for prev in (0, 1) for h in range(7)]

    for k in cellids:
        prev = 0
        istarget = bool(m.target >> k & 1)
        for t in range(1, H + 1):
            hits = []
            for i in range(6):
                for q, z in Z[t, i].items():
                    if (anchor[i] + q) % L == m.origins[i][k]:
                        hits.append(z)
            n = model.new_int_var(0, 6, f'n{t}_{k}')
            model.add(n == sum(hits))
            b = model.new_bool_var(f'b{t}_{k}')
            before[t, k] = b
            model.add_allowed_assignments([prev, n, b], transition)
            a = model.new_bool_var(f'm{t}_{k}')
            after[t, k] = a
            if istarget:
                model.add(a <= b)
                model.add(a + accept[t] <= 1)
                model.add(a >= b - accept[t])
                model.add(b == 1).only_enforce_if(accept[t])
            else:
                model.add(a == b)
                model.add(b == 0).only_enforce_if(accept[t])
            prev = a

    for t in range(1, H + 1):
        model.add_bool_or([accept[t]] + [before[t, k].Not() if m.target >> k & 1 else before[t, k] for k in cellids])

    model.add(sum(accept.values()) == copies)
    model.add(accept[H] == 1)

    # Hints
    ats = [t for t in range(1, len(states)) if states[t][3] > states[t - 1][3]]
    if len(ats) >= 2:
        begin = ats[0]
        end = ats[min(copies, len(ats) - 1)]
        for t in range(H + 1):
            s = states[begin + round(t * (end - begin) / H)]
            for i in range(6):
                q = delta(anchor[i], s[0][i], L)
                D = min(t, H - t) + offset
                model.add_hint(P[t, i], max(-D, min(D, q)))
                model.add_hint(A[t, i], bool(s[1] >> i & 1))

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = seconds
    solver.parameters.num_search_workers = workers
    status = solver.solve(model)

    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return None, solver.status_name(status)

    start = (tuple((anchor[i] + solver.value(P[0, i])) % L for i in range(6)), sum(solver.value(A[0, i]) << i for i in range(6)))
    lines = []
    for t in range(1, H + 1):
        line = []
        for i in range(6):
            d = solver.value(P[t, i]) - solver.value(P[t - 1, i])
            toggle = solver.value(A[t, i]) != solver.value(A[t - 1, i])
            line.append('T' if toggle else 'B' if d > 0 else 'F' if d < 0 else '-')
        lines.append(tuple(line))

    s = (*start, 0, 0)
    for line in lines:
        s = sim.step(s, line)
    assert s[3] == copies and s[:2] == start and (s[2] & (m.target | m.forbidden) == 0)
    return dict(start=start, lines=lines), solver.status_name(status)

def combine(case, program, loop):
    sim = Sim(case)
    s = sim.initial()
    out = []
    states = sim.prefix(program)
    prefix = next((t for t in range(1, len(states)) if states[t][3] and states[t][:2] == (tuple(loop['start'][0]), loop['start'][1]) and states[t][2] & (sim.target | sim.forbidden) == 0), None)
    if prefix is not None:
        out = list(program[:prefix])
        s = states[prefix]
    else:
        pos = loop['start'][0]
        while s[0] != tuple(pos):
            line = tuple('-' if p == q else 'B' if delta(p, q, 6 * case[0]) > 0 else 'F' for p, q in zip(s[0], pos))
            out.append(line)
            s = sim.step(s, line)
        line = tuple('T' if loop['start'][1] >> i & 1 else '-' for i in range(6))
        out.append(line)
        s = sim.step(s, line)
    for _ in range(case[2] + 2):
        for line in loop['lines']:
            if s[3] >= case[2]:
                return out
            out.append(line)
            s = sim.step(s, line)
    return None

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--dataset', default='2-medium')
    p.add_argument('--cases', default='')
    p.add_argument('--seconds', type=float, default=6.0)
    p.add_argument('--copies', type=int, default=2)
    p.add_argument('--offset', type=int, default=0)
    args = p.parse_args()

    source = ROOT / f'in_level-6_{args.dataset}.txt'
    target = ROOT / f'answer_level-6_{args.dataset}.txt'
    cases = parse(source)
    programs = load_programs(target)

    if args.cases:
        indices = [int(x) - 1 for x in args.cases.split(',')]
    else:
        indices = [i for i, c in enumerate(cases) if c[2] >= 3 and len(programs[i]) >= 40]

    print(f'Starting multi-cycle search on {len(indices)} cases in {args.dataset}...')
    total_improved = 0
    total_saved = 0

    for i in indices:
        case = cases[i]
        r, pat, count = case
        prog = programs[i]
        sim = Sim(case)
        states = sim.prefix(prog)
        ats = [t for t in range(1, len(states)) if states[t][3] > states[t - 1][3]]
        if len(ats) < 2:
            continue
        gaps = [ats[k] - ats[k - 1] for k in range(1, min(len(ats), 4))]
        avg_gap = sum(gaps) / len(gaps)
        max_H = int(avg_gap * args.copies)

        improved_case = False
        # Try horizons strictly shorter than current effective multi-cycle
        for H in range(max_H - 1, max(2, int(max_H * 0.6) - 1), -1):
            found, status = solve_multi(case, prog, H, copies=args.copies, offset=args.offset, seconds=args.seconds)
            if found:
                cand = combine(case, prog, found)
                if cand and len(cand) < len(prog):
                    assert verify(r, pat, cand) == count
                    saved = len(prog) - len(cand)
                    print(f'SUCCESS! Case {i+1}: {len(prog)} -> {len(cand)} (-{saved} ticks) with H={H}, copies={args.copies}', flush=True)
                    programs[i] = cand
                    atomic_save(target, programs)
                    total_saved += saved
                    total_improved += 1
                    improved_case = True
                    break
        if not improved_case:
            print(f'Case {i+1}: current={len(prog)}, tested down to H={max(2, int(max_H * 0.6))}, no shorter cycle found.', flush=True)

    print(f'=== Multi-cycle complete: saved {total_saved} ticks across {total_improved} cases! ===')

if __name__ == '__main__':
    main()
