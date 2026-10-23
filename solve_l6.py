from pathlib import Path
from functools import lru_cache
from itertools import combinations
from time import perf_counter
from solve_l4 import geometry, STEPS
from solve_l5 import verify


def parse(path):
    tokens = iter(path.read_text().split())
    cases = []
    for _ in range(int(next(tokens))):
        r, h, w, count = (int(next(tokens)) for _ in range(4))
        rows = [next(tokens) for _ in range(h)]
        assert h == 2*r+1 and w == 4*r+1 and all(len(row) == w for row in rows)
        pattern = frozenset((y,x) for y,row in enumerate(rows) for x,ch in enumerate(row) if ch == 'M')
        assert pattern and count > 0
        cases.append((r, pattern, count))
    assert next(tokens, None) is None
    return cases


@lru_cache(None)
def origins(r):
    _, cells, rays = geometry(r)
    result = []
    for direction in range(6):
        bycell = {}
        for pos in range(6*r):
            mask = rays[pos][direction]
            while mask:
                bit = mask & -mask
                index = bit.bit_length()-1
                assert index not in bycell
                bycell[index] = pos
                mask -= bit
        assert len(bycell) == len(cells)
        result.append(bycell)
    return result


def delta(a,b,length):
    return (b-a+length//2) % length - length//2


class Planner:
    def __init__(self,r,pattern,a,b):
        self.r, self.a, self.b = r,a,b
        self.length = 6*r
        _, cells, self.rays = geometry(r)
        self.index = {p:i for i,p in enumerate(cells)}
        self.target = sum(1 << self.index[p] for p in pattern)
        neighbors = {(y+dy,x+dx) for y,x in pattern for dy,dx in STEPS} - pattern
        self.forbidden = sum(1 << i for i,p in enumerate(cells) if p in neighbors)
        o = origins(r)
        self.points = [(o[a][self.index[p]],o[b][self.index[p]]) for p in sorted(pattern)]
        initial = [0,5*r,4*r,3*r,2*r,r]
        self.initial = initial[a],initial[b]
        self.cache = {}

    def transition(self, start, goal):
        key = start,goal
        if key in self.cache: return self.cache[key]
        ds = [delta(s,g,self.length) for s,g in zip(start,goal)]
        distances = list(map(abs,ds))
        signs = [1 if d>0 else -1 for d in ds]
        duration = max(distances)
        if duration == 0:
            result = (('-', '-'),)
            self.cache[key] = result
            return result
        # Try shortest simultaneous routes, varying when the shorter move starts.
        for late_a,late_b in ((False,False),(True,False),(False,True),(True,True)):
            late = [late_a,late_b]
            positions = list(start)
            program = []
            safe = True
            for tick in range(duration):
                line = ['-','-']
                for j in range(2):
                    offset = duration-distances[j] if late[j] else 0
                    if offset <= tick < offset+distances[j]:
                        positions[j] = (positions[j]+signs[j]) % self.length
                        line[j] = 'B' if signs[j]>0 else 'F'
                created = self.rays[positions[0]][self.a] & self.rays[positions[1]][self.b]
                if created & self.forbidden:
                    safe = False
                    break
                program.append(tuple(line))
            if safe:
                result = tuple(program)
                self.cache[key] = result
                return result
        # Disable one beam during transit; overlap toggles with the other motion.
        off = min(range(2),key=lambda j:max(distances[j]+2,distances[1-j]))
        duration = max(distances[off]+2,distances[1-off])
        program = [['-','-'] for _ in range(duration)]
        program[0][off] = program[-1][off] = 'T'
        for j in range(2):
            offset = 1 if j == off else 0
            for tick in range(offset,offset+distances[j]):
                program[tick][j] = 'B' if signs[j]>0 else 'F'
        result = tuple(map(tuple,program))
        self.cache[key] = result
        return result

    def orders(self):
        for swap in (False,True):
            for reverse in (False,True):
                for zig in (False,True):
                    def coord(p,j):
                        return delta(self.initial[j],p[j],self.length)
                    major,minor = (1,0) if swap else (0,1)
                    groups = {}
                    for p in self.points: groups.setdefault(coord(p,major),[]).append(p)
                    order = []
                    for k,g in enumerate(sorted(groups,reverse=reverse)):
                        order.extend(sorted(groups[g],key=lambda p:coord(p,minor),reverse=bool(k%2)^zig))
                    yield order

    def choose(self,count):
        best = None
        for order in self.orders():
            setup = max(abs(delta(s,g,self.length)) for s,g in zip(self.initial,order[0]))+1
            transitions = [self.transition(p,q) for p,q in zip(order,order[1:])]
            score = setup + count*sum(map(len,transitions)) + count-1
            if best is None or score < best[0]: best = score,order,transitions
        return best

    def program(self,order,count):
        positions = list(self.initial)
        active = [False,False]
        matter = accepted = 0
        output = []
        def emit(pair):
            nonlocal matter,accepted
            line = ['-']*6
            for j,i in enumerate((self.a,self.b)):
                ch = pair[j]
                line[i] = ch
                if ch == 'F': positions[j] = (positions[j]-1) % self.length
                elif ch == 'B': positions[j] = (positions[j]+1) % self.length
                elif ch == 'T': active[j] = not active[j]
            if all(active):
                matter |= self.rays[positions[0]][self.a] & self.rays[positions[1]][self.b]
            assert not matter & self.forbidden
            if matter & self.target == self.target:
                accepted += 1
                matter &= ~self.target
            output.append(tuple(line))
            return accepted >= count
        ds = [delta(s,g,self.length) for s,g in zip(positions,order[0])]
        for tick in range(max(map(abs,ds))+1):
            pair = []
            for d in ds:
                pair.append(('B' if d>0 else 'F') if tick<abs(d) else 'T' if tick==abs(d) else '-')
            if emit(pair): return output
        current = order[0]
        for sweep in range(count):
            route = order if sweep%2 == 0 else order[::-1]
            if sweep and emit(('-','-')): return output
            for goal in route[1:]:
                for pair in self.transition(current,goal):
                    if emit(pair): return output
                current = goal
        assert accepted == count, (accepted,count)
        return output


def solve(r,pattern,count):
    best = None
    for a,b in combinations(range(6),2):
        if (a-b)%3 == 0: continue
        planner = Planner(r,pattern,a,b)
        candidate = planner.choose(count)
        if best is None or candidate[0] < best[0]:
            best = candidate[0],planner,candidate[1]
    return best[1].program(best[2],count)


if __name__ == '__main__':
    start = perf_counter()
    root = Path(__file__).parent / 'level-6'
    for source in sorted(root.glob('in_*.txt')):
        cases = parse(source)
        programs = []
        for r,pattern,count in cases:
            program = solve(r,pattern,count)
            actual = verify(r,pattern,program)
            assert actual == count, (source.name,len(programs),actual,count)
            programs.append(program)
        target = source.with_name(source.name.replace('in_','answer_',1))
        target.write_text('\n\n'.join('\n'.join(' '.join(line) for line in p) for p in programs)+'\n\n',encoding='ascii')
        # Reparse final artifact and validate all six instructions and case counts.
        disk = target.read_text().strip().split('\n\n')
        assert len(disk) == len(cases)
        for block,original in zip(disk,programs):
            assert [tuple(line.split()) for line in block.splitlines()] == original
            assert all(len(line)==6 and all(ch in 'FBT-' for ch in line) for line in original)
        print(f'{target.name}: PASS, {len(cases)} programs, {sum(map(len,programs))} ticks; independent simulation',flush=True)
    print(f'All final files validated; elapsed {perf_counter()-start:.3f}s',flush=True)
