import sys
import time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from training_medium.setup_and_manager import MediumManager
from optimize_l6_super_compact import super_compact

def run_super_compact_on_medium():
    mgr = MediumManager()
    total_saved = 0
    t0 = time.time()
    
    print(f"Starting Super Compact on Medium: Current Total = {mgr.current_total()} ticks")
    
    for i, case in enumerate(mgr.cases):
        orig_prog = mgr.best_progs[i]
        old_len = len(orig_prog)
        cand = super_compact(case, orig_prog)
        if len(cand) < old_len:
            improved, old_len, new_len = mgr.update_case(i, cand, 'super_compact')
            if improved:
                saved = old_len - new_len
                total_saved += saved
                print(f"Case {i+1:3d}: {old_len} -> {new_len} (SAVED {saved} TICKS!) [Total: {mgr.current_total()}]", flush=True)
                
    print(f"\nSuper Compact finished in {time.time() - t0:.1f}s. Total saved: {total_saved} ticks.")
    print(f"New Total: {mgr.current_total()} ticks.")

if __name__ == '__main__':
    run_super_compact_on_medium()
