import json

diag = json.load(open('training_medium/diagnosis.json'))
setups = [d['first_copy_ticks'] for d in diag]
print(f"Total setup ticks across all 210 cases: {sum(setups)} / 5946 ticks ({sum(setups)/5946*100:.1f}%)")
print(f"Average setup ticks per case: {sum(setups) / len(setups):.2f}")
print(f"Max setup ticks: {max(setups)}")

long_setups = sorted(diag, key=lambda x: x['first_copy_ticks'], reverse=True)[:30]
print(f"{'Case':>5} | {'R':>2} | {'Count':>5} | {'Score':>5} | {'Setup':>5} | {'Cycle/Rate':>12}")
print("-" * 50)
for d in long_setups:
    cyc = d['detected_cycle']
    cyc_str = f"{cyc['period_ticks']}t/{cyc['period_copies']}c" if cyc else f"{d['avg_interval']:.2f}"
    print(f"{d['case']:5d} | {d['r']:2d} | {d['count']:5d} | {d['total_len']:5d} | {d['first_copy_ticks']:5d} | {cyc_str:>12}")
