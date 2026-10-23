from pathlib import Path


def board(radius):
    rows = []
    for y in range(2 * radius + 1):
        indent = abs(radius - y)
        width = 2 * radius - indent + 1
        cells = ['*'] * width if y in (0, 2 * radius) else ['*'] + ['O'] * (width - 2) + ['*']
        rows.append('-' * indent + '-'.join(cells) + '-' * indent)
    return '\n'.join(rows)


root = Path(__file__).parent / 'level-1'
for source in sorted(root.glob('in_*.txt')):
    values = list(map(int, source.read_text().split()))
    assert len(values) == values[0] + 1
    answer = '\n\n'.join(board(r) for r in values[1:]) + '\n\n'
    target = source.with_name(source.name.replace('in_', 'answer_', 1))
    target.write_text(answer, encoding='ascii')
    if 'example' in source.name:
        expected = source.with_name('out_level-1_0-example.txt').read_text()
        assert answer.rstrip('\n') == expected.rstrip('\n'), 'Example mismatch'
    # Reparse the final disk bytes and check geometric invariants separately.
    paragraphs = target.read_text().strip('\n').split('\n\n')
    assert len(paragraphs) == values[0]
    for r, paragraph in zip(values[1:], paragraphs):
        rows = paragraph.splitlines()
        assert len(rows) == 2 * r + 1
        assert all(len(row) == 4 * r + 1 for row in rows)
        assert rows == rows[::-1]
        assert all(row == row[::-1] for row in rows)
        assert sum(row.count('O') for row in rows) == 1 + 3 * r * (r - 1)
        assert sum(row.count('*') for row in rows) == 6 * r
        assert set(paragraph) <= set('O*-\n')
    print(f'{target.name}: PASS, {len(paragraphs)} boards')

assert board(1) == '-*-*-\n*-O-*\n-*-*-'
print('Example match, radius 1 edge case, final disk validation: PASS')
