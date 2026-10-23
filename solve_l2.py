from pathlib import Path

STEPS = {'1': (0, 2), '2': (1, 1), '3': (1, -1),
         '4': (0, -2), '5': (-1, -1), '6': (-1, 1)}


def parse(path):
    lines = iter(line for line in path.read_text().splitlines() if line.strip())
    count = int(next(lines))
    cases = []
    for _ in range(count):
        radius, height, width = map(int, next(lines).split())
        rows = [next(lines) for _ in range(height)]
        assert height == 2 * radius + 1 and width == 4 * radius + 1
        assert all(len(row) == width for row in rows)
        cases.append(rows)
    assert next(lines, None) is None
    return cases


def emitter(rows):
    found = [(y, x, ch) for y, row in enumerate(rows)
             for x, ch in enumerate(row) if ch in STEPS]
    assert len(found) == 1
    return found[0]


def solve(rows):
    grid = list(map(list, rows))
    y, x, direction = emitter(rows)
    dy, dx = STEPS[direction]
    y, x = y + dy, x + dx
    while 0 <= y < len(rows) and 0 <= x < len(rows[0]):
        if grid[y][x] == 'O':
            grid[y][x] = 'M'
        y, x = y + dy, x + dx
    return '\n'.join(map(''.join, grid))


root = Path(__file__).parent / 'level-2'
for source in sorted(root.glob('in_*.txt')):
    cases = parse(source)
    answer = '\n\n'.join(map(solve, cases)) + '\n\n'
    target = source.with_name(source.name.replace('in_', 'answer_', 1))
    target.write_text(answer, encoding='ascii')
    if 'example' in source.name:
        expected = source.with_name('out_level-2_0-example.txt').read_text()
        assert answer.rstrip('\n') == expected.rstrip('\n'), 'Example mismatch'
    outputs = target.read_text().strip('\n').split('\n\n')
    assert len(outputs) == len(cases)
    matter = 0
    for original, output in zip(cases, outputs):
        result = output.splitlines()
        assert len(result) == len(original)
        ey, ex, direction = emitter(original)
        dy, dx = STEPS[direction]
        for y, row in enumerate(original):
            assert len(result[y]) == len(row)
            for x, ch in enumerate(row):
                # Independent geometric check: collinear and forward of emitter.
                on_ray = (x-ex)*dy == (y-ey)*dx and (x-ex)*dx+(y-ey)*dy > 0
                want = 'M' if ch == 'O' and on_ray else ch
                assert result[y][x] == want, (source.name, y, x)
                matter += want == 'M'
    print(f'{target.name}: PASS, {len(cases)} boards, {matter} matter cells')
print('All six example directions match; final disk geometry validation: PASS')
