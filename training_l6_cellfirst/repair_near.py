from native import *
sys.path.insert(0,str(BASE/'repair'));sys.path.insert(0,str(BASE/'scheduler'))
from exact_model import synth
from graph_adapter import *
import argparse
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--limit',type=int,default=30);ap.add_argument('--seconds',type=float,default=2);ap.add_argument('--datasets',default='medium,large,enormous');ap.add_argument('--tag',default='repair');args=ap.parse_args()
    seen=set();files=[]
    for f in (BASE/'repair/near').glob('*.json'):
        x=json.loads(f.read_text())
        if x['dataset'] not in args.datasets.split(','):continue
        key=x['dataset'],x['case'],tuple(tuple(r) for r in x['program']),x['goal']
        if key in seen:continue
        seen.add(key);files.append((x['cost'],x['dataset']=='medium',f,x))
    files.sort(key=lambda v:(v[0],v[1],v[3]['horizon']));selected=[];percase={}
    for _,_,f,x in files:
        key=x['dataset'],x['case']
        if percase.get(key,0)>=2:continue
        percase[key]=percase.get(key,0)+1;selected.append((f,x))
        if len(selected)>=args.limit:break
    engine=Engine()
    try:
        for f,x in selected:
            ds=x['dataset'];i=x['case']-1;c=cases(ds)[i];p=[tuple(row) for row in x['program']];start=x['start'];start=(tuple(start[0]),*start[1:]);sim=Sim(c);ss=[start]
            for row in p:ss.append(sim.step(ss[-1],row))
            rel=sim.target|sim.forbidden;bad=(sim.target&~ss[-1][2])|(sim.forbidden&ss[-1][2]);cells=[j for j in range(len(geometry(c[0])[1])) if bad>>j&1]
            # Rank commands by proximity to a ray through a defect cell, then
            # expand the emitter/window neighborhood only after failed repair.
            opportunities=[]
            for e in range(6):
                best=10**6;bestt=1
                for t in range(1,len(ss)):
                    for cell in cells:
                        for pos in range(6*c[0]):
                            if sim.rays[pos][e]>>cell&1:
                                d=abs(ss[t][0][e]-pos);d=min(d,6*c[0]-d)+int(not (ss[t][1]>>e&1))
                                if d<best:best=d;bestt=t
                opportunities.append((best,e,bestt))
            opportunities.sort();goal=unpack(x['goal']) if x['goal'] is not None else None
            baseline=len(programs(ds)[i]);g=make_graph(ds,i,False);q=START if packed(start)==packed(sim.initial()) and not start[2] else tuple(start[0])+(start[1],)
            for kind in ['command_lns','targeted_cp','ordinary_cp']:
                if kind=='command_lns':
                    pp,_,info=engine.ask(c,start=start,k=x['copies'],horizon=len(p),ms=int(args.seconds*1000),seed=x['seed']+50,mode=8,goal=x['goal'],hint=p);status='FOUND' if pp else 'NO_PROGRAM';elapsed=info['runtime'];ev=info['evaluations']
                else:
                    free=tuple(e for _,e,_ in opportunities[:(3 if kind=='targeted_cp' else 4)])
                    slots=None
                    if kind=='targeted_cp':
                        slots=set()
                        for _,e,t in opportunities[:3]:
                            for tt in range(max(1,t-3),min(len(p),t+3)+1):slots.add((tt,e))
                    pp,info=synth(c,start,len(p),x['copies'],end=goal,hint=ss,free=free,free_slots=slots,seconds=args.seconds,seed=x['seed']+50)
                    status=info['status'];elapsed=info['seconds'];ev=info['branches']
                if pp:
                    # Native simulation of the exact proposed fragment before DP.
                    tracecpp=engine.ask(c,start=start,mode=9,hint=pp);st=start
                    for row,rr in zip(pp,tracecpp):st=sim.step(st,row);assert rr[0]==packed(st) and rr[1]==st[3]
                    g.walk(q,pp,kind);answer,_=g.dp(frontier=4096)
                    if answer:update(ds,i,answer,kind+'_repair_graph',elapsed,ev,x['seed']+50)
                rec=dict(dataset=ds,case=i+1,incumbent=baseline,candidate=len(programs(ds)[i]),saved=baseline-len(programs(ds)[i]),algorithm=kind,runtime=elapsed,evaluations=ev,seed=x['seed']+50,validation=status,near_source=str(f.relative_to(BASE)),free_emitters=[e for _,e,_ in opportunities[:3]],defect_cells=[geometry(c[0])[1][j] for j in cells],near_copies=x['copies'])
                with (BASE/'experiments'/f'{args.tag}.jsonl').open('a') as log:log.write(json.dumps(rec)+'\n')
                print(ds,i+1,kind,status,baseline,'->',len(programs(ds)[i]),flush=True)
    finally:engine.close()
if __name__=='__main__':main()
