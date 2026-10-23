import argparse
import random
import sys
import time
import subprocess
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from solve_l6 import delta
from solve_l4 import geometry
from solve_l5 import verify
from optimize_l6_compact import Sim
from training_medium.setup_and_manager import MediumManager

def get_neighborhoods(case, prog):
    sim = Sim(case)
    states = sim.prefix(prog)
    segments = []
    begin = 0
    for t in range(1, len(states)):
        if states[t][3] > states[t - 1][3]:
            segments.append((begin, t))
            begin = t
            
    options = []
    for lo, hi in segments:
        ones, zeros = sim.target, sim.forbidden
        req = {hi: (ones, zeros)}
        valid = True
        for t in range(hi - 1, lo - 1, -1):
            pos, active, _, _ = states[t + 1]
            one = two = three = 0
            for e in range(6):
                if active >> e & 1:
                    ray = sim.rays[pos[e]][e]
                    three |= two & ray
                    two |= one & ray
                    one |= ray
            if (ones & three) or (zeros & two & ~three):
                # Temporary skirting pollution or beam cancellation at this tick
                valid = False
                break
            ones &= ~two
            zeros &= ~three
            req[t] = (ones, zeros)
            
        if not valid:
            continue
            
        for W in (2, 3, 4, 6, 8, 12, 16, 20, 24, 32, 40):
            for b in sorted(set(range(lo + W, hi, max(2, W // 3))) | {hi - 1}):
                a = b - W
                if a < lo:
                    continue
                s, g = states[a], states[b]
                lower = max(abs(delta(s[0][e], g[0][e], 6 * case[0])) + int((s[1] >> e & 1) != (g[1] >> e & 1)) for e in range(6))
                if lower >= W:
                    continue
                ones, zeros = req[b]
                slack = W - lower
                constraints = ones.bit_count() + zeros.bit_count()
                options.append((slack / (1 + constraints / 25), a, b, ones, zeros, s))
                
    options.sort(reverse=True)
    return sim, options

def optimize_case_relax(engine, case, prog, budget_sec, ms_per_eval, rng):
    best = prog
    deadline = time.perf_counter() + budget_sec
    tested = set()
    attempts = 0
    r, pat, count = case
    rows = list(map(list, geometry(r)[0]))
    words = (len(geometry(r)[1]) + 63) // 64
    for y, x in pat:
        rows[y][x] = 'M'
    board = '\n'.join(map(''.join, rows))
    word_fn = lambda mask: ' '.join(str((mask >> (64 * w)) & ((1 << 64) - 1)) for w in range(words))
    
    while time.perf_counter() < deadline:
        sim, options = get_neighborhoods(case, best)
        key = hash(tuple(best))
        options = [o for o in options if (key, o[1], o[2]) not in tested]
        if not options:
            break
            
        o = options[min(len(options) - 1, int(rng.expovariate(0.2)))]
        _, a, b, ones, zeros, state = o
        tested.add((key, a, b))
        window = best[a:b]
        n = len(window)
        packed = sum((v + 128 * ((state[1] >> k) & 1)) << (8 * k) for k, v in enumerate(state[0]))
        data = f"{r} 1 {n}\n{board}\n{n}\n" + '\n'.join(' '.join(row) for row in window) + f"\n{packed}\n{word_fn(state[2])}\n{word_fn(ones)}\n{word_fn(zeros)}\n{ms_per_eval} {rng.randrange(1000000000)}\n"
        
        engine.stdin.write(data)
        engine.stdin.flush()
        out = engine.stdout.readline().split()
        if len(out) < 2:
            continue
        attempts += 1
        
        saved_in_window = int(out[1])
        if saved_in_window > 0:
            new_win = [tuple(row) for row in out[2:]]
            candidate = best[:a] + new_win + best[b:]
            st = sim.initial()
            finish = None
            for tick, row in enumerate(candidate):
                st = sim.step(st, row)
                if st[3] >= count:
                    finish = tick + 1
                    break
            if finish is not None and finish < len(best):
                best = candidate[:finish]
                
    return best, attempts

def run_relax_medium(case_indices, budget_sec=2.0, ms_per_eval=80, seed=42):
    mgr = MediumManager()
    rng = random.Random(seed)
    
    exe_path = Path(__file__).resolve().parent.parent / 'relaxed_window.exe'
    engine = subprocess.Popen([str(exe_path)], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, bufsize=1)
    
    total_saved = 0
    improved_count = 0
    t0 = time.time()
    
    print(f"=== Starting Relaxed Window Optimization on Medium ({len(case_indices)} cases) ===")
    print(f"Current Total: {mgr.current_total()} ticks | Budget per case: {budget_sec:.1f}s")
    
    try:
        for idx in case_indices:
            case = mgr.cases[idx]
            prog = mgr.best_progs[idx]
            old_len = len(prog)
            
            cand, attempts = optimize_case_relax(engine, case, prog, budget_sec, ms_per_eval, rng)
            if len(cand) < old_len:
                improved, old_len, new_len = mgr.update_case(idx, cand, 'relaxed_window')
                if improved:
                    saved = old_len - new_len
                    total_saved += saved
                    improved_count += 1
                    print(f"CASE {idx + 1:3d}: {old_len} -> {new_len} (SAVED {saved} TICKS in {attempts} tries!) [Total: {mgr.current_total()}]", flush=True)
                    
    finally:
        engine.stdin.close()
        engine.wait(timeout=5)
        
    print(f"\nFinished in {time.time() - t0:.1f}s. Improved {improved_count} cases, saved {total_saved} ticks.")
    print(f"New Total: {mgr.current_total()} ticks.")
    return total_saved

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--budget', type=float, default=2.0)
    parser.add_argument('--ms', type=int, default=80)
    parser.add_argument('--seed', type=int, default=42)
    parser.add_argument('cases', nargs='*')
    args = parser.parse_args()
    
    mgr = MediumManager()
    if args.cases:
        if args.cases[0] == 'all':
            # Sort by longest cases first for maximum leverage
            selected = sorted(range(210), key=lambda i: len(mgr.best_progs[i]), reverse=True)
        else:
            selected = [int(x) - 1 for x in args.cases]
    else:
        # Default top 30 longest cases
        selected = sorted(range(210), key=lambda i: len(mgr.best_progs[i]), reverse=True)[:30]
        
    run_relax_medium(selected, budget_sec=args.budget, ms_per_eval=args.ms, seed=args.seed)
