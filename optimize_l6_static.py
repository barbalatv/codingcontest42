from ortools.sat.python import cp_model
from time import perf_counter
from optimize_l6 import ROOT, Machine, Done, load_programs, save_programs
from solve_l6 import parse, delta
from solve_l5 import verify
import argparse


def solve_static(case,limit=0.15):
    r,pattern,count=case
    machine=Machine(*case)
    model=cp_model.CpModel()
    choices=[]; selected=[]
    initial=machine.pos[:]
    duration=model.new_int_var(0,r-1,'distance')
    for i in range(6):
        options={p:model.new_bool_var(f'e{i}p{p}') for p in range(6*r) if machine.rays[p][i]}
        model.add(sum(options.values())<=1)
        for p,v in options.items(): model.add(duration>=abs(delta(initial[i],p,6*r))*v)
        choices.append(options)
    for k,point in enumerate(machine.cells):
        if point not in pattern and not (machine.forbidden>>k&1): continue
        hits=sum(choices[i][machine.origins[i][k]] for i in range(6))
        if point in pattern: model.add(hits==2)
        else: model.add_linear_expression_in_domain(hits,cp_model.Domain.from_values([0,1,3,4,5,6]))
    model.minimize(duration)
    solver=cp_model.CpSolver()
    solver.parameters.max_time_in_seconds=limit
    solver.parameters.num_search_workers=1
    status=solver.solve(model)
    if status not in (cp_model.OPTIMAL,cp_model.FEASIBLE): return None,status
    goals={i:p for i,options in enumerate(choices) for p,v in options.items() if solver.value(v)}
    try:
        while any(machine.pos[i]!=p for i,p in goals.items()):
            line=['-']*6
            for i,p in goals.items(): line[i]=machine.move(i,p)
            machine.emit(line)
        machine.emit(['T' if i in goals else '-' for i in range(6)])
        while True: machine.emit(['-']*6)
    except Done: return machine.program,status


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--time',type=float,default=0.1);parser.add_argument('--file',default='')
    args=parser.parse_args(); started=perf_counter()
    for source in sorted(ROOT.glob('in_*.txt')):
        if args.file and args.file not in source.name:continue
        cases=parse(source);target=source.with_name(source.name.replace('in_','answer_',1));programs=load_programs(target)
        old=sum(map(len,programs));improved=0;found=0
        for i,case in enumerate(cases):
            candidate,status=solve_static(case,args.time)
            if candidate:
                found+=1
                if len(candidate)<len(programs[i]):
                    assert verify(case[0],case[1],candidate)==case[2]
                    programs[i]=candidate;improved+=1
            if (i+1)%50==0:save_programs(target,programs)
        save_programs(target,programs)
        print(f'{target.name}: {old} -> {sum(map(len,programs))}; static feasible {found}, improved {improved}; {perf_counter()-started:.1f}s',flush=True)
