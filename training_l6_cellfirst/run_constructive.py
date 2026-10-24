from native import *
import argparse
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--datasets',default='medium,large,enormous');ap.add_argument('--indices',default='');ap.add_argument('--ms',type=int,default=1500);ap.add_argument('--width',type=int,default=24);ap.add_argument('--algorithms',default='0,1,2,3');ap.add_argument('--seed',type=int,default=2000000);ap.add_argument('--tag',default='constructive');ap.add_argument('--engine',default='cellfirst_c.exe');args=ap.parse_args()
    pilot=json.loads((BASE/'experiments/pilot.json').read_text());engine=Engine(args.engine)
    try:
        for ds in args.datasets.split(','):
            for idx in list(map(int,args.indices.split(','))) if args.indices else pilot[ds]:
                i=idx-1;c=cases(ds)[i];p0=programs(ds)[i]
                for mode in map(int,args.algorithms.split(',')):
                    # No command/pose hints: synthesize the entire production
                    # schedule from the physical initial state, including K copies.
                    p,_,info=engine.ask(c,k=c[2],horizon=len(p0)-1,width=args.width,ms=args.ms,seed=args.seed+idx*137,mode=mode)
                    label={0:'constructive_command',1:'constructive_cellfirst',2:'constructive_chord',3:'constructive_cellfirst_chord',10:'cellfirst_chord_library'}[mode]
                    if p:update(ds,i,p,label,info['runtime'],info['evaluations'],args.seed+idx*137)
                    near=info.pop('near_program')
                    if near and info['near_cost']<=16:
                        # Keep a concrete full-horizon near solution from scratch.
                        near=near+[tuple('------')]*(len(p0)-1-len(near));sim=Sim(c);st=sim.prefix(near)[-1]
                        cost=max(0,c[2]-st[3]-1)*(len(c[1])*3+16)+(sim.target&~st[2]).bit_count()*3+(sim.forbidden&st[2]).bit_count()*4
                        if st[3]<c[2] and cost<=16:
                            neardir=BASE/'repair/near';neardir.mkdir(exist_ok=True)
                            atomic_json(neardir/f'fresh_{ds}_{idx}_{args.seed+idx*137}_{mode}.json',dict(dataset=ds,case=idx,start=sim.initial(),copies=c[2],goal=None,program=near,cost=cost,horizon=len(near),seed=args.seed+idx*137,kind='fresh_'+label))
                    rec=dict(dataset=ds,case=idx,incumbent=len(p0),candidate=len(p) if p else None,saved=len(p0)-len(p) if p else 0,algorithm=label,seed=args.seed+idx*137,validation='CPP_REPLAY_PASS' if p else 'NO_PROGRAM',**info)
                    with (BASE/'experiments'/f'{args.tag}_{ds}.jsonl').open('a') as f:f.write(json.dumps(rec)+'\n')
                    print(ds,idx,label,len(p0),'->',len(p) if p else None,flush=True)
    finally:engine.close()
if __name__=='__main__':main()
