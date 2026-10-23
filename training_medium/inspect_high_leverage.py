import json

with open('training_medium/diagnosis.json') as f:
    diag = json.load(f)

# Sort by highest score
high_score = sorted(diag, key=lambda x: x['total_len'], reverse=True)

print(f"{'Case':>5} | {'R':>2} | {'Count':>5} | {'Cells':>5} | {'Score':>5} | {'Setup':>5} | {'AvgInt':>6} | {'Cycle':<12} | {'Intervals'}")
print("-" * 90)

for d in high_score[:35]:
    c_idx = d['case']
    r = d['r']
    cnt = d['count']
    cells = d['cells']
    tot = d['total_len']
    setup = d['first_copy_ticks']
    avg_int = f"{d['avg_interval']:.2f}"
    cyc = d['detected_cycle']
    cyc_str = f"{cyc['period_ticks']}t/{cyc['period_copies']}c" if cyc else "None"
    ints = str(d['intervals'][:6])
    print(f"{c_idx:5d} | {r:2d} | {cnt:5d} | {cells:5d} | {tot:5d} | {setup:5d} | {avg_int:>6} | {cyc_str:<12} | {ints}")
