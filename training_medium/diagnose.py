import sys
import json
from pathlib import Path
from collections import Counter

BASE_DIR = Path(__file__).resolve().parent
ROOT_DIR = BASE_DIR.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from solve_l6 import parse
from optimize_l6 import load_programs
from optimize_l6_compact import Sim

def diagnose_all():
    cases = parse(ROOT_DIR / 'level-6' / 'in_level-6_2-medium.txt')
    progs = load_programs(BASE_DIR / 'best' / 'answer_level-6_2-medium.txt')
    
    results = []
    
    for i, (r, pat, count) in enumerate(cases):
        prog = progs[i]
        sim = Sim((r, pat, count))
        
        state = sim.initial()
        accept_ticks = []
        states_at_accept = []
        
        trace_states = [state]
        noops = 0
        toggles = 0
        moves = 0
        
        for t, line in enumerate(prog):
            if all(ch == '-' for ch in line):
                noops += 1
            for ch in line:
                if ch == 'T': toggles += 1
                elif ch in ('F', 'B'): moves += 1
                
            prev_acc = state[3]
            state = sim.step(state, line)
            trace_states.append(state)
            if state[3] > prev_acc:
                accept_ticks.append(t + 1)
                states_at_accept.append((state[0], state[1])) # (pos, active)
                
        intervals = [accept_ticks[0]]
        for k in range(1, len(accept_ticks)):
            intervals.append(accept_ticks[k] - accept_ticks[k-1])
            
        # Analyze periodic structure
        # Check repeated acceptance states
        seen_states = {}
        detected_cycle = None
        for k, st in enumerate(states_at_accept):
            if st in seen_states:
                prev_k = seen_states[st]
                period_ticks = accept_ticks[k] - accept_ticks[prev_k]
                period_copies = k - prev_k
                detected_cycle = {
                    'start_copy': prev_k + 1,
                    'period_ticks': period_ticks,
                    'period_copies': period_copies,
                    'ticks_per_copy': period_ticks / period_copies
                }
                break
            seen_states[st] = k
            
        # Classification
        classification = []
        if count == 1:
            classification.append('SINGLE_COPY')
        elif detected_cycle is not None:
            if detected_cycle['period_copies'] == 1:
                classification.append('1_COPY_CYCLE')
            else:
                classification.append('MULTI_COPY_CYCLE')
        else:
            classification.append('APERIODIC')
            
        if len(pat) >= 35:
            classification.append('DENSE_PATTERN')
            
        first_copy_cost = accept_ticks[0] if accept_ticks else len(prog)
        tail_intervals = intervals[1:] if len(intervals) > 1 else [first_copy_cost]
        avg_tail_interval = sum(tail_intervals) / len(tail_intervals) if tail_intervals else 0
        
        if first_copy_cost > avg_tail_interval * 2 and count >= 5:
            classification.append('EXPENSIVE_FIRST_CHEAP_REPEAT')
        elif avg_tail_interval > first_copy_cost * 1.5:
            classification.append('CHEAP_FIRST_EXPENSIVE_REPEAT')
            
        # Potential savings if steady period reduced by 1 tick
        if detected_cycle and count > detected_cycle['start_copy']:
            remaining_copies = count - detected_cycle['start_copy']
            pot_savings = (remaining_copies // detected_cycle['period_copies']) * 1
        elif count >= 5:
            pot_savings = count - 1
        else:
            pot_savings = 0
            
        diag = {
            'case': i + 1,
            'r': r,
            'cells': len(pat),
            'count': count,
            'total_len': len(prog),
            'first_copy_ticks': first_copy_cost,
            'intervals': intervals,
            'avg_interval': avg_tail_interval,
            'detected_cycle': detected_cycle,
            'classification': classification,
            'noops': noops,
            'toggles': toggles,
            'moves': moves,
            'potential_savings_per_tick': pot_savings,
            'score_density': len(prog) / count
        }
        results.append(diag)
        
    with open(BASE_DIR / 'diagnosis.json', 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2)
        
    # Print summary and ranking
    print("=== MEDIUM DIAGNOSTIC SUMMARY ===")
    print(f"Total cases: {len(results)}")
    total_ticks = sum(r['total_len'] for r in results)
    print(f"Total score: {total_ticks}")
    
    classes_count = Counter()
    for r in results:
        for c in r['classification']:
            classes_count[c] += 1
    print("\nClass distribution:")
    for c, cnt in classes_count.most_common():
        print(f"  {c}: {cnt}")
        
    print("\n--- TOP 25 HIGHEST POTENTIAL CASES (by Potential Savings from Cycle Reduction) ---")
    ranked_savings = sorted(results, key=lambda x: (x['potential_savings_per_tick'], x['total_len']), reverse=True)
    print(f"{'Case':>4} | {'R':>2} | {'Count':>5} | {'Cells':>5} | {'Score':>5} | {'1st':>3} | {'Cycle':>12} | {'Pot/Tick':>8} | {'Classes'}")
    print("-" * 80)
    for r in ranked_savings[:25]:
        c_str = f"P={r['detected_cycle']['period_ticks']}, C={r['detected_cycle']['period_copies']}" if r['detected_cycle'] else "None"
        classes_str = ','.join(r['classification'])
        print(f"{r['case']:>4} | {r['r']:>2} | {r['count']:>5} | {r['cells']:>5} | {r['total_len']:>5} | {r['first_copy_ticks']:>3} | {c_str:>12} | {r['potential_savings_per_tick']:>8} | {classes_str}")

    print("\n--- TOP 20 LONGEST CASES (by Total Score) ---")
    ranked_score = sorted(results, key=lambda x: x['total_len'], reverse=True)
    print(f"{'Case':>4} | {'R':>2} | {'Count':>5} | {'Cells':>5} | {'Score':>5} | {'1st':>3} | {'Cycle':>12} | {'Classes'}")
    print("-" * 75)
    for r in ranked_score[:20]:
        c_str = f"P={r['detected_cycle']['period_ticks']}, C={r['detected_cycle']['period_copies']}" if r['detected_cycle'] else "None"
        classes_str = ','.join(r['classification'])
        print(f"{r['case']:>4} | {r['r']:>2} | {r['count']:>5} | {r['cells']:>5} | {r['total_len']:>5} | {r['first_copy_ticks']:>3} | {c_str:>12} | {classes_str}")

if __name__ == '__main__':
    diagnose_all()
