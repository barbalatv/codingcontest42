from native import *
sys.path.insert(0,str(BASE/'hybrid'))
from graph_adapter import *
import importlib.util,argparse
sys.modules['graph_cycles']=prior
sp=importlib.util.spec_from_file_location('prior_symmetry',REPO/'training_medium_codex_v2/symmetry_graph.py');sym=importlib.util.module_from_spec(sp);sp.loader.exec_module(sym)
def pdist(a,b,L):return max(min(abs(a[e]-b[e]),L-abs(a[e]-b[e]))+int(((a[6]^b[6])>>e)&1) for e in range(6))
CHECKED_RADII=set()
def symmetry_sparse(g):
    r=g.case[0]
    if r not in CHECKED_RADII:
        for e in range(3):
            for p in range(6*r):assert g.sim.rays[p][e]==g.sim.rays[((3-2*e)*r-p)%(6*r)][e+3]
        CHECKED_RADII.add(r)
    for edge in list(g.E.values()):
        for mask in range(1,8):
            a=sym.swapq(edge['start'],mask,r);b=sym.swapq(edge['end'],mask,r);old=g.E.get((a,b,edge['copies']))
            if old is not None and old['ticks']<=edge['ticks']:continue
            g.add(a,b,edge['copies'],sym.swapprog(edge['program'],mask),'verified_opposed_symmetry')
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--queries',type=int,default=0);ap.add_argument('--ms',type=int,default=500);ap.add_argument('--indices',default='');ap.add_argument('--datasets',default='medium,large,enormous');ap.add_argument('--pure-library',action='store_true');ap.add_argument('--bounce',type=int,default=0);args=ap.parse_args();engine=Engine()
    try:
        for ds in args.datasets.split(','):
            ids=list(map(int,args.indices.split(','))) if args.indices else range(1,len(cases(ds))+1)
            for idx in ids:
                c=cases(ds)[idx-1];before=len(programs(ds)[idx-1]);ct=time.perf_counter();g=make_graph(ds,idx-1,True);new_ends=set();new_edges=0;pure_records=[]
                for directory in sorted((BASE/'experiments').glob('*')):
                    f=directory/f'{ds}_{idx}.json'
                    if not f.exists():continue
                    x=json.loads(f.read_text())
                    for r in x.get('rows',[]):
                        if r.get('program'):new_edges+=g.walk(START,[tuple(z) for z in r['program']],f"{r['strategy']}_{directory.name}")
                        for near in r.get('near_candidates',[]):
                            start=near['start']
                            if start[2]&(g.sim.target|g.sim.forbidden):continue
                            q=START if packed(start)==packed(g.sim.initial()) else tuple(start[0])+(start[1],)
                            new_edges+=g.walk(q,[tuple(z) for z in near['program']],f"{r['strategy']}_near_prefix")
                        if r['strategy'] not in ['B','C']:continue
                        if r.get('birth_program'):
                            pp=[tuple(z) for z in r['birth_program']];exact(c,pp);new_edges+=g.walk(START,pp,'independent_birth')
                        for edge in r.get('pure_discoveries',[]):
                            pp=[tuple(z) for z in edge['program']];st=g.sim.initial()
                            for row in pp:st=g.sim.step(st,row)
                            assert st[3]==edge['copies'] and packed(st)==edge['pose']
                            new_edges+=g.walk(START,pp,'independent_six_emitter_prefix');new_ends.add(tuple(st[0])+(st[1],));pure_records.append(dict(start=START,end=tuple(st[0])+(st[1],),copies=st[3],program=pp,origin='B_geometry' if r['strategy']=='B' else 'C_pre_history_geometry'))
                if args.pure_library:
                    source=BASE/'cellfirst/pure_graph'/f'{ds}_{idx}.json'
                    if source.exists():
                        for e in json.loads(source.read_text())['edges']:
                            a=START if e['start']==START else tuple(e['start']);b=tuple(e['end'])
                            new_edges+=g.add(a,b,e['copies'],[tuple(z) for z in e['program']],'independent_library')
                if args.bounce:g.bounce(rounds=args.bounce,cap=50)
                symmetry_sparse(g);candidate,path=g.dp(frontier=4096);update(ds,idx-1,candidate,'C_extended_graph' if args.pure_library or args.bounce else 'C_global_graph',time.perf_counter()-ct)
                queries=0
                for q in sorted(new_ends):
                    if queries>=args.queries or c[2]<2:break
                    donors=sorted((e for e in g.E.values() if e['start']!=START and e['start']!=q and e['copies']==1 and e['ticks']<=32),key=lambda e:(pdist(q,e['start'],6*c[0]),e['ticks']))
                    if not donors:continue
                    donor=donors[0]
                    if pdist(q,donor['start'],6*c[0])>4:continue
                    queries+=1;pp,_,info=engine.ask(c,start=pose_state(g,q),k=1,horizon=donor['ticks'],ms=args.ms,seed=7100000+idx*137+queries,mode=7,hint=donor['program'],goal=packed(pose_state(g,donor['end'])))
                    if pp:g.walk(q,pp,'hybrid_new_pose_bridge')
                if queries:
                    symmetry_sparse(g);candidate,path=g.dp(frontier=4096);update(ds,idx-1,candidate,'C_new_pose_bridge_graph',time.perf_counter()-ct)
                persist(g,ds);atomic_json(BASE/'cellfirst'/f'{ds}_{idx}_independent_edges.json',pure_records)
                rec=dict(dataset=ds,case=idx,strategy='C',incumbent=before,candidate=len(programs(ds)[idx-1]),saved=before-len(programs(ds)[idx-1]),algorithm='global_graph',runtime=time.perf_counter()-ct,new_edges=new_edges,independent_poses=len(new_ends),nodes=len(g.nodes),edges=len(g.E),queries=queries,incumbent_structure_used=True,pure_library=args.pure_library,bounce_rounds=args.bounce)
                with (BASE/'experiments/consolidation.jsonl').open('a') as f:f.write(json.dumps(rec)+'\n')
                if idx%20==0 or rec['saved']:print('CONSOLIDATE',ds,idx,before,'->',rec['candidate'],'new edges',new_edges,flush=True)
    finally:engine.close()
if __name__=='__main__':main()
