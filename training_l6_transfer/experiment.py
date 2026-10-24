from native import *
import concurrent.futures,atexit,argparse,random,collections,math

ENGINE=None;FROZEN={};PROFILES={};POLICY={};MEMORY={}

def context(p):return f"r{0 if p['radius']<=4 else 1 if p['radius']<=7 else 2}_k{0 if p['K']==1 else 1 if p['K']<=5 else 2}"

def init(snapshot='baseline',policy='operators/policy.json',catalog='transformation_catalog.json'):
    global ENGINE,FROZEN,PROFILES,POLICY,MEMORY
    from windows_limits import limit_current_process
    MEMORY=limit_current_process(1024);ENGINE=Engine(catalog_path=catalog);atexit.register(ENGINE.close)
    FROZEN={ds:programs(ds,snapshot) for ds in DATASETS}
    PROFILES={(r['dataset'],r['case']):r for r in json.loads((BASE/'similarity_index/profiles.json').read_text())}
    POLICY=json.loads((BASE/policy).read_text()) if (BASE/policy).exists() else {}

def ranking(p):
    raw=POLICY.get('contexts',{}).get(context(p),POLICY.get('global',[1]*5))
    avg=sum(raw[:4])/4
    # A fixed 20% uniform exploration floor is chosen before held-out results.
    return [.2+.8*w/max(.00001,avg) for w in raw]

def feedback(ds,i,before,after,method,seed):
    from forensics import detailed,alignment,segments,reverse_variants
    import difflib
    c=cases(ds)[i];ta=detailed(c,before);tb=detailed(c,after);observed=set()
    after_parts={tuple(p) for a,b,p in segments(tb,after)}
    for a,b,p in segments(ta,before):
        for v,q in enumerate(reverse_variants(p)):
            if q and tuple(q) in after_parts:observed.add(v)
    newrules=[]
    for tag,a,b,u,v in difflib.SequenceMatcher(a=before,b=after,autojunk=False).get_opcodes():
        if tag!='equal' and 1<=b-a<=8 and 0<=v-u<b-a:newrules.append(dict(before=encode(before[a:b]),after=encode(after[u:v]),donors=[[ds,i+1]]))
    existing=json.loads((BASE/'transformation_catalog.json').read_text());known={(tuple(r['before']),tuple(r['after'])) for r in existing['rewrites']}
    novelty=[r for r in newrules if (tuple(r['before']),tuple(r['after'])) not in known]
    atomic_json(BASE/'checkpoints'/f'feedback_{ds}_{i+1}_{len(after)}_{method}.json',dict(dataset=ds,case=i+1,method=method,seed=seed,before=before,after=after,new_rules=novelty,observed_variants=sorted(observed),alignment=alignment(ta,tb,c[0]),priority=len(before)-len(after),proposed_followups='held-out cases with matching short commands / acceptance motif; queued until matched comparison frozen',new_hypothesis=bool(novelty)))

def promote(record):
    ds=record['dataset'];i=record['case']-1
    for row in record['rows']:
        p=[tuple(z) for z in row['program']] if row.get('program') else None
        if not p:continue
        before=programs(ds)[i]
        if update(ds,i,p,f"{row['arm']}_{row['stage']}",row['runtime'],row['evaluations'],row['seed']):feedback(ds,i,before,p,row['arm'],row['seed'])

