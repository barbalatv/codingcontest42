from exact_acceptance import *
results=[]
for idx in [51,168,120]:
 i=idx-1;c=CASES[i];sim=Sim(c);p=load_programs(BASE/'baseline'/NAME)[i];ss=sim.prefix(p);acc=[t for t in range(1,len(ss)) if ss[t][3]>ss[t-1][3]];a,b=acc[0],acc[min(2,len(acc)-1)]
 q,info=synth(c,ss[a],b-a,ss[b][3]-ss[a][3],end=ss[b],hint=ss[a:b+1],free=(-1,),seconds=2)
 assert q is not None,(idx,info)
 results.append(dict(case=idx,**info));print('INCUMBENT_CP_WITNESS_PASS',idx,info['status'],flush=True)
(BASE/'experiments/cp_witnesses.json').write_text(json.dumps(results,indent=2))
