import sys,json,time,argparse
from pathlib import Path
BASE=Path(__file__).parent
sys.path[:0]=[str(BASE),str(BASE.resolve().parents[1])]
from ortools.sat.python import cp_model
from solve_l6 import origins,delta
from optimize_l6 import Machine,Done
from optimize_l6_compact import Sim

def solve(case,program,H,copies=2,offset=0,seconds=10,loop=True):
    r,pat,K=case;sim=Sim(case);states=sim.prefix(program)
    accepted=[s for s in states if s[3]>0]
    anchor,activation=accepted[0][:2] if loop else sim.initial()[:2]
    m=Machine(*case);L=6*r;model=cp_model.CpModel();P={};A={};Z={}
    for t in range(H+1):
        D=(min(t,H-t)+offset) if loop else t
        for i in range(6):
            P[t,i]=model.new_int_var(-D,D,f'p{t}_{i}');A[t,i]=model.new_bool_var(f'a{t}_{i}')
            if (loop and not offset and t in (0,H)) or (not loop and t==0):model.add(A[t,i]==bool(activation>>i&1))
            if t:
                dd=model.new_int_var(-1,1,f'd{t}_{i}');model.add(dd==P[t,i]-P[t-1,i])
                model.add_allowed_assignments([dd,A[t-1,i],A[t,i]],[(d,a,b) for d in (-1,0,1) for a in (0,1) for b in (0,1) if d==0 or a==b])
                Z[t,i]={}
                for q in range(-D,D+1):
                    z=model.new_bool_var(f'z{t}_{i}_{q}');model.add(P[t,i]==q).only_enforce_if(z);Z[t,i][q]=z
                model.add(sum(Z[t,i].values())==A[t,i])
    if loop:
        for i in range(6):model.add(P[H,i]==P[0,i]);model.add(A[H,i]==A[0,i])
    before={};after={};accept={t:model.new_bool_var(f'accept{t}') for t in range(1,H+1)}
    cellids=[k for k in range(len(m.cells)) if (m.target|m.forbidden)>>k&1]
    transition=[(prev,h,0 if h>=3 else 1 if h==2 else prev) for prev in (0,1) for h in range(7)]
    for k in cellids:
        prev=0;istarget=bool(m.target>>k&1)
        for t in range(1,H+1):
            hits=[]
            for i in range(6):
                for q,z in Z[t,i].items():
                    if (anchor[i]+q)%L==m.origins[i][k]:hits.append(z)
            n=model.new_int_var(0,6,f'n{t}_{k}');model.add(n==sum(hits))
            b=model.new_bool_var(f'b{t}_{k}');before[t,k]=b
            model.add_allowed_assignments([prev,n,b],transition)
            a=model.new_bool_var(f'm{t}_{k}');after[t,k]=a
            if istarget:
                model.add(a<=b);model.add(a+accept[t]<=1);model.add(a>=b-accept[t])
                model.add(b==1).only_enforce_if(accept[t])
            else:
                model.add(a==b);model.add(b==0).only_enforce_if(accept[t])
            prev=a
    for t in range(1,H+1):
        model.add_bool_or([accept[t]]+[before[t,k].Not() if m.target>>k&1 else before[t,k] for k in cellids])
    model.add(sum(accept.values())==copies)
    if loop:model.add(accept[H]==1)
    if loop:
        ats=[t for t in range(1,len(states)) if states[t][3]>states[t-1][3]]
        begin=ats[0];end=ats[min(copies,len(ats)-1)]
        for t in range(H+1):
            s=states[begin+round(t*(end-begin)/H)]
            for i in range(6):
                q=delta(anchor[i],s[0][i],L);D=min(t,H-t)+offset
                model.add_hint(P[t,i],max(-D,min(D,q)));model.add_hint(A[t,i],bool(s[1]>>i&1))
    solver=cp_model.CpSolver();solver.parameters.max_time_in_seconds=seconds;solver.parameters.num_search_workers=8
    status=solver.solve(model);stats=dict(status=solver.status_name(status),time=solver.wall_time,H=H,copies=copies,offset=offset,branches=solver.num_branches)
    if status not in (cp_model.OPTIMAL,cp_model.FEASIBLE):return None,stats
    start=(tuple((anchor[i]+solver.value(P[0,i]))%L for i in range(6)),sum(solver.value(A[0,i])<<i for i in range(6)))
    lines=[]
    for t in range(1,H+1):
        line=[]
        for i in range(6):
            d=solver.value(P[t,i])-solver.value(P[t-1,i]);toggle=solver.value(A[t,i])!=solver.value(A[t-1,i])
            line.append('T' if toggle else 'B' if d>0 else 'F' if d<0 else '-')
        lines.append(tuple(line))
    s=(*start,0,0)
    for line in lines:s=sim.step(s,line)
    assert s[3]==copies and (not loop or s[:2]==start) and (not loop or s[2]&(m.target|m.forbidden)==0)
    return dict(start=start,lines=lines,accept=[t for t in accept if solver.value(accept[t])]),stats

def combine(case,program,loop):
    sim=Sim(case);s=sim.initial();out=[]
    # Prefer incumbent prefix when it reaches the synthesized start pose after an acceptance.
    states=sim.prefix(program)
    prefix=next((t for t in range(1,len(states)) if states[t][3] and states[t][:2]==(tuple(loop['start'][0]),loop['start'][1]) and states[t][2]&(sim.target|sim.forbidden)==0),None)
    if prefix is not None:out=program[:prefix];s=states[prefix]
    else:
        pos=loop['start'][0]
        while s[0]!=tuple(pos):
            line=tuple('-' if p==q else 'B' if delta(p,q,6*case[0])>0 else 'F' for p,q in zip(s[0],pos));out.append(line);s=sim.step(s,line)
        line=tuple('T' if loop['start'][1]>>i&1 else '-' for i in range(6));out.append(line);s=sim.step(s,line)
    for _ in range(case[2]+2):
        for line in loop['lines']:
            if s[3]>=case[2]:return out
            out.append(line);s=sim.step(s,line)
    return None

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--kind',default='2-medium');p.add_argument('--cases',default='51,36,50,131,159');p.add_argument('--seconds',type=float,default=8);p.add_argument('--copies',type=int,default=2);p.add_argument('--offset',type=int,default=0);p.add_argument('--horizon',type=int,default=0);p.add_argument('--single',action='store_true');a=p.parse_args()
    data=json.loads((BASE/'inventory.json').read_text());results=[]
    for index in map(int,a.cases.split(',')):
        b=data['bundles'][a.kind][index-1];case=(b['r'],frozenset(map(tuple,b['P'])),b['K']);program=list(map(tuple,b['program']))
        rec=next(x for x in data['records'] if x['kind']==a.kind and x['case']==index)
        H=a.horizon or (max(rec['accept_gaps'])*a.copies-1)
        found,stats=solve(case,program,H,a.copies,a.offset,a.seconds,not a.single)
        out=combine(case,program,found) if found and not a.single else found['lines'] if found else None
        if out:
            sim=Sim(case);s=sim.initial()
            for line in out:s=sim.step(s,line)
            assert s[3]==case[2]
        result=dict(kind=a.kind,case=index,before=len(program),after=len(out) if out else None,**stats,solution=found,program=out)
        results.append(result);print(json.dumps({k:v for k,v in result.items() if k not in ('solution','program')}),flush=True)
    dest=BASE/f'probe_{a.kind}_{a.copies}_{a.offset}_{a.horizon}_{int(a.single)}_{a.cases.replace(",","-")}.json';dest.write_text(json.dumps(results,indent=1))
