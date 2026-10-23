import argparse
from time import perf_counter
from optimize_l6 import ROOT, load_programs, save_programs
from solve_l6 import parse
from solve_l5 import verify
from optimize_l6_compact import Sim
from phase2_run import atomic_save


def super_compact(case, program):
    sim = Sim(case)
    prog = [list(line) for line in program]
    
    def is_valid(p_lines):
        state = sim.initial()
        for l in p_lines:
            state = sim.step(state, l)
            if state[3] >= sim.required:
                return True
        return False

    improved = True
    iterations = 0
    while improved and iterations < 5:
        improved = False
        iterations += 1
        
        # Pass 1: Eliminate redundant toggle pairs
        for e in range(6):
            t = 0
            while t < len(prog):
                if prog[t][e] == 'T':
                    t2 = t + 1
                    while t2 < len(prog) and prog[t2][e] == '-':
                        t2 += 1
                    if t2 < len(prog) and prog[t2][e] == 'T':
                        prog[t][e] = '-'
                        prog[t2][e] = '-'
                        if is_valid(prog):
                            pass
                        else:
                            prog[t][e] = 'T'
                            prog[t2][e] = 'T'
                    t = t2 + 1
                else:
                    t += 1
                    
        # Pass 2: Multi-hop pull shift (pull from t+1..t+4 into t)
        t = 0
        while t < len(prog):
            for e in range(6):
                if prog[t][e] == '-':
                    for delta in [1, 2, 3, 4]:
                        if t + delta >= len(prog): break
                        if all(prog[t+k][e] == '-' for k in range(1, delta)) and prog[t+delta][e] != '-':
                            op = prog[t+delta][e]
                            prog[t][e] = op
                            prog[t+delta][e] = '-'
                            if is_valid(prog):
                                pass
                            else:
                                prog[t][e] = '-'
                                prog[t+delta][e] = op
                            break
            # Remove empty line
            if t < len(prog) and all(ch == '-' for ch in prog[t]):
                candidate = prog[:t] + prog[t+1:]
                if is_valid(candidate):
                    prog = candidate
                    improved = True
                    continue
            t += 1

        # Pass 3: Multi-hop push shift (push from t into t+1..t+4)
        t = len(prog) - 1
        while t >= 0:
            for e in range(6):
                if prog[t][e] != '-':
                    op = prog[t][e]
                    for delta in [1, 2, 3, 4]:
                        if t + delta >= len(prog): break
                        if all(prog[t+k][e] == '-' for k in range(1, delta+1)):
                            prog[t][e] = '-'
                            prog[t+delta][e] = op
                            if is_valid(prog):
                                pass
                            else:
                                prog[t][e] = op
                                prog[t+delta][e] = '-'
                            break
            if t < len(prog) and all(ch == '-' for ch in prog[t]):
                candidate = prog[:t] + prog[t+1:]
                if is_valid(candidate):
                    prog = candidate
                    improved = True
                    t = min(t, len(prog) - 1)
                    continue
            t -= 1

        # Pass 4: Block deletion (size 4, 2, 1)
        for size in [4, 2, 1]:
            i = 0
            while i + size <= len(prog):
                candidate = prog[:i] + prog[i+size:]
                if is_valid(candidate):
                    prog = candidate
                    improved = True
                else:
                    i += 1

    # Final trim to actual acceptance tick
    state = sim.initial()
    for tick, line in enumerate(prog):
        state = sim.step(state, line)
        if state[3] >= sim.required:
            prog = prog[:tick+1]
            break

    return [tuple(l) for l in prog]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--file', default='')
    args = parser.parse_args()
    started = perf_counter()

    for source in sorted(ROOT.glob('in_*.txt')):
        if args.file and args.file not in source.name:
            continue
        cases = parse(source)
        target = source.with_name(source.name.replace('in_', 'answer_', 1))
        programs = load_programs(target)
        old_total = sum(map(len, programs))
        improved_count = 0

        for i, case in enumerate(cases):
            candidate = super_compact(case, programs[i])
            if len(candidate) < len(programs[i]):
                assert verify(case[0], case[1], candidate) == case[2], (source.name, i)
                programs[i] = candidate
                improved_count += 1
            if (i + 1) % 25 == 0:
                atomic_save(target, programs)
                print(f'{source.name}: {i+1}/{len(cases)}, saved {old_total - sum(map(len, programs))}; {perf_counter() - started:.1f}s', flush=True)

        atomic_save(target, programs)
        print(f'{target.name}: {old_total} -> {sum(map(len, programs))}, improved {improved_count}/{len(cases)}; {perf_counter() - started:.1f}s', flush=True)


if __name__ == '__main__':
    main()
