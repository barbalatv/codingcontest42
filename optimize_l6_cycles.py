from ortools.sat.python import cp_model
from time import perf_counter
from optimize_l6 import ROOT, Machine, Done, load_programs, save_programs
from solve_l6 import parse,delta
from solve_l5 import verify
import argparse


def solve_cycle(case,period,limit,workers=1):
    r,pattern,count=case
    m=Machine(*case)
    initial=m.pos[:]
    model=cp_model.CpModel()
    pos={};active={};choices={}
    for t in range(period):
        for i in range(6):
            pos[t,i]=model.new_int_var(1-r,r-1,f'p{t}_{i}')
            active[t,i]=model.new_bool_var(f'a{t}_{i}')
            options={}
            for q in range(1-r,r):
                p=(initial[i]+q)%(6*r)
                v=model.new_bool_var(f'c{t}_{i}_{q}')
                model.add(pos[t,i]==q).only_enforce_if(v)
                options[p]=v
            model.add(sum(options.values())==active[t,i])
            choices[t,i]=options
    table=[]
    for q in range(1-r,r):
        for a in (0,1):
            table.append((q,a,q,1-a))
            for qq in (q-1,q,q+1):
                if 1-r<=qq<r:table.append((q,a,qq,a))
    for t in range(period):
        for i in range(6):
            nxt=(t+1)%period
            model.add_allowed_assignments([pos[t,i],active[t,i],pos[nxt,i],active[nxt,i]],table)
    for k,p in enumerate(m.cells):
        if p not in pattern and not(m.forbidden>>k&1):continue
        coverage=[]
        for t in range(period):
            hits=sum(choices[t,i][m.origins[i][k]] for i in range(6))
            if p in pattern:
                model.add(hits<=2)
                covered=model.new_bool_var(f'h{t}_{k}')
                model.add(hits==2).only_enforce_if(covered)
                model.add(hits<=1).only_enforce_if(covered.Not())
                coverage.append(covered)
            else:model.add_linear_expression_in_domain(hits,cp_model.Domain.from_values([0,1,3,4,5,6]))
        if coverage:model.add_bool_or(coverage)
    setup=model.new_int_var(0,r-1,'setup')
    for i in range(6):
        model.add(setup>=pos[0,i]);model.add(setup>=-pos[0,i])
    model.minimize(setup)
    solver=cp_model.CpSolver();solver.parameters.max_time_in_seconds=limit;solver.parameters.num_search_workers=workers
    status=solver.solve(model)
    if status not in (cp_model.FEASIBLE,cp_model.OPTIMAL):return None,status
    states=[]
    for t in range(period):
        states.append(([(initial[i]+solver.value(pos[t,i]))%(6*r) for i in range(6)],
                       [bool(solver.value(active[t,i])) for i in range(6)]))
    try:
        goals,activation=states[0]
        while m.pos!=goals:m.emit([m.move(i,p) for i,p in enumerate(goals)])
        m.emit(['T' if a else '-' for a in activation])
        for step in range(1,period*count):
            goals,activation=states[step%period]
            line=[]
            for i in range(6):
                if activation[i]!=m.active[i]:
                    assert goals[i]==m.pos[i]
                    line.append('T')
                else:
                    assert abs(delta(m.pos[i],goals[i],6*r))<=1
                    line.append(m.move(i,goals[i]))
            m.emit(line)
    except Done:return m.program,status
    raise AssertionError('Cycle did not produce required count')


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--time',type=float,default=0.15);parser.add_argument('--file',default='')
    parser.add_argument('--max-period',type=int,default=6);parser.add_argument('--limit',type=int,default=100000);parser.add_argument('--max-matter',type=int,default=50)
    args=parser.parse_args();started=perf_counter()
    for source in sorted(ROOT.glob('in_*.txt')):
        if args.file and args.file not in source.name:continue
        cases=parse(source);target=source.with_name(source.name.replace('in_','answer_',1));programs=load_programs(target)
        old=sum(map(len,programs));improved=0
        for i,case in enumerate(cases[:args.limit]):
            r,pattern,count=case
            if len(pattern)<=args.max_matter:
                maxperiod=min(args.max_period,(len(programs[i])-1)//count)
                for period in range(2,maxperiod+1):
                    candidate,status=solve_cycle(case,period,args.time)
                    if candidate:
                        if len(candidate)<len(programs[i]):
                            assert verify(r,pattern,candidate)==count,(source.name,i)
                            programs[i]=candidate;improved+=1
                        break
            if (i+1)%10==0:
                save_programs(target,programs)
                print(f'{source.name}: {i+1}/{len(cases)}, saved {old-sum(map(len,programs))}; {perf_counter()-started:.1f}s',flush=True)
        save_programs(target,programs)
        print(f'{target.name}: {old} -> {sum(map(len,programs))}, improved {improved}; {perf_counter()-started:.1f}s',flush=True)
