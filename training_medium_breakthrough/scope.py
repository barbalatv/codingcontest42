from pathlib import Path
B=Path('training_medium_breakthrough');p=B/'graph_cycles.py';s=p.read_text().replace("if 'training_medium_codex_v2' in str(f):continue","if 'training_medium_breakthrough' in str(f):continue");p.write_text(s)
