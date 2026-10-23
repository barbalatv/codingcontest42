from exact_acceptance import *
# Reuse newly shortened terminal paths as directed edges and their physical
# reversals; simulate every startup/phase instead of assuming reversibility.
started=time.perf_counter()
base=load_programs(BASE/'baseline'/NAME);best=load_programs(BASE/'best'/NAME)
for i,(orig,new) in enumerate(zip(base,best)):
 # Explore all cases after the successful case-50 pilot.
 c=CASES[i];sim=Sim(c);ss=sim.prefix(new);acc=[t for t in range(1,len(ss)) if ss[t][3]>ss[t-1][3]]
 for a in acc[-5:-1]:
  if len(new)-a>16:continue
  q=new[a:];rev=[tuple('B' if x=='F' else 'F' if x=='B' else x for x in row) for row in q[::-1]]
  for back in [rev,[tuple('------')]+rev[:-1]]:
   for anchor in acc:
    if ss[anchor][:2]!=ss[a][:2]:continue
    cand=new[:anchor];st=ss[anchor]
    for j in range(c[2]*2):
     for row in (q if j%2==0 else back):
      st=sim.step(st,row);cand.append(row)
      if st[3]>=c[2] or len(cand)>=len(new):break
     if st[3]>=c[2] or len(cand)>=len(new):break
    if st[3]==c[2] and len(cand)<len(new):update(i,cand,'terminal_bounce',time.perf_counter()-started)
print('BOUNCE_ALL_DONE',time.perf_counter()-started,flush=True)
