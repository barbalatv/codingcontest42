from common import *
import collections,math

def transformed(action,shift,reflect):
    out=0
    for e in range(6):
        op=action>>(2*e)&3
        if reflect and op in [1,2]:op=3-op
        f=(shift-e)%6 if reflect else (e+shift)%6;out|=op<<(2*f)
    return out

def main():
    inventory=[];rawrows=0;found_programs=0
    for directory in ['training_l6_full540','training_l6_cellfirst','training_medium_codex_v2','training_medium_breakthrough']:
        root=REPO/directory
        reports={}
        for name_ in ['REPORT.md','summary.json','results.csv','improvements.csv']:
            f=root/name_
            if not f.exists():continue
            data=f.read_bytes();reports[name_]=dict(bytes=len(data),sha256=hashlib.sha256(data).hexdigest())
            if f.suffix=='.csv':reports[name_]['rows']=sum(1 for _ in csv.DictReader(f.open()))
            if name_=='summary.json':reports[name_]['summary']=json.loads(data)
        count=0;rows=0;programs_found=0
        for f in (root/'experiments').glob('*/*.json'):
            if not any(f.stem.startswith(ds+'_') for ds in DATASETS):continue
            x=json.loads(f.read_text());count+=1
            for r in x.get('rows',[]):rows+=1;programs_found+=bool(r.get('program'))
        jsonl=[]
        for f in (root/'experiments').glob('*.jsonl'):
            n=0
            with f.open() as stream:
                for line in stream:
                    if line.strip():json.loads(line);n+=1
            jsonl.append(dict(path=str(f.relative_to(REPO)),records=n,sha256=hashlib.sha256(f.read_bytes()).hexdigest()))
        inventory.append(dict(directory=directory,reports=reports,per_case_json_records=count,raw_strategy_rows=rows,returned_program_records=programs_found,jsonl=jsonl));rawrows+=rows;found_programs+=programs_found
    atomic_json(BASE/'experiments/historical_source_inventory.json',dict(sources=inventory,raw_rows=rawrows,returned_program_records=found_programs))
    profiles=json.loads((BASE/'similarity_index/profiles.json').read_text());byid={(p['dataset'],p['case']):p for p in profiles};support=json.loads((BASE/'experiments/operator_support_audit.json').read_text())['exact_variant_support'];donors=sorted({tuple(d) for v in support.values() for d in v})
    # Recipient retrieval uses only frozen, pre-search features. No coordinate
    # scaling is performed. These are exemplars, not a physical equivalence.
    retrieval={};site_counts={};catalog=json.loads((BASE/'operators/catalog_primary_frozen.json').read_text());templates=collections.defaultdict(set)
    for rule in catalog['rewrites']:
        for shift in range(6):
            for reflect in [False,True]:templates[len(rule['before'])].add(tuple(transformed(a,shift,reflect) for a in rule['before']))
    for p in profiles:
        ds,idx=p['dataset'],p['case'];matches=[]
        for d in donors:
            if d==(ds,idx):continue
            q=byid[d]
            distance=abs(p['radius']-q['radius'])/8+abs(math.log1p(p['K'])-math.log1p(q['K']))/3+abs(math.log1p(p['target_cells'])-math.log1p(q['target_cells']))/3+abs(p['repeat_fraction']-q['repeat_fraction'])
            matches.append(dict(donor=list(d),distance=distance,radius=q['radius'],dataset=q['dataset']))
        retrieval[f'{ds}_{idx}']=sorted(matches,key=lambda x:x['distance'])[:8]
        program=encode(programs(ds,'baseline')[idx-1]);sites=0
        for n,patterns in templates.items():sites+=sum(tuple(program[t:t+n]) in patterns for t in range(len(program)-n+1))
        site_counts[f'{ds}_{idx}']=sites
    atomic_json(BASE/'similarity_index/retrieval.json',retrieval);atomic_json(BASE/'similarity_index/rewrite_match_sites.json',site_counts)
    print('SOURCE_AUDIT_PASS',rawrows,'raw strategy rows;',len(profiles),'retrieval/motif profiles',flush=True)

if __name__=='__main__':main()
