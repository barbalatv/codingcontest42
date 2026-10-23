from optimize_l6_cycles import solve_cycle
from optimize_l6 import ROOT,load_programs,save_programs
from solve_l6 import parse
from solve_l5 import verify
from time import perf_counter
import argparse

parser=argparse.ArgumentParser();parser.add_argument('--file',default='medium');parser.add_argument('--limit',type=int,default=20)
parser.add_argument('--time',type=float,default=0.8);parser.add_argument('--workers',type=int,default=8)
args=parser.parse_args();start=perf_counter()
for source in sorted(ROOT.glob('in_*.txt')):
    if args.file and args.file not in source.name:continue
    cases=parse(source);target=source.with_name(source.name.replace('in_','answer_',1));programs=load_programs(target)
    old=sum(map(len,programs))
    ranked=sorted(range(len(cases)),key=lambda i:len(programs[i])-cases[i][2]*max(2,(len(cases[i][1])+11)//12),reverse=True)
    for iteration,i in enumerate(ranked[:args.limit]):
        case=cases[i];previous=len(programs[i]);maxperiod=min(10,(previous-case[0])//case[2])
        # Establish a short feasible cycle, then try to reduce it.
        for period in (4,6,8,10,3,2,5,7,9):
            if period>maxperiod or period*case[2]>=len(programs[i]):continue
            candidate,status=solve_cycle(case,period,args.time,args.workers)
            if candidate and len(candidate)<len(programs[i]):
                assert verify(case[0],case[1],candidate)==case[2]
                programs[i]=candidate
        save_programs(target,programs)
        print(f'{source.name}: case {i+1}, {previous} -> {len(programs[i])}; {iteration+1}/{min(args.limit,len(cases))}; elapsed {perf_counter()-start:.1f}s',flush=True)
    print(f'{target.name}: {old} -> {sum(map(len,programs))}',flush=True)
