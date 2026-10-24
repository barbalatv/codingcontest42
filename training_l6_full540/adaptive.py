from screen import *
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--ms',type=int,default=6000);ap.add_argument('--workers',type=int,default=4);ap.add_argument('--seed',type=int,default=6500000);ap.add_argument('--pass-name',default='pass2');ap.add_argument('--replicates',action='store_true');args=ap.parse_args()
    chosen=json.loads((BASE/'experiments/adaptive_selection.json').read_text())
    if args.replicates:
        chosen=[]
        full=json.loads((BASE/'experiments/adaptive_ranking.json').read_text())
        for ds in DATASETS:
            pure_winners=[]
            for r in full:
                if r['dataset']!=ds:continue
                x=json.loads((BASE/'experiments/pass1'/f"{ds}_{r['case']}.json").read_text())
                if next(z for z in x['rows'] if z['strategy']=='B')['saved']>0:pure_winners.append(r)
            candidates=pure_winners+[r for r in full if r['dataset']==ds and r not in pure_winners];chosen+=candidates[:2]
    folder=BASE/'experiments'/args.pass_name;folder.mkdir(exist_ok=True);todo=[x for x in chosen if not (folder/f"{x['dataset']}_{x['case']}.json").exists()]
    snapshot='baseline' if args.replicates else 'experiments/pass2_baseline'
    atomic_json(folder/'run_config.json',dict(ms=args.ms,workers=args.workers,seed=args.seed,pure_exact=not args.replicates,snapshot=snapshot,cases=chosen))
    with concurrent.futures.ProcessPoolExecutor(max_workers=args.workers,initializer=init_worker,initargs=(snapshot,)) as pool:
        futures={pool.submit(run_case,x['dataset'],x['case']-1,args.ms,args.seed,args.pass_name,not args.replicates):(x['dataset'],x['case']) for x in todo}
        for future in concurrent.futures.as_completed(futures):
            ds,idx=futures[future];record=future.result();atomic_json(folder/f'{ds}_{idx}.json',record);consolidate_record(record);print('ADAPTIVE',args.pass_name,ds,idx,[(r['strategy'],r['saved'],r['solver_status']) for r in record['rows']],flush=True)
if __name__=='__main__':main()
