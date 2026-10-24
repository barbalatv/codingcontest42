from experiment import *
from repair.exact_model import synth

def select():
    jobs=[]
    for f in (BASE/'experiments/screen').glob('*.json'):
        x=json.loads(f.read_text())
        for row in x.get('rows',[]):
            if row['arm']!='A':continue
            ds=row['dataset'];i=row['case']-1;c=cases(ds)[i];inc=programs(ds,'baseline')[i];sim=Sim(c);ss=sim.prefix(inc);anchors=[0]+[t for t in range(1,len(ss)) if ss[t][3]>ss[t-1][3]];windows=[]
            for z in range(len(anchors)-1):
                for k in [1,2]:
                    if z+k<len(anchors):windows.append((anchors[z+k]-anchors[z],anchors[z],anchors[z+k],k))
            _,a,b,k=max(windows)
            contexts=[(0,len(inc),c[2]),(a,b,k)]
            for query,(a,b,k) in zip(row['queries'],contexts):
                near=[tuple(z) for z in query['near_program']];cost=query['near_cost'];projected=a+len(near)+len(inc)-b
                if not near or not 0<cost<=12 or len(near)>12 or len(c[1])>80 or projected>=len(programs(ds)[i]):continue
                start=(ss[a][0],ss[a][1],ss[a][2],0);hint=[start];st=start
                for command in near:st=sim.step(st,command);hint.append(st)
                defects=(sim.target&~st[2])|(sim.forbidden&st[2]);rank=[]
                for e in range(6):rank.append((sum((sim.rays[p][e]&defects).bit_count() for p in range(6*c[0])),e))
                free=[e for _,e in sorted(rank,reverse=True)[:4]]
                jobs.append(dict(dataset=ds,case=i+1,cost=cost,start=start,H=len(near),copies=k,end=ss[b] if b<len(inc) else None,hint=hint,free=free,prefix=inc[:a],suffix=inc[b:],seed=row['seed']+901))
    jobs.sort(key=lambda r:(r['cost'],r['H'],r['dataset'],r['case']))
    chosen=[];seen=set()
    for job in jobs:
        key=job['dataset'],job['case']
        if key not in seen:chosen.append(job);seen.add(key)
        if len(chosen)==12:break
    return chosen

def task(job):
    c=cases(job['dataset'])[job['case']-1];begin=time.perf_counter();cpu=time.process_time()
    p,info=synth(c,job['start'],job['H'],job['copies'],end=job['end'],hint=job['hint'],seconds=1.5,seed=job['seed'],free=job['free'])
    candidate=None
    if p:
        sim=Sim(c);st=sim.initial();full=[tuple(z) for z in job['prefix']]+p+[tuple(z) for z in job['suffix']]
        for t,command in enumerate(full,1):
            st=sim.step(st,command)
            if st[3]==c[2]:candidate=full[:t];exact(c,candidate);break
    return dict(job=job,program=candidate,info=info,cpu_seconds=time.process_time()-cpu,runtime=time.perf_counter()-begin)

def main():
    jobs=select();atomic_json(BASE/'experiments/exact_repair_selection.json',jobs);records=[]
    from windows_limits import limit_current_process
    with concurrent.futures.ProcessPoolExecutor(max_workers=4,initializer=limit_current_process,initargs=(1024,)) as pool:
        for x in pool.map(task,jobs):
            job=x['job'];ds=job['dataset'];idx=job['case'];before=programs(ds)[idx-1]
            if x['program'] and update(ds,idx-1,x['program'],'Hybrid_exact_repair',x['runtime'],0,job['seed']):feedback(ds,idx-1,before,x['program'],'Hybrid_exact_repair',job['seed'])
            records.append(x);atomic_json(BASE/'experiments/exact_repair_results.json',records)
            print('EXACT_REPAIR',ds,idx,x['info'],flush=True)
    if not records:atomic_json(BASE/'experiments/exact_repair_results.json',records)

if __name__=='__main__':main()
