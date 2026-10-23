from ortools.sat.python import cp_model
from optimize_l6 import ROOT,Machine,Done,load_programs
from optimize_l6_compact import Sim
from solve_l6 import parse,origins,delta
from solve_l4 import geometry
from solve_l5 import verify
from phase2_run import atomic_save
from phase2_regress import cyclic_free
from time import perf_counter
import argparse


def extract(case,program):
    sim=Sim(case);state=sim.initial();seen={}
    for k,line in enumerate(program):
        before=state[3];state=sim.step(state,line)
        if state[3]>before:
            key=state[:2]
            if key in seen:
                index,count=seen[key]
                if state[3]-count==1:return state[:2],program[:index],program[index:k+1]
            seen[key]=k+1,state[3]
    return None


def solve_loop(case,start,oldcycle,horizon,seconds,workers,offset=0):
    r,pattern,count=case;poses,activation=start
    m=Machine(*case);model=cp_model.CpModel();P={};A={};Z={};length=6*r
    if offset<0:offset=max(0,(length-1)//2-horizon//2)
    origin=origins(r)
    for t in range(horizon+1):
        distance=min(t,horizon-t)+offset
        for i in range(6):
            P[t,i]=model.new_int_var(-distance,distance,f'p{t}_{i}')
            A[t,i]=model.new_bool_var(f'a{t}_{i}')
            if not offset and t in (0,horizon):model.add(A[t,i]==int(activation>>i&1))
            if not t:continue
            options={}
            for q in range(-distance,distance+1):
                v=model.new_bool_var(f'z{t}_{i}_{q}');model.add(P[t,i]==q).only_enforce_if(v);options[q]=v
            model.add(sum(options.values())==A[t,i]);Z[t,i]=options
    if offset:
        for i in range(6):model.add(P[horizon,i]==P[0,i]);model.add(A[horizon,i]==A[0,i])
    transition=[(d,a,b) for d in (-1,0,1) for a in (0,1) for b in (0,1) if d==0 or a==b]
    for t in range(1,horizon+1):
        for i in range(6):
            step=model.new_int_var(-1,1,f'd{t}_{i}');model.add(step==P[t,i]-P[t-1,i])
            model.add_allowed_assignments([step,A[t-1,i],A[t,i]],transition)
    table=[(previous,n,0 if n>=3 else 1 if n==2 else previous) for previous in (0,1) for n in range(7)]
    presence={};target_ids=[];forbidden_ids=[]
    for k,p in enumerate(m.cells):
        if p not in pattern and not (m.forbidden>>k&1):continue
        (target_ids if p in pattern else forbidden_ids).append(k)
        previous=0
        for t in range(1,horizon+1):
            hits=[]
            for i in range(6):
                q=delta(poses[i],origin[i][k],length)
                if q in Z[t,i]:hits.append(Z[t,i][q])
            n=model.new_int_var(0,6,f'n{t}_{k}');model.add(n==sum(hits))
            value=model.new_bool_var(f'm{t}_{k}');presence[t,k]=value
            model.add_allowed_assignments([previous,n,value],table)
            previous=value
        model.add(previous==int(p in pattern))
    for t in range(1,horizon):
        model.add_bool_or([presence[t,k].Not() for k in target_ids]+[presence[t,k] for k in forbidden_ids])
    # A compressed incumbent is a hint, not a hard restriction on intermediate states.
    oldstates=[(tuple(poses),activation)];pos=list(poses);active=activation
    for line in oldcycle:
        for i,ch in enumerate(line):
            if ch=='F':pos[i]=(pos[i]-1)%length
            elif ch=='B':pos[i]=(pos[i]+1)%length
            elif ch=='T':active^=1<<i
        oldstates.append((tuple(pos),active))
    for t in range(horizon+1):
        source=oldstates[round(t*len(oldcycle)/horizon)];distance=min(t,horizon-t)+offset
        for i in range(6):
            q=delta(poses[i],source[0][i],length);q=max(-distance,min(distance,q))
            model.add_hint(P[t,i],q);model.add_hint(A[t,i],int(source[1]>>i&1))
    solver=cp_model.CpSolver();solver.parameters.max_time_in_seconds=seconds;solver.parameters.num_search_workers=workers
    status=solver.solve(model)
    if status not in (cp_model.OPTIMAL,cp_model.FEASIBLE):return None,None,solver.status_name(status)
    newstart=tuple((poses[i]+solver.value(P[0,i]))%length for i in range(6)),sum(int(solver.value(A[0,i]))<<i for i in range(6))
    program=[];pos=list(newstart[0]);active=newstart[1]
    for t in range(1,horizon+1):
        line=[]
        for i in range(6):
            goal=(poses[i]+solver.value(P[t,i]))%length;on=bool(solver.value(A[t,i]))
            if on!=bool(active>>i&1):
                assert goal==pos[i];line.append('T');active^=1<<i
            else:
                d=delta(pos[i],goal,length);assert abs(d)<=1;line.append('-' if not d else 'B' if d>0 else 'F')
            pos[i]=goal
        program.append(tuple(line))
    return program,newstart,solver.status_name(status)


def combine(case,seed,cycle,bound):
    m=Machine(*case)
    try:
        for line in seed:m.emit(line)
        for _ in range(case[2]+1):
            for line in cycle:
                m.emit(line)
                if len(m.program)>=bound:return None
    except Done:return m.program
    return None


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--file',default='medium');parser.add_argument('--limit',type=int,default=8);parser.add_argument('--time',type=float,default=1.5);parser.add_argument('--workers',type=int,default=8)
    parser.add_argument('--offset',type=int,default=0)
    args=parser.parse_args();started=perf_counter()
    for source in sorted(ROOT.glob('in_*.txt')):
        if args.file not in source.name:continue
        cases=parse(source);target=source.with_name(source.name.replace('in_','answer_',1));programs=load_programs(target)
        ranked=[]
        for i,(case,program) in enumerate(zip(cases,programs)):
            cycle=extract(case,program)
            if cycle and len(cycle[2])>=4 and case[2]>=3:
                estimated=(len(cycle[2])-max(2,(len(case[1])+11)//12))*(case[2]-1)
                ranked.append((estimated,i,cycle))
        ranked.sort(reverse=True);old=sum(map(len,programs));wins=0
        for _,i,loop in ranked[:args.limit]:
            start,seed,cycle=loop;before=len(programs[i]);period=len(cycle)
            for horizon in sorted({max(2,round(period*0.7)),period-1}):
                new,newstart,status=solve_loop(cases[i],start,cycle,horizon,args.time,args.workers,args.offset)
                if new:
                    if args.offset:
                        pose=sum((p+128*int(newstart[1]>>j&1))<<(8*j) for j,p in enumerate(newstart[0]))
                        candidate=cyclic_free(cases[i],programs[i],pose,new)
                    else:candidate=combine(cases[i],seed,new,len(programs[i]))
                    if candidate and len(candidate)<len(programs[i]):
                        assert verify(cases[i][0],cases[i][1],candidate)==cases[i][2]
                        programs[i]=candidate;atomic_save(target,programs);wins+=1
                print(f'{source.name} case={i+1}: period {period}->{horizon} {status}; score {before}->{len(programs[i])}; elapsed={perf_counter()-started:.1f}s',flush=True)
        print(f'FILE {target.name}: {old}->{sum(map(len,programs))}, wins={wins}',flush=True)
