"""Fast exact bitmask model of level 6 + per-case analysis helpers.

Only cells in  target | forbidden  ("relevant" cells) can influence the score:
 - matter outside them never blocks a ray and never takes part in acceptance.
So the whole machine can be compressed to a handful of 64-bit words.
"""
import sys
from pathlib import Path
from functools import lru_cache

sys.dont_write_bytecode = True
REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from solve_l4 import geometry, STEPS           # noqa: E402
from solve_l6 import parse                     # noqa: E402
from optimize_l6 import load_programs          # noqa: E402

DATASETS = {'medium': '2-medium', 'large': '3-large', 'enormous': '4-enormous'}
INITIAL = None  # per case, computed


def in_path(ds):
    return REPO / 'level-6' / f'in_level-6_{DATASETS[ds]}.txt'


def ans_path(ds):
    return REPO / 'level-6' / f'answer_level-6_{DATASETS[ds]}.txt'


@lru_cache(None)
def cases(ds):
    return tuple(parse(in_path(ds)))


def programs(ds, path=None):
    return load_programs(Path(path) if path else ans_path(ds))


class Machine:
    """Exact simulator restricted to relevant cells."""

    __slots__ = ('r', 'required', 'cells', 'idx', 'target', 'forbidden',
                 'rel', 'bit', 'rays', 'initial')

    def __init__(self, case):
        r, pattern, required = case
        self.r = r
        self.required = required
        _, cells, rays = geometry(r)
        self.cells = cells
        self.idx = {p: i for i, p in enumerate(cells)}
        target = sum(1 << self.idx[p] for p in pattern)
        border = {(y + dy, x + dx) for y, x in pattern for dy, dx in STEPS} & self.idx.keys()
        forbidden = sum(1 << self.idx[p] for p in border - pattern)
        rel = target | forbidden
        # compressed masks over relevant-cell indices
        bit = [i for i, p in enumerate(cells) if rel >> i & 1]
        self.bit = tuple(bit)
        self.target = sum(1 << k for k, i in enumerate(bit) if target >> i & 1)
        self.forbidden = sum(1 << k for k, i in enumerate(bit) if forbidden >> i & 1)
        self.rel = (1 << len(bit)) - 1
        comp = []
        for p in range(6 * r):
            row = []
            for d in range(6):
                m = 0
                for k, i in enumerate(bit):
                    if rays[p][d] >> i & 1:
                        m |= 1 << k
                row.append(m)
            comp.append(tuple(row))
        self.rays = tuple(comp)
        self.initial = (0, 5 * r, 4 * r, 3 * r, 2 * r, r)

    # --- fast step -------------------------------------------------------
    def step(self, state, line):
        pos, active, matter, count = state
        pos = list(pos)
        for i, ch in enumerate(line):
            if ch == 'F':
                pos[i] = (pos[i] - 1) % (6 * self.r)
            elif ch == 'B':
                pos[i] = (pos[i] + 1) % (6 * self.r)
            elif ch == 'T':
                active ^= 1 << i
        one = two = three = 0
        for i in range(6):
            if active >> i & 1:
                ray = self.rays[pos[i]][i]
                three |= two & ray
                two |= one & ray
                one |= ray
        matter = (matter | two) & ~three
        if matter & self.target == self.target and not matter & self.forbidden:
            count += 1
            matter &= ~self.target
        return (tuple(pos), active, matter, count)

    def initial_state(self):
        return (self.initial, 0, 0, 0)

    def run(self, program, want_trace=False):
        st = self.initial_state()
        acc = []
        trace = []
        for t, line in enumerate(program, 1):
            old = st
            st = self.step(st, line)
            if st[3] != old[3]:
                acc.append(t)
            if want_trace:
                trace.append(self.tick_features(old, st, line))
        return st, acc, trace

    def tick_features(self, old, new, line):
        pos, active, matter, count = new
        one = two = three = 0
        for i in range(6):
            if active >> i & 1:
                ray = self.rays[pos[i]][i]
                three |= two & ray
                two |= one & ray
                one |= ray
        h2 = two & ~three
        return dict(
            new_target=(h2 & self.target & ~old[2]).bit_count(),
            repeat_target=(h2 & self.target & old[2]).bit_count(),
            kill_target=(three & old[2] & self.target).bit_count(),
            new_skirt=(h2 & self.forbidden & ~old[2]).bit_count(),
            kill_skirt=(three & old[2] & self.forbidden).bit_count(),
            h2=h2.bit_count(), h3=three.bit_count(),
            motion=sum(ch in 'FB' for ch in line),
            toggles=line.count('T'),
            active=(active.bit_count()),
            matter=(matter & self.rel).bit_count(),
        )


def encode(program):
    return [sum('-FBT'.index(ch) << (2 * e) for e, ch in enumerate(row)) for row in program]


def decode(rows):
    return [tuple('-FBT'[(a >> (2 * e)) & 3] for e in range(6)) for a in rows]


def valid_tail(machine, program):
    """True when the program accepts exactly K copies and never after the Kth."""
    st, acc, _ = machine.run(program)
    return st[3] == machine.required and bool(acc) and acc[-1] == len(program)
