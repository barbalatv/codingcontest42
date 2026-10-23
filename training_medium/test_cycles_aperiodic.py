import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from training_medium.setup_and_manager import MediumManager
from optimize_l6_cycles import solve_cycle

def test_aperiodic_cases():
    mgr = MediumManager()
    with open(Path(__file__).parent / 'list_aperiodic.py') as f:
        pass
    import json
    diag = json.load(open(Path(__file__).parent / 'diagnosis.json'))
    aperiodic = [d for d in diag if 'APERIODIC' in d['classification']]
    
    print(f"Testing {len(aperiodic)} aperiodic cases with CP-SAT cycle solver...")
    
    total_saved = 0
    for d in aperiodic:
        c_idx = d['case'] - 1
        case = mgr.cases[c_idx]
        cur_len = len(mgr.best_progs[c_idx])
        r, pat, count = case
        
        # Determine min possible period
        for p in range(2, 7):
            cand, status = solve_cycle(case, p, limit=4.0, workers=8)
            if cand and len(cand) < cur_len:
                improved, old_len, new_len = mgr.update_case(c_idx, cand, f'cpsat_p{p}')
                if improved:
                    saved = old_len - new_len
                    total_saved += saved
                    print(f"*** CASE {c_idx + 1:3d}: {old_len} -> {new_len} (SAVED {saved} TICKS! P={p}) [Total: {mgr.current_total()}] ***", flush=True)
                    cur_len = new_len
                    break
            elif status == 2: # FEASIBLE or OPTIMAL
                if cand:
                    print(f"Case {c_idx + 1:3d} (P={p}): found len {len(cand)} vs cur {cur_len}")
                    
    print(f"\nAperiodic cycle search done. Total saved: {total_saved} ticks.")
    print(f"New total: {mgr.current_total()} ticks.")

if __name__ == '__main__':
    test_aperiodic_cases()
