from native import *
from collections import Counter
import concurrent.futures,atexit,argparse
ENGINE=None;FROZEN={};MEMORY_POLICY={}
def init_worker():
    global ENGINE,FROZEN,MEMORY_POLICY
    from windows_limits import limit_current_process
    MEMORY_POLICY=limit_current_process(1024)
    ENGINE=Engine();atexit.register(ENGINE.close);FROZEN={ds:programs(ds,'baseline') for ds in DATASETS}
def finish_at_k(c,p):
    sim=Sim(c);st=sim.initial()
    for t,row in enumerate(p,1):
        st=sim.step(st,row)
        if st[3]==c[2]:return p[:t]
    return None
def run_case(ds,i,ms=1500,seed_base=6100000,passname='pass1'):
    c=cases(ds)[i];inc=FROZEN[ds][i];T=len(inc);sim=Sim(c);ss=sim.prefix(inc);aa=[t for t in range(1,len(ss)) if ss[t][3]>ss[t-1][3]];seed=seed_base+list(DATASETS).index(ds)*100000+i*137
    rows=[]
    for strategy in ['A','B','C']:
        begin=time.perf_counter();pycpu=time.process_time();queries=[];candidates=[];near_candidates=[];discoveries=[];birth=[]
        if strategy=='A':
            q,_,info=ENGINE.ask(c,k=c[2],horizon=T-1,ms=ms//2,seed=seed+1,mode=7,hint=inc)
            if q:candidates.append(q)
            near=info.pop('near_program');info.pop('birth_program');info.pop('pure_discoveries');queries.append(dict(kind='whole',**info))
            if near:near_candidates.append(dict(start=sim.initial(),copies=c[2],goal=None,program=near,cost=info['near_cost'],origin='incumbent_deleted_tick'))
            # Cross-acceptance control uses the actual physical start state.
            anchors=[0]+aa;jobs=[]
            for z in range(len(anchors)-1):
                for count in [1,2]:
                    if z+count>=len(anchors):continue
                    a,b=anchors[z],anchors[z+count]
                    if b-a>1:jobs.append((b-a,a,b,count))
            if jobs:
                _,a,b,k=max(jobs);start=(ss[a][0],ss[a][1],ss[a][2],0);goal=packed(ss[b]) if b<T else None
                q,_,info=ENGINE.ask(c,start=start,k=k,horizon=b-a-1,ms=ms-ms//2,seed=seed+2,mode=7,goal=goal,hint=inc[a:b])
                if q:
                    candidate=finish_at_k(c,inc[:a]+q+inc[b:])
                    if candidate:candidates.append(candidate)
                near=info.pop('near_program');info.pop('birth_program');info.pop('pure_discoveries');queries.append(dict(kind='cross_acceptance',start_tick=a,end_tick=b,**info))
                if near:near_candidates.append(dict(start=start,copies=k,goal=goal,program=near,cost=info['near_cost'],origin='incumbent_cross_acceptance',prefix=inc[:a],suffix=inc[b:]))
        else:
            mode=11 if strategy=='B' else 12
            # Pure B receives no hint, no refs, no incumbent states or transitions.
            q,_,info=ENGINE.ask(c,k=c[2],horizon=T-1,width=32,ms=ms,seed=seed+3,mode=mode,hint=() if strategy=='B' else inc)
            if q:candidates.append(q)
            near=info.pop('near_program');birth=info.pop('birth_program');discoveries=info.pop('pure_discoveries');queries.append(dict(kind='independent' if strategy=='B' else 'fresh_then_historical_repair',**info))
            if near:near_candidates.append(dict(start=sim.initial(),copies=c[2],goal=None,program=near,cost=info['near_cost'],origin='pure_geometry' if strategy=='B' else 'pure_prefix_historical_suffix'))
        runtime=time.perf_counter()-begin;search_cpu=time.process_time()-pycpu+sum(q['cpu_seconds'] for q in queries)
        valid=[];invalid=[];vt=time.perf_counter()
        for candidate in candidates:
            try:exact(c,candidate);valid.append(candidate)
            except AssertionError as e:invalid.append(str(e))
        candidate=min(valid,key=len) if valid else None
        birth_valid=None
        if birth:
            exact(c,birth);birth_valid=True
        near_summary=[]
        for near in near_candidates:
            st=near['start'];last=0
            for t,row in enumerate(near['program'],1):
                old=st[3];st=sim.step(st,row)
                if st[3]>old:last=t
            near_summary.append(dict(cost=near['cost'],accepted=st[3],copies=near['copies'],missing_target=(sim.target&~st[2]).bit_count(),dirty_skirting=(sim.forbidden&st[2]).bit_count(),ticks=len(near['program']),last_acceptance=last))
        row=dict(dataset=ds,case=i+1,strategy=strategy,pass_name=passname,incumbent=T,upper_bound=T,horizon=T-1,candidate=len(candidate) if candidate else None,best_of_arm=min(T,len(candidate)) if candidate else T,saved=max(0,T-len(candidate)) if candidate else 0,program=candidate,incumbent_structure_used=strategy!='B',incumbent_trajectory_used=strategy!='B',state_hints_used=False,incumbent_transitions_used=strategy!='B',seed=seed+(1 if strategy=='A' else 3),budget_ms=ms,memory_policy='bounded_cpp_pools_H256_W128_width32',runtime=runtime,search_cpu_seconds=search_cpu,validation_seconds=time.perf_counter()-vt,evaluations=sum(q['evaluations'] for q in queries),configurations=sum(q['configurations'] for q in queries),valid_candidates=len(valid),invalid_candidates=len(invalid),validation_errors=invalid,validation='CPP_INTERNAL_PYTHON_PASS' if candidate else 'NO_SHORTER_PROGRAM',queries=queries,near_candidates=near_candidates,near_summary=near_summary,birth_program=birth,birth_valid=birth_valid,birth_ticks=len(birth) if birth else None,pure_discoveries=discoveries)
        row['memory_policy']=MEMORY_POLICY;rows.append(row)
    return dict(dataset=ds,case=i+1,baseline=T,rows=rows)
RESULT_FIELDS=['dataset','case','strategy','pass_name','incumbent','horizon','candidate','best_of_arm','saved','incumbent_structure_used','incumbent_trajectory_used','state_hints_used','incumbent_transitions_used','seed','budget_ms','runtime','search_cpu_seconds','evaluations','configurations','valid_candidates','invalid_candidates','validation','birth_ticks','birth_valid']
def consolidate_record(record):
    ds=record['dataset'];i=record['case']-1
    for r in record['rows']:
        if r['program']:update(ds,i,[tuple(row) for row in r['program']],f"{r['pass_name']}_{r['strategy']}",r['runtime'],r['evaluations'],r['seed'])
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--ms',type=int,default=1500);ap.add_argument('--workers',type=int,default=4);ap.add_argument('--seed',type=int,default=6100000);ap.add_argument('--pass-name',default='pass1');ap.add_argument('--indices',default='');ap.add_argument('--datasets',default='medium,large,enormous');args=ap.parse_args()
    folder=BASE/'experiments'/args.pass_name;folder.mkdir(exist_ok=True);todo=[];done=[]
    for ds in args.datasets.split(','):
        ids=list(map(int,args.indices.split(','))) if args.indices else range(1,len(cases(ds))+1)
        for idx in ids:
            path=folder/f'{ds}_{idx}.json'
            if path.exists():done.append(json.loads(path.read_text()))
            else:todo.append((ds,idx-1))
    # Previously completed read-only worker results are safely resumable.
    for record in done:consolidate_record(record)
    atomic_json(folder/'run_config.json',dict(ms=args.ms,workers=args.workers,seed=args.seed,pass_name=args.pass_name,datasets=args.datasets,indices=args.indices,baseline_sha256={ds:hashlib.sha256((BASE/'baseline'/name(ds)).read_bytes()).hexdigest() for ds in DATASETS}))
    start=time.perf_counter();completed=len(done)
    try:
        with concurrent.futures.ProcessPoolExecutor(max_workers=args.workers,initializer=init_worker) as pool:
            futures={pool.submit(run_case,ds,i,args.ms,args.seed,args.pass_name):(ds,i) for ds,i in todo}
            for future in concurrent.futures.as_completed(futures):
                ds,i=futures.pop(future);record=future.result();atomic_json(folder/f'{ds}_{i+1}.json',record);consolidate_record(record);completed+=1
                if completed%12==0 or not futures:print('PROGRESS',args.pass_name,completed,'/',len(done)+len(todo),'seconds',round(time.perf_counter()-start,1),'scores',{d:sum(map(len,programs(d))) for d in DATASETS},flush=True)
    finally:
        records=[x for f in folder.glob('*.json') if 'rows' in (x:=json.loads(f.read_text()))]
        with (BASE/'results.csv').open('w',newline='') as f:
            w=csv.DictWriter(f,RESULT_FIELDS);w.writeheader()
            for directory in [BASE/'experiments/pass1',BASE/'experiments/pass2']:
                for p in directory.glob('*.json'):
                    x=json.loads(p.read_text())
                    if 'rows' not in x:continue
                    for r in x['rows']:w.writerow({k:r.get(k) for k in RESULT_FIELDS})
        atomic_json(folder/'coverage.json',dict(completed_cases=len(records),strategy_counts=dict(Counter(r['strategy'] for rec in records for r in rec['rows'])),elapsed_seconds=time.perf_counter()-start))
if __name__=='__main__':main()