def run_case(ds,i,ms=600,stage='screen',seed_base=42270000,arms='ABCDE',force_mask=0,force_variants=0):
    c=cases(ds)[i];inc=FROZEN[ds][i];T=len(inc);profile=PROFILES[ds,i+1];seed=seed_base+list(DATASETS).index(ds)*100000+i*137
    rows=[];order=list(arms);random.Random(seed).shuffle(order)
    for arm in order:
        begin=time.perf_counter();pycpu=time.process_time();qinfo=[];candidates=[]
        if arm=='A':
            p,_,info=ENGINE.ask(c,k=c[2],horizon=T-1,hint=inc,mode=7,ms=ms//2,seed=seed);qinfo.append(info)
            if p:candidates.append(p)
            sim=Sim(c);ss=sim.prefix(inc);anchors=[0]+[t for t in range(1,len(ss)) if ss[t][3]>ss[t-1][3]];jobs=[]
            for aidx in range(len(anchors)-1):
                for n in [1,2]:
                    if aidx+n<len(anchors):jobs.append((anchors[aidx+n]-anchors[aidx],anchors[aidx],anchors[aidx+n],n))
            _,a,b,n=max(jobs);start=(ss[a][0],ss[a][1],ss[a][2],0)
            p,_,info=ENGINE.ask(c,start=start,k=n,horizon=b-a-1,hint=inc[a:b],goal=packed(ss[b]) if b<T else None,mode=7,ms=ms-ms//2,seed=seed+1);qinfo.append(info)
            if p:
                full=inc[:a]+p+inc[b:];st=sim.initial()
                for t,command in enumerate(full,1):
                    st=sim.step(st,command)
                    if st[3]==c[2]:candidates.append(full[:t]);break
        else:
            modes={'B':13,'C':14,'D':15,'E':16};weights=[1]*5 if arm=='B' else ranking(profile)
            p,_,info=ENGINE.ask(c,k=c[2],horizon=T-1,hint=inc,mode=modes[arm],ms=ms,seed=seed,weights=weights,operator_mask=force_mask or (31 if arm=='E' else 15),variant_mask=force_variants or None);qinfo.append(info)
            if p:candidates.append(p)
        runtime=time.perf_counter()-begin;cpu=time.process_time()-pycpu+sum(x['cpu_seconds'] for x in qinfo);valid=[];errors=[]
        for p in candidates:
            try:exact(c,p);valid.append(p)
            except AssertionError as e:errors.append(str(e))
        best=min(valid,key=len) if valid else None
        row=dict(dataset=ds,case=i+1,arm=arm,stage=stage,split=profile['split'],family=profile['family'],context=context(profile),incumbent=T,candidate=len(best) if best else None,saved=T-len(best) if best else 0,program=best,seed=seed,budget_ms=ms,runtime=runtime,cpu_seconds=cpu,evaluations=sum(x['evaluations'] for x in qinfo),queries=qinfo,memory_policy=MEMORY,validation='CPP_INTERNAL_PYTHON_PASS' if best else 'NO_SHORTER_PROGRAM',invalid_candidates=errors,predicted_weights=ranking(profile) if arm in 'CDE' else [1]*5,incumbent_structure_used=True)
        rows.append(row)
    return dict(dataset=ds,case=i+1,baseline=T,arm_order=order,rows=rows)

def pilot_case(ds,i,ms=150):
    c=cases(ds)[i];inc=FROZEN[ds][i];profile=PROFILES[ds,i+1];rows=[]
    for op in range(5):
        seed=42090000+i*137+op*17+list(DATASETS).index(ds)*100000;begin=time.perf_counter()
        p,_,info=ENGINE.ask(c,k=c[2],horizon=len(inc)-1,hint=inc,mode=14,ms=ms,seed=seed,operator_mask=1<<op)
        if p:exact(c,p)
        rows.append(dict(dataset=ds,case=i+1,arm='BCDE'[min(op,3)],operator=op,stage='ranking_train',split=profile['split'],context=context(profile),incumbent=len(inc),candidate=len(p) if p else None,saved=len(inc)-len(p) if p else 0,program=p,seed=seed,budget_ms=ms,runtime=time.perf_counter()-begin,cpu_seconds=info['cpu_seconds'],evaluations=info['evaluations'],queries=[info]))
    return dict(dataset=ds,case=i+1,rows=rows)

def train_policy():
    sums=collections.defaultdict(lambda:[dict(saved=0.,cpu=0.,n=0) for _ in range(5)])
    for f in (BASE/'experiments/ranking_train').glob('*.json'):
        x=json.loads(f.read_text())
        for r in x.get('rows',[]):
            for group in ['global',r['context']]:
                v=sums[group][r['operator']];v['saved']+=r['saved'];v['cpu']+=r['cpu_seconds'];v['n']+=1
    # Weak fixed prior: 0.1 tick / 1 CPU-second; no held-out tuning.
    values={g:[(r['saved']+.1)/(r['cpu']+1) for r in rr] for g,rr in sums.items()}
    atomic_json(BASE/'operators/policy.json',dict(global_=values.get('global',[1]*5),**{'global':values.get('global',[1]*5)},contexts={g:w for g,w in values.items() if g!='global'},observations=dict(sums),training='ranking_train geometric families only; primary held-out data unused',objective='expected saved ticks / measured search CPU second',prior_saved=.1,prior_cpu=1,exploration_floor=.2))

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--pilot',action='store_true');ap.add_argument('--ms',type=int,default=600);ap.add_argument('--stage',default='screen');ap.add_argument('--selection',default='');ap.add_argument('--snapshot',default='baseline');ap.add_argument('--arms',default='ABCDE');ap.add_argument('--seed',type=int,default=42270000);ap.add_argument('--catalog',default='operators/catalog_primary_frozen.json');ap.add_argument('--policy',default='operators/policy.json');ap.add_argument('--operator-mask',type=int,default=0);ap.add_argument('--variant-mask',type=int,default=0);args=ap.parse_args()
    stage='ranking_train' if args.pilot else args.stage;folder=BASE/'experiments'/stage;folder.mkdir(exist_ok=True)
    if args.pilot:chosen=json.loads((BASE/'similarity_index/split.json').read_text())['pilot']
    elif args.selection:chosen=json.loads((BASE/args.selection).read_text())
    else:chosen=[(ds,i+1) for ds in DATASETS for i in range(len(cases(ds)))]
    todo=[(ds,idx) for ds,idx in chosen if not (folder/f'{ds}_{idx}.json').exists()]
    atomic_json(folder/'run_config.json',dict(stage=stage,ms=args.ms,seed=args.seed,arms=args.arms,cases=chosen,snapshot=args.snapshot,catalog=args.catalog,operator_mask=args.operator_mask,variant_mask=args.variant_mask,policy_frozen_before_primary=True,workers=4))
    start=time.perf_counter();done=len(chosen)-len(todo)
    with concurrent.futures.ProcessPoolExecutor(max_workers=4,initializer=init,initargs=(args.snapshot,args.policy,args.catalog)) as pool:
        futures={pool.submit(pilot_case,ds,idx-1,args.ms) if args.pilot else pool.submit(run_case,ds,idx-1,args.ms,stage,args.seed,args.arms,args.operator_mask,args.variant_mask):(ds,idx) for ds,idx in todo}
        for future in concurrent.futures.as_completed(futures):
            ds,idx=futures[future];record=future.result();atomic_json(folder/f'{ds}_{idx}.json',record)
            if args.pilot:
                for row in record['rows']:
                    if row['program']:
                        before=programs(ds)[idx-1]
                        if update(ds,idx-1,[tuple(z) for z in row['program']],f"transfer_op{row['operator']}_pilot",row['runtime'],row['evaluations'],row['seed']):feedback(ds,idx-1,before,[tuple(z) for z in row['program']],f"op{row['operator']}",row['seed'])
            else:promote(record)
            done+=1
            if done%12==0 or done==len(chosen):print('PROGRESS',stage,done,'/',len(chosen),'wall',round(time.perf_counter()-start,1),'scores',{d:sum(map(len,programs(d))) for d in DATASETS},flush=True)
    atomic_json(folder/'coverage.json',dict(cases=len(chosen),completed=done,wall_seconds=time.perf_counter()-start))
    if args.pilot:train_policy()

if __name__=='__main__':main()
