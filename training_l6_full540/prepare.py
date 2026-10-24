from common import *
from collections import Counter
import re
def main():
    assert not (BASE/'experiments/frozen_baseline.json').exists(),'Frozen baseline already exists; resume instead'
    protected={str(f.relative_to(REPO)):hashlib.sha256(f.read_bytes()).hexdigest() for f in REPO.rglob('*') if f.is_file() and '.git' not in f.parts and BASE.name not in f.parts}
    atomic_json(BASE/'experiments/protected_sha256.json',protected)
    provenance=[];summary={};rejected=[]
    for ds in DATASETS:
        cc=cases(ds);bank=[None]*len(cc);seen=[set() for c in cc];origins=[None]*len(cc);sources=[]
        def offer(i,p,source):
            p=[tuple(row) for row in p];token=tuple(p)
            if token in seen[i] or (bank[i] is not None and len(p)>=len(bank[i])):return
            seen[i].add(token)
            try:exact(cc[i],p)
            except Exception as e:rejected.append(dict(dataset=ds,case=i+1,source=source,error=str(e)));return
            bank[i]=p;origins[i]=source
        # Known newest banks first; still test every strictly stronger candidate.
        files=sorted(REPO.rglob(name(ds)),key=lambda f:(f.parent!=REPO/'training_l6_cellfirst/best',str(f)))
        for f in files:
            if BASE.name in f.parts:continue
            try:pp=load_programs(f)
            except Exception:continue
            if len(pp)!=len(cc):continue
            source=str(f.relative_to(REPO));sources.append(source)
            for i,p in enumerate(pp):offer(i,p,source)
        for root in ['training_l6_cellfirst','training_medium','training_medium_codex','training_medium_codex_v2','training_medium_breakthrough']:
            for f in (REPO/root).rglob('case*.txt'):
                if ds!='medium':continue
                m=re.match(r'case_?(\d+)(?:_|\.)',f.name)
                if not m:continue
                i=int(m[1])-1
                if not 0<=i<len(cc):continue
                try:pp=load_programs(f)
                except Exception:continue
                if len(pp)==1:offer(i,pp[0],str(f.relative_to(REPO)))
        for root in ['training_l6_cellfirst/checkpoints','training_l6_cellfirst/repair/near']:
            for f in (REPO/root).glob('*.json'):
                x=json.loads(f.read_text())
                if x.get('dataset')==ds and 'program' in x:offer(x['case']-1,x['program'],str(f.relative_to(REPO)))
        assert all(bank)
        for folder in ['baseline','best']:save_programs(BASE/folder/name(ds),bank)
        for i,p in enumerate(bank):exact(cc[i],p)
        summary[ds]=dict(cases=len(cc),ticks=sum(map(len,bank)),sources=sources)
        provenance += [dict(dataset=ds,case=i+1,ticks=len(p),source=origins[i]) for i,p in enumerate(bank)]
        print('BASELINE',ds,summary[ds]['ticks'],flush=True)
    atomic_json(BASE/'experiments/frozen_baseline.json',summary);atomic_json(BASE/'experiments/provenance.json',provenance);atomic_json(BASE/'experiments/rejected_baseline_candidates.json',rejected)
    # Compatibility for the reused graph loader; it remains read only here.
    atomic_json(BASE/'experiments/baseline.json',summary)
    with (BASE/'improvements.csv').open('w',newline='') as f:csv.DictWriter(f,FIELDS).writeheader()
    manifest={str(f.relative_to(REPO)):hashlib.sha256(f.read_bytes()).hexdigest() for f in REPO.rglob('*.txt') if f.parent.name in ['best','baseline','level-6'] and (f.name.startswith('answer_level-6_') or f.name.startswith('in_level-6_'))}
    atomic_json(BASE/'experiments/input_answer_sha256.json',manifest)
    subprocess.run(['node',str(BASE/'validate_sandbox.cjs'),'baseline'],check=True)
if __name__=='__main__':main()
