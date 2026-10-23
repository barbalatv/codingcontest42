from optimize_l6 import ROOT,load_programs,save_programs
from solve_l6 import parse
from solve_l4 import geometry,STEPS
from solve_l5 import verify
from time import perf_counter


class Sim:
    def __init__(self,case):
        r,pattern,self.required=case
        self.r=r;_,cells,self.rays=geometry(r)
        self.target=sum(1<<i for i,p in enumerate(cells) if p in pattern)
        boundary={(y+dy,x+dx) for y,x in pattern for dy,dx in STEPS}-pattern
        self.forbidden=sum(1<<i for i,p in enumerate(cells) if p in boundary)
    def initial(self):return ((0,5*self.r,4*self.r,3*self.r,2*self.r,self.r),0,0,0)
    def step(self,state,line):
        pos,active,matter,count=state;pos=list(pos)
        for i,ch in enumerate(line):
            if ch=='F':pos[i]=(pos[i]-1)%(6*self.r)
            elif ch=='B':pos[i]=(pos[i]+1)%(6*self.r)
            elif ch=='T':active^=1<<i
        one=two=three=0
        for i in range(6):
            if active>>i&1:
                ray=self.rays[pos[i]][i];three|=two&ray;two|=one&ray;one|=ray
        matter=(matter|two)&~three
        if matter&self.target==self.target and not matter&self.forbidden:
            count+=1;matter&=~self.target
        return (tuple(pos),active,matter,count)
    def prefix(self,program):
        states=[self.initial()]
        for line in program:states.append(self.step(states[-1],line))
        return states
    def check(self,state,program,start):
        for k in range(start,len(program)):
            state=self.step(state,program[k])
            if state[3]>=self.required:return k+1
        return None


def compact(case,program):
    sim=Sim(case)
    for size in (16,8,4,2,1):
        states=sim.prefix(program);i=0
        while i+size<=len(program):
            end=sim.check(states[i],program,i+size)
            if end is not None:
                program=program[:i]+program[i+size:end]
                states=sim.prefix(program)
                i=max(0,i-size)
            else:i+=size
    states=sim.prefix(program);i=0
    while i+1<len(program):
        a,b=program[i:i+2]
        if all(x=='-' or y=='-' for x,y in zip(a,b)):
            merged=tuple(y if x=='-' else x for x,y in zip(a,b))
            state=sim.step(states[i],merged)
            end=i+2 if state[3]>=sim.required else sim.check(state,program,i+2)
            if end is not None:
                program=program[:i]+[merged]+program[i+2:end];states=sim.prefix(program);i=max(0,i-1);continue
        i+=1
    return program


if __name__=='__main__':
    started=perf_counter()
    for source in sorted(ROOT.glob('in_*.txt')):
        cases=parse(source);target=source.with_name(source.name.replace('in_','answer_',1));programs=load_programs(target)
        old=sum(map(len,programs));improved=0
        for i,case in enumerate(cases):
            candidate=compact(case,programs[i])
            if len(candidate)<len(programs[i]):
                assert verify(case[0],case[1],candidate)==case[2],(source.name,i)
                programs[i]=candidate;improved+=1
            if (i+1)%25==0:
                save_programs(target,programs)
                print(f'{source.name}: {i+1}/{len(cases)}, saved {old-sum(map(len,programs))}; {perf_counter()-started:.1f}s',flush=True)
        save_programs(target,programs)
        print(f'{target.name}: {old} -> {sum(map(len,programs))}, improved {improved}; {perf_counter()-started:.1f}s',flush=True)
