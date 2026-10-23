from pathlib import Path
from functools import lru_cache
from collections import Counter
from math import atan2
from time import perf_counter

STEPS = [(0, 2), (1, 1), (1, -1), (0, -2), (-1, -1), (-1, 1)]


def parse(path):
    tokens = iter(path.read_text().split())
    cases = []
    for _ in range(int(next(tokens))):
        r, length = int(next(tokens)), int(next(tokens))
        program = [tuple(next(tokens) for _ in range(6)) for _ in range(length)]
        assert all(ch in 'FBT-' for row in program for ch in row)
        cases.append((r, program))
    assert next(tokens, None) is None
    return cases


@lru_cache(None)
def geometry(r):
    rows = []
    for y in range(2*r+1):
        pad = abs(r-y)
        n = 2*r-pad+1
        chars = ['*']*n if y in (0, 2*r) else ['*']+['O']*(n-2)+['*']
        rows.append('-'*pad + '-'.join(chars) + '-'*pad)
    cells = [(y, x) for y, row in enumerate(rows) for x, ch in enumerate(row) if ch == 'O']
    index = {point: i for i, point in enumerate(cells)}
    corners = [(r, 0), (2*r, r), (2*r, 3*r), (r, 4*r), (0, 3*r), (0, r)]
    ring = []
    for (y, x), (yy, xx) in zip(corners, corners[1:]+corners[:1]):
        dy, dx = (yy-y)//r, (xx-x)//r
        ring.extend((y+k*dy, x+k*dx) for k in range(r))
    assert len(set(ring)) == 6*r
    rays = []
    for y, x in ring:
        directions = []
        for dy, dx in STEPS:
            mask = 0
            yy, xx = y+dy, x+dx
            while 0 <= yy <= 2*r and 0 <= xx <= 4*r:
                if (yy, xx) in index:
                    mask |= 1 << index[yy, xx]
                yy, xx = yy+dy, xx+dx
            directions.append(mask)
        rays.append(directions)
    return rows, cells, rays


def solve(r, program):
    rows, cells, rays = geometry(r)
    positions = [0, 5*r, 4*r, 3*r, 2*r, r]
    active = [False]*6
    matter = 0
    for line in program:
        for i, ch in enumerate(line):
            if ch == 'F': positions[i] = (positions[i]-1) % (6*r)
            elif ch == 'B': positions[i] = (positions[i]+1) % (6*r)
            elif ch == 'T': active[i] = not active[i]
        one = two = three = 0
        for i in range(6):
            if active[i]:
                ray = rays[positions[i]][i]
                three |= two & ray
                two |= one & ray
                one |= ray
        matter = (matter | two) & ~three
    result = list(map(list, rows))
    for i, (y, x) in enumerate(cells):
        if matter >> i & 1:
            result[y][x] = 'M'
    return '\n'.join(map(''.join, result))


@lru_cache(None)
def oracle_geometry(r):
    # Independently reconstruct the border and interior via hex inequalities.
    border, cells = [], []
    for y in range(2*r+1):
        for x in range(4*r+1):
            if (x-y-r) % 2:
                continue
            a, b = y-r, x-2*r
            distance = max(abs(a), abs(a+b)//2, abs(b-a)//2)
            if distance == r: border.append((y, x))
            elif distance < r: cells.append((y, x))
    border.sort(key=lambda p: atan2(p[0]-r, p[1]-2*r), reverse=True)
    assert len(border) == 6*r
    rays = {}
    for y, x in border:
        for i, (dy, dx) in enumerate(STEPS):
            rays[y, x, i] = tuple((yy, xx) for yy, xx in cells
                if (xx-x)*dy == (yy-y)*dx and (xx-x)*dx+(yy-y)*dy > 0)
    return border, cells, rays


def verify(r, program, output):
    border, cells, rays = oracle_geometry(r)
    corners = [(r, 0), (0, r), (0, 3*r), (r, 4*r), (2*r, 3*r), (2*r, r)]
    positions = [border.index(p) for p in corners]
    active = set()
    matter = set()
    for line in program:
        for i, instruction in enumerate(line):
            if instruction == 'T': active.symmetric_difference_update([i])
            elif instruction in 'FB':
                positions[i] = (positions[i] + (-1 if instruction == 'F' else 1)) % len(border)
        counts = Counter()
        for i in active:
            y, x = border[positions[i]]
            counts.update(rays[y, x, i])
        for cell, count in counts.items():
            if count == 2: matter.add(cell)
            elif count >= 3: matter.discard(cell)
    rows = output.splitlines()
    assert len(rows) == 2*r+1 and all(len(row) == 4*r+1 for row in rows)
    cellset, borderset = set(cells), set(border)
    for y, row in enumerate(rows):
        for x, ch in enumerate(row):
            p = y, x
            want = ('M' if p in matter else 'O') if p in cellset else '*' if p in borderset else '-'
            assert ch == want, (r, p, ch, want)


if __name__ == '__main__':
    start = perf_counter()
    root = Path(__file__).parent / 'level-4'
    for source in sorted(root.glob('in_*.txt')):
        cases = parse(source)
        answer = '\n\n'.join(solve(r, program) for r, program in cases) + '\n\n'
        target = source.with_name(source.name.replace('in_', 'answer_', 1))
        target.write_text(answer, encoding='ascii')
        if 'example' in source.name:
            expected = source.with_name('out_level-4_0-example.txt').read_text()
            assert answer.rstrip('\n') == expected.rstrip('\n'), 'Example mismatch'
        outputs = target.read_text().strip('\n').split('\n\n')
        assert len(outputs) == len(cases)
        for (r, program), output in zip(cases, outputs):
            verify(r, program, output)
        print(f'{target.name}: PASS, {len(cases)} programs, independent final disk validation', flush=True)
    # Full rail traversal, inactive movement, toggling and persistent firing.
    for r in (1, 2, 3):
        for program in ([('F',)*6]*(6*r), [('B',)*6]*(6*r),
                        [('T',)*6]+[('F',)*6]*(6*r)+[('T',)*6],
                        [('T',)*6]+[('-',)*6]*4):
            verify(r, program, solve(r, program))
    print(f'Example and boundary checks PASS; elapsed {perf_counter()-start:.3f}s')
