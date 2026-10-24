#!/usr/bin/env python3
"""Synthetic invariants for CCC42 bottleneck diagnostics."""
import importlib.util
from pathlib import Path

path = Path(__file__).with_name("ccc42_bottleneck_diagnose.py")
spec = importlib.util.spec_from_file_location("diag",path)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class ToySim:
    def __init__(self, target, forbidden=0, rays_by_emitter=None):
        self.target = target
        self.forbidden = forbidden
        # Six positions for six directions (no movement used in tests).
        self.rays = [[0]*6 for _ in range(6)]
        for e, mask in (rays_by_emitter or {}).items():
            self.rays[0][e] = mask

    def initial(self):
        return (tuple([0]*6), 0, 0, 0)

    def step(self, state, line):
        pos, active, matter, copies = state
        pos = list(pos)
        for e, cmd in enumerate(line):
            if cmd == 'T':
                active ^= 1 << e
            elif cmd == 'F':
                pos[e] = (pos[e]-1)%6
            elif cmd == 'B':
                pos[e] = (pos[e]+1)%6
        one=two=three=0
        for e in range(6):
            if active>>e & 1:
                beam=self.rays[pos[e]][e]
                three |= two & beam
                two |= one & beam
                one |= beam
        matter = (matter | two) & ~three
        if matter & self.target == self.target and not matter & self.forbidden:
            copies += 1
            matter &= ~self.target
        return tuple(pos), active, matter, copies


def run(sim, actions, K):
    return mod.analyze_case(sim,[tuple(r) for r in actions],
                            dataset="test", index=1,
                            radius=1, K=K, n_target=sim.target.bit_count())


def test_reset_at_acceptance():
    sim=ToySim(1,rays_by_emitter={0:1,1:1})
    rows=run(sim,["TT----","------"],2)
    assert len(rows)==2
    assert [r["last_tick_new"] for r in rows]==[1,1]
    assert [r["late_build"] for r in rows]==[1,1]
    assert [r["late_churn"] for r in rows]==[0,0]


def test_churn_in_tail():
    sim=ToySim(3,rays_by_emitter={0:1,1:1,2:1,3:2,4:2})
    rows=run(sim,["TT----","--T---","--TTT-"],1)
    assert len(rows)==1
    assert rows[0]["late_build"]==1 # second target cell first built on final tick
    assert rows[0]["late_churn"]==1 # first target cell was erased and recreated
    assert rows[0]["late_rebuilt_unique"]==1
    assert rows[0]["last_tick_new"]==2


def test_skirting_clean():
    sim=ToySim(1,2,rays_by_emitter={0:1,1:1,3:2,4:2,5:2})
    rows=run(sim,["TT-TT-","-----T"],1)
    assert len(rows)==1
    assert rows[0]["late_clean"]==1
    assert rows[0]["last_tick_new"]==0


if __name__=="__main__":
    test_reset_at_acceptance()
    test_churn_in_tail()
    test_skirting_clean()
    print("TESTS PASS: acceptance reset, late churn, skirting cleanup")
