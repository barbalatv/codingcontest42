from exact_acceptance import *
log=BASE/'experiments/joint_log.jsonl'
for idx in [51,81,168,50,36,120,145,159]:
 i=idx-1;c=CASES[i];p=load_programs(BASE/'best'/NAME)[i];sim=Sim(c);ss=sim.prefix(p);acc=[t for t in range(1,len(ss)) if ss[t][3]>ss[t-1][3]]
 found=None
 for a in acc:
  for b in acc:
   if a<b and ss[a][:2]==ss[b][:2] and 1<=ss[b][3]-ss[a][3]<=4:found=(a,b);break
  if found:break
 if not found:continue
 a,b=found;q,info=synth(c,(ss[a][0],ss[a][1],0,0),b-a-1,ss[b][3]-ss[a][3],closed=True,seconds=5,root_radius=1,seed=idx)
 info.update(case=idx,method='joint_free_root_cycle')
 print(info,flush=True)
 with log.open('a') as f:f.write(json.dumps(info)+'\n')
 if not q:continue
 root=info['root'];endpoint=(tuple(root[0]),root[1],0,1)
 for H in range(a,min(a+5,len(p))):
  setup,stat=synth(c,sim.initial(),H,1,end=endpoint,seconds=5,seed=idx)
  stat.update(case=idx,method='joint_setup')
  with log.open('a') as f:f.write(json.dumps(stat)+'\n')
  if setup:
   cand=list(setup);st=sim.prefix(setup)[-1]
   while len(cand)<len(p) and st[3]<c[2]:
    for row in q:
     cand.append(row);st=sim.step(st,row)
     if st[3]>=c[2]:break
   if st[3]==c[2]:update(i,cand,'joint_setup_cycle_cp',info['seconds']+stat['seconds'])
   break
