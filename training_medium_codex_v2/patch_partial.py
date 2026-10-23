from pathlib import Path
p=Path('training_medium_codex_v2/partial_replan.py');s=p.read_text().replace('for e in path:',"roots={e['start'] for e in path if e['start']!=START}\n for e in sorted(g.E.values(),key=lambda e:(e['ticks']/e['copies'],e['ticks'])):\n  if e['start'] not in roots or e['copies']>2:continue");p.write_text(s)
