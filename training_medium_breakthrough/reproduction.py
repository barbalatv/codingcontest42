from pathlib import Path
p=Path('training_medium_breakthrough/run_geometry.py');s=p.read_text().replace('prog=actions(out[5:]);assert len(prog)==out[0]','prog=actions(out[5:5+out[0]]);assert len(prog)==out[0]');p.write_text(s)
p=Path('training_medium_breakthrough/synthesis_experiment.py');s=p.read_text().replace("near_start=6+out[0];near_root=out[near_start];near_program=actions(out[near_start+1:]);", "near_start=6+out[0];near_root=out[near_start] if near_start<len(out) else 0;near_program=actions(out[near_start+1:]) if near_start<len(out) else [];")
s=s.replace("data=f'{c[0]} {copies} {H} {args.ms} {seed}\\n{board(c)}\\n{len(hint)} {packed(hintroot)}\\n'+' '.join(str(sum('-FBT'.index(ch)<<(2*e) for e,ch in enumerate(row))) for row in hint)+'\\n';", "data=f'{c[0]} {copies} {H} {args.ms} {seed}\\n{board(c)}\\n'\n    if not args.old_input:data+=f'{len(hint)} {packed(hintroot)}\\n'+' '.join(str(sum('-FBT'.index(ch)<<(2*e) for e,ch in enumerate(row))) for row in hint)+'\\n'\n    ")
s=s.replace("ap.add_argument('--macro',action='store_true');run", "ap.add_argument('--macro',action='store_true');ap.add_argument('--old-input',action='store_true');run")
p.write_text(s)
