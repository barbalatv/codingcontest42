from native import *
from windows_limits import limit_current_process
import concurrent.futures,atexit,argparse
E=None;F={}
def init(snapshot):
    global E,F
    limit_current_process(1024);E=Engine('cellfirst_v2.exe');atexit.register(E.close);F={ds:programs(ds,snapshot) for ds in DATASETS}
def task(ds,i,ms):
    c=cases(ds)[i];T=len(F[ds][i]);seed=9100000+list(DATASETS).index(ds)*100000+i*137;cpu=time.process_time();p,_,info=E.ask(c,k=c[2],horizon=T-1,width=32,ms=ms,mode=11,seed=seed);pycpu=time.process_time()-cpu;birth=info.pop('birth_program');near=info.pop('near_program');discoveries=info.pop('pure_discoveries')
    if p:exact(c,p)
    exact(c,birth)
    return dict(dataset=ds,case=i+1,baseline=T,rows=[dict(dataset=ds,case=i+1,strategy='B',pass_name='pure_cycles',incumbent=T,horizon=T-1,candidate=len(p) if p else None,best_of_arm=min(T,len(p)) if p else T,saved=max(0,T-len(p)) if p else 0,program=p,incumbent_structure_used=False,incumbent_trajectory_used=False,state_hints_used=False,incumbent_transitions_used=False,seed=seed,budget_ms=ms,runtime=info['runtime'],search_cpu_seconds=info['cpu_seconds']+pycpu,evaluations=info['evaluations'],configurations=info['configurations'],valid_candidates=int(bool(p)),invalid_candidates=0,validation='CPP_PYTHON_PASS' if p else 'NO_SHORTER_PROGRAM',birth_ticks=len(birth),birth_program=birth,birth_valid=True,pure_discoveries=discoveries,near_candidates=[dict(start=Sim(c).initial(),copies=c[2],goal=None,program=near,cost=info['near_cost'],origin='independent_cycle_macros')] if near else [],queries=[info],solver_status=None)])
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--ms',type=int,default=1500);ap.add_argument('--workers',type=int,default=4);args=ap.parse_args();folder=BASE/'experiments/pure_cycles';folder.mkdir(exist_ok=True);snapshot=BASE/'experiments/pure_cycles_baseline';snapshot.mkdir(exist_ok=True)
    for ds in DATASETS:
        if not (snapshot/name(ds)).exists():save_programs(snapshot/name(ds),programs(ds))
    jobs=[(ds,i) for ds in DATASETS for i,c in enumerate(cases(ds)) if c[2]>=2 and not (folder/f'{ds}_{i+1}.json').exists()];completed=0
    atomic_json(folder/'run_config.json',dict(ms=args.ms,workers=args.workers,eligibility='K>=2; operator has no effect for K=1',snapshot='experiments/pure_cycles_baseline',total=len(jobs),engine_sha256=hashlib.sha256((BASE/'engines/cellfirst_v2.exe').read_bytes()).hexdigest()))
    with concurrent.futures.ProcessPoolExecutor(max_workers=args.workers,initializer=init,initargs=('experiments/pure_cycles_baseline',)) as pool:
        fs={pool.submit(task,ds,i,args.ms):(ds,i) for ds,i in jobs}
        for future in concurrent.futures.as_completed(fs):
            ds,i=fs[future];r=future.result();atomic_json(folder/f'{ds}_{i+1}.json',r);x=r['rows'][0]
            if x['program']:update(ds,i,[tuple(z) for z in x['program']],'B_macro_cycles',x['runtime'],x['evaluations'],x['seed'])
            completed+=1
            if completed%30==0:print('PURE_CYCLES',completed,'/',len(jobs),flush=True)
if __name__=='__main__':main()
