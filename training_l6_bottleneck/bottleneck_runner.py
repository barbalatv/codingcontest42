"""Resumable paired experiments against an immutable best-of-local baseline."""
from native_bottleneck import *
from diagnostics import near_diagnostics,analyze_case,bits
import argparse,atexit,concurrent.futures
ENGINE=None;MEMORY={}
def init_worker(memory_mb=512):
    global ENGINE,MEMORY
    from windows_limits import limit_current_process
    MEMORY=limit_current_process(memory_mb)
    assert MEMORY['applied'],MEMORY
    ENGINE=Engine();atexit.register(ENGINE.close)
def context(c,p,kind):
    sim=Sim(c);ss=sim.prefix(p);T=len(p)
    if kind=='whole':return dict(start=ss[0],copies=c[2],horizon=T-1,prefix=[],suffix=[],hint=p,goal=None,a=0,b=T)
    aa=[0]+[t for t in range(1,T+1) if ss[t][3]>ss[t-1][3]]
    if kind=='tail':b=T;a=max(aa[-2],T-10)
    elif kind=='bridge':
        intervals=[(aa[z+1]-aa[z],aa[z],aa[z+1]) for z in range(len(aa)-2)]
        if not intervals:return context(c,p,'tail')
        _,lo,b=max(intervals);a=max(lo,b-10)
    else:raise ValueError(kind)
    st=(ss[a][0],ss[a][1],ss[a][2],0)
    return dict(start=st,copies=ss[b][3]-ss[a][3],horizon=b-a-1,prefix=p[:a],suffix=p[b:],hint=p[a:b],goal=packed(ss[b]) if b<T else None,a=a,b=b)
def run_query(c,inc,ctx,method,weights,seed,ms,mode=3,dynamic=0,cap=0,hint=None):
    begin=time.perf_counter();pycpu=time.process_time()
    p,edges,info=ENGINE.ask(c,start=ctx['start'],k=ctx['copies'],horizon=ctx['horizon'],width=16,ms=ms,seed=seed,mode=mode,goal=ctx['goal'],hint=hint if hint is not None else (ctx['hint'] if mode==7 else ()),weights=weights,dynamic=dynamic,cap=cap)
    near=info.pop('near_program');info.pop('birth_program');info.pop('pure_discoveries')
    candidate=ctx['prefix']+p+ctx['suffix'] if p else None;raw_candidate=candidate;valid=False;error=None
    if candidate:
        try:
            aa=exact(c,candidate);native_check(ENGINE,c,candidate);valid=len(candidate)<len(inc)
        except Exception as e:error=repr(e);candidate=None
    diag=near_diagnostics(c,near,ctx['start']) if near else None
    if diag:diag['required_copies']=ctx['copies']
    return dict(dataset='enormous',case=0,method=method,seed=seed,width=16,budget_ms=ms,incumbent=len(inc),candidate=len(candidate) if candidate else None,saved=max(0,len(inc)-len(candidate)) if candidate else 0,valid=valid,program=candidate,rejected_program=raw_candidate if error else None,error=error,weights=weights,dynamic=dynamic,cap=cap,mode=mode,context=ctx,near_program=near,near_diagnostics=diag,**info,python_cpu_seconds=time.process_time()-pycpu,total_wall_seconds=time.perf_counter()-begin,memory_policy=MEMORY)
