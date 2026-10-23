from pathlib import Path
p=Path('training_medium_codex/terminal_bounce.py');s=p.read_text().replace("if len(new)>=len(orig):continue","if c_unused := False:continue")
s=s.replace('for a in acc[-5:-1]:','for a in acc[-5:-1]:\n  if len(new)-a>16:continue')
s=s.replace("update(i,cand,'terminal_bounce',0)","update(i,cand,'terminal_bounce',time.perf_counter()-started)")
s=s.replace('base=load_programs', 'started=time.perf_counter()\nbase=load_programs');s=s.replace("if c_unused := False:continue", "# Explore all cases after the successful case-50 pilot.")
s=s.replace("print('BOUNCE_PILOT_DONE',flush=True)","print('BOUNCE_ALL_DONE',time.perf_counter()-started,flush=True)")
Path('training_medium_codex/bounce_all.py').write_text(s)
