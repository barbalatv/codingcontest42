from native import *
from screen import finish_at_k
sys.path.insert(0,str(BASE/'repair'));from exact_model import synth
import argparse
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--limit',type=int,default=24);ap.add_argument('--seconds',type=float,default=1.5);args=ap.parse_args();choices=[];seen=set()
    for folder in ['pass1','pass2','pure_cycles']:
        for f in (BASE/'experiments'/folder).glob('*.json'):
            x=json.loads(f.read_text())
            for r in x.get('rows',[]):
                ds=r['dataset'];i=r['case']-1;c=cases(ds)[i];sim=Sim(c)
                if (sim.target|sim.forbidden).bit_count()>140:continue
                for n in r['near_candidates']:
                    p=[tuple(row) for row in n['program']];projected=len(n.get('prefix',[]))+len(p)+len(n.get('suffix',[]))
                    if not 0<n['cost']<=12 or len(p)>14 or projected>=len(programs(ds)[i]):continue
                    token=ds,i,tuple(p),packed(n['start'])
                    if token in seen:continue
                    seen.add(token);choices.append((n['cost'],len(p),ds,i,r['strategy'],n,str(f.relative_to(BASE))))
    previous=json.loads((BASE/'experiments/final_repair.json').read_text()) if (BASE/'experiments/final_repair.json').exists() else []
    tested={(r['dataset'],r['case'],r['strategy'],r['source']) for r in previous}
    choices.sort(key=lambda x:(x[0],x[1]));selected=[];counts={}
    for q in choices:
        if (q[2],q[3]+1,q[4],q[6]) in tested:continue
        key=q[2],q[3]
        if counts.get(key,0)>=1:continue
        counts[key]=1;selected.append(q)
        if len(selected)>=args.limit:break
    E=Engine();logs=list(previous)
    try:
        for cost,_,ds,i,strategy,n,source in selected:
            c=cases(ds)[i];sim=Sim(c);p=[tuple(row) for row in n['program']];start=(tuple(n['start'][0]),*n['start'][1:]);ss=[start]
            for row in p:ss.append(sim.step(ss[-1],row))
            defects=(sim.target&~ss[-1][2])|(sim.forbidden&ss[-1][2]);related=[]
            for e in range(6):
                score=0
                for t,st in enumerate(ss[1:],1):score+=(sim.rays[st[0][e]][e]&defects).bit_count()*4
                related.append((score,e))
            related.sort(reverse=True);free=tuple(e for _,e in related[:4]);end=unpack(n['goal']) if n['goal'] is not None else None;t=time.process_time();q,info=synth(c,start,len(p),n['copies'],end=end,hint=ss,free=free,seconds=args.seconds,seed=10100000+i*137);before=len(programs(ds)[i])
            if q:
                native=E.ask(c,start=start,mode=9,hint=q);st=start
                for row,rr in zip(q,native):st=sim.step(st,row);assert packed(st)==rr[0] and st[3]==rr[1]
                if n.get('prefix') or n.get('suffix'):candidate=finish_at_k(c,[tuple(z) for z in n.get('prefix',[])]+q+[tuple(z) for z in n.get('suffix',[])])
                elif packed(start)==packed(sim.initial()) and n['copies']==c[2]:candidate=finish_at_k(c,q)
                else:candidate=None
                if candidate:update(ds,i,candidate,f'{strategy}_near_repair',info['seconds'],info['branches'],10100000+i*137)
            rec=dict(dataset=ds,case=i+1,strategy=strategy,algorithm='targeted_near_repair',status=info['status'],runtime=info['seconds'],cpu_seconds=time.process_time()-t,initial_cost=cost,free_emitters=free,incumbent=before,candidate=len(programs(ds)[i]),saved=before-len(programs(ds)[i]),source=source,global_impossibility_proof=False);logs.append(rec);print('FINAL_REPAIR',ds,i+1,info['status'],before,'->',rec['candidate'],flush=True)
            atomic_json(BASE/'experiments/final_repair.json',logs)
    finally:E.close()
if __name__=='__main__':main()
