from common import *
from screen import finish_at_k
def main():
    recovered=[]
    for directory in (BASE/'experiments').iterdir():
        if not directory.is_dir():continue
        for f in directory.glob('*.json'):
            x=json.loads(f.read_text())
            if 'rows' not in x:continue
            modified=False
            for r in x['rows']:
                ds=r['dataset'];i=r['case']-1;c=cases(ds)[i];sim=Sim(c);old=r.get('candidate');best=[tuple(z) for z in r['program']] if r.get('program') else None
                for n in r.get('near_candidates',[]):
                    if n.get('prefix') or n.get('suffix'):candidate=[tuple(z) for z in n.get('prefix',[])]+[tuple(z) for z in n['program']]+[tuple(z) for z in n.get('suffix',[])]
                    elif packed(n['start'])==packed(sim.initial()) and n['start'][2]==0:candidate=[tuple(z) for z in n['program']]
                    else:continue
                    p=finish_at_k(c,candidate)
                    if not p or len(p)>=r['incumbent'] or (best and len(p)>=len(best)):continue
                    exact(c,p);best=p
                if best and (old is None or len(best)<old):
                    r.setdefault('direct_candidate',old);r.setdefault('direct_saved',r['saved']);r.setdefault('direct_program',r['program']);r['program']=best;r['candidate']=len(best);r['best_of_arm']=len(best);r['saved']=r['incumbent']-len(best);r['postvalidated_from_returned_near']=True;r['valid_candidates']+=1;modified=True
                    update(ds,i,best,f"{r['strategy']}_near_recovery",r['runtime'],r['evaluations'],r['seed']);recovered.append(dict(dataset=ds,case=i+1,strategy=r['strategy'],stage=directory.name,old_reported=old,recovered=len(best)))
            if modified:atomic_json(f,x)
    atomic_json(BASE/'experiments/near_recovery.json',recovered);print('RETURNED_NEAR_RECOVERY',len(recovered),flush=True)
if __name__=='__main__':main()
