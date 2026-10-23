import json,sys
from pathlib import Path
from collections import defaultdict
B=Path(__file__).parent;sys.path.insert(0,str(B));sys.path.insert(0,str(B.resolve().parents[1]))
from inventory import variants,transform
from optimize_l6_compact import Sim

data=json.loads((B/'inventory.json').read_text());groups=defaultdict(list);solutions=[]
for kind,bb in data['bundles'].items():
 for b in bb:
  P=frozenset(map(tuple,b['P']));key=(b['r'],min(tuple(sorted(v)) for v in variants(P,b['r'])))
  groups[key].append((kind,b))
for group in groups.values():
 if len(group)<2:continue
 for dstkind,dst in group:
  best=dst['program'];source=None
  for srckind,src in group:
   if (srckind,src['case'])==(dstkind,dst['case']):continue
   for f in (False,True):
    for k in range(6):
     if {transform(p,src['r'],k,f) for p in src['P']}!=set(map(tuple,dst['P'])):continue
     case=(dst['r'],frozenset(map(tuple,dst['P'])),dst['K']);sim=Sim(case)
     raw=[]
     for line in src['program']:
      nl=['-']*6
      for i,c in enumerate(line):
       j=((1-i) if f else i)-k;j%=6
       if f:c={'F':'B','B':'F'}.get(c,c)
       nl[j]=c
      raw.append(tuple(nl))
     states=sim.prefix(raw);out=raw[:];s=states[-1]
     if s[3]<dst['K']:
      seen={};loop=None
      for t in range(1,len(states)):
       if states[t][3]==states[t-1][3]:continue
       key=states[t][:2]
       if key in seen:loop=raw[seen[key]:t];break
       seen[key]=t
      if loop:
       # Use the prefix ending at the discovered endpoint before repeating it.
       out=raw[:t];s=states[t]
       for _ in range(dst['K']):
        for line in loop:
         if s[3]>=dst['K']:break
         out.append(line);s=sim.step(s,line)
        if s[3]>=dst['K']:break
     s=sim.initial()
     for t,line in enumerate(out):
      s=sim.step(s,line)
      if s[3]>=dst['K']:
       out=out[:t+1]
       if len(out)<len(best):best=out;source=(srckind,src['case'],k,f)
       break
  if source:
   result=dict(kind=dstkind,case=dst['case'],before=len(dst['program']),after=len(best),source=source,program=best)
   solutions.append(result);print({k:v for k,v in result.items() if k!='program'})
print('savings',sum(x['before']-x['after'] for x in solutions),'wins',len(solutions))
(B/'symmetry_results.json').write_text(json.dumps(solutions,indent=1))
