from time import perf_counter
from optimize_l6 import ROOT,load_programs
from optimize_l6_compact import compact
from phase2_run import atomic_save
from solve_l6 import parse
from solve_l5 import verify

started=perf_counter()
for source in sorted(ROOT.glob('in_*.txt')):
    if not any(x in source.name for x in ('medium','large','enormous')):continue
    cases=parse(source);target=source.with_name(source.name.replace('in_','answer_',1));programs=load_programs(target)
    before=sum(map(len,programs));wins=0
    for i,case in enumerate(cases):
        candidate=compact(case,programs[i])
        if len(candidate)<len(programs[i]):
            assert verify(case[0],case[1],candidate)==case[2]
            programs[i]=candidate;atomic_save(target,programs);wins+=1
    print(f'{target.name}: {before}->{sum(map(len,programs))}, improved={wins}; elapsed={perf_counter()-started:.2f}s',flush=True)
