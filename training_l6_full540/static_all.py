from common import *
from screen import init_worker
import argparse,concurrent.futures
sys.path.insert(0,str(BASE/'cellfirst'));from static_model import static_synth
def task(ds,i,seconds):
    c=cases(ds)[i];t=time.process_time();p,info=static_synth(c,seconds=seconds,seed=8100000+i*137);return dict(dataset=ds,case=i+1,strategy='B',incumbent_structure_used=False,program=p,search_cpu_seconds=time.process_time()-t,**info)
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--seconds',type=float,default=1);ap.add_argument('--workers',type=int,default=4);args=ap.parse_args();folder=BASE/'experiments/static_all';folder.mkdir(exist_ok=True)
    with concurrent.futures.ProcessPoolExecutor(max_workers=args.workers,initializer=init_worker) as pool:
        fs={pool.submit(task,ds,i,args.seconds):(ds,i) for ds in DATASETS for i in range(len(cases(ds))) if not (folder/f'{ds}_{i+1}.json').exists()}
        n=540-len(fs)
        for future in concurrent.futures.as_completed(fs):
            ds,i=fs[future];r=future.result();atomic_json(folder/f'{ds}_{i+1}.json',r)
            if r['program']:update(ds,i,[tuple(z) for z in r['program']],'B_static_cell_assignment',r['seconds'],r.get('branches',0),8100000+i*137)
            n+=1
            if n%60==0:print('STATIC_ALL',n,'/540',flush=True)
if __name__=='__main__':main()
