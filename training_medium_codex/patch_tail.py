from pathlib import Path
p=Path('training_medium_codex/exact_acceptance.py');s=p.read_text().replace("jobs.sort(reverse=True);tested=set()","jobs.sort(reverse=True)\n  if args.mode=='tail':\n   jobs=[(0,max(0,len(p)-w),len(p)) for w in (6,8,10,12) if len(p)>=w and ss[len(p)][3]>ss[max(0,len(p)-w)][3]]\n  tested=set()")
p.write_text(s)
