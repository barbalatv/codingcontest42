from pathlib import Path
from collections import deque
from functools import lru_cache
from itertools import product
from time import perf_counter
import argparse
from solve_l6 import parse, origins, delta
from solve_l4 import geometry, STEPS
from solve_l5 import verify

ROOT = Path(__file__).parent / 'level-6'


class Done(Exception): pass


class Machine:
    def __init__(self,r,pattern,count):
        self.r,self.pattern,self.required = r,pattern,count
        _,self.cells,self.rays = geometry(r)
        self.index = {p:i for i,p in enumerate(self.cells)}
        self.origins = origins(r)
        self.target = sum(1<<self.index[p] for p in pattern)
        self.forbidden_cells = {(y+dy,x+dx) for y,x in pattern for dy,dx in STEPS} & self.index.keys() - pattern
        self.forbidden = sum(1<<self.index[p] for p in self.forbidden_cells)
        self.pos = [0,5*r,4*r,3*r,2*r,r]
        self.active = [False]*6
        self.matter = self.accepted = 0
        self.program = []
        self.future = {}

    def move(self,i,goal):
        d = delta(self.pos[i],goal,6*self.r)
        return '-' if not d else 'B' if d>0 else 'F'

    def emit(self,line):
        line = list(line)
        for i,goal in self.future.items():
            if line[i] == '-' and not self.active[i]: line[i] = self.move(i,goal)
        for i,ch in enumerate(line):
            if ch == 'F': self.pos[i] = (self.pos[i]-1) % (6*self.r)
            elif ch == 'B': self.pos[i] = (self.pos[i]+1) % (6*self.r)
            elif ch == 'T': self.active[i] = not self.active[i]
        one=two=three=0
        for i in range(6):
            if self.active[i]:
                ray=self.rays[self.pos[i]][i]
                three |= two & ray
                two |= one & ray
                one |= ray
        self.matter=(self.matter|two)&~three
        if self.matter&self.target == self.target and not self.matter&self.forbidden:
            self.accepted+=1
            self.matter &= ~self.target
        self.program.append(tuple(line))
        if self.accepted >= self.required: raise Done

    def off(self):
        self.future={}
        if any(self.active): self.emit(['T' if a else '-' for a in self.active])

    def setup(self, directions, point):
        goals={i:self.origins[i][self.index[point]] for i in directions}
        # Retain at most one active beam while moving to avoid unintended writes.
        keep=next((i for i in directions if self.active[i]),None)
        line=['T' if a and i != keep else '-' for i,a in enumerate(self.active)]
        self.future={i:g for i,g in goals.items() if not self.active[i]}
        if 'T' in line: self.emit(line)
        self.future={}
        while any(self.pos[i]!=g for i,g in goals.items()):
            line=['-']*6
            for i,g in goals.items(): line[i]=self.move(i,g)
            self.emit(line)
        line=['-']*6
        for i in directions:
            if not self.active[i]: line[i]='T'
        if 'T' in line: self.emit(line)


