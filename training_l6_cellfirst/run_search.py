from native import *
sys.path.insert(0,str(BASE/'scheduler'))
from graph_adapter import make_graph,pose_state,persist,START
from collections import Counter
import argparse
ALGORITHMS={0:'command_beam',1:'cellfirst',2:'macro_chord',3:'cellfirst_chord',4:'reverse_six_bridge',5:'reverse_geometry_bridge',6:'reverse_chord_bridge'}
def run_case(engine,ds,i,args,modes):
    c=cases(ds)[i];initial=programs(ds)[i];before=len(initial);metrics=[]
    # Fixed query anchors and horizons are shared by every ablation arm.
    sim=Sim(c);ss=sim.prefix(initial);aa=[t for t in range(1,len(ss)) if ss[t][3]>ss[t-1][3]]
    anchors=[(START,aa[0],initial[:aa[0]])]
    if len(aa)>1:
        t0,t1=aa[0:2];anchors.append((tuple(ss[t0][0])+(ss[t0][1],),t1-t0,initial[t0:t1]))
    for mode in modes:
        g=make_graph(ds,i,use_history=args.history);ct=time.perf_counter();total_ev=total_cfg=0;queries=[];newstarts=[]
        for j,(q,h,hint) in enumerate(anchors):
            start=pose_state(g,q);refs=list(dict.fromkeys(packed(s) for s in ss if s[3] and not s[2]&(sim.target|sim.forbidden)))[:16]
            # Free-end equal-length edges may enable cheaper subsequent copies.
            p,edges,info=engine.ask(c,start=start,k=1,horizon=min(h,args.maxh),width=args.width,ms=args.ms,seed=args.seed+i*137+j,mode=mode,hint=hint,refs=refs)
            total_ev+=info['evaluations'];total_cfg+=info['configurations'];queries.append(dict(anchor=j,horizon=min(h,args.maxh),**info))
            for end,pp in edges:
                if g.walk(q,pp,ALGORITHMS[mode]):
                    st=start
                    for row in pp:st=g.sim.step(st,row)
                    newstarts.append(tuple(st[0])+(st[1],))
        # Follow newly discovered acceptance poses; don't count an isolated cheap
        # one-copy edge as success until full K-copy DP is shorter.
        for j,q in enumerate(dict.fromkeys(newstarts)):
            if j>=args.follow:break
            h=min(args.maxh,max(2,round((before-aa[0])/max(1,c[2]-1))))
            p,edges,info=engine.ask(c,start=pose_state(g,q),k=1,horizon=h,width=args.width,ms=args.ms,seed=args.seed+i*137+30+j,mode=mode,refs=[packed(ss[t]) for t in aa[:8]])
            total_ev+=info['evaluations'];total_cfg+=info['configurations'];queries.append(dict(anchor='new_pose',horizon=h,**info))
            for _,pp in edges:g.walk(q,pp,ALGORITHMS[mode])
        if args.bounce:g.bounce(rounds=1,cap=60)
        p,path=g.dp(frontier=4096);elapsed=time.perf_counter()-ct
        # DP should always recover the original bank path.
        assert p and len(p)<=before
        direct=min((len(e['program']) for e in g.E.values() if e['start']==START and e['copies']==c[2]),default=before)
        improved=update(ds,i,p,ALGORITHMS[mode]+'_graph',elapsed,total_ev,args.seed+i*137)
        rec=dict(dataset=ds,case=i+1,incumbent=before,candidate=len(p),saved=before-len(p),algorithm=ALGORITHMS[mode],runtime=elapsed,evaluations=total_ev,configurations=total_cfg,seed=args.seed+i*137,validation='EXACT_EDGES_DP',queries=queries,nodes=len(g.nodes),edges=len(g.E),direct_candidate=direct)
        with (BASE/'experiments'/f'{args.tag}.jsonl').open('a') as f:f.write(json.dumps(rec)+'\n')
        if improved:persist(g,ds)
        print(ds,i+1,ALGORITHMS[mode],before,'->',len(p),'sec',round(elapsed,2),'cfg',total_cfg,flush=True);metrics.append(rec)
    return metrics
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--mode',default='pilot');ap.add_argument('--datasets',default='medium,large,enormous');ap.add_argument('--indices',default='');ap.add_argument('--algorithms',default='0,1,2,3');ap.add_argument('--ms',type=int,default=250);ap.add_argument('--width',type=int,default=24);ap.add_argument('--follow',type=int,default=1);ap.add_argument('--maxh',type=int,default=24);ap.add_argument('--seed',type=int,default=424200);ap.add_argument('--tag',default='pilot');ap.add_argument('--history',action='store_true');ap.add_argument('--bounce',action='store_true');args=ap.parse_args()
    pilot=json.loads((BASE/'experiments/pilot.json').read_text());engine=Engine(getattr(args,'engine','cellfirst.exe'))
    try:
        for ds in args.datasets.split(','):
            ids=list(map(int,args.indices.split(','))) if args.indices else pilot[ds] if args.mode=='pilot' else list(range(1,len(cases(ds))+1))
            for idx in ids:run_case(engine,ds,idx-1,args,list(map(int,args.algorithms.split(','))))
    finally:engine.close()
if __name__=='__main__':main()
