import json

diag = json.load(open('training_medium/diagnosis.json'))
aperiodic = [d for d in diag if 'APERIODIC' in d['classification']]
print(f"Total aperiodic cases: {len(aperiodic)}")
for d in sorted(aperiodic, key=lambda x: x['total_len'], reverse=True):
    print(f"Case {d['case']:3d}: R={d['r']} Count={d['count']:2d} Cells={d['cells']:2d} Score={d['total_len']:3d} Intervals={d['intervals']}")
