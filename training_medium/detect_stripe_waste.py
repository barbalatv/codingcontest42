import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from training_medium.setup_and_manager import MediumManager
from optimize_l6_compact import Sim

mgr = MediumManager()

total_reposition_ticks = 0
case_stats = []

for idx, prog in enumerate(mgr.best_progs):
    r, pat, count = mgr.cases[idx]
    
    # Analyze instructions
    pure_move_ticks = 0
    pure_toggle_ticks = 0
    noop_ticks = 0
    
    for row in prog:
        is_noop = all(ch == '-' for ch in row)
        is_pure_move = any(ch in 'FB' for ch in row) and all(ch in 'FB-' for ch in row)
        is_pure_toggle = any(ch == 'T' for ch in row) and all(ch in 'T-' for ch in row)
        
        if is_noop:
            noop_ticks += 1
        elif is_pure_toggle:
            pure_toggle_ticks += 1
        elif is_pure_move:
            pure_move_ticks += 1
            
    case_stats.append({
        'case': idx + 1,
        'r': r,
        'count': count,
        'len': len(prog),
        'pure_moves': pure_move_ticks,
        'pure_toggles': pure_toggle_ticks,
        'noops': noop_ticks,
        'waste': pure_moves + pure_toggles + noops if 'pure_moves' in locals() else pure_move_ticks + pure_toggle_ticks + noop_ticks
    })

case_stats.sort(key=lambda x: x['waste'], reverse=True)

print(f"{'Case':>5} | {'R':>2} | {'Count':>5} | {'Len':>5} | {'PureMoves':>10} | {'PureToggles':>11} | {'NoOps':>5} | {'TotalWaste':>10}")
print("-" * 75)

for s in case_stats[:30]:
    print(f"{s['case']:5d} | {s['r']:2d} | {s['count']:5d} | {s['len']:5d} | {s['pure_moves']:10d} | {s['pure_toggles']:11d} | {s['noops']:5d} | {s['waste']:10d}")

total_w = sum(s['waste'] for s in case_stats)
print("-" * 75)
print(f"Total pure move + pure toggle + noop lines across all 210 cases: {total_w} / 5946 ticks!")
