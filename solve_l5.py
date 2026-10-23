from pathlib import Path
from collections import Counter
from time import perf_counter
from solve_l4 import geometry, oracle_geometry, STEPS


def parse(path):
    tokens = iter(path.read_text().split())
    cases = []
    for _ in range(int(next(tokens))):
        r, height, width = (int(next(tokens)) for _ in range(3))
        rows = [next(tokens) for _ in range(height)]
        assert height == 2*r+1 and width == 4*r+1
        assert all(len(row) == width for row in rows)
        pattern = {(y, x) for y, row in enumerate(rows) for x, ch in enumerate(row) if ch == 'M'}
        assert pattern
        length = int(next(tokens))
        program = [tuple(next(tokens) for _ in range(6)) for _ in range(length)]
        assert all(ch in 'FBT-' for line in program for ch in line)
        cases.append((r, pattern, program))
    assert next(tokens, None) is None
    return cases


def solve(r, pattern, program):
    _, cells, rays = geometry(r)
    cellset = set(cells)
    assert pattern <= cellset
    neighbors = {(y+dy, x+dx) for y, x in pattern for dy, dx in STEPS} & cellset
    neighbors -= pattern
    pattern_mask = sum(1 << i for i, p in enumerate(cells) if p in pattern)
    neighbor_mask = sum(1 << i for i, p in enumerate(cells) if p in neighbors)
    positions = [0, 5*r, 4*r, 3*r, 2*r, r]
    active = [False]*6
    matter = submissions = 0
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
        if matter & pattern_mask == pattern_mask and not matter & neighbor_mask:
            submissions += 1
            matter &= ~pattern_mask
    return submissions


def verify(r, pattern, program):
    border, cells, rays = oracle_geometry(r)
    corners = [(r, 0), (0, r), (0, 3*r), (r, 4*r), (2*r, 3*r), (2*r, r)]
    positions = [border.index(p) for p in corners]
    active, matter = set(), set()
    submissions = 0
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
        if pattern <= matter:
            # Independent detection: flood-fill the connected component.
            component = {next(iter(pattern))}
            stack = list(component)
            while stack:
                y, x = stack.pop()
                for dy, dx in STEPS:
                    p = y+dy, x+dx
                    if p in matter and p not in component:
                        component.add(p)
                        stack.append(p)
            if component == pattern:
                submissions += 1
                matter.difference_update(pattern)
    return submissions


if __name__ == '__main__':
    start = perf_counter()
    root = Path(__file__).parent / 'level-5'
    for source in sorted(root.glob('in_*.txt')):
        cases = parse(source)
        answers = [solve(*case) for case in cases]
        target = source.with_name(source.name.replace('in_', 'answer_', 1))
        target.write_text('\n'.join(map(str, answers))+'\n', encoding='ascii')
        disk = list(map(int, target.read_text().split()))
        assert len(disk) == len(cases)
        if 'example' in source.name:
            expected = list(map(int, source.with_name('out_level-5_0-example.txt').read_text().split()))
            assert disk == expected, (disk, expected)
        for i, (case, answer) in enumerate(zip(cases, disk)):
            independent = verify(*case)
            assert answer == independent, (source.name, i, answer, independent)
        print(f'{target.name}: PASS, {len(cases)} programs, {sum(disk)} submissions; independent simulation and flood-fill', flush=True)
    print(f'Final disk validation PASS; elapsed {perf_counter()-start:.3f}s')
