from pathlib import Path
p=Path('training_medium_codex_v2/graph_cycles.py');s=p.read_text().replace("-e['ticks']/e['copies']))","e['ticks']/e['copies']))").replace("if 3<=e['ticks']<=20","if 3<=e['ticks']<=40").replace("e['ticks']<=16","e['ticks']<=32")
s=s.replace("ids=PILOT if args.mode=='pilot' else", "ids=PILOT if args.mode in ('pilot','focused') else")
p.write_text(s)
