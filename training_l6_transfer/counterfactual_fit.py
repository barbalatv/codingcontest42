"""Separate incidental sequence matches from executable historical support."""
from common import *
import importlib.util,collections

def main():
    spec=importlib.util.spec_from_file_location('frozen_graph',REPO/'training_medium_codex_v2/graph_cycles.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
    support=collections.defaultdict(set);records=[]
    for f in (BASE/'transformations').glob('*.json'):
        e=json.loads(f.read_text());ds=e['dataset'];i=e['case']-1;c=cases(ds)[i];mod.CASES=[c]
        before=[tuple(z) for z in e['before_program']];after=[tuple(z) for z in e['after_program']];sim=Sim(c);bs=sim.prefix(before);ss=sim.prefix(after);graphs={};seen=set();novel=collections.Counter()
        for match in e['matched_variants']:
            v=match['variant'];a,b=match['after'];p=after[a:b];st=ss[a];q=mod.START if a==0 else tuple(st[0])+(st[1],);end=tuple(ss[b][0])+(ss[b][1],);k=ss[b][3]-ss[a][3]
            token=v,q,tuple(p)
            if token in seen:continue
            seen.add(token)
            if v not in graphs:g=mod.Graph(0);g.walk(mod.START,before,'before_only');graphs[v]=g
            g=graphs[v];old=g.E.get((q,end,k))
            if old and old['ticks']<=len(p):continue
            g.add(q,end,k,p,'fitted_operator');novel[v]+=1
        outcomes=[]
        for v,g in graphs.items():
            p,path=g.dp(bound=len(before),frontier=4096);gain=len(before)-len(p) if p else 0
            if p:
                exact(c,p);js_check(ds,i,p);support[v].add((ds,i+1))
                if len(p)<len(programs(ds)[i]):update(ds,i,p,'Historical_forensic_reconstruction')
            outcomes.append(dict(variant=v,novel_matched_edges=novel[v],reproduced_saved=gain,program=p,scope='before trajectory edges plus only this fitted transformation family; no after-program edge without an exact donor transformation match'))
        records.append(dict(dataset=ds,case=i+1,event=e['index'],method=e['method'],historical_saved=e['saved'],outcomes=outcomes))
    atomic_json(BASE/'experiments/counterfactual_operator_fit.json',dict(records=records,events=len(records),events_with_executable_reproduction=sum(any(r['reproduced_saved'] for r in x['outcomes']) for x in records),executable_variant_support={str(k):sorted(v) for k,v in support.items()},warning='unrestricted before/after sequence matches include unchanged or already-known transitions; they alone do not establish a useful transformation. This replay/DP ablation is stronger but still limited to the known before graph.'))
    print('EXECUTABLE_HISTORICAL_SUPPORT',dict((k,len(v)) for k,v in support.items()),flush=True)

if __name__=='__main__':main()
