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


def emitters(rows):
    return [(y, x, STEPS[ch]) for y, row in enumerate(rows)
            for x, ch in enumerate(row) if ch in STEPS]


def state(ch, hits):
    return 'O' if hits >= 3 else 'M' if hits == 2 else ch


def solve(rows):
    height, width = len(rows), len(rows[0])
    hits = [[0] * width for _ in rows]
    sources = emitters(rows)
    assert len(sources) <= 6
    for y, x, (dy, dx) in sources:
        y, x = y + dy, x + dx
        while 0 <= y < height and 0 <= x < width:
            hits[y][x] += 1
            y, x = y + dy, x + dx
    return '\n'.join(''.join(state(ch, hits[y][x]) if ch in 'OM' else ch
                             for x, ch in enumerate(row))
                     for y, row in enumerate(rows))


root = Path(__file__).parent / 'level-3'
for source in sorted(root.glob('in_*.txt')):
    cases = parse(source)
    answer = '\n\n'.join(map(solve, cases)) + '\n\n'
    target = source.with_name(source.name.replace('in_', 'answer_', 1))
    target.write_text(answer, encoding='ascii')
    if 'example' in source.name:
        expected = source.with_name('out_level-3_0-example.txt').read_text()
        assert answer.rstrip('\n') == expected.rstrip('\n'), 'Example mismatch'
    outputs = target.read_text().strip('\n').split('\n\n')
    assert len(outputs) == len(cases)
    coverage = [0] * 7
    for original, output in zip(cases, outputs):
        result = output.splitlines()
        assert len(result) == len(original)
        sources = emitters(original)
        for y, row in enumerate(original):
            assert len(result[y]) == len(row)
            for x, ch in enumerate(row):
                expected = ch
                if ch in 'OM':
                    # Independent geometric oracle, without ray traversal.
                    count = sum((x-ex)*dy == (y-ey)*dx and
                                (x-ex)*dx+(y-ey)*dy > 0
                                for ey, ex, (dy, dx) in sources)
                    coverage[count] += 1
                    if count == 2:
                        expected = 'M'
                    elif count > 2:
                        expected = 'O'
                assert result[y][x] == expected, (source.name, y, x)
    print(f'{target.name}: PASS, {len(cases)} boards; cells by hit count: {coverage}')

for ch in 'OM':
    for count in range(7):
        expected = ch if count < 2 else 'M' if count == 2 else 'O'
        assert state(ch, count) == expected
print('Example match, all 0..6 hit transitions, final disk validation: PASS')
