"""Independent-library ablation: never import historical/current-best edges."""
from consolidate import prior, START, symmetry_sparse
from common import *

def main():
    folder=BASE/'cellfirst/pure_graph';folder.mkdir(exist_ok=True)
    logs=BASE/'experiments/pure_graph';logs.mkdir(exist_ok=True)
    sources=[d for d in sorted((BASE/'experiments').iterdir()) if d.is_dir()]
    totals=[]
    for ds in DATASETS:
        cc=cases(ds);prior.CASES=cc
        for i,c in enumerate(cc):
            begin=time.perf_counter();cpu=time.process_time();g=prior.Graph(i);seen=set();counts={}
            def ingest(p,origin):
                if not p:return
                p=[tuple(z) for z in p];token=tuple(p)
                if token in seen:return
                seen.add(token);counts[origin]=counts.get(origin,0)+1
                g.walk(START,p,origin)
            for d in sources:
                f=d/f'{ds}_{i+1}.json'
                if not f.exists():continue
                x=json.loads(f.read_text())
                for row in x.get('rows',[]):
                    s=row['strategy']
                    if s=='B':
                        assert not any(row.get(k,False) for k in ['incumbent_structure_used','incumbent_trajectory_used','state_hints_used','incumbent_transitions_used'])
                        ingest(row.get('program'),'B_complete')
                        for near in row.get('near_candidates',[]):
                            assert packed(near['start'])==packed(g.sim.initial()) and near['start'][2]==0
                            ingest(near['program'],'B_partial')
                    if s in ['B','C']:
                        ingest(row.get('birth_program'),'independent_birth')
                        for edge in row.get('pure_discoveries',[]):ingest(edge['program'],'independent_pre_history_prefix')
            static=json.loads((BASE/'experiments/static_all'/f'{ds}_{i+1}.json').read_text())
            ingest(static.get('program'),'independent_static')
            # Generalized reversals and emitter swaps depend only on this library.
            g.bounce(rounds=1,cap=30);symmetry_sparse(g)
            p,path=g.dp(frontier=4096)
            if p:exact(c,p)
            before=len(programs(ds)[i]);graph_cpu=time.process_time()-cpu;graph_wall=time.perf_counter()-begin
            gained=update(ds,i,p,'B_independent_graph',graph_wall)
            baseline=len(programs(ds,'baseline')[i])
            record=dict(dataset=ds,case=i+1,incumbent_structure_used=False,incumbent_trajectory_used=False,state_hints_used=False,incumbent_transitions_used=False,baseline=baseline,best_before=before,pure_graph_ticks=len(p) if p else None,saved_vs_frozen_baseline=max(0,baseline-len(p)) if p else 0,actual_saved=before-len(p) if gained else 0,nodes=len(g.nodes),edges=len(g.E),independent_source_counts=counts,graph_cpu_seconds=graph_cpu,graph_wall_seconds=graph_wall,frontier=4096,path=[dict(start=e['start'],end=e['end'],copies=e['copies'],ticks=e['ticks'],origin=e['origin']) for e in path])
            atomic_json(logs/f'{ds}_{i+1}.json',record)
            atomic_json(folder/f'{ds}_{i+1}.json',dict(dataset=ds,case=i+1,program=p,edges=list(g.E.values())))
            totals.append(record)
            if (i+1)%30==0 or gained:print('PURE_GRAPH',ds,i+1,'ticks',len(p) if p else None,'gain',record['actual_saved'],flush=True)
    atomic_json(BASE/'experiments/pure_graph_summary.json',dict(cases=len(totals),actual_saved=sum(r['actual_saved'] for r in totals),improved_vs_frozen=sum(r['saved_vs_frozen_baseline']>0 for r in totals),saved_vs_frozen=sum(r['saved_vs_frozen_baseline'] for r in totals),graph_cpu_seconds=sum(r['graph_cpu_seconds'] for r in totals),graph_wall_seconds=sum(r['graph_wall_seconds'] for r in totals),provenance='only B complete/partial, independent births, pre-history prefixes, independent static witnesses, verified transforms; no historical/current best edges'))

if __name__=='__main__':main()

