from native import *
sys.path.insert(0,str(BASE/'scheduler'))
from graph_adapter import *
import argparse,copy
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--datasets',default='medium,large,enormous');ap.add_argument('--mode',default='pilot');ap.add_argument('--indices',default='');ap.add_argument('--ms',type=int,default=250);ap.add_argument('--seed',type=int,default=800000);ap.add_argument('--algorithms',default='7,8');ap.add_argument('--tag',default='assignment');ap.add_argument('--jobs',type=int,default=3);args=ap.parse_args()
    pilot=json.loads((BASE/'experiments/pilot.json').read_text());engine=Engine()
    try:
        for ds in args.datasets.split(','):
            cc=cases(ds);ids=list(map(int,args.indices.split(','))) if args.indices else pilot[ds] if args.mode=='pilot' else range(1,len(cc)+1)
            for idx in ids:
                i=idx-1;c=cc[i];p0=programs(ds)[i];sim=Sim(c);ss=sim.prefix(p0);aa=[t for t in range(1,len(ss)) if ss[t][3]>ss[t-1][3]];gbase=make_graph(ds,i,False);jobs=[]
                jobs.append((START,aa[0],1,p0[:aa[0]],None,'setup'))
                if len(aa)>1:
                    a,b=aa[:2];q=tuple(ss[a][0])+(ss[a][1],);jobs.append((q,b-a,1,p0[a:b],None,'new_edge'))
                    # Fixed accepting endpoint retains a repeatable cycle when found.
                    if len(aa)>2:
                        b=aa[2];jobs.append((q,b-a,2,p0[a:b],packed(ss[b]),'two_copy'))
                    if len(aa)>3:
                        b=aa[3];jobs.append((q,b-a,3,p0[a:b],packed(ss[b]),'three_copy'))
                if len(p0)<=60:jobs.append((START,len(p0),c[2],p0,None,'whole'))
                for mode in map(int,args.algorithms.split(',')):
                    g=copy.deepcopy(gbase);ev=cfg=0;runtime=0;details=[];nearcount=0
                    for j,(q,h,k,hint,goal,kind) in enumerate(jobs[:args.jobs]):
                        if h<=1:continue
                        start=pose_state(g,q);seed=args.seed+idx*137+j
                        p,edges,info=engine.ask(c,start=start,k=k,horizon=h-1,ms=args.ms,seed=seed,mode=mode,goal=goal,hint=hint)
                        ev+=info['evaluations'];cfg+=info['configurations'];runtime+=info['runtime']
                        for _,candidate in edges:g.walk(q,candidate,'cell_assignment' if mode==7 else 'command_lns')
                        near=info.pop('near_program');cost=info['near_cost']
                        if near and 0<cost<=16:
                            neardir=BASE/'repair/near';neardir.mkdir(exist_ok=True);nearcount+=1
                            atomic_json(neardir/f'{ds}_{idx}_{seed}_{mode}.json',dict(dataset=ds,case=idx,start=start,copies=k,goal=goal,program=near,cost=cost,horizon=h-1,seed=seed,kind=kind))
                        details.append(dict(kind=kind,horizon=h-1,copies=k,seed=seed,**info))
                    candidate,path=g.dp(frontier=4096);assert candidate
                    algorithm='cell_assignment_graph' if mode==7 else 'command_lns_graph';did=update(ds,i,candidate,algorithm,runtime,ev,args.seed+idx*137)
                    if did:persist(g,ds)
                    rec=dict(dataset=ds,case=idx,incumbent=len(p0),candidate=len(candidate),saved=len(p0)-len(candidate),algorithm=algorithm,runtime=runtime,evaluations=ev,configurations=cfg,seed=args.seed+idx*137,validation='EXACT_EDGE_REPLAY',near_misses=nearcount,queries=details)
                    with (BASE/'experiments'/f'{args.tag}_{ds}.jsonl').open('a') as f:f.write(json.dumps(rec)+'\n')
                    print(ds,idx,algorithm,len(p0),'->',len(candidate),'near',nearcount,flush=True)
    finally:engine.close()
if __name__=='__main__':main()
