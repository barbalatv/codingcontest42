import sys
from pathlib import Path
from optimize_l6 import ROOT, load_programs, save_programs
from solve_l6 import parse
from optimize_l6_compact import Sim
import itertools, math, time

CHARS = '-FBT'

def get_emitter_paths(p0, a0, p1, a1, L, length):
    res = []
    def dfs(step, curr_p, curr_a, path):
        if step == L:
            if curr_p == p1 and curr_a == a1:
                res.append(tuple(path))
            return
        for ch in CHARS:
            np = curr_p; na = curr_a
            if ch == 'F': np = (np - 1) % length
            elif ch == 'B': np = (np + 1) % length
            elif ch == 'T': na = not na
            dfs(step + 1, np, na, path + [ch])
    dfs(0, p0, a0, [])
    return res

def optimize_case(case, prog, max_combos=200000):
    sim = Sim(case)
    r = case[0]
    length = 6 * r
    improved = True
    total_saved = 0
    
    while improved:
        improved = False
        states = sim.prefix(prog)
        n = len(prog)
        
        # Try W=3 -> L=2, L=1; W=4 -> L=3, L=2
        for W in (3, 4):
            i = 0
            while i + W <= len(prog):
                s0 = states[i]
                s1 = states[i + W]
                found_shortcut = None
                
                for L in range(1, W):
                    cand_per_emitter = [
                        get_emitter_paths(s0[0][c], bool(s0[1] & (1<<c)), s1[0][c], bool(s1[1] & (1<<c)), L, length)
                        for c in range(6)
                    ]
                    combos = math.prod(len(p) for p in cand_per_emitter)
                    if combos == 0 or combos > max_combos:
                        continue
                    
                    for choice in itertools.product(*cand_per_emitter):
                        lines = [tuple(choice[c][step] for c in range(6)) for step in range(L)]
                        st = s0
                        for line in lines:
                            st = sim.step(st, line)
                        
                        # Exact state match check
                        if st[0] == s1[0] and st[1] == s1[1] and st[2] == s1[2] and st[3] == s1[3]:
                            found_shortcut = lines
                            break
                        # Tail simulation check
                        elif st[0] == s1[0] and st[1] == s1[1] and st[3] == s1[3]:
                            if sim.check(st, prog, i + W) is not None:
                                # Verify full tail finishes
                                tail_st = st
                                for t_idx in range(i + W, len(prog)):
                                    tail_st = sim.step(tail_st, prog[t_idx])
                                if tail_st[3] >= sim.required:
                                    found_shortcut = lines
                                    break
                    if found_shortcut:
                        break
                
                if found_shortcut:
                    saved = W - len(found_shortcut)
                    total_saved += saved
                    prog = prog[:i] + found_shortcut + prog[i + W:]
                    states = sim.prefix(prog)
                    improved = True
                    # Don't increment i, check again from i
                else:
                    i += 1
    return prog, total_saved

if __name__ == '__main__':
    kind = sys.argv[1] if len(sys.argv) > 1 else '4-enormous'
    cases = parse(Path(f'level-6/in_level-6_{kind}.txt'))
    progs = load_programs(Path(f'level-6/answer_level-6_{kind}.txt'))
    
    t0 = time.time()
    total_reduction = 0
    num_improved = 0
    for idx in range(min(10, len(cases))):
        c = cases[idx]
        p = progs[idx]
        new_p, saved = optimize_case(c, p)
        if saved > 0:
            total_reduction += saved
            num_improved += 1
            print(f'Case {idx+1}: {len(p)} -> {len(new_p)} (-{saved} ticks)')
        else:
            print(f'Case {idx+1}: {len(p)} (no change)')
    print(f'Done 10 cases: saved {total_reduction} ticks in {time.time()-t0:.1f}s')
