from pathlib import Path
import sys, json, subprocess, hashlib, csv, os, time
from functools import lru_cache
BASE = Path(__file__).resolve().parent
REPO = BASE.parent
sys.path.insert(0, str(REPO))
from solve_l6 import parse
from solve_l5 import verify
from solve_l4 import geometry, STEPS
from optimize_l6 import load_programs, save_programs
from optimize_l6_compact import Sim
DATASETS = {'medium': '2-medium', 'large': '3-large', 'enormous': '4-enormous'}
FIELDS = ['dataset','case','incumbent','candidate','saved','algorithm','runtime','evaluations','seed','validation']
def name(ds): return f'answer_level-6_{DATASETS[ds]}.txt'
@lru_cache(None)
def cases(ds): return parse(REPO/'level-6'/f'in_level-6_{DATASETS[ds]}.txt')
def programs(ds, folder='best'): return load_programs(BASE/folder/name(ds))
def packed(s): return sum((p+128*((s[1]>>e)&1))<<(8*e) for e,p in enumerate(s[0]))
def unpack(q): return (tuple((q>>(8*e))&127 for e in range(6)),sum(((q>>(8*e+7))&1)<<e for e in range(6)),0,0)
def encode(p): return [sum('-FBT'.index(ch)<<(2*e) for e,ch in enumerate(row)) for row in p]
def decode(p): return [tuple('-FBT'[(a>>(2*e))&3] for e in range(6)) for a in p]
def exact(case, p):
    assert p and all(len(row)==6 and all(ch in '-FBT' for ch in row) for row in p)
    sim=Sim(case); st=sim.initial(); accepted=[]
    for t,row in enumerate(p,1):
        old=st[3];st=sim.step(st,row)
        if st[3]!=old: accepted.append(t)
    assert st[3]==case[2] and accepted[-1]==len(p), (st[3],case[2],accepted[-1:] ,len(p))
    assert verify(case[0],case[1],p)==case[2]
    return accepted
def js_check(ds, i, p):
    req=json.dumps(dict(dataset=ds,case=i+1,program=[' '.join(row) for row in p]))
    r=subprocess.run(['node',str(BASE/'validate_sandbox.cjs'),'--single'],input=req,text=True,capture_output=True,check=True)
    return json.loads(r.stdout)
def atomic_json(path, value):
    tmp=path.with_suffix('.tmp');tmp.write_text(json.dumps(value,indent=2),encoding='utf-8');os.replace(tmp,path)
def _update_locked(ds,i,p,algorithm,runtime=0,evaluations=0,seed=0):
    if not p:return False
    bank=programs(ds);old=len(bank[i])
    if len(p)>=old:return False
    c=cases(ds)[i];aa=exact(c,p);js_check(ds,i,p)
    from native import Engine
    engine=Engine('cellfirst_discover.exe' if (BASE/'engines/cellfirst_discover.exe').exists() else 'cellfirst.exe')
    try:
        native=engine.ask(c,mode=9,hint=p);sim=Sim(c);st=sim.initial();rel=sim.target|sim.forbidden
        for row,rr in zip(p,native):
            st=sim.step(st,row);matter=sum(v<<(64*w) for w,v in enumerate(rr[2:]));assert rr[0]==packed(st) and rr[1]==st[3] and matter==st[2]&rel
    finally:engine.close()
    bank[i]=p; target=BASE/'best'/name(ds);tmp=target.with_suffix('.pending');save_programs(tmp,bank)
    assert load_programs(tmp)==bank
    checkpoint=BASE/'checkpoints'/f'{ds}_{i+1}_{old}_{len(p)}_{algorithm}.json'
    atomic_json(checkpoint,dict(dataset=ds,case=i+1,old=old,new=len(p),algorithm=algorithm,program=p,acceptances=aa))
    os.replace(tmp,target)
    with (BASE/'results.csv').open('a',newline='') as f:
        csv.DictWriter(f,FIELDS).writerow(dict(dataset=ds,case=i+1,incumbent=old,candidate=len(p),saved=old-len(p),algorithm=algorithm,runtime=runtime,evaluations=evaluations,seed=seed,validation='CPP_PYTHON_JS_PASS'))
    print('IMPROVED',ds,i+1,old,'->',len(p),algorithm,flush=True)
    return True
def update(ds,i,p,algorithm,runtime=0,evaluations=0,seed=0):
    # Serialize writers of each complete answer bank across experiment processes.
    import msvcrt
    lockpath=BASE/'checkpoints'/f'{ds}.lock'
    with lockpath.open('a+b') as lock:
        lock.seek(0,2)
        if lock.tell()==0:lock.write(b'0');lock.flush()
        lock.seek(0);msvcrt.locking(lock.fileno(),msvcrt.LK_LOCK,1)
        try:return _update_locked(ds,i,p,algorithm,runtime,evaluations,seed)
        finally:lock.seek(0);msvcrt.locking(lock.fileno(),msvcrt.LK_UNLCK,1)
def trace(case,p):
    sim=Sim(case);st=sim.initial();m=dict(new_target=0,repeated_target=0,erased_target=0,new_skirting=0,skirting_tick_cells=0,h2_target=0,h3_target=0,motion=0,toggles=0);aa=[];details=[]
    for t,row in enumerate(p,1):
        old=st;st=sim.step(st,row);one=two=three=0
        for e in range(6):
            if st[1]>>e&1:
                ray=sim.rays[st[0][e]][e];three|=two&ray;two|=one&ray;one|=ray
        h2=two&~three
        v=dict(new_target=(h2&sim.target&~old[2]).bit_count(),repeated_target=(h2&sim.target&old[2]).bit_count(),erased_target=(three&old[2]&sim.target).bit_count(),new_skirting=(h2&sim.forbidden&~old[2]).bit_count(),skirting_tick_cells=(st[2]&sim.forbidden).bit_count(),h2_target=(h2&sim.target).bit_count(),h3_target=(three&sim.target).bit_count(),motion=sum(ch in 'FB' for ch in row),toggles=row.count('T'))
        for k,x in v.items():m[k]+=x
        if st[3]>old[3]:aa.append(t)
        details.append(dict(tick=t,**v,pose=packed(st),matter=str(st[2]&(sim.target|sim.forbidden)),accepted=st[3]))
    m.update(ticks=len(p),target_cells=len(case[1]),copies=case[2],acceptances=aa,first_copy=aa[0],later_mean=(len(p)-aa[0])/(len(aa)-1) if len(aa)>1 else None)
    m['repeat_fraction']=m['repeated_target']/max(1,m['h2_target'])
    return m,details
