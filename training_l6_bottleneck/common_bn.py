"""Isolated experiment utilities. All case numbers in persisted records are 1-based."""
import sys
sys.dont_write_bytecode = True
from pathlib import Path
import csv, hashlib, json, os, subprocess, time
from functools import lru_cache
BASE = Path(__file__).resolve().parent
REPO = BASE.parent
sys.path.insert(0, str(REPO))
from optimize_l6 import load_programs, save_programs
from optimize_l6_compact import Sim
from solve_l4 import geometry
from solve_l5 import verify
from solve_l6 import parse
DATASETS = {'medium':'2-medium', 'large':'3-large', 'enormous':'4-enormous'}
def name(ds): return f'answer_level-6_{DATASETS[ds]}.txt'
@lru_cache(None)
def cases(ds): return parse(REPO/'level-6'/f'in_level-6_{DATASETS[ds]}.txt')
def programs(ds, folder='best'): return load_programs(BASE/folder/name(ds))
def packed(s): return sum((p+128*((s[1]>>e)&1))<<(8*e) for e,p in enumerate(s[0]))
def encode(p): return [sum('-FBT'.index(ch)<<(2*e) for e,ch in enumerate(row)) for row in p]
def decode(p): return [tuple('-FBT'[(a>>(2*e))&3] for e in range(6)) for a in p]
def atomic_json(path, value):
    path=Path(path); path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_suffix('.pending'); tmp.write_text(json.dumps(value,indent=2),encoding='utf-8'); os.replace(tmp,path)
def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def exact(c,p):
    assert p and all(len(row)==6 and all(ch in '-FBT' for ch in row) for row in p)
    sim=Sim(c); st=sim.initial(); aa=[]
    for t,row in enumerate(p,1):
        old=st[3]; st=sim.step(st,row)
        if st[3]>old: aa.append(t)
        assert st[3]<=c[2]
    assert st[3]==c[2] and aa[-1]==len(p),(st[3],c[2],aa,len(p))
    assert verify(c[0],c[1],p)==c[2]
    return aa
def js_check(ds,i,p):
    r=subprocess.run(['node',str(BASE/'validate_sandbox.cjs'),'--single'],input=json.dumps(dict(dataset=ds,case=i+1,program=[' '.join(row) for row in p])),text=True,capture_output=True,check=True)
    return json.loads(r.stdout)
def native_check(engine,c,p):
    rows=engine.ask(c,mode=9,hint=p); sim=Sim(c); st=sim.initial(); rel=sim.target|sim.forbidden
    assert len(rows)==len(p)
    for command,rr in zip(p,rows):
        st=sim.step(st,command)
        assert rr[0]==packed(st) and rr[1]==st[3] and sum(v<<(64*w) for w,v in enumerate(rr[2:]))==st[2]&rel
    return True
def promote(engine,ds,i,p,method,record):
    bank=programs(ds); old=len(bank[i])
    if not p or len(p)>=old:return False
    begin=time.perf_counter(); aa=exact(cases(ds)[i],p); native_check(engine,cases(ds)[i],p); js=js_check(ds,i,p)
    assert aa==js['acceptances']
    checkpoint=dict(dataset=ds,case=i+1,old=old,new=len(p),saved=old-len(p),method=method,program=p,acceptances=aa,validation='CPP_PYTHON_VERIFY_ORIGINAL_JS_PASS',validation_seconds=time.perf_counter()-begin,source_record=record)
    atomic_json(BASE/'checkpoints'/f'{ds}_{i+1}_{old}_{len(p)}_{method}.json',checkpoint)
    bank[i]=p; dest=BASE/'best'/name(ds); tmp=dest.with_suffix('.pending'); save_programs(tmp,bank)
    assert load_programs(tmp)==bank; os.replace(tmp,dest)
    print('IMPROVED',ds,i+1,old,'->',len(p),method,flush=True)
    return True
