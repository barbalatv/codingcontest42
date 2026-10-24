from native import *
sys.path.insert(0,str(BASE/'scheduler'))
from graph_adapter import *
import argparse,importlib.util
sys.modules['graph_cycles']=prior
sp=importlib.util.spec_from_file_location('prior_graph_symmetries',REPO/'training_medium_codex_v2/symmetry_graph.py');sym=importlib.util.module_from_spec(sp);sp.loader.exec_module(sym)
def distance(q,r,L):return max(min(abs(q[e]-r[e]),L-abs(q[e]-r[e]))+int(((q[6]^r[6])>>e)&1) for e in range(6))
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--datasets',default='medium,large,enormous');ap.add_argument('--indices',default='');ap.add_argument('--ms',type=int,default=250);ap.add_argument('--queries',type=int,default=3);ap.add_argument('--seed',type=int,default=4000000);ap.add_argument('--tag',default='frontier');ap.add_argument('--history',action='store_true');args=ap.parse_args();engine=Engine()
    try:
        for ds in args.datasets.split(','):
            ids=list(map(int,args.indices.split(','))) if args.indices else range(1,len(cases(ds))+1)
            for idx in ids:
                i=idx-1;c=cases(ds)[i];before=len(programs(ds)[i]);ct=time.perf_counter();g=make_graph(ds,i,args.history);sym.symmetry(g);p,_=g.dp(frontier=4096);update(ds,i,p,'acceptance_symmetry_graph',time.perf_counter()-ct)
                # New cheap setup endpoints need outgoing production edges.
                setup=sorted((e for e in g.E.values() if e['start']==START and e['copies']==1),key=lambda e:e['ticks']);queries=ev=0
                used=set()
                for incoming in setup:
                    if queries>=args.queries:break
                    q=incoming['end']
                    if q in used:continue
                    used.add(q)
                    reachable=sorted((e for e in g.E.values() if e['start']!=START and e['start']!=q and e['copies']<=3 and e['ticks']<=40),key=lambda e:(distance(q,e['start'],6*c[0]),e['ticks']/e['copies']))[:3]
                    for donor in reachable:
                        if queries>=args.queries:break
                        if distance(q,donor['start'],6*c[0])>4:continue
                        seed=args.seed+idx*137+queries;queries+=1
                        candidate,edges,info=engine.ask(c,start=pose_state(g,q),k=donor['copies'],horizon=donor['ticks'],ms=args.ms,seed=seed,mode=7,goal=packed(pose_state(g,donor['end'])),hint=donor['program']);ev+=info['evaluations']
                        for _,pp in edges:g.walk(q,pp,'cell_assignment_frontier')
                if args.queries:g.bounce(1,40);sym.symmetry(g)
                p,path=g.dp(frontier=4096);did=update(ds,i,p,'cell_assignment_frontier_graph',time.perf_counter()-ct,ev,args.seed+idx*137)
                if did or queries:persist(g,ds)
                rec=dict(dataset=ds,case=idx,incumbent=before,candidate=len(programs(ds)[i]),saved=before-len(programs(ds)[i]),algorithm='frontier_symmetry_and_bridges',runtime=time.perf_counter()-ct,evaluations=ev,seed=args.seed+idx*137,validation='EXACT_EDGE_REPLAY',queries=queries,nodes=len(g.nodes),edges=len(g.E))
                with (BASE/'experiments'/f'{args.tag}_{ds}.jsonl').open('a') as f:f.write(json.dumps(rec)+'\n')
                print(ds,idx,'frontier',before,'->',len(programs(ds)[i]),'queries',queries,flush=True)
    finally:engine.close()
if __name__=='__main__':main()
