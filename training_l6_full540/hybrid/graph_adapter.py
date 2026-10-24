import importlib.util
from common import *
# Reuse the previous acceptance graph and its DP verbatim. No original module
# is edited; only its dataset globals are bound to the current isolated run.
spec=importlib.util.spec_from_file_location('prior_acceptance_graph',REPO/'training_medium_codex_v2/graph_cycles.py')
prior=importlib.util.module_from_spec(spec);spec.loader.exec_module(prior)
original_add=prior.Graph.add
def add_with_verified_dominance(self,a,b,c,prog,origin):
    old=self.E.get((a,b,c))
    if old is not None and len(prog)>=old['ticks']:return False
    return original_add(self,a,b,c,prog,origin)
prior.Graph.add=add_with_verified_dominance
START=prior.START
@lru_cache(None)
def history_banks(ds):
    sources=json.loads((BASE/'experiments/baseline.json').read_text())[ds]['sources']
    return [load_programs(REPO/source) for source in sources]
def make_graph(ds,i,use_history=True):
    cc=cases(ds);prior.CASES=cc;g=prior.Graph(i);g.walk(START,programs(ds)[i],'incumbent')
    if use_history:
        seen=set()
        for bank in history_banks(ds):
            p=bank[i];token=tuple(p)
            if token in seen:continue
            seen.add(token)
            try:exact(cc[i],p);g.walk(START,p,'historical')
            except Exception:pass
    saved=BASE/'edges'/ds/f'case{i+1}.json'
    if saved.exists():
        for e in json.loads(saved.read_text())['edges']:
            a=START if e['start']==START else tuple(e['start']);b=tuple(e['end'])
            g.add(a,b,e['copies'],[tuple(row) for row in e['program']],e['origin'])
    return g
def pose_state(g,q):return g.sim.initial() if q==START else prior.state(q)
def persist(g,ds):
    folder=BASE/'edges'/ds;folder.mkdir(exist_ok=True)
    atomic_json(folder/f'case{g.i+1}.json',dict(case=g.i+1,dataset=ds,nodes=len(g.nodes),edges=list(g.E.values())))