def task(job):
    i,stage,ms=job;c=cases('enormous')[i];p=programs('enormous','baseline')[i];mask=json.loads((BASE/'experiments/bottleneck_cases.json').read_text())[str(i+1)]['cell_ids'];rows=[];seed=6420000+i*137+{'pilot':0,'universal':100000,'modes':200000,'dynamic':300000,'deep':400000,'iterative':500000}[stage]
    if stage=='pilot':
        ctx=context(c,p,'whole')
        for w in [100,150,200,300,500]:rows.append(run_query(c,p,ctx,'standard_beam' if w==100 else f'weighted_{w}',{cell:w for cell in mask} if w!=100 else {},seed,ms))
    elif stage=='universal':
        for kind in ['whole','tail']:
            ctx=context(c,p,kind)
            for w in [100,200]:rows.append(run_query(c,p,ctx,f'{kind}_'+('standard_beam' if w==100 else 'weighted_200'),{cell:w for cell in mask} if w!=100 else {},seed+(0 if kind=='whole' else 1),ms))
    elif stage=='modes':
        for mode in [0,3]:
            for w in [100,200]:rows.append(run_query(c,p,context(c,p,'whole'),f'mode{mode}_w{w}',{cell:w for cell in mask} if w!=100 else {},seed+mode,ms,mode=mode))
        for kind in ['tail','bridge']:
            for w in [100,200]:rows.append(run_query(c,p,context(c,p,kind),f'{kind}_lns_w{w}',{cell:w for cell in mask} if w!=100 else {},seed+7,ms,mode=7))
    elif stage=='dynamic':
        for dynamic,cap in [(0,0),(1,0),(2,0),(3,0),(0,250),(1,250)]:rows.append(run_query(c,p,context(c,p,'tail'),f'dynamic{dynamic}_cap{cap}',{cell:300 for cell in mask},seed,ms,dynamic=dynamic,cap=cap))
    elif stage=='deep':
        for kind in ['whole','tail','bridge']:
            ctx=context(c,p,kind)
            for w in [100,200]:rows.append(run_query(c,p,ctx,f'deep_{kind}_w{w}',{cell:w for cell in mask} if w!=100 else {},seed,ms))
    elif stage=='iterative':
        ctx=context(c,p,'tail')
        for decay in [0,5,7,9]:
            weights={cell:200 for cell in mask};source=None
            for iteration in range(3):
                # Fixed and EMA use identical seeds, context and horizon.
                for method,ww in [('fixed',{cell:200 for cell in mask}),('ema',weights)]:
                    r=run_query(c,p,ctx,f'{method}_decay{decay}_it{iteration}',ww,seed+iteration,ms);r.update(iteration=iteration,decay_numerator=decay,weight_source=source);rows.append(r)
                    if method=='ema':current=r
                source=dict(kind='near_miss',iteration=iteration)
                if current['program']:
                    rr=analyze_case(Sim(c),current['program'],dataset='enormous',index=i+1,radius=c[0],K=c[2],n_target=len(c[1]));newmask={cell for r in rr for cell in r['bottleneck_cell_ids']};source['kind']='accepted_program'
                elif current['near_diagnostics']:
                    d=current['near_diagnostics'];newmask=set(d['missing_target'])|set(d['destroyed_in_last_five']);newmask&=set(bits(Sim(c).target))
                else:newmask=set(mask)
                # floor division, exact integer decay and 100-point current bonus.
                weights={cell:min(500,100+decay*(weights.get(cell,100)-100)//10+(100 if cell in newmask else 0)) for cell in set(weights)|newmask}
    for row in rows:row.update(case=i+1,stage=stage)
    return dict(case=i+1,stage=stage,rows=rows)
def select(stage):
    masks=json.loads((BASE/'experiments/bottleneck_cases.json').read_text())
    if stage=='universal':return list(range(140))
    sparse=[int(k)-1 for k,v in masks.items() if v['sparse_tail']]
    cleanup=[int(k)-1 for k,v in masks.items() if v['cleanup_tail'] and not v['sparse_tail']]
    dense=[int(k)-1 for k,v in masks.items() if v['dense_finale'] and not v['sparse_tail'] and not v['cleanup_tail']]
    if stage=='pilot':return sorted(set(sparse+cleanup[:6]+dense[:6]))
    if stage=='modes':return sparse[:4]+cleanup[:2]+dense[:2]
    ranks={i:0 for i in range(140)}
    for folder in ['pilot','universal']:
        for f in (BASE/'experiments'/folder).glob('case_*.json'):
            x=json.loads(f.read_text());i=x['case']-1
            for r in x['rows']:
                d=r['near_diagnostics'];defects=d['defects'] if d else 999
                ranks[i]=max(ranks[i],1000*r['saved']+(max(0,12-defects)*10 if d and d['accepted']<d['required_copies'] else 0))
    order=sorted(range(140),key=lambda i:(-ranks[i],masks[str(i+1)]['late_final'],i))
    if stage=='deep':
        for f in (BASE/'checkpoints').glob('enormous_*.json'):
            r=json.loads(f.read_text());ranks[r['case']-1]+=10000*r['saved']
        order=sorted(range(140),key=lambda i:(-ranks[i],masks[str(i+1)]['late_final'],i))
    return order[:(12 if stage=='deep' else 8)]
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--stage',choices=['pilot','universal','modes','dynamic','iterative','deep'],required=True);ap.add_argument('--ms',type=int,default=1000);ap.add_argument('--workers',type=int,default=2);args=ap.parse_args()
    folder=BASE/'experiments'/args.stage;folder.mkdir(exist_ok=True)
    ids=[i-1 for i in json.loads((folder/'config.json').read_text())['case_ids']] if (folder/'config.json').exists() else select(args.stage)
    config=dict(stage=args.stage,budget_ms=args.ms,workers=args.workers,case_ids=[i+1 for i in ids],frozen_sha256=sha(BASE/'baseline'/name('enormous')),engine_sha256=sha(BASE/'engines/bottleneck_beam.cpp'),memory_mb_per_worker_and_child=512)
    if (folder/'config.json').exists():assert json.loads((folder/'config.json').read_text())==config,'configuration changed; use a new isolated experiment'
    else:atomic_json(folder/'config.json',config)
    todo=[i for i in ids if not(folder/f'case_{i+1}.json').exists()];validator=Engine();begin=time.perf_counter();completed=len(ids)-len(todo)
    try:
        # Recover a result saved just before an interrupted bank promotion.
        for i in ids:
            path=folder/f'case_{i+1}.json'
            if not path.exists():continue
            for row in json.loads(path.read_text())['rows']:
                if row['valid']:promote(validator,'enormous',i,[tuple(z) for z in row['program']],row['method'],str(path.relative_to(BASE)))
        with concurrent.futures.ProcessPoolExecutor(max_workers=args.workers,initializer=init_worker) as pool:
            futures={pool.submit(task,(i,args.stage,args.ms)):i for i in todo}
            for f in concurrent.futures.as_completed(futures):
                x=f.result();path=folder/f"case_{x['case']}.json";atomic_json(path,x)
                # Worker completed the whole comparable group before promotion.
                for row in x['rows']:
                    if row['valid']:promote(validator,'enormous',x['case']-1,[tuple(z) for z in row['program']],row['method'],str(path.relative_to(BASE)))
                completed+=1
                print('PROGRESS',args.stage,completed,'/',len(ids),'seconds',round(time.perf_counter()-begin,1),'Enormous',sum(map(len,programs('enormous'))),flush=True)
    finally:validator.close()
    receipt=dict(completed_cases=completed,expected_cases=len(ids),wall_seconds=time.perf_counter()-begin,newly_searched_cases=len(todo))
    atomic_json(folder/('resume_receipt.json' if (folder/'coverage.json').exists() else 'coverage.json'),receipt)
    initial={ds:sum(map(len,programs(ds,'baseline'))) for ds in DATASETS};best={ds:sum(map(len,programs(ds))) for ds in DATASETS}
    print('CCC42 LEVEL 6 — BOTTLENECK OPTIMIZATION',args.stage)
    for ds in ['enormous','medium','large']:print(ds.upper(),initial[ds],'->',best[ds])
    screened=len(list((BASE/'experiments/universal').glob('case_*.json')))
    improved=sum(len(a)<len(b) for a,b in zip(programs('enormous'),programs('enormous','baseline')))
    print('TOTAL',sum(initial.values()),'->',sum(best.values()),'SAVED',sum(initial.values())-sum(best.values()),'SCREENED',screened,'/140','IMPROVED',improved,'VALIDATION CPP_PYTHON_VERIFY_ORIGINAL_JS_PASS_FOR_PROMOTIONS')
if __name__=='__main__':main()
