from pathlib import Path
p=Path('training_medium_codex/exact_acceptance.py');s=p.read_text();s=s.replace('seed=0,free=()):','seed=0,free=(),root_radius=0):');s=s.replace("if t==0:m.add(v==start[0][e]+L*((start[1]>>e)&1))","if t==0:\n    if root_radius:\n     allowed=[((start[0][e]+d)%L)+L*a for d in range(-root_radius,root_radius+1) for a in range(2)];m.add_allowed_assignments([v],[(z,) for z in allowed])\n    else:m.add(v==start[0][e]+L*((start[1]>>e)&1))")
s=s.replace('prog=[];old=start','prog=[];old=start\n  if root_radius:old=(tuple(solver.value(states[0,e])%L for e in range(6)),sum((solver.value(states[0,e])//L)<<e for e in range(6)),0,0)\n  solved_root=old')
s=s.replace("branches=solver.num_branches)","branches=solver.num_branches,root=solved_root if prog is not None else None)")
p.write_text(s)
