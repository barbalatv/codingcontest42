"""Dump all level-6 cases into a flat text format for the C++ searchers."""
import sys
sys.dont_write_bytecode = True
from sim import *


def w(x, nw=6):
    return ' '.join(str((x >> (64 * i)) & ((1 << 64) - 1)) for i in range(nw))


def main(out='cases.txt'):
    lines = []
    for ds in ('medium', 'large', 'enormous'):
        cs = cases(ds)
        ps = programs(ds)
        lines.append(f'# dataset {ds} n {len(cs)}')
        for i, (c, p) in enumerate(zip(cs, ps)):
            m = Machine(c)
            r = c[0]
            lines.append(f'case {ds} {i+1} {r} {c[2]} {m.rel.bit_count()} {len(p)}')
            lines.append(f'cur {len(p)}')
            enc = encode(p)
            for t in range(0, len(enc), 40):
                lines.append('prog ' + ' '.join(map(str, enc[t:t+40])))
            lines.append('init ' + ' '.join(map(str, m.initial)))
            lines.append('target ' + w(m.target))
            lines.append('forbid ' + w(m.forbidden))
            for pos in range(6 * r):
                for d in range(6):
                    lines.append('ray %d %d %s' % (pos, d, w(m.rays[pos][d])))
    open(out, 'w').write('\n'.join(lines) + '\n')
    print('wrote', out)


if __name__ == '__main__':
    main()
