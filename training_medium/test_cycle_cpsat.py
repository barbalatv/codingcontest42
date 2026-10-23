import sys
import time
from pathlib import Path
from ortools.sat.python import cp_model

BASE_DIR = Path(__file__).resolve().parent
ROOT_DIR = BASE_DIR.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from solve_l6 import parse, origins, delta
from solve_l4 import geometry
from optimize_l6 import Machine, load_programs
from optimize_l6_compact import Sim
from solve_l5 import verify

def solve_free_cycle(case, period, copies=1, time_limit=15.0, workers=8):
    r, pattern, count = case
    m = Machine(*case)
    L = 6 * r
    origin = origins(r)
    
    model = cp_model.CpModel()
    
    # Emitter positions P[t, i] in [0, L-1] and active A[t, i] in {0, 1}
    # for t = 0 .. period
    P = {}
    A = {}
    for t in range(period + 1):
        for i in range(6):
            P[t, i] = model.new_int_var(0, L - 1, f'p_{t}_{i}')
            A[t, i] = model.new_bool_var(f'a_{t}_{i}')
            
    # Periodic boundary: t = 0 matches t = period
    for i in range(6):
        model.add(P[period, i] == P[0, i])
        model.add(A[period, i] == A[0, i])
        
    # Transition rules between t-1 and t:
    # Action per emitter: stay(0), F(-1), B(+1), T(toggle active)
    # If move: active unchanged. If toggle: pos unchanged.
    for t in range(1, period + 1):
        for i in range(6):
            # We can model movement modulo L:
            # dp in {-1, 0, 1} or wrap around
            # Better: bool vars for step types: stay, F, B, T
            is_stay = model.new_bool_var(f'stay_{t}_{i}')
            is_f = model.new_bool_var(f'f_{t}_{i}')
            is_b = model.new_bool_var(f'b_{t}_{i}')
            is_t = model.new_bool_var(f't_{t}_{i}')
            
            model.add(is_stay + is_f + is_b + is_t == 1)
            
            # Pos transitions
            # F: P[t, i] == (P[t-1, i] - 1 + L) % L
            # B: P[t, i] == (P[t-1, i] + 1) % L
            # stay/T: P[t, i] == P[t-1, i]
            # Since L is small (e.g. 18, 24, 30), we can enforce allowed assignments or table!
            # Table of valid (p_prev, a_prev, p_curr, a_curr)
            pass

    # Let's use Table constraint for transitions:
    table = []
    for p in range(L):
        for a in (0, 1):
            # stay
            table.append((p, a, p, a))
            # F
            table.append((p, a, (p - 1 + L) % L, a))
            # B
            table.append((p, a, (p + 1) % L, a))
            # T
            table.append((p, a, p, 1 - a))
            
    for t in range(1, period + 1):
        for i in range(6):
            model.add_allowed_assignments([P[t-1, i], A[t-1, i], P[t, i], A[t, i]], table)
            
    # Relevant cells: target | skirting
    cell_indices = [k for k in range(len(m.cells)) if (m.target | m.forbidden) >> k & 1]
    is_target = {k: bool((m.target >> k) & 1) for k in cell_indices}
    
    # Hit detection for each cell at each tick t in 1..period
    # Ray origins: origin[i][k] is the unique perimeter position where emitter i's ray passes through cell k
    # Emitter i hits cell k at tick t iff (A[t, i] == 1 and P[t, i] == origin[i][k])
    
    # Presence of matter on cell k at tick t: M[t, k] in {0, 1}
    M = {}
    for t in range(period + 1):
        for k in cell_indices:
            M[t, k] = model.new_bool_var(f'm_{t}_{k}')
            
    # Acceptance at tick t: accept[t] in {0, 1}
    accept = {t: model.new_bool_var(f'acc_{t}') for t in range(1, period + 1)}
    model.add(sum(accept.values()) == copies)
    
    # Table for matter update:
    # (prev_m, hits, is_accepted_at_t, is_target_cell, next_m)
    # Rules:
    # If hits >= 3: matter destroyed -> 0
    # If hits == 2: matter created -> 1
    # If hits <= 1: matter unchanged from prev_m
    # If accept[t] == 1 and is_target: after acceptance, target matter is cleared to 0!
    # Also, at acceptance tick, target MUST have matter (before clearing) and skirting MUST NOT have matter!
    
    for t in range(1, period + 1):
        for k in cell_indices:
            hits = []
            for i in range(6):
                req_p = origin[i][k]
                hit_var = model.new_bool_var(f'hit_{t}_{i}_{k}')
                # hit_var == 1 <=> (A[t, i] == 1 and P[t, i] == req_p)
                p_match = model.new_bool_var(f'pm_{t}_{i}_{k}')
                model.add(P[t, i] == req_p).only_enforce_if(p_match)
                model.add(P[t, i] != req_p).only_enforce_if(p_match.Not())
                model.add(hit_var == 1).only_enforce_if([A[t, i], p_match])
                model.add(hit_var == 0).only_enforce_if(A[t, i].Not())
                model.add(hit_var == 0).only_enforce_if(p_match.Not())
                hits.append(hit_var)
                
            n_hits = model.new_int_var(0, 6, f'nhits_{t}_{k}')
            model.add(n_hits == sum(hits))
            
            # Pre-acceptance matter:
            pre_m = model.new_bool_var(f'prem_{t}_{k}')
            # Table: (prev_m, n_hits, pre_m)
            # prev in 0,1; n_hits in 0..6
            pass
            
    # Let's simplify pre_m logic:
    # if n_hits >= 3 => pre_m = 0
    # if n_hits == 2 => pre_m = 1
    # if n_hits <= 1 => pre_m = M[t-1, k]
    matter_trans = []
    for prev_val in (0, 1):
        for h in range(7):
            res = 0 if h >= 3 else 1 if h == 2 else prev_val
            matter_trans.append((prev_val, h, res))
            
    for t in range(1, period + 1):
        for k in cell_indices:
            hits = []
            for i in range(6):
                req_p = origin[i][k]
                hit_var = model.new_bool_var(f'hit_{t}_{i}_{k}')
                p_match = model.new_bool_var(f'pm_{t}_{i}_{k}')
                model.add(P[t, i] == req_p).only_enforce_if(p_match)
                model.add(P[t, i] != req_p).only_enforce_if(p_match.Not())
                model.add(hit_var == 1).only_enforce_if([A[t, i], p_match])
                model.add(hit_var == 0).only_enforce_if(A[t, i].Not())
                model.add(hit_var == 0).only_enforce_if(p_match.Not())
                hits.append(hit_var)
                
            n_hits = model.new_int_var(0, 6, f'nhits_{t}_{k}')
            model.add(n_hits == sum(hits))
            
            pre_m = model.new_bool_var(f'prem_{t}_{k}')
            model.add_allowed_assignments([M[t-1, k], n_hits, pre_m], matter_trans)
            
            # Post-acceptance matter:
            # If accept[t] == 1:
            #   If is_target[k]: pre_m MUST BE 1, and M[t, k] = 0 (cleared)!
            #   If not is_target[k]: pre_m MUST BE 0 (skirting must be clean!), and M[t, k] = 0!
            # If accept[t] == 0:
            #   M[t, k] == pre_m
            if is_target[k]:
                model.add(pre_m == 1).only_enforce_if(accept[t])
                model.add(M[t, k] == 0).only_enforce_if(accept[t])
                model.add(M[t, k] == pre_m).only_enforce_if(accept[t].Not())
            else:
                model.add(pre_m == 0).only_enforce_if(accept[t])
                model.add(M[t, k] == pre_m)
                
    # Periodic matter condition: M[period, k] == M[0, k]
    for k in cell_indices:
        model.add(M[period, k] == M[0, k])
        
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = time_limit
    solver.parameters.num_search_workers = workers
    
    t0 = time.time()
    status = solver.solve(model)
    elapsed = time.time() - t0
    
    print(f"Period {period}, Copies {copies}: Status {solver.status_name(status)} ({elapsed:.2f}s)")
    if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        # Extract program
        cycle_lines = []
        for t in range(1, period + 1):
            line = []
            for i in range(6):
                p_prev = solver.value(P[t-1, i])
                p_curr = solver.value(P[t, i])
                a_prev = bool(solver.value(A[t-1, i]))
                a_curr = bool(solver.value(A[t, i]))
                if a_curr != a_prev:
                    line.append('T')
                elif p_curr == (p_prev + 1) % L:
                    line.append('B')
                elif p_curr == (p_prev - 1 + L) % L:
                    line.append('F')
                else:
                    line.append('-')
            cycle_lines.append(tuple(line))
            
        start_pose = tuple(solver.value(P[0, i]) for i in range(6))
        start_active = sum(int(solver.value(A[0, i])) << i for i in range(6))
        return cycle_lines, (start_pose, start_active)
        
    return None, None

if __name__ == '__main__':
    cases = parse(ROOT_DIR / 'level-6' / 'in_level-6_2-medium.txt')
    c51 = cases[50] # Case 51
    print("Testing Case 51 with Free-Pose Cycle CP-SAT...")
    for period in [4, 5]:
        lines, pose = solve_free_cycle(c51, period=period, copies=1, time_limit=15.0)
        if lines:
            print(f"FOUND CYCLE FOR CASE 51 with P={period}!")
            for l in lines:
                print(' '.join(l))
            break
