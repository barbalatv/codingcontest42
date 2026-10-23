import sys
import time
from pathlib import Path
from subprocess import Popen, PIPE

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from training_medium.setup_and_manager import MediumManager
from solve_l4 import geometry
from solve_l5 import verify

def run_deep_optimizer(case_indices):
    mgr = MediumManager()
    exe_path = Path(__file__).resolve().parent.parent / 'window_opt_deep.exe'
    engine = Popen([str(exe_path)], stdin=PIPE, stdout=PIPE, text=True, bufsize=1)
    
    t0 = time.time()
    total_saved = 0
    improved_count = 0
    
    print(f"=== Starting Deep Window Optimizer ({len(case_indices)} cases) ===")
    print(f"Current Total: {mgr.current_total()} ticks")
    
    try:
        for idx in case_indices:
            r, pat, count = mgr.cases[idx]
            prog = mgr.best_progs[idx]
            old_len = len(prog)
            
            rows = list(map(list, geometry(r)[0]))
            for y, x in pat:
                rows[y][x] = 'M'
                
            header = f"{r} {count} {old_len}\n"
            grid_str = '\n'.join(''.join(row) for row in rows) + '\n'
            prog_str = f"{old_len}\n" + '\n'.join(' '.join(row) for row in prog) + '\n'
            payload = header + grid_str + prog_str
            
            engine.stdin.write(payload)
            engine.stdin.flush()
            
            resp = engine.stdout.readline().split()
            if not resp:
                continue
                
            new_len = int(resp[0])
            saved = int(resp[1])
            
            if saved > 0 and new_len < old_len:
                candidate = [tuple(token) for token in resp[2:]]
                assert len(candidate) == new_len
                improved, old_len, final_len = mgr.update_case(idx, candidate, 'window_opt_deep')
                if improved:
                    total_saved += (old_len - final_len)
                    improved_count += 1
                    print(f"CASE {idx + 1:3d}: {old_len} -> {final_len} (SAVED {old_len - final_len} TICKS!) [Total: {mgr.current_total()}]", flush=True)
                    
    finally:
        engine.stdin.close()
        engine.wait(timeout=5)
        
    print(f"\nDeep Window Optimizer finished in {time.time() - t0:.1f}s.")
    print(f"Improved {improved_count} cases, saved {total_saved} ticks.")
    print(f"New Total: {mgr.current_total()} ticks.")
    return total_saved

if __name__ == '__main__':
    mgr = MediumManager()
    if len(sys.argv) > 1:
        if sys.argv[1] == 'all':
            batch = list(range(210))
        else:
            batch = [int(x) - 1 for x in sys.argv[1:]]
    else:
        # Default top 30 cases
        batch = sorted(range(210), key=lambda i: len(mgr.best_progs[i]), reverse=True)[:30]
        
    run_deep_optimizer(batch)