@lru_cache(None)
def boundary_orders(r,pattern,required_subset=None):
    _,cells,_=geometry(r)
    available=set(cells)-pattern
    required={(y+dy,x+dx) for y,x in pattern for dy,dx in STEPS}&available
    if required_subset is not None:required &= required_subset
    if not required:
        return [(min(pattern),)], {}
    graph={p:[(p[0]+dy,p[1]+dx) for dy,dx in STEPS if (p[0]+dy,p[1]+dx) in available] for p in available}
    # Shortest paths between boundary cells through non-pattern cells.
    paths={}
    for source in sorted(required):
        prev={source:None}
        queue=deque([source])
        while queue:
            p=queue.popleft()
            for q in graph[p]:
                if q not in prev: prev[q]=p; queue.append(q)
        for target in required:
            if target in prev:
                route=[]; p=target
                while p!=source: route.append(p); p=prev[p]
                paths[source,target]=tuple(route[::-1])
    orders=[]
    # Starting at coordinate extremes yields different boundary traversals.
    starts=set()
    for axis in (lambda p:p[0],lambda p:p[1],lambda p:p[0]+p[1],lambda p:p[1]-p[0]):
        starts.add(min(required,key=lambda p:(axis(p),p)))
        starts.add(max(required,key=lambda p:(axis(p),p)))
    for start in sorted(starts):
        unvisited=set(required)-{start}
        order=[start]; current=start
        while unvisited:
            def cost(q):
                route=paths.get((current,q))
                dy,dx=q[0]-current[0],q[1]-current[1]
                jump=max(abs(dy),abs(dy+dx)//2,abs(dx-dy)//2)+2
                return (min(len(route),jump) if route is not None else jump,q)
            q=min(unvisited,key=cost)
            route=paths.get((current,q))
            if route is not None:
                dy,dx=q[0]-current[0],q[1]-current[1]
                jump=max(abs(dy),abs(dy+dx)//2,abs(dx-dy)//2)+2
                if len(route)<=jump:
                    for p in route: unvisited.discard(p)
                else:unvisited.discard(q)
            else: unvisited.remove(q)
            order.append(q); current=q
        orders.append(tuple(order))
    return orders,paths


def fill_erase(r,pattern,count,axis,ascending,triplet,order,paths):
    machine=Machine(r,pattern,count)
    o=machine.origins
    pair=(axis,axis+3)
    # Each selected pair fills all target-containing lines in monotone order.
    groups={}
    for p in sorted(pattern): groups.setdefault(o[axis][machine.index[p]],p)
    initial=[0,5*r,4*r,3*r,2*r,r]
    fillpoints=[groups[k] for k in sorted(groups,key=lambda k:delta(initial[axis],k,6*r),reverse=not ascending)]
    try:
        for cycle in range(count):
            before=machine.accepted
            route=fillpoints if cycle%2 == 0 else fillpoints[::-1]
            eraseorder=order if cycle%2 == 0 else order[::-1]
            machine.off()
            machine.future={i:o[i][machine.index[eraseorder[0]]] for i in triplet if i not in pair}
            # First relocate fill emitters while all inactive.
            goals={i:o[i][machine.index[route[0]]] for i in pair}
            while any(machine.pos[i]!=g for i,g in goals.items()):
                line=['-']*6
                for i,g in goals.items(): line[i]=machine.move(i,g)
                machine.emit(line)
            line=['-']*6
            for i in pair: line[i]='T'
            machine.emit(line)
            for point in route[1:]:
                goals={i:o[i][machine.index[point]] for i in pair}
                while any(machine.pos[i]!=g for i,g in goals.items()):
                    line=['-']*6
                    for i,g in goals.items(): line[i]=machine.move(i,g)
                    machine.emit(line)
            machine.future={}
            if machine.accepted>before: continue
            machine.setup(triplet,eraseorder[0])
            current=eraseorder[0]
            for target in eraseorder[1:]:
                path=paths.get((current,target))
                distance=max(abs(delta(machine.pos[i],o[i][machine.index[target]],6*r)) for i in triplet)
                if path is None or len(path)>distance+2: machine.setup(triplet,target)
                else:
                    for point in path:
                        line=['-']*6
                        for i in triplet:
                            goal=o[i][machine.index[point]]
                            assert abs(delta(machine.pos[i],goal,6*r))<=1
                            line[i]=machine.move(i,goal)
                        machine.emit(line)
                current=target
            assert machine.accepted>before,(r,len(pattern),machine.accepted,before)
    except Done:
        return machine.program
    raise AssertionError('Not complete')


def optimize_case(case,incumbent,effort=1):
    r,pattern,count=case
    best=incumbent
    # Rank inexpensive geometric estimates before simulating programs.
    candidates=[]
    o=origins(r); _,cells,_=geometry(r); index={p:i for i,p in enumerate(cells)}
    initial=[0,5*r,4*r,3*r,2*r,r]
    for axis in range(3):
        groups={}
        for p in pattern: groups.setdefault(o[axis][index[p]],p)
        _,_,raymasks=geometry(r)
        filled=0
        for p in groups:filled |= raymasks[p][axis]
        touched=frozenset(p for k,p in enumerate(cells) if filled>>k&1 and p not in pattern)
        orders,paths=boundary_orders(r,pattern,touched)
        points=[groups[k] for k in sorted(groups,key=lambda k:delta(initial[axis],k,6*r))]
        for ascending in (True,False):
            start,end=(points[0],points[-1]) if ascending else (points[-1],points[0])
            for order in orders:
                pathcost=sum(len(paths.get((p,q),())) if (p,q) in paths else 2+max(abs(delta(o[i][index[p]],o[i][index[q]],6*r)) for i in range(3)) for p,q in zip(order,order[1:]))
                for choice in product((0,3),repeat=3):
                    triplet=tuple(i+choice[i] for i in range(3))
                    reposition=max(abs(delta(o[i][index[end]],o[i][index[order[0]]],6*r)) for i in triplet)
                    setup=max(abs(delta(initial[i],o[i][index[start]],6*r)) for i in (axis,axis+3))
                    estimate=setup+count*(len(points)+pathcost+reposition+4)
                    candidates.append((estimate,axis,ascending,triplet,order,paths))
    candidates.sort(key=lambda c:c[:5])
    for _,axis,ascending,triplet,order,paths in candidates[:12*effort]:
        candidate=fill_erase(r,pattern,count,axis,ascending,triplet,order,paths)
        if len(candidate)<len(best): best=candidate
    return best


def load_programs(path):
    return [[tuple(line.split()) for line in block.splitlines()] for block in path.read_text().strip().split('\n\n')]


def save_programs(path,programs):
    path.write_text('\n\n'.join('\n'.join(' '.join(line) for line in p) for p in programs)+'\n\n',encoding='ascii')


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--limit',type=int,default=100000)
    parser.add_argument('--file',default='')
    parser.add_argument('--effort',type=int,default=1)
    args=parser.parse_args()
    started=perf_counter()
    backup=ROOT/'baseline_l6'
    backup.mkdir(exist_ok=True)
    for source in sorted(ROOT.glob('in_*.txt')):
        if args.file and args.file not in source.name: continue
        target=source.with_name(source.name.replace('in_','answer_',1))
        if not (backup/target.name).exists(): (backup/target.name).write_bytes(target.read_bytes())
        cases=parse(source); programs=load_programs(target)
        old=sum(map(len,programs)); improved=0
        for i,case in enumerate(cases[:args.limit]):
            candidate=optimize_case(case,programs[i],args.effort)
            if len(candidate)<len(programs[i]):
                assert verify(case[0],case[1],candidate)==case[2],(source.name,i)
                programs[i]=candidate; improved+=1
            if (i+1)%20==0:
                save_programs(target,programs)
                print(f'{source.name}: {i+1}/{len(cases)}, saved {old-sum(map(len,programs))} ticks; elapsed {perf_counter()-started:.1f}s',flush=True)
        save_programs(target,programs)
        print(f'{target.name}: {old} -> {sum(map(len,programs))}, improved {improved}/{len(cases)}; elapsed {perf_counter()-started:.1f}s',flush=True)


if __name__=='__main__': main()
