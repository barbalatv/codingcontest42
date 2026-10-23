import json

with open('training_medium/diagnosis.json') as f:
    diag = json.load(f)

for c in [5, 6, 7, 8, 9, 12, 13]:
    d = diag[c - 1]
    print(f"Case {c}: Count={d['count']} Total={d['total_len']} Setup={d['first_copy_ticks']} Intervals={d['intervals']}")
