from common import *
from collections import Counter
import re
def main():
    for d in ['baseline','best','engines','geometry','scheduler','repair','experiments','checkpoints','edges']:(BASE/d).mkdir(exist_ok=True)
    assert not (BASE/'baseline'/name('medium')).exists(), 'Do not reset an existing experiment'
    protected={str(p.relative_to(REPO)):hashlib.sha256(p.read_bytes()).hexdigest() for p in REPO.rglob('*') if p.is_file() and '.git' not in p.parts and BASE.name not in p.parts}
    atomic_json(BASE/'experiments/protected_sha256.json',protected)
    summary={};provenance=[];rejected=[]
    for ds in DATASETS:
        cc=cases(ds);bank=[None]*len(cc);origin=[None]*len(cc);seen=[set() for _ in cc];sources=[]
        def offer(i,p,path):
            token=tuple(p)
            if token in seen[i]:return
            seen[i].add(token)
            try:exact(cc[i],p)
            except Exception as e:
                rejected.append(dict(dataset=ds,case=i+1,path=str(path),error=str(e)));return
            if bank[i] is None or len(p)<len(bank[i]):bank[i]=p;origin[i]=str(path.relative_to(REPO))
        for f in sorted(REPO.rglob(name(ds))):
            if BASE.name in f.parts:continue
            try: pp=load_programs(f)
            except Exception:continue
            if len(pp)!=len(cc):continue
            sources.append(str(f.relative_to(REPO)))
            for i,p in enumerate(pp):offer(i,p,f)
        # Historical stand-alone Medium candidates use a case-number naming convention.
        if ds=='medium':
            for root in ['training_medium','training_medium_codex','training_medium_codex_v2','training_medium_breakthrough']:
                for f in (REPO/root).rglob('case*.txt'):
                    match=re.match(r'case_?(\d+)(?:_|\.)',f.name)
                    if not match:continue
                    i=int(match[1])-1
                    if not 0<=i<len(cc):continue
                    try:pp=load_programs(f)
                    except Exception:continue
                    if len(pp)==1:offer(i,pp[0],f)
        assert all(bank)
        for folder in ['baseline','best']:save_programs(BASE/folder/name(ds),bank)
        score=sum(map(len,bank));summary[ds]=dict(cases=len(cc),ticks=score,unique_programs=sum(map(len,seen)),sources=sources)
        provenance += [dict(dataset=ds,case=i+1,ticks=len(p),origin=origin[i]) for i,p in enumerate(bank)]
        print(ds,summary[ds]['cases'],score,summary[ds]['unique_programs'],flush=True)
    atomic_json(BASE/'experiments/baseline.json',summary);atomic_json(BASE/'experiments/provenance.json',provenance);atomic_json(BASE/'experiments/rejected.json',rejected)
    with (BASE/'results.csv').open('w',newline='') as f:csv.DictWriter(f,FIELDS).writeheader()
    subprocess.run(['node',str(BASE/'validate_sandbox.cjs'),'baseline'],check=True)
if __name__=='__main__':main()
