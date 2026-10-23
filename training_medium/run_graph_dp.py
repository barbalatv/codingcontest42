import sys
import time
from pathlib import Path
from subprocess import Popen, PIPE

BASE_DIR = Path(__file__).resolve().parent
ROOT_DIR = BASE_DIR.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from solve_l6 import parse
from solve_l4 import geometry
from solve_l5 import verify
from optimize_l6_compact import Sim
from training_medium.setup_and_manager import MediumManager

def run_case_graph_dp(case_idx, manager, engine_proc=None):
    case = manager.cases[case_idx]
    incumbent_prog = manager.best_progs[case_idx]
    r, pat, count = case
    
    if count <= 1:
        return 0 # single copy case, graph dp for multiple copies not needed
        
    sim = Sim(case)
    st = sim.initial()
    
    seed_poses = []
    accept_ticks = []
    
    for t, line in enumerate(incumbent_prog):
        prev = st[3]
        st = sim.step(st, line)
        if st[3] > prev:
            accept_ticks.append(t + 1)
            # pack pose
            p_int = sum((st[0][i] | (((st[1] >> i) & 1) << 7)) << (8 * i) for i in range(6))
            if p_int not in seed_poses:
                seed_poses.append(p_int)
                
    if not accept_ticks:
        return 0
        
    setup_prog = incumbent_prog[:accept_ticks[0]]
    rows = list(map(list, geometry(r)[0]))
    for y, x in pat: rows[y][x] = 'M'
    
    payload = f"{r} {count} {len(incumbent_prog)}\n"
    payload += '\n'.join(''.join(row) for row in rows) + '\n'
    payload += f"{len(seed_poses)}\n"
    payload += ' '.join(map(str, seed_poses)) + '\n'
    payload += f"{len(setup_prog)}\n"
    payload += '\n'.join(' '.join(line) for line in setup_prog) + '\n'
    
    local_proc = False
    if engine_proc is None:
        engine_proc = Popen(['graph_dp_optimizer.exe'], stdin=PIPE, stdout=PIPE, text=True)
        local_proc = True
        
    t0 = time.time()
    engine_proc.stdin.write(payload)
    engine_proc.stdin.flush()
    
    out = engine_proc.stdout.readline().split()
    if local_proc:
        engine_proc.stdin.close()
        engine_proc.wait()
        
    if not out:
        return 0
        
    new_len = int(out[0])
    saved = int(out[1])
    
    if saved > 0 and new_len < len(incumbent_prog):
        cand = [tuple(token) for token in out[2:]]
        assert len(cand) == new_len
        improved, old_len, final_len = manager.update_case(case_idx, cand, 'graph_dp')
        if improved:
            print(f"CASE {case_idx + 1}: {old_len} -> {final_len} (SAVED {saved} TICKS!) [{time.time() - t0:.2f}s]", flush=True)
            return saved
            
    return 0

def run_graph_dp_on_cases(case_indices):
    mgr = MediumManager()
    engine = Popen(['graph_dp_optimizer.exe'], stdin=PIPE, stdout=PIPE, text=True, bufsize=1)
    total_saved = 0
    t_start = time.time()
    
    try:
        for idx in case_indices:
            saved = run_case_graph_dp(idx, mgr, engine)
            total_saved += saved
    finally:
        engine.stdin.close()
        engine.wait()
        
    print(f"\nGraph DP finished: saved {total_saved} ticks in {time.time() - t_start:.1f}s")
    print(f"New total: {mgr.current_total()} ticks")

if __name__ == '__main__':
    mgr = MediumManager()
    # Test on priority cases: 81, 10, 26, 132, 54, 94, 51, 50, 36
    priority_cases = [80, 9, 25, 131, 53, 93, 50, 49, 35] # 0-based
    if len(sys.argv) > 1:
        if sys.argv[1] == 'all':
            priority_cases = list(range(210))
        else:
            priority_cases = [int(x) - 1 for x in sys.argv[1:]]
            
    run_graph_dp_on_cases(priority_cases)
